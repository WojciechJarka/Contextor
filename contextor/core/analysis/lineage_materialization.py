"""Pure deterministic materialization of one lineage source slice."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from contextor.core.analysis.lineage_extraction_contracts import (
    _module_name_from_source_key,
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
    SemanticAnchorBinding,
    SemanticEndpoint,
    SemanticEndpointOrigin,
    SemanticEndpointRole,
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


class LineageOriginUnavailableError(ValueError):
    """A legacy semantic endpoint cannot be safely re-resolved."""


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
    origins: list[SemanticEndpointOrigin] = []

    def endpoint(
        reference: ExtractedOccurrenceRef | ExtractedSymbolicRef,
        kind: ResolutionKind,
        confidence: LineageConfidence,
        fact_local_id: str,
        endpoint_role: SemanticEndpointRole,
    ) -> MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint:
        if isinstance(reference, ExtractedOccurrenceRef):
            return occurrence(reference.local_id)
        resolved = _symbolic_endpoint(
            reference,
            resolution,
            descriptors,
            kind,
            confidence,
            extracted.source_key,
            extracted.source_fingerprint,
        )
        if isinstance(resolved, SemanticEndpoint):
            origins.append(
                _semantic_origin(
                    reference,
                    extracted.source_key,
                    extracted.source_fingerprint,
                    fact_local_id,
                    endpoint_role,
                )
            )
        return resolved
    anchors = tuple(
        sorted(
            MaterializedAnchorFact(
                anchor.local_id, occurrence(anchor.local_id), anchor.kind, anchor.span
            )
            for anchor in extracted.anchors
        )
    )
    semantic_anchors = _semantic_anchor_bindings(
        extracted,
        resolution,
        occurrence,
    )
    flows = tuple(sorted(
        MaterializedFlowFact(
            flow.local_id,
            endpoint(
                flow.source,
                flow.resolution_kind,
                flow.confidence,
                flow.local_id,
                SemanticEndpointRole.FLOW_SOURCE,
            ),
            endpoint(
                flow.target,
                flow.resolution_kind,
                flow.confidence,
                flow.local_id,
                SemanticEndpointRole.FLOW_TARGET,
            ),
            flow.relation,
            flow.evidence,
            flow.resolution_kind,
            flow.confidence,
            flow.dynamic_boundary,
            flow.provider,
        )
        for flow in extracted.flows
    ))
    surfaces = tuple(sorted(
        MaterializedSurfaceFact(
            surface.local_id,
            surface.kind,
            endpoint(
                surface.exposed,
                surface.resolution_kind,
                surface.confidence,
                surface.local_id,
                SemanticEndpointRole.SURFACE_EXPOSED,
            ),
            surface.evidence,
            surface.resolution_kind,
            surface.confidence,
            surface.declared_name,
            surface.dynamic_boundary,
            surface.provider,
            surface.declaration_evidence,
        )
        for surface in extracted.surfaces
    ))
    manifest = SourceLineageManifest(
        extracted.source_key,
        extracted.source_fingerprint,
        LINEAGE_FACTS_SEMANTIC_VERSION,
        extracted.status,
        len(anchors),
        len(flows),
        len(surfaces),
        extracted.resource_limit_reason,
        semantic_anchor_bindings_materialized=True,
    )
    return MaterializedLineageSourceFacts(
        manifest,
        anchors,
        flows,
        surfaces,
        tuple(sorted(descriptors.values())),
        tuple(sorted(origins)),
        semantic_anchors,
    )


def reresolve_materialized_lineage_source_facts(
    materialized: MaterializedLineageSourceFacts,
    resolution: LineageResolutionContext,
) -> MaterializedLineageSourceFacts:
    """Re-resolve one canonical slice without source, AST, or extracted facts."""

    if not isinstance(materialized, MaterializedLineageSourceFacts):
        raise TypeError("materialized must be MaterializedLineageSourceFacts.")
    if not isinstance(resolution, LineageResolutionContext):
        raise TypeError("resolution must be LineageResolutionContext.")

    origins = {
        (origin.fact_local_id, origin.endpoint_role): origin
        for origin in materialized.semantic_endpoint_origins
    }
    descriptors: dict[str, SemanticInterfaceDescriptor] = {}
    resolved_origins: list[SemanticEndpointOrigin] = []

    def endpoint(
        current: MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint,
        resolution_kind: ResolutionKind,
        confidence: LineageConfidence,
        fact_local_id: str,
        endpoint_role: SemanticEndpointRole,
    ) -> MaterializedOccurrenceRef | MaterializedSymbolicRef | SemanticEndpoint:
        if isinstance(current, MaterializedOccurrenceRef):
            return current
        if isinstance(current, MaterializedSymbolicRef):
            reference = ExtractedSymbolicRef(
                current.kind,
                current.module_name,
                current.symbol_name,
                current.source_local_id,
            )
            source_key = current.source_key
            source_fingerprint = current.source_fingerprint
        else:
            origin = origins.get((fact_local_id, endpoint_role))
            if origin is None:
                raise LineageOriginUnavailableError(
                    "Semantic endpoint is missing compact symbolic origin."
                )
            reference = ExtractedSymbolicRef(
                origin.kind,
                origin.module_name,
                origin.symbol_name,
                origin.source_local_id,
            )
            source_key = origin.source_key
            source_fingerprint = origin.source_fingerprint
        resolved = _symbolic_endpoint(
            reference,
            resolution,
            descriptors,
            resolution_kind,
            confidence,
            source_key,
            source_fingerprint,
        )
        if isinstance(resolved, SemanticEndpoint):
            resolved_origins.append(
                _semantic_origin(
                    reference,
                    source_key,
                    source_fingerprint,
                    fact_local_id,
                    endpoint_role,
                )
            )
        return resolved

    flows = tuple(sorted(
        MaterializedFlowFact(
            flow.local_id,
            endpoint(
                flow.source,
                flow.resolution_kind,
                flow.confidence,
                flow.local_id,
                SemanticEndpointRole.FLOW_SOURCE,
            ),
            endpoint(
                flow.target,
                flow.resolution_kind,
                flow.confidence,
                flow.local_id,
                SemanticEndpointRole.FLOW_TARGET,
            ),
            flow.relation,
            flow.evidence,
            flow.resolution_kind,
            flow.confidence,
            flow.dynamic_boundary,
            flow.provider,
        )
        for flow in materialized.flows
    ))
    surfaces = tuple(sorted(
        MaterializedSurfaceFact(
            surface.local_id,
            surface.kind,
            endpoint(
                surface.exposed,
                surface.resolution_kind,
                surface.confidence,
                surface.local_id,
                SemanticEndpointRole.SURFACE_EXPOSED,
            ),
            surface.evidence,
            surface.resolution_kind,
            surface.confidence,
            surface.declared_name,
            surface.dynamic_boundary,
            surface.provider,
            surface.declaration_evidence,
        )
        for surface in materialized.surfaces
    ))
    semantic_anchors = tuple(
        sorted(
            SemanticAnchorBinding(
                owner_id,
                binding.qualified_name,
                binding.reference,
            )
            for binding in materialized.semantic_anchors
            if (
                owner_id := resolution.active_artifact_ids.get(
                    binding.qualified_name
                )
            )
            is not None
        )
    )
    return MaterializedLineageSourceFacts(
        materialized.manifest,
        materialized.anchors,
        flows,
        surfaces,
        tuple(sorted(descriptors.values())),
        tuple(sorted(resolved_origins)),
        semantic_anchors,
    )


def _semantic_anchor_bindings(
    extracted: ExtractedLineageSourceFacts,
    resolution: LineageResolutionContext,
    occurrence,
) -> tuple[SemanticAnchorBinding, ...]:
    anchors_by_id = {
        anchor.local_id: anchor
        for anchor in extracted.anchors
    }
    module_name = _module_name_from_source_key(extracted.source_key)
    result: list[SemanticAnchorBinding] = []

    for anchor in extracted.anchors:
        if anchor.kind not in {
            "class",
            "function",
            "async_function",
            "binding",
            "import_binding",
        }:
            continue

        symbol_path = _anchor_symbol_path(anchor, anchors_by_id)
        if symbol_path is None:
            continue

        qualified_name = f"{module_name}::{symbol_path}"
        owner_id = resolution.active_artifact_ids.get(qualified_name)
        if owner_id is None:
            continue

        result.append(
            SemanticAnchorBinding(
                owner_id,
                qualified_name,
                occurrence(anchor.local_id),
            )
        )

    return tuple(sorted(result))


def _anchor_symbol_path(anchor, anchors_by_id) -> str | None:
    parts: list[str] = []
    current = anchor
    seen: set[str] = set()

    while current.kind != "module":
        if current.local_id in seen:
            raise ValueError("Lineage anchor ownership contains a cycle.")
        seen.add(current.local_id)

        try:
            _kind, _path, _ordinal, name = parse_local_occurrence_id(
                current.local_id
            )
        except ValueError:
            return None
        if not name:
            return None
        parts.append(name)

        owner_local_id = current.owner_local_id
        if owner_local_id is None:
            return None
        current = anchors_by_id.get(owner_local_id)
        if current is None:
            return None

    return ".".join(reversed(parts))


def _semantic_origin(
    reference: ExtractedSymbolicRef,
    source_key: str,
    source_fingerprint: str,
    fact_local_id: str,
    endpoint_role: SemanticEndpointRole,
) -> SemanticEndpointOrigin:
    return SemanticEndpointOrigin(
        source_key,
        source_fingerprint,
        fact_local_id,
        endpoint_role,
        reference.kind,
        reference.module_name,
        reference.symbol_name,
        reference.source_local_id,
    )


def _symbolic_endpoint(
    reference: ExtractedSymbolicRef,
    resolution: LineageResolutionContext,
    descriptors: dict[str, SemanticInterfaceDescriptor],
    resolution_kind: ResolutionKind,
    confidence: LineageConfidence,
    source_key: str,
    source_fingerprint: str,
) -> MaterializedSymbolicRef | SemanticEndpoint:
    symbolic = MaterializedSymbolicRef(
        source_key, source_fingerprint, reference.kind,
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
