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


def ensure_cycles(state: RepositoryAnalysisState) -> None:
    """
    Ensures state.cycles is fresh and computed from canonical graph.
    Recomputes in RAM when state is deferred/missing and dependency_graph is present.
    Preserves stale state when graph is untrusted.
    Preserves fresh state without recomputation (even if empty).
    RAM ONLY — ZERO source I/O.
    """
    if not hasattr(state, "cycles_state") or state.cycles_state is None:
        state.cycles_state = "deferred"

    if not hasattr(state, "cycles") or state.cycles is None:
        state.cycles = []

    # A. Fresh state: preserve, zero recomputation (even if cycles == [])
    if state.cycles_state == "fresh":
        return

    # B. Stale state: untrusted/desynced graph -> do NOT auto-heal
    if state.cycles_state == "stale":
        return

    # C. Deferred / missing cycles + valid graph: atomic in-memory recomputation
    if getattr(state, "dependency_graph", None) is not None:
        try:
            from contextor.core.graph.cycles import detect_cycles

            hard_edges = getattr(state.dependency_graph, "hard_edges", {}) or {}
            computed = detect_cycles(hard_edges)
            state.cycles = computed
            state.cycles_state = "fresh"
        except Exception:
            # Fail-safe continuation: preserve existing cycles, do not leave false fresh
            if state.cycles_state == "fresh":
                state.cycles_state = "deferred"


VALID_COLLISION_TYPES = {"class", "function", "variable"}
REQUIRED_FACT_KEYS = {
    "name",
    "type",
    "file",
    "file_path",
    "code",
    "line_start",
    "line_end",
    "col_start",
    "col_end",
}


def _is_int_or_none(val: Any) -> bool:
    return val is None or (isinstance(val, int) and not isinstance(val, bool))


def _validate_collision_facts_dict(facts: Any, modules: Any) -> bool:
    """Validates structural integrity and canonical fact schema."""
    if not isinstance(facts, dict) or not isinstance(modules, dict):
        return False
    if set(facts.keys()) != set(modules.keys()):
        return False
    for mod_key, fact_list in facts.items():
        if not isinstance(fact_list, list):
            return False
        for fact in fact_list:
            if not isinstance(fact, dict):
                return False
            if not REQUIRED_FACT_KEYS.issubset(fact.keys()):
                return False
            if fact.get("type") not in VALID_COLLISION_TYPES:
                return False
            if fact.get("file") != mod_key:
                return False
            if not isinstance(fact.get("name"), str) or not isinstance(fact.get("code"), str):
                return False
            if not isinstance(fact.get("file_path"), str):
                return False
            if not _is_int_or_none(fact.get("line_start")) or not _is_int_or_none(fact.get("line_end")):
                return False
            if not _is_int_or_none(fact.get("col_start")) or not _is_int_or_none(fact.get("col_end")):
                return False
    return True


def collision_facts_complete(state: RepositoryAnalysisState) -> bool:
    """
    Returns True if and only if every canonical module in state.modules
    has a corresponding valid list of extracted facts in state.collision_facts.
    Validates fact schema, type domain, and module key integrity.
    An empty repository ({} == {}) is valid complete coverage.
    """
    if not hasattr(state, "collision_facts") or not hasattr(state, "modules"):
        return False
    return _validate_collision_facts_dict(state.collision_facts, state.modules)


