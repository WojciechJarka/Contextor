"""Prepare P1C0 evidence from selected original indexer worker bytes.

This is caller-supplied, non-atomic, in-memory evidence preparation.
It does not establish canonical ownership, publication, installed LIVE
identity, original cross-file atomicity, or runtime import safety.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.source import (
    SourceError,
    parse_source_snapshot,
)

from .contracts import CycleSemanticsSnapshot
from .evidence import build_source_bound_cycle_evidence
from .generation_manifest import (
    PreparedCycleSourceManifest,
    PreparedSCCSourceBinding,
    prepare_cycle_source_manifest,
)
from .original_worker_binding import (
    assess_original_worker_cycle_closure,
)


@dataclass(frozen=True)
class OriginalWorkerManifestPreparation:
    status: str
    reason: str | None
    manifest: PreparedCycleSourceManifest | None
    source_modules: tuple[str, ...]
    component_preparations: tuple[PreparedSCCSourceBinding, ...] = ()


def prepare_original_worker_cycle_manifest(
    index: object,
    hard_edges: Mapping[str, object],
    snapshot: CycleSemanticsSnapshot,
) -> OriginalWorkerManifestPreparation:
    """Prepare a non-published manifest from supplied original-worker bytes.

    The existing P1D2B binding owns selection and byte fingerprint checks.
    Existing P0/P1B/P1C0 functions own graph/model, byte/AST and manifest
    consistency checks.

    No filesystem reading, worker execution, canonical mutation, store
    operation, receipt sealing, LIVE IPC or generation certification occurs.
    """

    if type(snapshot) is not CycleSemanticsSnapshot:
        raise TypeError(
            "snapshot must be CycleSemanticsSnapshot"
        )

    def unavailable(
        reason: str,
        *,
        component_preparations: tuple[PreparedSCCSourceBinding, ...] = (),
    ) -> OriginalWorkerManifestPreparation:
        return OriginalWorkerManifestPreparation(
            status="UNAVAILABLE",
            reason=reason,
            manifest=None,
            source_modules=(),
            component_preparations=component_preparations,
        )

    binding = assess_original_worker_cycle_closure(
        index,
        hard_edges,
    )

    if binding.status != (
        "SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC"
    ):
        return unavailable(
            "BINDING_" + (
                binding.reason
                or "UNAVAILABLE"
            )
        )

    try:
        parsed_sources = {
            module_id: parse_source_snapshot(
                binding.source_snapshots[module_id],
                module_id,
            )
            for module_id in binding.reachable_modules
        }
    except (
        SourceError,
        SyntaxError,
        ValueError,
        TypeError,
        RecursionError,
        OverflowError,
    ):
        return unavailable(
            "ORIGINAL_SOURCE_AST_UNAVAILABLE"
        )

    try:
        evidence = build_source_bound_cycle_evidence(
            hard_edges,
            parsed_sources,
        )

        manifest = prepare_cycle_source_manifest(
            hard_edges,
            index.source_fingerprints_by_module,
            snapshot,
            evidence,
            binding.source_snapshots,
        )
    except (
        SourceError,
        SyntaxError,
        ValueError,
        TypeError,
        RecursionError,
        OverflowError,
    ):
        return unavailable(
            "SOURCE_EVIDENCE_PREPARATION_FAILED"
        )

    if (
        type(manifest.source_manifest_sha256) is not str
        or len(manifest.source_manifest_sha256) != 64
        or not manifest.components
        or any(
            component.preparation_state
            != "PREPARED_UNPUBLISHED"
            for component in manifest.components
        )
    ):
        return unavailable(
            "P1C0_SOURCE_EVIDENCE_UNAVAILABLE",
            component_preparations=manifest.components,
        )

    if manifest.authority != (
        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    ):
        return unavailable(
            "PREPARED_AUTHORITY_INVALID"
        )

    if tuple(
        component.members
        for component in manifest.components
    ) != binding.cyclic_components:
        return unavailable(
            "SCC_COMPONENT_IDENTITY_MISMATCH"
        )

    return OriginalWorkerManifestPreparation(
        status="PREPARED_UNPUBLISHED_NON_ATOMIC",
        reason=None,
        manifest=manifest,
        source_modules=binding.reachable_modules,
        component_preparations=manifest.components,
    )
