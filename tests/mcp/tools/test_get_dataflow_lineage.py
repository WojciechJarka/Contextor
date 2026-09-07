import ast
import inspect
import json
from contextlib import nullcontext
from types import SimpleNamespace

from contextor import mcp_server
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.mcp import query_helpers, runtime as mcp_runtime
from contextor.mcp.documentation import load_tool_document
from contextor.mcp.tools.get_dataflow_lineage import get_dataflow_lineage


_SYMBOLS = {
    "contextor.core.analysis.state_manager::build_canonical_artifact_consumption": "A901/1",
    "contextor.core.analysis.incremental.plan_executor::_rebuild_consumer_slice": "A902/1",
    "contextor.core.analysis.state_manager::build_syntax_diagnostics_from_index": "A903/1",
    "contextor.core.analysis.incremental.engine::IncrementalAnalysisEngine._commit_syntax_candidate": "A904/1",
    "contextor.core.reference.engine::extract_module_usage_facts": "A905/1",
    "contextor.core.reference.module_usage_reuse::build_module_usage_baseline_with_reuse": "A906/1",
    "contextor.core.analysis.incremental.preparation::prepare_source_update": "A907/1",
    "contextor.core.analysis.incremental.materialization::ensure_module_usages": "A908/1",
    "contextor.mcp.tools.get_artifact_blast_radius::get_artifact_blast_radius": "A909/1",
    "contextor.mcp.tools.get_module_blast_radius::get_module_blast_radius": "A910/1",
    "contextor.mcp.tools.get_file_edit_context::get_file_edit_context": "A911/1",
    "contextor.mcp.tools.get_symbol_call_context::get_symbol_call_context": "A912/1",
}
_MODULES = {
    name.split("::", 1)[0]: f"{index}/1"
    for index, name in enumerate(sorted(_SYMBOLS), start=100)
}


class _LiveRegistry:
    def __init__(self, artifact_path_to_id):
        self._state = {
            "module_registry": {
                "path_to_id": _MODULES,
                "id_to_path": {value: key for key, value in _MODULES.items()},
            },
            "artifact_registry": {
                "path_to_id": artifact_path_to_id,
                "id_to_path": {
                    value: key for key, value in artifact_path_to_id.items()
                },
            },
        }

    def read_transaction(self):
        return nullcontext()


def _state(*, artifact_state="fresh", syntax_state="fresh", usages=None, resync=False):
    modules = {
        "pkg.alpha": SimpleNamespace(path="pkg/alpha.py", module_id="100/1"),
        "pkg.beta": SimpleNamespace(path="pkg/beta.py", module_id="101/1"),
    }
    artifacts = {
        "pkg.alpha": {
            "own_symbols": ["alpha"],
            "symbols": {"functions": ["alpha"]},
        },
        "pkg.beta": {
            "own_symbols": ["beta"],
            "symbols": {"functions": ["beta"]},
        },
    }
    consumption = {
        "pkg.alpha::alpha": {
            "consumers": ["pkg.beta"],
            "channels": {"pkg.beta": ["direct_calls"]},
        },
        "pkg.beta::beta": {"consumers": [], "channels": {}},
    }
    default_usages = {
        module: SimpleNamespace(
            symbol_calls=("caller", "callee", 3, "direct"),
            symbol_calls_materialized=True,
            reference_evidence=("target", "direct_calls", "caller", 3),
            reference_evidence_materialized=True,
        )
        for module in modules
    }
    state = RepositoryAnalysisState(
        modules=modules,
        artifacts=artifacts,
        artifact_consumption=consumption,
        artifact_consumption_state=artifact_state,
        syntax_diagnostics_by_path={
            "pkg/alpha.py": {"status": "checked_and_none", "errors": []}
        },
        syntax_diagnostics_state=syntax_state,
        module_usages=usages if usages is not None else default_usages,
        module_parse_freshness={},
    )
    state.provenance = "live"
    state.revision = 17
    state.state_id = "state-17"
    state.resync_required = resync
    return state


