"""Prepared source manifests for cyclic SCC model evidence.

The manifest binds graph identity, reachable source fingerprints,
AST fingerprints and successful P1B assessments. Preparation is
not canonical publication, atomic source capture or runtime safety.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.source import SourceSnapshot

from .contracts import (
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from .evidence import OPTIONAL_EVIDENCE_SEMANTIC_VERSION, SourceBoundCycleEvidence
from .source_proof import (
    assess_scc_source_bytes,
    assess_optional_scc_source_bytes,
)
from .model_source_closure import CycleModelSourceClosure
from .evidence import _scenario_fingerprint


MANIFEST_VERSION = "cycle-source-manifest/2"
OPTIONAL_MANIFEST_VERSION = "cycle-source-manifest/3"
_AUTHORITY = "PREPARED_ONLY_NOT_CANONICALLY_PUBLISHED"


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class PreparedSCCSourceBinding:
    members: tuple[str, ...]
    source_signatures: tuple[tuple[str, str, str], ...]
    model_classification: str
    preparation_state: str
    reason: str | None
    model_kind: str = "FLAT_MODULE"
    model_evidence_sha256: str | None = None


@dataclass(frozen=True)
class OptionalManifestEvidenceWitness:
    evidence_semantic_version: str
    source_manifest_fingerprint: str
    component_evidence_tokens: tuple[str, ...]


@dataclass(frozen=True)
class PreparedCycleSourceManifest:
    graph_sha256: str
    source_manifest_sha256: str | None
    components: tuple[PreparedSCCSourceBinding, ...]
    version: str = MANIFEST_VERSION
    authority: str = _AUTHORITY
    source_selection: str = "HARD_ONLY"
    optional_witness: OptionalManifestEvidenceWitness | None = None


def prepare_cycle_source_manifest(
    hard_edges: Mapping[str, object],
    indexed_fingerprints_by_module: Mapping[str, str],
    snapshot: CycleSemanticsSnapshot,
    source_evidence: SourceBoundCycleEvidence,
    source_snapshots: Mapping[str, SourceSnapshot],
    *,
    max_source_bytes: int = 2 * 1024 * 1024,
    max_closure_bytes: int = 32 * 1024 * 1024,
    source_selection: str = "HARD_ONLY",
    indexed_imports_by_module: Mapping[str, object] | None = None,
    package_root: str | None = None,
    source_closures: tuple[CycleModelSourceClosure, ...] | None = None,
) -> PreparedCycleSourceManifest:
    """Prepare immutable source evidence without publication.

    P1B owns byte-to-AST consistency and source budget checks.
    This operation never asserts that a canonical owner accepted
    these inputs or that they belong to a published revision.
    """
    graph_hash = fingerprint_hard_edges(hard_edges)

    if source_selection == "HARD_ONLY":
        if (
            indexed_imports_by_module is not None
            or package_root is not None
            or source_closures is not None
        ):
            raise ValueError("HARD_ONLY_OPTIONAL_INPUTS_UNSUPPORTED")

        manifest_version = MANIFEST_VERSION
        checks = assess_scc_source_bytes(
            hard_edges,
            indexed_fingerprints_by_module,
            snapshot,
            source_evidence,
            source_snapshots,
            max_source_bytes=max_source_bytes,
            max_closure_bytes=max_closure_bytes,
        )

    elif source_selection == "OPTIONAL_NAMED_CHILDREN":
        if (
            type(source_evidence) is not SourceBoundCycleEvidence
            or not isinstance(indexed_imports_by_module, Mapping)
            or type(source_closures) is not tuple
            or not source_closures
        ):
            raise ValueError("OPTIONAL_MANIFEST_INPUT_INVALID")

        manifest_version = OPTIONAL_MANIFEST_VERSION

        checks = assess_optional_scc_source_bytes(
            hard_edges,
            indexed_fingerprints_by_module,
            snapshot,
            source_evidence,
            source_snapshots,
            indexed_imports_by_module,
            package_root=package_root,
            source_closures=source_closures,
            max_source_bytes=max_source_bytes,
            max_closure_bytes=max_closure_bytes,
        )

        if (
            len(source_evidence.components) != len(checks)
            or len(source_evidence.scenarios.components) != len(checks)
        ):
            raise ValueError("OPTIONAL_MANIFEST_COMPONENT_IDENTITY_MISMATCH")

    else:
        raise ValueError("SOURCE_SELECTION_INVALID")

    prepared: list[PreparedSCCSourceBinding] = []
    accepted_signatures: dict[str, tuple[str, str]] = {}
    all_complete = bool(checks)

    for position, check in enumerate(checks):
        complete = (
            check.bytes_state == "BYTE_AST_CONSISTENT_NON_ATOMIC"
            and check.authority
            == "CALLER_SUPPLIED_BYTES_NOT_ATOMICALLY_BOUND_TO_LIVE"
            and check.model_classification
            in {
                "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
                "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
            }
        )

        if not complete:
            all_complete = False
            prepared.append(PreparedSCCSourceBinding(
                members=check.members,
                source_signatures=(),
                model_classification="INDETERMINATE",
                preparation_state="UNAVAILABLE",
                reason=check.reason or "P1B_EVIDENCE_UNAVAILABLE",
                model_kind=source_evidence.scenarios.components[position].model_kind,
                model_evidence_sha256=None,
            ))
            continue

        source_component = source_evidence.components[position]

        # P1B has already validated the exact component,
        # its reachable closure, source hashes and AST hashes.
        signatures = source_component.source_signatures

        conflict = next((
            module
            for module, raw_hash, ast_hash in signatures
            if (
                module in accepted_signatures
                and accepted_signatures[module]
                != (raw_hash, ast_hash)
            )
        ), None)

        if conflict is not None:
            all_complete = False
            prepared.append(PreparedSCCSourceBinding(
                members=check.members,
                source_signatures=(),
                model_classification="INDETERMINATE",
                preparation_state="UNAVAILABLE",
                reason="SOURCE_MANIFEST_CONFLICT:" + conflict,
                model_kind=source_evidence.scenarios.components[position].model_kind,
                model_evidence_sha256=None,
            ))
            continue

        for module, raw_hash, ast_hash in signatures:
            accepted_signatures[module] = (raw_hash, ast_hash)

        prepared.append(PreparedSCCSourceBinding(
            members=check.members,
            source_signatures=signatures,
            model_classification=check.model_classification,
            preparation_state="PREPARED_UNPUBLISHED",
            reason=None,
            model_kind=source_evidence.scenarios.components[position].model_kind,
            model_evidence_sha256=_scenario_fingerprint(
                source_evidence.scenarios.components[position]
            ),
        ))

    # A global manifest digest must not imply completeness
    # when even one SCC lacks sufficient evidence.
    optional_witness: OptionalManifestEvidenceWitness | None = None

    if all_complete:
        ordered_sources = tuple(
            (module, *accepted_signatures[module])
            for module in sorted(accepted_signatures)
        )
        if source_selection == "HARD_ONLY":
            manifest_hash: str | None = _digest((
                MANIFEST_VERSION,
                graph_hash,
                tuple((
                    component.members,
                    component.model_classification,
                    component.model_kind,
                    component.model_evidence_sha256,
                    component.source_signatures,
                ) for component in prepared),
                ordered_sources,
            ))
        else:
            optional_witness = OptionalManifestEvidenceWitness(
                evidence_semantic_version=source_evidence.semantic_version,
                source_manifest_fingerprint=(
                    source_evidence.source_manifest_fingerprint
                ),
                component_evidence_tokens=tuple(
                    component.evidence_token
                    for component in source_evidence.components
                ),
            )
            manifest_hash = _digest((
                OPTIONAL_MANIFEST_VERSION,
                "OPTIONAL_NAMED_CHILDREN",
                optional_witness.evidence_semantic_version,
                graph_hash,
                optional_witness.source_manifest_fingerprint,
                tuple((
                    component.members,
                    component.model_classification,
                    component.model_kind,
                    component.model_evidence_sha256,
                    component.source_signatures,
                    optional_witness.component_evidence_tokens[position],
                ) for position, component in enumerate(prepared)),
                ordered_sources,
            ))
    else:
        manifest_hash = None

    return PreparedCycleSourceManifest(
        graph_sha256=graph_hash,
        source_manifest_sha256=manifest_hash,
        components=tuple(prepared),
        version=manifest_version,
        source_selection=source_selection,
        optional_witness=optional_witness,
    )


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def verify_prepared_optional_manifest_digest(
    manifest: object,
) -> bool:
    """Replay a v3 declaration digest without certifying source origin.

    The witness makes the digest reproducible from the manifest.
    This validates internal consistency of caller-supplied declarations.
    It does not authenticate source bytes, canonical ownership or LIVE.
    """
    if type(manifest) is not PreparedCycleSourceManifest:
        return False

    witness = manifest.optional_witness
    components = manifest.components

    if (
        manifest.version != OPTIONAL_MANIFEST_VERSION
        or manifest.source_selection != "OPTIONAL_NAMED_CHILDREN"
        or manifest.authority != _AUTHORITY
        or not _is_sha256(manifest.graph_sha256)
        or not _is_sha256(manifest.source_manifest_sha256)
        or type(witness) is not OptionalManifestEvidenceWitness
        or witness.evidence_semantic_version
        != OPTIONAL_EVIDENCE_SEMANTIC_VERSION
        or not _is_sha256(witness.source_manifest_fingerprint)
        or type(components) is not tuple
        or not components
        or type(witness.component_evidence_tokens) is not tuple
        or len(witness.component_evidence_tokens) != len(components)
        or any(
            not _is_sha256(token)
            for token in witness.component_evidence_tokens
        )
    ):
        return False

    accepted: dict[str, tuple[str, str]] = {}

    for component in components:
        if type(component) is not PreparedSCCSourceBinding:
            return False

        if (
            type(component.members) is not tuple
            or not component.members
            or any(
                type(name) is not str or not name
                for name in component.members
            )
            or component.members != tuple(sorted(set(component.members)))
            or component.preparation_state != "PREPARED_UNPUBLISHED"
            or component.reason is not None
            or type(component.model_classification) is not str
            or component.model_classification not in {
                "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS",
                "MODEL_INTERNAL_EARLY_BINDING_HAZARD",
            }
            or type(component.model_kind) is not str
            or component.model_kind not in {
                "FLAT_MODULE",
                "REGULAR_PACKAGE",
            }
            or not _is_sha256(component.model_evidence_sha256)
            or type(component.source_signatures) is not tuple
            or not component.source_signatures
        ):
            return False

        names: list[str] = []

        for row in component.source_signatures:
            if type(row) is not tuple or len(row) != 3:
                return False

            module, raw_sha256, ast_sha256 = row

            if (
                type(module) is not str
                or not module
                or not _is_sha256(raw_sha256)
                or not _is_sha256(ast_sha256)
            ):
                return False

            names.append(module)
            signature = (raw_sha256, ast_sha256)

            if module in accepted and accepted[module] != signature:
                return False

            accepted[module] = signature

        if tuple(names) != tuple(sorted(set(names))):
            return False

    ordered_sources = tuple(
        (module, *accepted[module])
        for module in sorted(accepted)
    )

    if (
        witness.source_manifest_fingerprint
        != _digest(ordered_sources)
    ):
        return False

    expected = _digest((
        OPTIONAL_MANIFEST_VERSION,
        "OPTIONAL_NAMED_CHILDREN",
        witness.evidence_semantic_version,
        manifest.graph_sha256,
        witness.source_manifest_fingerprint,
        tuple((
            component.members,
            component.model_classification,
            component.model_kind,
            component.model_evidence_sha256,
            component.source_signatures,
            witness.component_evidence_tokens[position],
        ) for position, component in enumerate(components)),
        ordered_sources,
    ))

    return expected == manifest.source_manifest_sha256
