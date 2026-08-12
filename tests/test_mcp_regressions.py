"""Regression tests for MCP subprocess handling and single-file reports."""

import ast
import asyncio
import inspect
import json
import os
import subprocess
from contextlib import nullcontext
from pathlib import Path

import pytest

from contextor import mcp_process_registry, mcp_server
from contextor.core.analysis import git_context
from contextor.core.api.facade import ContextorFacade


def test_new_mcp_tools_document_their_llm_usage():
    server_path = Path(mcp_server.__file__)
    tree = ast.parse(server_path.read_text(encoding="utf-8"))
    expected = {
        "analyze_project",
        "analyze_layer",
        "analyze_single_file",
        "update_file",
        "get_artifact_blast_radius",
        "search_artifacts",
        "get_file_edit_context",
        "get_layer_isolation",
        "query_canonical_state_bounded",
        "lookup_index_entries",
        "get_artifacts_for_module",
        "lookup_artifact_by_symbol",
    }
    docs = {
        node.name: ast.get_docstring(node) or ""
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in expected
    }

    assert set(docs) == expected
    assert all("LLM use:" in doc for doc in docs.values())
    assert "exclude_paths" in docs["analyze_project"]
    assert "tests_covering" in docs["analyze_project"]
    assert "code diff" in docs["update_file"]


def test_fastmcp_schema_exposes_excludes_and_llm_guidance():
    signature = inspect.signature(mcp_server.analyze_project.fn)

    assert "exclude_paths" in signature.parameters
    assert "LLM use:" in mcp_server.analyze_project.description
    assert "tests_covering" in mcp_server.analyze_project.description
    assert "LLM use:" in mcp_server.update_file.description
    assert "code diff" in mcp_server.update_file.description


def test_mcp_bootstrap_keeps_an_existing_virtual_environment(monkeypatch):
    monkeypatch.setattr(mcp_server.sys, "prefix", "C:/repo/.venv")
    monkeypatch.setattr(mcp_server.sys, "base_prefix", "C:/Python")
    exec_calls = []
    monkeypatch.setattr(
        mcp_server.os, "execv", lambda *args: exec_calls.append(args)
    )

    mcp_server._ensure_virtual_environment()

    assert exec_calls == []


def test_mcp_bootstrap_reexecs_outside_venv_with_preserved_stdio(monkeypatch):
    interpreter = Path("C:/repo/.venv/Scripts/python.exe")
    monkeypatch.setattr(mcp_server.sys, "prefix", "C:/Python")
    monkeypatch.setattr(mcp_server.sys, "base_prefix", "C:/Python")
    monkeypatch.setattr(mcp_server.sys, "argv", ["contextor-mcp", "--flag"])
    monkeypatch.setattr(mcp_server, "_project_venv_python", lambda: interpreter)
    monkeypatch.setattr(Path, "is_file", lambda self: self == interpreter)

    class ReexecCalled(Exception):
        pass

    calls = []

    def fake_execv(executable, argv):
        calls.append((executable, argv))
        raise ReexecCalled

    monkeypatch.setattr(mcp_server.os, "execv", fake_execv)

    with pytest.raises(ReexecCalled):
        mcp_server._ensure_virtual_environment()

    assert calls == [
        (
            str(interpreter),
            [
                str(interpreter),
                "-u",
                "-m",
                "contextor.mcp_server",
                "--flag",
            ],
        )
    ]


def test_mcp_bootstrap_fails_when_project_venv_is_missing(monkeypatch):
    interpreter = Path("C:/repo/.venv/Scripts/python.exe")
    monkeypatch.setattr(mcp_server.sys, "prefix", "C:/Python")
    monkeypatch.setattr(mcp_server.sys, "base_prefix", "C:/Python")
    monkeypatch.setattr(mcp_server, "_project_venv_python", lambda: interpreter)
    monkeypatch.setattr(Path, "is_file", lambda _self: False)

    with pytest.raises(RuntimeError, match="must run in a virtual environment"):
        mcp_server._ensure_virtual_environment()


