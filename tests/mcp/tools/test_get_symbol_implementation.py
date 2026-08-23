import json
from types import SimpleNamespace
from pathlib import Path
import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.mcp import query_helpers, runtime as mcp_runtime
from contextor.mcp.tools.get_symbol_implementation import get_symbol_implementation


def _setup_symbol_implementation_workspace(tmp_path, monkeypatch):
    """Creates real Python source files on disk and mocks the active registry and LIVE state."""
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    services_dir = pkg_dir / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    file_a = pkg_dir / "a.py"
    file_a.write_text(
        "def process_data(x):\n"
        "    \"\"\"Process input data.\"\"\"\n"
        "    return x * 2\n\n"
        "def helper_func():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    file_b = pkg_dir / "b.py"
    file_b.write_text(
        "def process_datum(y):\n"
        "    \"\"\"Process datum.\"\"\"\n"
        "    return y + 1\n\n"
        "def helper_func():\n"
        "    return 2\n",
        encoding="utf-8",
    )

    file_auth = services_dir / "auth.py"
    file_auth.write_text(
        "class AuthService:\n"
        "    def login(self, username, password):\n"
        "        return True\n"
        "    def logout(self):\n"
        "        pass\n\n"
        "def authenticate(token):\n"
        "    return token == 'valid'\n",
        encoding="utf-8",
    )

    mod_a_obj = SimpleNamespace(module_id="10/1", path="pkg/a.py")
    mod_b_obj = SimpleNamespace(module_id="11/1", path="pkg/b.py")
    mod_auth_obj = SimpleNamespace(module_id="13/1", path="pkg/services/auth.py")

    state = RepositoryAnalysisState(
        modules={
            "pkg.a": mod_a_obj,
            "pkg.b": mod_b_obj,
            "pkg.services.auth": mod_auth_obj,
        },
        artifacts={
            "pkg.a": {
                "own_symbols": ["process_data", "helper_func"],
                "symbols": {"functions": ["process_data", "helper_func"]},
                "consumers": {"process_data": ["pkg.b"], "helper_func": []},
            },
            "pkg.b": {
                "own_symbols": ["process_datum", "helper_func"],
                "symbols": {"functions": ["process_datum", "helper_func"]},
                "consumers": {"process_datum": [], "helper_func": []},
            },
            "pkg.services.auth": {
                "own_symbols": ["AuthService", "AuthService.login", "AuthService.logout", "authenticate"],
                "symbols": {
                    "classes": ["AuthService"],
                    "functions": ["authenticate"],
                    "methods": ["AuthService.login", "AuthService.logout"],
                },
                "consumers": {"authenticate": ["pkg.a"], "AuthService": []},
            },
        },
        artifact_consumption={},
        artifact_consumption_state="fresh",
    )

    mod_path_to_id = {
        "pkg.a": "10/1",
        "pkg.b": "11/1",
        "pkg.services.auth": "13/1",
    }
    mod_id_to_path = {v: k for k, v in mod_path_to_id.items()}

    art_path_to_id = {
        "pkg.a::process_data": "A10/1",
        "pkg.a::helper_func": "A10/2",
        "pkg.b::process_datum": "A11/1",
        "pkg.b::helper_func": "A11/2",
        "pkg.services.auth::AuthService": "A13/1",
        "pkg.services.auth::AuthService.login": "A13/2",
        "pkg.services.auth::AuthService.logout": "A13/3",
        "pkg.services.auth::authenticate": "A13/4",
    }
    art_id_to_path = {v: k for k, v in art_path_to_id.items()}

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )

    return {
        "state": state,
        "mod_path_to_id": mod_path_to_id,
        "mod_id_to_path": mod_id_to_path,
        "art_path_to_id": art_path_to_id,
        "art_id_to_path": art_id_to_path,
    }


# ============================================================
# 1. LEGACY CONTRACT TESTS
# ============================================================

