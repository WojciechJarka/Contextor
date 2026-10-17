
"""Bounded public projection of cycle-semantic evidence.

This module consumes approved immutable reports.
It performs no source reads, graph mutations or imports
of analyzed repository modules.

The projection does not establish atomic graph/source
binding or certify runtime import execution.
"""

from __future__ import annotations

from dataclasses import asdict

from .activation_view import analyze_cycle_activation_view
from .closure_witness import analyze_single_edge_cycle_closures
from .conditional_discovery import ConditionalDiscoveryReport
from .conditional_grouping import group_conditional_reexports
from .diagnostic_view import build_cycle_evidence_digest
from .edge_sites import CyclicImportSiteReport
from .weighted_closures import analyze_weighted_cycle_closures


PUBLIC_CYCLE_SEMANTICS_SCHEMA_VERSION = "1.0.0"


def _limit(value: int, name: str) -> int:
    if type(value) is not int or not 0 <= value <= 64:
        raise ValueError(
            name + " must be an integer in range 0..64"
        )
    return value


def project_cycle_semantics(
    import_sites: CyclicImportSiteReport,
    discovery: ConditionalDiscoveryReport,
    *,
    max_components: int = 8,
    max_edges: int = 3,
    max_groups: int = 3,
    max_witnesses: int = 3,
) -> dict:
    """Build a bounded semantic presentation without I/O.

    All truncation applies only to presentation, not
    to structural facts or original witness objects.

    The caller remains responsible for LIVE authority,
    cache generation and source fingerprint binding.
    """

    if not isinstance(import_sites, CyclicImportSiteReport):
        raise TypeError(
            "import_sites must be CyclicImportSiteReport"
        )

    if not isinstance(discovery, ConditionalDiscoveryReport):
        raise TypeError(
            "discovery must be ConditionalDiscoveryReport"
        )

    max_components = _limit(max_components, "max_components")
    max_edges = _limit(max_edges, "max_edges")
    max_groups = _limit(max_groups, "max_groups")
    max_witnesses = _limit(max_witnesses, "max_witnesses")

    activation = analyze_cycle_activation_view(import_sites)

    closures = analyze_single_edge_cycle_closures(
        activation,
        import_sites,
    )

    digest = build_cycle_evidence_digest(
        import_sites,
        activation,
        closures,
    )

    weighted = analyze_weighted_cycle_closures(digest)

    grouped = group_conditional_reexports(discovery)

    components = digest.components

    member_sets = tuple(
        frozenset(component.members)
        for component in components
    )

    edge_sets = tuple(
        frozenset(
            (edge.source, edge.target)
            for edge in component.edges
        )
        for component in components
    )

    grouped_by_component = {
        index: []
        for index in range(len(components))
    }

    for group in grouped.groups:
        matching = set()

        for witness in group.witnesses:
            chain = witness.assessment.chain
            chain_members = frozenset(chain[:-1])
            chain_edges = frozenset(
                zip(chain, chain[1:])
            )

            indices = [
                index
                for index, members in enumerate(member_sets)
                if chain_members <= members
                and chain_edges <= edge_sets[index]
            ]

            if len(indices) != 1:
                raise ValueError(
                    "conditional witness not bound "
                    "to exactly one structural SCC"
                )

            matching.add(indices[0])

        if len(matching) != 1:
            raise ValueError(
                "group witnesses disagree on SCC identity"
            )

        index = next(iter(matching))
        grouped_by_component[index].append(group)

    projected = []

    for index, component in enumerate(
        components[:max_components]
    ):
        weighted_component = weighted.components[index]

        if weighted_component.members != component.members:
            raise ValueError(
                "weighted and structural SCC identities differ"
            )

        group_rows = grouped_by_component[index]

        visible_edges = []

        for edge in component.edges[:max_edges]:
            visible_edges.append({
                "source": edge.source,
                "target": edge.target,
                "source_status": edge.lexical.status,
                "activation_classification": (
                    edge.activation.classification
                ),
                "in_direct_candidate_graph": (
                    edge.in_direct_candidate_graph
                ),
                "lexical_site_count": len(
                    edge.lexical.sites
                ),
                "lexical_sites": [
                    asdict(site)
                    for site in edge.lexical.sites[:2]
                ],
                "lexical_sites_truncated": (
                    len(edge.lexical.sites) > 2
                ),
            })

        visible_groups = []

        for group in group_rows[:max_groups]:
            selected = group.witnesses[:max_witnesses]

            visible_groups.append({
                "package_initializer": (
                    group.package_initializer
                ),
                "provider": group.provider,
                "export_name": group.export_name,
                "package_reexport_line": (
                    group.package_reexport_line
                ),
                "provider_definition_line": (
                    group.provider_definition_line
                ),
                "closing_module": group.closing_module,
                "closing_line": group.closing_line,
                "closing_column": group.closing_column,
                "outgoing_import_sites": [
                    list(site)
                    for site in group.outgoing_import_sites
                ],
                "witness_total": group.witness_count,
                "witnesses_returned": len(selected),
                "witnesses_truncated": (
                    len(selected) < group.witness_count
                ),
                "witnesses": [
                    {
                        "chain": list(
                            witness.assessment.chain
                        ),
                        "outgoing_target": (
                            witness.outgoing_target
                        ),
                        "hops": [
                            asdict(hop)
                            for hop in witness.assessment.hops
                        ],
                        "assessment_status": (
                            witness.assessment.status
                        ),
                        "assessment_reason": (
                            witness.assessment.reason
                        ),
                        "prefix_execution_status": (
                            witness.assessment
                            .prefix_execution_status
                        ),
                    }
                    for witness in selected
                ],
                "evidence_scope": group.evidence_scope,
                "runtime_execution_status": (
                    group.runtime_execution_status
                ),
            })

        projected.append({
            "members": list(component.members),
            "structural_kind": component.structural_kind,
            "diagnostic_category": component.category,
            "structural_edge_count": (
                component.structural_edge_count
            ),
            "matched_edge_count": (
                component.matched_edge_count
            ),
            "unresolved_edge_count": (
                component.unresolved_edge_count
            ),
            "direct_candidate_edge_count": (
                component.direct_candidate_edge_count
            ),
            "non_direct_candidate_edge_count": (
                component.non_direct_candidate_edge_count
            ),
            "direct_cyclic_component_count": len(
                component.direct_cyclic_components
            ),
            "single_non_direct_closure_count": (
                weighted_component
                .single_non_direct_witness_count
            ),
            "multiple_non_direct_closure_count": (
                weighted_component
                .multiple_non_direct_witness_count
            ),
            "edges": {
                "total": len(component.edges),
                "returned": len(visible_edges),
                "truncated": (
                    len(visible_edges) < len(component.edges)
                ),
                "items": visible_edges,
            },
            "conditional_reexports": {
                "group_total": len(group_rows),
                "group_returned": len(visible_groups),
                "truncated": (
                    len(visible_groups) < len(group_rows)
                ),
                "groups": visible_groups,
            },
            "runtime_execution_status": (
                component.runtime_execution_status
            ),
        })

    return {
        "schema_version": (
            PUBLIC_CYCLE_SEMANTICS_SCHEMA_VERSION
        ),
        "evidence_scope": (
            "STRUCTURAL_LEXICAL_CONDITIONAL_NOT_RUNTIME"
        ),
        "source_snapshot_binding": (
            grouped.source_snapshot_binding
        ),
        "canonical_graph_revision": None,
        "canonical_graph_revision_status": (
            "CALLER_MUST_SUPPLY_AUTHORITY"
        ),
        "runtime_execution_status": (
            "UNKNOWN_NOT_EVALUATED"
        ),
        "selection_coverage_status": (
            grouped.coverage_status
        ),
        "selection_scope": discovery.search_scope,
        "unavailable_source_modules": list(
            grouped.unavailable_source_modules
        ),
        "unresolved_lexical_edge_count": (
            grouped.unresolved_lexical_edge_count
        ),
        "examined_outgoing_count": (
            grouped.examined_outgoing_count
        ),
        "summary": {
            "cyclic_scc_total": len(components),
            "cyclic_scc_returned": len(projected),
            "components_truncated": (
                len(projected) < len(components)
            ),
            "conditional_group_total": (
                grouped.group_count
            ),
            "conditional_witness_total": (
                grouped.witness_count
            ),
        },
        "components": projected,
    }
