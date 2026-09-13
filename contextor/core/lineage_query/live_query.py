from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from contextor.core.lineage_query.backend import (
    RepositoryStateLineageBackend,
)
from contextor.core.domain.lineage_facts import (
    ExtractedSymbolicKind,
    SemanticEndpoint,
    SemanticEndpointRole,
)
from contextor.core.lineage_query.service import (
    SYMBOL_LINEAGE_SECTION_ORDER,
    LineageFlowMatch,
    LineageQueryService,
    LineageSurfaceMatch,
    LineageTargetResolution,
    SelectedSymbolLineageFacts,
)
from contextor.core.report_query import (
    ARTIFACT_ID_RE,
    IndexCatalog,
)


_UNAVAILABLE_MESSAGE = (
    "Canonical lineage target identity catalog "
    "is unavailable or stale."
)

_OWNER_NAME_ORIGIN_UNAVAILABLE = (
    "Canonical semantic owner name origin is unavailable."
)
_OWNER_NAME_INCONSISTENT = (
    "Canonical semantic owner identity is inconsistent."
)


@dataclass(frozen=True)
class LiveSymbolLineageQueryResult:
    resolution: LineageTargetResolution
    selected: SelectedSymbolLineageFacts | None = None
    unavailable_reason: str | None = None


def _selected_lineage_flow_matches(
    selected: SelectedSymbolLineageFacts,
) -> tuple[LineageFlowMatch, ...]:
    matches: dict[tuple[str, str, str], LineageFlowMatch] = {}

    def add(items: tuple[LineageFlowMatch, ...]) -> None:
        for match in items:
            key = (
                match.source_key,
                match.source_fingerprint,
                match.flow.local_id,
            )
            existing = matches.get(key)
            if existing is not None and existing != match:
                raise ValueError(
                    "Selected lineage flow identity is inconsistent."
                )
            matches[key] = match

    if selected.interface is not None:
        add(selected.interface.parameter_defaults)
    if selected.connections is not None:
        add(selected.connections.incoming)
        add(selected.connections.outgoing)
    for name in (
        "bindings",
        "parameter_flows",
        "calls_interfaces",
        "returns",
        "state",
        "callbacks",
        "unresolved_dynamic_boundaries",
    ):
        value = getattr(selected, name)
        if value is not None:
            add(value)
    if selected.surfaces is not None:
        add(selected.surfaces.flows)
    return tuple(matches[key] for key in sorted(matches))


def _selected_lineage_surface_matches(
    selected: SelectedSymbolLineageFacts,
) -> tuple[LineageSurfaceMatch, ...]:
    if selected.surfaces is None:
        return ()
    return tuple(
        sorted(
            selected.surfaces.facts,
            key=lambda match: (
                match.source_key,
                match.source_fingerprint,
                match.surface.local_id,
            ),
        )
    )


def _owner_name_from_origin(origin) -> str:
    if origin.kind is ExtractedSymbolicKind.STATE:
        return origin.module_name
    return f"{origin.module_name}::{origin.symbol_name}"


def _install_owner_name(
    owner_names: dict[str, str],
    owner_id: str,
    owner_name: str,
) -> None:
    existing = owner_names.get(owner_id)
    if existing is not None and existing != owner_name:
        raise ValueError(_OWNER_NAME_INCONSISTENT)
    owner_names[owner_id] = owner_name