def test_git_never_inherits_mcp_stdin_and_unregisters_after_exit(tmp_path, monkeypatch):
    registry = tmp_path / "registry"
    monkeypatch.setenv("CONTEXTOR_MCP_PROCESS_REGISTRY", str(registry))
    monkeypatch.setattr(git_context.shutil, "which", lambda _: "C:/Git/bin/git.exe")

    popen_call = {}

    class FakeProcess:
        pid = 4321
        returncode = 0

        def __init__(self, command, **kwargs):
            popen_call["command"] = command
            popen_call["kwargs"] = kwargs

        def communicate(self):
            return "abc123\n", ""

    registered = []
    removed = []

    def fake_register(directory, **record):
        registered.append((directory, record))
        return directory / "git-4321.json"

    monkeypatch.setattr(git_context.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(git_context, "register_process", fake_register)
    monkeypatch.setattr(git_context, "remove_record", removed.append)

    result = git_context._run_git(["rev-parse", "HEAD"], str(tmp_path))

    assert result == "abc123"
    assert popen_call["command"][0] == "C:/Git/bin/git.exe"
    assert popen_call["kwargs"]["stdin"] is subprocess.DEVNULL
    assert popen_call["kwargs"]["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert popen_call["kwargs"]["env"]["GIT_PAGER"] == "cat"
    assert registered[0][0] == registry
    assert registered[0][1]["parent_pid"] == os.getpid()
    assert removed == [registry / "git-4321.json"]


def test_git_unregisters_even_when_communication_fails(tmp_path, monkeypatch):
    registry = tmp_path / "registry"
    monkeypatch.setenv("CONTEXTOR_MCP_PROCESS_REGISTRY", str(registry))

    class BrokenProcess:
        pid = 9876

        def __init__(self, *_args, **_kwargs):
            pass

        def communicate(self):
            raise OSError("simulated pipe failure")

    record = registry / "git-9876.json"
    removed = []
    monkeypatch.setattr(git_context.subprocess, "Popen", BrokenProcess)
    monkeypatch.setattr(git_context, "register_process", lambda *_args, **_kwargs: record)
    monkeypatch.setattr(git_context, "remove_record", removed.append)

    assert git_context._run_git(["status"], str(tmp_path)) is None
    assert removed == [record]


def test_registry_rejects_reused_pid(monkeypatch):
    record = {
        "pid": 123,
        "executable": "C:/Git/bin/git.exe",
        "creation_time": 100,
    }
    monkeypatch.setattr(
        mcp_process_registry,
        "process_identity",
        lambda _pid: ("C:/Git/bin/git.exe", 200, True),
    )

    assert not mcp_process_registry.record_matches_process(record)


def _write_process_record(directory: Path, name: str, **values) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def test_startup_cleanup_stops_only_orphaned_registered_processes(tmp_path, monkeypatch):
    directory = tmp_path / "registry"
    orphan = _write_process_record(
        directory, "git-10", pid=10, parent_pid=20, kind="git"
    )
    live = _write_process_record(
        directory, "git-11", pid=11, parent_pid=21, kind="git"
    )
    stopped = []

    monkeypatch.setattr(mcp_server, "record_matches_process", lambda _record: True)
    monkeypatch.setattr(
        mcp_server,
        "process_identity",
        lambda pid: ("python.exe", None, pid == 21),
    )
    monkeypatch.setattr(
        mcp_server,
        "terminate_registered_process",
        lambda record: stopped.append(record["pid"]) or True,
    )

    mcp_server._cleanup_orphaned_processes(directory)

    assert stopped == [10]
    assert not orphan.exists()
    assert live.exists()


def test_shutdown_cleanup_stops_only_children_owned_by_server(tmp_path, monkeypatch):
    directory = tmp_path / "registry"
    owned = _write_process_record(
        directory, "git-30", pid=30, parent_pid=100, kind="git"
    )
    foreign = _write_process_record(
        directory, "git-31", pid=31, parent_pid=200, kind="git"
    )
    stopped = []
    monkeypatch.setattr(
        mcp_server,
        "terminate_registered_process",
        lambda record: stopped.append(record["pid"]) or True,
    )

    mcp_server._cleanup_owned_processes(directory, owner_pid=100)

    assert stopped == [30]
    assert not owned.exists()
    assert foreign.exists()


def test_mcp_single_file_worker_uses_registry_and_restores_environment(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    target = repo / "module.py"
    repo.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    calls = []

    def fake_analysis(
        file_path, repo_path, log=None, additional_excludes=None
    ):
        calls.append((file_path, repo_path, log, additional_excludes))
        assert os.environ["CONTEXTOR_DISABLE_PROCESS_POOL"] == "1"
        assert os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] == str(
            mcp_process_registry.registry_dir(repo)
        )

    monkeypatch.setattr(ContextorFacade, "analyze_single_file", fake_analysis)
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", "original-cache")
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    monkeypatch.delenv("CONTEXTOR_MCP_PROCESS_REGISTRY", raising=False)

    asyncio.run(mcp_server._run_analysis_worker("single_file", repo, target))

    assert calls == [(str(target), str(repo), mcp_server._stderr_log, None)]
    assert os.environ["CONTEXTOR_CACHE_DIR"] == "original-cache"
    assert "CONTEXTOR_DISABLE_PROCESS_POOL" not in os.environ
    assert "CONTEXTOR_MCP_PROCESS_REGISTRY" not in os.environ


def test_mcp_analysis_worker_forwards_per_run_excludes(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    calls = []

    def fake_analysis(
        repo_path, log=None, progress_callback=None, additional_excludes=None
    ):
        calls.append((repo_path, additional_excludes))
        return [], object()

    monkeypatch.setattr(ContextorFacade, "analyze_project", fake_analysis)

    asyncio.run(
        mcp_server._run_analysis_worker(
            "project", repo, exclude_paths=["tests", "legacy/adapter.py"]
        )
    )

    assert calls == [
        (str(repo), ["tests", "legacy/adapter.py"])
    ]


def test_single_file_report_is_written_end_to_end(sample_repo, isolated_dirs):
    target = sample_repo / "core" / "alpha.py"

    output = Path(ContextorFacade.analyze_single_file(str(target), str(sample_repo)))

    assert output.is_file()
    assert output.name == "single_core.alpha.json"
    assert output.with_name("single_core.alpha_graph_analytics.json").is_file()
    assert output.with_name("single_core.alpha_llm_context.md").is_file()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert Path(report["file"]).resolve() == target.resolve()
    assert report["module_id"]
    assert report["module_name"] == "core.alpha"
    assert report["generated_at"]
    snapshots = [
        path
        for path in output.parent.glob(f"{sample_repo.name}_*")
        if path.is_dir()
    ]
    assert len(snapshots) == 1
    assert (snapshots[0] / output.name).is_file()
    assert (
        snapshots[0] / "single_core.alpha_graph_analytics.json"
    ).is_file()
    assert (snapshots[0] / "single_core.alpha_llm_context.md").is_file()


def test_semantic_artifact_diff_reports_signature_changes():
    old = {
        "symbols": {
            "functions": ["kept", "removed"],
            "classes": [],
            "methods": [],
            "globals": [],
            "signatures": {
                "kept": "def kept(value: int) -> int",
                "removed": "def removed()",
            },
        }
    }
    new = {
        "symbols": {
            "functions": ["kept", "added"],
            "classes": [],
            "methods": [],
            "globals": [],
            "signatures": {
                "kept": "def kept(value: str) -> str",
                "added": "def added()",
            },
        }
    }

    result = mcp_server._semantic_artifact_diff(old, new)

    assert result["symbols_added"] == ["added"]
    assert result["symbols_removed"] == ["removed"]
    assert result["affected_symbols"] == ["added", "kept", "removed"]
    assert result["signatures_changed"]["kept"] == {
        "before": "def kept(value: int) -> int",
        "after": "def kept(value: str) -> str",
    }
    assert result["changed_symbol_count"] == 3
    assert result["body_only_changes_tracked"] is False


def test_artifact_lookup_ignores_stale_registry_entries(tmp_path, monkeypatch):
    report = tmp_path / "artifacts.json"
    report.write_text(
        json.dumps(
            {
                "artifacts": {
                    "A1/1": {
                        "kind": "function",
                        "definer_module": "1/1",
                        "consumer_module_indices": [],
                        "consumer_count": 0,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda *_: report)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {},
            {"1/1": "pkg.module"},
            {
                "pkg.module::target": "A1/1",
                "stale.module::target": "A9/9",
            },
            {
                "A1/1": "pkg.module::target",
                "A9/9": "stale.module::target",
            },
        ),
    )

    result = json.loads(
        mcp_server.lookup_artifact_by_symbol.fn(
            repo_path=str(tmp_path), symbol_name="target"
        )
    )

    assert result["match_count"] == 1
    assert list(result["artifacts"]) == ["A1/1"]
    assert result["artifacts"]["A1/1"]["kind"] == "function"
    assert result["data_source"] == "current_artifacts_compact"


def test_file_edit_context_decodes_modules_and_marks_unresolved_api(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    target = repo / "pkg" / "module.py"
    target.parent.mkdir(parents=True)
    target.write_text("def api():\n    pass\n", encoding="utf-8")
    reports = {
        "repo_graph_analytics.json": {
            "modules": {"pkg.module": {"layer": "domain"}},
            "module_dependency_matrix": {
                "1/1": {"2/1": {"import": 1}, "4/1": {"import": 1}},
                "3/1": {"1/1": {"import": 1}},
                "5/1": {"1/1": {"import": 1}},
            },
        },
        "repo_artifacts_compact.json": {
            "artifacts": {
                "A1/1": {"definer_module": "1/1"},
                "A2/1": {"definer_module": "1/1"},
                "A3/1": {"definer_module": "1/1"},
            }
        },
        "repo_summary.json": {"top_hotspots": []},
    }
    paths = {}
    for name, payload in reports.items():
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    monkeypatch.setattr(
        mcp_server,
        "_get_canonical_report",
        lambda _root, name: paths.get(name),
    )
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.module": "1/1"},
            {
                "1/1": "pkg.module",
                "2/1": "pkg.dep",
                "3/1": "tests.test_module",
                "4/1": "pkg.other",
                "5/1": "tests.test_other",
            },
            {},
            {"A1/1": "pkg.module::api", "A3/1": "pkg.module::other"},
        ),
    )

    class FakeRegistry:
        def __init__(self, _root):
            self._state = {}

        def transaction(self):
            return nullcontext()

        def get_module_id(self, _module):
            return "1/1"

    import contextor.core.reporting_engine.persistent_registry as registry_module

    monkeypatch.setattr(registry_module, "PersistentIdentityRegistry", FakeRegistry)

    result = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(repo), file_path="pkg/module.py", max_items=1
        )
    )

    assert result["module"] == "pkg.module"
    assert result["file_exists"] is True
    assert result["module_id"] == "1/1"
    assert result["imports"] == [{"module_id": "2/1", "module": "pkg.dep"}]
    assert result["consumers"] == [
        {"module_id": "3/1", "module": "tests.test_module"}
    ]
    assert result["public_api"] == {"A1/1": "pkg.module::api"}
    assert result["public_api_total"] == 2
    assert result["public_api_truncated"] is True
    assert result["unresolved_public_api_ids"] == ["A2/1"]
    assert result["imports_total"] == 2
    assert result["imports_truncated"] is True
    assert result["consumers_total"] == 2
    assert result["consumers_truncated"] is True
    assert result["tests_covering"]["tests"] == [
        {"module_id": "3/1", "module": "tests.test_module"}
    ]
    assert result["tests_covering"]["total"] == 2
    assert result["tests_covering"]["truncated"] is True


def test_artifacts_for_module_includes_live_zero_consumer_signature(
    tmp_path, monkeypatch
):
    report = tmp_path / "artifacts.json"
    report.write_text(json.dumps({"artifacts": {}}), encoding="utf-8")
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda *_: report)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.module": "1/1"},
            {"1/1": "pkg.module"},
            {"pkg.module::unused": "A1/1"},
            {"A1/1": "pkg.module::unused"},
        ),
    )

    class State:
        artifacts = {
            "pkg.module": {
                "symbols": {
                    "classes": [],
                    "functions": ["unused"],
                    "methods": [],
                    "globals": [],
                    "signatures": {"unused": "def unused(value: int) -> None"},
                }
            }
        }

    class Engine:
        state = State()

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: Engine())

    result = json.loads(
        mcp_server.get_artifacts_for_module.fn(
            repo_path=str(tmp_path), module_name="pkg.module"
        )
    )

    assert result["complete_symbol_catalog"] is True
    assert result["artifact_count"] == 1
    assert result["total_artifact_count"] == 1
    assert result["truncated"] is False
    assert result["artifacts"]["A1/1"] == {
        "artifact_id": "A1/1",
        "symbol": "unused",
        "full_name": "pkg.module::unused",
        "kind": "function",
        "signature": "def unused(value: int) -> None",
        "consumer_count": 0,
        "consumers": [],
    }


