import json
from contextlib import nullcontext
from types import SimpleNamespace
import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.mcp import query_helpers, runtime as mcp_runtime
from contextor.mcp.tools.get_artifacts_for_module import get_artifacts_for_module


def _setup_test_state(monkeypatch):
    """Sets up a minimal isolated RepositoryAnalysisState and active registry."""
    module_obj = SimpleNamespace(module_id="10/1", path="pkg/mod_a.py", imports=[])
    auth_module_obj = SimpleNamespace(module_id="13/1", path="pkg/services/auth.py", imports=[])
    state = RepositoryAnalysisState(
        modules={
            "pkg.mod_a": module_obj,
            "pkg.services.auth": auth_module_obj,
        },
        artifacts={
            "pkg.mod_a": {
                "own_symbols": ["my_func", "extra_func"],
                "symbols": {
                    "functions": ["my_func", "extra_func"],
                },
                "consumers": {
                    "my_func": {
                        "consumer_count": {"total": 2},
                        "consumers": ["tests.test_1", "tests.test_2"],
                    },
                    "extra_func": {
                        "consumer_count": {"total": 1},
                        "consumers": ["tests.test_1"],
                    },
                },
            },
            "pkg.services.auth": {
                "own_symbols": ["login"],
                "symbols": {
                    "functions": ["login"],
                },
                "consumers": {
                    "login": {
                        "consumer_count": {"total": 1},
                        "consumers": ["tests.test_1"],
                    }
                },
            },
        },
        artifact_consumption={
            "pkg.mod_a::my_func": {
                "consumers": ["tests.test_1", "tests.test_2"],
                "channels": {"tests.test_1": ["direct_calls"], "tests.test_2": ["direct_calls"]},
            },
            "pkg.mod_a::extra_func": {
                "consumers": ["tests.test_1"],
                "channels": {"tests.test_1": ["direct_calls"]},
            },
            "pkg.services.auth::login": {
                "consumers": ["tests.test_1"],
                "channels": {"tests.test_1": ["direct_calls"]},
            },
        },
        artifact_consumption_state="fresh",
    )
    mod_path_to_id = {"pkg.mod_a": "10/1", "pkg.services.auth": "13/1"}
    mod_id_to_path = {v: k for k, v in mod_path_to_id.items()}
    art_path_to_id = {
        "pkg.mod_a::my_func": "A1/1",
        "pkg.mod_a::extra_func": "A2/1",
        "pkg.services.auth::login": "A3/1",
    }
    art_id_to_path = {v: k for k, v in art_path_to_id.items()}
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path))
    return state


def test_get_artifacts_for_module__legacy_dotted_module_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_get_artifacts_for_module__legacy_path_normalization_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg/mod_a.py",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_get_artifacts_for_module__module_alias_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_get_artifacts_for_module__module_name_legacy_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_get_artifacts_for_module__both_aliases_identical_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_get_artifacts_for_module__alias_conflict_controlled_error(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
        module="pkg.mod_b",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "module_name and module must match when both are provided."


def test_get_artifacts_for_module__missing_both_controlled_error(tmp_path):
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "module_name or module is required."


