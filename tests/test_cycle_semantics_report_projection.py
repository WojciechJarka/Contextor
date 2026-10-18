"""Pure historical report projection from immutable cycle evidence."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import replace

import pytest

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
from contextor.core.cycle_semantics.report_projection import (
    REPORT_LIVE_BINDING_STATUS,
    build_cycle_semantics_report,
)
from contextor.core.cycle_semantics.scc import CyclicImportComponent, ImportCycleTopology
from contextor.core.errors import AnalysisCancelled


HEADER = {"schema_version": "1.0", "generated_at": "synthetic-time", "data_source": "global"}


def _snapshot(*, cyclic: bool = True) -> CycleSemanticsSnapshot:
    if cyclic:
        members = ("pkg.a", "pkg.b")
        edges = (("pkg.a", "pkg.b"), ("pkg.b", "pkg.a"))
        hard_edges = {"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}
        components = (CyclicImportComponent(
            members=members, internal_edges=edges, kind="MULTI_NODE_SCC",
        ),)
        site_components = (SCCImportSiteEvidence(
            members=members,
            internal_edges=tuple(
                HardEdgeSiteEvidence(source, target, "UNRESOLVED", ())
                for source, target in edges
            ),
            matched_edge_count=0,
            unresolved_edge_count=2,
        ),)
    else:
        members = ()
        edges = ()
        hard_edges = {}
        components = ()
        site_components = ()
    topology = ImportCycleTopology(
        node_count=len(members), hard_edge_count=len(edges),
        total_scc_count=(1 if cyclic else 0), cyclic_components=components,
    )
    sites = CyclicImportSiteReport(topology=topology, components=site_components)
    discovery = ConditionalDiscoveryReport(
        candidates=(), examined_outgoing_count=0,
        unavailable_source_modules=(), unresolved_lexical_edge_count=len(edges),
        coverage_status="NO_CONDITIONAL_CANDIDATES",
    )
    return CycleSemanticsSnapshot(
        graph_sha256=fingerprint_hard_edges(hard_edges),
        cyclic_modules=members,
        observed_source_fingerprints=tuple(
            (module, hashlib.sha256(module.encode()).hexdigest()) for module in members
        ),
        source_issues=(), coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
        source_snapshot_binding=UNVERIFIED_SOURCE_BINDING,
        runtime_execution_status=UNVERIFIED_RUNTIME_EXECUTION,
        import_sites=sites, conditional_discovery=discovery,
    )


def _build(snapshot, freshness="fresh", reason=None):
    return build_cycle_semantics_report(
        snapshot, freshness, reason, report_header=HEADER,
    )


def test_complete_cycle_report_has_bounded_projection_and_evidence() -> None:
    snapshot = _snapshot()
    report = _build(snapshot)
    assert report["schema_version"] == "1.0.0"
    assert report["status"] == "ok"
    assert report["projection"]["summary"]["cyclic_scc_total"] == 1
    assert report["projection"]["components"]
    assert report["semantic_evidence"]["cyclic_module_count"] == 2
    assert report["semantic_evidence"]["observed_source_count"] == 2
    assert report["semantic_evidence"]["source_fingerprints"] == [
        {"module_id": module, "sha256": digest}
        for module, digest in snapshot.observed_source_fingerprints
    ]
    assert report["semantic_evidence"]["graph_sha256"] == snapshot.graph_sha256


def test_complete_empty_cycle_report_is_not_unavailable() -> None:
    report = _build(_snapshot(cyclic=False))
    assert report["status"] == "ok"
    assert report["semantic_evidence"]["cyclic_module_count"] == 0
    assert report["projection"]["summary"]["cyclic_scc_total"] == 0


def test_missing_evidence_is_unavailable() -> None:
    report = _build(None, "deferred")
    assert report["status"] == "unavailable"
    assert report["semantic_evidence"]["available"] is False
    assert report["projection"] is None


def test_missing_evidence_cannot_be_fresh() -> None:
    with pytest.raises(ValueError, match="Missing semantic evidence"):
        _build(None, "fresh")


def test_fresh_evidence_cannot_have_invalidation_reason() -> None:
    with pytest.raises(ValueError, match="Fresh semantic evidence"):
        _build(_snapshot(), "fresh", "SOURCE_CHANGED")


def test_stale_report_preserves_historical_issues() -> None:
    original = _snapshot()
    snapshot = replace(
        original,
        observed_source_fingerprints=original.observed_source_fingerprints[1:],
        source_issues=(("pkg.a", "CANONICAL_FINGERPRINT_MISMATCH"),),
        coverage_status="PARTIAL_SOURCE_EVIDENCE",
    )
    report = _build(snapshot, "stale", "SOURCE_CHANGED")
    assert report["status"] == "stale"
    assert report["semantic_evidence"]["available"] is True
    assert report["semantic_evidence"]["source_issues"] == [
        {"module_id": "pkg.a", "reason": "CANONICAL_FINGERPRINT_MISMATCH"}
    ]
    assert report["semantic_evidence"]["freshness_at_report_generation"] == "stale"


def test_partial_current_report_preserves_coverage() -> None:
    original = _snapshot()
    snapshot = replace(
        original,
        observed_source_fingerprints=original.observed_source_fingerprints[1:],
        source_issues=(("pkg.a", "SOURCE_FILE_LIMIT"),),
        coverage_status="PARTIAL_SOURCE_EVIDENCE",
    )
    report = _build(snapshot)
    assert report["status"] == "partial"
    assert report["semantic_evidence"]["coverage_status"] == "PARTIAL_SOURCE_EVIDENCE"
    assert report["semantic_evidence"]["unobserved_source_count"] == 1


def test_projection_failure_preserves_evidence(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("projection failed")
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.report_projection.project_cycle_semantics", fail,
    )
    snapshot = _snapshot()
    report = _build(snapshot)
    assert report["status"] == "projection_unavailable"
    assert report["projection_error"] == "RuntimeError"
    assert report["semantic_evidence"]["graph_sha256"] == snapshot.graph_sha256
    assert report["projection"] is None


def test_projection_cancellation_propagates(monkeypatch) -> None:
    def cancel(*args, **kwargs):
        raise AnalysisCancelled()
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.report_projection.project_cycle_semantics", cancel,
    )
    with pytest.raises(AnalysisCancelled):
        _build(_snapshot())


def test_header_and_snapshot_are_not_mutated() -> None:
    snapshot = _snapshot()
    before = dict(HEADER)
    report = _build(snapshot)
    report["report_header"]["generated_at"] = "changed"
    assert HEADER == before
    assert snapshot.source_issues == ()
    assert snapshot.cyclic_modules == ("pkg.a", "pkg.b")


def test_publication_binding_is_explicitly_unverified() -> None:
    report = _build(_snapshot())
    assert report["publication_binding"] == {
        "status": REPORT_LIVE_BINDING_STATUS,
        "canonical_revision": None,
        "live_revision": None,
    }


def test_report_builder_cold_import_is_isolated() -> None:
    code = (
        "import sys; import contextor.core.cycle_semantics.report_projection; "
        "assert not any(name == prefix or name.startswith(prefix + '.') "
        "for prefix in ('contextor.ui', 'contextor.repo_generator', "
        "'contextor.mcp', 'contextor.core.live_state') for name in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
