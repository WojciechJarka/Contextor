import importlib
import json
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.cycle_semantics.contracts import fingerprint_hard_edges
from contextor.core.cycle_semantics.edge_sites import LexicalEdgeSite
from contextor.core.domain.graph import ProjectGraph
from contextor.mcp.query_helpers import build_state_freshness
from contextor.mcp import query_helpers
from contextor.core.cycle_semantics.report_projection import build_cycle_semantics_report
from contextor.mcp.cycle_semantics_views import project_historical_cycle_semantics
from tests.test_cycle_semantics_report_projection import _snapshot


architecture_tool = importlib.import_module(
    "contextor.mcp.tools.get_project_architecture"
)

_REPORT_SUFFIXES = {
    "summary": "summary.json",
    "structure": "structure.json",
    "name_collisions": "name_collisions.json",
    "artifacts_compact": "artifacts_compact.json",
    "graph_analytics": "graph_analytics.json",
    "report_diff": "report_diff.json",
}


def _install_runtime(tmp_path, monkeypatch, reports):
    paths = {}
    for field, payload in reports.items():
        path = tmp_path / f"{field}.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        suffix = "cycle_semantics.json" if field == "cycle_semantics" else _REPORT_SUFFIXES[field]
        paths[f"{tmp_path.name}_{suffix}"] = path

    monkeypatch.setattr(
        architecture_tool.report_helpers,
        "get_canonical_report",
        lambda _root, filename: paths.get(filename),
    )

    state = RepositoryAnalysisState(
        modules={"pkg.mod": object()},
        cycles_state="fresh",
        collisions_state="fresh",
        topology_metrics_state="fresh",
        artifact_consumption_state="fresh",
        lineage_facts_state="fresh",
    )
    engine = SimpleNamespace(
        state=state,
        revision=77,
        provenance="live",
    )
    monkeypatch.setattr(
        architecture_tool.mcp_runtime,
        "get_or_init_engine",
        lambda _root: engine,
    )
    monkeypatch.setattr(
        architecture_tool,
        "diagnostics_summary",
        lambda _root, _state: {
            "attention_required": False,
            "availability": {
                "cycles": "fresh",
                "name_collisions": "fresh",
            },
        },
    )
    monkeypatch.setattr(
        architecture_tool.query_helpers,
        "build_state_freshness",
        lambda _root, _state, engine=None: {
            "canonical_state": "fresh",
            "workspace_sync": "unverified",
            "canonical_revision": 77,
            "provenance": "live",
            "families": {
                "graph": "fresh",
                "topology": "fresh",
                "artifact_consumption": "fresh",
                "cycles": "fresh",
                "collisions": "fresh",
                "lineage": "fresh",
            },
            "advisory_warning": None,
        },
    )


def _small_bundle():
    return {
        "summary": {
            "status": "WARNING",
            "metrics": {"nodes": 3, "edges_total": 4},
            "action_items": ["inspect pkg.mod"],
            "report_header": {
                "commit_sha": "abc",
                "generated_at": "2026-09-16T07:41:26",
            },
        },
        "structure": {
            "hard_edges": {"pkg.mod": ["pkg.dep"]},
            "soft_edges": {},
        },
        "name_collisions": {
            "total_collisions": 0,
            "collision_summary": {"total": 0},
            "collisions": [],
        },
        "artifacts_compact": {
            "_format_version": "3",
            "artifact_count": 1,
            "artifacts": {"A1": {"kind": "function"}},
        },
        "graph_analytics": {
            "report_type": "graph_analytics",
            "module_count": 1,
            "modules": {
                "pkg.mod": {
                    "fan_in": 1,
                    "fan_out": 1,
                }
            },
        },
        "report_diff": {
            "classification": "NO_CHANGE",
            "report_diff": {
                "metrics": {},
                "debt": {},
                "layers": {},
                "is_empty": True,
            },
            "current": {
                "commit_sha": "abc",
                "generated_at": "2026-09-16T07:41:26",
            },
        },
    }


def _historical_report():
    return build_cycle_semantics_report(
        _snapshot(), "fresh", None,
        report_header={"generated_at": "2026-01-01T00:00:00", "data_source": "global"},
    )


def _read_architecture(tmp_path, **kwargs):
    return json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path), **kwargs))


def test_get_project_architecture_returns_lossless_global_report_bundle_under_50k(
    tmp_path,
    monkeypatch,
):
    reports = _small_bundle()
    _install_runtime(tmp_path, monkeypatch, reports)

    result = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
        )
    )

    assert result["status"] == "ok"
    assert result["report_bundle_state"] == "complete"
    assert result["selected_fields"] == list(_REPORT_SUFFIXES)
    assert result["reports"] == reports
    assert result["live_state"]["state_freshness"]["canonical_revision"] == 77
    assert result["live_state"]["state_freshness"]["provenance"] == "live"

    for field, payload in reports.items():
        metadata = result["report_catalog"][field]
        assert metadata["available"] is True
        assert metadata["serialized_bytes"] == len(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ).encode("utf-8")
        )


def test_get_project_architecture_normalizes_malformed_public_family(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
    engine.state.cycles_state = "pretend_fresh"
    monkeypatch.setattr(architecture_tool.query_helpers, "build_state_freshness", build_state_freshness)

    result = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))

    assert result["status"] == "ok"
    freshness = result["live_state"]["state_freshness"]
    assert freshness["families"]["cycles"] == "unavailable"
    assert freshness["families"]["lineage"] == "fresh"
    assert engine.state.cycles_state == "pretend_fresh"


