from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.domain.lineage_facts import (
    MaterializedLineageSourceFacts,
    SemanticEndpoint,
)
from contextor.core.reference.shared import (
    _canonicalize_package_reference_target,
    _assemble_module_export_surfaces,
)


@dataclass(frozen=True)
class ReexportLineageHop:
    source: str
    target: str
    kind: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("re-export hop source must be a non-empty string.")
        if not isinstance(self.target, str) or not self.target:
            raise ValueError("re-export hop target must be a non-empty string.")
        if self.kind not in {"binding", "star"}:
            raise ValueError("re-export hop kind must be 'binding' or 'star'.")


@dataclass(frozen=True)
class ReexportLineageResolution:
    status: str
    query: str
    canonical_target: str | None = None
    hops: tuple[ReexportLineageHop, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"not_alias", "resolved", "cycle", "unresolved"}:
            raise ValueError("re-export lineage resolution status is invalid.")
        if not isinstance(self.query, str):
            raise TypeError("re-export lineage query must be a string.")
        if self.canonical_target is not None and (
            not isinstance(self.canonical_target, str)
            or not self.canonical_target
        ):
            raise ValueError("canonical_target must be a non-empty string or None.")
        if not isinstance(self.hops, tuple) or any(
            not isinstance(hop, ReexportLineageHop) for hop in self.hops
        ):
            raise TypeError("re-export lineage hops must be a tuple of hops.")
        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("re-export lineage reason must be a string or None.")


def canonicalize_lineage_qualified_identity(
    qualified_name: str,
    modules,
) -> str:
    if not isinstance(qualified_name, str):
        raise TypeError("qualified_name must be a string.")
    if not isinstance(modules, Mapping):
        raise TypeError("modules must be a mapping.")
    if qualified_name.count("::") != 1:
        return qualified_name

    module_name, symbol_name = qualified_name.split("::", 1)
    if not module_name or not symbol_name:
        return qualified_name

    dotted = f"{module_name}.{symbol_name}"
    canonical_dotted = _canonicalize_package_reference_target(
        dotted,
        modules,
    )
    if not isinstance(canonical_dotted, str) or not canonical_dotted:
        return qualified_name

    module_names = set(modules)
    parts = canonical_dotted.split(".")
    for split_at in range(len(parts) - 1, 0, -1):
        candidate_module = ".".join(parts[:split_at])
        if candidate_module not in module_names:
            continue
        candidate_symbol = ".".join(parts[split_at:])
        if candidate_symbol:
            return f"{candidate_module}::{candidate_symbol}"
    return qualified_name


def _qualified_reexport_target(
    target: str,
    known_modules: set[str],
) -> str:
    if target.count("::") == 1:
        return target
    parts = target.split(".")
    for split_at in range(len(parts) - 1, 0, -1):
        candidate_module = ".".join(parts[:split_at])
        if candidate_module not in known_modules:
            continue
        candidate_symbol = ".".join(parts[split_at:])
        if candidate_symbol:
            return f"{candidate_module}::{candidate_symbol}"
    return target


