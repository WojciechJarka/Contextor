from contextor.core.reporting_engine.dictionary import IndexDictionary
from contextor.core.reporting_engine.layer_slicer import _compute_layer_health, slice_report_for_layer
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def test_dense_acyclic_layer_is_not_recomputed_as_a_possible_cycle():
    modules = ["pkg.a", "pkg.b", "pkg.c", "pkg.d"]
    hard_edges = {
        "pkg.a": ["pkg.b", "pkg.c", "pkg.d"],
        "pkg.b": ["pkg.c", "pkg.d"],
        "pkg.c": ["pkg.d"],
        "pkg.d": [],
    }

    result = _compute_layer_health(
        layer_set=set(modules),
        layer_modules=modules,
        internal_hard=hard_edges,
        internal_soft={},
        inbound_hard=[],
        outbound_hard=[],
        global_cycles=[],
        global_hotspots=[],
        global_collisions=[],
        global_skipped_files=[],
        global_summary={"metrics": {"density_hard": 0.5}},
    )

    assert result["computation_mode"] == "filtered"
    assert "full_computation_triggered_by" not in result


def test_layer_artifact_report_counts_shared_keys_and_keeps_usage_sidecar(tmp_path):
    module_name = "pkg.layer.alpha"
    artifacts = {
        "artifacts": {
            f"{module_name}::Engine": {
                "definer_module": module_name,
                "kind": "class",
                "consumers": [module_name],
            }
        },
        "shared_artifact_keys": [f"{module_name}::Engine"],
        "_usage_sidecar": {f"{module_name}::Engine": {"api_imports": [module_name]}},
    }
    registry = PersistentIdentityRegistry(str(tmp_path))

    with registry.transaction():
        registry.get_module_id(module_name)
        registry.get_artifact_id(f"{module_name}::Engine")
        reports = slice_report_for_layer(
            layer_path=str(tmp_path / "pkg" / "layer"),
            root_path=str(tmp_path),
            global_metrics={"nodes": 1, "density_hard": 0.0},
            global_structure={"hard_edges": {module_name: []}, "soft_edges": {module_name: []}},
            global_artifacts=artifacts,
            global_compact_artifacts={},
            global_summary={},
            index_dict=IndexDictionary(registry),
        )

    assert reports["artifacts"]["shared_artifact_count"] == 1
    assert reports["artifacts"]["_usage_sidecar"][f"{module_name}::Engine"] == {"api_imports": [module_name]}