def test_project_architecture_overlay_distinguishes_untrusted_from_lkg(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
    entry = {"state": "unknown"}
    engine.state.module_parse_freshness = {"pkg.mod": entry}
    monkeypatch.setattr(
        architecture_tool.query_helpers,
        "build_state_freshness",
        build_state_freshness,
    )

    result = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))

    live = result["live_state"]
    assert live["parse_stale_modules"]["pkg.mod"]["state"] == "unavailable"
    assert live["parse_stale_modules"]["pkg.mod"]["provenance"] == "untrusted"
    assert live["state_freshness"]["canonical_state"] == "unavailable"
    assert live["state_freshness"]["families"]["module"] == "unavailable"
    assert "untrusted" in live["state_freshness"]["advisory_warning"]
    assert "last-known-good" not in live["state_freshness"]["advisory_warning"]
    assert engine.state.module_parse_freshness["pkg.mod"] is entry


def test_project_architecture_overlay_keeps_stale_and_resync_contract(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
    engine.state.module_parse_freshness = {"pkg.mod": {"state": "stale"}}

    stale = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))
    assert stale["live_state"]["state_freshness"]["canonical_state"] == "stale"
    assert stale["live_state"]["parse_stale_modules"]["pkg.mod"]["provenance"] == "last_known_good"

    engine.state.module_parse_freshness = {"pkg.mod": {"state": "unknown"}}
    engine.state.resync_required = True
    resync = json.loads(mcp_server.get_project_architecture.fn(repo_path=str(tmp_path)))
    assert resync["live_state"]["state_freshness"]["canonical_state"] == "stale"
    assert resync["live_state"]["parse_stale_modules"]["pkg.mod"]["state"] == "unavailable"


def test_get_project_architecture_preflights_over_50k_and_reports_section_sizes(
    tmp_path,
    monkeypatch,
):
    reports = _small_bundle()
    reports["graph_analytics"] = {
        "report_type": "graph_analytics",
        "payload": "x" * 60000,
    }
    _install_runtime(tmp_path, monkeypatch, reports)

    result = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
        )
    )

    assert result["status"] == "confirmation_required"
    assert result["estimated_output_bytes"] > 50 * 1024
    assert result["warning_threshold_bytes"] == 50 * 1024
    assert result["warning_threshold_kib"] == 50.0
    assert (
        result["report_catalog"]["graph_analytics"]["serialized_bytes"]
        > 50 * 1024
    )
    assert result["retry"] == {
        "fields": list(_REPORT_SUFFIXES),
        "allow_large_output": True,
    }


def test_get_project_architecture_fields_narrow_before_large_retrieval(
    tmp_path,
    monkeypatch,
):
    reports = _small_bundle()
    reports["graph_analytics"] = {
        "report_type": "graph_analytics",
        "payload": "x" * 60000,
    }
    _install_runtime(tmp_path, monkeypatch, reports)

    result = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
            fields=["summary", "report_diff"],
        )
    )

    assert result["status"] == "ok"
    assert result["selected_fields"] == ["summary", "report_diff"]
    assert set(result["reports"]) == {"summary", "report_diff"}
    assert result["reports"]["summary"] == reports["summary"]
    assert result["reports"]["report_diff"] == reports["report_diff"]
    assert set(result["report_catalog"]) == set(_REPORT_SUFFIXES) | {
        "cycle_semantics",
    }
    assert (
        result["report_catalog"]["graph_analytics"]["serialized_bytes"]
        > 50 * 1024
    )


def test_get_project_architecture_allow_large_output_returns_exact_selected_report(
    tmp_path,
    monkeypatch,
):
    reports = _small_bundle()
    reports["graph_analytics"] = {
        "report_type": "graph_analytics",
        "payload": "x" * 60000,
    }
    _install_runtime(tmp_path, monkeypatch, reports)

    result = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
            fields=["graph_analytics"],
            allow_large_output=True,
        )
    )

    assert result["status"] == "ok"
    assert result["selected_fields"] == ["graph_analytics"]
    assert result["reports"]["graph_analytics"] == reports["graph_analytics"]


def test_get_project_architecture_missing_reports_are_explicit_and_unknown_fields_fail(
    tmp_path,
    monkeypatch,
):
    reports = {
        "summary": _small_bundle()["summary"],
    }
    _install_runtime(tmp_path, monkeypatch, reports)

    result = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
            fields=["summary", "structure"],
        )
    )

    assert result["status"] == "partial"
    assert result["reports"]["summary"] == reports["summary"]
    assert result["reports"]["structure"]["available"] is False
    assert result["reports"]["structure"]["state"] == "unavailable"

    invalid = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
            fields=["does_not_exist"],
        )
    )
    assert invalid["status"] == "error"
    assert invalid["error"] == "unsupported_fields"
    assert invalid["unknown_fields"] == ["does_not_exist"]


