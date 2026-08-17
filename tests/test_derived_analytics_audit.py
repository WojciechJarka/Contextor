"""
tests/test_derived_analytics_audit.py

Stage 3D.1 — Derived Analytics Dependency Audit & Refresh Classification Tests.
Proves that graph-only and cached-facts analytics run in RAM without source rereads.
"""

from unittest.mock import patch
from pathlib import Path
import pytest

from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.graph.cycles import detect_cycles
from contextor.core.hotspots.engine import detect_hotspots
from contextor.core.reporting_engine.graph_analytics import (
    _compute_pagerank,
    _compute_betweenness,
    _compute_hub_authority,
    _compute_bridge_score,
    _classify_layer,
    _classify_visibility,
    _compute_export_degrees,
    build_module_dependency_matrix,
)
from contextor.core.validator.layers import validate_layer_rules
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module


def test_graph_only_analytics_pure_ram_no_disk_reads():
    """Prove that graph-only analytics run with filesystem reads blocked."""
    hard_edges = {
        "pkg.a": {"pkg.b", "pkg.c"},
        "pkg.b": {"pkg.c"},
        "pkg.c": {"pkg.a"},  # cycle
        "pkg.d": set(),
    }
    soft_edges = {"pkg.a": {"pkg.d"}}

    # Block disk reads of source code
    with patch("pathlib.Path.read_text", side_effect=OSError("Disk read blocked")), \
         patch("pathlib.Path.read_bytes", side_effect=OSError("Disk read blocked")), \
         patch("builtins.open", side_effect=OSError("Disk open blocked")):

        # 1. Macro metrics
        macro = compute_graph_metrics(hard_edges, soft_edges)
        assert macro["nodes"] == 4
        assert macro["edges_hard"] == 4

        # 2. PageRank
        pr = _compute_pagerank(hard_edges)
        assert len(pr) == 4
        assert max(pr.values()) == 1.0

        # 3. Betweenness
        bw = _compute_betweenness(hard_edges)
        assert len(bw) == 4

        # 4. HITS
        hub, auth = _compute_hub_authority(hard_edges)
        assert len(hub) == 4
        assert len(auth) == 4

        # 5. Bridge Score
        br = _compute_bridge_score(hard_edges, bw)
        assert len(br) == 4

        # 6. Cycles
        cycles = detect_cycles(hard_edges)
        assert len(cycles) >= 1

        # 7. Hotspots
        hotspots = detect_hotspots(hard_edges)
        assert isinstance(hotspots, list)



def test_cached_facts_analytics_pure_ram_no_disk_reads():
    """Prove that cached-facts analytics run with filesystem reads blocked."""
    modules = {
        "contextor.core.analysis.engine": Module(
            module_id="contextor.core.analysis.engine",
            path="contextor/core/analysis/engine.py",
            absolute_path="/tmp/engine.py",
            imports=[],
        ),
        "contextor.cli.main": Module(
            module_id="contextor.cli.main",
            path="contextor/cli/main.py",
            absolute_path="/tmp/main.py",
            imports=[],
        ),
    }
    graph = ProjectGraph(
        hard_edges={"contextor.cli.main": {"contextor.core.analysis.engine"}},
        soft_edges={},
    )
    artifact_data = {
        "artifacts": {
            "contextor.core.analysis.engine::run": {
                "definer_module": "contextor.core.analysis.engine",
                "consumers": ["contextor.cli.main"],
                "kind": "function",
            }
        }
    }

    with patch("pathlib.Path.read_text", side_effect=AssertionError("Disk read blocked")), \
         patch("pathlib.Path.read_bytes", side_effect=AssertionError("Disk read blocked")), \
         patch("builtins.open", side_effect=AssertionError("Disk open blocked")):

        # 1. Layer classification
        assert _classify_layer("contextor.core.analysis.engine") == "runtime"
        assert _classify_layer("contextor.cli.main") == "cli"

        # 2. Visibility
        vis = _classify_visibility(
            "contextor.core.analysis.engine",
            ["contextor.cli.main"],
            "runtime",
        )
        assert vis == "public"  # consumed from cli layer outside runtime

        # 3. Export degree
        exp = _compute_export_degrees(artifact_data)
        assert exp.get("contextor.core.analysis.engine") == 1

        # 4. Module dependency matrix
        mat = build_module_dependency_matrix(artifact_data, graph.hard_edges)
        assert "contextor.cli.main" in mat
        assert "contextor.core.analysis.engine" in mat["contextor.cli.main"]

        # 5. Layer validation rules
        errors = validate_layer_rules(modules, graph)
        assert isinstance(errors, list)


def test_body_only_vs_topology_change_analytics_invariance():
    """Prove that body-only change preserves graph topology analytics without recomputation."""
    graph1_hard = {"a": {"b"}, "b": set()}
    graph2_hard_body_only = {"a": {"b"}, "b": set()}  # unchanged topology
    graph3_hard_import_change = {"a": {"b", "c"}, "b": set(), "c": set()}  # changed topology

    pr1 = _compute_pagerank(graph1_hard)
    pr2 = _compute_pagerank(graph2_hard_body_only)
    pr3 = _compute_pagerank(graph3_hard_import_change)

    assert pr1 == pr2
    assert pr1 != pr3
