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

from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
from .evidence import build_source_bound_cycle_evidence
from .generation_manifest import (
    MANIFEST_VERSION,
    OPTIONAL_MANIFEST_VERSION,
    PreparedCycleSourceManifest,
    PreparedSCCSourceBinding,
    prepare_cycle_source_manifest,
)
from .original_worker_binding import (
    _select_original_worker_sources,
    assess_original_worker_cycle_closure,
)


@dataclass(frozen=True)
class OriginalWorkerManifestPreparation:
    status: str
    reason: str | None
    manifest: PreparedCycleSourceManifest | None
    source_modules: tuple[str, ...]
    component_preparations: tuple[PreparedSCCSourceBinding, ...] = ()
    source_selection: str = "HARD_ONLY"


def prepare_original_worker_cycle_manifest(
    index: object,
    hard_edges: Mapping[str, object],
    snapshot: CycleSemanticsSnapshot,
    *,
    source_selection: str = "HARD_ONLY",
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
            source_selection=source_selection,
        )

    if source_selection not in (
        "HARD_ONLY",
        "OPTIONAL_NAMED_CHILDREN",
    ):
        return unavailable("SOURCE_SELECTION_INVALID")

    binding = assess_original_worker_cycle_closure(
        index,
        hard_edges,
        source_selection=source_selection,
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

    mode_kwargs: dict[str, object] = {}

    if source_selection == "OPTIONAL_NAMED_CHILDREN":
        try:
            closures, selected, package_root = (
                _select_original_worker_sources(
                    index,
                    hard_edges,
                    source_selection,
                )
            )
            indexed_imports = {
                name: module.imports
                for name, module in index.modules.items()
            }
        except (AttributeError, TypeError, ValueError, KeyError):
            return unavailable("OPTIONAL_SOURCE_COHORT_UNAVAILABLE")

        if (
            selected != binding.reachable_modules
            or tuple(row.members for row in closures)
            != binding.cyclic_components
        ):
            return unavailable("OPTIONAL_SOURCE_COHORT_MISMATCH")

        mode_kwargs = {
            "source_selection": source_selection,
            "indexed_imports_by_module": indexed_imports,
            "package_root": package_root,
            "source_closures": closures,
        }

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
            **mode_kwargs,
        )

        manifest = prepare_cycle_source_manifest(
            hard_edges,
            index.source_fingerprints_by_module,
            snapshot,
            evidence,
            binding.source_snapshots,
            **mode_kwargs,
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

    if type(manifest) is not PreparedCycleSourceManifest:
        return unavailable(
            "SOURCE_EVIDENCE_PREPARATION_FAILED"
        )

    expected_version = (
        MANIFEST_VERSION
        if source_selection == "HARD_ONLY"
        else OPTIONAL_MANIFEST_VERSION
    )

    if (
        manifest.version != expected_version
        or manifest.source_selection != source_selection
    ):
        return unavailable("SOURCE_MANIFEST_MODE_MISMATCH")

    if manifest.authority != (
        "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
    ):
        return unavailable(
            "PREPARED_AUTHORITY_INVALID"
        )

    if not (
        manifest.graph_sha256
        == snapshot.graph_sha256
        == fingerprint_hard_edges(hard_edges)
    ):
        return unavailable(
            "SOURCE_MANIFEST_GRAPH_MISMATCH"
        )

    if (
        type(manifest.components) is not tuple
        or len(manifest.components) != len(binding.cyclic_components)
        or any(
            type(component) is not PreparedSCCSourceBinding
            for component in manifest.components
        )
    ):
        return unavailable(
            "SCC_COMPONENT_IDENTITY_MISMATCH"
        )

    if tuple(
        component.members
        for component in manifest.components
    ) != binding.cyclic_components:
        return unavailable(
            "SCC_COMPONENT_IDENTITY_MISMATCH"
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

    return OriginalWorkerManifestPreparation(
        status="PREPARED_UNPUBLISHED_NON_ATOMIC",
        reason=None,
        manifest=manifest,
        source_modules=binding.reachable_modules,
        component_preparations=manifest.components,
        source_selection=source_selection,
    )
