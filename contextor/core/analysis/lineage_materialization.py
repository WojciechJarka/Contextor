"""Pure deterministic materialization of one lineage source slice."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from urllib.parse import quote

from contextor.core.analysis.lineage_extraction_contracts import (
    parse_local_occurrence_id,
)
from contextor.core.domain.lineage_facts import (
    LINEAGE_FACTS_SEMANTIC_VERSION,
    ExtractedLineageSourceFacts,
    ExtractedOccurrenceRef,
    ExtractedSymbolicKind,
    ExtractedSymbolicRef,
    LineageConfidence,
    MaterializedAnchorFact,
    MaterializedFlowFact,
    MaterializedLineageSourceFacts,
    MaterializedOccurrenceRef,
    MaterializedSymbolicRef,
    MaterializedSurfaceFact,
    ParameterKind,
    ResolutionKind,
    SemanticEndpoint,
    SemanticInterfaceDescriptor,
    SourceLineageManifest,
    build_module_global_slot,
    build_parameter_value_slot,
    build_return_slot,
    claims_exact_semantic_target,
)


@dataclass(frozen=True)
class LineageResolutionContext:
    """Narrow read-only evidence of currently active canonical identities."""

    active_module_ids: Mapping[str, str]
    active_artifact_ids: Mapping[str, str]
    active_owner_ids: frozenset[str]
    interface_descriptors: Mapping[str, SemanticInterfaceDescriptor]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "active_module_ids", MappingProxyType(dict(self.active_module_ids))
        )
        object.__setattr__(
            self, "active_artifact_ids", MappingProxyType(dict(self.active_artifact_ids))
        )
        object.__setattr__(
            self,
            "interface_descriptors",
            MappingProxyType(dict(self.interface_descriptors)),
        )
        for owner_id in (
            *self.active_module_ids.values(),
            *self.active_artifact_ids.values(),
        ):
            if owner_id not in self.active_owner_ids:
                raise ValueError(
                    "Resolution mappings must contain only active owner ids."
                )
        for owner_id, descriptor in self.interface_descriptors.items():
            if owner_id != descriptor.owner_id or owner_id not in self.active_owner_ids:
                raise ValueError(
                    "Interface descriptors must belong to active owners."
                )


def materialize_lineage_source_facts(
    extracted: ExtractedLineageSourceFacts,
    resolution: LineageResolutionContext,
) -> MaterializedLineageSourceFacts:
    """Convert one extracted slice without I/O, allocation, or mutation."""

    if not isinstance(extracted, ExtractedLineageSourceFacts):
        raise TypeError("extracted must be ExtractedLineageSourceFacts.")
    if not isinstance(resolution, LineageResolutionContext):
        raise TypeError("resolution must be LineageResolutionContext.")

    def occurrence(local_id: str) -> MaterializedOccurrenceRef:
        return MaterializedOccurrenceRef(
            extracted.source_key, extracted.source_fingerprint, local_id
        )

    descriptors: dict[str, SemanticInterfaceDescriptor] = {}

    def endpoint(
        reference: ExtractedOccurrenceRef | ExtractedSymbolicRef,
        kind: ResolutionKind,
        confidence: LineageConfidence,
    ) -> MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint:
        if isinstance(reference, ExtractedOccurrenceRef):
            return occurrence(reference.local_id)
        return _symbolic_endpoint(
            reference, resolution, descriptors, kind, confidence, extracted
        )
    anchors = tuple(
        sorted(
            MaterializedAnchorFact(
                anchor.local_id, occurrence(anchor.local_id), anchor.kind, anchor.span
            )
            for anchor in extracted.anchors
        )
    )
    flows = tuple(
        sorted(
            MaterializedFlowFact(
                flow.local_id,
                endpoint(flow.source, flow.resolution_kind, flow.confidence),
                endpoint(flow.target, flow.resolution_kind, flow.confidence),
                flow.relation,
                flow.evidence,
                flow.resolution_kind,
                flow.confidence,
                flow.dynamic_boundary,
                flow.provider,
            )
            for flow in extracted.flows
        )
    )
    surfaces = tuple(
        sorted(
            MaterializedSurfaceFact(
                surface.local_id,
                surface.kind,
                endpoint(surface.exposed, surface.resolution_kind, surface.confidence),
                surface.evidence,
                surface.resolution_kind,
                surface.confidence,
                surface.declared_name,
                surface.dynamic_boundary,
                surface.provider,
                surface.declaration_evidence,
            )
            for surface in extracted.surfaces
        )
    )
    manifest = SourceLineageManifest(
        extracted.source_key,
        extracted.source_fingerprint,
        LINEAGE_FACTS_SEMANTIC_VERSION,
        extracted.status,
        len(anchors),
        len(flows),
        len(surfaces),
        extracted.resource_limit_reason,
    )
    return MaterializedLineageSourceFacts(
        manifest, anchors, flows, surfaces, tuple(sorted(descriptors.values()))
    )


def _symbolic_endpoint(
    reference: ExtractedSymbolicRef,
    resolution: LineageResolutionContext,
    descriptors: dict[str, SemanticInterfaceDescriptor],
    resolution_kind: ResolutionKind,
    confidence: LineageConfidence,
    extracted: ExtractedLineageSourceFacts,
) -> MaterializedSymbolicRef | SemanticEndpoint:
    symbolic = MaterializedSymbolicRef(
        extracted.source_key, extracted.source_fingerprint, reference.kind,
        reference.module_name, reference.symbol_name, reference.source_local_id,
    )
    if not claims_exact_semantic_target(resolution_kind, confidence):
        return symbolic
    owner_id = (
        resolution.active_module_ids.get(reference.module_name)
        if reference.kind is ExtractedSymbolicKind.STATE
        else resolution.active_artifact_ids.get(reference.qualified_name)
    )
    if owner_id is None:
        return symbolic
    slot = _slot_for(reference, owner_id)
    if slot is not None:
        descriptor = resolution.interface_descriptors.get(owner_id)
        if descriptor is None or slot not in descriptor.slots:
            return symbolic
        descriptors[owner_id] = descriptor
    return SemanticEndpoint(owner_id, slot)


def _slot_for(reference: ExtractedSymbolicRef, owner_id: str) -> str | None:
    if reference.kind is ExtractedSymbolicKind.RETURN:
        return build_return_slot(owner_id)
    if reference.kind is ExtractedSymbolicKind.STATE:
        return build_module_global_slot(owner_id, reference.symbol_name)
    if reference.kind is not ExtractedSymbolicKind.PARAMETER:
        return None
    if reference.source_local_id is None:
        raise ValueError("Parameter symbolic reference requires source_local_id.")
    local_kind, _path, ordinal, name = parse_local_occurrence_id(
        reference.source_local_id
    )
    parameter_kinds = {
        "parameter_posonly": ParameterKind.POSITIONAL_ONLY,
        "parameter_poskw": ParameterKind.POSITIONAL_OR_KEYWORD,
        "parameter_vararg": ParameterKind.VAR_POSITIONAL,
        "parameter_kwonly": ParameterKind.KEYWORD_ONLY,
        "parameter_varkw": ParameterKind.VAR_KEYWORD,
    }
    try:
        kind = parameter_kinds[local_kind]
    except KeyError as exc:
        raise ValueError(
            "Parameter symbolic reference must point at a parameter local id."
        ) from exc
    return build_parameter_value_slot(owner_id, kind, ordinal=ordinal, name=name)
