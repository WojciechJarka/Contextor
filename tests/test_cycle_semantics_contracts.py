"""Isolated contracts for immutable cycle semantics evidence."""

from __future__ import annotations

import hashlib
import pickle
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from contextor.core.cycle_semantics.conditional_discovery import (
    ConditionalDiscoveryReport,
)
from contextor.core.cycle_semantics.contracts import (
    CYCLE_SEMANTICS_CONTRACT_VERSION,
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
from contextor.core.cycle_semantics.scc import (
    CyclicImportComponent,
    ImportCycleTopology,
)


CONTRACT_GRAPH = {"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}
CONTRACT_MODULES = ("pkg.a", "pkg.b")
FINGERPRINTS = tuple(
    (module, hashlib.sha256(module.encode()).hexdigest())
    for module in CONTRACT_MODULES
)


def _reports() -> tuple[CyclicImportSiteReport, ConditionalDiscoveryReport]:
    component = CyclicImportComponent(
        members=CONTRACT_MODULES,
        internal_edges=(("pkg.a", "pkg.b"), ("pkg.b", "pkg.a")),
        kind="MULTI_NODE_SCC",
    )
    topology = ImportCycleTopology(
        node_count=2,
        hard_edge_count=2,
        total_scc_count=1,
        cyclic_components=(component,),
    )
    import_sites = CyclicImportSiteReport(
        topology=topology,
        components=(SCCImportSiteEvidence(
            members=CONTRACT_MODULES,
            internal_edges=(
                HardEdgeSiteEvidence("pkg.a", "pkg.b", "UNRESOLVED", ()),
                HardEdgeSiteEvidence("pkg.b", "pkg.a", "UNRESOLVED", ()),
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
    return import_sites, discovery


def _snapshot(**overrides: object) -> CycleSemanticsSnapshot:
    import_sites, discovery = _reports()
    values = dict(
        graph_sha256=fingerprint_hard_edges(CONTRACT_GRAPH),
        cyclic_modules=CONTRACT_MODULES,
        observed_source_fingerprints=FINGERPRINTS,
        source_issues=(),
        coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
        source_snapshot_binding=UNVERIFIED_SOURCE_BINDING,
        runtime_execution_status=UNVERIFIED_RUNTIME_EXECUTION,
        import_sites=import_sites,
        conditional_discovery=discovery,
    )
    values.update(overrides)
    return CycleSemanticsSnapshot(**values)


def test_graph_fingerprint_is_order_independent_and_does_not_mutate() -> None:
    graph = {"pkg.b": ["pkg.a", "pkg.a"], "pkg.a": ("pkg.b",)}
    before = {key: tuple(value) for key, value in graph.items()}
    assert fingerprint_hard_edges(graph) == fingerprint_hard_edges(CONTRACT_GRAPH)
    assert {key: tuple(value) for key, value in graph.items()} == before


def test_graph_fingerprint_changes_for_real_edge() -> None:
    changed = {"pkg.a": {"pkg.b", "pkg.c"}, "pkg.b": {"pkg.a"}}
    assert fingerprint_hard_edges(changed) != fingerprint_hard_edges(CONTRACT_GRAPH)


@pytest.mark.parametrize(
    ("graph", "error"),
    [
        ({"": ["pkg.a"]}, ValueError),
        ({1: ["pkg.a"]}, ValueError),
        ({"pkg.a": [""]}, ValueError),
        ({"pkg.a": [1]}, ValueError),
        ({"pkg.a": "pkg.b"}, TypeError),
        ({"pkg.a": {"pkg.b": True}}, TypeError),
        ([], TypeError),
    ],
)
def test_graph_rejects_invalid_identity_or_collection(graph: object, error: type[Exception]) -> None:
    with pytest.raises(error):
        fingerprint_hard_edges(graph)


def test_complete_snapshot_preserves_exact_reports() -> None:
    snapshot = _snapshot()
    reports = _reports()
    assert snapshot.import_sites == reports[0]
    assert snapshot.conditional_discovery == reports[1]
    assert snapshot.schema_version == CYCLE_SEMANTICS_CONTRACT_VERSION
    assert (snapshot.cyclic_module_count, snapshot.observed_source_count, snapshot.unobserved_source_count) == (2, 2, 0)
    assert not hasattr(snapshot, "freshness")
    assert not hasattr(snapshot, "materialized_revision")


def test_snapshot_fields_are_frozen() -> None:
    snapshot = _snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot.coverage_status = "PARTIAL_SOURCE_EVIDENCE"


@pytest.mark.parametrize(
    "changes",
    [
        {"observed_source_fingerprints": FINGERPRINTS[:1]},
        {"source_issues": (("pkg.a", "missing"),)},
    ],
)
def test_complete_coverage_rejects_missing_sources_or_issues(changes: dict) -> None:
    with pytest.raises(ValueError, match="Complete source coverage"):
        _snapshot(**changes)


def test_partial_coverage_preserves_missing_sources_and_issues() -> None:
    snapshot = _snapshot(
        observed_source_fingerprints=FINGERPRINTS[:1],
        source_issues=(("pkg.b", "missing"),),
        coverage_status="PARTIAL_SOURCE_EVIDENCE",
    )
    assert snapshot.unobserved_source_count == 1
    assert snapshot.source_issues == (("pkg.b", "missing"),)
    assert snapshot.coverage_status == "PARTIAL_SOURCE_EVIDENCE"


@pytest.mark.parametrize(
    ("fingerprints", "error"),
    [
        ((FINGERPRINTS[0], FINGERPRINTS[0]), "Duplicate source fingerprint"),
        (tuple(reversed(FINGERPRINTS)), "Source fingerprints must be sorted"),
        ((("pkg.a", "bad"),), "Invalid observed source fingerprint"),
        ((("pkg.c", FINGERPRINTS[0][1]),), "outside cyclic cohort"),
    ],
)
def test_bad_source_fingerprints_rejected(fingerprints: tuple, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        _snapshot(observed_source_fingerprints=fingerprints, coverage_status="PARTIAL_SOURCE_EVIDENCE")


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"graph_sha256": "x"}, "Invalid graph SHA-256"),
        ({"schema_version": "2.0.0"}, "Unsupported cycle semantics contract version"),
        ({"source_snapshot_binding": "ATOMIC"}, "Unsupported source binding claim"),
        ({"runtime_execution_status": "SAFE"}, "Unsupported runtime execution claim"),
    ],
)
def test_unsupported_claims_rejected(changes: dict, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        _snapshot(**changes)


def test_topology_must_match_cyclic_modules() -> None:
    with pytest.raises(ValueError, match="topology and cyclic cohort differ"):
        _snapshot(
            cyclic_modules=("pkg.a",),
            observed_source_fingerprints=FINGERPRINTS[:1],
        )


def test_pickle_roundtrip_preserves_snapshot() -> None:
    snapshot = _snapshot()
    restored = pickle.loads(pickle.dumps(snapshot))
    assert restored == snapshot
    assert restored.import_sites.topology.cyclic_components[0].members == CONTRACT_MODULES


def test_cold_contract_import_does_not_import_ui_or_repo_generator() -> None:
    code = (
        "import sys; import contextor.core.cycle_semantics.contracts; "
        "assert not any(name.startswith(('contextor.ui', "
        "'contextor.repo_generator')) for name in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_rejects_mutable_conditional_discovery() -> None:
    with pytest.raises(
        TypeError,
        match="conditional_discovery must be",
    ):
        _snapshot(
            conditional_discovery={
                "candidates": [],
            },
        )


def test_rejects_duck_typed_import_sites() -> None:
    import_sites, _ = _reports()

    with pytest.raises(
        TypeError,
        match="import_sites must be",
    ):
        _snapshot(
            import_sites=SimpleNamespace(
                topology=import_sites.topology,
            ),
        )


def test_rejects_nested_mutable_conditional_evidence() -> None:
    _, discovery = _reports()

    bad_discovery = replace(
        discovery,
        candidates=[],
    )

    with pytest.raises(
        TypeError,
        match="mutable or unsupported evidence",
    ):
        _snapshot(
            conditional_discovery=bad_discovery,
        )


def test_rejects_nested_mutable_import_evidence() -> None:
    import_sites, _ = _reports()

    bad_sites = replace(
        import_sites,
        components=list(import_sites.components),
    )

    with pytest.raises(
        TypeError,
        match="mutable or unsupported evidence",
    ):
        _snapshot(
            import_sites=bad_sites,
        )


def test_rejects_component_topology_divergence() -> None:
    import_sites, _ = _reports()

    bad_sites = replace(
        import_sites,
        components=(),
    )

    with pytest.raises(
        ValueError,
        match="Import-site components and topology differ",
    ):
        _snapshot(
            import_sites=bad_sites,
        )