def test_bounded_mcp_collections_report_truncation():
    selected, total, truncated = mcp_server._bounded_items(
        ["first", "second", "third"], 2
    )

    assert selected == ["first", "second"]
    assert total == 3
    assert truncated is True


def test_bounded_canonical_query_preserves_totals_for_lists_and_dicts():
    bounded_list = mcp_server._bounded_query_result([1, 2, 3], 2)
    bounded_dict = mcp_server._bounded_query_result(
        {"first": 1, "second": 2}, 1
    )

    assert bounded_list == {
        "result": [1, 2],
        "result_type": "list",
        "total_items": 3,
        "truncated": True,
    }
    assert bounded_dict == {
        "result": {"first": 1},
        "result_type": "dict",
        "total_items": 2,
        "truncated": True,
    }


def test_layer_cluster_ids_are_resolved_without_an_extra_lookup():
    result = mcp_server._resolve_cluster_ids(
        {"modules": ["1/1", "2/1"], "shared_artifact_keys": ["A1/1"]},
        {"1/1": "pkg.first", "2/1": "pkg.second"},
        {"A1/1": "pkg.first::shared"},
    )

    assert result["modules"] == ["pkg.first", "pkg.second"]
    assert result["shared_artifact_keys"] == ["pkg.first::shared"]
    assert result["ids_resolved"] is True


