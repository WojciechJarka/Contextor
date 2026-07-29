# -*- coding: utf-8 -*-
"""
repo_guardian/core/facade.py

Orchestrator for the Repo Guardian analysis pipeline.
Exposes high-level operations for the presentation layer (GUI/CLI)
so they don't have to couple with internal analyzers.
"""

from pathlib import Path
import json

from repo_guardian.core.symbol_engine.indexer import build_index
from repo_guardian.core.graph.graph import build_graph
from repo_guardian.core.graph.incremental import get_cached_graph
from repo_guardian.core.validator import validate
from repo_guardian.core.validator.collisions import validate_name_collisions

from repo_guardian.core.graph.metrics import compute_graph_metrics
from repo_guardian.core.graph.cycles import detect_cycles
from repo_guardian.core.hotspots import detect_hotspots
from repo_guardian.core.reporting_engine.debt import compute_debt

from repo_guardian.core.reporting_engine.engine import (
    generate_report,
    save_all_reports,
    generate_summary_report,
    generate_structure_report,
    slice_report_for_layer,
    save_layer_reports,
)
from repo_guardian.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report
from repo_guardian.core.reporting_layer.artifact_usage_report_compact import compact_artifact_report

from repo_guardian.core.reporting_layer.reporting_single_file import (
    generate_single_file_report,
    save_single_file_report,
)
from repo_guardian.core.reporting_layer.reporting_llm import generate_llm_markdown

from repo_guardian.core.single_file.single_file_analysis import collect_all_contexts


def _compute_metrics_and_debt(modules, graph):
    """
    Shared analytical pipeline extracting graph metrics and tech debt scores.
    """
    metrics = compute_graph_metrics(graph.hard_edges, graph.soft_edges)
    cycles = detect_cycles(graph.hard_edges)
    all_collisions = validate_name_collisions(modules)
    debt = compute_debt(
        graph.hard_edges,
        graph.soft_edges,
        cycles,
        metrics,
        collisions=all_collisions,
    )
    return metrics, cycles, all_collisions, debt

def _load_excludes_for_repo(repo_path: str) -> tuple[list, set]:
    """Helper to read soft excludes and auto-exclude dir names for a given repo.
    Returns (excluded_paths, extra_ignored_dirs).
    """
    repo_name = Path(repo_path).name
    safe_name = repo_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    ui_dir = Path(__file__).resolve().parent.parent.parent / "ui"
    state_file = ui_dir / f"exclude_state_{safe_name}.json"

    if not state_file.exists():
        state_file = ui_dir / "exclude_state.json"

    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            excluded = data.get("excluded", [])
            # Auto-exclude dir names stored by exclude_gui (pre-computed list)
            extra_dirs = set(data.get("auto_exclude_dirs", [
                "__pycache__", ".git", "venv", ".venv", "dist", "build",
                ".idea", ".vscode", "node_modules", "scratch",
            ]))
            return excluded, extra_dirs
        except Exception:
            pass
    # Sensible defaults when no state file exists
    default_dirs = {
        "__pycache__", ".git", "venv", ".venv", "dist", "build",
        ".idea", ".vscode", "node_modules", "scratch",
    }
    return [], default_dirs

