"""Plan and verify bounded second-pass original indexer source capture.

The second index pass has its own worker reads. Equality with a
first-pass inventory does not make the repository cross-file atomic,
authenticate a canonical generation, or authorize publication.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .contracts import fingerprint_hard_edges
from .original_worker_binding import (
    assess_original_worker_cycle_closure,
)
from .model_source_closure import compute_cycle_model_source_closures
from .scc import analyze_import_cycle_topology


_MAX_SELECTED = 256
_READY = "READY_FOR_REINDEX_NON_ATOMIC"
_VERIFIED = "REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC"


@dataclass(frozen=True)
class OriginalWorkerReindexPlan:
    status: str
    reason: str | None
    selected_module_ids: frozenset[str]
    graph_sha256: str | None
    fingerprints: tuple[tuple[str, str], ...]
    module_paths: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class OriginalWorkerReindexVerification:
    status: str
    reason: str | None
    source_modules: tuple[str, ...]


def plan_original_worker_reindex(
    index: object,
    hard_edges: Mapping[str, object],
) -> OriginalWorkerReindexPlan:
    """Select SCC closures for a subsequent, separate index pass.

    Inputs are caller-supplied. This function performs no filesystem
    access, source reading, indexing, IPC or publication.
    """
    from contextor.core.symbol_engine.indexer import RepositoryIndex

    if type(index) is not RepositoryIndex:
        raise TypeError("index must be RepositoryIndex")

    def unavailable(reason: str) -> OriginalWorkerReindexPlan:
        return OriginalWorkerReindexPlan(
            status="UNAVAILABLE",
            reason=reason,
            selected_module_ids=frozenset(),
            graph_sha256=None,
            fingerprints=(),
            module_paths=(),
        )

    if (
        type(index.modules) is not dict
        or type(index.source_fingerprints_by_module) is not dict
    ):
        return unavailable("INDEX_SHAPE_INVALID")

    try:
        topology = analyze_import_cycle_topology(hard_edges)
        graph_sha256 = fingerprint_hard_edges(hard_edges)
    except (TypeError, ValueError):
        return unavailable("GRAPH_INVALID")

    indexed_ids = set(index.modules)

    if set(hard_edges) != indexed_ids:
        return unavailable("GRAPH_INDEX_DOMAIN_MISMATCH")

    if set(index.source_fingerprints_by_module) != indexed_ids:
        return unavailable("INDEX_FINGERPRINT_DOMAIN_MISMATCH")

    fingerprints = index.source_fingerprints_by_module

    if any(
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
        for value in fingerprints.values()
    ):
        return unavailable("INDEX_FINGERPRINT_INVALID")

    if not topology.cyclic_components:
        return unavailable("NO_CYCLIC_COMPONENTS")

    selected: set[str] = set()
    for closure in compute_cycle_model_source_closures(hard_edges):
        selected.update(closure.evidence_source_modules)

        if len(selected) > _MAX_SELECTED:
            return unavailable("CLOSURE_MODULE_LIMIT")

    if any(module_id not in indexed_ids for module_id in selected):
        return unavailable("CLOSURE_MODULE_NOT_INDEXED")

    try:
        module_paths = tuple(
            sorted(
                (
                    module_id,
                    index.modules[module_id].path,
                    index.modules[module_id].absolute_path,
                )
                for module_id in indexed_ids
            )
        )
    except (AttributeError, TypeError, ValueError):
        return unavailable("INDEX_MODULE_PATH_INVALID")

    if any(
        type(path) is not str
        or type(absolute) is not str
        or not path
        or not absolute
        for _, path, absolute in module_paths
    ):
        return unavailable("INDEX_MODULE_PATH_INVALID")

    return OriginalWorkerReindexPlan(
        status=_READY,
        reason=None,
        selected_module_ids=frozenset(selected),
        graph_sha256=graph_sha256,
        fingerprints=tuple(sorted(fingerprints.items())),
        module_paths=module_paths,
    )


def verify_original_worker_reindex(
    plan: OriginalWorkerReindexPlan,
    discovery_index: object,
    discovery_hard_edges: Mapping[str, object],
    captured_index: object,
    captured_hard_edges: Mapping[str, object],
) -> OriginalWorkerReindexVerification:
    """Verify two caller-supplied index passes before manifest preparation.

    This verifies declared agreement, not an atomic snapshot or
    authentic canonical provenance. No filesystem or LIVE access.
    """
    from contextor.core.symbol_engine.indexer import RepositoryIndex

    if type(plan) is not OriginalWorkerReindexPlan:
        raise TypeError("plan must be OriginalWorkerReindexPlan")
    if (
        type(discovery_index) is not RepositoryIndex
        or type(captured_index) is not RepositoryIndex
    ):
        raise TypeError("both passes must be RepositoryIndex")

    def unavailable(reason: str) -> OriginalWorkerReindexVerification:
        return OriginalWorkerReindexVerification(
            status="UNAVAILABLE",
            reason=reason,
            source_modules=(),
        )

    if plan.status != _READY:
        return unavailable("REINDEX_PLAN_UNAVAILABLE")

    if not plan.selected_module_ids:
        return unavailable("REINDEX_PLAN_EMPTY")

    try:
        discovery_graph_hash = fingerprint_hard_edges(
            discovery_hard_edges
        )
        captured_graph_hash = fingerprint_hard_edges(
            captured_hard_edges
        )
    except (TypeError, ValueError):
        return unavailable("REINDEX_GRAPH_INVALID")

    if discovery_graph_hash != plan.graph_sha256:
        return unavailable("DISCOVERY_GRAPH_CHANGED")

    if captured_graph_hash != plan.graph_sha256:
        return unavailable("REINDEX_GRAPH_CHANGED")

    try:
        discovery_fingerprints = tuple(sorted(
            discovery_index.source_fingerprints_by_module.items()
        ))
        captured_fingerprints = tuple(sorted(
            captured_index.source_fingerprints_by_module.items()
        ))

        discovery_paths = tuple(sorted(
            (
                module_id,
                module.path,
                module.absolute_path,
            )
            for module_id, module in discovery_index.modules.items()
        ))
        captured_paths = tuple(sorted(
            (
                module_id,
                module.path,
                module.absolute_path,
            )
            for module_id, module in captured_index.modules.items()
        ))
    except (AttributeError, TypeError, ValueError):
        return unavailable("REINDEX_INDEX_SHAPE_INVALID")

    if discovery_paths != plan.module_paths:
        return unavailable("DISCOVERY_MODULE_INVENTORY_CHANGED")

    if captured_paths != plan.module_paths:
        return unavailable("REINDEX_MODULE_INVENTORY_CHANGED")

    if discovery_fingerprints != plan.fingerprints:
        return unavailable("DISCOVERY_FINGERPRINTS_CHANGED")

    if captured_fingerprints != plan.fingerprints:
        return unavailable("REINDEX_SOURCE_CHANGED")

    if discovery_index.skipped != captured_index.skipped:
        return unavailable("REINDEX_SKIPPED_FILES_CHANGED")

    if captured_index.original_worker_capture_status != (
        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    ):
        return unavailable("REINDEX_CAPTURE_NOT_COMPLETE")

    if (
        set(captured_index.original_worker_source_snapshots)
        != plan.selected_module_ids
        or set(captured_index.original_worker_ast_modes)
        != plan.selected_module_ids
    ):
        return unavailable("REINDEX_SELECTION_MISMATCH")

    binding = assess_original_worker_cycle_closure(
        captured_index,
        captured_hard_edges,
    )

    if binding.status != (
        "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
    ):
        return unavailable(
            "REINDEX_BINDING_" + (
                binding.reason or "UNAVAILABLE"
            )
        )

    if frozenset(binding.reachable_modules) != (
        plan.selected_module_ids
    ):
        return unavailable("REINDEX_CLOSURE_CHANGED")

    return OriginalWorkerReindexVerification(
        status=_VERIFIED,
        reason=None,
        source_modules=binding.reachable_modules,
    )