def test_get_symbol_implementation__plain_leaf_file_path_success(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert res["resolution"]["symbol"] == "process_data"
    assert "def process_data(x):" in res["implementation"]


def test_get_symbol_implementation__plain_leaf_file_paths_success(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
        file_paths=["pkg/a.py"],
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert "def process_data(x):" in res["implementation"]


def test_get_symbol_implementation__file_path_alias_merge_dedupe(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
        file_paths=["pkg/a.py"],
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["resolution"]["symbol"] == "process_data"


def test_get_symbol_implementation__plain_leaf_without_files_required_error(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "At least one Python source file is required."


def test_get_symbol_implementation__ambiguous_leaf_fail_closed(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="helper_func",
        file_paths=["pkg/a.py", "pkg/b.py"],
    )
    res = json.loads(raw)
    assert res["status"] == "ambiguous"
    assert res["candidate_count"] == 2
    assert "implementation" not in res


def test_get_symbol_implementation__explicit_preview_unchanged(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
        file_path="pkg/a.py",
        mode="preview",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "preview"
    assert "fetch_plans" in res
    assert "implementation" not in res


def test_get_symbol_implementation__explicit_fetch_include_unchanged(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
        file_path="pkg/a.py",
        mode="fetch",
        include=["signature", "docstring"],
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "def process_data(x)" in res["signature"]
    assert res["docstring"] == "Process input data."
    assert "implementation" not in res


# ============================================================
# 2. ARTIFACT ID & QUALIFIED IDENTITY
# ============================================================

def test_get_symbol_implementation__exact_active_artifact_id_explicit_correct_file(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["resolution"]["symbol"] == "process_data"
    assert "def process_data(x):" in res["implementation"]


def test_get_symbol_implementation__lowercase_artifact_id_success(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="a10/1",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["resolution"]["symbol"] == "process_data"


def test_get_symbol_implementation__exact_artifact_id_wrong_explicit_file_fails_closed(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
        file_path="pkg/b.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "outside the requested file constraints" in res["message"]
    assert "implementation" not in res


def test_get_symbol_implementation__exact_artifact_id_without_file_canonical_live_path(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["resolution"]["symbol"] == "process_data"
    assert "def process_data(x):" in res["implementation"]


def test_get_symbol_implementation__missing_artifact_id_not_found_no_fuzzy(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A999/1",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "similar_candidates" not in res
    assert "A999/1" in res["message"]


def test_get_symbol_implementation__exact_canonical_qualified_identity_correct_file(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="pkg.a::process_data",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["resolution"]["symbol"] == "process_data"
    assert "def process_data(x):" in res["implementation"]


def test_get_symbol_implementation__exact_canonical_qualified_identity_wrong_file_fails_closed(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="pkg.a::process_data",
        file_path="pkg/b.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "outside the requested file constraints" in res["message"]


def test_get_symbol_implementation__exact_canonical_qualified_identity_without_file_canonical_live_path(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="pkg.services.auth::authenticate",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["resolution"]["symbol"] == "authenticate"
    assert "def authenticate(token):" in res["implementation"]


def test_get_symbol_implementation__wrong_module_prefix_no_false_success(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    # pkg.wrong::process_data must NOT silently match process_data from pkg/a.py
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="pkg.wrong::process_data",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "implementation" not in res


# ============================================================
# 3. FUZZY SUGGESTIONS & SCOPING
# ============================================================

def test_get_symbol_implementation__plain_leaf_typo_explicit_file_scoped_suggestions(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_dat",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["symbol"] == "process_dat"
    assert res["data_source"] == "active_artifact_registry"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["artifact"] == "pkg.a::process_data"
    assert top["artifact_id"] == "A10/1"
    assert "implementation" not in res


def test_get_symbol_implementation__scoped_fuzzy_candidate_belongs_only_to_explicit_scope(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_dat",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    candidate_artifacts = [c["artifact"] for c in res["similar_candidates"]]
    # Must only contain pkg.a artifacts, not pkg.b::process_datum
    for art in candidate_artifacts:
        assert art.startswith("pkg.a::")
    assert "pkg.b::process_datum" not in candidate_artifacts


def test_get_symbol_implementation__global_out_of_scope_does_not_displace_in_scope_candidate(tmp_path, monkeypatch):
    """Important scoped fuzzy test (Section 19)."""
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    # Query 'process_datum' matches pkg.b::process_datum better globally (score 1.0), but file is pkg/a.py
    # In pkg.a, 'process_data' qualifies with score >= 0.75 (0.9167).
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_datum",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "similar_candidates" in res
    assert len(res["similar_candidates"]) >= 1
    candidate_artifacts = [c["artifact"] for c in res["similar_candidates"]]
    assert "pkg.a::process_data" in candidate_artifacts
    assert "pkg.b::process_datum" not in candidate_artifacts
    assert all(art.startswith("pkg.a::") for art in candidate_artifacts)


def test_get_symbol_implementation__qualified_typo_without_files_global_suggestions(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="pkg.services.auth::authenticte",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert len(res["similar_candidates"]) > 0
    assert res["similar_candidates"][0]["artifact"] == "pkg.services.auth::authenticate"


def test_get_symbol_implementation__fuzzy_never_auto_resolves(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_dat",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "implementation" not in res
    assert "resolution" not in res


def test_get_symbol_implementation__fuzzy_max_five_candidates(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="func",
        file_paths=["pkg/a.py", "pkg/b.py"],
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    if res.get("similar_candidates"):
        assert len(res["similar_candidates"]) <= 5


def test_get_symbol_implementation__unrelated_query_explicit_files_legacy_not_found(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="completely_unrelated_xyz",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["message"] == "No exact class, function, or method match was found."
    assert "similar_candidates" not in res


def test_get_symbol_implementation__missing_artifact_id_never_fuzzy(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A999/99",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "similar_candidates" not in res


# ============================================================
# 4. PIPELINE & AUTO DECISION
# ============================================================

def test_get_symbol_implementation__valid_plain_leaf_lookup_does_not_call_shared_resolver(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_artifact_identity should NOT have been called for valid plain leaf lookup!")

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", fail_if_called)

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["resolution"]["symbol"] == "process_data"


def test_get_symbol_implementation__ast_ambiguity_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_artifact_identity should NOT have been called for ambiguous AST lookup!")

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", fail_if_called)

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="helper_func",
        file_paths=["pkg/a.py", "pkg/b.py"],
    )
    res = json.loads(raw)
    assert res["status"] == "ambiguous"


def test_get_symbol_implementation__exact_id_and_canonical_identity_same_result_builder(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw_id = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
        file_path="pkg/a.py",
    )
    raw_qualified = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="pkg.a::process_data",
        file_path="pkg/a.py",
    )
    res_id = json.loads(raw_id)
    res_qualified = json.loads(raw_qualified)
    assert res_id == res_qualified


def test_get_symbol_implementation__exact_id_respects_mode_preview(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
        mode="preview",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "preview"
    assert "fetch_plans" in res
    assert "implementation" not in res


def test_get_symbol_implementation__exact_id_respects_explicit_fetch_include(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
        mode="fetch",
        include=["signature"],
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "def process_data(x)" in res["signature"]
    assert "implementation" not in res


def test_get_symbol_implementation__exact_id_auto_small_response_uses_existing_fetch_decision(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
        mode="auto",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "fetch"
    assert "auto_fetch" not in res
    assert "def process_data(x):" in res["implementation"]


def test_get_symbol_implementation__exact_id_auto_large_response_uses_existing_preview_decision(tmp_path, monkeypatch):
    ws = _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    # Create a large source function (>5120 bytes) in pkg/a.py
    pkg_dir = tmp_path / "pkg"
    large_code = "def large_symbol():\n" + "    x = 1\n" * 1500
    file_large = pkg_dir / "large.py"
    file_large.write_text(large_code, encoding="utf-8")

    ws["mod_path_to_id"]["pkg.large"] = "19/1"
    ws["mod_id_to_path"]["19/1"] = "pkg.large"
    ws["art_path_to_id"]["pkg.large::large_symbol"] = "A19/1"
    ws["art_id_to_path"]["A19/1"] = "pkg.large::large_symbol"
    ws["state"].modules["pkg.large"] = SimpleNamespace(module_id="19/1", path="pkg/large.py")
    ws["state"].artifacts["pkg.large"] = {
        "own_symbols": ["large_symbol"],
        "symbols": {"functions": ["large_symbol"]},
        "consumers": {},
    }

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A19/1",
        mode="auto",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert res["mode"] == "preview"
    assert "auto_fetch" in res
    assert res["auto_fetch"]["decision"] == "preview"
    assert res["auto_fetch"]["threshold_bytes"] == 5120
    assert res["auto_fetch"]["candidate_response_bytes"] > 5120
    assert "implementation" not in res


# ============================================================
# 5. CURRENTNESS & LIVE DEPENDENCY
# ============================================================

def test_get_symbol_implementation__inferred_source_path_fails_closed_no_usable_canonical_live(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert "No usable canonical LIVE state" in res["error"]


def test_get_symbol_implementation__inferred_source_path_fails_closed_for_stale_module(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    monkeypatch.setattr(
        query_helpers,
        "module_truth_unavailable",
        lambda _state, mod: {"status": "stale", "module": mod} if mod == "pkg.a" else None,
    )

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="A10/1",
    )
    res = json.loads(raw)
    assert res["status"] == "stale"
    assert res["module"] == "pkg.a"


def test_get_symbol_implementation__explicit_correct_source_does_not_require_global_live(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    # When explicit file_path is given, AST search works even if engine is None
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert "def process_data(x):" in res["implementation"]


# ============================================================
# 6. LAZY REGISTRY OWNERSHIP & FAILURE ISOLATION
# ============================================================

def test_get_symbol_implementation__plain_leaf_success_does_not_read_registry(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)

    def fail_if_read(*_args, **_kwargs):
        raise AssertionError("read_registries MUST NOT be called for plain leaf exact match!")

    monkeypatch.setattr(query_helpers, "read_registries", fail_if_read)

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "resolved"
    assert "def process_data(x):" in res["implementation"]


def test_get_symbol_implementation__plain_leaf_ambiguity_does_not_read_registry(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)

    def fail_if_read(*_args, **_kwargs):
        raise AssertionError("read_registries MUST NOT be called for plain leaf ambiguity!")

    monkeypatch.setattr(query_helpers, "read_registries", fail_if_read)

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="helper_func",
        file_paths=["pkg/a.py", "pkg/b.py"],
    )
    res = json.loads(raw)
    assert res["status"] == "ambiguous"


def test_get_symbol_implementation__plain_leaf_without_files_does_not_read_registry(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)

    def fail_if_read(*_args, **_kwargs):
        raise AssertionError("read_registries MUST NOT be called for plain leaf without files!")

    monkeypatch.setattr(query_helpers, "read_registries", fail_if_read)

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_data",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "At least one Python source file is required."


def test_get_symbol_implementation__fuzzy_miss_does_read_registry(tmp_path, monkeypatch):
    _setup_symbol_implementation_workspace(tmp_path, monkeypatch)
    reads = []
    original_read = query_helpers.read_registries

    def counting_read(root):
        reads.append(root)
        return original_read(root)

    monkeypatch.setattr(query_helpers, "read_registries", counting_read)

    raw = get_symbol_implementation(
        repo_path=str(tmp_path),
        symbol="process_dat",
        file_path="pkg/a.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert len(reads) == 1
    assert len(res["similar_candidates"]) >= 1

