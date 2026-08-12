"""
contextor/core/facade.py

Orchestrator for the Contextor analysis pipeline.
Exposes high-level operations for the presentation layer (GUI/CLI)
so they don't have to couple with internal analyzers.
"""

import json
import os
from pathlib import Path

from contextor.core.errors import AnalysisCancelled, checkpoint
from contextor.core.graph.cycles import detect_cycles
from contextor.core.graph.graph import build_graph
from contextor.core.graph.incremental import get_cached_graph
from contextor.core.graph.metrics import compute_graph_metrics
from contextor.core.hotspots import detect_hotspots
from contextor.core.paths import DEFAULT_IGNORED_DIRS, output_dir, repo_key, state_dir
from contextor.core.reference.engine import reset_caches
from contextor.core.reporting_engine.debt import compute_debt
from contextor.core.reporting_engine.generators import (
    generate_report,
    generate_structure_report,
    generate_summary_report,
    slice_report_for_layer,
)
from contextor.core.reporting_engine.header import build_report_header
from contextor.core.reporting_engine.pipeline import execute_global_pipeline

from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report
from contextor.core.reporting_layer.artifact_usage_report_compact import compact_artifact_report
from contextor.core.reporting_layer.reporting_llm import generate_llm_markdown
from contextor.core.reporting_layer.reporting_single_file import (
    generate_single_file_report,
    save_single_file_report,
)
from contextor.core.single_file.single_file_analysis import collect_all_contexts
from contextor.core.symbol_engine.indexer import build_index, index_repository
from contextor.core.validator import validate
from contextor.core.validator.collisions import validate_name_collisions


def _compute_metrics_and_debt(modules, graph, progress_callback=None):
    """
    Shared analytical pipeline extracting graph metrics and tech debt scores.
    """
    checkpoint(progress_callback, "Computing graph metrics...")
    metrics = compute_graph_metrics(graph.hard_edges, graph.soft_edges)

    checkpoint(progress_callback, "Detecting cycles...")
    cycles = detect_cycles(graph.hard_edges, progress_callback=progress_callback)

    checkpoint(progress_callback, "Validating collisions...")
    all_collisions = validate_name_collisions(modules)

    checkpoint(progress_callback, "Computing tech debt...")
    debt = compute_debt(
        graph.hard_edges,
        graph.soft_edges,
        cycles,
        metrics,
        collisions=all_collisions,
    )
    return metrics, cycles, all_collisions, debt


def exclude_state_file(repo_path: str) -> Path:
    """
    Location of the exclude configuration for one repository.

    Keyed by absolute path rather than folder name, so '/work/api' and
    '/private/api' no longer share one configuration. Stored under the
    user state directory, because the installation directory may be
    read-only.
    """

    return state_dir() / "excludes" / f"{repo_key(repo_path)}.json"


def _legacy_exclude_files(repo_path: str) -> list[Path]:
    """
    Pre-1.0.5 locations, still read so existing setups keep working.

    Back then the project root was the package root and state lived in
    its 'ui' directory; the package now sits one level deeper.
    """

    repo_name = Path(repo_path).name
    safe_name = repo_name.replace(" ", "_").replace("/", "_").replace("\\", "_")

    candidates = []

    for base in (
        Path(__file__).resolve().parents[2] / "ui",  # contextor/ui
        Path(__file__).resolve().parents[3] / "ui",  # pre-rebrand <root>/ui
    ):
        candidates.append(base / f"exclude_state_{safe_name}.json")
        candidates.append(base / "exclude_state.json")

    return candidates