def test_live_artifact_search_handles_list_based_symbol_state(
    tmp_path, monkeypatch
):
    class Registry:
        def get_module_id(self, module):
            return {"pkg.module": "1/1", "tests.test_module": "2/1"}.get(module)

        def get_module_path(self, module_id):
            return {"2/1": "tests.test_module"}.get(module_id)

    class State:
        artifacts = {
            "pkg.module": {
                "symbols": {
                    "functions": ["target"],
                    "classes": [],
                    "methods": [],
                    "globals": [],
                },
                "consumers": {"target": {"consumers": ["2/1"]}},
            }
        }

    class Engine:
        state = State()
        registry = Registry()

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: Engine())

    result = json.loads(
        mcp_server.search_artifacts.fn(
            repo_path=str(tmp_path), search_term="target", limit=1
        )
    )

    assert result["total_matches"] == 1
    assert result["truncated"] is False
    assert result["artifacts"]["pkg.module::target"]["consumers"] == [
        "tests.test_module"
    ]


def test_file_edit_context_missing_module_does_not_open_registry_transaction(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    reports = {}
    for name, payload in {
        "repo_graph_analytics.json": {"modules": {}, "module_dependency_matrix": {}},
        "repo_artifacts_compact.json": {"artifacts": {}},
    }.items():
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        reports[name] = path
    monkeypatch.setattr(
        mcp_server, "_get_canonical_report", lambda _root, name: reports.get(name)
    )
    monkeypatch.setattr(mcp_server, "_read_registries", lambda _root: ({}, {}, {}, {}))

    result = mcp_server.get_file_edit_context.fn(
        repo_path=str(repo), file_path="missing.py"
    )

    assert "not present in the current registry" in result


def test_artifact_blast_radius_uses_only_current_compact_report(
    tmp_path, monkeypatch
):
    report = tmp_path / "artifacts.json"
    report.write_text(
        json.dumps({"artifacts": {"A1/1": {
            "kind": "function",
            "definer_module": "1/1",
            "consumer_module_indices": ["2/1"],
        }}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda *_: report)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {},
            {"1/1": "pkg.module", "2/1": "tests.test_module"},
            {},
            {
                "A1/1": "pkg.module::target",
                "A9/9": "stale.module::target",
            },
        ),
    )

    result = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(tmp_path), artifact_name="target"
        )
    )

    assert result["artifact_id"] == "A1/1"
    assert result["definer"] == "pkg.module"
    assert result["consumers"] == ["tests.test_module"]
    assert result["evidence_scope"] == "direct_static_artifact_consumption"