def test_get_artifacts_for_module__exact_module_id_via_module_alias(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="10/1",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert res["module_id"] == "10/1"
    assert "A1/1" in res["artifacts"]


def test_get_artifacts_for_module__exact_module_id_via_legacy_module_name(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="10/1",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert res["module_id"] == "10/1"
    assert "A1/1" in res["artifacts"]


def test_get_artifacts_for_module__nonexistent_module_id_never_fuzzy(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="9999/1",
    )
    assert raw == "Module '9999/1' not found in registry or canonical LIVE state. Check the module name or run an analysis."


def test_get_artifacts_for_module__fuzzy_dotted_typo_suggestions(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.servces.auth",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg.servces.auth"
    assert res["data_source"] == "active_module_registry"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["module"] == "pkg.services.auth"
    assert top["module_id"] == "13/1"
    assert top["score"] >= 0.75
    assert "artifacts" not in res


def test_get_artifacts_for_module__fuzzy_path_typo_suggestions(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg/servces/auth.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg/servces/auth.py"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["module"] == "pkg.services.auth"
    assert top["module_id"] == "13/1"
    assert top["score"] >= 0.75


def test_get_artifacts_for_module__fuzzy_never_auto_resolves(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.mod_aa",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "artifacts" not in res
    assert len(res["similar_candidates"]) > 0


def test_get_artifacts_for_module__fuzzy_max_five_candidates(tmp_path, monkeypatch):
    state = RepositoryAnalysisState(
        artifacts={f"pkg.module_{i}": {"symbols": {}} for i in range(10)},
        artifact_consumption={},
        artifact_consumption_state="fresh",
    )
    mod_p2i = {f"pkg.module_{i}": f"{100+i}/1" for i in range(10)}
    mod_i2p = {v: k for k, v in mod_p2i.items()}

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: (mod_p2i, mod_i2p, {}, {}))

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.modul_x",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert len(res["similar_candidates"]) <= 5


def test_get_artifacts_for_module__unrelated_query_exact_legacy_fallback(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="completely_unrelated_xyz",
    )
    assert raw == "Module 'completely_unrelated_xyz' not found in registry or canonical LIVE state. Check the module name or run an analysis."


def test_get_artifacts_for_module__exact_module_id_currentness_fail_closed(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    monkeypatch.setattr(
        query_helpers,
        "module_truth_unavailable",
        lambda _state, mod: {"status": "stale", "module": mod} if mod == "pkg.mod_a" else None,
    )

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="10/1",
    )
    res = json.loads(raw)
    assert res["status"] == "stale"
    assert res["module"] == "pkg.mod_a"


def test_get_artifacts_for_module__exact_module_id_respects_presentation_controls(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="10/1",
        compact=False,
        limit=1,
        representation="named",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert res["artifact_count"] == 1
    assert res["truncated"] is True


def test_get_artifacts_for_module__valid_dotted_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_module_identity should NOT have been called for valid dotted module!")

    monkeypatch.setattr(query_helpers, "resolve_module_identity", fail_if_called)

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"


def test_get_artifacts_for_module__valid_path_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_module_identity should NOT have been called for valid path lookup!")

    monkeypatch.setattr(query_helpers, "resolve_module_identity", fail_if_called)

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg/mod_a.py",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"


def test_get_artifacts_for_module__fuzzy_miss_calls_resolver_with_normalized_query(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    orig_resolve = query_helpers.resolve_module_identity
    calls = []

    def tracking_resolver(query, p2i, i2p):
        calls.append(query)
        return orig_resolve(query, p2i, i2p)

    monkeypatch.setattr(query_helpers, "resolve_module_identity", tracking_resolver)

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg/servces/auth.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg/servces/auth.py"
    assert len(calls) == 1
    assert calls[0] == "pkg.servces.auth"


def test_get_artifacts_for_module__missing_id_with_no_engine_returns_global_error(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="9999/1",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."


def test_get_artifacts_for_module__missing_id_with_resync_required_returns_global_error(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=SimpleNamespace(resync_required=True)),
    )

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="9999/1",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."


def test_get_artifacts_for_module__existing_id_with_no_engine_returns_global_error(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="10/1",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."


def test_get_artifacts_for_module__usable_live_with_missing_id_preserves_legacy_not_found(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="9999/1",
    )
    assert raw == "Module '9999/1' not found in registry or canonical LIVE state. Check the module name or run an analysis."


def test_get_artifacts_for_module__fresh_live_reuses_engine_registry_with_exact_parity(tmp_path, monkeypatch):
    state = _setup_test_state(monkeypatch)
    request = {
        "repo_path": str(tmp_path),
        "module_name": "pkg.mod_a",
        "compact": False,
        "limit": 20,
        "evidence_limit": 3,
        "representation": "named",
    }
    expected = get_artifacts_for_module(**request)
    mod_path_to_id = {"pkg.mod_a": "10/1", "pkg.services.auth": "13/1"}
    art_path_to_id = {
        "pkg.mod_a::my_func": "A1/1",
        "pkg.mod_a::extra_func": "A2/1",
        "pkg.services.auth::login": "A3/1",
    }
    registry = SimpleNamespace(
        _state={
            "module_registry": {
                "path_to_id": mod_path_to_id,
                "id_to_path": {value: key for key, value in mod_path_to_id.items()},
            },
            "artifact_registry": {
                "path_to_id": art_path_to_id,
                "id_to_path": {value: key for key, value in art_path_to_id.items()},
            },
        }
    )
    transaction_calls = []
    registry.read_transaction = lambda: (transaction_calls.append(True) or nullcontext())
    engine_calls = []
    read_calls = []

    def fresh_live_engine(_root):
        engine_calls.append(True)
        return SimpleNamespace(state=state, provenance="live", registry=registry)

    def fail_if_read(_root):
        read_calls.append(True)
        raise AssertionError("fresh LIVE path must not call read_registries")

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", fresh_live_engine)
    monkeypatch.setattr(query_helpers, "read_registries", fail_if_read)

    raw = get_artifacts_for_module(**request)

    assert raw == expected
    assert len(engine_calls) == 1
    assert len(transaction_calls) == 1
    assert read_calls == []


@pytest.mark.parametrize("engine", [None, SimpleNamespace(state=SimpleNamespace(resync_required=True))])
def test_get_artifacts_for_module__nonfresh_live_paths_keep_registry_fallback(tmp_path, monkeypatch, engine):
    _setup_test_state(monkeypatch)
    read_calls = []
    registries = ({"pkg.mod_a": "10/1"}, {"10/1": "pkg.mod_a"}, {}, {})

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (read_calls.append(True) or registries),
    )

    raw = get_artifacts_for_module(repo_path=str(tmp_path), module_name="pkg.mod_a")

    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."
    assert len(read_calls) == 1


def test_get_artifacts_for_module__original_query_preserved_and_candidate_structure(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg/servces/auth.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg/servces/auth.py"
    assert "similar_candidates" in res
    candidate = res["similar_candidates"][0]
    assert "module" in candidate
    assert "module_id" in candidate
    assert "score" in candidate
    assert candidate["module"] == "pkg.services.auth"
    assert candidate["module_id"] == "13/1"
    assert isinstance(candidate["score"], float)


def test_get_artifacts_for_module__runtime_description_and_discovery_parity():
    from contextor import mcp_server
    from contextor.mcp import documentation

    tool = mcp_server.mcp._tool_manager._tools["get_artifacts_for_module"]
    index = documentation.load_documentation_index()
    entry = next(
        item for item in index["tools"]
        if item["tool"] == "get_artifacts_for_module"
    )

    assert tool.description == entry["short_description"]
    assert tool.fn.__doc__ is None
    assert len(tool.description.encode("utf-8")) <= 300

    description = tool.description.lower()
    assert "directly" in description
    assert "dotted name" in description
    assert "source path" in description
    assert "module id" in description
    assert "no prior get_module_context" in description

    doc = documentation.load_tool_document("get_artifacts_for_module")
    usage_text = " ".join(doc.get("usage_notes", [])).lower()
    assert "get_module_context" in usage_text
    assert "directly" in usage_text

    behavior_text = " ".join(doc.get("behavior", [])).lower()
    assert "without requiring a prior get_module_context call" in behavior_text

    params_text = " ".join(doc.get("parameters", [])).lower()
    assert "alias-conflict" in params_text or "conflict" in params_text
    assert "identical" in params_text