def test_cycle_semantics_default_bundle_unchanged(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    result = _read_architecture(tmp_path)
    assert result["status"] == "ok"
    assert result["report_bundle_state"] == "complete"
    assert result["selected_fields"] == list(_REPORT_SUFFIXES)
    assert set(result["reports"]) == set(_REPORT_SUFFIXES)
    assert "cycle_semantics" in result["available_fields"]
    assert result["report_catalog"]["cycle_semantics"]["state"] == "unavailable"
    assert result["report_catalog"]["cycle_semantics"]["available"] is False
    assert result["report_catalog"]["cycle_semantics"]["serialized_bytes"] is None
    assert result["report_catalog"]["cycle_semantics"]["historical_only"] is True
    assert result["report_catalog"]["cycle_semantics"]["report_live_binding_verified"] is False


def test_cycle_semantics_empty_selection_returns_catalog_without_report_bodies(
    tmp_path,
    monkeypatch,
):
    report = _historical_report()
    _install_runtime(
        tmp_path,
        monkeypatch,
        {**_small_bundle(), "cycle_semantics": report},
    )
    result = _read_architecture(tmp_path, fields=[])

    assert result["status"] == "ok"
    assert result["selected_fields"] == []
    assert result["reports"] == {}
    assert set(result["report_catalog"]) == set(_REPORT_SUFFIXES) | {
        "cycle_semantics",
    }
    metadata = result["report_catalog"]["cycle_semantics"]
    assert metadata["available"] is True
    assert metadata["state"] == "available"
    assert metadata["historical_only"] is True
    assert metadata["report_live_binding_verified"] is False
    assert metadata["serialized_bytes"] == len(
        json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8")
    )


def test_cycle_semantics_explicit_selection_lossless(tmp_path, monkeypatch):
    report = _historical_report()
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert result["status"] == "ok"
    assert result["selected_fields"] == ["cycle_semantics"]
    assert result["reports"]["cycle_semantics"] == report
    assert result["report_catalog"]["cycle_semantics"]["historical_only"] is True
    assert result["report_catalog"]["cycle_semantics"]["report_live_binding_verified"] is False
    assert result["reports"]["cycle_semantics"]["publication_binding"]["live_revision"] is None


def test_cycle_semantics_full_view_is_exact_persisted_report(tmp_path, monkeypatch):
    report = _historical_report()
    _install_runtime(
        tmp_path,
        monkeypatch,
        {**_small_bundle(), "cycle_semantics": report},
    )
    result = _read_architecture(
        tmp_path,
        fields=["cycle_semantics"],
        cycle_semantics_view="full",
    )
    assert result["reports"]["cycle_semantics"] == report


def test_cycle_semantics_diagnostic_view_omits_only_transmitted_fingerprints(
    tmp_path,
    monkeypatch,
):
    report = _historical_report()
    original = deepcopy(report)
    _install_runtime(
        tmp_path,
        monkeypatch,
        {**_small_bundle(), "cycle_semantics": report},
    )
    result = _read_architecture(
        tmp_path,
        fields=["cycle_semantics"],
        cycle_semantics_view="diagnostic",
    )

    projected = result["reports"]["cycle_semantics"]
    assert "source_fingerprints" not in projected["semantic_evidence"]
    assert projected["semantic_evidence"]["coverage_status"] == original[
        "semantic_evidence"
    ]["coverage_status"]
    assert projected["semantic_evidence"]["source_snapshot_binding"] == original[
        "semantic_evidence"
    ]["source_snapshot_binding"]
    assert projected["publication_binding"] == original["publication_binding"]
    assert projected["projection"] == original["projection"]
    assert projected["presentation"] == {
        "view": "diagnostic",
        "source_fingerprints_omitted": True,
        "source_fingerprint_count": len(
            original["semantic_evidence"]["source_fingerprints"]
        ),
        "full_evidence_available": True,
    }
    assert report == original


def test_cycle_semantics_overview_omits_edges_and_witness_chains(tmp_path, monkeypatch):
    report = _historical_report()
    _install_runtime(
        tmp_path,
        monkeypatch,
        {**_small_bundle(), "cycle_semantics": report},
    )
    result = _read_architecture(
        tmp_path,
        fields=["cycle_semantics"],
        cycle_semantics_view="overview",
    )
    projected = result["reports"]["cycle_semantics"]

    assert projected["report_header"] == report["report_header"]
    assert projected["publication_binding"] == report["publication_binding"]
    assert projected["semantic_evidence"]["source_issues"] == report[
        "semantic_evidence"
    ]["source_issues"]
    assert projected["semantic_evidence"]["observed_source_count"] == report[
        "semantic_evidence"
    ]["observed_source_count"]
    assert projected["semantic_evidence"]["snapshot_schema_version"] == report[
        "semantic_evidence"
    ]["snapshot_schema_version"]
    assert projected["semantic_evidence"]["invalidation_reason"] is None
    assert projected["projection"]["summary"] == report["projection"]["summary"]
    assert "source_fingerprints" not in projected["semantic_evidence"]
    component = projected["projection"]["components"][0]
    assert "members" in component
    assert "diagnostic_category" in component
    assert "edges" not in component
    assert "conditional_reexports" not in component
    assert projected["presentation"]["full_evidence_available"] is True
    assert "full" in projected["presentation"]["full_evidence_retrieval_path"]
    assert report == _historical_report()


def test_reduced_historical_views_do_not_mutate_loaded_report():
    report = _historical_report()
    original = deepcopy(report)
    for view in ("diagnostic", "overview"):
        projected, error = project_historical_cycle_semantics(
            report,
            view=view,
            component=None,
        )
        assert error is None
        assert projected is not report
        assert report == original


def test_overview_mutable_values_are_independent_of_historical_report():
    report = _historical_report()
    report["report_header"]["nested"] = {"items": ["original"]}
    report["publication_binding"]["nested"] = {"items": ["original"]}
    report["semantic_evidence"]["source_issues"] = [
        {"module": "pkg.a", "details": ["original"]}
    ]
    report["projection"]["selection_scope"] = {"items": ["original"]}
    report["projection"]["summary"]["cyclic_scc_total"] = {
        "items": ["original"]
    }
    original = deepcopy(report)

    overview, error = project_historical_cycle_semantics(
        report, view="overview", component=None,
    )
    assert error is None
    overview["report_header"]["nested"]["items"].append("changed")
    overview["publication_binding"]["nested"]["items"].append("changed")
    overview["semantic_evidence"]["source_issues"][0]["details"].append("changed")
    overview["projection"]["selection_scope"]["items"].append("changed")
    overview["projection"]["summary"]["cyclic_scc_total"]["items"].append("changed")
    overview["projection"]["components"][0]["members"].append("changed")

    assert report == original


def test_historical_overview_preserves_invalidation_reason():
    report = _historical_report()
    report["semantic_evidence"]["invalidation_reason"] = "GRAPH_CHANGED"
    overview, error = project_historical_cycle_semantics(
        report, view="overview", component=None,
    )
    assert error is None
    assert overview["semantic_evidence"]["invalidation_reason"] == "GRAPH_CHANGED"
    assert overview["semantic_evidence"]["snapshot_schema_version"] == report[
        "semantic_evidence"
    ]["snapshot_schema_version"]


def test_cycle_semantics_component_selection_is_bounded_and_preserves_total(
    tmp_path,
    monkeypatch,
):
    report = _historical_report()
    _install_runtime(
        tmp_path,
        monkeypatch,
        {**_small_bundle(), "cycle_semantics": report},
    )
    result = _read_architecture(
        tmp_path,
        fields=["cycle_semantics"],
        cycle_semantics_view="overview",
        cycle_semantics_component="pkg.a",
    )
    projection = result["reports"]["cycle_semantics"]["projection"]
    assert len(projection["components"]) == 1
    assert "pkg.a" in projection["components"][0]["members"]
    assert projection["summary"]["cyclic_scc_total"] == 1
    assert projection["summary"]["cyclic_scc_returned"] == 1


def test_cycle_semantics_component_outside_projection_is_explicit(tmp_path, monkeypatch):
    report = _historical_report()
    _install_runtime(
        tmp_path,
        monkeypatch,
        {**_small_bundle(), "cycle_semantics": report},
    )
    result = _read_architecture(
        tmp_path,
        fields=["cycle_semantics"],
        cycle_semantics_view="diagnostic",
        cycle_semantics_component="pkg.missing",
    )
    assert result["status"] == "error"
    assert result["error"] == "component_not_in_projection"
    assert result["projection_truncated"] is False
    assert result["cyclic_scc_total"] == 1


def test_cycle_semantics_missing_component_in_truncated_projection_is_not_graph_absence(
    tmp_path,
    monkeypatch,
):
    report = _historical_report()
    report["projection"]["summary"].update(
        cyclic_scc_total=5,
        components_truncated=True,
    )
    _install_runtime(
        tmp_path,
        monkeypatch,
        {**_small_bundle(), "cycle_semantics": report},
    )
    result = _read_architecture(
        tmp_path,
        fields=["cycle_semantics"],
        cycle_semantics_view="overview",
        cycle_semantics_component="pkg.omitted",
    )
    assert result["error"] == "component_not_in_projection"
    assert result["projection_truncated"] is True
    assert result["cyclic_scc_total"] == 5
    assert result["cyclic_scc_returned"] == 1


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"cycle_semantics_view": "compact"}, "invalid_cycle_semantics_view"),
        ({"cycle_semantics_view": None}, "invalid_cycle_semantics_view"),
        ({"cycle_semantics_component": "   "}, "invalid_cycle_semantics_component"),
        ({"cycle_semantics_component": 7}, "invalid_cycle_semantics_component"),
        ({"cycle_semantics_view": "overview"}, "invalid_selection"),
        ({"cycle_semantics_component": "pkg.a"}, "invalid_selection"),
        (
            {
                "fields": ["cycle_semantics"],
                "cycle_semantics_view": "full",
                "cycle_semantics_component": "pkg.a",
            },
            "invalid_selection",
        ),
    ],
)
def test_cycle_semantics_view_parameters_fail_with_controlled_errors(
    tmp_path,
    monkeypatch,
    kwargs,
    error,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    result = _read_architecture(tmp_path, **kwargs)
    assert result["status"] == "error"
    assert result["error"] == error


def test_cycle_semantics_combined_selection(tmp_path, monkeypatch):
    bundle = _small_bundle()
    report = _historical_report()
    _install_runtime(tmp_path, monkeypatch, {**bundle, "cycle_semantics": report})
    result = _read_architecture(tmp_path, fields=["structure", "cycle_semantics"])
    assert result["selected_fields"] == ["structure", "cycle_semantics"]
    assert result["reports"] == {"structure": bundle["structure"], "cycle_semantics": report}


def test_cycle_semantics_explicit_selection_deduplicates_in_first_seen_order(
    tmp_path,
    monkeypatch,
):
    report = _historical_report()
    bundle = {**_small_bundle(), "cycle_semantics": report}
    _install_runtime(tmp_path, monkeypatch, bundle)
    result = _read_architecture(
        tmp_path,
        fields=["cycle_semantics", "structure", "cycle_semantics"],
    )
    assert result["selected_fields"] == ["cycle_semantics", "structure"]
    assert list(result["reports"]) == ["cycle_semantics", "structure"]
    assert result["reports"] == {
        "cycle_semantics": report,
        "structure": bundle["structure"],
    }


def test_cycle_semantics_missing_optional_is_partial(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    selected = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert selected["status"] == "partial"
    assert selected["report_bundle_state"] == "complete"
    assert selected["reports"]["cycle_semantics"]["available"] is False
    assert selected["reports"]["cycle_semantics"]["state"] == "unavailable"
    assert selected["report_catalog"]["cycle_semantics"]["historical_only"] is True
    assert _read_architecture(tmp_path)["status"] == "ok"


def test_cycle_semantics_invalid_json_fails_closed(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    original = architecture_tool.report_helpers.get_canonical_report
    monkeypatch.setattr(
        architecture_tool.report_helpers, "get_canonical_report",
        lambda root, filename: path if filename.endswith("_cycle_semantics.json") else original(root, filename),
    )
    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert result["status"] == "partial"
    assert result["reports"]["cycle_semantics"]["state"] == "invalid"
    assert result["reports"]["cycle_semantics"]["available"] is False
    assert result["report_catalog"]["cycle_semantics"]["state"] == "invalid"
    assert result["report_catalog"]["cycle_semantics"]["available"] is False
    assert result["report_bundle_state"] == "complete"


def test_cycle_semantics_unsupported_schema_fails_closed(tmp_path, monkeypatch):
    report = _historical_report()
    report["schema_version"] = "9.0.0"
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert result["status"] == "partial"
    assert result["reports"]["cycle_semantics"]["state"] == "invalid"
    assert "schema_version" in result["reports"]["cycle_semantics"]["reason"]


@pytest.mark.parametrize("forgery", [
    {"live_revision": 77},
    {"status": "VERIFIED_REPORT_VS_CANONICAL_LIVE"},
])
def test_cycle_semantics_forged_live_binding_rejected(tmp_path, monkeypatch, forgery):
    report = _historical_report()
    report["publication_binding"].update(forgery)
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert result["reports"]["cycle_semantics"]["state"] == "invalid"
    assert result["report_catalog"]["cycle_semantics"]["available"] is False


@pytest.mark.parametrize("changes", [
    {"semantic_evidence": {"available": False}, "status": "ok"},
    {"projection": None, "status": "ok"},
    {"semantic_evidence": {"coverage_status": "FILESYSTEM_STABLE_NON_ATOMIC"}, "status": "partial"},
    {"semantic_evidence": {"freshness_at_report_generation": "fresh"}, "status": "stale"},
])
def test_cycle_semantics_inconsistent_status_rejected(tmp_path, monkeypatch, changes):
    report = _historical_report()
    for key, value in changes.items():
        if key == "semantic_evidence":
            report[key].update(value)
        else:
            report[key] = value
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert result["reports"]["cycle_semantics"]["state"] == "invalid"


def test_cycle_semantics_report_remains_historical_with_newer_live(tmp_path, monkeypatch):
    report = _historical_report()
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert result["reports"]["cycle_semantics"] == report
    assert result["live_state"]["state_freshness"]["canonical_revision"] == 77
    assert result["reports"]["cycle_semantics"]["publication_binding"] == {
        "status": "UNVERIFIED_REPORT_VS_CANONICAL_LIVE",
        "canonical_revision": None,
        "live_revision": None,
    }


def test_cycle_semantics_large_selected_output_guard(tmp_path, monkeypatch):
    report = deepcopy(_historical_report())
    report["semantic_evidence"]["source_fingerprints"] = [
        {"module_id": f"pkg.module_{i}", "sha256": "a" * 64}
        for i in range(1200)
    ]
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    guarded = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert guarded["status"] == "confirmation_required"
    assert guarded["estimated_output_bytes"] > 50 * 1024
    assert guarded["selected_fields"] == ["cycle_semantics"]
    assert guarded["retry"] == {"fields": ["cycle_semantics"], "allow_large_output": True}
    assert guarded["report_catalog"]["cycle_semantics"]["serialized_bytes"] > 50 * 1024
    full = _read_architecture(tmp_path, fields=["cycle_semantics"], allow_large_output=True)
    assert full["status"] == "ok"
    assert full["reports"]["cycle_semantics"] == report


def test_cycle_semantics_diagnostic_guard_runs_after_fingerprint_redaction(
    tmp_path,
    monkeypatch,
):
    report = deepcopy(_historical_report())
    report["semantic_evidence"]["source_fingerprints"] = [
        {"module_id": f"pkg.module_{i}", "sha256": "b" * 64}
        for i in range(1200)
    ]
    _install_runtime(
        tmp_path,
        monkeypatch,
        {**_small_bundle(), "cycle_semantics": report},
    )

    result = _read_architecture(
        tmp_path,
        fields=["cycle_semantics"],
        cycle_semantics_view="diagnostic",
    )

    assert result["status"] == "ok"
    assert "source_fingerprints" not in result["reports"]["cycle_semantics"][
        "semantic_evidence"
    ]
    assert result["report_catalog"]["cycle_semantics"]["serialized_bytes"] > 50 * 1024


def test_cycle_semantics_reader_does_not_rematerialize(tmp_path, monkeypatch):
    report = _historical_report()
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    def fail(*args, **kwargs):
        raise AssertionError("semantic recomputation attempted")
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail,
    )
    monkeypatch.setattr(
        "contextor.core.cycle_semantics.source_cohort.build_cycle_source_cohort", fail,
    )
    assert _read_architecture(tmp_path, fields=["cycle_semantics"])["reports"]["cycle_semantics"] == report


def test_cycle_semantics_selected_missing_does_not_change_default(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    before = _read_architecture(tmp_path)
    assert _read_architecture(tmp_path, fields=["cycle_semantics"])["status"] == "partial"
    after = _read_architecture(tmp_path)
    assert before == after


def _semantic_state(*, marker="fresh"):
    state = RepositoryAnalysisState(
        cycles_state="fresh",
        cycle_semantics=_snapshot(),
        cycle_semantics_state=marker,
    )
    state.dependency_graph = ProjectGraph(
        hard_edges={"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}},
        soft_edges={},
    )
    return state


def _snapshot_with_lexical_sites(*, activation_scope):
    snapshot = _snapshot()
    component = snapshot.import_sites.components[0]
    edges = tuple(
        replace(
            edge,
            status="LEXICAL_CANDIDATES",
            sites=(LexicalEdgeSite(
                ordinal=index,
                line=index + 1,
                column=0,
                form="IMPORT",
                match_kind="DIRECT_MODULE",
                requested_name=edge.target,
                matched_member=None,
                scopes=(),
                controls=(),
                activation_scope=activation_scope,
            ),),
        )
        for index, edge in enumerate(component.internal_edges)
    )
    sites = replace(
        snapshot.import_sites,
        components=(replace(
            component,
            internal_edges=edges,
            matched_edge_count=len(edges),
            unresolved_edge_count=0,
        ),),
    )
    discovery = replace(
        snapshot.conditional_discovery,
        unresolved_lexical_edge_count=0,
    )
    return replace(snapshot, import_sites=sites, conditional_discovery=discovery)


def _install_real_freshness(tmp_path, monkeypatch, state):
    engine = architecture_tool.mcp_runtime.get_or_init_engine(tmp_path)
    engine.state = state
    state.state_id = "synthetic-generation"
    state.revision = 77
    engine.state_manager = SimpleNamespace(state_id="synthetic-generation", revision=77)
    monkeypatch.setattr(architecture_tool.query_helpers, "build_state_freshness", build_state_freshness)
    monkeypatch.setattr(query_helpers, "is_explicit_generation_mismatch", lambda *args, **kwargs: False)
    monkeypatch.setattr("contextor.mcp.analysis_jobs._latest_analysis_job", lambda _root: None)
    return engine


def test_d4c_default_missing_semantics_is_deferred():
    state = RepositoryAnalysisState(cycle_semantics=None, cycle_semantics_state="deferred")
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "deferred"


def test_d4c_no_snapshot_cannot_claim_fresh():
    state = RepositoryAnalysisState(cycle_semantics=None, cycle_semantics_state="fresh")
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "unavailable"


def test_d4c_current_semantics_fresh_with_generation_proof():
    state = _semantic_state()
    assert fingerprint_hard_edges(state.dependency_graph.hard_edges) == state.cycle_semantics.graph_sha256
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "fresh"


def test_d4c_unverified_generation_cannot_claim_fresh():
    assert query_helpers._cycle_semantics_family_freshness(
        _semantic_state(), generation_coherent=False,
    ) == "unavailable"


def test_d4c_graph_drift_marks_semantics_stale():
    state = _semantic_state()
    snapshot = state.cycle_semantics
    state.dependency_graph = ProjectGraph(hard_edges={"pkg.a": set()}, soft_edges={})
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "stale"
    assert state.cycle_semantics is snapshot
    assert snapshot.graph_sha256 == fingerprint_hard_edges({"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}})


def test_d4c_semantic_stale_independent_of_cycles():
    state = _semantic_state(marker="stale")
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "stale"
    assert state.cycles_state == "fresh"


def test_d4c_resync_fail_closed():
    state = _semantic_state()
    state.resync_required = True
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "stale"


def test_d4c_malformed_evidence_is_unavailable():
    state = _semantic_state()
    state.cycle_semantics = {"graph_sha256": state.cycle_semantics.graph_sha256}
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "unavailable"


def test_d4c_legacy_state_remains_deferred():
    state = RepositoryAnalysisState()
    for name in ("cycle_semantics", "cycle_semantics_state", "cycle_semantics_invalidation_reason"):
        delattr(state, name)
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=False) == "deferred"


def test_d4c_public_envelope_includes_new_family(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state()
    engine = _install_real_freshness(tmp_path, monkeypatch, state)
    def fail(*args, **kwargs):
        raise AssertionError("semantic materializer called")
    monkeypatch.setattr("contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail)
    fresh = build_state_freshness(tmp_path, state, engine=engine)
    assert fresh["families"]["cycle_semantics"] == "fresh"
    assert fresh["families"]["cycles"] == "fresh"
    assert {"module", "graph", "topology", "artifact_consumption", "collisions", "lineage"} <= set(fresh["families"])
    engine.state_manager.revision = 76
    unverified = build_state_freshness(tmp_path, state, engine=engine)
    assert unverified["families"]["cycle_semantics"] == "unavailable"


def test_d4c_reader_reports_historical_and_live_separately(tmp_path, monkeypatch):
    report = _historical_report()
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    state = _semantic_state(marker="stale")
    _install_real_freshness(tmp_path, monkeypatch, state)
    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert result["reports"]["cycle_semantics"] == report
    assert result["reports"]["cycle_semantics"]["semantic_evidence"]["freshness_at_report_generation"] == "fresh"
    assert result["live_state"]["state_freshness"]["families"]["cycle_semantics"] == "stale"
    assert result["live_state"]["state_freshness"]["canonical_revision"] == 77
    assert result["reports"]["cycle_semantics"]["publication_binding"]["live_revision"] is None
    assert result["live_state"]["cycle_semantic_diagnostics"]["status"] == "stale"
    assert result["live_state"]["cycle_semantic_diagnostics"]["cyclic_scc_count"] is None
    assert result["live_state"]["cycle_semantic_diagnostics"]["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"


def test_live_semantic_diagnostics_uses_positive_current_snapshot_gate(
    tmp_path,
    monkeypatch,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state()
    engine = _install_real_freshness(tmp_path, monkeypatch, state)
    result = _read_architecture(tmp_path, fields=[])

    semantic = result["live_state"]["cycle_semantic_diagnostics"]
    assert result["live_state"]["state_freshness"]["families"][
        "cycle_semantics"
    ] == "fresh"
    assert semantic["status"] == "fresh"
    assert semantic["source"] == "live_canonical_state"
    assert semantic["canonical_revision"] == engine.revision == 77
    assert semantic["cyclic_scc_count"] == 1
    assert semantic["cyclic_module_count"] == 2
    assert semantic["unresolved_lexical_edge_count"] == 2
    assert semantic["direct_candidate_attention_required"] is None
    assert "unresolved lexical activation" in semantic["reason"]
    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"
    assert result["live_state"]["diagnostics_attention_required"] is False


def test_live_semantic_diagnostics_resolved_lexical_absence_allows_false(
    tmp_path, monkeypatch,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state()
    state.cycle_semantics = _snapshot_with_lexical_sites(
        activation_scope="FUNCTION_SCOPED",
    )
    _install_real_freshness(tmp_path, monkeypatch, state)

    semantic = _read_architecture(tmp_path)["live_state"][
        "cycle_semantic_diagnostics"
    ]
    assert semantic["status"] == "fresh"
    assert semantic["unguarded_direct_cyclic_scc_count"] == 0
    assert semantic["unresolved_lexical_edge_count"] == 0
    assert semantic["direct_candidate_attention_required"] is False
    assert semantic["reason"] is None
    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"


def test_live_semantic_diagnostics_unrecognized_activation_blocks_false(
    tmp_path, monkeypatch,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state()
    state.cycle_semantics = _snapshot_with_lexical_sites(
        activation_scope="UNKNOWN_SCOPE",
    )
    _install_real_freshness(tmp_path, monkeypatch, state)

    semantic = _read_architecture(tmp_path)["live_state"][
        "cycle_semantic_diagnostics"
    ]
    assert semantic["status"] == "fresh"
    assert semantic["unguarded_direct_cyclic_scc_count"] == 0
    assert semantic["unresolved_lexical_edge_count"] == 0
    assert semantic["direct_candidate_attention_required"] is None
    assert "unresolved lexical activation" in semantic["reason"]
    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"


def test_live_semantic_diagnostics_partial_coverage_never_infers_absence(
    tmp_path,
    monkeypatch,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    snapshot = _snapshot()
    partial_snapshot = replace(
        snapshot,
        observed_source_fingerprints=snapshot.observed_source_fingerprints[:1],
        source_issues=(("pkg.b", "SOURCE_UNAVAILABLE"),),
        coverage_status="PARTIAL_SOURCE_EVIDENCE",
    )
    state = _semantic_state()
    state.cycle_semantics = partial_snapshot
    engine = _install_real_freshness(tmp_path, monkeypatch, state)
    result = _read_architecture(tmp_path)

    semantic = result["live_state"]["cycle_semantic_diagnostics"]
    assert semantic["status"] == "partial"
    assert semantic["coverage_status"] == "PARTIAL_SOURCE_EVIDENCE"
    assert semantic["direct_candidate_attention_required"] is None
    assert semantic["cyclic_scc_count"] == 1
    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"
    assert engine.revision == 77


def test_live_semantic_diagnostics_retains_positive_partial_evidence(
    tmp_path,
    monkeypatch,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    snapshot = _snapshot_with_lexical_sites(activation_scope="MODULE_TOP_LEVEL")
    partial_snapshot = replace(
        snapshot,
        observed_source_fingerprints=snapshot.observed_source_fingerprints[:1],
        source_issues=(("pkg.b", "SOURCE_UNAVAILABLE"),),
        coverage_status="PARTIAL_SOURCE_EVIDENCE",
    )
    state = _semantic_state()
    state.cycle_semantics = partial_snapshot
    _install_real_freshness(tmp_path, monkeypatch, state)
    semantic = _read_architecture(tmp_path)["live_state"][
        "cycle_semantic_diagnostics"
    ]
    assert semantic["status"] == "partial"
    assert semantic["unguarded_direct_cyclic_scc_count"] == 1
    assert semantic["direct_candidate_attention_required"] is True
    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"


@pytest.mark.parametrize(
    ("marker", "expected"),
    [("deferred", "deferred"), ("stale", "stale"), ("invalid", "unavailable")],
)
def test_live_semantic_diagnostics_nonfresh_families_fail_closed(
    tmp_path,
    monkeypatch,
    marker,
    expected,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state(marker=marker)
    _install_real_freshness(tmp_path, monkeypatch, state)
    semantic = _read_architecture(tmp_path)["live_state"][
        "cycle_semantic_diagnostics"
    ]
    assert semantic["status"] == expected
    assert semantic["cyclic_scc_count"] is None
    assert semantic["direct_candidate_attention_required"] is None
    assert semantic["reason"]


def test_live_semantic_diagnostics_generation_mismatch_fails_closed(
    tmp_path,
    monkeypatch,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state()
    engine = _install_real_freshness(tmp_path, monkeypatch, state)
    engine.state_manager.revision = 76
    semantic = _read_architecture(tmp_path)["live_state"][
        "cycle_semantic_diagnostics"
    ]
    assert semantic["status"] in {"unavailable", "stale"}
    assert semantic["cyclic_scc_count"] is None
    assert semantic["direct_candidate_attention_required"] is None


def test_live_semantic_diagnostics_resync_fails_closed(tmp_path, monkeypatch):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state()
    state.resync_required = True
    _install_real_freshness(tmp_path, monkeypatch, state)
    semantic = _read_architecture(tmp_path)["live_state"][
        "cycle_semantic_diagnostics"
    ]
    assert semantic["status"] == "stale"
    assert semantic["cyclic_scc_count"] is None
    assert semantic["direct_candidate_attention_required"] is None


def test_live_semantic_attention_is_separate_from_structural_attention(
    tmp_path,
    monkeypatch,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state()
    state.cycles = [["pkg.a", "pkg.b", "pkg.a"]]
    _install_real_freshness(tmp_path, monkeypatch, state)
    monkeypatch.setattr(
        "contextor.mcp.cycle_semantics_views.build_cycle_evidence_digest",
        lambda *_args: SimpleNamespace(components=(SimpleNamespace(
            members=state.cycle_semantics.cyclic_modules,
            category="UNGUARDED_DIRECT_CYCLIC_SUBGRAPH",
        ),)),
    )
    monkeypatch.setattr(
        architecture_tool,
        "diagnostics_summary",
        lambda *_args: {
            "attention_required": True,
            "availability": {"cycles": "fresh"},
        },
    )

    result = _read_architecture(tmp_path, fields=[])
    assert result["live_state"]["diagnostics_attention_required"] is True
    assert result["diagnostics_attention_required"] is True
    assert result["live_state"]["cycle_semantic_diagnostics"][
        "direct_candidate_attention_required"
    ] is True


def test_live_semantic_diagnostics_derivation_error_is_local_and_fail_closed(
    tmp_path,
    monkeypatch,
):
    _install_runtime(tmp_path, monkeypatch, _small_bundle())
    state = _semantic_state()
    _install_real_freshness(tmp_path, monkeypatch, state)

    def fail(*_args, **_kwargs):
        raise RuntimeError("test evidence failure")

    monkeypatch.setattr(
        "contextor.mcp.cycle_semantics_views.build_cycle_evidence_digest",
        fail,
    )
    result = _read_architecture(tmp_path)
    assert result["status"] == "ok"
    semantic = result["live_state"]["cycle_semantic_diagnostics"]
    assert semantic["status"] == "unavailable"
    assert semantic["cyclic_scc_count"] is None
    assert semantic["direct_candidate_attention_required"] is None
    assert semantic["runtime_execution_status"] == "UNKNOWN_NOT_EVALUATED"


def test_d4c_no_semantic_source_io(tmp_path, monkeypatch):
    report = _historical_report()
    _install_runtime(tmp_path, monkeypatch, {**_small_bundle(), "cycle_semantics": report})
    state = _semantic_state()
    snapshot = state.cycle_semantics
    _install_real_freshness(tmp_path, monkeypatch, state)
    def fail(*args, **kwargs):
        raise AssertionError("semantic source access or recomputation")
    monkeypatch.setattr("contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail)
    monkeypatch.setattr("contextor.core.cycle_semantics.source_cohort.build_cycle_source_cohort", fail)
    assert query_helpers._cycle_semantics_family_freshness(state, generation_coherent=True) == "fresh"
    result = _read_architecture(tmp_path, fields=["cycle_semantics"])
    assert result["reports"]["cycle_semantics"] == report
    assert result["live_state"]["state_freshness"]["families"]["cycle_semantics"] == "fresh"
    assert state.cycle_semantics is snapshot
