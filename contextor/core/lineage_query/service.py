from __future__ import annotations

from dataclasses import dataclass

from contextor.core.domain.lineage_facts import (
    LineageConfidence,
    MaterializedAnchorFact,
    MaterializedFlowFact,
    MaterializedOccurrenceRef,
    MaterializedSurfaceFact,
    MaterializedSymbolicRef,
    ResolutionKind,
    SemanticAnchorBinding,
    SemanticEndpoint,
)
from contextor.core.lineage_query.backend import (
    CanonicalLineageBackend,
    LineageBackendMetadata,
)
from contextor.core.report_query import ARTIFACT_ID_RE, IndexCatalog


_LEXICAL_SCOPE_KINDS = frozenset(
    {
        "class",
        "function",
        "async_function",
        "lambda",
        "comprehension",
    }
)


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
class LineageScopeRootMatch:
    source_key: str
    source_fingerprint: str
    binding: SemanticAnchorBinding
    anchor: MaterializedAnchorFact


@dataclass(frozen=True)
class LineageLocalAnchorMatch:
    source_key: str
    source_fingerprint: str
    anchor: MaterializedAnchorFact


@dataclass(frozen=True)
class LexicalScopeFacts:
    target: ResolvedLineageTarget
    metadata: LineageBackendMetadata
    roots: tuple[LineageScopeRootMatch, ...]
    flows: tuple[LineageFlowMatch, ...]
    nested_scopes: tuple[LineageLocalAnchorMatch, ...]
    materialization_complete: bool

    @property
    def scope_available(self) -> bool:
        return len(self.roots) == 1

    @property
    def root_ambiguous(self) -> bool:
        return len(self.roots) > 1

    @property
    def complete(self) -> bool:
        return (
            self.scope_available
            and self.materialization_complete
            and self.metadata.family_state == "fresh"
            and self.metadata.query_index_state == "fresh"
            and self.metadata.semantic_anchor_bindings_complete
        )


@dataclass(frozen=True)
class LineageTraversalStep:
    depth: int
    flow: LineageFlowMatch


@dataclass(frozen=True)
class LineageTraversalBoundary:
    depth: int
    flow: LineageFlowMatch
    endpoint: (
        MaterializedOccurrenceRef
        | MaterializedSymbolicRef
        | SemanticEndpoint
    )
    reason: str


