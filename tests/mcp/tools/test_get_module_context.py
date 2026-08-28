import json
from types import SimpleNamespace
import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.mcp import query_helpers, runtime as mcp_runtime
from contextor.mcp.tools.get_module_context import get_module_context


def _setup_module_context_state(monkeypatch):
    """Sets up a minimal isolated RepositoryAnalysisState and active registry."""
    module_obj_a = SimpleNamespace(module_id="10/1", path="pkg/mod_a.py", imports=["pkg.services.auth"])
    module_obj_auth = SimpleNamespace(module_id="13/1", path="pkg/services/auth.py", imports=[])

    class MockGraph:
        hard_edges = {
            "pkg.mod_a": {"pkg.services.auth"},
            "pkg.services.auth": set(),
        }
        soft_edges = {
            "pkg.mod_a": set(),
            "pkg.services.auth": set(),
        }

    state = RepositoryAnalysisState(
        modules={
            "pkg.mod_a": module_obj_a,
            "pkg.services.auth": module_obj_auth,
        },
        artifacts={
            "pkg.mod_a": {
                "own_symbols": ["func_a"],
                "symbols": {"functions": ["func_a"]},
            },
            "pkg.services.auth": {
                "own_symbols": ["login", "token_auth"],
                "symbols": {"functions": ["login", "token_auth"]},
            },
        },
        artifact_consumption={},
        artifact_consumption_state="fresh",
        dependency_graph=MockGraph(),
        cached_analytics={
            "module_layers": {
                "pkg.mod_a": "core",
                "pkg.services.auth": "service",
            },
            "visibility": {
                "pkg.mod_a": "public",
                "pkg.services.auth": "public",
            },
            "export_degree": {
                "pkg.mod_a": 1,
                "pkg.services.auth": 2,
            },
        },
        cached_analytics_state="fresh",
        topology_analytics={
            "pagerank": {"pkg.mod_a": 0.15, "pkg.services.auth": 0.25},
            "betweenness": {"pkg.mod_a": 0.05, "pkg.services.auth": 0.1},
            "hub_scores": {"pkg.mod_a": 0.3, "pkg.services.auth": 0.1},
            "authority_scores": {"pkg.mod_a": 0.1, "pkg.services.auth": 0.4},
            "bridge_scores": {"pkg.mod_a": 0.0, "pkg.services.auth": 0.2},
            "module_risk": {"pkg.mod_a": 0.2, "pkg.services.auth": 0.3},
        },
        topology_metrics_state="fresh",
    )

    mod_path_to_id = {"pkg.mod_a": "10/1", "pkg.services.auth": "13/1"}
    mod_id_to_path = {v: k for k, v in mod_path_to_id.items()}
    art_path_to_id = {
        "pkg.mod_a::func_a": "A10/1",
        "pkg.services.auth::login": "A13/1",
        "pkg.services.auth::token_auth": "A13/2",
    }
    art_id_to_path = {v: k for k, v in art_path_to_id.items()}

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )
    return state