class GuardianFacade:
    """
    Main entry point for executing static analysis workflows.
    Provides isolated static methods bridging the presentation layer (GUI/CLI)
    with the underlying graph building and heuristic evaluation logic.
    """

    @staticmethod
    def analyze_project(path: str, log=None) -> list:
        """
        Analyzes full project hierarchy, builds dependency graph, evaluates
        technical debt, detects cycles and saves all generated artifacts.
        
        Args:
            path: Absolute string path to the project root directory.
            log: Optional callback function for streaming stdout progress.
            
        Returns:
            list: List of architectural validation errors, if any.
        """
        if log: log("Starting directory indexing...")
        excludes, extra_dirs = _load_excludes_for_repo(path)
        modules = build_index(path, excludes=excludes, extra_ignored_dirs=extra_dirs)

        if log: log(f"Found {len(modules)} modules. Fetching graph...")
        graph, cache_hit = get_cached_graph(modules, build_graph)

        if log: log(f"Graph validation (cache_hit={cache_hit})...")
        errors = validate(modules, graph)

        repo_name = Path(path).name

        if log: log("Calculating metrics, detecting cycles and tech debt...")
        metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(modules, graph)

        save_all_reports(
            repo_name=repo_name,
            modules=modules,
            graph=graph,
            metrics=metrics,
            cycles=cycles,
            debt=debt,
            runtime={"cache_hit": cache_hit},
            root_path=path,
            log=log,
            collisions=all_collisions,
        )

        return errors

    @staticmethod
    def analyze_layer(root_dir: str, layer_dir: str, log=None) -> str:
        """Analyzes a specific layer. Returns output pattern."""
        root_resolved = Path(root_dir).resolve()
        layer_resolved = Path(layer_dir).resolve()
        repo_name = root_resolved.name
        layer_name = layer_resolved.name

        if log: log(f"Processing layer '{layer_name}' in project '{repo_name}'...")
        excludes, extra_dirs = _load_excludes_for_repo(str(root_resolved))
        modules = build_index(str(root_resolved), excludes=excludes, extra_ignored_dirs=extra_dirs)
        graph, cache_hit = get_cached_graph(modules, build_graph)

        if log: log("Calculating metrics and collisions for the full project...")
        metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(modules, graph)

        runtime = {"cache_hit": cache_hit}

        if log: log("Preparing data structures for slicing...")
        hotspots = detect_hotspots(graph.hard_edges)
        global_summary = generate_summary_report(
            metrics, cycles, debt,
            collisions=all_collisions,
            hotspots=hotspots,
        )
        global_structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
        global_artifacts = generate_artifact_usage_report(modules, str(root_resolved), runtime)
        global_compact_artifacts = compact_artifact_report(global_artifacts)

        if log: log(f"Slicing reports for layer: {layer_name}...")
        layer_sliced_reports = slice_report_for_layer(
            layer_path=str(layer_resolved),
            root_path=str(root_resolved),
            global_metrics=metrics,
            global_structure=global_structure,
            global_summary=global_summary,
            global_artifacts=global_artifacts,
            global_compact_artifacts=global_compact_artifacts
        )

        if log: log(f"Saving 5 layer reports for '{layer_name}'...")
        save_layer_reports(
            repo_name=repo_name,
            layer_name=layer_name,
            layer_reports=layer_sliced_reports,
            log=log
        )

        if log: log(f"Finished! Saved reports package: output/{repo_name}_{layer_name}_*.json")
        return f"output/{repo_name}_{layer_name}_*.json"

    @staticmethod
    def analyze_single_file(file_path: str, repo_root: str, log=None) -> str:
        """Analyzes a single file within the context of a project. Returns report output path."""
        file = Path(file_path)
        if log: log(f"Single file analysis: {file.name}")

        if log: log("Indexing and building project graph...")
        excludes, extra_dirs = _load_excludes_for_repo(repo_root)
        modules = build_index(repo_root, excludes=excludes, extra_ignored_dirs=extra_dirs)
        graph, cache_hit = get_cached_graph(modules, build_graph)

        if log: log("Generating global report (hotspots)...")
        global_report = generate_report(
            graph,
            modules=modules,
            runtime={"cache_hit": cache_hit}
        )

        if log: log("Fetching deep context for file...")
        ctx = collect_all_contexts(
            file_path,
            modules,
            graph,
            global_report=global_report,
            root_path=repo_root
        )

        if log: log("Creating report for file...")
            
        report = generate_single_file_report(ctx, len(modules))

        output = f"output/single_{file.stem}.json"
        save_single_file_report(report, output)

        md_output = f"output/single_{file.stem}_llm_context.md"
        generate_llm_markdown(report, md_output)

        if log: log("Single file report and MD bundle saved successfully.")
        return output
