from __future__ import annotations

from collections.abc import Mapping

from contextor.core.domain.lineage_facts import (
    MaterializedLineageSourceFacts,
    SemanticEndpoint,
)


def lineage_owner_ids_for_source(
    source: MaterializedLineageSourceFacts,
) -> tuple[str, ...]:
    if not isinstance(source, MaterializedLineageSourceFacts):
        raise TypeError("source must be MaterializedLineageSourceFacts.")

    owners = {binding.owner_id for binding in source.semantic_anchors}
    for flow in source.flows:
        if isinstance(flow.source, SemanticEndpoint):
            owners.add(flow.source.owner_id)
        if isinstance(flow.target, SemanticEndpoint):
            owners.add(flow.target.owner_id)
    for surface in source.surfaces:
        if isinstance(surface.exposed, SemanticEndpoint):
            owners.add(surface.exposed.owner_id)
    return tuple(sorted(owners))


def semantic_anchor_bindings_complete(
    sources: Mapping[str, MaterializedLineageSourceFacts],
) -> bool:
    return all(
        source.manifest.semantic_anchor_bindings_materialized
        for source in sources.values()
    )


def build_lineage_query_indexes(
    sources: Mapping[str, MaterializedLineageSourceFacts],
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], bool]:
    if not isinstance(sources, Mapping):
        raise TypeError("sources must be a mapping.")

    owner_sources: dict[str, set[str]] = {}
    source_owners: dict[str, tuple[str, ...]] = {}
    for source_key in sorted(sources):
        source = sources[source_key]
        if not isinstance(source_key, str) or not source_key:
            raise ValueError("lineage source key must be a non-empty string.")
        if not isinstance(source, MaterializedLineageSourceFacts):
            raise TypeError("lineage source value has invalid type.")
        if source.manifest.source_key != source_key:
            raise ValueError("lineage mapping key does not match source manifest.")

        owners = lineage_owner_ids_for_source(source)
        source_owners[source_key] = owners
        for owner_id in owners:
            owner_sources.setdefault(owner_id, set()).add(source_key)

    return (
        {
            owner_id: tuple(sorted(source_keys))
            for owner_id, source_keys in sorted(owner_sources.items())
        },
        dict(sorted(source_owners.items())),
        semantic_anchor_bindings_complete(sources),
    )


def patch_lineage_query_indexes(
    owner_source_index: Mapping[str, tuple[str, ...]],
    source_owner_index: Mapping[str, tuple[str, ...]],
    *,
    source_key: str,
    source: MaterializedLineageSourceFacts | None,
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    if not isinstance(source_key, str) or not source_key:
        raise ValueError("source_key must be a non-empty string.")

    owner_sources = {
        str(owner_id): set(source_keys)
        for owner_id, source_keys in owner_source_index.items()
    }
    source_owners = {
        str(key): tuple(owners)
        for key, owners in source_owner_index.items()
    }
    for owner_id in source_owners.pop(source_key, ()):
        current = owner_sources.get(owner_id)
        if current is None:
            continue
        current.discard(source_key)
        if not current:
            owner_sources.pop(owner_id, None)

    if source is not None:
        if not isinstance(source, MaterializedLineageSourceFacts):
            raise TypeError("source must be MaterializedLineageSourceFacts or None.")
        if source.manifest.source_key != source_key:
            raise ValueError("source_key does not match source manifest.")
        owners = lineage_owner_ids_for_source(source)
        source_owners[source_key] = owners
        for owner_id in owners:
            owner_sources.setdefault(owner_id, set()).add(source_key)

    return (
        {
            owner_id: tuple(sorted(source_keys))
            for owner_id, source_keys in sorted(owner_sources.items())
        },
        dict(sorted(source_owners.items())),
    )
