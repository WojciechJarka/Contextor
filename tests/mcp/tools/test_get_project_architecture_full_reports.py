import importlib
import json
from types import SimpleNamespace

from contextor import mcp_server
from contextor.core.analysis.state_manager import RepositoryAnalysisState


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
        paths[f"{tmp_path.name}_{_REPORT_SUFFIXES[field]}"] = path

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
