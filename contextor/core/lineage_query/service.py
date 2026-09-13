from __future__ import annotations

from dataclasses import dataclass

from contextor.core.domain.lineage_facts import (
    MaterializedFlowFact,
    MaterializedOccurrenceRef,
    MaterializedSurfaceFact,
    SemanticAnchorBinding,
    SemanticEndpoint,
)
from contextor.core.lineage_query.backend import (
    CanonicalLineageBackend,
    LineageBackendMetadata,
)
from contextor.core.report_query import ARTIFACT_ID_RE, IndexCatalog


@dataclass(frozen=True)
class ResolvedLineageTarget:
    artifact_id: str
    qualified_name: str
    module_name: str
    symbol_name: str
    resolution: str


@dataclass(frozen=True)
class LineageTargetResolution:
    status: str
    query: str
    target: ResolvedLineageTarget | None = None
    candidates: tuple[ResolvedLineageTarget, ...] = ()


@dataclass(frozen=True)
class LineageAnchorMatch:
    source_key: str
    source_fingerprint: str
    binding: SemanticAnchorBinding


@dataclass(frozen=True)
class LineageFlowMatch:
    source_key: str
    source_fingerprint: str
    flow: MaterializedFlowFact


@dataclass(frozen=True)
class LineageSurfaceMatch:
    source_key: str
    source_fingerprint: str
    surface: MaterializedSurfaceFact


@dataclass(frozen=True)
class DirectLineageFacts:
    target: ResolvedLineageTarget
    metadata: LineageBackendMetadata
    anchors: tuple[LineageAnchorMatch, ...]
    incoming: tuple[LineageFlowMatch, ...]
    outgoing: tuple[LineageFlowMatch, ...]
    surfaces: tuple[LineageSurfaceMatch, ...]

    @property
    def complete(self) -> bool:
        return (
            self.metadata.family_state == "fresh"
            and self.metadata.query_index_state == "fresh"
            and self.metadata.semantic_anchor_bindings_complete
        )


