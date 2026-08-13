"""Tests for layer_slicer — _compute_layer_health and slice_report_for_layer.

Coverage based on Contextor analysis (module_id 15/1):
- Public API: slice_report_for_layer
- Key internal: _compute_layer_health

Areas:
  _compute_layer_health:
    - filtered vs full computation trigger (density_ratio, HUB hotspot)
    - cycle attribution (ALL modules in layer)
    - collision filtering (is_identical flag, node membership)
    - skipped file matching (path normalisation, __init__, extensions)
    - debt / status / action_items plumbing
    - report_header propagation
    - layer_skipped included only when non-empty

  slice_report_for_layer:
    - layer_prefix derivation (root==layer, relative, cross-drive fallback)
    - is_in_layer: exact match, prefix+dot, excluded sibling prefix
    - edge partitioning: internal / inbound / outbound
    - soft edge isolation
    - per_module degree calculation (internal + boundary)
    - artifact filtering by definer_module
    - shared_artifact_keys & _usage_sidecar filtered to layer
    - index_dict=None raises ValueError
    - return shape: all expected keys present
"""

import os
import pytest
from pathlib import Path
from types import SimpleNamespace

from contextor.core.reporting_engine.dictionary import IndexDictionary
from contextor.core.reporting_engine.layer_slicer import (
    _compute_layer_health,
    slice_report_for_layer,
)
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _registry(tmp_path, modules=()):
    reg = PersistentIdentityRegistry(str(tmp_path))
    with reg.transaction():
        for m in modules:
            reg.get_module_id(m)
    return reg


def _index(tmp_path, modules=()):
    return IndexDictionary(_registry(tmp_path, modules))


def _skipped(path, reason="parse_error"):
    return SimpleNamespace(path=path, reason=reason)


def _collision(nodes, is_identical=False):
    return SimpleNamespace(nodes=nodes, is_identical=is_identical)


# ---------------------------------------------------------------------------
# _compute_layer_health — filtered mode
# ---------------------------------------------------------------------------

class TestComputeLayerHealthFiltered:

    def test_empty_layer_returns_filtered_mode(self):
        result = _compute_layer_health(
            layer_set=set(),
            layer_modules=[],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=[],
            global_summary={},
        )
        assert result["computation_mode"] == "filtered"
        assert result["layer_cycles_count"] == 0

    def test_cycles_attributed_only_when_all_modules_in_layer(self):
        layer_set = {"pkg.a", "pkg.b"}
        global_cycles = [
            ["pkg.a", "pkg.b"],        # fully inside → included
            ["pkg.a", "pkg.external"],  # partially outside → excluded
        ]
        result = _compute_layer_health(
            layer_set=layer_set,
            layer_modules=list(layer_set),
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=global_cycles,
            global_collisions=[],
            global_skipped_files=[],
            global_summary={},
        )
        assert result["layer_cycles_count"] == 1
        assert ["pkg.a", "pkg.b"] in result["cycles"]

    def test_identical_collision_excluded(self):
        layer_set = {"pkg.a", "pkg.b"}
        collisions = [
            _collision(["pkg.a", "pkg.b"], is_identical=True),   # filtered out
            _collision(["pkg.a", "pkg.b"], is_identical=False),  # kept
        ]
        result = _compute_layer_health(
            layer_set=layer_set,
            layer_modules=list(layer_set),
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=[],
            global_collisions=collisions,
            global_skipped_files=[],
            global_summary={},
        )
        assert result["name_collisions_count"] == 1

    def test_collision_with_external_node_excluded(self):
        layer_set = {"pkg.a"}
        collisions = [
            _collision(["pkg.a", "pkg.external"]),  # external node → excluded
        ]
        result = _compute_layer_health(
            layer_set=layer_set,
            layer_modules=["pkg.a"],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=[],
            global_collisions=collisions,
            global_skipped_files=[],
            global_summary={},
        )
        assert result["name_collisions_count"] == 0

    def test_hotspot_filtered_to_layer(self):
        global_hotspots = [
            {"module": "pkg.a", "score": 0.5, "type": "HOTSPOT"},
            {"module": "pkg.outside", "score": 0.9, "type": "HOTSPOT"},
        ]
        result = _compute_layer_health(
            layer_set={"pkg.a"},
            layer_modules=["pkg.a"],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=global_hotspots,
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=[],
            global_summary={},
        )
        # Only pkg.a's hotspot should appear
        hotspot_modules = [h["module"] for h in result["hotspots"]]
        assert "pkg.outside" not in hotspot_modules

    def test_report_header_propagated(self):
        header = {"branch": "main", "commit_sha": "abc123"}
        result = _compute_layer_health(
            layer_set=set(),
            layer_modules=[],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=[],
            global_summary={},
            report_header=header,
        )
        assert result["report_header"]["branch"] == "main"
        assert result["report_header"]["data_source"] == "layer"

    def test_no_report_header_key_when_none(self):
        result = _compute_layer_health(
            layer_set=set(),
            layer_modules=[],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=[],
            global_summary={},
        )
        assert "report_header" not in result

    def test_skipped_files_matched_by_dotted_path(self):
        layer_set = {"pkg.core.api"}
        skipped = [
            _skipped("pkg/core/api.py"),          # matches → included
            _skipped("pkg/other/module.py"),       # outside → excluded
            _skipped("pkg/core/api/__init__.py"),  # __init__ stripped → included
        ]
        result = _compute_layer_health(
            layer_set=layer_set,
            layer_modules=["pkg.core.api"],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=skipped,
            global_summary={},
        )
        assert "skipped_files" in result
        paths = [s["path"] for s in result["skipped_files"]]
        assert "pkg/core/api.py" in paths
        assert "pkg/core/api/__init__.py" in paths
        assert "pkg/other/module.py" not in paths

    def test_no_skipped_files_key_when_empty(self):
        result = _compute_layer_health(
            layer_set={"pkg.a"},
            layer_modules=["pkg.a"],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=[],
            global_summary={},
        )
        assert "skipped_files" not in result


