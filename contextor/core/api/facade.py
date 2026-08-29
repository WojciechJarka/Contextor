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
from contextor.core.reporting_engine.canonical_artifacts import (
    canonical_artifact_report,
)
from contextor.core.reporting_engine.pipeline import execute_global_pipeline
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)

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
from contextor.core.validator.collisions import (
    compute_collisions_from_facts,
    extract_repository_collision_facts,
    validate_name_collisions,
)
from contextor.core.live_state import hydrate_repository_engine


def _compute_metrics_and_debt(
    modules,
    graph,
    progress_callback=None,
    collisions=None,
    collision_facts=None,
):
    """
    Shared analytical pipeline extracting graph metrics and tech debt scores.
    """
    checkpoint(progress_callback, "Computing graph metrics...")
    metrics = compute_graph_metrics(graph.hard_edges, graph.soft_edges)

    checkpoint(progress_callback, "Detecting cycles...")
    cycles = detect_cycles(graph.hard_edges, progress_callback=progress_callback)

    checkpoint(progress_callback, "Validating collisions...")
    if collisions is not None:
        all_collisions = collisions
    elif collision_facts is not None:
        all_collisions = compute_collisions_from_facts(collision_facts)
    else:
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


def _initialize_repository_identity(repo_root: str | Path) -> PersistentIdentityRegistry:
    """Persist a repository identity before any analysis pipeline starts."""

    root = Path(repo_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Repository root does not exist: {root}")

    registry = PersistentIdentityRegistry(str(root))
    registry.ensure_initialized()
    return registry


def _resolve_repository_target(
    repo_root: str | Path,
    target: str | Path,
    *,
    target_kind: str,
) -> tuple[Path, Path]:
    """Resolve and validate one layer/file target against its repository root."""

    root = Path(repo_root).expanduser().resolve()
    candidate = Path(target).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Repository root does not exist: {root}")
    if candidate == root or root not in candidate.parents:
        raise ValueError(
            f"Selected {target_kind} is outside the repository root: {candidate} (root: {root})"
        )
    if target_kind == "layer" and not candidate.is_dir():
        raise ValueError(f"Selected layer does not exist or is not a directory: {candidate}")
    if target_kind == "file" and not candidate.is_file():
        raise ValueError(f"Selected file does not exist or is not a file: {candidate}")
    return root, candidate


class _StagedProgress:
    """Map every top-level analysis stage into one monotonic progress range."""

    _SCALE = 1000

    def __init__(self, callback, total_stages: int, log=None):
        self._callback = callback
        self._total_stages = total_stages
        self._current_stage = 0
        self._label = "Preparing analysis"
        self._log = log

    def begin(self, label: str):
        """Start a stage and return its bounded item-level progress callback."""

        if self._current_stage >= self._total_stages:
            raise RuntimeError("Progress plan contains more stages than declared")
        self._current_stage += 1
        self._label = label
        if self._log:
            self._log(f"[PROGRESS] Step {self._current_stage}/{self._total_stages}: {label}")
        if not self._emit(0.0, label):
            raise AnalysisCancelled()
        return self.items

    def items(self, completed, total, filename):
        ratio = (completed / total) if total else 0.0
        ratio = min(1.0, max(0.0, ratio))
        detail = str(filename) if filename else self._label
        return self._emit(ratio, detail)

    def finish(self):
        self._current_stage = self._total_stages
        self._emit(1.0, "Analysis complete")

    def _emit(self, ratio: float, detail: str):
        if self._callback is None:
            return True
        completed = int(((self._current_stage - 1) + ratio) * self._SCALE)
        total = self._total_stages * self._SCALE
        message = f"Step {self._current_stage}/{self._total_stages}: {self._label} — {detail}"
        result = self._callback(completed, total, message)
        return result is not False


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
        owner: str = "desktop_analysis",
    ) -> list:
        """
        Analyzes full project hierarchy, builds dependency graph, evaluates
        technical debt, detects cycles and saves all generated artifacts.

        Args:
            path: Absolute string path to the project root directory.
            log: Optional callback function for streaming stdout progress.
            progress_callback: Optional callback for progress percentage (completed, total, filename).
            additional_excludes: Optional list of additional directory paths to exclude.
            owner: Analysis caller identity (desktop_analysis, mcp_analysis, cli_analysis).

        Returns:
            list: List of architectural validation errors, if any.
        """
        progress = _StagedProgress(progress_callback, total_stages=8, log=log)
        progress.begin("Initializing repository identity")
        registry = _initialize_repository_identity(path)
        path = str(registry.repo_path.resolve())
        reset_caches()

        if log:
            log("Starting directory indexing...")
        excludes, extra_dirs = _analysis_filters(path, additional_excludes)
        index_progress = progress.begin("Indexing repository files")
        index = index_repository(
            path,
            excludes=excludes,
            extra_ignored_dirs=extra_dirs,
            progress_callback=index_progress,
        )
        modules = index.modules

        # Compute collision facts once from current-run modules
        from contextor.core.validator.collisions import compute_collisions_from_facts, extract_repository_collision_facts
        collision_facts = extract_repository_collision_facts(modules)
        all_collisions = compute_collisions_from_facts(collision_facts)

        from contextor.core.graph.resolver import build_trie, detect_package_root
        trie = build_trie(modules.keys())
        package_root = detect_package_root(modules, trie)

        if log:
            log(f"Found {len(modules)} modules. Fetching graph...")
            _log_skipped(index.skipped, log)
        progress.begin("Resolving dependency graph")
        graph_progress = progress.items
        graph, cache_hit = get_cached_graph(
            modules, 
            lambda m: build_graph(
                m,
                trie=trie,
                package_root=package_root,
                progress_callback=graph_progress,
            )
        )

        if log:
            log(f"Graph validation (cache_hit={cache_hit})...")
        validation_progress = progress.begin("Validating dependency graph")
        errors = validate(
            modules, 
            graph, 
            progress_callback=validation_progress,
            collisions=all_collisions,
            collision_facts=collision_facts,
        )

        repo_name = Path(path).name

        metrics_progress = progress.begin("Computing metrics, cycles and debt")
        metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(
            modules,
            graph,
            progress_callback=metrics_progress,
            collisions=all_collisions,
            collision_facts=collision_facts,
        )

        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report_progress = progress.begin("Generating architectural reports")
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
            collision_facts=collision_facts,
            progress_callback=report_progress,
            skipped_files=index.skipped,
            datestamp=datestamp,
            trie=trie,
            package_root=package_root,
            symbol_facts_by_module=index.symbol_facts_by_module,
        )

        if log and report_result.get("high_risk_layers"):
            high_risk_layers = ", ".join(report_result["high_risk_layers"])
            log(f"Generated additional reports for high risk layers: {high_risk_layers}")


        analysis_result = report_result.get("_analysis_result")
        
        progress.begin("Persisting canonical LIVE snapshot")
        if analysis_result:
            from contextor.core.analysis.state_manager import (
                FileStateManager,
                RepositoryAnalysisState,
                artifact_consumption_is_fresh,
                build_canonical_artifact_consumption,
                dependency_matrix_inputs_are_fresh,
                save_engine_state,
                validate_canonical_artifact_consumption_coverage,
            )
            from contextor.core.paths import repo_cache_dir
            from contextor.core.live_state.store import read_metadata
            from contextor.core.reporting_engine.graph_analytics import (
                compute_dependency_matrix_from_state,
                compute_shared_usage_clusters_from_state,
                compute_topology_analytics,
            )

            graph = getattr(analysis_result, "graph", None)
            hard_edges = getattr(graph, "hard_edges", {}) if graph else {}
            soft_edges = getattr(graph, "soft_edges", {}) if graph else {}
            metrics = getattr(analysis_result, "metrics", {})
            topology_analytics = compute_topology_analytics(hard_edges, soft_edges, metrics) if hard_edges else {}

            from contextor.core.analysis.incremental.materialization import _validate_collision_facts_dict
            from contextor.core.validator.collisions import compute_collisions_from_facts

            cf = getattr(analysis_result, "collision_facts", None)
            mods = getattr(analysis_result, "modules", {})
            is_collision_complete = _validate_collision_facts_dict(cf, mods)

            if is_collision_complete:
                canonical_collisions = compute_collisions_from_facts(cf)
                collisions_state = "fresh"
            else:
                canonical_collisions = []
                collisions_state = "deferred"

            raw_artifacts = getattr(analysis_result, "artifacts", {}) or {}
            canonical_consumption = build_canonical_artifact_consumption(raw_artifacts)

            # Exact canonical coverage trust gate (no truthiness)
            consumption_valid = validate_canonical_artifact_consumption_coverage(
                canonical_consumption,
                raw_artifacts,
            )

            state = RepositoryAnalysisState(
                modules=getattr(analysis_result, "modules", {}),
                artifacts=raw_artifacts,
                dependency_graph=graph,
                trie=getattr(analysis_result, "trie", None),
                package_root=getattr(analysis_result, "package_root", ""),
                artifact_consumption=canonical_consumption,
                artifact_consumption_state="fresh" if consumption_valid else "stale",
                metrics=metrics,
                topology_analytics=topology_analytics,
                topology_metrics_state="fresh",
                cycles=getattr(analysis_result, "cycles", []),
                cycles_state="fresh",
                collision_facts=cf if isinstance(cf, dict) else {},
                collisions=canonical_collisions,
                collisions_state=collisions_state,
                layer_information={
                    "layer_index": getattr(analysis_result, "layer_index", []),
                    "hotspots": getattr(analysis_result, "hotspots", []),
                    "debt": getattr(analysis_result, "debt", {}),
                    "summary_data": getattr(analysis_result, "summary_data", {}),
                },
                dependency_matrix={},
                dependency_matrix_state="deferred",
                shared_usage_clusters=[],
                shared_usage_clusters_state="deferred",
            )

            if getattr(analysis_result, "resync_required", False):
                state.resync_required = True

            # Compute Dependency Matrix from canonical state (independent failure & graph trust)
            if dependency_matrix_inputs_are_fresh(state):
                try:
                    _dm_candidate = compute_dependency_matrix_from_state(state)
                except Exception:
                    state.dependency_matrix_state = "stale"
                else:
                    state.dependency_matrix = _dm_candidate
                    state.dependency_matrix_state = "fresh"
            else:
                state.dependency_matrix_state = "stale"

            # Compute Shared Usage Clusters from canonical state (independent failure & AC trust)
            if artifact_consumption_is_fresh(state):
                try:
                    _suc_candidate = compute_shared_usage_clusters_from_state(state)
                except Exception:
                    state.shared_usage_clusters_state = "stale"
                else:
                    state.shared_usage_clusters = _suc_candidate
                    state.shared_usage_clusters_state = "fresh"
            else:
                state.shared_usage_clusters_state = "stale"

            live_publish_status = "not_attempted"
            live_publish_revision = None
            live_publish_warning = None

            writer = "mcp" if "mcp" in str(owner) else "desktop"
            origin = str(owner) if str(owner) in {"desktop_analysis", "mcp_analysis", "cli_analysis"} else "desktop_analysis"

            cache_dir = str(repo_cache_dir(path))
            file_state_manager = report_result.get("_file_state_manager")
            current_metadata = read_metadata(cache_dir)
            target_revision = (current_metadata.revision if current_metadata else 0) + 1
            file_state_payload = (
                file_state_manager.build_payload(datestamp or "", target_revision)
                if file_state_manager is not None
                else None
            )
            meta = save_engine_state(
                state,
                cache_dir,
                datestamp,
                writer=writer,
                repo_id=registry.repo_id,
                root_path=path,
                exact_revision=target_revision,
                file_state_payload=file_state_payload,
            )
            if meta is not None:
                from contextor.core.live_state import connect

                try:
                    client = connect(path)
                    if client is not None:
                        published = client.publish(state, origin=origin)
                        if (
                            isinstance(published, dict)
                            and published.get("status") == "ok"
                            and published.get("revision") is not None
                        ):
                            live_publish_status = "success"
                            live_publish_revision = int(published["revision"])
                            live_publish_warning = None
                        else:
                            live_publish_status = "failed"
                            live_publish_revision = None
                            err = published.get("error") if isinstance(published, dict) else None
                            status_val = published.get("status") if isinstance(published, dict) else None
                            live_publish_warning = err or (f"LIVE service returned status '{status_val}'." if status_val else "Canonical LIVE service rejected publication.")
                            if log:
                                log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")
                    else:
                        live_publish_status = "not_attempted"
                except Exception as e:
                    live_publish_status = "timed_out" if isinstance(e, TimeoutError) else "failed"
                    live_publish_revision = None
                    live_publish_warning = f"{type(e).__name__}: {e}"
                    if log:
                        log(f"Warning: Failed to publish canonical state to live daemon: {live_publish_warning}")

            if analysis_result is not None:
                analysis_result.live_publish_status = live_publish_status
                analysis_result.live_publish_revision = live_publish_revision
                analysis_result.live_publish_warning = live_publish_warning
                if hasattr(analysis_result, "summary_data") and isinstance(analysis_result.summary_data, dict):
                    analysis_result.summary_data["live_publish_status"] = live_publish_status
                    analysis_result.summary_data["live_publish_revision"] = live_publish_revision
                    analysis_result.summary_data["live_publish_warning"] = live_publish_warning

        progress.begin("Finalizing analysis")
        progress.finish()
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
        progress = _StagedProgress(progress_callback, total_stages=10, log=log)
        progress.begin("Validating repository and layer scope")
        root_resolved, layer_resolved = _resolve_repository_target(
            root_dir, layer_dir, target_kind="layer"
        )
        repo_name = root_resolved.name
        layer_name = layer_resolved.name

        progress.begin("Initializing repository identity")
        registry = _initialize_repository_identity(root_resolved)
        reset_caches()

        if log:
            log(f"Processing layer '{layer_name}' in project '{repo_name}'...")
        excludes, extra_dirs = _analysis_filters(
            str(root_resolved), additional_excludes
        )
        from contextor.core.graph.resolver import build_trie, detect_package_root

        hydrated = hydrate_repository_engine(root_resolved)
        if hydrated is not None:
            progress.begin("Loading canonical LIVE context")
            modules = hydrated.engine.state.modules
            trie = hydrated.engine.state.trie or build_trie(modules.keys())
            package_root = (
                hydrated.engine.state.package_root
                or detect_package_root(modules, trie)
            )
            progress.begin("Reusing canonical dependency graph")
            graph = hydrated.engine.state.dependency_graph
            cache_hit = True
            skipped_files = []
            if log:
                log(
                    "Reused canonical context "
                    f"from {hydrated.source}; skipped repository re-indexing."
                )
        else:
            index_progress = progress.begin("Indexing repository files")
            index = index_repository(
                str(root_resolved),
                excludes=excludes,
                extra_ignored_dirs=extra_dirs,
                progress_callback=index_progress,
            )
            modules = index.modules
            trie = build_trie(modules.keys())
            package_root = detect_package_root(modules, trie)
            progress.begin("Resolving dependency graph")
            graph_progress = progress.items
            graph, cache_hit = get_cached_graph(
                modules,
                lambda m: build_graph(
                    m,
                    trie=trie,
                    package_root=package_root,
                    progress_callback=graph_progress,
                ),
            )
            skipped_files = getattr(index, "skipped", [])

        if log:
            log("Calculating metrics and collisions for the full project...")
        metrics_progress = progress.begin("Computing metrics, cycles and debt")
        metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(
            modules, graph, progress_callback=metrics_progress
        )

        runtime = {"cache_hit": cache_hit}

        if log:
            log("Preparing data structures for slicing...")
        progress.begin("Preparing report data structures")
        hotspots = detect_hotspots(graph.hard_edges)
        global_summary = generate_summary_report(
            metrics,
            cycles,
            debt,
            collisions=all_collisions,
            hotspots=hotspots,
        )
        global_structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
        artifacts_progress = progress.begin("Preparing artifact usage")
        if hydrated is not None:
            checkpoint(artifacts_progress, "Projecting canonical artifacts", 0, 1)
            global_artifacts = canonical_artifact_report(
                hydrated.engine.state.artifacts
            )
        else:
            global_artifacts = generate_artifact_usage_report(
                modules,
                str(root_resolved),
                runtime,
                progress_callback=artifacts_progress,
                symbol_facts_by_module=getattr(index, "symbol_facts_by_module", None),
            )
        
        from contextor.core.reporting_engine.dictionary import IndexDictionary
        
        progress.begin("Compacting and slicing layer reports")
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
            global_skipped_files=skipped_files,
            report_header=report_header,
            index_dict=index_dict,
        )

        if log:
            log(f"Saving 5 layer reports for '{layer_name}'...")
            
        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        from contextor.core.reporting_engine.layer_pipeline import (
            execute_layer_pipeline,
        )
        from contextor.core.reporting_engine.io_manager import write_layer_reports
        
        progress.begin("Writing layer report bundle")
        execute_layer_pipeline(
            repo_name,
            layer_name,
            layer_sliced_reports,
            log=log,
            datestamp=datestamp,
            progress_callback=progress.items,
        )
        write_layer_reports(
            repo_name=repo_name,
            layer_name=layer_name,
            layer_reports=layer_sliced_reports,
            datestamp=datestamp,
            log=log,
        )

        # Absolute, so what the GUI shows the user is a path that exists.
        pattern = str(output_dir() / f"{repo_name}_{layer_name}_*.json")

        progress.begin("Finalizing layer analysis")
        progress.finish()
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
        progress = _StagedProgress(progress_callback, total_stages=11, log=log)
        progress.begin("Validating repository and file scope")
        root_resolved, file = _resolve_repository_target(
            repo_root, file_path, target_kind="file"
        )
        if file.suffix.lower() != ".py":
            raise ValueError(f"Selected file is not a Python file: {file}")
        progress.begin("Initializing repository identity")
        registry = _initialize_repository_identity(root_resolved)
        repo_root = str(registry.repo_path.resolve())
        reset_caches()
        if log:
            log(f"Single file analysis: {file.name}")

        if log:
            log("Preparing project context...")
        excludes, extra_dirs = _analysis_filters(repo_root, additional_excludes)
        hydrated = hydrate_repository_engine(repo_root)
        if hydrated is not None:
            progress.begin("Loading canonical LIVE context")
            update_progress = progress.begin("Refreshing selected file in LIVE context")
            checkpoint(update_progress, f"Refreshing {file.name}", 0, 1)
            update_result = hydrated.engine.update_file(str(file))
            if update_result.status in {"SYNTAX_ERROR", "ERROR"}:
                location = ""
                if getattr(update_result, "line_number", None):
                    location = f" at line {update_result.line_number}"
                raise ValueError(
                    f"Cannot analyze {file.name}{location}: {update_result.error}"
                )
            modules = hydrated.engine.state.modules
            graph = hydrated.engine.state.dependency_graph
            cache_hit = True
            if update_result.status == "UPDATED" and hydrated.client is not None:
                try:
                    hydrated.client.publish(
                        hydrated.engine.state,
                        origin="scoped_analysis",
                        timeout=5.0,
                    )
                except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError):
                    if log:
                        log("[WARNING] Updated single-file state could not be published to LIVE.")
            if log:
                log(
                    "Reused canonical context "
                    f"from {hydrated.source}; skipped repository re-indexing."
                )
        else:
            index_progress = progress.begin("Indexing repository files")
            modules = build_index(
                repo_root,
                excludes=excludes,
                extra_ignored_dirs=extra_dirs,
                progress_callback=index_progress,
            )
            graph_progress = progress.begin("Resolving dependency graph")
            graph, cache_hit = get_cached_graph(
                modules,
                lambda m: build_graph(m, progress_callback=graph_progress),
            )

        if log:
            log("Generating global report (hotspots)...")
        progress.begin("Generating global context")
        global_report = generate_report(graph, modules=modules, runtime={"cache_hit": cache_hit})

        if log:
            log("Fetching deep context for file...")
        progress.begin("Collecting deep file context")
        ctx = collect_all_contexts(
            file_path,
            modules,
            graph,
            global_report=global_report,
            root_path=repo_root,
            progress_callback=progress.items,
            engine_state=hydrated.engine.state if hydrated is not None else None,
        )

        if log:
            log("Creating report for file...")

        from datetime import datetime
        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        from contextor.core.reporting_engine.dictionary import IndexDictionary

        progress.begin("Building and compacting file report")
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
        progress.begin("Writing JSON report snapshots")
        compact_report = compact_recursively(
            report,
            index_dict,
            set(modules.keys()),
            progress_callback=progress.items,
        )
        compact_report["module_name"] = report["module_name"]
        save_single_file_report(compact_report, output)
        snapshot_dir = output_dir() / f"{Path(repo_root).resolve().name}_{datestamp}"
        snapshot_json = snapshot_dir / f"single_{slug}.json"
        save_single_file_report(compact_report, str(snapshot_json))



        # Graph analytics for the single analyzed module
        progress.begin("Generating graph analytics")
        from contextor.core.reporting_engine.graph_analytics import generate_graph_analytics_report
        from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report as _gen_art
        try:
            if hydrated is not None:
                sf_artifact_data = canonical_artifact_report(
                    hydrated.engine.state.artifacts
                )
            else:
                sf_artifact_data = _gen_art(
                    modules,
                    repo_root,
                    runtime={"cache_hit": cache_hit},
                    progress_callback=progress.items,
                )
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
                progress_callback=progress.items,
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

        progress.begin("Writing Markdown context")
        md_output = str(output_dir() / f"single_{slug}_llm_context.md")
        generate_llm_markdown(report, md_output)
        generate_llm_markdown(
            report,
            str(snapshot_dir / f"single_{slug}_llm_context.md"),
        )

        progress.begin("Finalizing single-file analysis")
        progress.finish()
        if log:
            log("Single file report and MD bundle saved successfully.")
        return output
