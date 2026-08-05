from contextor.core.reporting_engine.generators import (
    _compute_action_items,
    _compute_layer_health,
    _sanity_check_reports,
    slice_report_for_layer,
)

def test_compute_action_items_entrypoints():
    isolated = ["cli_main", "core.engine", "tests.test_app", "main"]
    hotspots = [{"module": "core.alpha", "type": "OUTBOUND_HOTSPOT", "out_degree": 10}]
    
    items = _compute_action_items(
        cycles=[],
        real_collisions=[],
        hotspots=hotspots,
        isolated_modules=isolated,
    )
    
    joined = " ".join(items)
    assert "WARNING: Refactor 'core.alpha'" in joined
    assert "isolated CLI/entry-point module(s)" in joined
    assert "cli_main, main" in joined
    assert "isolated module(s) with no connections" in joined
    assert "core.engine, tests.test_app" in joined

def test_sanity_check_reports():
    summary = {"metrics": {"nodes": 10}}
    artifacts = {"module_count": 9, "artifact_count": 50}
    compact = {"artifact_count": 48}
    
    warnings = _sanity_check_reports(summary, artifacts, compact)
    assert len(warnings) == 2
    assert any("nodes mismatch" in w for w in warnings)
    assert any("artifact_count mismatch" in w for w in warnings)
    
    summary_ok = {"metrics": {"nodes": 10}}
    artifacts_ok = {"module_count": 10, "artifact_count": 50}
    compact_ok = {"artifact_count": 50}
    warnings_ok = _sanity_check_reports(summary_ok, artifacts_ok, compact_ok)
    assert len(warnings_ok) == 0

def test_compute_layer_health_trigger():
    layer_summary = {"status": "ok", "metrics": {"density_ratio": 5.0, "density": 0.5}}
    global_summary = {"status": "ok", "metrics": {"density": 0.1}}
    
    health = _compute_layer_health(
        layer_set={"core.a"},
        layer_modules=["core.a"],
        internal_hard={"core.a": ["core.b", "core.c", "core.d", "core.e"]},
        internal_soft={},
        inbound_hard=[],
        outbound_hard=[],
        global_hotspots=[],
        global_cycles=[],
        global_collisions=[],
        global_skipped_files=[],
        global_summary={"metrics": {"density_hard": 0.5}},
    )
    assert health["computation_mode"] == "full"

def test_compute_layer_health_filtered():
    layer_summary = {"status": "ok", "metrics": {"density_ratio": 1.5, "density": 0.15}}
    global_summary = {"status": "ok", "metrics": {"density": 0.1}}
    
    health = _compute_layer_health(
        layer_set={"core.a"},
        layer_modules=["core.a", "core.b"],
        internal_hard={"core.a": ["core.b"]},
        internal_soft={},
        inbound_hard=[],
        outbound_hard=[],
        global_hotspots=[],
        global_cycles=[],
        global_collisions=[],
        global_skipped_files=[],
        global_summary={"metrics": {"density_hard": 0.5}},
    )
    assert health["computation_mode"] == "filtered"

def test_slice_report_for_layer(sample_repo, isolated_dirs):
    from contextor.core.symbol_engine.indexer import build_index
    from contextor.core.graph.graph import build_graph
    from contextor.core.graph.metrics import compute_graph_metrics
    from contextor.core.reporting_engine.generators import generate_summary_report, generate_structure_report
    from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report
    from contextor.core.reporting_layer.artifact_usage_report_compact import compact_artifact_report
    from contextor.core.api.facade import _compute_metrics_and_debt
    
    root = str(sample_repo)
    modules = build_index(root)
    graph = build_graph(modules)
    metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(modules, graph)
    
    structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
    artifacts = generate_artifact_usage_report(modules, root, {"cache_hit": False})
    artifacts.pop("_usage_sidecar", None)
    compact = compact_artifact_report(artifacts)
    summary = generate_summary_report(metrics, [], {"score": 0}, [], [], [])
    
    layer_path = str(sample_repo / "core")
    
    sliced = slice_report_for_layer(
        layer_path=layer_path,
        root_path=root,
        global_metrics=metrics,
        global_structure=structure,
        global_summary=summary,
        global_artifacts=artifacts,
        global_compact_artifacts=compact,
        global_hotspots=[],
        global_cycles=[],
        global_collisions=[],
        global_skipped_files=[],
        report_header={"schema_version": "1.0", "data_source": "global"},
    )
    
    assert "summary" in sliced
    assert "metrics" in sliced
    assert "artifacts" in sliced
    assert "artifacts_compact" in sliced
    
    assert sliced["summary"]["layer"]["path"] == layer_path
    assert sliced["metrics"]["layer_scope"] == layer_path
    assert sliced["metrics"]["density_ratio"] > 0
    assert "core.alpha" in sliced["metrics"]["per_module"]
    assert sliced["summary"]["report_header"]["data_source"] == "layer"
