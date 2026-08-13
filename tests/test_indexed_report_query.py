"""Edge cases for the shared GUI/MCP indexed-report resolver."""

from pathlib import Path

from contextor.core.report_query import (
    IndexCatalog,
    catalog_from_registry,
    discover_module_paths,
    query_indexed_report,
    resolve_index_query,
)
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def test_module_path_discovery_prefers_root_and_supports_src_layout(tmp_path):
    paths = [
        "main.py",
        "nested/main.py",
        "src/pkg/service.py",
        "src/pkg/cli.py",
        "src/pkg/cli/__init__.py",
    ]
    for relative in paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    result = discover_module_paths(
        str(tmp_path),
        ["main", "pkg.service", "pkg.cli", "pkg.cli.__init__"],
    )

    assert result == {
        "main": "main.py",
        "pkg.service": "src/pkg/service.py",
        "pkg.cli": "src/pkg/cli.py",
        "pkg.cli.__init__": "src/pkg/cli/__init__.py",
    }


def test_module_path_discovery_does_not_choose_ambiguous_suffix(tmp_path):
    for relative in ("one/pkg/main.py", "two/pkg/main.py"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    assert discover_module_paths(str(tmp_path), ["pkg.main"]) == {}


def test_catalog_reads_both_physical_recovery_dictionaries(tmp_path):
    registry = PersistentIdentityRegistry(str(tmp_path))
    with registry.transaction():
        registry.sync_with_workspace({"old.module"}, {"old.module::run"})
    module_id = registry.get_module_id("old.module")
    artifact_id = registry.get_artifact_id("old.module::run")
    with registry.transaction():
        registry.sync_with_workspace(set(), set())

    catalog = catalog_from_registry(str(tmp_path))

    assert catalog.recovered_modules == {module_id: "old.module"}
    assert catalog.recovered_artifacts == {artifact_id: "old.module::run"}
    assert module_id not in catalog.modules
    assert artifact_id not in catalog.artifacts


def _catalog():
    return IndexCatalog(
        modules={
            "1/1": "main",
            "2/1": "pkg.main",
            "3/1": "tools.main",
            "4/1": "pkg.__main__",
            "5/1": "pkg.cli",
            "6/1": "pkg.cli.__init__",
        },
        module_paths={
            "main": "main.py",
            "pkg.main": "src/pkg/main.py",
            "tools.main": "tools/main.py",
            "pkg.__main__": "src/pkg/__main__.py",
            "pkg.cli": "src/pkg/cli.py",
            "pkg.cli.__init__": "src/pkg/cli/__init__.py",
        },
        artifacts={
            "A1/1": "main::main",
            "A2/1": "pkg.main::main",
            "A3/1": "tools.main::Runner.main",
            "A4/1": "pkg.cli::main",
            "A5/1": "pkg.cli::Client.maintain",
            "A6/1": "pkg.cli::Zażółć",
            "A7/1": "pkg.main::nested.value",
        },
        recovered_modules={"9/1": "old.main"},
        recovered_artifacts={"A9/1": "old.main::main"},
    )


def _report():
    return {
        "_format_version": "3",
        "artifacts": {
            "A1/1": {
                "definer_module": "1/1",
                "consumer_module_indices": ["5/1"],
                "usage": {"nested": [{"text": "literal }, is not a delimiter"}]},
            },
            "A3/1": {
                "definer_module": "3/1",
                "consumer_module_indices": [],
                "usage": None,
            },
            "A4/1": {
                "definer_module": "5/1",
                "consumer_module_indices": ["2/1"],
                "usage": {"calls": []},
            },
        },
    }


def test_exact_root_main_file_beats_nested_same_basenames():
    result = resolve_index_query("main.py", _catalog(), {"A1/1"})

    assert result["status"] == "matched"
    assert [item["id"] for item in result["matches"]] == ["1/1"]
    assert result["matches"][0]["match_kind"] == "exact_path"


def test_missing_root_main_file_reports_ambiguous_nested_basenames():
    catalog = _catalog()
    catalog = IndexCatalog(
        modules={key: value for key, value in catalog.modules.items() if key != "1/1"},
        artifacts=catalog.artifacts,
        module_paths={key: value for key, value in catalog.module_paths.items() if key != "main"},
    )

    result = resolve_index_query("main.py", catalog)

    assert result["status"] == "ambiguous"
    assert {item["path"] for item in result["matches"]} == {
        "src/pkg/main.py",
        "tools/main.py",
    }


def test_symbol_main_does_not_match_modules_named_main():
    result = resolve_index_query("main", _catalog())

    assert result["status"] == "ambiguous"
    assert {item["name"] for item in result["matches"]} == {
        "main::main",
        "pkg.main::main",
        "pkg.cli::main",
    }
    assert "tools.main::Runner.main" not in {item["name"] for item in result["matches"]}


def test_qualified_method_is_selected_before_suffix_matches():
    result = resolve_index_query("Runner.main", _catalog())

    assert result["status"] == "matched"
    assert [item["name"] for item in result["matches"]] == ["tools.main::Runner.main"]


def test_full_artifact_key_uses_exact_index_identity():
    result = resolve_index_query("pkg.main::nested.value", _catalog())

    assert result["match_count"] == 1
    assert result["matches"][0]["id"] == "A7/1"
    assert result["matches"][0]["match_kind"] == "exact_artifact"


def test_cli_file_and_cli_package_init_remain_distinct():
    file_result = resolve_index_query("src/pkg/cli.py", _catalog())
    package_result = resolve_index_query("src/pkg/cli/__init__.py", _catalog())

    assert file_result["matches"][0]["id"] == "5/1"
    assert package_result["matches"][0]["id"] == "6/1"


def test_windows_separators_and_dot_prefix_are_normalized():
    result = resolve_index_query(r".\src\pkg\__main__.py", _catalog())

    assert result["matches"][0]["id"] == "4/1"


def test_absolute_path_inside_repo_is_allowed_and_outside_is_rejected(tmp_path):
    inside = tmp_path / "src" / "pkg" / "main.py"
    inside.parent.mkdir(parents=True)
    inside.write_text("", encoding="utf-8")

    matched = resolve_index_query(str(inside), _catalog(), repo_root=str(tmp_path))
    rejected = resolve_index_query(str(tmp_path.parent / "outside.py"), _catalog(), repo_root=str(tmp_path))

    assert matched["matches"][0]["id"] == "2/1"
    assert rejected["status"] == "invalid"
    assert rejected["reason"] == "path_outside_repository"


def test_case_collision_is_not_silently_chosen():
    catalog = _catalog()
    artifacts = dict(catalog.artifacts)
    artifacts["A8/1"] = "pkg.cli::MAIN"
    catalog = IndexCatalog(modules=catalog.modules, artifacts=artifacts)

    result = resolve_index_query("Main", catalog)

    assert result["status"] == "ambiguous"
    assert {item["id"] for item in result["matches"]} == {"A1/1", "A2/1", "A4/1", "A8/1"}
    assert all(item["match_kind"] == "case_insensitive_symbol" for item in result["matches"])


def test_unicode_symbol_uses_exact_match():
    result = resolve_index_query("Zażółć", _catalog())

    assert result["matches"][0]["id"] == "A6/1"
    assert result["matches"][0]["match_kind"] == "exact_symbol"


def test_recovery_id_is_reported_as_stale_not_active():
    result = resolve_index_query("A9/1", _catalog())

    assert result["status"] == "stale_recovery_entry"
    assert result["matches"] == []
    assert result["recovery_matches"][0]["name"] == "old.main::main"


def test_recovery_name_resolves_whole_block_when_old_id_is_in_report():
    report = {
        "artifacts": {
            "A9/1": {
                "definer_module": "9/1",
                "consumer_module_indices": ["1/1"],
                "details": {"text": "complete }, block"},
            }
        }
    }

    result = query_indexed_report(report, "old.main::main", _catalog())

    assert result["resolution"]["status"] == "matched"
    assert result["artifacts"]["old.main::main"]["definer_module"] == "old.main"
    assert {item["kind"] for item in result["diagnostics"]["resolved_from_recovery"]} == {
        "artifact",
        "module",
    }


def test_unknown_artifact_id_omits_entire_block():
    report = {
        "artifacts": {
            "A404/1": {"definer_module": "1/1", "consumer_module_indices": []},
        }
    }

    result = query_indexed_report(report, "module:main", _catalog())

    assert result["artifacts"] == {}
    assert result["diagnostics"]["omitted_blocks"] == [
        {"artifact_id": "A404/1", "reason": "unknown_artifact_id"}
    ]


def test_unknown_definer_id_omits_entire_block():
    report = {
        "artifacts": {
            "A1/1": {"definer_module": "404/1", "consumer_module_indices": []},
        }
    }

    result = query_indexed_report(report, "main::main", _catalog())

    assert result["artifacts"] == {}
    assert result["diagnostics"]["omitted_blocks"] == [
        {
            "artifact_id": "A1/1",
            "reason": "unknown_definer_module_id",
            "module_id": "404/1",
        }
    ]


def test_unknown_consumer_reference_is_dropped_and_reported():
    report = {
        "artifacts": {
            "A1/1": {
                "definer_module": "1/1",
                "consumer_module_indices": ["404/1", "9/1"],
            }
        }
    }

    result = query_indexed_report(report, "main::main", _catalog())

    assert result["artifacts"]["main::main"]["consumer_modules"] == ["old.main"]
    assert result["diagnostics"]["dropped_references"] == [
        {
            "artifact_id": "A1/1",
            "field": "consumer_module_indices",
            "module_id": "404/1",
        }
    ]


def test_unresolved_raw_mode_still_omits_invalid_blocks_and_references():
    report = {
        "artifacts": {
            "A1/1": {
                "definer_module": "1/1",
                "consumer_module_indices": ["2/1", "404/1"],
            },
            "A404/1": {
                "definer_module": "1/1",
                "consumer_module_indices": [],
            },
        }
    }

    result = query_indexed_report(
        report,
        "module:main",
        _catalog(),
        resolve_indices=False,
    )

    assert result["artifacts"] == {
        "A1/1": {
            "definer_module": "1/1",
            "consumer_module_indices": ["2/1"],
        }
    }
    assert result["diagnostics"]["omitted_blocks"][0]["reason"] == "unknown_artifact_id"
    assert result["diagnostics"]["dropped_references"][0]["module_id"] == "404/1"


def test_nested_usage_ids_use_recovery_without_damaging_other_json_values():
    report = {
        "artifacts": {
            "A1/1": {
                "definer_module": "1/1",
                "consumer_module_indices": [],
                "usage": {
                    "modules": ["2/1", "9/1", "404/1"],
                    "details": [
                        {"module": "9/1", "text": "literal }, remains"},
                        {"module": "404/1", "text": "drop unresolved detail"},
                    ],
                },
            }
        }
    }

    result = query_indexed_report(report, "main::main", _catalog())

    assert result["artifacts"]["main::main"]["usage"] == {
        "modules": ["pkg.main", "old.main"],
        "details": [{"module": "old.main", "text": "literal }, remains"}],
    }
    dropped = result["diagnostics"]["dropped_references"]
    assert [item["module_id"] for item in dropped] == ["404/1", "404/1"]


def test_symbol_known_to_registry_but_absent_from_compact_is_explicit():
    result = resolve_index_query("Client.maintain", _catalog(), {"A1/1", "A4/1"})

    assert result["status"] == "resolved_but_not_in_report"
    assert result["matches"][0]["in_report"] is False


def test_fuzzy_candidates_are_suggestions_and_never_selected():
    result = resolve_index_query("maint", _catalog())

    assert result["status"] == "not_found"
    assert result["matches"] == []
    assert result["suggestions"][0]["name"] == "pkg.cli::Client.maintain"


def test_fuzzy_suggestions_do_not_match_middle_of_unrelated_word():
    catalog = _catalog()
    artifacts = dict(catalog.artifacts)
    artifacts["A8/1"] = "tests.graph::test_acyclic_graph"
    catalog = IndexCatalog(modules=catalog.modules, artifacts=artifacts)

    result = resolve_index_query("cli", catalog)

    assert result["status"] == "not_found"
    assert [item["name"] for item in result["suggestions"]] == [
        "pkg.cli::Client.maintain"
    ]
    assert all("acyclic" not in item["name"] for item in result["suggestions"])


def test_qualified_prefixes_are_suggestions_without_becoming_matches():
    catalog = IndexCatalog(
        modules={"1/1": "contextor.ui.test_runner"},
        artifacts={
            "A1/1": "contextor.ui.test_runner::run_test_suite",
            "A2/1": "contextor.core.api.facade::ContextorFacade.analyze_project",
        },
    )

    short = resolve_index_query("run_test_suit", catalog)
    qualified = resolve_index_query("ContextorFacade.analyze_proj", catalog)
    full = resolve_index_query(
        "artifact:contextor.core.api.facade::ContextorFacade.analyze_proj",
        catalog,
    )

    assert short["status"] == "not_found"
    assert short["matches"] == []
    assert [item["name"] for item in short["suggestions"]] == [
        "contextor.ui.test_runner::run_test_suite"
    ]
    assert [item["name"] for item in qualified["suggestions"]] == [
        "contextor.core.api.facade::ContextorFacade.analyze_project"
    ]
    assert [item["name"] for item in full["suggestions"]] == [
        "contextor.core.api.facade::ContextorFacade.analyze_project"
    ]


def test_exact_matches_suppress_fuzzy_suggestion_noise():
    result = resolve_index_query("main", _catalog())

    assert result["matches"]
    assert result["suggestions"] == []


def test_module_query_selects_whole_definer_and_consumer_blocks():
    result = query_indexed_report(_report(), "src/pkg/cli.py", _catalog())

    assert result["artifact_count"] == 2
    assert set(result["artifacts"]) == {"main::main", "pkg.cli::main"}
    assert result["artifacts"]["main::main"]["usage"]["nested"][0]["text"] == (
        "literal }, is not a delimiter"
    )
    assert result["selection"] == [
        {"artifact_id": "A1/1", "artifact": "main::main", "roles": ["consumed_here"]},
        {"artifact_id": "A4/1", "artifact": "pkg.cli::main", "roles": ["defined_here"]},
    ]


def test_symbol_query_copies_entire_nested_block_without_mutating_report():
    report = _report()
    result = query_indexed_report(report, "main::main", _catalog())

    block = result["artifacts"]["main::main"]
    assert block["usage"] == {"nested": [{"text": "literal }, is not a delimiter"}]}
    assert block["definer_module"] == "main"
    assert block["consumer_modules"] == ["pkg.cli"]
    assert "consumer_module_indices" in report["artifacts"]["A1/1"]


def test_invalid_report_without_artifact_object_raises():
    try:
        query_indexed_report({"artifacts": []}, "main", _catalog())
    except ValueError as exc:
        assert "artifacts" in str(exc)
    else:
        raise AssertionError("Expected invalid indexed report to fail")
