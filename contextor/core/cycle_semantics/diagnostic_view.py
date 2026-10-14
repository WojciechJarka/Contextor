"""Immutable structural and lexical cycle-evidence digest.

Combines already approved analysis reports without execution or source reads.
No runtime safety, failure or canonical warning policy is inferred.
"""

from __future__ import annotations

from dataclasses import dataclass

from .activation_view import (
    CycleActivationViewReport,
    EdgeActivationView,
    analyze_cycle_activation_view,
)
from .closure_witness import (
    NonDirectClosureWitness,
    SingleEdgeClosureReport,
    analyze_single_edge_cycle_closures,
)
from .edge_sites import (
    CyclicImportSiteReport,
    HardEdgeSiteEvidence,
)
from .scc import CyclicImportComponent, ImportCycleTopology


@dataclass(frozen=True)
class CycleDiagnosticEdge:
    source: str
    target: str
    lexical: HardEdgeSiteEvidence
    activation: EdgeActivationView
    in_direct_candidate_graph: bool
    single_edge_closure: NonDirectClosureWitness | None


@dataclass(frozen=True)
class SCCCycleDiagnosis:
    members: tuple[str, ...]
    structural_kind: str
    category: str
    structural_edge_count: int
    matched_edge_count: int
    unresolved_edge_count: int
    direct_candidate_edge_count: int
    non_direct_candidate_edge_count: int
    direct_cyclic_components: tuple[CyclicImportComponent, ...]
    single_edge_closures: tuple[NonDirectClosureWitness, ...]
    non_direct_without_direct_return: tuple[tuple[str, str], ...]
    edges: tuple[CycleDiagnosticEdge, ...]
    runtime_execution_status: str = "UNKNOWN_NOT_EVALUATED"


@dataclass(frozen=True)
class CycleEvidenceDigest:
    structural_topology: ImportCycleTopology
    components: tuple[SCCCycleDiagnosis, ...]
    evidence_scope: str = "STRUCTURAL_AND_LEXICAL_NOT_RUNTIME"
    source_snapshot_binding: str = "NOT_VERIFIED_BY_DIGEST"


def build_cycle_evidence_digest(
    sites: CyclicImportSiteReport,
    activation: CycleActivationViewReport,
    closures: SingleEdgeClosureReport,
) -> CycleEvidenceDigest:
    """Join consistent immutable reports without modifying original graphs.

    Recomputing the approved pure projections rejects mismatched or altered
    reports rather than silently combining inconsistent source evidence.
    It cannot authenticate a canonical LIVE revision or source fingerprints.
    """
    if not isinstance(sites, CyclicImportSiteReport):
        raise TypeError("sites must be CyclicImportSiteReport")
    if not isinstance(activation, CycleActivationViewReport):
        raise TypeError("activation must be CycleActivationViewReport")
    if not isinstance(closures, SingleEdgeClosureReport):
        raise TypeError("closures must be SingleEdgeClosureReport")

    if activation != analyze_cycle_activation_view(sites):
        raise ValueError("activation evidence differs from lexical sources")

    if closures != analyze_single_edge_cycle_closures(
        activation,
        sites,
    ):
        raise ValueError("closure evidence differs from activation sources")

    topology = sites.topology

    if not (
        len(topology.cyclic_components)
        == len(sites.components)
        == len(activation.components)
        == len(closures.components)
    ):
        raise ValueError("SCC component cardinalities differ")

    output: list[SCCCycleDiagnosis] = []

    for structural, source, view, closure in zip(
        topology.cyclic_components,
        sites.components,
        activation.components,
        closures.components,
    ):
        if not (
            structural.members
            == source.members
            == view.members
            == closure.members
        ):
            raise ValueError("canonical SCC member identities differ")

        source_ids = tuple(
            (item.source, item.target)
            for item in source.internal_edges
        )

        view_ids = tuple(
            (item.source, item.target)
            for item in view.edges
        )

        if (
            source_ids != structural.internal_edges
            or view_ids != structural.internal_edges
        ):
            raise ValueError("structural internal edge identities differ")

        matched = sum(
            item.status == "LEXICAL_CANDIDATES"
            for item in source.internal_edges
        )
        unresolved = len(source.internal_edges) - matched

        if (
            source.matched_edge_count != matched
            or source.unresolved_edge_count != unresolved
        ):
            raise ValueError("lexical evidence counts differ")

        direct = set(view.unguarded_direct_edges)

        witnesses = {
            (item.source, item.target): item
            for item in closure.single_edge_witnesses
        }

        edge_rows = tuple(
            CycleDiagnosticEdge(
                source=lexical.source,
                target=lexical.target,
                lexical=lexical,
                activation=classification,
                in_direct_candidate_graph=(
                    (lexical.source, lexical.target) in direct
                ),
                single_edge_closure=witnesses.get(
                    (lexical.source, lexical.target)
                ),
            )
            for lexical, classification in zip(
                source.internal_edges,
                view.edges,
            )
        )

        if view.unguarded_direct_topology.cyclic_components:
            category = "UNGUARDED_DIRECT_CYCLIC_SUBGRAPH"
        elif closure.single_edge_witnesses:
            category = (
                "ACYCLIC_DIRECT_SUBGRAPH_WITH_SINGLE_EDGE_CLOSURES"
            )
        else:
            category = (
                "ACYCLIC_DIRECT_SUBGRAPH_NO_SINGLE_EDGE_CLOSURE"
            )

        output.append(
            SCCCycleDiagnosis(
                members=structural.members,
                structural_kind=structural.kind,
                category=category,
                structural_edge_count=len(edge_rows),
                matched_edge_count=matched,
                unresolved_edge_count=unresolved,
                direct_candidate_edge_count=len(direct),
                non_direct_candidate_edge_count=(
                    len(edge_rows) - len(direct)
                ),
                direct_cyclic_components=(
                    view.unguarded_direct_topology.cyclic_components
                ),
                single_edge_closures=closure.single_edge_witnesses,
                non_direct_without_direct_return=(
                    closure.non_direct_without_direct_return
                ),
                edges=edge_rows,
            )
        )

    return CycleEvidenceDigest(topology, tuple(output))