@dataclass(frozen=True)
class LocalLineageTraversal:
    target: ResolvedLineageTarget
    scope: LexicalScopeFacts
    seed: MaterializedOccurrenceRef
    direction: str
    max_depth: int
    seed_in_scope: bool
    steps: tuple[LineageTraversalStep, ...]
    boundaries: tuple[LineageTraversalBoundary, ...]
    truncated: bool

    @property
    def traversal_available(self) -> bool:
        return self.scope.complete and self.seed_in_scope


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

    def lexical_scope_facts(
        self,
        target: ResolvedLineageTarget,
    ) -> LexicalScopeFacts:
        if not isinstance(target, ResolvedLineageTarget):
            raise TypeError("target must be ResolvedLineageTarget.")

        metadata = self._backend.metadata()
        roots: list[LineageScopeRootMatch] = []
        flows: list[LineageFlowMatch] = []
        nested_scopes: list[LineageLocalAnchorMatch] = []
        materialization_complete = True

        source_keys = self._backend.source_keys_for_owner(
            target.artifact_id
        )
        for source in self._backend.iter_sources(source_keys):
            manifest = source.manifest
            anchors_by_id = {
                anchor.local_id: anchor
                for anchor in source.anchors
            }
            root_ids: set[str] = set()

            for binding in source.semantic_anchors:
                if binding.owner_id != target.artifact_id:
                    continue
                anchor = anchors_by_id.get(
                    binding.reference.local_id
                )
                if (
                    anchor is None
                    or anchor.kind not in _LEXICAL_SCOPE_KINDS
                ):
                    continue
                root_ids.add(anchor.local_id)
                roots.append(
                    LineageScopeRootMatch(
                        source_key=manifest.source_key,
                        source_fingerprint=(
                            manifest.source_fingerprint
                        ),
                        binding=binding,
                        anchor=anchor,
                    )
                )

            if not root_ids:
                continue

            if not (
                manifest.status.value == "fresh"
                and manifest.anchor_ownership_materialized
                and manifest.flow_ownership_materialized
            ):
                materialization_complete = False

            for flow in source.flows:
                if flow.owner_local_id not in root_ids:
                    continue
                flows.append(
                    LineageFlowMatch(
                        source_key=manifest.source_key,
                        source_fingerprint=(
                            manifest.source_fingerprint
                        ),
                        flow=flow,
                    )
                )

            for anchor in source.anchors:
                if (
                    anchor.owner_local_id in root_ids
                    and anchor.kind in _LEXICAL_SCOPE_KINDS
                ):
                    nested_scopes.append(
                        LineageLocalAnchorMatch(
                            source_key=manifest.source_key,
                            source_fingerprint=(
                                manifest.source_fingerprint
                            ),
                            anchor=anchor,
                        )
                    )

        roots.sort(key=_scope_root_match_key)
        flows.sort(key=_flow_match_key)
        nested_scopes.sort(key=_local_anchor_match_key)

        if len(roots) != 1:
            flows.clear()
            nested_scopes.clear()

        return LexicalScopeFacts(
            target=target,
            metadata=metadata,
            roots=tuple(roots),
            flows=tuple(flows),
            nested_scopes=tuple(nested_scopes),
            materialization_complete=materialization_complete,
        )


    def traverse_lexical_scope(
        self,
        target: ResolvedLineageTarget,
        seed: MaterializedOccurrenceRef,
        *,
        direction: str,
        max_depth: int = 1,
    ) -> LocalLineageTraversal:
        if not isinstance(target, ResolvedLineageTarget):
            raise TypeError(
                "target must be ResolvedLineageTarget."
            )
        if not isinstance(seed, MaterializedOccurrenceRef):
            raise TypeError(
                "seed must be MaterializedOccurrenceRef."
            )
        if direction not in {"upstream", "downstream"}:
            raise ValueError(
                "direction must be 'upstream' or 'downstream'."
            )
        if (
            isinstance(max_depth, bool)
            or not isinstance(max_depth, int)
            or not 1 <= max_depth <= 3
        ):
            raise ValueError(
                "max_depth must be an integer from 1 to 3."
            )

        scope = self.lexical_scope_facts(target)

        scope_occurrences: set[
            MaterializedOccurrenceRef
        ] = set()
        for match in scope.flows:
            if isinstance(
                match.flow.source,
                MaterializedOccurrenceRef,
            ):
                scope_occurrences.add(match.flow.source)
            if isinstance(
                match.flow.target,
                MaterializedOccurrenceRef,
            ):
                scope_occurrences.add(match.flow.target)

        seed_in_scope = seed in scope_occurrences
        if not scope.complete or not seed_in_scope:
            return LocalLineageTraversal(
                target=target,
                scope=scope,
                seed=seed,
                direction=direction,
                max_depth=max_depth,
                seed_in_scope=seed_in_scope,
                steps=(),
                boundaries=(),
                truncated=False,
            )

        adjacency: dict[
            MaterializedOccurrenceRef,
            list[LineageFlowMatch],
        ] = {}
        for match in scope.flows:
            endpoint = (
                match.flow.source
                if direction == "downstream"
                else match.flow.target
            )
            if not isinstance(
                endpoint,
                MaterializedOccurrenceRef,
            ):
                continue
            adjacency.setdefault(endpoint, []).append(match)

        for matches in adjacency.values():
            matches.sort(key=_flow_match_key)

        queue: list[
            tuple[MaterializedOccurrenceRef, int]
        ] = [(seed, 0)]
        queue_index = 0
        reached_occurrence_depths = {seed: 0}
        selected_flows: set[tuple] = set()
        steps: list[LineageTraversalStep] = []
        boundaries: list[LineageTraversalBoundary] = []

        while queue_index < len(queue):
            current, current_depth = queue[queue_index]
            queue_index += 1

            for match in adjacency.get(current, ()):
                flow_key = _flow_match_identity(match)
                if flow_key in selected_flows:
                    continue

                step_depth = current_depth + 1
                selected_flows.add(flow_key)
                steps.append(
                    LineageTraversalStep(
                        depth=step_depth,
                        flow=match,
                    )
                )

                next_endpoint = (
                    match.flow.target
                    if direction == "downstream"
                    else match.flow.source
                )

                terminal_reason = _terminal_flow_reason(
                    match.flow
                )
                if terminal_reason is not None:
                    boundaries.append(
                        LineageTraversalBoundary(
                            depth=step_depth,
                            flow=match,
                            endpoint=next_endpoint,
                            reason=terminal_reason,
                        )
                    )
                    continue

                if isinstance(
                    next_endpoint,
                    MaterializedSymbolicRef,
                ):
                    boundaries.append(
                        LineageTraversalBoundary(
                            depth=step_depth,
                            flow=match,
                            endpoint=next_endpoint,
                            reason="symbolic",
                        )
                    )
                    continue

                if isinstance(
                    next_endpoint,
                    SemanticEndpoint,
                ):
                    boundaries.append(
                        LineageTraversalBoundary(
                            depth=step_depth,
                            flow=match,
                            endpoint=next_endpoint,
                            reason="semantic",
                        )
                    )
                    continue

                if not isinstance(
                    next_endpoint,
                    MaterializedOccurrenceRef,
                ):
                    raise TypeError(
                        "Canonical lineage flow has an "
                        "unsupported endpoint type."
                    )

                if next_endpoint not in reached_occurrence_depths:
                    reached_occurrence_depths[
                        next_endpoint
                    ] = step_depth
                    if step_depth < max_depth:
                        queue.append(
                            (next_endpoint, step_depth)
                        )

        truncated = any(
            depth == max_depth
            and any(
                _flow_match_identity(candidate)
                not in selected_flows
                for candidate in adjacency.get(
                    occurrence,
                    (),
                )
            )
            for occurrence, depth
            in reached_occurrence_depths.items()
        )

        return LocalLineageTraversal(
            target=target,
            scope=scope,
            seed=seed,
            direction=direction,
            max_depth=max_depth,
            seed_in_scope=True,
            steps=tuple(steps),
            boundaries=tuple(boundaries),
            truncated=truncated,
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


def _scope_root_match_key(
    match: LineageScopeRootMatch,
) -> tuple:
    binding = match.binding
    anchor = match.anchor
    span = anchor.span
    return (
        match.source_key,
        match.source_fingerprint,
        binding.owner_id,
        binding.qualified_name,
        anchor.local_id,
        anchor.kind,
        span.start_line,
        span.start_column,
        span.end_line,
        span.end_column,
    )


def _local_anchor_match_key(
    match: LineageLocalAnchorMatch,
) -> tuple:
    anchor = match.anchor
    span = anchor.span
    return (
        match.source_key,
        match.source_fingerprint,
        anchor.local_id,
        anchor.kind,
        span.start_line,
        span.start_column,
        span.end_line,
        span.end_column,
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


def _flow_match_identity(
    match: LineageFlowMatch,
) -> tuple[str, str, str]:
    return (
        match.source_key,
        match.source_fingerprint,
        match.flow.local_id,
    )


def _terminal_flow_reason(
    flow: MaterializedFlowFact,
) -> str | None:
    if (
        flow.resolution_kind
        is ResolutionKind.DYNAMIC_RUNTIME_BOUNDARY
        or flow.confidence is LineageConfidence.DYNAMIC
    ):
        return "dynamic"
    if (
        flow.resolution_kind
        is ResolutionKind.UNRESOLVED_NAME
        or flow.confidence is LineageConfidence.UNRESOLVED
    ):
        return "unresolved"
    return None

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