def _load_excludes_for_repo(repo_path: str) -> tuple[list, set]:
    """Helper to read soft excludes and auto-exclude dir names for a given repo.
    Returns (excluded_paths, extra_ignored_dirs).
    """

    for state_file in [exclude_state_file(repo_path), *_legacy_exclude_files(repo_path)]:
        if not state_file.exists():
            continue

        try:
            with open(state_file, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue

        excluded = data.get("excluded", [])
        # Auto-exclude dir names stored by exclude_gui (pre-computed list)
        extra_dirs = set(data.get("auto_exclude_dirs", DEFAULT_IGNORED_DIRS))

        return excluded, extra_dirs

    # Sensible defaults when no state file exists
    return [], set(DEFAULT_IGNORED_DIRS)


def _analysis_filters(
    repo_path: str, additional_excludes: list[str] | None = None
) -> tuple[list[str], set]:
    """Combine saved GUI excludes with safe, per-analysis path exclusions.

    ``additional_excludes`` is intentionally ephemeral: MCP and other API
    callers can narrow one analysis without modifying the repository-specific
    exclude state managed by the GUI. Entries identify a repository-relative
    Python file or directory prefix. Absolute entries are accepted only when
    they resolve inside the repository.
    """

    saved_excludes, extra_dirs = _load_excludes_for_repo(repo_path)
    if not additional_excludes:
        return list(saved_excludes), extra_dirs
    if len(additional_excludes) > 500:
        raise ValueError("At most 500 per-analysis exclude paths are allowed.")

    root = Path(repo_path).expanduser().resolve()
    combined = list(saved_excludes)
    known = {str(item).replace("\\", "/").strip("/") for item in combined}

    for item in additional_excludes:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Exclude paths must be non-empty strings.")
        candidate = Path(item).expanduser()
        if candidate.is_absolute():
            try:
                candidate = candidate.resolve().relative_to(root)
            except ValueError as exc:
                raise ValueError(
                    f"Exclude path is outside the repository: {item}"
                ) from exc

        normalized = candidate.as_posix().removeprefix("./").strip("/")
        if not normalized or ".." in Path(normalized).parts:
            raise ValueError(f"Invalid repository-relative exclude path: {item}")
        if normalized not in known:
            combined.append(normalized)
            known.add(normalized)

    return combined, extra_dirs


def _log_skipped(skipped, log) -> None:
    """
    Reports files that carry a '.py' name but are not analyzable Python.
    """

    if not skipped or not log:
        return

    log(f"Skipped {len(skipped)} file(s) that are not analyzable Python:")

    for item in skipped[:10]:
        log(f"  - {item.path} ({item.reason})")

    if len(skipped) > 10:
        log(f"  … and {len(skipped) - 10} more (see the report)")


class ContextorFacade:
    """
    Main entry point for executing static analysis workflows.
    Provides isolated static methods bridging the presentation layer (GUI/CLI)
    with the underlying graph building and heuristic evaluation logic.
    """

    @staticmethod
    def analyze_project(
        path: str,
        log=None,
        progress_callback=None,
        additional_excludes: list[str] | None = None,
    ) -> list:
        """
        Analyzes full project hierarchy, builds dependency graph, evaluates
        technical debt, detects cycles and saves all generated artifacts.

        Args:
            path: Absolute string path to the project root directory.
            log: Optional callback function for streaming stdout progress.
            progress_callback: Optional callback for progress percentage (completed, total, filename).

        Returns:
            list: List of architectural validation errors, if any.
        """
        reset_caches()

        if log:
            log("Starting directory indexing...")
        excludes, extra_dirs = _analysis_filters(path, additional_excludes)
        index = index_repository(
            path,
            excludes=excludes,
            extra_ignored_dirs=extra_dirs,
            progress_callback=progress_callback,
        )
        modules = index.modules

        from contextor.core.graph.resolver import build_trie, detect_package_root
        trie = build_trie(modules.keys())
        package_root = detect_package_root(modules, trie)

        if log:
            log(f"Found {len(modules)} modules. Fetching graph...")
            _log_skipped(index.skipped, log)
        graph, cache_hit = get_cached_graph(
            modules, 
            lambda m: build_graph(m, trie=trie, package_root=package_root)
        )

        if log:
            log(f"Graph validation (cache_hit={cache_hit})...")
        errors = validate(modules, graph, progress_callback=progress_callback)

        repo_name = Path(path).name

        if log:
            log("Calculating metrics, detecting cycles and tech debt...")
        metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(
            modules, graph, progress_callback=progress_callback
        )

        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report_result = execute_global_pipeline(
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
            progress_callback=progress_callback,
            skipped_files=index.skipped,
            datestamp=datestamp,
            trie=trie,
            package_root=package_root,
        )

        if log and report_result.get("high_risk_layers"):
            high_risk_layers = ", ".join(report_result["high_risk_layers"])
            log(f"Generated additional reports for high risk layers: {high_risk_layers}")

        analysis_result = report_result.get("_analysis_result")
        
        if analysis_result:
            from contextor.core.analysis.state_manager import RepositoryAnalysisState, save_engine_state
            from contextor.core.paths import repo_cache_dir
            state = RepositoryAnalysisState(
                modules=getattr(analysis_result, "modules", {}),
                artifacts=getattr(analysis_result, "artifacts", {}),
                dependency_graph=getattr(analysis_result, "graph", None),
                trie=getattr(analysis_result, "trie", None),
                package_root=getattr(analysis_result, "package_root", ""),
                artifact_consumption={"_report": getattr(analysis_result, "compact_artifacts", {})}
            )
            save_engine_state(state, str(repo_cache_dir(path)), datestamp)

        return errors, analysis_result

    @staticmethod
    def analyze_layer(
        root_dir: str,
        layer_dir: str,
        log=None,
        progress_callback=None,
        additional_excludes: list[str] | None = None,
    ) -> str:
        """Analyzes a specific layer. Returns output pattern."""
        root_resolved = Path(root_dir).resolve()
        layer_resolved = Path(layer_dir).resolve()
        repo_name = root_resolved.name
        layer_name = layer_resolved.name

        reset_caches()

        if log:
            log(f"Processing layer '{layer_name}' in project '{repo_name}'...")
        excludes, extra_dirs = _analysis_filters(
            str(root_resolved), additional_excludes
        )
        index = index_repository(
            str(root_resolved),
            excludes=excludes,
            extra_ignored_dirs=extra_dirs,
            progress_callback=progress_callback,
        )
        modules = index.modules
        from contextor.core.graph.resolver import build_trie, detect_package_root
        trie = build_trie(modules.keys())
        package_root = detect_package_root(modules, trie)
        
        graph, cache_hit = get_cached_graph(
            modules, 
            lambda m: build_graph(m, trie=trie, package_root=package_root)
        )

        if log:
            log("Calculating metrics and collisions for the full project...")
        metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(
            modules, graph, progress_callback=progress_callback
        )

        runtime = {"cache_hit": cache_hit}

        if log:
            log("Preparing data structures for slicing...")
        hotspots = detect_hotspots(graph.hard_edges)
        global_summary = generate_summary_report(
            metrics,
            cycles,
            debt,
            collisions=all_collisions,
            hotspots=hotspots,
        )
        global_structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
        global_artifacts = generate_artifact_usage_report(
            modules, str(root_resolved), runtime, progress_callback=progress_callback
        )
        
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
        from contextor.core.reporting_engine.dictionary import IndexDictionary
        registry = PersistentIdentityRegistry(str(root_resolved))
        
        with registry.transaction():
            index_dict = IndexDictionary(registry)
            global_compact_artifacts = compact_artifact_report(global_artifacts, index_dict)

            if log:
                log(f"Slicing reports for layer: {layer_name}...")

            # Build report_header once — same header for global summary and layer reports.
            report_header = build_report_header(str(root_resolved), "global")
            
            layer_sliced_reports = slice_report_for_layer(
            layer_path=str(layer_resolved),
            root_path=str(root_resolved),
            global_metrics=metrics,
            global_structure=global_structure,
            global_summary=global_summary,
            global_artifacts=global_artifacts,
            global_compact_artifacts=global_compact_artifacts,
            global_hotspots=hotspots,
            global_cycles=cycles,
            global_collisions=all_collisions,
            global_skipped_files=getattr(index, "skipped", []),
            report_header=report_header,
            index_dict=index_dict,
        )

        if log:
            log(f"Saving 5 layer reports for '{layer_name}'...")
            
        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        from contextor.core.reporting_engine.pipeline import execute_layer_pipeline
        from contextor.core.reporting_engine.io_manager import write_layer_reports
        
        execute_layer_pipeline(repo_name, layer_name, layer_sliced_reports, log=log, datestamp=datestamp)
        write_layer_reports(
            repo_name=repo_name,
            layer_name=layer_name,
            layer_reports=layer_sliced_reports,
            datestamp=datestamp,
            log=log,
        )

        # Absolute, so what the GUI shows the user is a path that exists.
        pattern = str(output_dir() / f"{repo_name}_{layer_name}_*.json")

        if log:
            log(f"Finished! Saved reports package: {pattern}")
        return pattern

    @staticmethod
    def analyze_single_file(
        file_path: str,
        repo_root: str,
        log=None,
        progress_callback=None,
        additional_excludes: list[str] | None = None,
    ) -> str:
        """Analyzes a single file within the context of a project. Returns report output path."""
        reset_caches()

        file = Path(file_path)
        if log:
            log(f"Single file analysis: {file.name}")

        if log:
            log("Indexing and building project graph...")
        excludes, extra_dirs = _analysis_filters(repo_root, additional_excludes)
        modules = build_index(
            repo_root,
            excludes=excludes,
            extra_ignored_dirs=extra_dirs,
            progress_callback=progress_callback,
        )
        graph, cache_hit = get_cached_graph(modules, build_graph)

        if log:
            log("Generating global report (hotspots)...")
        global_report = generate_report(graph, modules=modules, runtime={"cache_hit": cache_hit})

        if log:
            log("Fetching deep context for file...")
        ctx = collect_all_contexts(
            file_path, modules, graph, global_report=global_report, root_path=repo_root
        )

        if log:
            log("Creating report for file...")

        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        from contextor.core.reporting_engine.dictionary import IndexDictionary
        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
        
        registry = PersistentIdentityRegistry(repo_root)
        with registry.transaction():
            index_dict = IndexDictionary(registry)
            report = generate_single_file_report(ctx, len(modules), index_dict=index_dict)

        # Named after the module path, not the bare stem: two files called
        # 'engine.py' in different packages used to overwrite each other.
        try:
            relative = file.resolve().relative_to(Path(repo_root).resolve())
            slug = ".".join(relative.with_suffix("").parts)
        except ValueError:
            slug = file.stem

        output = str(output_dir() / f"single_{slug}.json")
        from contextor.core.reporting_engine.dictionary import compact_recursively
        compact_report = compact_recursively(report, index_dict, set(modules.keys()))
        compact_report["module_name"] = report["module_name"]
        save_single_file_report(compact_report, output)
        snapshot_dir = output_dir() / f"{Path(repo_root).resolve().name}_{datestamp}"
        snapshot_json = snapshot_dir / f"single_{slug}.json"
        save_single_file_report(compact_report, str(snapshot_json))



        # Graph analytics for the single analyzed module
        from contextor.core.reporting_engine.graph_analytics import generate_graph_analytics_report
        from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report as _gen_art
        try:
            sf_artifact_data = _gen_art(modules, repo_root, runtime={"cache_hit": cache_hit})
            target_module_id = None
            # Find module_id matching the analyzed file
            file_resolved = file.resolve()
            for mid, mod in modules.items():
                mod_path = Path(getattr(mod, "absolute_path", None) or getattr(mod, "path", ""))
                if mod_path.resolve() == file_resolved:
                    target_module_id = mid
                    break

            scope_mods = {target_module_id} if target_module_id else None
            # Include direct neighbors for useful matrix
            if scope_mods and target_module_id:
                from contextor.core.graph.graph import build_graph as _bg
                hard_e = graph.hard_edges
                neighbors = set(hard_e.get(target_module_id, []))
                for src, tgts in hard_e.items():
                    if target_module_id in tgts:
                        neighbors.add(src)
                scope_mods = {target_module_id} | neighbors

            ga_data = generate_graph_analytics_report(
                artifact_data=sf_artifact_data,
                hard_edges=graph.hard_edges,
                soft_edges=graph.soft_edges,
                modules=modules,
                index_dict=index_dict,
                scope="single_file",
                scope_modules=scope_mods,
            )
            ga_output = str(output_dir() / f"single_{slug}_graph_analytics.json")
            import json as _json
            with open(ga_output, "w", encoding="utf-8") as f_ga:
                _json.dump(ga_data, f_ga, indent=2, ensure_ascii=False)
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            with open(
                snapshot_dir / f"single_{slug}_graph_analytics.json",
                "w",
                encoding="utf-8",
            ) as f_ga:
                _json.dump(ga_data, f_ga, indent=2, ensure_ascii=False)
        except Exception as _ga_err:
            if log:
                log(f"[WARNING] graph_analytics skipped for single file: {_ga_err}")

        md_output = str(output_dir() / f"single_{slug}_llm_context.md")
        generate_llm_markdown(report, md_output)
        generate_llm_markdown(
            report,
            str(snapshot_dir / f"single_{slug}_llm_context.md"),
        )

        if log:
            log("Single file report and MD bundle saved successfully.")
        return output