def build_selected_lineage_owner_names(
    backend: RepositoryStateLineageBackend,
    selected: SelectedSymbolLineageFacts,
) -> dict[str, str]:
    if not isinstance(backend, RepositoryStateLineageBackend):
        raise TypeError("backend must be RepositoryStateLineageBackend.")
    if not isinstance(selected, SelectedSymbolLineageFacts):
        raise TypeError("selected must be SelectedSymbolLineageFacts.")

    owner_names: dict[str, str] = {}
    source_cache = {}
    origin_cache = {}

    def origin_for(
        source_key: str,
        source_fingerprint: str,
        fact_local_id: str,
        endpoint_role: SemanticEndpointRole,
    ):
        source = source_cache.get(source_key)
        if source is None:
            source = backend.get_source(source_key)
            if source is None:
                raise ValueError(_OWNER_NAME_ORIGIN_UNAVAILABLE)
            source_cache[source_key] = source
        if source.manifest.source_fingerprint != source_fingerprint:
            raise ValueError(_OWNER_NAME_ORIGIN_UNAVAILABLE)
        cache_key = (
            source_key,
            source_fingerprint,
            fact_local_id,
            endpoint_role,
        )
        cached = origin_cache.get(cache_key)
        if cached is not None:
            return cached
        matches = tuple(
            origin
            for origin in source.semantic_endpoint_origins
            if (
                origin.fact_local_id == fact_local_id
                and origin.endpoint_role is endpoint_role
            )
        )
        if len(matches) != 1:
            raise ValueError(_OWNER_NAME_ORIGIN_UNAVAILABLE)
        origin_cache[cache_key] = matches[0]
        return matches[0]

    def resolve(
        endpoint,
        *,
        source_key: str,
        source_fingerprint: str,
        fact_local_id: str,
        endpoint_role: SemanticEndpointRole,
    ) -> None:
        if not isinstance(endpoint, SemanticEndpoint):
            return
        origin = origin_for(
            source_key,
            source_fingerprint,
            fact_local_id,
            endpoint_role,
        )
        _install_owner_name(
            owner_names,
            endpoint.owner_id,
            _owner_name_from_origin(origin),
        )

    for match in _selected_lineage_flow_matches(selected):
        resolve(
            match.flow.source,
            source_key=match.source_key,
            source_fingerprint=match.source_fingerprint,
            fact_local_id=match.flow.local_id,
            endpoint_role=SemanticEndpointRole.FLOW_SOURCE,
        )
        resolve(
            match.flow.target,
            source_key=match.source_key,
            source_fingerprint=match.source_fingerprint,
            fact_local_id=match.flow.local_id,
            endpoint_role=SemanticEndpointRole.FLOW_TARGET,
        )
    for match in _selected_lineage_surface_matches(selected):
        resolve(
            match.surface.exposed,
            source_key=match.source_key,
            source_fingerprint=match.source_fingerprint,
            fact_local_id=match.surface.local_id,
            endpoint_role=SemanticEndpointRole.SURFACE_EXPOSED,
        )
    return dict(sorted(owner_names.items()))


def _require_exact_identity_capability(
    backend: RepositoryStateLineageBackend,
) -> None:
    metadata = backend.metadata()
    if (
        metadata.family_state != "fresh"
        or metadata.query_index_state != "fresh"
        or not metadata.semantic_anchor_bindings_complete
    ):
        raise ValueError(_UNAVAILABLE_MESSAGE)


def _module_source_key(
    state: object,
    module_name: str,
) -> str | None:
    modules = getattr(state, "modules", {})
    if not isinstance(modules, Mapping):
        raise TypeError(
            "Canonical state modules must be a mapping."
        )

    module = modules.get(module_name)
    if module is None:
        return None

    raw_path = getattr(module, "path", None)
    if raw_path is None:
        return None

    source_key = str(raw_path).replace("\\", "/")
    while source_key.startswith("./"):
        source_key = source_key[2:]

    return source_key or None


def _install_identity(
    identities: dict[str, str],
    owner_id: str,
    qualified_name: str,
) -> None:
    existing = identities.get(owner_id)
    if (
        existing is not None
        and existing != qualified_name
    ):
        raise ValueError(
            "Canonical lineage owner identity is inconsistent."
        )
    identities[owner_id] = qualified_name


