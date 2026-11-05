"""Bound selected original indexer bytes to a supplied SCC closure.

This is a non-atomic, in-memory consistency check. It does not authenticate
canonical graph ownership, bind an installed LIVE generation, or mint receipts.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.source import SourceError, SourceSnapshot

from .scc import analyze_import_cycle_topology
from .model_source_closure import (
    compute_cycle_model_source_closures,
    compute_cycle_model_source_closures_with_optional_children,
)


_CAPTURE_STATUS = "ALL_SELECTED_CAPTURED_NON_ATOMIC"
_ACCEPTED_MODES = frozenset({
    "PARSED_FROM_WORKER_READ",
    "CACHE_SHA256_EQUIVALENT",
})
_MAX_MODULES = 256
_MAX_SOURCE_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_BYTES = 32 * 1024 * 1024
_HARD_ONLY = "HARD_ONLY"
_OPTIONAL_NAMED_CHILDREN = "OPTIONAL_NAMED_CHILDREN"


def _select_original_worker_sources(
    index: object,
    hard_edges: Mapping[str, object],
    source_selection: str,
) -> tuple[tuple[object, ...], tuple[str, ...], str | None]:
    """Select indexed SCC sources without reading source bytes or changing graph edges."""
    if source_selection == _HARD_ONLY:
        closures = compute_cycle_model_source_closures(hard_edges)
        package_root = None
    elif source_selection == _OPTIONAL_NAMED_CHILDREN:
        if (
            type(index.modules) is not dict
            or type(index.source_fingerprints_by_module) is not dict
            or set(index.modules) != set(hard_edges)
            or set(index.source_fingerprints_by_module) != set(hard_edges)
        ):
            raise ValueError("INDEX_DOMAIN_MISMATCH")
        from contextor.core.graph.resolver import build_trie, detect_package_root

        imports = {
            module_id: module.imports
            for module_id, module in index.modules.items()
        }
        trie = build_trie(index.modules)
        package_root = detect_package_root(index.modules, trie)
        closures = compute_cycle_model_source_closures_with_optional_children(
            hard_edges, imports, package_root=package_root,
        )
    else:
        raise ValueError("SOURCE_SELECTION_INVALID")
    selected = tuple(sorted({
        module_id
        for closure in closures
        for module_id in closure.evidence_source_modules
    }))
    if len(selected) > _MAX_MODULES:
        raise ValueError("CLOSURE_MODULE_LIMIT")
    return closures, selected, package_root


@dataclass(frozen=True)
class OriginalWorkerCycleClosureBinding:
    status: str
    reason: str | None
    cyclic_components: tuple[tuple[str, ...], ...]
    reachable_modules: tuple[str, ...]  # Evidence-source closure, including initializers.
    source_snapshots: dict[str, SourceSnapshot]
    ast_modes: tuple[tuple[str, str], ...]
    retained_raw_bytes: int


def assess_original_worker_cycle_closure(
    index: object,
    hard_edges: Mapping[str, object],
    *,
    source_selection: str = _HARD_ONLY,
) -> OriginalWorkerCycleClosureBinding:
    """Validate that opted-in original indexer captures cover every SCC closure.

    Inputs are caller-supplied index and graph. No filesystem access, parsing,
    worker execution, canonical freshness assertion, publication, or LIVE I/O.
    Complete only means selected worker-read bytes match the supplied index
    fingerprints, across all reachable cyclic SCC closures, without atomically
    capturing the repository or authenticating who supplied the graph.
    """
    # Import locally to avoid creating an import-time dependency back to the
    # indexer from cycle-semantics modules.
    from contextor.core.symbol_engine.indexer import RepositoryIndex

    if type(index) is not RepositoryIndex:
        raise TypeError("index must be RepositoryIndex")
    if not isinstance(hard_edges, Mapping):
        raise TypeError("hard_edges must be a mapping")

    def unavailable(reason: str) -> OriginalWorkerCycleClosureBinding:
        # Never expose partially validated snapshots or modes.
        return OriginalWorkerCycleClosureBinding(
            status="UNAVAILABLE",
            reason=reason,
            cyclic_components=(),
            reachable_modules=(),
            source_snapshots={},
            ast_modes=(),
            retained_raw_bytes=0,
        )

    if source_selection not in (_HARD_ONLY, _OPTIONAL_NAMED_CHILDREN):
        return unavailable("SOURCE_SELECTION_INVALID")

    topology = analyze_import_cycle_topology(hard_edges)
    if not topology.cyclic_components:
        return unavailable("NO_CYCLIC_COMPONENTS")
    if (
        index.original_worker_capture_status != _CAPTURE_STATUS
        or index.original_worker_capture_reason is not None
    ):
        return unavailable("INDEX_CAPTURE_NOT_COMPLETE")

    if (
        type(index.modules) is not dict
        or type(index.source_fingerprints_by_module) is not dict
        or type(index.original_worker_source_snapshots) is not dict
        or type(index.original_worker_ast_modes) is not dict
    ):
        return unavailable("INDEX_CAPTURE_SHAPE_INVALID")

    snapshots = index.original_worker_source_snapshots
    modes = index.original_worker_ast_modes
    if (
        len(snapshots) > _MAX_MODULES
        or set(snapshots) != set(modes)
    ):
        return unavailable("INDEX_CAPTURE_SHAPE_INVALID")

    required: set[str] = set()
    try:
        closures, selected, _ = _select_original_worker_sources(
            index, hard_edges, source_selection
        )
    except (AttributeError, TypeError, ValueError) as exc:
        if source_selection == _HARD_ONLY and str(exc) == "CLOSURE_MODULE_LIMIT":
            return unavailable("CLOSURE_MODULE_LIMIT")
        return unavailable("SOURCE_SELECTION_INVALID:" + str(exc))
    components = tuple(closure.members for closure in closures)
    for closure in closures:
        required.update(closure.evidence_source_modules)
        if len(required) > _MAX_MODULES:
            return unavailable("CLOSURE_MODULE_LIMIT")

    if source_selection == _OPTIONAL_NAMED_CHILDREN and (
        set(snapshots) != set(selected) or set(modes) != set(selected)
    ):
        return unavailable("CLOSURE_CAPTURE_SET_MISMATCH")
    for module_id in selected:
        if module_id not in index.modules:
            return unavailable("CLOSURE_MODULE_NOT_INDEXED:" + module_id)
        if module_id not in snapshots or module_id not in modes:
            return unavailable("CLOSURE_CAPTURE_MISSING:" + module_id)

    selected_snapshots: dict[str, SourceSnapshot] = {}
    selected_modes: dict[str, str] = {}
    if source_selection == _OPTIONAL_NAMED_CHILDREN:
        from contextor.core.source import parse_source_snapshot
        from contextor.core.symbol_engine.indexer import read_imports

    total = 0
    for module_id in selected:
        snapshot = snapshots[module_id]
        if type(snapshot) is not SourceSnapshot or type(snapshot.raw) is not bytes:
            return unavailable("CLOSURE_SOURCE_INVALID:" + module_id)
        if len(snapshot.raw) > _MAX_SOURCE_BYTES:
            return unavailable("CLOSURE_SOURCE_BYTE_LIMIT:" + module_id)
        total += len(snapshot.raw)
        if total > _MAX_TOTAL_BYTES:
            return unavailable("CLOSURE_TOTAL_BYTE_LIMIT")
        indexed_hash = index.source_fingerprints_by_module.get(module_id)
        if (
            type(indexed_hash) is not str
            or snapshot.source_fingerprint != indexed_hash
            or hashlib.sha256(snapshot.raw).hexdigest() != indexed_hash
        ):
            return unavailable("CLOSURE_SOURCE_DIGEST_MISMATCH:" + module_id)
        mode = modes[module_id]
        if type(mode) is not str or mode not in _ACCEPTED_MODES:
            return unavailable("CLOSURE_AST_MODE_INVALID:" + module_id)
        if source_selection == _OPTIONAL_NAMED_CHILDREN:
            from pathlib import Path

            try:
                path = Path(index.modules[module_id].absolute_path)
                parsed = parse_source_snapshot(snapshot, path)
                replayed, error = read_imports(path, tree=parsed.tree)
            except (SourceError, SyntaxError, RecursionError):
                return unavailable("CLOSURE_IMPORT_REPLAY_UNAVAILABLE:" + module_id)
            if replayed is None or error is not None:
                return unavailable("CLOSURE_IMPORT_REPLAY_UNAVAILABLE:" + module_id)
            if replayed != index.modules[module_id].imports:
                return unavailable("CLOSURE_IMPORT_FACTS_MISMATCH:" + module_id)
        selected_snapshots[module_id] = snapshot
        selected_modes[module_id] = mode

    return OriginalWorkerCycleClosureBinding(
        status="SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC",
        reason=None,
        cyclic_components=components,
        reachable_modules=selected,
        source_snapshots=selected_snapshots,
        ast_modes=tuple(sorted(selected_modes.items())),
        retained_raw_bytes=total,
    )
