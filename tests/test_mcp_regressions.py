"""Regression tests for MCP subprocess handling and single-file reports."""

import asyncio
import inspect
import json
import os
import subprocess
import threading
from types import SimpleNamespace
from contextlib import nullcontext
from pathlib import Path

import pytest

pytestmark = pytest.mark.live

from contextor import mcp_process_registry, mcp_server
from contextor.core.analysis import git_context
from contextor.core.api.facade import ContextorFacade
from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    load_engine_state,
)
from contextor.core.report_query import IndexCatalog, query_indexed_report
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.symbol_engine.extractor import extract_file_symbols


def _live_engine_fixture():
    graph = SimpleNamespace(
        hard_edges={"pkg.module": {"pkg.dep"}, "tests.test_module": {"pkg.module"}},
        soft_edges={"external.client": {"pkg.module"}},
    )
    module = SimpleNamespace(module_id="1/1", path="pkg/module.py", imports=[])
    state = RepositoryAnalysisState(
        modules={"pkg.module": module, "pkg.dep": object(), "tests.test_module": object()},
        artifacts={
            "pkg.module": {
                "own_symbols": ["api"],
                "symbols": {"functions": ["api"], "signatures": {"api": "api()"}},
                "consumers": {
                    "api": {
                        "consumer_count": {"total": 1},
                        "consumers": ["tests.test_module"],
                    }
                },
            }
        },
        dependency_graph=graph,
        metrics={"pkg.module": {"layer": "domain", "hub_score": 0.4}},
        layer_information={
            "layer_index": [{"layer": "pkg", "module_count": 2}],
            "hotspots": [{"module": "pkg.module", "score": 0.7}],
            "debt": {"score": 3},
            "summary_data": {"action_items": ["review pkg.module"]},
        },
    )
    return SimpleNamespace(state=state)


def test_live_first_tools_work_without_any_saved_reports(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    target = repo / "pkg" / "module.py"
    target.parent.mkdir(parents=True)
    target.write_text("def api():\n    return 1\n", encoding="utf-8")
    engine = _live_engine_fixture()
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda *_args: None)
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.module": "1/1", "pkg.dep": "2/1", "tests.test_module": "3/1"},
            {"1/1": "pkg.module", "2/1": "pkg.dep", "3/1": "tests.test_module"},
            {"pkg.module::api": "A1/1"},
            {"A1/1": "pkg.module::api"},
        ),
    )

    architecture = json.loads(mcp_server.get_project_architecture.fn(str(repo)))
    blast = json.loads(
        mcp_server.get_artifact_blast_radius.fn(str(repo), "pkg.module::api", compact=False)
    )
    edit = json.loads(
        mcp_server.get_file_edit_context.fn(
            str(repo), "pkg/module.py", compact=False, max_items=10
        )
    )
    layer = json.loads(mcp_server.get_layer_isolation.fn(str(repo), "pkg", compact=False))

    assert architecture["data_source"] == "live_canonical_state"
    assert architecture["module_count"] == 3
    assert blast["data_source"] == "live_canonical_state"
    assert blast["consumers"]["items"] == ["tests.test_module"]
    assert edit["dependency_data_source"] == "live_canonical_graph"
    assert edit["public_api"]["total"] == 1
    assert edit["tests_covering"]["available"] is True
    assert layer["data_source"] == "live_canonical_graph"
    assert layer["module_count"] == 2


