import importlib
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.mcp.query_helpers import build_state_freshness
from contextor.core.cycle_semantics.report_projection import build_cycle_semantics_report
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
    assert "cycle_semantics" not in result["report_catalog"]


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


def test_cycle_semantics_combined_selection(tmp_path, monkeypatch):
    bundle = _small_bundle()
    report = _historical_report()
    _install_runtime(tmp_path, monkeypatch, {**bundle, "cycle_semantics": report})
    result = _read_architecture(tmp_path, fields=["structure", "cycle_semantics"])
    assert result["selected_fields"] == ["structure", "cycle_semantics"]
    assert result["reports"] == {"structure": bundle["structure"], "cycle_semantics": report}


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