def _install(monkeypatch, tmp_path, state, *, active_ids=True):
    artifact_ids = _SYMBOLS if active_ids else {}
    registry = _LiveRegistry(artifact_ids)
    engine = SimpleNamespace(
        state=state,
        registry=registry,
        provenance="live",
        revision=state.revision,
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (
            _MODULES,
            {value: key for key, value in _MODULES.items()},
            artifact_ids,
            {value: key for key, value in artifact_ids.items()},
        ),
    )
    return engine


def _load(raw):
    return json.loads(raw)


def _edge(result, edge_type, source=None, target=None):
    return [
        edge
        for edge in result["edges"]
        if edge["type"] == edge_type
        and (source is None or edge["source"] == source)
        and (target is None or edge["target"] == target)
    ]


def test_artifact_consumption_fresh_contains_both_branches_and_projections(tmp_path, monkeypatch):
    state = _state()
    _install(monkeypatch, tmp_path, state)

    result = _load(
        get_dataflow_lineage(
            str(tmp_path), "artifact_consumption", direction="both", depth=4
        )
    )

    assert result["status"] == "ok"
    assert result["owner"] == ["state:RepositoryAnalysisState.artifact_consumption"]
    assert result["freshness"]["families"]["artifact_consumption"] == "fresh"
    assert {
        "data_family:raw_artifact_consumer_facts",
        "data_family:module_usage_facts",
    } <= {node["id"] for node in result["nodes"]}
    qualified = {node.get("qualified_name") for node in result["nodes"]}
    assert "contextor.core.analysis.state_manager::build_canonical_artifact_consumption" in qualified
    assert "contextor.core.analysis.incremental.plan_executor::_rebuild_consumer_slice" in qualified
    assert _edge(result, "PERSISTS")
    assert _edge(result, "HYDRATES")
    assert {"tool:get_artifact_blast_radius", "tool:get_module_blast_radius"} <= set(
        result["public_projections"]
    )
    assert all(edge["confidence"] == "confirmed" for edge in result["edges"])
    assert not any(edge["confidence"] == "structural" for edge in result["edges"])


def test_artifact_consumption_stale_stops_downstream_and_reports_gap(tmp_path, monkeypatch):
    state = _state(artifact_state="stale")
    _install(monkeypatch, tmp_path, state)

    result = _load(get_dataflow_lineage(str(tmp_path), "artifact_consumption"))

    assert result["status"] == "stale"
    assert result["nodes"]
    assert not _edge(result, "PERSISTS")
    assert not _edge(result, "PROJECTS")
    assert any(
        gap["status"] == "stale" and gap["expected_edge"] == "CURRENT_CANONICAL_FAMILY_DATA"
        for gap in result["unresolved"]
    )
    assert not any("consumers" in node for node in result["nodes"])


def test_artifact_consumption_incomplete_is_partial_without_downstream_edges(tmp_path, monkeypatch):
    state = _state()
    state.artifact_consumption.pop("pkg.beta::beta")
    _install(monkeypatch, tmp_path, state)

    result = _load(get_dataflow_lineage(str(tmp_path), "artifact_consumption"))

    assert result["status"] == "partial"
    assert not _edge(result, "PERSISTS")
    assert not _edge(result, "PROJECTS")
    assert any(gap["status"] == "partial" for gap in result["unresolved"])


def test_syntax_diagnostics_fresh_contains_full_incremental_and_file_projection(
    tmp_path, monkeypatch
):
    state = _state()
    _install(monkeypatch, tmp_path, state)

    result = _load(get_dataflow_lineage(str(tmp_path), "syntax_diagnostics"))

    assert result["status"] == "ok"
    assert {
        "data_family:repository_index_parse_results",
        "data_family:prepared_source_update",
    } <= {node["id"] for node in result["nodes"]}
    qualified = {node.get("qualified_name") for node in result["nodes"]}
    assert "contextor.core.analysis.state_manager::build_syntax_diagnostics_from_index" in qualified
    assert "contextor.core.analysis.incremental.engine::IncrementalAnalysisEngine._commit_syntax_candidate" in qualified
    assert result["public_projections"] == ["tool:get_file_edit_context"]
    assert _edge(result, "PERSISTS") and _edge(result, "HYDRATES")


