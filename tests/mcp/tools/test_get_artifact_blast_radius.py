import json
from contextlib import contextmanager
from types import SimpleNamespace
import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.mcp import query_helpers, runtime as mcp_runtime
from contextor.mcp.tools.get_artifact_blast_radius import get_artifact_blast_radius


def _setup_blast_radius_state(monkeypatch):
    module_obj = SimpleNamespace(module_id="10/1", path="pkg/mod_a.py", imports=[])
    auth_module_obj = SimpleNamespace(module_id="13/1", path="pkg/services/auth.py", imports=[])

    state = RepositoryAnalysisState(
        modules={
            "pkg.mod_a": module_obj,
            "pkg.services.auth": auth_module_obj,
        },
        artifacts={
            "pkg.mod_a": {
                "own_symbols": ["my_func", "extra_func", "MyClass"],
                "symbols": {
                    "functions": ["my_func", "extra_func"],
                    "classes": ["MyClass"],
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
                    "MyClass": {
                        "consumer_count": {"total": 0},
                        "consumers": [],
                    },
                },
            },
            "pkg.services.auth": {
                "own_symbols": ["login_user", "authenticate_token"],
                "symbols": {
                    "functions": ["login_user", "authenticate_token"],
                },
                "consumers": {
                    "login_user": {
                        "consumer_count": {"total": 1},
                        "consumers": ["tests.test_1"],
                    },
                    "authenticate_token": {
                        "consumer_count": {"total": 1},
                        "consumers": ["tests.test_1"],
                    },
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
            "pkg.mod_a::MyClass": {
                "consumers": [],
                "channels": {},
            },
            "pkg.services.auth::login_user": {
                "consumers": ["tests.test_1"],
                "channels": {"tests.test_1": ["direct_calls"]},
            },
            "pkg.services.auth::authenticate_token": {
                "consumers": ["tests.test_1"],
                "channels": {"tests.test_1": ["direct_calls"]},
            },
        },
        artifact_consumption_state="fresh",
        cached_analytics={
            "module_layers": {
                "pkg.mod_a": "core",
                "pkg.services.auth": "service",
                "tests.test_1": "tests",
                "tests.test_2": "tests",
            }
        },
        cached_analytics_state="fresh",
    )

    mod_path_to_id = {"pkg.mod_a": "10/1", "pkg.services.auth": "13/1"}
    mod_id_to_path = {v: k for k, v in mod_path_to_id.items()}
    art_path_to_id = {
        "pkg.mod_a::my_func": "A100/1",
        "pkg.mod_a::extra_func": "A101/1",
        "pkg.mod_a::MyClass": "A102/1",
        "pkg.services.auth::login_user": "A103/1",
        "pkg.services.auth::authenticate_token": "A104/1",
    }
    art_id_to_path = {v: k for k, v in art_path_to_id.items()}

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )
    return state


class _LiveRegistry:
    def __init__(self, state):
        self._state = state
        self.read_transaction_count = 0

    @contextmanager
    def read_transaction(self):
        self.read_transaction_count += 1
        yield


def _registry_state(mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path):
    return {
        "module_registry": {
            "path_to_id": mod_path_to_id,
            "id_to_path": mod_id_to_path,
        },
        "artifact_registry": {
            "path_to_id": art_path_to_id,
            "id_to_path": art_id_to_path,
        },
    }


def test_get_artifact_blast_radius__fresh_live_reuses_engine_registry_with_exact_parity(
    tmp_path, monkeypatch
):
    state = _setup_blast_radius_state(monkeypatch)
    state.provenance = "live"
    mod_path_to_id = {"pkg.mod_a": "10/1", "pkg.services.auth": "13/1"}
    mod_id_to_path = {value: key for key, value in mod_path_to_id.items()}
    art_path_to_id = {
        "pkg.mod_a::my_func": "A100/1",
        "pkg.mod_a::extra_func": "A101/1",
        "pkg.mod_a::MyClass": "A102/1",
        "pkg.services.auth::login_user": "A103/1",
        "pkg.services.auth::authenticate_token": "A104/1",
    }
    art_id_to_path = {value: key for key, value in art_path_to_id.items()}
    registry = _LiveRegistry(
        _registry_state(mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path)
    )
    engine_calls = 0
    registry_reads = 0

    def get_live_engine(_root):
        nonlocal engine_calls
        engine_calls += 1
        return SimpleNamespace(state=state, provenance="live", registry=registry)

    def fail_registry_read(_root):
        nonlocal registry_reads
        registry_reads += 1
        raise AssertionError("fresh LIVE path must not call read_registries")

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", get_live_engine)
    monkeypatch.setattr(query_helpers, "read_registries", fail_registry_read)

    optimized = get_artifact_blast_radius(
        repo_path=str(tmp_path), artifact_name="A100/1", compact=False, max_items=1
    )

    assert engine_calls == 1
    assert registry.read_transaction_count == 1
    assert registry_reads == 0

    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=state, provenance="snapshot"),
    )
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )
    fallback = get_artifact_blast_radius(
        repo_path=str(tmp_path), artifact_name="A100/1", compact=False, max_items=1
    )

    assert optimized == fallback


