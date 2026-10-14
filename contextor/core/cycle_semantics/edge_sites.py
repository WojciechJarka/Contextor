"""Source-snapshot lexical candidates for canonical cyclic hard edges.

Matches are provenance evidence, never proof of import activation or runtime
resolution. Unmatched edges remain explicit, rather than being discarded.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.source import ParsedSourceInput

from .provenance import ControlFrame, ScopeFrame, extract_import_provenance
from .scc import ImportCycleTopology, analyze_import_cycle_topology

MAX_SOURCE_AST_NODES = 100_000


@dataclass(frozen=True)
class LexicalEdgeSite:
    ordinal: int
    line: int
    column: int
    form: str
    match_kind: str
    requested_name: str
    matched_member: str | None
    scopes: tuple[ScopeFrame, ...]
    controls: tuple[ControlFrame, ...]
    activation_scope: str


@dataclass(frozen=True)
class HardEdgeSiteEvidence:
    source: str
    target: str
    status: str
    sites: tuple[LexicalEdgeSite, ...]


@dataclass(frozen=True)
class SCCImportSiteEvidence:
    members: tuple[str, ...]
    internal_edges: tuple[HardEdgeSiteEvidence, ...]
    matched_edge_count: int
    unresolved_edge_count: int
    evidence_scope: str = "LEXICAL_IMPORT_CANDIDATES_NOT_EXECUTION"


@dataclass(frozen=True)
class CyclicImportSiteReport:
    topology: ImportCycleTopology
    components: tuple[SCCImportSiteEvidence, ...]
    evidence_scope: str = "SNAPSHOT_LEXICAL_EVIDENCE_NOT_RUNTIME_CERTIFICATION"


def _canonical(name: str, indexed: set[str]) -> tuple[str, ...]:
    """Keep indexed file/package collisions as distinct candidates."""
    return tuple(
        candidate
        for candidate in (name, name + ".__init__")
        if candidate in indexed
    )


def _parents(name: str, indexed: set[str]) -> tuple[str, ...]:
    pieces = name.split(".")
    return tuple(
        prefix + ".__init__"
        for length in range(1, len(pieces))
        if (
            prefix := ".".join(pieces[:length])
        ) + ".__init__" in indexed
    )


def _absolute_from(
    importer: str,
    module: str | None,
    level: int,
) -> str | None:
    if level == 0:
        return (
            module
            if module
            and all(p.isidentifier() for p in module.split("."))
            else None
        )

    if level < 0:
        return None

    context = (
        importer.rsplit(".", 1)[0]
        if not importer.endswith(".__init__")
        else importer.removesuffix(".__init__")
    )

    parts = context.split(".") if context else []
    climb = level - 1

    if not parts or climb >= len(parts):
        return None

    parent = parts[:len(parts) - climb]

    if module:
        if not all(p.isidentifier() for p in module.split(".")):
            return None
        parent.extend(module.split("."))

    return ".".join(parent)


def _candidate_targets(
    occurrence,
    importer: str,
    indexed: set[str],
) -> tuple[tuple[str, str, str, str | None], ...]:
    """Return canonical target, match kind, request and member."""
    found: set[tuple[str, str, str, str | None]] = set()

    if occurrence.form == "IMPORT":
        for requested, _alias in occurrence.aliases:
            if (
                not requested
                or not all(
                    p.isidentifier()
                    for p in requested.split(".")
                )
            ):
                continue

            for candidate in _canonical(requested, indexed):
                found.add((
                    candidate,
                    "DIRECT_MODULE",
                    requested,
                    None,
                ))

            for candidate in _parents(requested, indexed):
                found.add((
                    candidate,
                    "PARENT_INITIALIZER",
                    requested,
                    None,
                ))

    elif occurrence.form == "IMPORT_FROM":
        base = _absolute_from(
            importer,
            occurrence.module,
            occurrence.level,
        )

        if base is None:
            return ()

        for candidate in _canonical(base, indexed):
            found.add((
                candidate,
                "FROM_BASE",
                base,
                None,
            ))

        for candidate in _parents(base, indexed):
            found.add((
                candidate,
                "PARENT_INITIALIZER",
                base,
                None,
            ))

        for member, _alias in occurrence.aliases:
            if member == "*" or not member.isidentifier():
                continue

            child = base + "." + member

            for candidate in _canonical(child, indexed):
                found.add((
                    candidate,
                    "OPTIONAL_FROM_CHILD",
                    base,
                    member,
                ))

    return tuple(sorted(found))


def _activation(
    scopes: tuple[ScopeFrame, ...],
    controls: tuple[ControlFrame, ...],
) -> str:
    if any(
        scope.kind in {"FUNCTION", "ASYNC_FUNCTION"}
        for scope in scopes
    ):
        return "FUNCTION_SCOPED"

    if scopes:
        return "OTHER_SCOPED"

    if controls:
        return "GUARDED_TOP_LEVEL"

    return "MODULE_TOP_LEVEL"


def analyze_cyclic_import_sites(
    hard_edges: Mapping[
        str,
        set[str] | frozenset[str] | list[str] | tuple[str, ...],
    ],
    parsed_sources: Mapping[str, ParsedSourceInput],
) -> CyclicImportSiteReport:
    """Join canonical internal SCC edges to lexical AST candidates.

    All graph edges survive even when source or lexical evidence is missing.
    The model performs no runtime import execution or source reads.
    """
    if not isinstance(hard_edges, Mapping):
        raise TypeError("hard_edges must be a mapping")

    topology = analyze_import_cycle_topology(hard_edges)

    if not isinstance(parsed_sources, Mapping):
        raise TypeError("parsed_sources must be a mapping")

    indexed = set(hard_edges)

    for targets in hard_edges.values():
        indexed.update(targets)

    members = {
        name
        for component in topology.cyclic_components
        for name in component.members
    }

    available: dict[
        str,
        dict[str, tuple[LexicalEdgeSite, ...]],
    ] = {}

    invalid: set[str] = set()

    for module in sorted(members):
        source = parsed_sources.get(module)

        if (
            not isinstance(source, ParsedSourceInput)
            or not isinstance(source.tree, ast.Module)
            or not isinstance(source.source_fingerprint, str)
            or len(source.source_fingerprint) != 64
            or any(
                c not in "0123456789abcdef"
                for c in source.source_fingerprint
            )
        ):
            invalid.add(module)
            continue

        node_count = 0

        for _ in ast.walk(source.tree):
            node_count += 1

            if node_count > MAX_SOURCE_AST_NODES:
                invalid.add(module)
                break

        if module in invalid:
            continue

        evidence = extract_import_provenance(
            source.tree,
            module_id=module,
            source_key=module,
            source_path=module,
            source_fingerprint=source.source_fingerprint,
        )

        matches: dict[
            str,
            set[LexicalEdgeSite],
        ] = {}

        for occurrence in evidence.occurrences:
            candidates = _candidate_targets(
                occurrence,
                module,
                indexed,
            )

            for target, kind, requested, member in candidates:
                site = LexicalEdgeSite(
                    ordinal=occurrence.ordinal,
                    line=occurrence.line,
                    column=occurrence.column,
                    form=occurrence.form,
                    match_kind=kind,
                    requested_name=requested,
                    matched_member=member,
                    scopes=occurrence.scopes,
                    controls=occurrence.controls,
                    activation_scope=_activation(
                        occurrence.scopes,
                        occurrence.controls,
                    ),
                )

                matches.setdefault(target, set()).add(site)

        available[module] = {
            target: tuple(
                sorted(
                    sites,
                    key=lambda site: (
                        site.ordinal,
                        site.match_kind,
                        site.matched_member or "",
                    ),
                )
            )
            for target, sites in matches.items()
        }

    components: list[SCCImportSiteEvidence] = []

    for component in topology.cyclic_components:
        edges: list[HardEdgeSiteEvidence] = []

        for source, target in component.internal_edges:
            if source in invalid:
                edges.append(
                    HardEdgeSiteEvidence(
                        source,
                        target,
                        "SOURCE_MISSING_OR_INVALID",
                        (),
                    )
                )
                continue

            sites = available[source].get(target, ())

            edges.append(
                HardEdgeSiteEvidence(
                    source,
                    target,
                    (
                        "LEXICAL_CANDIDATES"
                        if sites
                        else "NO_MATCHING_LEXICAL_SITE"
                    ),
                    sites,
                )
            )

        components.append(
            SCCImportSiteEvidence(
                members=component.members,
                internal_edges=tuple(edges),
                matched_edge_count=sum(
                    edge.status == "LEXICAL_CANDIDATES"
                    for edge in edges
                ),
                unresolved_edge_count=sum(
                    edge.status != "LEXICAL_CANDIDATES"
                    for edge in edges
                ),
            )
        )

    return CyclicImportSiteReport(
        topology=topology,
        components=tuple(components),
    )