def test_get_module_context__legacy_dotted_module_success(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert res["metrics"]["fan_out"] == 1
    assert "dependencies_outbound_who_i_call" in res


def test_get_module_context__legacy_path_normalization_success(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg/mod_a.py",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert "metrics" in res


def test_get_module_context__module_alias_success(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"


def test_get_module_context__module_name_legacy_success(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"


def test_get_module_context__both_aliases_identical_success(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"


def test_get_module_context__alias_conflict_controlled_error(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module_name="pkg.mod_a",
        module="pkg.services.auth",
    )
    res = json.loads(raw)
    assert "error" in res
    assert "Conflicting" in res["error"]


def test_get_module_context__missing_both_controlled_error(tmp_path):
    raw = get_module_context(
        repo_path=str(tmp_path),
    )
    res = json.loads(raw)
    assert res["error"] == "Either 'module_name' or 'module' must be provided."


def test_get_module_context__exact_module_id_success(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="10/1",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"
    assert res["metrics"]["fan_out"] == 1


def test_get_module_context__exact_module_id_via_legacy_module_name(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module_name="10/1",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"


def test_get_module_context__nonexistent_module_id_never_fuzzy(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="9999/1",
    )
    assert raw == "Module '9999/1' not found in the project graph."


def test_get_module_context__valid_dotted_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_module_identity should NOT have been called for valid dotted module!")

    monkeypatch.setattr(query_helpers, "resolve_module_identity", fail_if_called)

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"


def test_get_module_context__valid_path_lookup_does_not_call_fuzzy_fallback(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("resolve_module_identity should NOT have been called for valid path lookup!")

    monkeypatch.setattr(query_helpers, "resolve_module_identity", fail_if_called)

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg/mod_a.py",
    )
    res = json.loads(raw)
    assert res["module"] == "pkg.mod_a"


def test_get_module_context__fuzzy_dotted_typo_suggestions(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
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
    assert "metrics" not in res


def test_get_module_context__fuzzy_path_typo_suggestions(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
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


def test_get_module_context__fuzzy_never_auto_resolves(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.mod_aa",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert "metrics" not in res
    assert len(res["similar_candidates"]) > 0


def test_get_module_context__fuzzy_max_five_candidates(tmp_path, monkeypatch):
    state = RepositoryAnalysisState(
        artifacts={f"pkg.module_{i}": {"symbols": {}} for i in range(10)},
        artifact_consumption={},
        artifact_consumption_state="fresh",
    )
    mod_p2i = {f"pkg.module_{i}": f"{100+i}/1" for i in range(10)}
    mod_i2p = {v: k for k, v in mod_p2i.items()}

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: (mod_p2i, mod_i2p, {}, {}))

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.modul_x",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert len(res["similar_candidates"]) <= 5


def test_get_module_context__unrelated_query_exact_legacy_fallback(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="completely_unrelated_xyz",
    )
    assert raw == "Module 'completely_unrelated_xyz' not found in the project graph."


def test_get_module_context__missing_id_with_no_engine_returns_global_error(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="9999/1",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."


def test_get_module_context__missing_id_with_resync_required_returns_global_error(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=SimpleNamespace(resync_required=True)),
    )

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="9999/1",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."


def test_get_module_context__existing_id_with_no_engine_returns_global_error(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="10/1",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."


def test_get_module_context__exact_module_id_currentness_fail_closed(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    monkeypatch.setattr(
        query_helpers,
        "module_truth_unavailable",
        lambda _state, mod: {"status": "stale", "module": mod} if mod == "pkg.mod_a" else None,
    )

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="10/1",
    )
    res = json.loads(raw)
    assert res["status"] == "stale"
    assert res["module"] == "pkg.mod_a"


def test_get_module_context__exact_module_id_respects_presentation_controls(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="10/1",
        compact=False,
        max_items=1,
        fields=["module", "metrics"],
    )
    res = json.loads(raw)
    assert set(res.keys()) == {"module", "metrics"}
    assert res["module"] == "pkg.mod_a"


def test_get_module_context__exact_id_downstream_equivalence(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw_dotted = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
        compact=True,
        max_items=10,
    )
    raw_id = get_module_context(
        repo_path=str(tmp_path),
        module="10/1",
        compact=True,
        max_items=10,
    )
    res_dotted = json.loads(raw_dotted)
    res_id = json.loads(raw_id)
    assert res_dotted == res_id


def test_get_module_context__artifact_input_redirect_preserved(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.services.auth::login",
    )
    res = json.loads(raw)
    assert res["resolved_as"] == "artifact"
    assert res["artifact"] == "pkg.services.auth::login"
    assert res["definer_module"] == "pkg.services.auth"
    assert res["suggested_next_tool"] == "get_artifact_blast_radius"
    assert "similar_candidates" not in res


def test_get_module_context__artifact_redirect_precedes_missing_engine(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.services.auth::login",
    )
    res = json.loads(raw)
    assert res["resolved_as"] == "artifact"
    assert res["artifact"] == "pkg.services.auth::login"
    assert res["definer_module"] == "pkg.services.auth"
    assert res["suggested_next_tool"] == "get_artifact_blast_radius"


def test_get_module_context__artifact_redirect_precedes_resync_required(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=SimpleNamespace(resync_required=True)),
    )

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.services.auth::login",
    )
    res = json.loads(raw)
    assert res["resolved_as"] == "artifact"
    assert res["artifact"] == "pkg.services.auth::login"
    assert res["definer_module"] == "pkg.services.auth"
    assert res["suggested_next_tool"] == "get_artifact_blast_radius"


def test_get_module_context__text_module_no_engine_guard(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg.mod_a",
    )
    assert raw == "Error: No usable canonical LIVE state. Run analyze_project first."


def test_get_module_context__fuzzy_windows_path_typo_suggestions(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module=r"pkg\servces\auth.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == r"pkg\servces\auth.py"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["module"] == "pkg.services.auth"
    assert top["module_id"] == "13/1"
    assert top["score"] >= 0.75


def test_get_module_context__fuzzy_absolute_path_typo_suggestions(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    abs_path = str(tmp_path / "pkg" / "servces" / "auth.py")
    raw = get_module_context(
        repo_path=str(tmp_path),
        module=abs_path,
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == abs_path
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["module"] == "pkg.services.auth"
    assert top["module_id"] == "13/1"
    assert top["score"] >= 0.75


def test_get_module_context__fuzzy_init_path_typo_suggestions(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module="pkg/servces/__init__.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == "pkg/servces/__init__.py"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["module"] == "pkg.services.auth"
    assert top["module_id"] == "13/1"


def test_get_module_context__fuzzy_windows_init_path_typo_suggestions(tmp_path, monkeypatch):
    _setup_module_context_state(monkeypatch)
    raw = get_module_context(
        repo_path=str(tmp_path),
        module=r"pkg\servces\__init__.py",
    )
    res = json.loads(raw)
    assert res["status"] == "not_found"
    assert res["query"] == r"pkg\servces\__init__.py"
    assert len(res["similar_candidates"]) > 0
    top = res["similar_candidates"][0]
    assert top["module"] == "pkg.services.auth"
    assert top["module_id"] == "13/1"


def test_get_module_context_revision_scoped_query_index_rebuilds_on_revision_change(tmp_path, monkeypatch):
    state = _setup_module_context_state(monkeypatch)
    state.revision = 101
    original_read = query_helpers.read_registries
    read_calls = []

    def counted_read(root):
        read_calls.append(root)
        return original_read(root)

    monkeypatch.setattr(query_helpers, "read_registries", counted_read)
    get_module_context(str(tmp_path), module="pkg/mod_a.py")
    get_module_context(str(tmp_path), module="pkg/mod_a.py")
    assert len(read_calls) == 1

    state.revision = 102
    get_module_context(str(tmp_path), module="pkg/mod_a.py")
    assert len(read_calls) == 2


def test_get_module_context__normalize_module_path_to_dotted_unit():
    from contextor.core.report_query import normalize_module_path_to_dotted

    assert normalize_module_path_to_dotted("pkg/services/auth.py") == "pkg.services.auth"
    assert normalize_module_path_to_dotted(r"pkg\services\auth.py") == "pkg.services.auth"
    assert normalize_module_path_to_dotted("pkg/services/__init__.py") == "pkg.services"
    assert normalize_module_path_to_dotted(r"pkg\services\__init__.py") == "pkg.services"
    assert normalize_module_path_to_dotted("pkg.services.auth") == "pkg.services.auth"
    assert normalize_module_path_to_dotted("./pkg/services/auth.py") == "pkg.services.auth"