@pytest.mark.parametrize(
    "artifact_name, representation",
    [
        ("A100/1", "named"),
        ("pkg.mod_a::my_func", "indexed"),
        ("my_func", "auto"),
        ("pkg.services.auth", "named"),
        ("my_funcc", "named"),
        ("completely_unrelated_xyz_123", "named"),
    ],
)
def test_get_artifact_blast_radius__fresh_live_registry_parity_for_contract_paths(
    tmp_path, monkeypatch, artifact_name, representation
):
    state = _setup_blast_radius_state(monkeypatch)
    state.provenance = "live"
    state.artifacts["pkg.services.auth"]["symbols"]["functions"].append("my_func")
    state.artifacts["pkg.services.auth"]["own_symbols"].append("my_func")
    state.artifact_consumption["pkg.services.auth::my_func"] = {
        "consumers": [],
        "channels": {},
    }
    mod_path_to_id = {"pkg.mod_a": "10/1", "pkg.services.auth": "13/1"}
    mod_id_to_path = {value: key for key, value in mod_path_to_id.items()}
    art_path_to_id = {
        "pkg.mod_a::my_func": "A100/1",
        "pkg.mod_a::extra_func": "A101/1",
        "pkg.mod_a::MyClass": "A102/1",
        "pkg.services.auth::login_user": "A103/1",
        "pkg.services.auth::authenticate_token": "A104/1",
        "pkg.services.auth::my_func": "A105/1",
    }
    art_id_to_path = {value: key for key, value in art_path_to_id.items()}
    registry = _LiveRegistry(
        _registry_state(mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path)
    )
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=state, provenance="snapshot"),
    )
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )
    baseline = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name=artifact_name,
        compact=False,
        max_items=10,
        representation=representation,
    )
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=state, provenance="live", registry=registry),
    )
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (_ for _ in ()).throw(AssertionError("unexpected fallback")),
    )
    optimized = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name=artifact_name,
        compact=False,
        max_items=10,
        representation=representation,
    )

    assert optimized == baseline


def test_get_artifact_blast_radius__unusable_live_paths_keep_registry_fallback(tmp_path, monkeypatch):
    state = _setup_blast_radius_state(monkeypatch)
    reads = 0

    def read_registries(_root):
        nonlocal reads
        reads += 1
        return ({}, {}, {}, {})

    monkeypatch.setattr(query_helpers, "read_registries", read_registries)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
    assert get_artifact_blast_radius(repo_path=str(tmp_path), artifact_name="A999/1") == (
        "Error: No usable canonical LIVE state. Run analyze_project first."
    )
    assert reads == 1

    state.resync_required = True
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=state, provenance="live", registry=_LiveRegistry({})),
    )
    assert get_artifact_blast_radius(repo_path=str(tmp_path), artifact_name="A999/1") == (
        "Error: No usable canonical LIVE state. Run analyze_project first."
    )
    assert reads == 2