def build_live_lineage_target_catalog(
    state: object,
    backend: RepositoryStateLineageBackend,
    query: str,
) -> IndexCatalog:
    if not isinstance(
        backend,
        RepositoryStateLineageBackend,
    ):
        raise TypeError(
            "backend must be RepositoryStateLineageBackend."
        )
    if not isinstance(query, str):
        raise TypeError("query must be a string.")

    _require_exact_identity_capability(backend)

    raw = query.strip()
    identities: dict[str, str] = {}

    if not raw:
        return IndexCatalog(
            modules={},
            artifacts={},
        )

    if ARTIFACT_ID_RE.fullmatch(raw):
        owner_id = raw[0].upper() + raw[1:]
        source_keys = backend.source_keys_for_owner(
            owner_id
        )
        for source in backend.iter_sources(
            source_keys
        ):
            for binding in source.semantic_anchors:
                if binding.owner_id != owner_id:
                    continue
                _install_identity(
                    identities,
                    owner_id,
                    binding.qualified_name,
                )

        return IndexCatalog(
            modules={},
            artifacts=dict(sorted(identities.items())),
        )

    if raw.count("::") != 1:
        return IndexCatalog(
            modules={},
            artifacts={},
        )

    module_name, symbol_name = raw.split("::", 1)
    if not module_name or not symbol_name:
        return IndexCatalog(
            modules={},
            artifacts={},
        )

    source_key = _module_source_key(
        state,
        module_name,
    )
    if source_key is None:
        return IndexCatalog(
            modules={},
            artifacts={},
        )

    source = backend.get_source(source_key)
    if source is None:
        return IndexCatalog(
            modules={},
            artifacts={},
        )

    for binding in source.semantic_anchors:
        if binding.qualified_name != raw:
            continue
        _install_identity(
            identities,
            binding.owner_id,
            binding.qualified_name,
        )

    return IndexCatalog(
        modules={},
        artifacts=dict(sorted(identities.items())),
    )


def _canonical_lineage_sections(
    sections: tuple[str, ...],
) -> tuple[str, ...]:
    if not isinstance(sections, tuple):
        raise TypeError(
            "sections must be a tuple of section names."
        )
    if any(
        not isinstance(section, str)
        or not section
        for section in sections
    ):
        raise ValueError(
            "sections must contain non-empty strings."
        )
    if len(set(sections)) != len(sections):
        raise ValueError(
            "sections must not contain duplicates."
        )

    requested = set(sections)
    unknown = tuple(
        sorted(
            requested
            - set(SYMBOL_LINEAGE_SECTION_ORDER)
        )
    )
    if unknown:
        raise ValueError(
            "Unknown symbol lineage sections: "
            + ", ".join(unknown)
        )

    return tuple(
        section
        for section in SYMBOL_LINEAGE_SECTION_ORDER
        if section in requested
    )


def query_live_symbol_lineage(
    state: object,
    query: str,
    sections: tuple[str, ...],
) -> LiveSymbolLineageQueryResult:
    if not isinstance(query, str):
        raise TypeError("query must be a string.")

    canonical_sections = (
        _canonical_lineage_sections(sections)
    )
    backend = RepositoryStateLineageBackend(
        state
    )

    try:
        catalog = build_live_lineage_target_catalog(
            state,
            backend,
            query,
        )
    except ValueError as exc:
        if str(exc) != _UNAVAILABLE_MESSAGE:
            raise
        return LiveSymbolLineageQueryResult(
            resolution=LineageTargetResolution(
                status="unavailable",
                query=query.strip(),
            ),
            unavailable_reason=str(exc),
        )

    service = LineageQueryService(
        backend,
        catalog,
    )
    resolution = service.resolve_target(
        query
    )

    if (
        resolution.status != "resolved"
        or resolution.target is None
    ):
        return LiveSymbolLineageQueryResult(
            resolution=resolution,
        )

    facts = service.symbol_lineage_facts(
        resolution.target
    )
    selected = (
        service.select_symbol_lineage_sections(
            facts,
            canonical_sections,
        )
    )

    return LiveSymbolLineageQueryResult(
        resolution=resolution,
        selected=selected,
    )
