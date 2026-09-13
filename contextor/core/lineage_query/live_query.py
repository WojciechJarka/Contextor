from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from contextor.core.lineage_query.backend import (
    RepositoryStateLineageBackend,
)
from contextor.core.lineage_query.service import (
    SYMBOL_LINEAGE_SECTION_ORDER,
    LineageQueryService,
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


@dataclass(frozen=True)
class LiveSymbolLineageQueryResult:
    resolution: LineageTargetResolution
    selected: SelectedSymbolLineageFacts | None = None
    unavailable_reason: str | None = None


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