def test_analysis_endpoint_returns_reusable_job_and_pollable_completion(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    release = threading.Event()

    async def fake_worker(*_args, **_kwargs):
        await asyncio.to_thread(release.wait)

    published = []
    engine = SimpleNamespace(state={"fresh": True})
    client = SimpleNamespace(
        publish=lambda state, *, origin, timeout: published.append(
            (state, origin, timeout)
        ) or {"revision": 1}
    )
    monkeypatch.setattr(mcp_server, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        "contextor.core.live_state.connect_or_start",
        lambda _root, timeout: client,
    )
    mcp_server._analysis_tasks.clear()
    mcp_server._analysis_jobs_by_repo.clear()

    async def scenario():
        first = json.loads(await mcp_server.analyze_project.fn(str(repo)))
        second = json.loads(await mcp_server.analyze_project.fn(str(repo)))

        assert first["status"] == "queued"
        assert second["job_id"] == first["job_id"]
        assert second["reused"] is True
        running = json.loads(
            mcp_server.get_analysis_status.fn(str(repo), first["job_id"])
        )
        assert running["status"] in {"queued", "running"}

        task = mcp_server._analysis_tasks[first["job_id"]]
        release.set()
        task.join(timeout=5)
        assert not task.is_alive()
        completed = json.loads(
            mcp_server.get_analysis_status.fn(str(repo), first["job_id"])
        )
        assert completed["status"] == "completed"
        assert completed["error"] is None
        assert completed["live_publish_status"] == "success"
        assert completed["live_publish_revision"] == 1
        assert completed["live_publish_warning"] is None
        assert published == [(engine.state, "mcp_analysis", 10.0)]

    asyncio.run(scenario())


def test_analysis_job_persists_failure_for_later_polling(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    async def broken_worker(*_args, **_kwargs):
        raise RuntimeError("simulated analysis failure")

    monkeypatch.setattr(mcp_server, "_run_analysis_worker", broken_worker)
    mcp_server._analysis_tasks.clear()
    mcp_server._analysis_jobs_by_repo.clear()

    async def scenario():
        accepted = json.loads(await mcp_server.analyze_project.fn(str(repo)))
        task = mcp_server._analysis_tasks[accepted["job_id"]]
        task.join(timeout=5)
        assert not task.is_alive()
        failed = json.loads(
            mcp_server.get_analysis_status.fn(str(repo), accepted["job_id"])
        )
        assert failed["status"] == "failed"
        assert "simulated analysis failure" in failed["error"]
        assert failed["live_publish_status"] == "not_attempted"

    asyncio.run(scenario())


def test_analysis_job_preserves_live_publish_timeout_status(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    async def fake_worker(*_args, **_kwargs):
        return {"skipped_python_files": []}

    engine = SimpleNamespace(state={"fresh": True})

    class Client:
        def publish(self, _state, *, origin, timeout):
            assert origin == "mcp_analysis"
            assert timeout == 10.0
            raise TimeoutError("simulated LIVE timeout")

    monkeypatch.setattr(mcp_server, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        "contextor.core.live_state.connect_or_start",
        lambda _root, timeout: Client(),
    )
    mcp_server._analysis_tasks.clear()
    mcp_server._analysis_jobs_by_repo.clear()

    async def scenario():
        accepted = json.loads(await mcp_server.analyze_project.fn(str(repo)))
        task = mcp_server._analysis_tasks[accepted["job_id"]]
        task.join(timeout=5)
        assert not task.is_alive()

        completed = json.loads(
            mcp_server.get_analysis_status.fn(str(repo), accepted["job_id"])
        )
        assert completed["status"] == "completed"
        assert completed["live_publish_status"] == "timed_out"
        assert completed["live_publish_revision"] is None
        assert "simulated LIVE timeout" in completed["live_publish_warning"]
        assert "LIVE publish timed_out" in completed["message"]

    asyncio.run(scenario())


def test_analysis_status_marks_previous_server_job_interrupted(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    job_id = "a" * 32
    mcp_server._write_analysis_job(
        repo,
        {
            "job_id": job_id,
            "operation": "project",
            "repo_path": str(repo),
            "target": None,
            "status": "running",
            "created_at": "2026-01-01T00:00:00+00:00",
            "started_at": "2026-01-01T00:00:01+00:00",
            "completed_at": None,
            "message": "Analysis started.",
            "error": None,
            "owner_pid": -1,
        },
    )

    result = json.loads(mcp_server.get_analysis_status.fn(str(repo), job_id))

    assert result["status"] == "interrupted"
    assert result["error"] == "owner_process_changed"
    assert result["completed_at"]


def test_project_worker_carries_indexer_skips_into_durable_job_status(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    skipped = [
        {"path": "broken_indent.py", "reason": "is not valid Python (line 2, column 5: unexpected indent)", "line_number": 2, "column_number": 5},
        {"path": "broken_bracket.py", "reason": "is not valid Python (line 1, column 8: '[' was never closed)"},
    ]

    def fake_analyze_project(*_args, **_kwargs):
        return [], SimpleNamespace(summary_data={"skipped_files": skipped})

    monkeypatch.setattr(
        mcp_server.ContextorFacade,
        "analyze_project",
        staticmethod(fake_analyze_project),
    )

    outcome = asyncio.run(mcp_server._run_analysis_worker("project", repo))

    assert outcome == {"skipped_python_files": skipped}


def test_analysis_status_bounds_and_exposes_skipped_python_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    job_id = "b" * 32
    mcp_server._write_analysis_job(
        repo,
        {
            "job_id": job_id,
            "operation": "project",
            "repo_path": str(repo),
            "target": None,
            "status": "completed",
            "created_at": "2026-01-01T00:00:00+00:00",
            "started_at": "2026-01-01T00:00:01+00:00",
            "completed_at": "2026-01-01T00:00:02+00:00",
            "message": "Analysis completed successfully.",
            "error": None,
            "owner_pid": os.getpid(),
            "skipped_python_files": [
                {"path": "broken_indent.py", "reason": "is not valid Python (line 2, column 5: unexpected indent)", "line_number": 2, "column_number": 5},
                {"path": "unreadable.py", "reason": "not valid text in its declared encoding"},
                {"path": "broken_bracket.py", "reason": "is not valid Python (line 1: '[' was never closed)"},
            ],
        },
    )

    bounded = json.loads(
        mcp_server.get_analysis_status.fn(str(repo), job_id, max_skipped_files=1)
    )
    collection = bounded["analysis_coverage"]["skipped_python_files"]
    assert collection["total"] == 3
    assert collection["syntax_error_count"] == 2
    assert collection["truncated"] is True
    assert len(collection["items"]) == 1
    assert collection["items"][0]["line_number"] == 2
    assert collection["items"][0]["column_number"] == 5

    unbounded = json.loads(
        mcp_server.get_analysis_status.fn(str(repo), job_id, max_skipped_files=None)
    )
    all_items = unbounded["analysis_coverage"]["skipped_python_files"]
    assert all_items["truncated"] is False
    assert len(all_items["items"]) == 3


def test_layer_and_single_file_tools_submit_nonblocking_jobs(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    layer = repo / "pkg"
    layer.mkdir(parents=True)
    target = layer / "module.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    calls = []

    def fake_start(operation, root, submitted_target=None, exclude_paths=None):
        calls.append((operation, root, submitted_target, exclude_paths))
        return {"job_id": operation, "status": "queued"}

    monkeypatch.setattr(mcp_server, "_start_analysis_job", fake_start)

    layer_result = json.loads(
        asyncio.run(
            mcp_server.analyze_layer.fn(
                str(repo), "pkg", exclude_paths=["tests"]
            )
        )
    )
    file_result = json.loads(
        asyncio.run(
            mcp_server.analyze_single_file.fn(
                str(repo), "pkg/module.py", exclude_paths=["legacy"]
            )
        )
    )

    assert layer_result == {"job_id": "layer", "status": "queued"}
    assert file_result == {"job_id": "single_file", "status": "queued"}
    assert calls == [
        ("layer", repo.resolve(), layer.resolve(), ["tests"]),
        ("single_file", repo.resolve(), target.resolve(), ["legacy"]),
    ]


def test_analysis_status_exposes_latest_worker_progress(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    progress_written = threading.Event()
    release = threading.Event()

    async def fake_worker(*_args, log=None, **_kwargs):
        log("Indexing 42 modules...")
        progress_written.set()
        await asyncio.to_thread(release.wait)

    monkeypatch.setattr(mcp_server, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: object())
    mcp_server._analysis_tasks.clear()
    mcp_server._analysis_jobs_by_repo.clear()

    async def scenario():
        accepted = json.loads(await mcp_server.analyze_project.fn(str(repo)))
        await asyncio.to_thread(progress_written.wait)
        running = json.loads(
            mcp_server.get_analysis_status.fn(str(repo), accepted["job_id"])
        )
        assert running["status"] == "running"
        assert running["message"] == "Indexing 42 modules..."
        release.set()
        task = mcp_server._analysis_tasks[accepted["job_id"]]
        task.join(timeout=5)
        assert not task.is_alive()

    asyncio.run(scenario())


def test_lookup_index_entries_distinguishes_active_recovery_and_missing(
    tmp_path, monkeypatch
):
    catalog = IndexCatalog(
        modules={"1/1": "pkg.active"},
        artifacts={"A1/1": "pkg.active::run"},
        recovered_modules={"2/1": "pkg.removed"},
        recovered_artifacts={"A2/1": "pkg.removed::old"},
    )
    monkeypatch.setattr(mcp_server, "catalog_from_registry", lambda _root: catalog)

    result = json.loads(
        mcp_server.lookup_index_entries.fn(
            repo_path=str(tmp_path),
            ids=["1/1", "2/1", "A1/1", "a2/1", "999/1"],
        )
    )

    assert result["1/1"] == {"name": "pkg.active", "status": "active"}
    assert result["2/1"] == {"name": "pkg.removed", "status": "recovery"}
    assert result["A1/1"] == {"name": "pkg.active::run", "status": "active"}
    assert result["a2/1"] == {"name": "pkg.removed::old", "status": "recovery"}
    assert result["999/1"] == {"name": None, "status": "missing"}


def test_extract_indexed_report_context_returns_every_shared_resolver_block(tmp_path, monkeypatch):
    catalog = IndexCatalog(
        modules={"1/1": "main", "2/1": "pkg.cli"},
        artifacts={"A1/1": "main::main", "A2/1": "pkg.cli::main"},
        module_paths={"main": "main.py", "pkg.cli": "pkg/cli.py"},
    )
    report = {
        "_format_version": "3",
        "artifacts": {
            "A1/1": {
                "definer_module": "1/1",
                "consumer_module_indices": ["2/1"],
                "nested": {"text": "complete }, block"},
            },
            "A2/1": {
                "definer_module": "2/1",
                "consumer_module_indices": [],
            },
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(mcp_server, "catalog_from_registry", lambda *_args, **_kwargs: catalog)
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)

    raw = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="pkg/cli.py",
        report_path=str(report_path),
    )
    result = json.loads(raw)
    expected = query_indexed_report(report, "pkg/cli.py", catalog, repo_root=str(tmp_path))

    assert result["artifacts"] == expected["artifacts"]
    assert result["artifact_count"] == 2
    assert result["total_artifact_count"] == 2
    assert result["truncated"] is False
    assert result["artifacts"]["main::main"]["nested"]["text"] == "complete }, block"

    bounded = json.loads(mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path), query="pkg/cli.py", report_path=str(report_path),
        max_items=1, fields=["artifacts", "artifact_count", "total_artifact_count", "truncated"],
    ))
    assert bounded["artifact_count"] == 1
    assert bounded["total_artifact_count"] == 2
    assert bounded["truncated"] is True

    unbounded = json.loads(mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path), query="pkg/cli.py", report_path=str(report_path),
        max_items=None, fields=["artifacts", "truncated"],
    ))
    assert len(unbounded["artifacts"]) == 2
    assert unbounded["truncated"] is False


def test_extract_indexed_report_context_can_filter_to_public_api(tmp_path, monkeypatch):
    catalog = IndexCatalog(
        modules={"1/1": "pkg.cli"},
        artifacts={
            "A1/1": "pkg.cli::run",
            "A2/1": "pkg.cli::_helper",
            "A3/1": "pkg.cli::__enter__",
        },
        module_paths={"pkg.cli": "pkg/cli.py"},
    )
    report = {
        "_format_version": "3",
        "artifacts": {
            artifact_id: {
                "definer_module": "1/1",
                "consumer_module_indices": [],
                "consumer_count": 0,
            }
            for artifact_id in catalog.artifacts
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(mcp_server, "catalog_from_registry", lambda *_args, **_kwargs: catalog)
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)

    all_artifacts = json.loads(
        mcp_server.extract_indexed_report_context.fn(
            repo_path=str(tmp_path), query="pkg/cli.py", report_path=str(report_path)
        )
    )
    public_only = json.loads(
        mcp_server.extract_indexed_report_context.fn(
            repo_path=str(tmp_path),
            query="pkg/cli.py",
            report_path=str(report_path),
            public_api_only=True,
        )
    )

    assert set(all_artifacts["artifacts"]) == {
        "pkg.cli::run",
        "pkg.cli::_helper",
        "pkg.cli::__enter__",
    }
    assert set(public_only["artifacts"]) == {
        "pkg.cli::run",
        "pkg.cli::__enter__",
    }
    assert public_only["artifact_count"] == 2


def test_file_edit_context_prefers_fresh_live_graph_over_stale_saved_matrix(
    tmp_path, monkeypatch
):
    graph_report = tmp_path / "graph.json"
    artifact_report = tmp_path / "artifacts.json"
    summary_report = tmp_path / "summary.json"
    graph_report.write_text(
        json.dumps({"modules": {}, "module_dependency_matrix": {}}), encoding="utf-8"
    )
    artifact_report.write_text(json.dumps({"artifacts": {}}), encoding="utf-8")
    summary_report.write_text(json.dumps({"top_hotspots": []}), encoding="utf-8")
    reports = {
        "graph_analytics.json": graph_report,
        "artifacts_compact.json": artifact_report,
        "summary.json": summary_report,
    }
    monkeypatch.setattr(
        mcp_server,
        "_get_canonical_report",
        lambda _root, name: next(
            (path for suffix, path in reports.items() if name.endswith(suffix)), None
        ),
    )
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"provider": "1/1", "consumer": "2/1"},
            {"1/1": "provider", "2/1": "consumer"},
            {"provider::run": "A1/1", "provider::_private": "A2/1"},
            {"A1/1": "provider::run", "A2/1": "provider::_private"},
        ),
    )
    graph = SimpleNamespace(
        hard_edges={"provider": set(), "consumer": {"provider"}},
        soft_edges={"provider": set(), "consumer": set()},
    )
    engine = SimpleNamespace(
        state=SimpleNamespace(
            modules={"provider": object(), "consumer": object()},
            artifacts={"provider": {"symbols": {"functions": ["run"]}}},
            dependency_graph=graph,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    (tmp_path / "provider.py").write_text("def run(): pass\n", encoding="utf-8")

    result = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(tmp_path), file_path="provider.py", compact=False
        )
    )

    assert result["consumers"]["items"] == [
        {"module_id": "2/1", "module": "consumer"}
    ]
    assert result["public_api"]["items"] == {"A1/1": "provider::run"}
    assert result["dependency_data_source"] == "live_canonical_graph"
    assert result["artifact_data_source"] == "live_registry_and_symbol_state"


def test_incremental_live_state_persistence_roundtrips_for_restart(
    tmp_path, monkeypatch
):
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    registry = PersistentIdentityRegistry(str(tmp_path))
    state = RepositoryAnalysisState(
        modules={},
        artifacts={"new.module": {"symbols": {"functions": ["run"]}}},
        dependency_graph=None,
        trie={},
        package_root=None,
        artifact_consumption={},
    )
    engine = SimpleNamespace(
        state=state,
        state_manager=SimpleNamespace(state_id="after-incremental-update"),
    )

    persisted = mcp_server._persist_live_engine(tmp_path, engine)

    from contextor.core.paths import repo_cache_dir

    loaded = load_engine_state(
        str(repo_cache_dir(tmp_path)),
        "after-incremental-update",
        expected_repo_id=registry.repo_id,
        expected_root_path=tmp_path,
    )
    assert persisted is True
    assert loaded is not None
    assert loaded.artifacts == state.artifacts


def test_fastmcp_schema_exposes_analysis_parameters():
    signature = inspect.signature(mcp_server.analyze_project.fn)
    status_signature = inspect.signature(mcp_server.get_analysis_status.fn)
    extraction_signature = inspect.signature(
        mcp_server.extract_indexed_report_context.fn
    )

    assert "exclude_paths" in signature.parameters
    assert "job_id" in status_signature.parameters
    assert "public_api_only" in extraction_signature.parameters
def test_update_file_marks_running_mcp_server_as_requiring_restart(monkeypatch):
    server_path = Path(mcp_server.__file__).resolve()
    repo = server_path.parents[1]
    engine = SimpleNamespace(
        state=SimpleNamespace(artifacts={"contextor.mcp_server": {}}),
        update_file=lambda file_path: SimpleNamespace(
            status="UPDATED",
            file_path=file_path,
            graph_state="fresh",
            dependencies_state="fresh",
            blast_radius_state="fresh",
            local_metrics_state="deferred",
            global_metrics_state="deferred",
            artifact_consumption_state="deferred",
            affected_modules=["contextor.mcp_server"],
            delta=None,
        ),
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(mcp_server, "_persist_live_engine", lambda *_args: True)

    current = json.loads(
        mcp_server.update_file.fn(repo_path=str(repo), file_path=str(server_path))
    )
    assert current["runtime_restart_required"] is False
    assert "runtime_state" not in current

    monkeypatch.setattr(mcp_server, "_MCP_SERVER_SOURCE_FINGERPRINT", "stale")
    result = json.loads(
        mcp_server.update_file.fn(repo_path=str(repo), file_path=str(server_path))
    )

    assert result["runtime_restart_required"] is True
    assert result["runtime_state"] == "stale_until_mcp_server_restart"
    assert "running MCP process" in result["runtime_warning"]
    assert "Restart" in result["runtime_warning"]


def test_mcp_update_file_shapes_affected_modules_compact_full_and_fields(tmp_path, monkeypatch):
    target = tmp_path / "provider.py"
    target.write_text("def run(): pass\n", encoding="utf-8")
    engine = SimpleNamespace(
        state=SimpleNamespace(artifacts={"provider": {}}),
        update_file=lambda file_path: SimpleNamespace(
            status="UPDATED",
            file_path=file_path,
            graph_state="fresh",
            dependencies_state="fresh",
            blast_radius_state="fresh",
            local_metrics_state="deferred",
            global_metrics_state="deferred",
            artifact_consumption_state="deferred",
            affected_modules=["consumer_a", "consumer_b", "provider"],
            delta=None,
        ),
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(mcp_server, "_persist_live_engine", lambda *_args: True)

    compact = json.loads(
        mcp_server.update_file.fn(repo_path=str(tmp_path), file_path=str(target), compact=True)
    )
    assert compact["status"] == "UPDATED"
    assert compact["blast_radius_state"] == "fresh"
    assert compact["affected_modules"] == {"total": 3, "truncated": False}
    assert "items" not in compact["affected_modules"]

    full = json.loads(
        mcp_server.update_file.fn(repo_path=str(tmp_path), file_path=str(target), compact=False, max_items=2)
    )
    assert full["affected_modules"] == {
        "total": 3,
        "truncated": True,
        "items": ["consumer_a", "consumer_b"],
    }

    filtered = json.loads(
        mcp_server.update_file.fn(
            repo_path=str(tmp_path),
            file_path=str(target),
            fields=["status", "affected_modules"],
        )
    )
    assert set(filtered.keys()) == {"status", "affected_modules"}
    assert filtered["status"] == "UPDATED"



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
    assert result["bodies_changed"] == []
    assert result["body_only_changes_tracked"] is True


def test_semantic_artifact_diff_flags_body_only_change_without_body_text(tmp_path):
    source = tmp_path / "module.py"
    source.write_text(
        "def calculate(value: int) -> int:\n"
        "    return value + 1\n",
        encoding="utf-8",
    )
    old = {"symbols": extract_file_symbols(source)}
    source.write_text(
        "def calculate(value: int) -> int:\n"
        "    # formatting/comments do not enter the hash\n"
        "    return value * 2\n",
        encoding="utf-8",
    )
    new = {"symbols": extract_file_symbols(source)}

    result = mcp_server._semantic_artifact_diff(old, new)

    assert result["symbols_added"] == []
    assert result["symbols_removed"] == []
    assert result["signatures_changed"] == {}
    assert result["bodies_changed"] == ["calculate"]
    assert result["body_change_count"] == 1
    assert result["affected_symbols"] == ["calculate"]
    assert "return value" not in json.dumps(result)


def test_semantic_diff_view_is_compact_bounded_and_schema_stable():
    diff = {
        "symbols_added": ["a", "b"],
        "symbols_removed": ["c"],
        "signatures_changed": {
            "a": {"before": "def a()", "after": "def a(value)"},
            "b": {"before": "def b()", "after": "def b(value)"},
        },
        "bodies_changed": ["a", "b"],
        "affected_symbols": ["a", "b", "c"],
        "changed_symbol_count": 3,
        "body_change_count": 2,
        "body_only_changes_tracked": True,
    }

    compact = mcp_server._semantic_diff_view(diff, max_items=1, compact=True)
    full = mcp_server._semantic_diff_view(diff, max_items=1, compact=False)

    assert compact["symbols_added"] == {"total": 2, "truncated": True}
    assert "items" not in compact["signatures_changed"]
    assert full["symbols_added"]["items"] == ["a"]
    assert full["signatures_changed"]["items"] == {
        "a": {"before": "def a()", "after": "def a(value)"}
    }
    assert full["affected_symbols"]["total"] == 3
    assert full["affected_symbols"]["truncated"] is True


def test_artifact_lookup_ignores_stale_registry_entries(tmp_path, monkeypatch):
    report = tmp_path / "artifacts.json"
    report.write_text(
        json.dumps(
            {
                "artifacts": {
                    "A1/1": {
                        "kind": "function",
                        "definer_module": "1/1",
                        "consumer_module_indices": ["2/1", "3/1"],
                        "consumer_count": 2,
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
            {"1/1": "pkg.module", "2/1": "pkg.first", "3/1": "pkg.second"},
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
            repo_path=str(tmp_path), symbol_name="target", evidence_limit=1
        )
    )

    assert result["match_count"] == 1
    assert list(result["artifacts"]) == ["A1/1"]
    assert result["artifacts"]["A1/1"]["kind"] == "function"
    assert result["artifacts"]["A1/1"]["consumers"] == {
        "total": 2,
        "truncated": True,
    }
    assert result["data_source"] == "current_artifacts_compact"

    full = json.loads(mcp_server.lookup_artifact_by_symbol.fn(
        repo_path=str(tmp_path), symbol_name="target", evidence_limit=1,
        compact=False, fields=["artifacts"],
    ))
    assert full["artifacts"]["A1/1"]["consumers"] == {
        "items": ["pkg.first"],
        "total": 2,
        "truncated": True,
    }


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
            repo_path=str(repo), file_path="pkg/module.py", max_items=1, compact=False
        )
    )

    assert result["module"] == "pkg.module"
    assert result["file_exists"] is True
    assert result["module_id"] == "1/1"
    assert result["imports"]["items"] == [
        {"module_id": "2/1", "module": "pkg.dep"}
    ]
    assert result["consumers"]["items"] == [
        {"module_id": "3/1", "module": "tests.test_module"}
    ]
    assert result["public_api"]["items"] == {"A1/1": "pkg.module::api"}
    assert result["public_api"]["total"] == 2
    assert result["public_api"]["truncated"] is True
    assert result["public_api"]["unresolved_ids"] == ["A2/1"]
    assert result["public_api"]["unresolved_total"] == 1
    assert result["imports"]["total"] == 2
    assert result["imports"]["truncated"] is True
    assert result["consumers"]["total"] == 2
    assert result["consumers"]["truncated"] is True
    assert result["tests_covering"]["tests"] == [
        {
            "module_id": "3/1",
            "module": "tests.test_module",
            "distance": 1,
            "evidence_path": ["tests.test_module", "pkg.module"],
            "evidence_scope": "static_dependency_reachability",
        }
    ]
    assert result["tests_covering"]["evidence_scope"] == (
        "static_dependency_reachability"
    )
    assert result["tests_covering"]["total"] == 2
    assert result["tests_covering"]["truncated"] is True

    compact = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(repo), file_path="pkg/module.py", max_items=1
        )
    )
    assert compact["consumers"] == {"total": 2, "truncated": True}
    assert compact["imports"] == {"total": 2, "truncated": True}
    assert compact["public_api"] == {
        "total": 2,
        "truncated": True,
        "unresolved_total": 1,
    }
    assert compact["tests_covering"]["total"] == 2
    assert "tests" not in compact["tests_covering"]

    projection = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(repo),
            file_path="pkg/module.py",
            max_items=1,
            fields=["risk_score", "consumers"],
        )
    )
    assert set(projection) == {"risk_score", "consumers"}
    assert projection["consumers"] == {"total": 2, "truncated": True}

    evidence_projection = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(repo),
            file_path="pkg/module.py",
            max_items=1,
            compact=False,
            fields=["consumers", "tests_covering"],
        )
    )
    assert evidence_projection["consumers"] == result["consumers"]
    assert evidence_projection["tests_covering"] == result["tests_covering"]

    invalid = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(repo), file_path="pkg/module.py", fields=["unknown_field"]
        )
    )
    assert invalid["error"] == "Unsupported fields for get_file_edit_context"
    assert invalid["unknown_fields"] == ["unknown_field"]


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
        "consumers": {"total": 0, "truncated": False},
    }


