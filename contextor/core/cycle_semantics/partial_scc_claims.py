"""Pure validation of declared, uncommitted per-SCC preparations.

This does not authenticate source bytes, publication, or runtime safety.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import CycleSemanticsSnapshot, fingerprint_hard_edges
from .generation_manifest import (
    MANIFEST_VERSION,
    PreparedCycleSourceManifest,
    PreparedSCCSourceBinding,
)
from .model_source_closure import compute_cycle_model_source_closures
from .original_worker_preparation import OriginalWorkerManifestPreparation
from .scc import analyze_import_cycle_topology


PARTIAL_SCC_CLAIMS_VERSION = "cycle-partial-scc-preparation/1"
PARTIAL_SCC_CLAIMS_AUTHORITY = (
    "DECLARED_PREPARATIONS_NOT_COMMITTED_NOT_SOURCE_CERTIFIED"
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class PreparedPartialSCCClaims:
    graph_sha256: str
    components: tuple[PreparedSCCSourceBinding, ...]
    version: str = PARTIAL_SCC_CLAIMS_VERSION
    authority: str = PARTIAL_SCC_CLAIMS_AUTHORITY


def validate_partial_scc_claims(
    hard_edges,
    snapshot,
    preparation,
) -> PreparedPartialSCCClaims | None:
    """Check supplied graph, snapshot and preparation declarations only."""
    if (
        type(snapshot) is not CycleSemanticsSnapshot
        or type(preparation) is not OriginalWorkerManifestPreparation
        or snapshot.coverage_status != "FILESYSTEM_STABLE_NON_ATOMIC"
        or snapshot.source_issues
    ):
        return None

    try:
        graph_sha256 = fingerprint_hard_edges(hard_edges)
        topology = analyze_import_cycle_topology(hard_edges)
        closures = compute_cycle_model_source_closures(hard_edges)
        expected_source_modules = tuple(sorted({
            module_id
            for closure in closures
            for module_id in closure.evidence_source_modules
        }))
        components = topology.cyclic_components
        cyclic_members = tuple(sorted(
            member for component in components for member in component.members
        ))
        observed_rows = snapshot.observed_source_fingerprints
        if (
            not components
            or graph_sha256 != snapshot.graph_sha256
            or snapshot.import_sites.topology != topology
            or snapshot.cyclic_modules != cyclic_members
            or type(observed_rows) is not tuple
            or any(
                type(row) is not tuple or len(row) != 2
                or type(row[0]) is not str or not row[0]
                or type(row[1]) is not str
                or _SHA256_PATTERN.fullmatch(row[1]) is None
                for row in observed_rows
            )
        ):
            return None
        observed = dict(observed_rows)
        if (
            len(observed_rows) != len(cyclic_members)
            or tuple(sorted(observed)) != cyclic_members
        ):
            return None

        declarations = preparation.component_preparations
        if (
            type(declarations) is not tuple
            or len(declarations) != len(components)
            or any(type(item) is not PreparedSCCSourceBinding for item in declarations)
            or tuple(item.members for item in declarations)
            != tuple(component.members for component in components)
        ):
            return None

        if preparation.status == "PREPARED_UNPUBLISHED_NON_ATOMIC":
            manifest = preparation.manifest
            if (
                preparation.reason is not None
                or type(preparation.source_modules) is not tuple
                or preparation.source_modules != expected_source_modules
                or type(manifest) is not PreparedCycleSourceManifest
                or manifest.components != declarations
                or manifest.version != MANIFEST_VERSION
                or manifest.authority
                != "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"
                or manifest.graph_sha256 != snapshot.graph_sha256
                or type(manifest.source_manifest_sha256) is not str
                or _SHA256_PATTERN.fullmatch(manifest.source_manifest_sha256) is None
                or any(item.preparation_state != "PREPARED_UNPUBLISHED"
                       for item in declarations)
            ):
                return None
        elif preparation.status == "UNAVAILABLE":
            if (
                preparation.reason != "P1C0_SOURCE_EVIDENCE_UNAVAILABLE"
                or preparation.manifest is not None
                or preparation.source_modules != ()
                or not any(item.preparation_state == "UNAVAILABLE"
                           for item in declarations)
            ):
                return None
        else:
            return None

        shared_signatures: dict[str, tuple[str, str]] = {}
        for structural, closure, item in zip(components, closures, declarations):
            if item.members != structural.members or closure.members != structural.members:
                return None
            if item.preparation_state == "PREPARED_UNPUBLISHED":
                if (
                    item.reason is not None
                    or item.model_classification not in {
                        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
                        "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
                    }
                    or item.model_kind not in {"FLAT_MODULE", "REGULAR_PACKAGE"}
                    or type(item.model_evidence_sha256) is not str
                    or _SHA256_PATTERN.fullmatch(item.model_evidence_sha256) is None
                    or type(item.source_signatures) is not tuple
                ):
                    return None
                rows = item.source_signatures
                if any(
                    type(row) is not tuple or len(row) != 3
                    or type(row[0]) is not str or not row[0]
                    or type(row[1]) is not str
                    or _SHA256_PATTERN.fullmatch(row[1]) is None
                    or type(row[2]) is not str
                    or _SHA256_PATTERN.fullmatch(row[2]) is None
                    for row in rows
                ):
                    return None
                if tuple(row[0] for row in rows) != closure.evidence_source_modules:
                    return None
                for module_id, raw_sha256, ast_sha256 in rows:
                    if module_id in observed and observed[module_id] != raw_sha256:
                        return None
                    signature = (raw_sha256, ast_sha256)
                    if (
                        module_id in shared_signatures
                        and shared_signatures[module_id] != signature
                    ):
                        return None
                    shared_signatures[module_id] = signature
            elif item.preparation_state == "UNAVAILABLE":
                if (
                    item.model_classification != "INDETERMINATE"
                    or type(item.model_kind) is not str
                    or item.model_kind not in {"FLAT_MODULE", "REGULAR_PACKAGE"}
                    or type(item.reason) is not str or not item.reason
                    or item.source_signatures != ()
                    or item.model_evidence_sha256 is not None
                ):
                    return None
            else:
                return None

        return PreparedPartialSCCClaims(
            graph_sha256=snapshot.graph_sha256,
            components=declarations,
        )
    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
        return None
