"""State-carrier contracts for immutable cycle semantics evidence."""

from __future__ import annotations

import hashlib
import pickle
from dataclasses import fields

import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.cycle_semantics.conditional_discovery import ConditionalDiscoveryReport
from contextor.core.cycle_semantics.contracts import (
    UNVERIFIED_RUNTIME_EXECUTION,
    UNVERIFIED_SOURCE_BINDING,
    CycleSemanticsSnapshot,
    fingerprint_hard_edges,
)
from contextor.core.cycle_semantics.edge_sites import (
    CyclicImportSiteReport,
    HardEdgeSiteEvidence,
    SCCImportSiteEvidence,
)
from contextor.core.cycle_semantics.scc import CyclicImportComponent, ImportCycleTopology


@pytest.fixture
def semantic_snapshot() -> CycleSemanticsSnapshot:
    members = ("pkg.a", "pkg.b")
    edges = (("pkg.a", "pkg.b"), ("pkg.b", "pkg.a"))
    topology = ImportCycleTopology(
        node_count=2,
        hard_edge_count=2,
        total_scc_count=1,
        cyclic_components=(CyclicImportComponent(
            members=members, internal_edges=edges, kind="MULTI_NODE_SCC"
        ),),
    )
    sites = CyclicImportSiteReport(
        topology=topology,
        components=(SCCImportSiteEvidence(
            members=members,
            internal_edges=tuple(
                HardEdgeSiteEvidence(source, target, "UNRESOLVED", ())
                for source, target in edges
            ),
            matched_edge_count=0,
            unresolved_edge_count=2,
        ),),
    )
    discovery = ConditionalDiscoveryReport(
        candidates=(),
        examined_outgoing_count=0,
        unavailable_source_modules=(),
        unresolved_lexical_edge_count=2,
        coverage_status="NO_CONDITIONAL_CANDIDATES",
    )
    return CycleSemanticsSnapshot(
        graph_sha256=fingerprint_hard_edges({"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}),
        cyclic_modules=members,
        observed_source_fingerprints=tuple(
            (module, hashlib.sha256(module.encode()).hexdigest()) for module in members
        ),
        source_issues=(),
        coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
        source_snapshot_binding=UNVERIFIED_SOURCE_BINDING,
        runtime_execution_status=UNVERIFIED_RUNTIME_EXECUTION,
        import_sites=sites,
        conditional_discovery=discovery,
    )


def test_new_canonical_family_defaults() -> None:
    first = RepositoryAnalysisState()
    second = RepositoryAnalysisState()
    assert first.cycle_semantics is None
    assert first.cycle_semantics_state == "deferred"
    assert first.cycle_semantics_invalidation_reason is None
    assert first.cycles == [] and first.cycles_state == "deferred"
    assert first.cycles is not second.cycles


def test_structural_fresh_does_not_imply_semantic_fresh() -> None:
    state = RepositoryAnalysisState(cycles_state="fresh")
    assert state.cycles_state == "fresh"
    assert state.cycle_semantics is None
    assert state.cycle_semantics_state == "deferred"


def test_canonical_state_accepts_immutable_evidence(
    semantic_snapshot: CycleSemanticsSnapshot,
) -> None:
    cycles = [["pkg.a", "pkg.b", "pkg.a"]]
    state = RepositoryAnalysisState(
        cycles=cycles, cycle_semantics=semantic_snapshot, cycle_semantics_state="deferred"
    )
    assert state.cycle_semantics is semantic_snapshot
    assert state.cycle_semantics_state == "deferred"
    assert state.cycles is cycles


def test_clone_preserves_immutable_evidence_identity(
    semantic_snapshot: CycleSemanticsSnapshot,
) -> None:
    state = RepositoryAnalysisState(cycle_semantics=semantic_snapshot)
    candidate = state.clone_for_update()
    assert candidate is not state
    assert candidate.cycle_semantics is state.cycle_semantics
    candidate.cycle_semantics_state = "stale"
    candidate.cycle_semantics_invalidation_reason = "source changed"
    assert state.cycle_semantics_state == "deferred"
    assert state.cycle_semantics_invalidation_reason is None


def test_state_pickle_roundtrip_preserves_family(
    semantic_snapshot: CycleSemanticsSnapshot,
) -> None:
    cycles = [["pkg.a", "pkg.b", "pkg.a"]]
    state = RepositoryAnalysisState(
        cycles=cycles,
        cycle_semantics=semantic_snapshot,
        cycle_semantics_state="stale",
        cycle_semantics_invalidation_reason="source changed",
    )
    restored = pickle.loads(pickle.dumps(state))
    assert restored.cycle_semantics == semantic_snapshot
    assert isinstance(restored.cycle_semantics, CycleSemanticsSnapshot)
    assert isinstance(restored.cycle_semantics.import_sites, CyclicImportSiteReport)
    assert isinstance(restored.cycle_semantics.conditional_discovery, ConditionalDiscoveryReport)
    assert restored.cycle_semantics_state == "stale"
    assert restored.cycle_semantics_invalidation_reason == "source changed"
    assert restored.cycles == cycles


def test_legacy_missing_family_is_not_fresh() -> None:
    state = RepositoryAnalysisState(cycles_state="fresh")
    for name in (
        "cycle_semantics", "cycle_semantics_state", "cycle_semantics_invalidation_reason"
    ):
        del state.__dict__[name]
    restored = pickle.loads(pickle.dumps(state))
    assert restored.cycle_semantics is None
    assert restored.cycle_semantics_state == "deferred"
    assert restored.cycle_semantics_invalidation_reason is None
    assert restored.cycle_semantics_state != "fresh"
    assert not isinstance(restored.cycle_semantics, CycleSemanticsSnapshot)
    candidate = restored.clone_for_update()
    assert candidate.cycle_semantics is None
    assert candidate.cycle_semantics_state == "deferred"


def test_existing_constructor_compatibility() -> None:
    previous_fields = (
        "modules", "artifacts", "reexport_facts_by_module", "dependency_graph",
        "artifact_consumption", "artifact_consumption_state", "layer_information",
        "metrics", "file_state", "module_parse_freshness", "syntax_diagnostics_by_path",
        "syntax_diagnostics_state", "module_usages", "module_usages_manifest",
        "lineage_facts_by_source", "lineage_facts_state",
        "lineage_facts_semantic_version", "lineage_owner_source_index",
        "lineage_source_owner_index", "lineage_query_index_state",
        "lineage_semantic_anchor_bindings_complete", "topology_analytics",
        "topology_metrics_state", "cached_analytics", "cached_analytics_state",
        "cycles", "cycles_state", "collision_facts", "collisions", "collisions_state",
        "dependency_matrix", "dependency_matrix_state", "shared_usage_clusters",
        "shared_usage_clusters_state", "trie", "package_root",
    )
    assert tuple(field.name for field in fields(RepositoryAnalysisState)) == (
        *previous_fields, "cycle_semantics", "cycle_semantics_state",
        "cycle_semantics_invalidation_reason",
    )
    seed = RepositoryAnalysisState()
    values = tuple(getattr(seed, name) for name in previous_fields)
    state = RepositoryAnalysisState(*values)
    assert all(getattr(state, name) is value for name, value in zip(previous_fields, values))
    assert (state.cycle_semantics, state.cycle_semantics_state,
            state.cycle_semantics_invalidation_reason) == (None, "deferred", None)


def test_invalidating_candidate_does_not_mutate_original(
    semantic_snapshot: CycleSemanticsSnapshot,
) -> None:
    state = RepositoryAnalysisState(cycle_semantics=semantic_snapshot)
    candidate = state.clone_for_update()
    candidate.cycle_semantics_state = "stale"
    candidate.cycle_semantics_invalidation_reason = "graph changed"
    assert state.cycle_semantics is semantic_snapshot
    assert state.cycle_semantics_state == "deferred"
    assert state.cycle_semantics_invalidation_reason is None
    assert candidate.cycle_semantics is semantic_snapshot
    assert candidate.cycle_semantics_state == "stale"
    assert candidate.cycle_semantics_invalidation_reason == "graph changed"
