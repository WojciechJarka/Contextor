# -*- coding: utf-8 -*-
"""
repo_guardian/cli.py

Warstwa CLI:
- buduje model projektu
- generuje graf zależności
- wykorzystuje incremental cache
- waliduje architekturę
- zapisuje raport JSON
"""

import sys
import os

from repo_guardian.core.indexer import build_index
from repo_guardian.core.graph import build_graph
from repo_guardian.core.incremental import get_cached_graph
from repo_guardian.core.validator import validate
from repo_guardian.core.reporting import (
    generate_summary_report,
    generate_structure_report,
    save_json
)
from repo_guardian.core.artifact_usage_report import generate_artifact_usage_report
from repo_guardian.core.metrics import compute_graph_metrics
from repo_guardian.core.cycles import detect_cycles
from repo_guardian.core.debt import compute_debt

def main(root_path: str = ".") -> int:
    modules = build_index(root_path)

    graph, cache_hit = get_cached_graph(
        modules,
        build_graph
    )

    if not cache_hit:
        print("[INFO] Cache miss, rebuilding graph...")

    errors = validate(modules, graph)

    # Pobranie nazwy repo dla plików
    repo_name = os.path.basename(os.path.abspath(root_path))
    
    # 1. Summary
    metrics = compute_graph_metrics(graph.hard_edges, graph.soft_edges)
    cycles = detect_cycles(graph.hard_edges)
    debt = compute_debt(graph.hard_edges, graph.soft_edges, cycles, metrics)
    
    summary = generate_summary_report(graph, metrics, cycles, debt)
    save_json(summary, f"output/{repo_name}_summary.json")

    # 2. Structure
    structure = generate_structure_report(graph)
    save_json(structure, f"output/{repo_name}_structure.json")

    # 3. Artifacts
    artifact_report = generate_artifact_usage_report(modules, root_path=root_path, runtime={"cache_hit": cache_hit})
    save_json(artifact_report, f"output/{repo_name}_artifacts.json")
    
    for e in errors:
        print(f"[{e.kind}] {e.message}")

    return 0 if not errors else 1


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(path))
