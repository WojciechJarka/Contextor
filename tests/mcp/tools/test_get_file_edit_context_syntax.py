import json
from types import SimpleNamespace

import pytest

from contextor.core.report_query import IndexCatalog
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools.get_file_edit_context import get_file_edit_context


class _Graph:
    hard_edges = {}
    soft_edges = {}


def _state(*, family_state="fresh", fact=None, stale=False):
    return SimpleNamespace(
        resync_required=False,
        modules={"pkg.module": SimpleNamespace(path="pkg/module.py")},
        artifacts={"pkg.module": {"symbols": {"functions": [], "classes": [], "methods": [], "globals": []}}},
        dependency_graph=_Graph(),
        metrics={},
        cached_analytics={},
        cached_analytics_state="deferred",
        topology_analytics={},
        topology_metrics_state="deferred",
        syntax_diagnostics_state=family_state,
        syntax_diagnostics_by_path={"pkg/module.py": fact} if fact is not None else {},
        module_parse_freshness={"pkg.module": {"state": "stale"}} if stale else {},
    )


@pytest.fixture
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: ({"pkg.module": "1/1"}, {"1/1": "pkg.module"}, {}, {}),
    )
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda _root: IndexCatalog(
            modules={"1/1": "pkg.module"},
            artifacts={},
            module_paths={"pkg.module": "pkg/module.py"},
        ),
    )
    monkeypatch.setattr(
        "contextor.core.report_query.resolve_index_query",
        lambda _query, _catalog, repo_root=None: {
            "matches": [{"kind": "module", "name": "pkg.module", "id": "1/1"}]
        },
    )
    monkeypatch.setattr(query_helpers, "build_state_freshness", lambda *args, **kwargs: {"workspace_sync": "verified"})
    harness = SimpleNamespace(root=tmp_path, state=None)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=harness.state))
    return harness


def _install_state(monkeypatch, harness, state):
    harness.state = state
    monkeypatch.setattr(query_helpers, "module_truth_unavailable", lambda _state, _module: (
        {"status": "stale", "available": False, "module": "pkg.module"}
        if state.module_parse_freshness else None
    ))


def test_valid_canonical_fact_is_projected_without_query_parse_or_source_read(monkeypatch, harness):
    state = _state(fact={"status": "checked_and_none", "errors": []})
    _install_state(monkeypatch, harness, state)
    with monkeypatch.context() as blocker:
        blocker.setattr("contextor.core.source.ast.parse", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("query must not parse")))
        blocker.setattr("pathlib.Path.read_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("query must not read source")))
        result = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py", fields=["syntax_diagnostics"]))

    assert result["syntax_diagnostics"] == {
        "status": "checked_and_none",
        "availability": "fresh",
        "materialized": True,
        "source_path": "pkg/module.py",
        "errors": [],
        "total": 0,
        "truncated": False,
    }


def test_syntax_error_survives_structural_fail_closed_response(monkeypatch, harness):
    state = _state(
        fact={
            "status": "checked_with_errors",
            "errors": [{"message": "invalid syntax", "line_number": 3, "column_number": 7}],
        },
        stale=True,
    )
    _install_state(monkeypatch, harness, state)
    with monkeypatch.context() as blocker:
        blocker.setattr("contextor.core.source.ast.parse", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("query must not parse")))
        result = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py"))

    assert result["status"] == "stale"
    assert result["syntax_diagnostics"]["status"] == "checked_with_errors"
    assert result["syntax_diagnostics"]["errors"] == [{
        "message": "invalid syntax", "line_number": 3, "column_number": 7
    }]
    assert result["syntax_diagnostics"]["availability"] == "fresh"


@pytest.mark.parametrize("family_state", ["not_materialized", "deferred"])
def test_unavailable_syntax_family_never_fabricates_empty_errors(monkeypatch, harness, family_state):
    state = _state(family_state=family_state)
    _install_state(monkeypatch, harness, state)

    result = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py"))

    assert result["syntax_diagnostics"]["status"] == "unavailable"
    assert result["syntax_diagnostics"]["availability"] == family_state
    assert result["syntax_diagnostics"]["materialized"] is False
    assert result["syntax_diagnostics"]["errors"] is None


def test_syntax_projection_obeys_compact_full_and_bounded_fields(monkeypatch, harness):
    state = _state(
        fact={
            "status": "checked_with_errors",
            "errors": [{"message": f"e{i}", "line_number": i, "column_number": 1} for i in range(5)],
        }
    )
    _install_state(monkeypatch, harness, state)

    compact = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py", compact=True))
    full = json.loads(get_file_edit_context(str(harness.root), file_path="pkg/module.py", compact=False, max_items=4))

    assert len(compact["syntax_diagnostics"]["errors"]) == 3
    assert compact["syntax_diagnostics"]["total"] == 5
    assert compact["syntax_diagnostics"]["truncated"] is True
    assert len(full["syntax_diagnostics"]["errors"]) == 4
    assert full["syntax_diagnostics"]["total"] == 5
    assert full["syntax_diagnostics"]["truncated"] is True
