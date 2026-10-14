"""Candidate import activation topology for source-attributed cyclic SCCs.

Retains every canonical hard edge. Top-level lexical sites can only support
candidate import activation, never runtime reachability or safety decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .edge_sites import CyclicImportSiteReport
from .scc import ImportCycleTopology, analyze_import_cycle_topology

_DIRECT = frozenset({"DIRECT_MODULE", "FROM_BASE"})
_INDIRECT = frozenset({"OPTIONAL_FROM_CHILD", "PARENT_INITIALIZER"})


@dataclass(frozen=True)
class EdgeActivationView:
    source: str
    target: str
    source_status: str
    classification: str
    site_count: int
    unguarded_direct_count: int
    function_scoped_count: int
    guarded_top_level_count: int
    other_scoped_count: int
    indirect_candidate_count: int


@dataclass(frozen=True)
class SCCActivationView:
    members: tuple[str, ...]
    edges: tuple[EdgeActivationView, ...]
    unguarded_direct_edges: tuple[tuple[str, str], ...]
    unguarded_direct_topology: ImportCycleTopology
    unresolved_edges: int
    evidence_scope: str = "INTERNAL_UNGUARDED_LEXICAL_SUBGRAPH_ONLY"


@dataclass(frozen=True)
class CycleActivationViewReport:
    structural_topology: ImportCycleTopology
    components: tuple[SCCActivationView, ...]
    evidence_scope: str = "ACTIVATION_CANDIDATES_NOT_RUNTIME_SAFETY"


def analyze_cycle_activation_view(
    import_sites: CyclicImportSiteReport,
) -> CycleActivationViewReport:
    """Project each retained internal edge onto candidate activation classes.

    Even a cycle-free unguarded subset cannot certify the original SCC as safe:
    a function-scoped import may execute during module initialization.
    """
    if not isinstance(import_sites, CyclicImportSiteReport):
        raise TypeError("import_sites must be CyclicImportSiteReport")

    views: list[SCCActivationView] = []

    for component in import_sites.components:
        edge_views: list[EdgeActivationView] = []
        selected: dict[str, set[str]] = {
            member: set() for member in component.members
        }

        for edge in component.internal_edges:
            sites = edge.sites

            direct = sum(
                site.activation_scope == "MODULE_TOP_LEVEL"
                and site.match_kind in _DIRECT
                for site in sites
            )

            functions = sum(
                site.activation_scope == "FUNCTION_SCOPED"
                for site in sites
            )

            guarded = sum(
                site.activation_scope == "GUARDED_TOP_LEVEL"
                for site in sites
            )

            other = sum(
                site.activation_scope == "OTHER_SCOPED"
                for site in sites
            )

            indirect = sum(
                site.match_kind in _INDIRECT
                for site in sites
            )

            unguarded_indirect = any(
                site.activation_scope == "MODULE_TOP_LEVEL"
                and site.match_kind in _INDIRECT
                for site in sites
            )

            if edge.status != "LEXICAL_CANDIDATES" or not sites:
                classification = "UNRESOLVED_SOURCE_SITE"

            elif direct:
                classification = "UNGUARDED_DIRECT_CANDIDATE"
                selected[edge.source].add(edge.target)

            elif unguarded_indirect:
                classification = "INDIRECT_TOP_LEVEL_CANDIDATE"

            elif guarded:
                classification = "GUARDED_TOP_LEVEL_CANDIDATE"

            elif other:
                classification = "OTHER_SCOPE_CANDIDATE"

            elif functions:
                classification = "CALL_DEPENDENT_CANDIDATE"

            else:
                classification = "UNRECOGNIZED_SITE_SEMANTICS"

            edge_views.append(
                EdgeActivationView(
                    edge.source,
                    edge.target,
                    edge.status,
                    classification,
                    len(sites),
                    direct,
                    functions,
                    guarded,
                    other,
                    indirect,
                )
            )

        direct_edges = tuple(
            (source, target)
            for source in sorted(selected)
            for target in sorted(selected[source])
        )

        views.append(
            SCCActivationView(
                component.members,
                tuple(edge_views),
                direct_edges,
                analyze_import_cycle_topology(selected),
                sum(
                    edge.classification in {
                        "UNRESOLVED_SOURCE_SITE",
                        "UNRECOGNIZED_SITE_SEMANTICS",
                    }
                    for edge in edge_views
                ),
            )
        )

    return CycleActivationViewReport(
        structural_topology=import_sites.topology,
        components=tuple(views),
    )