def test_artifacts_for_module_uses_live_state_without_compact_report(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda *_: None)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.module": "1/1"},
            {"1/1": "pkg.module"},
            {"pkg.module::run": "A1/1"},
            {"A1/1": "pkg.module::run"},
        ),
    )

    class State:
        modules = {"pkg.module": object()}
        artifacts = {
            "pkg.module": {
                "symbols": {
                    "classes": [],
                    "functions": ["run"],
                    "methods": [],
                    "globals": [],
                    "signatures": {"run": "def run() -> None"},
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

    assert result["data_sources"] == ["live_symbol_state"]
    assert result["complete_symbol_catalog"] is True
    assert result["artifacts"]["A1/1"] == {
        "artifact_id": "A1/1",
        "symbol": "run",
        "full_name": "pkg.module::run",
        "kind": "function",
        "signature": "def run() -> None",
        "consumers": {"total": 0, "truncated": False},
    }


def test_artifacts_for_module_bounds_nested_consumers(tmp_path, monkeypatch):
    report = tmp_path / "artifacts.json"
    report.write_text(json.dumps({"artifacts": {"A1/1": {
        "kind": "function",
        "definer_module": "1/1",
        "consumer_module_indices": ["2/1", "3/1"],
    }}}), encoding="utf-8")
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda *_: report)
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.module": "1/1"},
            {"1/1": "pkg.module", "2/1": "pkg.first", "3/1": "pkg.second"},
            {"pkg.module::run": "A1/1"},
            {"A1/1": "pkg.module::run"},
        ),
    )

    result = json.loads(mcp_server.get_artifacts_for_module.fn(
        repo_path=str(tmp_path), module_name="pkg.module", evidence_limit=1,
        compact=False, fields=["artifacts"],
    ))

    consumers = result["artifacts"]["A1/1"]["consumers"]
    assert consumers == {
        "items": ["pkg.first"],
        "total": 2,
        "truncated": True,
    }