def build_reexport_lineage_alias_index(
    reexport_facts_by_module,
) -> dict[str, ReexportLineageHop]:
    if not isinstance(reexport_facts_by_module, Mapping):
        raise TypeError("reexport_facts_by_module must be a mapping.")

    facts_by_exporter: dict[str, Mapping[str, object]] = {}
    known_modules: set[str] = set()
    for facts in reexport_facts_by_module.values():
        if not isinstance(facts, Mapping):
            raise TypeError("canonical re-export fact must be a mapping.")
        exporter = facts.get("exporter")
        bindings = facts.get("bindings")
        star_sources = facts.get("star_sources")
        if not isinstance(exporter, str) or not exporter:
            raise ValueError("canonical re-export exporter is invalid.")
        if not isinstance(bindings, Mapping):
            raise ValueError("canonical re-export bindings are invalid.")
        if not isinstance(star_sources, (list, tuple)) or any(
            not isinstance(source, str) or not source
            for source in star_sources
        ):
            raise ValueError("canonical re-export star_sources are invalid.")
        if exporter in facts_by_exporter:
            raise ValueError("canonical re-export exporter identity is duplicated.")
        facts_by_exporter[exporter] = facts
        known_modules.add(exporter)
        known_modules.update(star_sources)

    module_export_surfaces = _assemble_module_export_surfaces(
        dict(reexport_facts_by_module)
    )
    alias_index: dict[str, ReexportLineageHop] = {}

    def install(hop: ReexportLineageHop) -> None:
        existing = alias_index.get(hop.source)
        if existing is not None and existing != hop:
            raise ValueError("canonical re-export alias identity is ambiguous.")
        alias_index[hop.source] = hop

    for exporter, facts in facts_by_exporter.items():
        bindings = facts["bindings"]
        assert isinstance(bindings, Mapping)
        for local, target in bindings.items():
            if not isinstance(local, str) or not local:
                raise ValueError("canonical re-export binding name is invalid.")
            if not isinstance(target, str) or not target:
                raise ValueError("canonical re-export binding target is invalid.")
            source = f"{exporter}::{local}"
            if f"{exporter}.{local}" == target:
                continue
            install(
                ReexportLineageHop(
                    source=source,
                    target=_qualified_reexport_target(target, known_modules),
                    kind="binding",
                )
            )

    # Reproduce the existing export-surface assembler's deterministic
    # fixed-point ordering to retain the first star source that installs a
    # visible local. The final visibility set still comes from its canonical
    # helper above.
    working_surfaces: dict[str, dict[str, str]] = {}
    direct_bindings: dict[str, Mapping[str, object]] = {}
    star_imports: list[tuple[str, str, set[str] | None]] = []
    for exporter, facts in facts_by_exporter.items():
        bindings = facts["bindings"]
        explicit_all = facts.get("explicit_all")
        if explicit_all is not None and not isinstance(explicit_all, (list, tuple)):
            raise ValueError("canonical re-export explicit_all is invalid.")
        allowed = None if explicit_all is None else set(explicit_all)
        assert isinstance(bindings, Mapping)
        direct_bindings[exporter] = bindings
        visible: dict[str, str] = {}
        for local, target in bindings.items():
            if not isinstance(local, str) or not isinstance(target, str):
                raise ValueError("canonical re-export binding is invalid.")
            if allowed is not None and local not in allowed:
                continue
            if allowed is None and local.startswith("_"):
                continue
            visible[local] = target
        working_surfaces[exporter] = visible
        for source in facts["star_sources"]:
            star_imports.append((exporter, source, allowed))

    star_winners: dict[tuple[str, str], str] = {}
    changed = True
    while changed:
        changed = False
        for exporter, source, allowed in star_imports:
            for local, target in tuple(working_surfaces.get(source, {}).items()):
                if allowed is not None and local not in allowed:
                    continue
                if allowed is None and local.startswith("_"):
                    continue
                # A named binding owns its namespace slot even when it is a
                # self-binding and therefore did not create a binding edge.
                if local in direct_bindings.get(exporter, {}):
                    continue
                winner_key = (exporter, local)
                if winner_key in star_winners:
                    continue
                working_surfaces.setdefault(exporter, {})[local] = target
                star_winners[winner_key] = source
                changed = True

    for exporter, visible_bindings in module_export_surfaces.items():
        facts = facts_by_exporter.get(exporter)
        if facts is None:
            continue
        bindings = facts["bindings"]
        assert isinstance(bindings, Mapping)
        for local in visible_bindings:
            if local in bindings:
                continue
            source = star_winners.get((exporter, local))
            if source is None:
                continue
            install(
                ReexportLineageHop(
                    source=f"{exporter}::{local}",
                    target=f"{source}::{local}",
                    kind="star",
                )
            )

    return dict(sorted(alias_index.items()))


def resolve_reexport_lineage_alias(
    query: str,
    alias_index: Mapping[str, ReexportLineageHop],
    modules,
) -> ReexportLineageResolution:
    if not isinstance(query, str):
        raise TypeError("query must be a string.")
    if not isinstance(alias_index, Mapping):
        raise TypeError("alias_index must be a mapping.")
    if not isinstance(modules, Mapping):
        raise TypeError("modules must be a mapping.")

    original = query.strip()
    if original not in alias_index:
        return ReexportLineageResolution(
            status="not_alias",
            query=original,
        )

    hops: list[ReexportLineageHop] = []
    visited: set[str] = set()
    current = original
    while True:
        if current in visited:
            return ReexportLineageResolution(
                status="cycle",
                query=original,
                hops=tuple(hops),
                reason="reexport_cycle",
            )
        visited.add(current)
        hop = alias_index.get(current)
        if hop is None:
            canonical_target = canonicalize_lineage_qualified_identity(
                current,
                modules,
            )
            if canonical_target.count("::") != 1:
                return ReexportLineageResolution(
                    status="unresolved",
                    query=original,
                    hops=tuple(hops),
                    reason="target_outside_repository",
                )
            module_name = canonical_target.split("::", 1)[0]
            if module_name not in modules:
                return ReexportLineageResolution(
                    status="unresolved",
                    query=original,
                    hops=tuple(hops),
                    reason="target_outside_repository",
                )
            return ReexportLineageResolution(
                status="resolved",
                query=original,
                canonical_target=canonical_target,
                hops=tuple(hops),
            )

        if hop.target in alias_index:
            # Keep a package façade alias in its re-export identity form long
            # enough to follow the next edge. Canonicalizing it to
            # pkg.__init__::name here would skip the alias-index key pkg::name.
            canonical_target = hop.target
        else:
            canonical_target = canonicalize_lineage_qualified_identity(
                hop.target,
                modules,
            )
            if canonical_target.count("::") != 1:
                return ReexportLineageResolution(
                    status="unresolved",
                    query=original,
                    hops=tuple(hops),
                    reason="target_outside_repository",
                )
            module_name = canonical_target.split("::", 1)[0]
            if module_name not in modules:
                return ReexportLineageResolution(
                    status="unresolved",
                    query=original,
                    hops=tuple(hops),
                    reason="target_outside_repository",
                )

        resolved_hop = ReexportLineageHop(
            source=current,
            target=canonical_target,
            kind=hop.kind,
        )
        hops.append(resolved_hop)
        if canonical_target in visited:
            return ReexportLineageResolution(
                status="cycle",
                query=original,
                hops=tuple(hops),
                reason="reexport_cycle",
            )
        current = canonical_target


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
