import json
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


def test_legacy_dotted_module_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_legacy_path_normalization_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg/mod_a.py",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_module_alias_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_module_name_legacy_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_both_aliases_identical_success(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "A1/1" in res["artifacts"]


def test_alias_conflict_controlled_error(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
        module="pkg.mod_b",
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "module_name and module must match when both are provided."


def test_missing_both_controlled_error(tmp_path):
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
    )
    res = json.loads(raw)
    assert res["status"] == "error"
    assert res["error"] == "module_name or module is required."


def test_exact_module_id_via_module_alias(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="10/1",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert res["module_id"] == "10/1"
    assert "A1/1" in res["artifacts"]


def test_exact_module_id_via_legacy_module_name(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module_name="10/1",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert res["module_id"] == "10/1"
    assert "A1/1" in res["artifacts"]


def test_nonexistent_module_id_never_fuzzy(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="9999/1",
    )
    assert raw == "Module '9999/1' not found in registry or canonical LIVE state. Check the module name or run an analysis."


def test_fuzzy_dotted_typo_suggestions(tmp_path, monkeypatch):
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


def test_fuzzy_path_typo_suggestions(tmp_path, monkeypatch):
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


def test_fuzzy_never_auto_resolves(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.mod_aa",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "artifacts" not in res
    assert len(res["similar_candidates"]) > 0


def test_fuzzy_max_five_candidates(tmp_path, monkeypatch):
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


def test_unrelated_query_exact_legacy_fallback(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="completely_unrelated_xyz",
    )
    assert raw == "Module 'completely_unrelated_xyz' not found in registry or canonical LIVE state. Check the module name or run an analysis."


def test_exact_module_id_currentness_fail_closed(tmp_path, monkeypatch):
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


def test_exact_module_id_respects_presentation_controls(tmp_path, monkeypatch):
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


def test_valid_dotted_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    orig_resolve = query_helpers.resolve_module_identity
    calls = []

    def tracking_resolver(query, p2i, i2p):
        calls.append(query)
        return orig_resolve(query, p2i, i2p)

    monkeypatch.setattr(query_helpers, "resolve_module_identity", tracking_resolver)

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    # RAW ID check is called once with "pkg.mod_a", but fuzzy fallback is NOT called
    assert len(calls) == 1
    assert calls[0] == "pkg.mod_a"


def test_valid_path_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_test_state(monkeypatch)
    orig_resolve = query_helpers.resolve_module_identity
    calls = []

    def tracking_resolver(query, p2i, i2p):
        calls.append(query)
        return orig_resolve(query, p2i, i2p)

    monkeypatch.setattr(query_helpers, "resolve_module_identity", tracking_resolver)

    raw = get_artifacts_for_module(
        repo_path=str(tmp_path),
        module="pkg/mod_a.py",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    # RAW ID check is called once with "pkg/mod_a.py", but fuzzy fallback is NOT called
    assert len(calls) == 1
    assert calls[0] == "pkg/mod_a.py"


def test_original_query_preserved_and_candidate_structure(tmp_path, monkeypatch):
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