def test_syntax_diagnostics_deferred_keeps_owner_and_reports_unavailable_downstream(
    tmp_path, monkeypatch
):
    state = _state(syntax_state="deferred")
    _install(monkeypatch, tmp_path, state)

    result = _load(get_dataflow_lineage(str(tmp_path), "syntax_diagnostics"))

    assert result["status"] == "unavailable"
    assert "state:RepositoryAnalysisState.syntax_diagnostics_by_path" in {
        node["id"] for node in result["nodes"]
    }
    assert not _edge(result, "PROJECTS")
    assert any(gap["status"] == "unavailable" for gap in result["unresolved"])
    assert result["freshness"]["families"]["syntax_diagnostics"] == "unavailable"


def test_syntax_diagnostics_stale_is_not_empty_success(tmp_path, monkeypatch):
    state = _state(syntax_state="stale")
    _install(monkeypatch, tmp_path, state)

    result = _load(get_dataflow_lineage(str(tmp_path), "syntax_diagnostics"))

    assert result["status"] == "stale"
    assert not _edge(result, "PROJECTS")
    assert any(gap["status"] == "stale" for gap in result["unresolved"])


def test_symbol_calls_complete_reports_coverage_and_three_update_branches(tmp_path, monkeypatch):
    state = _state()
    _install(monkeypatch, tmp_path, state)

    result = _load(get_dataflow_lineage(str(tmp_path), "symbol_calls"))

    assert result["status"] == "ok"
    assert result["coverage"] == {
        "canonical_module_count": 2,
        "symbol_calls_materialized_count": 2,
        "reference_evidence_materialized_count": 2,
        "missing_symbol_calls_materialization_count": 0,
        "missing_reference_evidence_count": 0,
        "stale_module_count": 0,
    }
    qualified = {node.get("qualified_name") for node in result["nodes"]}
    assert "contextor.core.reference.engine::extract_module_usage_facts" in qualified
    assert "contextor.core.reference.module_usage_reuse::build_module_usage_baseline_with_reuse" in qualified
    assert "contextor.core.analysis.incremental.preparation::prepare_source_update" in qualified
    assert "contextor.core.analysis.incremental.materialization::ensure_module_usages" in qualified
    assert result["public_projections"] == ["tool:get_symbol_call_context"]
    assert _edge(result, "PERSISTS") and _edge(result, "HYDRATES")


def test_symbol_calls_partial_uses_one_aggregate_coverage_gap(tmp_path, monkeypatch):
    usages = {
        "pkg.alpha": SimpleNamespace(
            symbol_calls_materialized=True,
            reference_evidence_materialized=True,
        ),
        "pkg.beta": SimpleNamespace(
            symbol_calls_materialized=False,
            reference_evidence_materialized=False,
        ),
    }
    state = _state(usages=usages)
    _install(monkeypatch, tmp_path, state)

    result = _load(get_dataflow_lineage(str(tmp_path), "symbol_calls"))

    assert result["status"] == "partial"
    assert result["coverage"]["missing_symbol_calls_materialization_count"] == 1
    assert result["coverage"]["missing_reference_evidence_count"] == 1
    coverage_gaps = [
        gap
        for gap in result["unresolved"]
        if gap["expected_edge"] == "COMPLETE_SYMBOL_CALLS_COVERAGE"
    ]
    assert len(coverage_gaps) == 1
    assert len(result["unresolved"]) == 1


def test_resync_fails_closed_without_confirmed_downstream_data_edges(tmp_path, monkeypatch):
    state = _state(resync=True)
    _install(monkeypatch, tmp_path, state)

    result = _load(get_dataflow_lineage(str(tmp_path), "artifact_consumption"))

    assert result["status"] == "unavailable"
    assert result["freshness"]["resync_required"] is True
    assert not _edge(result, "PERSISTS")
    assert not _edge(result, "PROJECTS")
    assert all(edge["confidence"] == "confirmed" for edge in result["edges"])
    assert any(gap["status"] == "unavailable" for gap in result["unresolved"])


