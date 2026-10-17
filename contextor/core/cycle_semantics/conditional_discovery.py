"""Bounded discovery of conditional delayed-reexport candidates.

Structural and lexical evidence is not execution evidence.
Inputs do not authenticate an atomic canonical source snapshot.
"""

from __future__ import annotations

import ast
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from contextor.core.source import ParsedSourceInput

from .conditional_export import (
    ConditionalReexportAssessment,
    _exact_hop,
    _logical_module,
    analyze_conditional_reexport_order,
)
from .edge_sites import CyclicImportSiteReport
from .package_layout import build_package_layout


@dataclass(frozen=True)
class DiscoveredConditionalReexport:
    package_initializer: str
    provider: str
    export_name: str
    outgoing_target: str
    assessment: ConditionalReexportAssessment


@dataclass(frozen=True)
class ConditionalDiscoveryReport:
    candidates: tuple[DiscoveredConditionalReexport, ...]
    examined_outgoing_count: int
    unavailable_source_modules: tuple[str, ...]
    unresolved_lexical_edge_count: int
    coverage_status: str
    search_scope: str = (
        "ONE_SHORTEST_VALIDATED_PATH_PER_PROVIDER_OUTGOING"
    )
    source_snapshot_binding: str = (
        "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    )
    runtime_execution_status: str = (
        "UNKNOWN_NOT_EVALUATED"
    )


def _usable_source(
    source: object,
) -> ast.Module | None:
    if (
        not isinstance(source, ParsedSourceInput)
        or not isinstance(source.tree, ast.Module)
        or not isinstance(source.source_fingerprint, str)
        or len(source.source_fingerprint) != 64
        or any(
            char not in "0123456789abcdef"
            for char in source.source_fingerprint
        )
    ):
        return None

    count = 0

    for _ in ast.walk(source.tree):
        count += 1

        if count > 100_000:
            return None

    try:
        compile(
            source.tree,
            "<conditional_discovery>",
            "exec",
            dont_inherit=True,
        )
    except (
        SyntaxError,
        TypeError,
        ValueError,
        RecursionError,
        OverflowError,
    ):
        return None

    return source.tree


def _shortest_return_path(
    start: str,
    package: str,
    provider: str,
    export_name: str,
    adjacency: Mapping[str, tuple[str, ...]],
    hops: Mapping[tuple[str, str], object],
) -> tuple[str, ...] | None:
    """Iterative BFS with deterministic lexical tie resolution."""
    if start in {package, provider}:
        return None

    queue = deque([start])
    previous: dict[str, str | None] = {
        start: None,
    }

    while queue:
        current = queue.popleft()

        if current == package:
            break

        for target in adjacency.get(current, ()):
            if target == provider:
                continue

            if (
                target == package
                and hops[(current, target)].requested_member
                != export_name
            ):
                continue

            if target in previous:
                continue

            previous[target] = current
            queue.append(target)

    if package not in previous:
        return None

    reverse_path = []
    current: str | None = package

    while current is not None:
        reverse_path.append(current)
        current = previous[current]

    return tuple(reversed(reverse_path))


def discover_conditional_reexports(
    import_sites: CyclicImportSiteReport,
    parsed_sources: Mapping[str, ParsedSourceInput],
    indexed_module_ids: Iterable[str],
    *,
    max_searches: int = 256,
) -> ConditionalDiscoveryReport:
    """Discover bounded candidate chains, then validate with C26F.

    The caller must supply a coherent candidate graph and source
    collection. This function cannot establish LIVE revision
    atomicity or runtime execution.
    """

    if not isinstance(import_sites, CyclicImportSiteReport):
        raise TypeError(
            "import_sites must be CyclicImportSiteReport"
        )

    if not isinstance(parsed_sources, Mapping):
        raise TypeError(
            "parsed_sources must be a mapping"
        )

    if (
        type(max_searches) is not int
        or not 1 <= max_searches <= 4096
    ):
        raise ValueError(
            "max_searches must be in range 1..4096"
        )

    layout = build_package_layout(indexed_module_ids)

    layout_by_name = {
        node.name: node
        for node in layout.nodes
    }

    candidates = []
    seen = set()
    unavailable = set()
    unresolved = 0
    examined = 0
    truncated = False

    for component in sorted(
        import_sites.components,
        key=lambda item: item.members,
    ):
        members = set(component.members)

        trees = {}

        for member in sorted(members):
            tree = _usable_source(
                parsed_sources.get(member)
            )

            if tree is None:
                unavailable.add(member)
            else:
                trees[member] = tree

        edge_records = {
            (edge.source, edge.target): edge
            for edge in component.internal_edges
        }

        eligible_hops = {}

        for source, target in sorted(edge_records):
            edge = edge_records[(source, target)]

            if edge.status != "LEXICAL_CANDIDATES":
                unresolved += 1
                continue

            if source not in trees or target not in trees:
                continue

            source_layout = layout_by_name.get(
                _logical_module(source)
            )
            target_layout = layout_by_name.get(
                _logical_module(target)
            )

            if (
                source_layout is None
                or target_layout is None
                or source_layout.kind not in {
                    "REGULAR_PACKAGE",
                    "MODULE_FILE",
                }
                or target_layout.kind not in {
                    "REGULAR_PACKAGE",
                    "MODULE_FILE",
                }
                or source_layout.indexed_module_ids
                != (source,)
                or target_layout.indexed_module_ids
                != (target,)
            ):
                continue

            hop = _exact_hop(
                trees,
                source,
                target,
            )

            if hop is None:
                continue

            if not any(
                site.line == hop.line
                and site.column == hop.column
                and site.form == "IMPORT_FROM"
                and site.match_kind == "FROM_BASE"
                and site.activation_scope
                == "MODULE_TOP_LEVEL"
                and not site.controls
                for site in edge.sites
            ):
                continue

            eligible_hops[(source, target)] = hop

        adjacency_dict: dict[str, list[str]] = {}

        for source, target in sorted(eligible_hops):
            adjacency_dict.setdefault(
                source, []
            ).append(target)

        adjacency = {
            source: tuple(sorted(set(targets)))
            for source, targets
            in adjacency_dict.items()
        }

        package_initializers = sorted(
            member
            for member in members
            if member.endswith(".__init__")
            and member in trees
            and (
                node := layout_by_name.get(
                    _logical_module(member)
                )
            ) is not None
            and node.kind == "REGULAR_PACKAGE"
            and node.indexed_module_ids == (member,)
        )

        for package in package_initializers:
            for provider in adjacency.get(package, ()):
                first_hop = eligible_hops[
                    (package, provider)
                ]

                export_name = first_hop.requested_member

                provider_tree = trees[provider]

                definitions = [
                    statement
                    for statement in provider_tree.body
                    if isinstance(
                        statement,
                        ast.FunctionDef,
                    )
                    and statement.name == export_name
                ]

                if len(definitions) != 1:
                    continue

                definition_line = definitions[0].lineno

                for outgoing in adjacency.get(provider, ()):
                    outgoing_hop = eligible_hops[
                        (provider, outgoing)
                    ]

                    if outgoing_hop.line >= definition_line:
                        continue

                    if examined >= max_searches:
                        truncated = True
                        break

                    examined += 1

                    return_path = _shortest_return_path(
                        outgoing,
                        package,
                        provider,
                        export_name,
                        adjacency,
                        eligible_hops,
                    )

                    if return_path is None:
                        continue

                    chain = (
                        package,
                        provider,
                    ) + return_path

                    if (
                        len(chain) < 4
                        or len(set(chain[:-1]))
                        != len(chain) - 1
                    ):
                        continue

                    identity = (
                        chain,
                        export_name,
                    )

                    if identity in seen:
                        continue

                    seen.add(identity)

                    assessment = (
                        analyze_conditional_reexport_order(
                            trees,
                            chain,
                            export_name,
                        )
                    )

                    if assessment.status != (
                        "CONDITIONAL_DELAYED_REEXPORT"
                    ):
                        continue

                    candidates.append(
                        DiscoveredConditionalReexport(
                            package_initializer=package,
                            provider=provider,
                            export_name=export_name,
                            outgoing_target=outgoing,
                            assessment=assessment,
                        )
                    )

                if truncated:
                    break

            if truncated:
                break

        if truncated:
            break

    if truncated:
        coverage = "PARTIAL_SEARCH_LIMIT"
    elif unavailable or unresolved:
        coverage = "PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE"
    else:
        coverage = "BOUNDED_SELECTION_COMPLETE"

    return ConditionalDiscoveryReport(
        candidates=tuple(candidates),
        examined_outgoing_count=examined,
        unavailable_source_modules=tuple(
            sorted(unavailable)
        ),
        unresolved_lexical_edge_count=unresolved,
        coverage_status=coverage,
    )