def test_get_artifact_blast_radius__legacy_normal_artifact_success(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"
    assert res["artifact_id"] == "A100/1"
    assert res["consumers"]["total"] == 2


def test_get_artifact_blast_radius__artifact_alias_success(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"
    assert res["artifact_id"] == "A100/1"


def test_get_artifact_blast_radius__artifact_name_legacy_success(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"
    assert res["artifact_id"] == "A100/1"


def test_get_artifact_blast_radius__both_aliases_identical_success(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name="pkg.mod_a::my_func",
        artifact="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"
    assert res["artifact_id"] == "A100/1"


def test_get_artifact_blast_radius__alias_conflict_controlled_error(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact_name="pkg.mod_a::my_func",
        artifact="pkg.mod_a::extra_func",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "artifact_name and artifact must match when both are provided."


def test_get_artifact_blast_radius__missing_both_controlled_error(tmp_path):
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "artifact_name or artifact is required."


def test_get_artifact_blast_radius__exact_active_artifact_id(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="A100/1",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"
    assert res["artifact_id"] == "A100/1"
    assert res["consumers"]["total"] == 2


def test_get_artifact_blast_radius__lowercase_artifact_id(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="a100/1",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"
    assert res["artifact_id"] == "A100/1"


def test_get_artifact_blast_radius__nonexistent_artifact_id_never_fuzzy_and_no_module_redirect(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="A9999/1",
    )
    assert raw == "Artifact 'A9999/1' not found in the registry."


def test_get_artifact_blast_radius__exact_full_canonical_identity(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.services.auth::login_user",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.services.auth::login_user"
    assert res["artifact_id"] == "A103/1"


def test_get_artifact_blast_radius__existing_unique_local_symbol_lookup(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="login_user",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.services.auth::login_user"
    assert res["artifact_id"] == "A103/1"


def test_get_artifact_blast_radius__existing_ambiguity_handling(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    # Add duplicate symbol leaf across modules
    state = mcp_runtime.get_or_init_engine(tmp_path).state
    state.artifacts["pkg.services.auth"]["symbols"]["functions"].append("my_func")
    state.artifacts["pkg.services.auth"]["own_symbols"].append("my_func")
    state.artifacts["pkg.services.auth"]["consumers"]["my_func"] = {
        "consumer_count": {"total": 0},
        "consumers": [],
    }
    state.artifact_consumption["pkg.services.auth::my_func"] = {
        "consumers": [],
        "channels": {},
    }

    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="my_func",
    )
    res = json.loads(raw)
    assert res["error"] == "Ambiguous canonical artifact identity."
    assert "pkg.mod_a::my_func" in res["candidates"]
    assert "pkg.services.auth::my_func" in res["candidates"]


def test_get_artifact_blast_radius__module_input_redirect_preserved(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.services.auth",
    )
    res = json.loads(raw)
    assert res["resolved_as"] == "module"
    assert res["module"] == "pkg.services.auth"
    assert res["suggested_next_tool"] == "get_module_context"
    assert res["suggested_next_call"] == {
        "tool": "get_module_context",
        "arguments": {
            "module": "pkg.services.auth",
        },
    }
    assert "similar_candidates" not in res
    assert "artifact_candidates" in res


def test_get_artifact_blast_radius__module_input_does_not_return_fuzzy(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["resolved_as"] == "module"
    assert res["module"] == "pkg.mod_a"
    assert "similar_candidates" not in res


def test_get_artifact_blast_radius__fuzzy_leaf_typo_suggestions(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="login_usr",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "login_usr"
    assert res["data_source"] == "active_artifact_registry"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["artifact"] == "pkg.services.auth::login_user"
    assert top["artifact_id"] == "A103/1"
    assert top["score"] >= 0.75


def test_get_artifact_blast_radius__fuzzy_full_identity_typo_suggestions(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.services.auth::login_usr",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg.services.auth::login_usr"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["artifact"] == "pkg.services.auth::login_user"
    assert top["artifact_id"] == "A103/1"


def test_get_artifact_blast_radius__fuzzy_candidate_structure(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="authenticat_token",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "similar_candidates" in res
    candidate = res["similar_candidates"][0]
    assert "artifact" in candidate
    assert "artifact_id" in candidate
    assert "score" in candidate
    assert candidate["artifact"] == "pkg.services.auth::authenticate_token"
    assert candidate["artifact_id"] == "A104/1"
    assert isinstance(candidate["score"], float)


def test_get_artifact_blast_radius__fuzzy_never_auto_resolves(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="my_funcc",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "consumers" not in res
    assert len(res["similar_candidates"]) > 0


def test_get_artifact_blast_radius__fuzzy_max_five_candidates(tmp_path, monkeypatch):
    state = RepositoryAnalysisState(
        artifacts={
            "pkg.mod": {
                "symbols": {"functions": [f"func_{i}" for i in range(10)]},
                "own_symbols": [f"func_{i}" for i in range(10)],
            }
        },
        artifact_consumption={},
        artifact_consumption_state="fresh",
    )
    art_path_to_id = {f"pkg.mod::func_{i}": f"A{100+i}/1" for i in range(10)}
    art_id_to_path = {v: k for k, v in art_path_to_id.items()}

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: ({}, {}, art_path_to_id, art_id_to_path))

    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="func_x",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert len(res["similar_candidates"]) <= 5


def test_get_artifact_blast_radius__unrelated_query_exact_legacy_fallback(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="completely_unrelated_xyz_123",
    )
    assert raw == "Artifact 'completely_unrelated_xyz_123' not found in the registry."


def test_get_artifact_blast_radius__exact_artifact_id_currentness_fail_closed(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    monkeypatch.setattr(
        query_helpers,
        "module_truth_unavailable",
        lambda _state, mod: {"status": "stale", "module": mod} if mod == "pkg.mod_a" else None,
    )

    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="A100/1",
    )
    res = json.loads(raw)
    assert res["status"] == "stale"
    assert res["module"] == "pkg.mod_a"


def test_get_artifact_blast_radius__exact_artifact_id_respects_presentation_controls(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="A100/1",
        compact=False,
        max_items=1,
        fields=["artifact", "artifact_id", "consumers"],
        representation="named",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"
    assert res["artifact_id"] == "A100/1"
    assert res["consumers"]["total"] == 2
    assert len(res["consumers"]["items"]) == 1
    assert res["consumers"]["truncated"] is True


def test_get_artifact_blast_radius__valid_normal_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_artifact_identity should NOT have been called for valid normal artifact!")

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", fail_if_called)

    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.mod_a::my_func",
    )
    res = json.loads(raw)
    assert res["artifact"] == "pkg.mod_a::my_func"


def test_get_artifact_blast_radius__module_redirect_path_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_artifact_identity should NOT have been called on module redirect path!")

    monkeypatch.setattr(query_helpers, "resolve_artifact_identity", fail_if_called)

    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="pkg.services.auth",
    )
    res = json.loads(raw)
    assert res["resolved_as"] == "module"


def test_get_artifact_blast_radius__missing_id_with_no_engine_returns_global_error(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="A9999/1",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."


def test_get_artifact_blast_radius__missing_id_with_resync_required_returns_global_error(tmp_path, monkeypatch):
    _setup_blast_radius_state(monkeypatch)
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=SimpleNamespace(resync_required=True)),
    )

    raw = get_artifact_blast_radius(
        repo_path=str(tmp_path),
        artifact="A9999/1",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."
