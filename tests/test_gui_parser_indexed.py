"""Dedicated GUI integration tests for the shared indexed-report resolver."""

import json

from contextor.core.report_query import IndexCatalog, query_indexed_report
from contextor.ui import gui_parser


def test_gui_parser_matches_core_and_keeps_zero_consumer_public_api(tmp_path, monkeypatch):
    catalog = IndexCatalog(
        modules={"1/1": "main", "2/1": "pkg.cli"},
        artifacts={"A1/1": "main::main", "A2/1": "main::_private"},
        module_paths={"main": "main.py", "pkg.cli": "pkg/cli.py"},
    )
    report = {
        "_format_version": "3",
        "artifacts": {
            "A1/1": {
                "definer_module": "1/1",
                "consumer_module_indices": ["2/1"],
                "consumer_count": 0,
                "nested": {"text": "whole }, block"},
            },
            "A2/1": {
                "definer_module": "1/1",
                "consumer_module_indices": [],
                "consumer_count": 2,
            },
        },
    }
    report_path = tmp_path / "artifacts.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(gui_parser, "catalog_from_registry", lambda _repo: catalog)

    output_path = gui_parser.parse_and_filter_json(
        str(report_path),
        "main.py",
        str(tmp_path),
        output_dir=str(tmp_path / "output"),
        public_api_only=True,
    )
    saved = json.loads(open(output_path, encoding="utf-8").read())
    core = query_indexed_report(report, "main.py", catalog, repo_root=str(tmp_path))

    assert saved["artifacts"] == {"main::main": core["artifacts"]["main::main"]}
    assert saved["artifact_count"] == 1
    assert saved["artifacts"]["main::main"]["nested"]["text"] == "whole }, block"
    assert saved["query_resolution"]["status"] == "matched"


def test_full_gui_rewriter_uses_shared_recovery_and_omits_unknown_blocks(
    tmp_path, monkeypatch
):
    catalog = IndexCatalog(
        modules={"1/1": "main"},
        artifacts={"A1/1": "main::run"},
        recovered_modules={"9/1": "old.module"},
        recovered_artifacts={"A9/1": "old.module::run"},
    )
    report = {
        "_format_version": "3",
        "shared_artifact_keys": ["A1/1", "A9/1", "A404/1"],
        "artifacts": {
            "A1/1": {
                "definer_module": "1/1",
                "consumer_module_indices": ["9/1", "404/1"],
            },
            "A9/1": {"definer_module": "9/1", "consumer_module_indices": []},
            "A404/1": {"definer_module": "1/1", "consumer_module_indices": []},
        },
    }
    report_path = tmp_path / "artifacts.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(gui_parser, "catalog_from_registry", lambda _repo: catalog)

    output_path = gui_parser.rewrite_index_to_text(
        str(report_path), str(tmp_path), output_dir=str(tmp_path / "output")
    )
    saved = json.loads(open(output_path, encoding="utf-8").read())

    assert set(saved["artifacts"]) == {"main::run", "old.module::run"}
    assert saved["artifacts"]["main::run"]["consumer_modules"] == ["old.module"]
    assert saved["shared_artifacts"] == ["main::run", "old.module::run"]
    assert saved["index_diagnostics"]["omitted_blocks"][0]["artifact_id"] == "A404/1"
    assert {item.get("module_id") for item in saved["index_diagnostics"]["dropped_references"]} == {
        "404/1",
        None,
    }