def test_bounded_mcp_collections_report_truncation():
    selected, total, truncated = mcp_server._bounded_items(
        ["first", "second", "third"], 2
    )

    assert selected == ["first", "second"]
    assert total == 3
    assert truncated is True

    unbounded, unbounded_total, unbounded_truncated = mcp_server._bounded_items(
        ["first", "second", "third"], None
    )
    assert unbounded == ["first", "second", "third"]
    assert unbounded_total == 3
    assert unbounded_truncated is False


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
    assert result["artifacts"]["pkg.module::target"]["consumers"] == {
        "total": 1,
        "truncated": False,
    }

    full = json.loads(
        mcp_server.search_artifacts.fn(
            repo_path=str(tmp_path),
            search_term="target",
            limit=1,
            evidence_limit=1,
            compact=False,
            fields=["artifacts"],
        )
    )
    assert full["artifacts"]["pkg.module::target"]["consumers"] == {
        "items": ["tests.test_module"],
        "total": 1,
        "truncated": False,
    }


def test_live_artifact_search_also_returns_matching_modules(tmp_path, monkeypatch):
    class Registry:
        def get_module_id(self, module):
            return {"pkg.unique_probe": "7/1"}.get(module)

        def get_module_path(self, module_id):
            return None

    class Graph:
        hard_edges = {
            "pkg.caller": {"pkg.unique_probe"},
            "pkg.unique_probe": {"pkg.dependency"},
        }
        soft_edges = {
            "pkg.soft_caller": {"pkg.unique_probe"},
            "pkg.unique_probe": {"pkg.soft_dependency"},
        }

    class State:
        modules = {"pkg.unique_probe": object()}
        artifacts = {}
        dependency_graph = Graph()

    class Engine:
        state = State()
        registry = Registry()

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: Engine())

    result = json.loads(
        mcp_server.search_artifacts.fn(
            repo_path=str(tmp_path), search_term="unique_probe", limit=10
        )
    )

    module = result["modules"]["pkg.unique_probe"]
    assert result["total_matches"] == 1
    assert result["artifacts"] == {}
    assert module["module_id"] == "7/1"
    assert module["dependencies_inbound"] == {"total": 2, "truncated": False}
    assert module["dependencies_outbound"] == {"total": 2, "truncated": False}

    full = json.loads(
        mcp_server.search_artifacts.fn(
            repo_path=str(tmp_path),
            search_term="unique_probe",
            limit=10,
            evidence_limit=1,
            compact=False,
            fields=["modules"],
        )
    )
    full_module = full["modules"]["pkg.unique_probe"]
    assert full_module["dependencies_inbound"]["items"] == ["pkg.caller"]
    assert full_module["dependencies_inbound"]["total"] == 2
    assert full_module["dependencies_inbound"]["truncated"] is True
    assert full_module["dependencies_outbound"]["items"] == ["pkg.dependency"]
    assert full_module["dependencies_outbound"]["total"] == 2
    assert full_module["dependencies_outbound"]["truncated"] is True


