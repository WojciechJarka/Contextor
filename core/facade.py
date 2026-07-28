# -*- coding: utf-8 -*-
"""
repo_guardian/core/facade.py

Orchestrator for the Repo Guardian analysis pipeline.
Exposes high-level operations for the presentation layer (GUI/CLI)
so they don't have to couple with internal analyzers.
"""

from pathlib import Path

from repo_guardian.core.indexer import build_index
from repo_guardian.core.graph import build_graph
from repo_guardian.core.incremental import get_cached_graph
from repo_guardian.core.validator import validate
from repo_guardian.core.validator.collisions import validate_name_collisions

from repo_guardian.core.metrics import compute_graph_metrics
from repo_guardian.core.cycles import detect_cycles
from repo_guardian.core.hotspots import detect_hotspots
from repo_guardian.core.debt import compute_debt

from repo_guardian.core.reporting import (
    generate_report,
    save_all_reports,
    generate_summary_report,
    generate_structure_report,
    generate_artifact_usage_report,
    compact_artifact_report,
    slice_report_for_layer,
    save_layer_reports,
)

from repo_guardian.core.reporting_single_file import (
    generate_single_file_report,
    save_single_file_report,
)

from repo_guardian.core.single_file_analysis import collect_all_contexts

class GuardianFacade:

    @staticmethod
    def analyze_project(path: str, log=None) -> list:
        """Analyzes full project and saves reports. Returns validation errors."""
        if log: log("Rozpoczynanie indeksowania katalogu...")
        modules = build_index(path)

        if log: log(f"Znaleziono {len(modules)} modułów. Pobieranie grafu...")
        graph, cache_hit = get_cached_graph(modules, build_graph)

        if log: log(f"Walidacja grafu (cache_hit={cache_hit})...")
        errors = validate(modules, graph)

        repo_name = Path(path).name

        if log: log("Obliczanie metryk, wykrywanie cykli i długu technicznego...")
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

        if log: log(f"Przetwarzanie warstwy '{layer_name}' w projekcie '{repo_name}'...")
        modules = build_index(str(root_resolved))
        graph, cache_hit = get_cached_graph(modules, build_graph)

        if log: log("Obliczanie metryk i kolizji dla pełnego projektu...")
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

        runtime = {"cache_hit": cache_hit}

        if log: log("Przygotowywanie struktur danych do 'slicingu'...")
        hotspots = detect_hotspots(graph.hard_edges)
        global_summary = generate_summary_report(
            metrics, cycles, debt,
            collisions=all_collisions,
            hotspots=hotspots,
        )
        global_structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
        global_artifacts = generate_artifact_usage_report(modules, str(root_resolved), runtime)
        global_compact_artifacts = compact_artifact_report(global_artifacts)

        if log: log(f"Slicing raportów dla warstwy: {layer_name}...")
        layer_sliced_reports = slice_report_for_layer(
            layer_path=str(layer_resolved),
            root_path=str(root_resolved),
            global_metrics=metrics,
            global_structure=global_structure,
            global_summary=global_summary,
            global_artifacts=global_artifacts,
            global_compact_artifacts=global_compact_artifacts
        )

        if log: log(f"Zapisywanie 5 raportów warstwy dla '{layer_name}'...")
        save_layer_reports(
            repo_name=repo_name,
            layer_name=layer_name,
            layer_reports=layer_sliced_reports,
            log=log
        )

        if log: log(f"Zakończono! Zapisano pakiet raportów: output/{repo_name}_{layer_name}_*.json")
        return f"output/{repo_name}_{layer_name}_*.json"

    @staticmethod
    def analyze_single_file(file_path: str, repo_root: str, log=None) -> str:
        """Analyzes a single file within the context of a project. Returns report output path."""
        file = Path(file_path)
        if log: log(f"Analiza pojedynczego pliku: {file.name}")

        if log: log("Indeksowanie i budowanie grafu projektu...")
        modules = build_index(repo_root)
        graph, cache_hit = get_cached_graph(modules, build_graph)

        if log: log("Generowanie globalnego raportu (hotspots)...")
        global_report = generate_report(
            graph,
            modules=modules,
            runtime={"cache_hit": cache_hit}
        )

        if log: log("Pobieranie głębokiego kontekstu dla pliku...")
        ctx = collect_all_contexts(
            file_path,
            modules,
            graph,
            global_report=global_report,
            root_path=repo_root
        )

        if log: log("Tworzenie raportu dla pliku...")
        report = generate_single_file_report(ctx, len(modules))

        output = f"output/single_{file.stem}.json"
        save_single_file_report(report, output)

        if log: log("Raport pojedynczego pliku zapisany pomyślnie.")
        return output