class LineageQueryService:
    def __init__(
        self,
        backend: CanonicalLineageBackend,
        catalog: IndexCatalog,
    ) -> None:
        if not isinstance(backend, CanonicalLineageBackend):
            raise TypeError("backend must implement CanonicalLineageBackend.")
        if not isinstance(catalog, IndexCatalog):
            raise TypeError("catalog must be IndexCatalog.")
        self._backend = backend
        self._catalog = catalog

    def resolve_target(self, query: str) -> LineageTargetResolution:
        if not isinstance(query, str):
            raise TypeError("query must be a string.")

        raw = query.strip()
        if not raw:
            return LineageTargetResolution(
                status="invalid",
                query=raw,
            )

        if ARTIFACT_ID_RE.fullmatch(raw):
            artifact_id = raw[0].upper() + raw[1:]
            qualified_name = self._catalog.artifacts.get(artifact_id)
            if qualified_name is None:
                return LineageTargetResolution(
                    status="not_found",
                    query=raw,
                )
            return LineageTargetResolution(
                status="resolved",
                query=raw,
                target=_target(
                    artifact_id,
                    str(qualified_name),
                    resolution="exact_id",
                ),
            )

        if raw.count("::") != 1:
            return LineageTargetResolution(
                status="invalid",
                query=raw,
            )

        module_name, symbol_name = raw.split("::", 1)
        if not module_name or not symbol_name:
            return LineageTargetResolution(
                status="invalid",
                query=raw,
            )

        matches = tuple(
            _target(
                str(artifact_id),
                str(qualified_name),
                resolution="exact_identity",
            )
            for artifact_id, qualified_name in sorted(
                self._catalog.artifacts.items(),
                key=lambda item: (str(item[1]), str(item[0])),
            )
            if str(qualified_name) == raw
        )

        if not matches:
            return LineageTargetResolution(
                status="not_found",
                query=raw,
            )
        if len(matches) > 1:
            return LineageTargetResolution(
                status="ambiguous",
                query=raw,
                candidates=matches,
            )
        return LineageTargetResolution(
            status="resolved",
            query=raw,
            target=matches[0],
        )

    def direct_facts(
        self,
        target: ResolvedLineageTarget,
    ) -> DirectLineageFacts:
        if not isinstance(target, ResolvedLineageTarget):
            raise TypeError("target must be ResolvedLineageTarget.")

        metadata = self._backend.metadata()
        anchors: list[LineageAnchorMatch] = []
        incoming: list[LineageFlowMatch] = []
        outgoing: list[LineageFlowMatch] = []
        surfaces: list[LineageSurfaceMatch] = []

        source_keys = self._backend.source_keys_for_owner(target.artifact_id)
        for source in self._backend.iter_sources(source_keys):
            manifest = source.manifest
            anchor_refs: set[MaterializedOccurrenceRef] = set()
            for binding in source.semantic_anchors:
                if binding.owner_id != target.artifact_id:
                    continue
                anchor_refs.add(binding.reference)
                anchors.append(
                    LineageAnchorMatch(
                        source_key=manifest.source_key,
                        source_fingerprint=manifest.source_fingerprint,
                        binding=binding,
                    )
                )

            for flow in source.flows:
                match = LineageFlowMatch(
                    source_key=manifest.source_key,
                    source_fingerprint=manifest.source_fingerprint,
                    flow=flow,
                )
                target_matches = (
                    isinstance(flow.target, SemanticEndpoint)
                    and flow.target.owner_id == target.artifact_id
                ) or (
                    isinstance(flow.target, MaterializedOccurrenceRef)
                    and flow.target in anchor_refs
                )
                source_matches = (
                    isinstance(flow.source, SemanticEndpoint)
                    and flow.source.owner_id == target.artifact_id
                ) or (
                    isinstance(flow.source, MaterializedOccurrenceRef)
                    and flow.source in anchor_refs
                )
                if target_matches:
                    incoming.append(match)
                if source_matches:
                    outgoing.append(match)

            for surface in source.surfaces:
                if (
                    (
                        isinstance(surface.exposed, SemanticEndpoint)
                        and surface.exposed.owner_id == target.artifact_id
                    )
                    or (
                        isinstance(surface.exposed, MaterializedOccurrenceRef)
                        and surface.exposed in anchor_refs
                    )
                ):
                    surfaces.append(
                        LineageSurfaceMatch(
                            source_key=manifest.source_key,
                            source_fingerprint=manifest.source_fingerprint,
                            surface=surface,
                        )
                    )

        anchors.sort(key=_anchor_match_key)
        incoming.sort(key=_flow_match_key)
        outgoing.sort(key=_flow_match_key)
        surfaces.sort(key=_surface_match_key)

        return DirectLineageFacts(
            target=target,
            metadata=metadata,
            anchors=tuple(anchors),
            incoming=tuple(incoming),
            outgoing=tuple(outgoing),
            surfaces=tuple(surfaces),
        )


def _anchor_match_key(match: LineageAnchorMatch) -> tuple:
    binding = match.binding
    reference = binding.reference
    return (
        match.source_key,
        match.source_fingerprint,
        binding.owner_id,
        binding.qualified_name,
        reference.local_id,
    )


def _flow_match_key(match: LineageFlowMatch) -> tuple:
    flow = match.flow
    evidence = flow.evidence
    return (
        match.source_key,
        match.source_fingerprint,
        flow.local_id,
        flow.relation.value,
        evidence.start_line,
        evidence.start_column,
        evidence.end_line,
        evidence.end_column,
    )


def _surface_match_key(match: LineageSurfaceMatch) -> tuple:
    surface = match.surface
    evidence = surface.evidence
    return (
        match.source_key,
        match.source_fingerprint,
        surface.local_id,
        surface.kind.value,
        surface.declared_name,
        evidence.start_line,
        evidence.start_column,
        evidence.end_line,
        evidence.end_column,
    )


def _target(
    artifact_id: str,
    qualified_name: str,
    *,
    resolution: str,
) -> ResolvedLineageTarget:
    if qualified_name.count("::") != 1:
        raise ValueError(
            "Active artifact identity must be canonical module::symbol."
        )
    module_name, symbol_name = qualified_name.split("::", 1)
    if not module_name or not symbol_name:
        raise ValueError(
            "Active artifact identity must be canonical module::symbol."
        )
    return ResolvedLineageTarget(
        artifact_id=artifact_id,
        qualified_name=qualified_name,
        module_name=module_name,
        symbol_name=symbol_name,
        resolution=resolution,
    )