# ---------------------------------------------------------------------------
# _compute_layer_health — full computation trigger
# ---------------------------------------------------------------------------

class TestComputeLayerHealthFullTrigger:

    def _health_with_density(self, layer_edge_count, layer_module_count, global_density):
        modules = [f"m.{i}" for i in range(layer_module_count)]
        # Build a chain so edge count matches
        hard = {}
        edges_added = 0
        for i, src in enumerate(modules):
            hard[src] = []
            for tgt in modules[i + 1:]:
                if edges_added >= layer_edge_count:
                    break
                hard[src].append(tgt)
                edges_added += 1
            if edges_added >= layer_edge_count:
                break
        return _compute_layer_health(
            layer_set=set(modules),
            layer_modules=modules,
            internal_hard=hard,
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=[],
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=[],
            global_summary={"metrics": {"density_hard": global_density}},
        )

    def test_high_density_ratio_triggers_full_mode(self):
        # 4 modules, 6 edges → density = 6/(4*3) = 0.5; global = 0.1 → ratio = 5.0 > 3.0
        result = self._health_with_density(
            layer_edge_count=6, layer_module_count=4, global_density=0.1
        )
        assert result["computation_mode"] == "full"
        assert "full_computation_triggered_by" in result
        assert any("density_ratio" in r for r in result["full_computation_triggered_by"])

    def test_low_density_ratio_stays_filtered(self):
        # 4 modules, 3 edges → density = 3/12 = 0.25; global = 0.5 → ratio = 0.5 ≤ 3.0
        result = self._health_with_density(
            layer_edge_count=3, layer_module_count=4, global_density=0.5
        )
        assert result["computation_mode"] == "filtered"

    def test_hub_hotspot_above_threshold_triggers_full(self):
        layer_set = {"pkg.hub"}
        hotspots = [{"module": "pkg.hub", "score": 0.9, "type": "HUB"}]
        result = _compute_layer_health(
            layer_set=layer_set,
            layer_modules=["pkg.hub"],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=hotspots,
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=[],
            global_summary={"metrics": {"density_hard": 0.5}},
        )
        assert result["computation_mode"] == "full"
        assert any("HUB" in r for r in result["full_computation_triggered_by"])

    def test_hub_below_threshold_does_not_trigger(self):
        layer_set = {"pkg.hub"}
        hotspots = [{"module": "pkg.hub", "score": 0.8, "type": "HUB"}]
        result = _compute_layer_health(
            layer_set=layer_set,
            layer_modules=["pkg.hub"],
            internal_hard={},
            internal_soft={},
            inbound_hard=[],
            outbound_hard=[],
            global_hotspots=hotspots,
            global_cycles=[],
            global_collisions=[],
            global_skipped_files=[],
            global_summary={"metrics": {"density_hard": 0.5}},
        )
        assert result["computation_mode"] == "filtered"