def test_module_context_exposes_new_live_module_before_full_report(
    tmp_path, monkeypatch
):
    report = tmp_path / "graph.json"
    report.write_text(
        json.dumps({"modules": {"pkg.old": {}}, "module_dependency_matrix": {}}),
        encoding="utf-8",
    )

    class Registry:
        def get_module_id(self, module):
            return {"pkg.new": "9/1"}.get(module)

    class Graph:
        hard_edges = {
            "pkg.caller": {"pkg.new"},
            "pkg.new": {"pkg.dependency"},
        }
        soft_edges = {"pkg.new": {"pkg.optional"}}

    class State:
        modules = {"pkg.new": object()}
        artifacts = {}
        dependency_graph = Graph()

    class Engine:
        state = State()
        registry = Registry()

    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: Engine())
    monkeypatch.setattr(
        mcp_server, "_get_canonical_report", lambda _root, _name: report
    )

    result = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(tmp_path), module_name="pkg.new"
        )
    )

    assert result["module"] == "pkg.new"
    assert result["metrics"] == {
        "module_idx": "9/1",
        "fan_in": 1,
        "fan_out": 2,
        "visibility": "unknown",
        "metrics_state": "deferred",
    }
    assert result["metrics_source"] == "deferred_until_full_analysis"
    assert result["dependency_data_source"] == "live_canonical_graph"
    assert result["dependencies_inbound_who_calls_me"] == {
        "total": 1,
        "truncated": False,
    }
    assert result["dependencies_outbound_who_i_call"] == {
        "total": 2,
        "truncated": False,
    }

    full = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(tmp_path),
            module_name="pkg.new",
            max_items=1,
            compact=False,
            fields=[
                "dependencies_inbound_who_calls_me",
                "dependencies_outbound_who_i_call",
            ],
        )
    )
    assert set(full["dependencies_inbound_who_calls_me"]["items"]) == {
        "pkg.caller"
    }
    assert full["dependencies_inbound_who_calls_me"]["total"] == 1
    assert full["dependencies_inbound_who_calls_me"]["truncated"] is False
    assert len(full["dependencies_outbound_who_i_call"]["items"]) == 1
    assert full["dependencies_outbound_who_i_call"]["total"] == 2
    assert full["dependencies_outbound_who_i_call"]["truncated"] is True

    invalid = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(tmp_path),
            module_name="pkg.new",
            fields=["unknown_field"],
        )
    )
    assert invalid["error"] == "Unsupported fields for get_module_context"
    assert invalid["unknown_fields"] == ["unknown_field"]