def ensure_collisions(state: RepositoryAnalysisState) -> None:
    """
    Ensures state.collisions is fresh and computed from complete collision_facts.
    Recomputes in RAM when state is deferred/missing and collision_facts is complete.
    Preserves stale state when canonical source facts are untrusted.
    Preserves fresh state without recomputation when complete.
    RAM ONLY — ZERO source I/O.
    """
    if not hasattr(state, "collisions_state") or state.collisions_state is None:
        state.collisions_state = "deferred"

    if not hasattr(state, "collisions") or state.collisions is None:
        state.collisions = []

    if not hasattr(state, "collision_facts") or state.collision_facts is None:
        state.collision_facts = {}

    # A. Stale state: untrusted/desynced source facts -> do NOT auto-heal
    if state.collisions_state == "stale":
        return

    # B. Fresh state: verify completeness! Incomplete coverage degrades to deferred
    if state.collisions_state == "fresh":
        if collision_facts_complete(state):
            return
        state.collisions_state = "deferred"

    # C. Deferred / missing collisions + complete collision_facts: atomic in-memory recomputation
    if collision_facts_complete(state):
        try:
            from contextor.core.validator.collisions import compute_collisions_from_facts

            computed = compute_collisions_from_facts(state.collision_facts)
            state.collisions = computed
            state.collisions_state = "fresh"
        except Exception:
            # Fail-safe continuation: preserve existing collisions, do not leave false fresh
            if state.collisions_state == "fresh":
                state.collisions_state = "deferred"


def ensure_artifact_consumption(state: RepositoryAnalysisState) -> None:
    """
    Ensures state.artifact_consumption conforms to the canonical contract.
    Lifecycle rules:
    1. If state requires resync or is already marked stale: fail-closed (preserve stale marker).
    2. If consumption is a recognized LEGACY shape (e.g. {"_report": ...}):
       safely migrates in RAM from state.artifacts. If migrated candidate passes both
       structural validation and coverage validation, marks state fresh; otherwise stale.
    3. If consumption is a VALID canonical structure AND has COMPLETE COVERAGE:
       marks fresh (if not already set) and preserves.
    4. If consumption is an INVALID modern canonical structure or has INCOMPLETE COVERAGE:
       DO NOT auto-heal from state.artifacts; set state.artifact_consumption_state = "stale" (fail-closed).
    """
    if getattr(state, "resync_required", False) or getattr(state, "artifact_consumption_state", None) == "stale":
        state.artifact_consumption_state = "stale"
        return

    from contextor.core.analysis.state_manager import (
        build_canonical_artifact_consumption,
        is_legacy_artifact_consumption,
        validate_canonical_artifact_consumption,
        validate_canonical_artifact_consumption_coverage,
    )

    consumption = getattr(state, "artifact_consumption", None)
    artifacts = getattr(state, "artifacts", {}) or {}

    # A. Explicit Legacy Migration
    if is_legacy_artifact_consumption(consumption):
        candidate = build_canonical_artifact_consumption(artifacts)
        if (
            validate_canonical_artifact_consumption(candidate)
            and validate_canonical_artifact_consumption_coverage(candidate, artifacts)
        ):
            state.artifact_consumption = candidate
            state.artifact_consumption_state = "fresh"
        else:
            state.artifact_consumption_state = "stale"
        return

    # B. Valid Canonical State with Complete Coverage
    if (
        validate_canonical_artifact_consumption(consumption)
        and validate_canonical_artifact_consumption_coverage(consumption, artifacts)
    ):
        if not hasattr(state, "artifact_consumption_state") or state.artifact_consumption_state == "deferred":
            state.artifact_consumption_state = "fresh"
        return

    # C. Invalid Modern Canonical State OR Incomplete Coverage -> Fail Closed
    state.artifact_consumption_state = "stale"



def materialize_incremental_state(state: RepositoryAnalysisState) -> None:
    """
    Orchestrates complete materialization of incremental state in exact required lifecycle order:
    1. ensure_artifact_consumption (RAM-only self-heal from legacy _report if needed)
    2. ensure_module_usages (legacy source-backed reconstruction if needed)
    3. ensure_topology_analytics (RAM-only)
    4. ensure_cached_analytics (RAM-only)
    5. ensure_cycles (RAM-only)
    6. ensure_collisions (RAM-only)
    """
    ensure_artifact_consumption(state)
    ensure_module_usages(state)
    ensure_topology_analytics(state)
    ensure_cached_analytics(state)
    ensure_cycles(state)
    ensure_collisions(state)