def test_direction_and_depth_are_relative_to_family_anchor(tmp_path, monkeypatch):
    state = _state()
    _install(monkeypatch, tmp_path, state)

    upstream = _load(
        get_dataflow_lineage(str(tmp_path), "artifact_consumption", "upstream", 1)
    )
    downstream = _load(
        get_dataflow_lineage(str(tmp_path), "artifact_consumption", "downstream", 1)
    )
    shallow = _load(
        get_dataflow_lineage(str(tmp_path), "artifact_consumption", "both", 1)
    )

    assert upstream["entry_points"] == ["family:artifact_consumption"]
    assert _edge(upstream, "PRODUCES")
    assert not _edge(upstream, "MATERIALIZES")
    assert _edge(downstream, "MATERIALIZES")
    assert not _edge(downstream, "PRODUCES")
    assert _edge(shallow, "PRODUCES") and _edge(shallow, "MATERIALIZES")
    assert all(
        edge["source"] == "family:artifact_consumption"
        or edge["target"] == "family:artifact_consumption"
        for edge in shallow["edges"]
    )


def test_output_is_deterministic_and_identity_resolution_is_dynamic(tmp_path, monkeypatch):
    state = _state()
    _install(monkeypatch, tmp_path, state)

    first = get_dataflow_lineage(str(tmp_path), "symbol_calls", depth=4)
    second = get_dataflow_lineage(str(tmp_path), "symbol_calls", depth=4)
    assert first == second
    result = _load(first)
    assert result["nodes"] == sorted(result["nodes"], key=lambda node: (node["type"], node["id"]))
    assert result["edges"] == sorted(
        result["edges"],
        key=lambda edge: (edge["source"], edge["target"], edge["type"]),
    )
    assert any(
        node.get("artifact_id") == "A905/1"
        for node in result["nodes"]
        if node.get("qualified_name") == "contextor.core.reference.engine::extract_module_usage_facts"
    )

    _install(monkeypatch, tmp_path, state, active_ids=False)
    without_ids = _load(get_dataflow_lineage(str(tmp_path), "symbol_calls", depth=4))
    extractor = next(
        node
        for node in without_ids["nodes"]
        if node.get("qualified_name") == "contextor.core.reference.engine::extract_module_usage_facts"
    )
    assert "artifact_id" not in extractor
    assert any(
        gap.get("kind") == "identity_resolution"
        and gap.get("qualified_name") == extractor["qualified_name"]
        for gap in without_ids["unresolved"]
    )


def test_query_time_does_not_parse_or_call_other_mcp_tools(tmp_path, monkeypatch):
    state = _state()
    _install(monkeypatch, tmp_path, state)
    monkeypatch.setattr(
        query_helpers,
        "build_state_freshness",
        lambda *_args, **_kwargs: {
            "canonical_state": "fresh",
            "workspace_sync": "unverified",
            "canonical_revision": 17,
            "provenance": "live",
            "families": {},
            "advisory_warning": None,
        },
    )
    monkeypatch.setattr(ast, "parse", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("AST parse")))
    monkeypatch.setattr(
        mcp_server,
        "get_module_blast_radius",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("MCP call")),
    )
    monkeypatch.setattr(
        mcp_server,
        "get_artifact_blast_radius",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("MCP call")),
    )
    monkeypatch.setattr(
        mcp_server,
        "get_symbol_call_context",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("MCP call")),
    )

    result = _load(get_dataflow_lineage(str(tmp_path), "artifact_consumption"))
    assert result["status"] == "ok"


def test_signature_docs_registration_and_public_contract_parity():
    tool = mcp_server.mcp._tool_manager._tools["get_dataflow_lineage"]
    assert set(inspect.signature(tool.fn).parameters) == {
        "repo_path",
        "family",
        "direction",
        "depth",
    }
    assert str(inspect.signature(tool.fn)) == (
        "(repo_path: str, family: str, direction: str = 'both', depth: int = 3) -> str"
    )
    assert list(mcp_server.REGISTERED_MCP_TOOL_NAMES)[-1] == "get_dataflow_lineage"
    document = load_tool_document("get_dataflow_lineage")
    assert document["tool"] == "get_dataflow_lineage"
    assert any(entry.startswith("family (string, required)") for entry in document["parameters"])
    source = inspect.getsource(get_dataflow_lineage)
    assert "ast.parse" not in source
    assert "get_module_blast_radius(" not in source
    assert "get_artifact_blast_radius(" not in source
    assert "get_symbol_call_context(" not in source