@pytest.mark.parametrize(
    "query",
    ["contextor.core.reporting_engine", "contextor/core/reporting_engine"],
)
def test_layer_isolation_addresses_nested_dotted_and_path_layers(
    tmp_path, monkeypatch, query
):
    report = tmp_path / "nested_graph.json"
    report.write_text(
        json.dumps(
            {
                "module_count": 2,
                "modules": {},
                "module_dependency_matrix": {},
                "shared_usage_clusters": [],
                "dependency_type_breakdown": {"import": 1},
            }
        ),
        encoding="utf-8",
    )
    requested = []

    def canonical(_root, filename):
        requested.append(filename)
        return report if filename.endswith("_reporting_engine_graph_analytics.json") else None

    monkeypatch.setattr(mcp_server, "_get_canonical_report", canonical)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: ({}, {}, {}, {}),
    )

    result = json.loads(
        mcp_server.get_layer_isolation.fn(str(tmp_path), query)
    )

    assert requested == [
        f"{tmp_path.name}_reporting_engine_graph_analytics.json"
    ]
    assert result["layer"] == "contextor.core.reporting_engine"
    assert result["report_layer"] == "reporting_engine"
    assert result["module_count"] == 2


def test_layer_isolation_reads_report_from_shared_output_dir(tmp_path, monkeypatch):
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    reports = tmp_path / "shared_reports"
    reports.mkdir()
    report = reports / "sample_repo_package_graph_analytics.json"
    report.write_text(
        json.dumps(
            {
                "module_count": 1,
                "modules": {},
                "module_dependency_matrix": {},
                "shared_usage_clusters": [],
                "dependency_type_breakdown": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mcp_server, "resolve_output_dir", lambda: reports)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: ({}, {}, {}, {}),
    )

    result = json.loads(
        mcp_server.get_layer_isolation.fn(str(repo), "package")
    )

    assert result["module_count"] == 1
    assert result["data_source"] == str(report)
    assert not (repo / "output").exists()


def test_layer_isolation_handles_missing_shared_output_dir(tmp_path, monkeypatch):
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    monkeypatch.setattr(
        mcp_server,
        "resolve_output_dir",
        lambda: tmp_path / "missing_reports",
    )

    result = mcp_server.get_layer_isolation.fn(str(repo), "package")

    assert result == (
        "Error: No layer report found for 'package' and no global summary found."
    )


def test_symbol_implementation_previews_costs_and_fetches_complete_ast_symbols(
    tmp_path, monkeypatch
):
    source = tmp_path / "pkg" / "service.py"
    source.parent.mkdir()
    source.write_text(
        """def traced(value):
    return value


@traced
class Service:
    \"\"\"Service documentation.\"\"\"

    @staticmethod
    def save(value: str) -> str:
        \"\"\"Save one value.\"\"\"
        return value.upper()

    def remove(self, value: str) -> str:
        return value.lower()


def standalone(value: int) -> int:
    return value + 1
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)

    preview = json.loads(
        mcp_server.get_symbol_implementation.fn(
            repo_path=str(tmp_path),
            symbol="Service",
            file_paths=["pkg/service.py"],
            member_limit=1,
        )
    )

    assert preview["status"] == "resolved"
    assert preview["mode"] == "preview"
    assert "implementation" not in preview
    assert preview["methods"]["total"] == 2
    assert preview["methods"]["truncated"] is True
    assert preview["fetch_plans"]["implementation"]["bytes"] > 0
    assert preview["source_contract"]["no_partial_symbol_source"] is True

    fetched = json.loads(
        mcp_server.get_symbol_implementation.fn(
            repo_path=str(tmp_path),
            symbol="Service",
            file_paths=["pkg/service.py"],
            mode="fetch",
            include=["signature", "docstring", "methods"],
            methods=["save"],
        )
    )

    assert fetched["signature"] == "class Service"
    assert fetched["docstring"] == "Service documentation."
    assert fetched["methods"][0]["name"] == "save"
    assert fetched["methods"][0]["implementation"] == (
        "    @staticmethod\n"
        "    def save(value: str) -> str:\n"
        "        \"\"\"Save one value.\"\"\"\n"
        "        return value.upper()\n"
    )
    assert "remove" not in fetched["methods"][0]["implementation"]


def test_symbol_implementation_refuses_ambiguous_source_without_guessing(
    tmp_path, monkeypatch
):
    first = tmp_path / "one.py"
    second = tmp_path / "two.py"
    first.write_text("def same():\n    return 1\n", encoding="utf-8")
    second.write_text("def same():\n    return 2\n", encoding="utf-8")
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)

    result = json.loads(
        mcp_server.get_symbol_implementation.fn(
            repo_path=str(tmp_path),
            symbol="same",
            file_paths=["one.py", "two.py"],
        )
    )

    assert result["status"] == "ambiguous"
    assert result["candidate_count"] == 2
    assert "implementation" not in result


def test_symbol_implementation_uses_contextor_source_reader_for_utf8_bom(
    tmp_path, monkeypatch
):
    source = tmp_path / "bom.py"
    source.write_bytes(b"\xef\xbb\xbfdef readable():\n    return 1\n")
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)

    result = json.loads(
        mcp_server.get_symbol_implementation.fn(
            repo_path=str(tmp_path),
            symbol="readable",
            file_paths=["bom.py"],
        )
    )

    assert result["status"] == "resolved"
    assert result["resolution"]["symbol"] == "readable"


def test_project_architecture_and_report_diff_offer_optional_bounds(
    tmp_path, monkeypatch
):
    summary_path = tmp_path / "summary.json"
    diff_path = tmp_path / "diff.json"
    summary_path.write_text(json.dumps({
        "action_items": ["a", "b"],
        "layer_index": [{"layer": "a"}, {"layer": "b"}],
        "top_hotspots": [{"module": "a"}, {"module": "b"}],
        "debt_summary": {"total_score": 1},
        "metrics": {"nodes": 2},
    }), encoding="utf-8")
    diff_path.write_text(json.dumps({
        "classification": "REGRESSION",
        "report_diff": {
            "metrics": {}, "debt": {}, "is_empty": False,
            "layers": {"a": {"module_count": {}}, "b": {"module_count": {}}},
        },
    }), encoding="utf-8")

    def canonical(_root, filename):
        if filename.endswith("_summary.json"):
            return summary_path
        if filename.endswith("_report_diff.json"):
            return diff_path
        return None

    monkeypatch.setattr(mcp_server, "_get_canonical_report", canonical)

    architecture = json.loads(mcp_server.get_project_architecture.fn(
        repo_path=str(tmp_path), max_items=1, compact=False,
        fields=["action_items", "top_global_hotspots"],
    ))
    assert architecture["action_items"] == {
        "items": ["a"], "total": 2, "truncated": True,
    }
    assert architecture["top_global_hotspots"]["total"] == 2

    diff = json.loads(mcp_server.get_report_diff.fn(
        repo_path=str(tmp_path), max_items=1, compact=False,
        fields=["report_diff"],
    ))
    layers = diff["report_diff"]["layers"]
    assert list(layers["items"]) == ["a"]
    assert layers["total"] == 2
    assert layers["truncated"] is True

    all_layers = json.loads(mcp_server.get_report_diff.fn(
        repo_path=str(tmp_path), max_items=None, compact=False,
        fields=["report_diff"],
    ))["report_diff"]["layers"]
    assert set(all_layers["items"]) == {"a", "b"}
    assert all_layers["truncated"] is False


def test_test_reachability_finds_direct_alias_and_reexport_paths():
    hard_edges = {
        "tests.test_direct": {"pkg.target"},
        "tests.test_alias": {"pkg.public_api"},
        "pkg.public_api": {"pkg.target"},
        "tests.test_indirect": {"pkg.facade"},
        "pkg.facade": {"pkg.public_api"},
    }

    result = mcp_server._static_test_reachability(
        "pkg.target",
        hard_edges,
        {},
        {"tests.test_direct", "tests.test_alias", "tests.test_indirect"},
        {
            "tests.test_direct": "1/1",
            "tests.test_alias": "2/1",
            "tests.test_indirect": "3/1",
        },
    )

    by_module = {item["module"]: item for item in result}
    assert by_module["tests.test_direct"]["distance"] == 1
    assert by_module["tests.test_alias"]["evidence_path"] == [
        "tests.test_alias",
        "pkg.public_api",
        "pkg.target",
    ]
    assert by_module["tests.test_indirect"]["distance"] == 3
    assert all(
        item["evidence_scope"] == "static_dependency_reachability"
        for item in result
    )


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
            repo_path=str(tmp_path), artifact_name="target", max_items=0
        )
    )

    assert result["artifact_id"] == "A1/1"
    assert result["definer"] == "pkg.module"
    assert result["consumers"] == {"total": 1, "truncated": True}
    assert result["evidence_scope"] == "direct_static_artifact_consumption"

    full = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(tmp_path),
            artifact_name="target",
            compact=False,
            fields=["consumers"],
        )
    )
    assert full == {
        "consumers": {
            "items": ["tests.test_module"],
            "total": 1,
            "truncated": False,
        }
    }