# ---------------------------------------------------------------------------
# slice_report_for_layer — edge partitioning and layer membership
# ---------------------------------------------------------------------------

class TestSliceReportForLayer:

    def _slice(self, tmp_path, layer_subdir, hard_edges, soft_edges=None, artifacts=None):
        layer_path = str(tmp_path / layer_subdir)
        os.makedirs(layer_path, exist_ok=True)
        registry = _registry(tmp_path, list(hard_edges.keys()))
        idx = IndexDictionary(registry)
        return slice_report_for_layer(
            layer_path=layer_path,
            root_path=str(tmp_path),
            global_metrics={"nodes": len(hard_edges), "density_hard": 0.1},
            global_structure={
                "hard_edges": hard_edges,
                "soft_edges": soft_edges or {},
            },
            global_artifacts=artifacts or {"artifacts": {}, "shared_artifact_keys": [], "_usage_sidecar": {}},
            global_compact_artifacts={},
            global_summary={},
            index_dict=idx,
        )

    def test_return_shape_has_all_expected_keys(self, tmp_path):
        result = self._slice(tmp_path, "pkg", {"pkg.a": []})
        assert set(result.keys()) >= {
            "summary", "structure", "structure_raw", "metrics", "artifacts",
            "artifacts_compact", "_index_dict",
        }

    def test_internal_edge_stays_internal(self, tmp_path):
        result = self._slice(
            tmp_path, "pkg",
            {"pkg.a": ["pkg.b"], "pkg.b": []}
        )
        assert "pkg.a" in result["structure_raw"]["hard_edges"]
        assert "pkg.b" in result["structure_raw"]["hard_edges"]["pkg.a"]

    def test_outbound_edge_detected(self, tmp_path):
        result = self._slice(
            tmp_path, "pkg",
            {"pkg.a": ["external.lib"], "external.lib": []}
        )
        outbound = result["summary"]["boundary"]["outbound_hard"]
        assert any(e["source"] == "pkg.a" and e["target"] == "external.lib" for e in outbound)

    def test_inbound_edge_detected(self, tmp_path):
        result = self._slice(
            tmp_path, "pkg",
            {"external.caller": ["pkg.a"], "pkg.a": []}
        )
        inbound = result["summary"]["boundary"]["inbound_hard"]
        assert any(e["source"] == "external.caller" and e["target"] == "pkg.a" for e in inbound)

    def test_soft_edge_only_included_if_internal(self, tmp_path):
        result = self._slice(
            tmp_path, "pkg",
            hard_edges={"pkg.a": [], "pkg.b": []},
            soft_edges={"pkg.a": ["pkg.b"], "pkg.a2": ["external.x"]},
        )
        assert "pkg.a" in result["structure_raw"]["soft_edges"]
        # external soft edge not in internal_soft
        assert "pkg.a2" not in result["structure_raw"].get("soft_edges", {})

    def test_sibling_prefix_not_confused(self, tmp_path):
        # 'pkg.core2' must NOT be included when layer is 'pkg/core'
        result = self._slice(
            tmp_path, "pkg/core",
            {"pkg.core.api": ["pkg.core2.other"], "pkg.core2.other": []}
        )
        layer_modules = result["summary"]["layer_modules"]
        assert "pkg.core.api" in layer_modules
        assert "pkg.core2.other" not in layer_modules

    def test_per_module_degree_counts_boundary(self, tmp_path):
        # pkg.a → external (outbound), external → pkg.b (inbound for pkg.b)
        result = self._slice(
            tmp_path, "pkg",
            {"pkg.a": ["external.x"], "external.x": ["pkg.b"], "pkg.b": []}
        )
        metrics = result["metrics"]["per_module"]
        assert metrics["pkg.a"]["out_degree"] >= 1   # outbound boundary
        assert metrics["pkg.b"]["in_degree"] >= 1    # inbound boundary

    def test_artifact_filtered_to_layer(self, tmp_path):
        artifacts = {
            "artifacts": {
                "pkg.core.api::Engine": {"definer_module": "pkg.core.api", "kind": "class", "consumers": []},
                "external.lib::Other": {"definer_module": "external.lib", "kind": "class", "consumers": []},
            },
            "shared_artifact_keys": [],
            "_usage_sidecar": {},
        }
        result = self._slice(tmp_path, "pkg/core", {"pkg.core.api": []}, artifacts=artifacts)
        layer_artifacts = result["artifacts"]["artifacts"]
        assert "pkg.core.api::Engine" in layer_artifacts
        assert "external.lib::Other" not in layer_artifacts

    def test_shared_artifact_keys_filtered(self, tmp_path):
        module = "pkg.layer.mod"
        artifacts = {
            "artifacts": {
                f"{module}::Cls": {"definer_module": module, "kind": "class", "consumers": []},
                "ext::Cls2": {"definer_module": "ext", "kind": "class", "consumers": []},
            },
            "shared_artifact_keys": [f"{module}::Cls", "ext::Cls2"],
            "_usage_sidecar": {f"{module}::Cls": {"api_imports": [module]}},
        }
        registry = _registry(tmp_path, [module])
        with registry.transaction():
            registry.get_artifact_id(f"{module}::Cls")
        idx = IndexDictionary(registry)
        result = slice_report_for_layer(
            layer_path=str(tmp_path / "pkg" / "layer"),
            root_path=str(tmp_path),
            global_metrics={"nodes": 1, "density_hard": 0.0},
            global_structure={"hard_edges": {module: []}, "soft_edges": {}},
            global_artifacts=artifacts,
            global_compact_artifacts={},
            global_summary={},
            index_dict=idx,
        )
        assert result["artifacts"]["shared_artifact_count"] == 1
        assert f"{module}::Cls" in result["artifacts"]["_usage_sidecar"]
        assert "ext::Cls2" not in result["artifacts"]["_usage_sidecar"]

    def test_missing_index_dict_raises(self, tmp_path):
        with pytest.raises(ValueError, match="index_dict"):
            slice_report_for_layer(
                layer_path=str(tmp_path / "pkg"),
                root_path=str(tmp_path),
                global_metrics={},
                global_structure={"hard_edges": {}, "soft_edges": {}},
                global_artifacts={"artifacts": {}, "shared_artifact_keys": [], "_usage_sidecar": {}},
                global_compact_artifacts={},
                global_summary={},
                index_dict=None,
            )

    def test_root_equals_layer_includes_all(self, tmp_path):
        # When layer_path == root_path, layer_prefix="" → all modules included
        registry = _registry(tmp_path, ["mod.a", "mod.b"])
        idx = IndexDictionary(registry)
        result = slice_report_for_layer(
            layer_path=str(tmp_path),
            root_path=str(tmp_path),
            global_metrics={"nodes": 2, "density_hard": 0.1},
            global_structure={"hard_edges": {"mod.a": ["mod.b"], "mod.b": []}, "soft_edges": {}},
            global_artifacts={"artifacts": {}, "shared_artifact_keys": [], "_usage_sidecar": {}},
            global_compact_artifacts={},
            global_summary={},
            index_dict=idx,
        )
        assert "mod.a" in result["summary"]["layer_modules"]
        assert "mod.b" in result["summary"]["layer_modules"]
        # No boundary edges when everything is internal
        assert result["summary"]["boundary"]["inbound_hard"] == []
        assert result["summary"]["boundary"]["outbound_hard"] == []
