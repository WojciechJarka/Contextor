"""
contextor/core/analysis/incremental/materialization.py

Bootstrap and legacy-state materialization for incremental analysis state.
Provides idempotent RAM materialization of derived analytics and source-backed
reconstruction of missing legacy facts.
"""

from pathlib import Path
from typing import Optional, Any

from contextor.core.analysis.state_manager import RepositoryAnalysisState


def ensure_module_usages(state: RepositoryAnalysisState) -> None:
    """
    Initializes state.module_usages for pre-existing state.modules if missing.
    Source-backed legacy reconstruction: only missing modules read source from disk.
    """
    if not hasattr(state, "module_usages") or state.module_usages is None:
        state.module_usages = {}

    missing_modules = set(state.modules.keys()) - set(state.module_usages.keys())
    if missing_modules:
        from contextor.core.reference.engine import extract_module_usage_facts

        for mod_path in missing_modules:
            mod = state.modules[mod_path]
            mod_abs = getattr(mod, "absolute_path", None) or getattr(mod, "path", None)
            source_text = None
            if mod_abs and Path(mod_abs).exists():
                try:
                    source_text = Path(mod_abs).read_text(encoding="utf-8")
                except OSError:
                    source_text = None
            imports = getattr(mod, "imports", [])
            state.module_usages[mod_path] = extract_module_usage_facts(
                mod_path,
                source_text,
                imports=imports,
            )


def ensure_topology_analytics(state: RepositoryAnalysisState) -> None:
    """
    Ensures state.topology_analytics is fresh and complete from canonical graph.
    Recomputes in RAM when state is deferred/missing and dependency_graph is present.
    Preserves stale state when graph is untrusted.
    RAM ONLY — ZERO source I/O.
    """
    if not hasattr(state, "topology_metrics_state") or state.topology_metrics_state is None:
        state.topology_metrics_state = "deferred"

    if not hasattr(state, "topology_analytics") or state.topology_analytics is None:
        state.topology_analytics = {}

    # A. Fresh + populated analytics: preserve, zero recomputation
    if state.topology_metrics_state == "fresh" and state.topology_analytics:
        return

    # B. Stale state: untrusted/desynced graph -> do NOT auto-heal
    if state.topology_metrics_state == "stale":
        return

    # C. Deferred / missing analytics + valid graph: atomic in-memory recomputation
    if getattr(state, "dependency_graph", None) is not None:
        try:
            from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics

            hard_edges = getattr(state.dependency_graph, "hard_edges", {}) or {}
            soft_edges = getattr(state.dependency_graph, "soft_edges", {}) or {}
            metrics = getattr(state, "metrics", {}) or {}

            computed = compute_topology_analytics(
                hard_edges,
                soft_edges,
                metrics,
            )
            state.topology_analytics = computed
            state.topology_metrics_state = "fresh"
        except Exception:
            # Fail-safe continuation: preserve existing analytics, do not leave false fresh
            if state.topology_metrics_state == "fresh":
                state.topology_metrics_state = "deferred"


def ensure_cached_analytics(state: RepositoryAnalysisState) -> None:
    """
    Materializes state.cached_analytics from canonical facts if missing/empty and not stale.
    RAM ONLY — ZERO source I/O.
    """
    if not hasattr(state, "cached_analytics_state") or state.cached_analytics_state is None:
        state.cached_analytics_state = (
            "fresh" if bool(getattr(state, "cached_analytics", None)) else "deferred"
        )

    if not hasattr(state, "cached_analytics") or state.cached_analytics is None:
        state.cached_analytics = {}

    if (
        state.cached_analytics_state != "stale"
        and not state.cached_analytics
        and getattr(state, "modules", None)
    ):
        from contextor.core.reporting_engine.graph_analytics import compute_cached_analytics

        hard_edges = (
            getattr(state.dependency_graph, "hard_edges", {})
            if state.dependency_graph
            else {}
        )
        state.cached_analytics = compute_cached_analytics(
            modules=state.modules,
            artifacts=getattr(state, "artifacts", {}),
            artifact_consumption=getattr(state, "artifact_consumption", {}),
            hard_edges=hard_edges,
        )
        state.cached_analytics_state = "fresh"


def materialize_incremental_state(state: RepositoryAnalysisState) -> None:
    """
    Orchestrates complete materialization of incremental state in exact required lifecycle order:
    1. ensure_module_usages (legacy source-backed reconstruction if needed)
    2. ensure_topology_analytics (RAM-only)
    3. ensure_cached_analytics (RAM-only)
    """
    ensure_module_usages(state)
    ensure_topology_analytics(state)
    ensure_cached_analytics(state)
