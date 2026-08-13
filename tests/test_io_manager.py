
import json
import os

from contextor.core.reporting_engine.header import build_report_header
from contextor.core.reporting_engine.io_manager import (
    write_layer_reports,
    write_global_reports,
)


def test_build_report_header_fallback(tmp_path):
    header = build_report_header(str(tmp_path), "global")

    assert header["schema_version"] == "1.0"
    assert "generated_at" in header
    assert header["data_source"] == "global"
    assert header["commit_sha"] is None
    assert header["branch"] is None


def test_write_layer_reports(tmp_path, monkeypatch):
    layer_reports = {
        "summary": {
            "status": "ok",
            "layer_module_count": 5,
        },
        "structure": {
            "hard_edges": [],
        },
        "metrics": {
            "density": 0.5,
        },
        "artifacts_compact": {
            "artifact_count": 10,
        },
        "graph_analytics": {
            "fan_in": 1,
        },
    }

    layer_output_dir = "integration_test_layer"

    def mock_resolve_report_path(path):
        return os.path.join(str(tmp_path), path)

    monkeypatch.setattr(
        "contextor.core.reporting_engine.formatting.resolve_report_path",
        mock_resolve_report_path,
    )

    write_layer_reports(
        repo_name="test_repo",
        layer_name="test_layer",
        layer_reports=layer_reports,
        log=None,
        layer_output_dir=layer_output_dir,
    )

    expected_dir = os.path.join(
        str(tmp_path),
        "output",
        layer_output_dir,
    )

    assert os.path.isdir(expected_dir)

    summary_path = os.path.join(
        expected_dir,
        "test_repo_test_layer_summary.json",
    )

    assert os.path.isfile(summary_path)

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "ok"
    assert data["layer_module_count"] == 5


def test_write_layer_reports_has_no_datestamp_suffix(tmp_path, monkeypatch):
    layer_reports = {
        "summary": {
            "status": "ok",
        },
    }

    layer_output_dir = "integration_test_layer"

    def mock_resolve_report_path(path):
        return os.path.join(str(tmp_path), path)

    monkeypatch.setattr(
        "contextor.core.reporting_engine.formatting.resolve_report_path",
        mock_resolve_report_path,
    )

    write_layer_reports(
        repo_name="test_repo",
        layer_name="test_layer",
        layer_reports=layer_reports,
        log=None,
        datestamp="20260808",
        layer_output_dir=layer_output_dir,
    )

    expected_dir = os.path.join(
        str(tmp_path),
        "output",
        layer_output_dir,
    )

    canonical_path = os.path.join(
        expected_dir,
        "test_repo_test_layer_summary.json",
    )

    legacy_path = os.path.join(
        expected_dir,
        "test_repo_test_layer_summary_20260808.json",
    )

    assert os.path.isfile(canonical_path)
    assert not os.path.exists(legacy_path)
    assert os.path.isfile(
        os.path.join(expected_dir, "20260808", "test_repo_test_layer_summary.json")
    )


def test_standalone_layer_snapshot_shares_repository_timestamp_directory(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "contextor.core.reporting_engine.formatting.resolve_report_path",
        lambda path: tmp_path / path,
    )
    monkeypatch.setattr(
        "contextor.core.reporting_engine.io_manager.resolve_report_path",
        lambda path: tmp_path / path,
    )

    write_layer_reports(
        "repo",
        "ui",
        {"summary": {"status": "OK"}},
        datestamp="20260808",
    )

    snapshot = (
        tmp_path / "output" / "repo_20260808" / "repo_ui_summary.json"
    )
    assert snapshot.is_file()


def test_write_layer_reports_emits_markdown_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "contextor.core.reporting_engine.formatting.resolve_report_path",
        lambda path: tmp_path / path,
    )
    monkeypatch.setattr(
        "contextor.core.reporting_engine.io_manager.resolve_report_path",
        lambda path: tmp_path / path,
    )

    write_layer_reports("repo", "ui", {"summary": {"status": "OK", "layer_module_count": 3}})

    markdown = tmp_path / "output" / "repo_ui_summary.md"
    assert markdown.is_file()
    assert "# Layer report: ui" in markdown.read_text(encoding="utf-8")


def test_write_global_reports_uses_canonical_names(tmp_path, monkeypatch):
    reports_data = {
        "summary": {
            "status": "ok",
        },
        "structure": {
            "hard_edges": [],
        },
        "collisions": [],
        "graph_analytics": {
            "nodes": 1,
        },
        "diff_report": {"changed": True},
    }

    def mock_resolve_report_path(path):
        return os.path.join(str(tmp_path), path)

    monkeypatch.setattr(
        "contextor.core.reporting_engine.formatting.resolve_report_path",
        mock_resolve_report_path,
    )

    write_global_reports(
        reports_data,
        repo_name="test_repo",
        datestamp="20260808",
        log=None,
    )

    output_dir = os.path.join(str(tmp_path), "output")

    assert os.path.isfile(
        os.path.join(output_dir, "test_repo_summary.json")
    )

    assert os.path.isfile(
        os.path.join(output_dir, "test_repo_structure.json")
    )

    assert os.path.isfile(
        os.path.join(output_dir, "test_repo_name_collisions.json")
    )

    assert os.path.isfile(
        os.path.join(output_dir, "test_repo_graph_analytics.json")
    )

    assert not os.path.exists(
        os.path.join(output_dir, "test_repo_summary_20260808.json")
    )

    assert os.path.isfile(
        os.path.join(output_dir, "test_repo_20260808", "test_repo_summary.json")
    )
    assert os.path.isfile(
        os.path.join(
            output_dir,
            "test_repo_20260808",
            "test_repo_report_diff.json",
        )
    )


def test_write_global_reports_emits_markdown_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "contextor.core.reporting_engine.formatting.resolve_report_path",
        lambda path: tmp_path / path,
    )
    monkeypatch.setattr(
        "contextor.core.reporting_engine.io_manager.resolve_report_path",
        lambda path: tmp_path / path,
    )

    write_global_reports({"summary": {"status": "OK", "metrics": {"nodes": 4}}}, "repo")

    markdown = tmp_path / "output" / "repo_summary.md"
    assert markdown.is_file()
    content = markdown.read_text(encoding="utf-8")
    assert "# Project report: repo" in content
    assert "**nodes:** 4" in content
