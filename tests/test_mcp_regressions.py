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
        lambda _root, *args, **kwargs: client,
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
        lambda _root, *args, **kwargs: Client(),
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
        "fan_in": 1,
        "fan_out": 1,
    }
    assert result["metrics_source"] == "deferred_topology_analytics"
    assert result["degree_metrics_source"] == "live_canonical_graph"
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


def test_file_edit_context_minimal_mode_and_target_resolution(tmp_path, monkeypatch):
    root = tmp_path
    pkg_file = root / "pkg" / "module.py"
    pkg_file.parent.mkdir(parents=True)
    pkg_file.write_text("def hello(): pass\n", encoding="utf-8")

    from contextor.core.domain.graph import ProjectGraph

    mock_graph = ProjectGraph(
        hard_edges={"consumer.mod": {"pkg.module"}, "tests.test_pkg": {"consumer.mod"}},
        soft_edges={},
    )
    engine = SimpleNamespace(
        state=SimpleNamespace(
            modules={"pkg.module": SimpleNamespace(layer="core")},
            artifacts={"pkg.module": {"own_symbols": ["hello"]}},
            dependency_graph=mock_graph,
            revision=42,
            topology_metrics_state="fresh",
            topology_analytics={"module_risk": {"pkg.module": 0.15}},
            cached_analytics_state="fresh",
            cached_analytics={"module_layers": {"pkg.module": "core"}},
        )
    )
    mcp_server._live_engine_revisions[str(root)] = 42
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.module": "10/1", "consumer.mod": "20/1", "tests.test_pkg": "30/1"},
            {"10/1": "pkg.module", "20/1": "consumer.mod", "30/1": "tests.test_pkg"},
            {"pkg.module::hello": "A1/1"},
            {"A1/1": "pkg.module::hello"},
        ),
    )

    # 1. Legacy call (mode=None) keeps exact legacy contract
    legacy_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            file_path="pkg/module.py",
        )
    )
    assert "public_api" in legacy_res
    assert "imports" in legacy_res
    assert "consumers" in legacy_res
    assert "dependency_data_source" in legacy_res
    assert "scope_hint" not in legacy_res
    assert "state_certainty" not in legacy_res

    # 2. Minimal mode via relative path (fresh topology & cached analytics)
    min_rel = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg/module.py",
            mode="minimal",
        )
    )
    assert min_rel["resolved_as"] == "module"
    assert min_rel["module"] == "pkg.module"
    assert min_rel["module_id"] == "10/1"
    assert min_rel["live_revision"] == 42
    assert min_rel["layer"] == "core"
    assert min_rel["risk_score"] == 0.15
    assert min_rel["consumers"]["direct_count"] == 1
    assert min_rel["consumers"]["transitive_count"] == 2
    assert min_rel["consumers"]["sample"] == ["consumer.mod"]
    assert min_rel["consumers"]["truncated"] is False
    assert min_rel["tests_covering"]["count"] == 1
    assert min_rel["tests_covering"]["sample"] == ["tests.test_pkg"]
    assert min_rel["warnings"] == []
    assert "scope_hint" not in min_rel
    assert "state_certainty" not in min_rel

    # 3. Minimal mode via dotted module name
    min_dotted = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="minimal",
        )
    )
    assert min_dotted["module"] == "pkg.module"
    assert min_dotted["resolved_as"] == "module"

    # 4. Minimal mode via module ID
    min_id = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="10/1",
            mode="minimal",
        )
    )
    assert min_id["module"] == "pkg.module"
    assert min_id["resolved_as"] == "module"

    # 5. Minimal mode via absolute path
    min_abs = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target=str(pkg_file),
            mode="minimal",
        )
    )
    assert min_abs["module"] == "pkg.module"
    assert min_abs["resolved_as"] == "module"

    # 6. Artifact input returns structured diagnostic
    art_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module::hello",
            mode="minimal",
        )
    )
    assert art_res["resolved_as"] == "artifact"
    assert art_res["artifact"] == "pkg.module::hello"
    assert art_res["artifact_id"] == "A1/1"
    assert art_res["definer_module"] == "pkg.module"
    assert art_res["suggested_next_tool"] == "get_artifact_blast_radius"

    # 7. Conflicting target and file_path returns clear validation error when resolving to different targets
    conflict_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            file_path="pkg/module.py",
            target="consumer.mod",
            mode="minimal",
        )
    )
    assert "error" in conflict_res
    assert "Conflicting" in conflict_res["error"]

    # 8. Equivalent target and file_path in different representations do NOT conflict
    equiv_res1 = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            file_path="pkg/module.py",
            target="pkg.module",
            mode="minimal",
        )
    )
    assert equiv_res1.get("resolved_as") == "module"
    assert equiv_res1["module"] == "pkg.module"

    equiv_res2 = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            file_path=str(pkg_file),
            target="10/1",
            mode="minimal",
        )
    )
    assert equiv_res2.get("resolved_as") == "module"
    assert equiv_res2["module"] == "pkg.module"

    # 9. Unsupported mode is rejected explicitly
    unsupported_mode_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="invalid_unsupported_mode",
        )
    )
    assert "error" in unsupported_mode_res
    assert "Unsupported mode" in unsupported_mode_res["error"]

    # 10. Sample bounding and truncation semantics
    bounded_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="minimal",
            max_items=0,
        )
    )
    assert bounded_res["consumers"]["direct_count"] == 1
    assert bounded_res["consumers"]["sample"] == []
    assert bounded_res["consumers"]["truncated"] is True
    assert bounded_res["tests_covering"]["count"] == 1
    assert bounded_res["tests_covering"]["sample"] == []
    assert bounded_res["tests_covering"]["truncated"] is True

    # 11. Freshness guards on module_risk: deferred -> null, stale -> null, fresh+missing -> null with warning
    engine.state.topology_metrics_state = "deferred"
    deferred_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="minimal",
        )
    )
    assert deferred_res["risk_score"] is None

    engine.state.topology_metrics_state = "stale"
    stale_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="minimal",
        )
    )
    assert stale_res["risk_score"] is None

    engine.state.topology_metrics_state = "fresh"
    engine.state.topology_analytics = {"module_risk": {}}
    missing_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="minimal",
        )
    )
    assert missing_res["risk_score"] is None
    assert any("Canonical module_risk not computed" in w for w in missing_res["warnings"])

    # 12. Freshness guards on layer: deferred -> unknown, stale -> unknown, fresh+missing -> unknown with warning
    engine.state.cached_analytics_state = "deferred"
    def_layer_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="minimal",
        )
    )
    assert def_layer_res["layer"] == "unknown"

    engine.state.cached_analytics_state = "stale"
    stale_layer_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="minimal",
        )
    )
    assert stale_layer_res["layer"] == "unknown"

    engine.state.cached_analytics_state = "fresh"
    engine.state.cached_analytics = {"module_layers": {}}
    missing_layer_res = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root),
            target="pkg.module",
            mode="minimal",
        )
    )
    assert missing_layer_res["layer"] == "unknown"
    assert any("Canonical module_layers entry not found" in w for w in missing_layer_res["warnings"])


def test_module_context_forgiving_input_and_artifact_redirect(tmp_path, monkeypatch):
    root = tmp_path
    from contextor.core.domain.graph import ProjectGraph

    mock_graph = ProjectGraph(
        hard_edges={"consumer.mod": {"pkg.module"}, "pkg.module": {"dep.mod"}},
        soft_edges={},
    )
    engine = SimpleNamespace(
        state=SimpleNamespace(
            modules={"pkg.module": SimpleNamespace(layer="core")},
            artifacts={"pkg.module": {"own_symbols": ["hello"]}},
            dependency_graph=mock_graph,
            revision=42,
            topology_metrics_state="fresh",
            topology_analytics={"module_risk": {"pkg.module": 0.15}, "pagerank": {"pkg.module": 0.1}, "betweenness": {}, "hub_scores": {}, "authority_scores": {}, "bridge_scores": {}},
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.module": "10/1", "consumer.mod": "20/1", "dep.mod": "30/1"},
            {"10/1": "pkg.module", "20/1": "consumer.mod", "30/1": "dep.mod"},
            {"pkg.module::hello": "A1/1"},
            {"A1/1": "pkg.module::hello"},
        ),
    )

    # 1. Legacy call via module_name
    legacy_res = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(root),
            module_name="pkg.module",
        )
    )
    assert legacy_res["module"] == "pkg.module"
    assert "metrics" in legacy_res

    # 2. Call via module alias
    alias_res = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(root),
            module="pkg.module",
        )
    )
    assert alias_res["module"] == "pkg.module"

    # 3. Call via module ID
    id_res = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(root),
            module="10/1",
        )
    )
    assert id_res["module"] == "pkg.module"

    # 4. Equivalent module_name and module
    equiv_res = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(root),
            module_name="pkg.module",
            module="10/1",
        )
    )
    assert equiv_res["module"] == "pkg.module"

    # 5. Conflicting module_name and module
    conflict_res = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(root),
            module_name="pkg.module",
            module="consumer.mod",
        )
    )
    assert "error" in conflict_res
    assert "Conflicting" in conflict_res["error"]

    # 6. Artifact passed to module tool -> structured redirect
    art_redirect = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(root),
            module="pkg.module::hello",
        )
    )
    assert art_redirect["resolved_as"] == "artifact"
    assert art_redirect["artifact"] == "pkg.module::hello"
    assert art_redirect["definer_module"] == "pkg.module"
    assert art_redirect["suggested_next_tool"] == "get_artifact_blast_radius"


def test_artifact_blast_radius_module_aware_diagnostic(tmp_path, monkeypatch):
    root = tmp_path
    engine = SimpleNamespace(
        state=SimpleNamespace(
            modules={"pkg.module": SimpleNamespace(layer="core")},
            artifacts={
                "pkg.module": {
                    "own_symbols": ["hello", "WorldClass", "WorldClass.analyze", "WorldClass._add_row", "WorldClass.__init__"],
                    "symbols": {
                        "functions": ["hello"],
                        "classes": ["WorldClass"],
                        "methods": ["WorldClass.analyze", "WorldClass._add_row", "WorldClass.__init__"],
                    },
                    "consumers": {"hello": {"consumers": ["consumer.mod"]}},
                }
            },
            dependency_graph=None,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.module": "10/1"},
            {"10/1": "pkg.module"},
            {
                "pkg.module::hello": "A1/1",
                "pkg.module::WorldClass": "A2/1",
                "pkg.module::WorldClass.analyze": "A3/1",
                "pkg.module::WorldClass._add_row": "A4/1",
                "pkg.module::WorldClass.__init__": "A5/1",
            },
            {
                "A1/1": "pkg.module::hello",
                "A2/1": "pkg.module::WorldClass",
                "A3/1": "pkg.module::WorldClass.analyze",
                "A4/1": "pkg.module::WorldClass._add_row",
                "A5/1": "pkg.module::WorldClass.__init__",
            },
        ),
    )

    # 7. Valid artifact unchanged
    valid_res = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.module::hello",
        )
    )
    assert valid_res["artifact"] == "pkg.module::hello"
    assert valid_res["definer"] == "pkg.module"

    # 8. Artifact ID unchanged
    id_res = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="A1/1",
        )
    )
    assert id_res["artifact_id"] == "A1/1"

    # 9. Module dotted name -> module diagnostic with public-first ranked candidates
    mod_diag = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.module",
        )
    )
    assert mod_diag["resolved_as"] == "module"
    assert mod_diag["module"] == "pkg.module"
    assert mod_diag["module_id"] == "10/1"
    assert mod_diag["suggested_next_tool"] == "get_module_context"
    assert mod_diag["artifact_candidates"]["total"] == 5
    assert len(mod_diag["artifact_candidates"]["items"]) == 5
    assert mod_diag["artifact_candidates"]["truncated"] is False

    # Verify public class & method precede dunder and private methods
    candidate_names = [item["artifact"] for item in mod_diag["artifact_candidates"]["items"]]
    assert candidate_names == [
        "pkg.module::WorldClass",
        "pkg.module::hello",
        "pkg.module::WorldClass.analyze",
        "pkg.module::WorldClass.__init__",
        "pkg.module::WorldClass._add_row",
    ]

    # 10. Module ID -> module diagnostic with candidates
    mod_id_diag = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="10/1",
        )
    )
    assert mod_id_diag["resolved_as"] == "module"
    assert mod_id_diag["module"] == "pkg.module"

    # 11. Bounded artifact candidates
    bounded_diag = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.module",
            max_items=2,
        )
    )
    assert bounded_diag["artifact_candidates"]["total"] == 5
    assert len(bounded_diag["artifact_candidates"]["items"]) == 2
    assert bounded_diag["artifact_candidates"]["truncated"] is True
    assert [item["artifact"] for item in bounded_diag["artifact_candidates"]["items"]] == [
        "pkg.module::WorldClass",
        "pkg.module::hello",
    ]

    # 12. Truly unknown target -> not found
    unknown_res = mcp_server.get_artifact_blast_radius.fn(
        repo_path=str(root),
        artifact_name="nonexistent_completely_unknown",
    )
    assert "not found" in str(unknown_res)


def test_file_edit_context_live_revision_lifecycle(tmp_path, monkeypatch):
    root1 = tmp_path / "repo1"
    root2 = tmp_path / "repo2"
    root1.mkdir(parents=True)
    root2.mkdir(parents=True)

    from contextor.core.domain.graph import ProjectGraph
    from contextor.core.live_state.store import LiveStateMetadata

    mock_graph = ProjectGraph(hard_edges={}, soft_edges={})
    engine1 = SimpleNamespace(
        state=SimpleNamespace(
            modules={"r1.mod": SimpleNamespace(layer="core")},
            artifacts={"r1.mod": {"own_symbols": []}},
            dependency_graph=mock_graph,
            topology_metrics_state="fresh",
            topology_analytics={"module_risk": {"r1.mod": 0.1}},
            cached_analytics_state="fresh",
            cached_analytics={"module_layers": {"r1.mod": "core"}},
        ),
        state_manager=SimpleNamespace(state_id="state1"),
    )
    engine2 = SimpleNamespace(
        state=SimpleNamespace(
            modules={"r2.mod": SimpleNamespace(layer="ui")},
            artifacts={"r2.mod": {"own_symbols": []}},
            dependency_graph=mock_graph,
            topology_metrics_state="fresh",
            topology_analytics={"module_risk": {"r2.mod": 0.2}},
            cached_analytics_state="fresh",
            cached_analytics={"module_layers": {"r2.mod": "ui"}},
        ),
        state_manager=SimpleNamespace(state_id="state2"),
    )

    import contextor.core.live_state as core_live_state
    import contextor.core.repository_identity as core_repo_id
    import contextor.core.analysis.state_manager as core_state_mgr

    # Clear revision dictionary
    mcp_server._live_engine_revisions.clear()
    mcp_server._live_engines.clear()

    # 1. Hydrated metadata revision -> minimal pre-edit returns exact persisted revision
    monkeypatch.setattr(core_live_state, "connect", lambda _r: None)
    monkeypatch.setattr(core_repo_id, "read_repository_identity", lambda r: SimpleNamespace(repo_id=f"id_{r.name}", root_path=str(r)))
    monkeypatch.setattr(core_live_state, "migrate_legacy_snapshot", lambda r: str(r / ".contextor"))
    monkeypatch.setattr(core_live_state, "read_metadata", lambda _c: LiveStateMetadata(revision=366, state_id="s366"))
    monkeypatch.setattr(core_state_mgr, "load_engine_state", lambda _c, _sid, **_kw: engine1.state)
    monkeypatch.setattr(mcp_server, "_read_registries", lambda _r: ({"r1.mod": "1/1"}, {"1/1": "r1.mod"}, {}, {}))

    res1 = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root1),
            target="r1.mod",
            mode="minimal",
        )
    )
    assert res1["live_revision"] == 366
    assert mcp_server._live_engine_revisions[str(root1)] == 366

    # 2. No metadata / revision -> null
    mcp_server._live_engine_revisions.clear()
    mcp_server._live_engines.clear()
    monkeypatch.setattr(core_live_state, "read_metadata", lambda _c: None)
    res_no_meta = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root1),
            target="r1.mod",
            mode="minimal",
        )
    )
    assert res_no_meta["live_revision"] is None

    # 3. Active / newer revision in _live_engine_revisions -> exact newer revision
    mcp_server._live_engine_revisions[str(root1)] = 367
    res_active = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root1),
            target="r1.mod",
            mode="minimal",
        )
    )
    assert res_active["live_revision"] == 367

    # 4. Hydration does not increment revision
    assert mcp_server._live_engine_revisions[str(root1)] == 367

    # 5. Two repo roots retain independent revision values
    monkeypatch.setattr(core_live_state, "read_metadata", lambda c: LiveStateMetadata(revision=500, state_id="s500") if "repo2" in str(c) else LiveStateMetadata(revision=366, state_id="s366"))
    monkeypatch.setattr(core_state_mgr, "load_engine_state", lambda c, _sid, **_kw: engine2.state if "repo2" in str(c) else engine1.state)
    monkeypatch.setattr(mcp_server, "_read_registries", lambda r: ({"r2.mod": "2/1"}, {"2/1": "r2.mod"}, {}, {}) if "repo2" in str(r) else ({"r1.mod": "1/1"}, {"1/1": "r1.mod"}, {}, {}))

    mcp_server._live_engine_revisions.clear()
    mcp_server._live_engines.clear()

    res_r1 = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root1), target="r1.mod", mode="minimal"))
    res_r2 = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root2), target="r2.mod", mode="minimal"))
    assert res_r1["live_revision"] == 366
    assert res_r2["live_revision"] == 500
    assert mcp_server._live_engine_revisions[str(root1)] == 366
    assert mcp_server._live_engine_revisions[str(root2)] == 500

    # 6. Rejected / invalid hydration does not publish invalid revision
    mcp_server._live_engine_revisions[str(root1)] = 999
    monkeypatch.setattr(core_state_mgr, "load_engine_state", lambda _c, _sid, **_kw: None)
    mcp_server._live_engines.clear()
    engine_rejected = mcp_server._get_or_init_engine(root1)
    assert engine_rejected is None
    assert str(root1) not in mcp_server._live_engine_revisions

    # 7. Legacy get_file_edit_context contract unchanged
    monkeypatch.setattr(core_state_mgr, "load_engine_state", lambda _c, _sid, **_kw: engine1.state)
    mcp_server._live_engine_revisions[str(root1)] = 366
    legacy_res = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root1), file_path="r1/mod.py"))
    assert "public_api" in legacy_res
    assert "live_revision" not in legacy_res


def test_file_edit_context_layer_guard(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    from types import SimpleNamespace

    # Mock registries
    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.ui_mod": "1/1", "pkg.cli_mod": "2/1", "pkg.core_mod": "3/1"},
            {"1/1": "pkg.ui_mod", "2/1": "pkg.cli_mod", "3/1": "pkg.core_mod"},
            {},
            {},
        ),
    )

    # 1. Fresh cached analytics + module with no violations
    engine_fresh_clean = SimpleNamespace(
        state=SimpleNamespace(
            modules={
                "pkg.ui_mod": SimpleNamespace(layer="ui"),
                "pkg.cli_mod": SimpleNamespace(layer="cli"),
                "pkg.core_mod": SimpleNamespace(layer="adapter"),
            },
            cached_analytics={
                "module_layers": {"pkg.ui_mod": "ui", "pkg.cli_mod": "cli", "pkg.core_mod": "adapter"},
                "layer_violations": [],
            },
            cached_analytics_state="fresh",
            topology_analytics={},
            topology_metrics_state="fresh",
            dependency_graph=None,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_fresh_clean)

    res_clean_ui = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
    assert res_clean_ui["layer_guard"]["available"] is True
    assert res_clean_ui["layer_guard"]["outbound_rules_defined"] is True
    assert "rules_defined" not in res_clean_ui["layer_guard"]
    assert res_clean_ui["layer_guard"]["forbidden_outbound_layers"] == ["cli"]
    assert res_clean_ui["layer_guard"]["forbidden_outbound_prefixes"] == ["core.internal"]
    assert res_clean_ui["layer_guard"]["outbound_violation_count"] == 0
    assert res_clean_ui["layer_guard"]["inbound_violation_count"] == 0
    assert res_clean_ui["layer_guard"]["violations"]["total"] == 0
    assert res_clean_ui["layer_guard"]["violations"]["items"] == []
    assert res_clean_ui["layer_guard"]["suggested_next_tool"] == "get_layer_isolation"

    # 2. Module without rules defined (adapter)
    res_clean_core = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.core_mod", mode="minimal"))
    assert res_clean_core["layer_guard"]["available"] is True
    assert res_clean_core["layer_guard"]["outbound_rules_defined"] is False
    assert "rules_defined" not in res_clean_core["layer_guard"]
    assert "forbidden_outbound_layers" not in res_clean_core["layer_guard"]
    assert res_clean_core["layer_guard"]["outbound_violation_count"] == 0
    assert res_clean_core["layer_guard"]["inbound_violation_count"] == 0
    assert "suggested_next_tool" not in res_clean_core["layer_guard"]

    # 3. Fresh + Outbound & Inbound violations
    sample_v = [
        {"kind": "LAYER", "message": "ui -> cli dependency: pkg.ui_mod -> pkg.cli_mod", "nodes": ["pkg.ui_mod", "pkg.cli_mod"]},
        {"kind": "FORBIDDEN_DEPENDENCY", "message": "ui accessing internal core: pkg.ui_mod -> core.internal.x", "nodes": ["pkg.ui_mod", "core.internal.x"]},
    ]
    engine_with_v = SimpleNamespace(
        state=SimpleNamespace(
            modules=engine_fresh_clean.state.modules,
            cached_analytics={
                "module_layers": {"pkg.ui_mod": "ui", "pkg.cli_mod": "cli", "pkg.core_mod": "adapter"},
                "layer_violations": sample_v,
            },
            cached_analytics_state="fresh",
            topology_analytics={},
            topology_metrics_state="fresh",
            dependency_graph=None,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_with_v)

    # For pkg.ui_mod (source of 2 violations -> 2 outbound)
    res_ui_v = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
    assert res_ui_v["layer_guard"]["outbound_violation_count"] == 2
    assert res_ui_v["layer_guard"]["inbound_violation_count"] == 0
    assert res_ui_v["layer_guard"]["violations"]["total"] == 2
    assert len(res_ui_v["layer_guard"]["violations"]["items"]) == 2
    assert res_ui_v["layer_guard"]["violations"]["items"][0]["direction"] == "outbound"
    assert res_ui_v["layer_guard"]["violations"]["items"][0]["source_module"] == "pkg.ui_mod"
    assert res_ui_v["layer_guard"]["violations"]["items"][0]["target_module"] == "pkg.cli_mod"
    assert res_ui_v["layer_guard"]["suggested_next_tool"] == "get_layer_isolation"

    # For pkg.cli_mod (target of 1 violation -> 1 inbound)
    res_cli_v = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.cli_mod", mode="minimal"))
    assert res_cli_v["layer_guard"]["outbound_violation_count"] == 0
    assert res_cli_v["layer_guard"]["inbound_violation_count"] == 1
    assert res_cli_v["layer_guard"]["violations"]["total"] == 1
    assert res_cli_v["layer_guard"]["violations"]["items"][0]["direction"] == "inbound"
    assert res_cli_v["layer_guard"]["suggested_next_tool"] == "get_layer_isolation"

    # 4. Critical case: outbound_rules_defined == False + inbound_violation_count > 0 -> suggested_next_tool present
    sample_inbound_core_v = [
        {"kind": "FORBIDDEN_DEPENDENCY", "message": "ui accessing internal core: pkg.ui_mod -> pkg.core_mod", "nodes": ["pkg.ui_mod", "pkg.core_mod"]},
    ]
    engine_inbound_core = SimpleNamespace(
        state=SimpleNamespace(
            modules=engine_fresh_clean.state.modules,
            cached_analytics={
                "module_layers": {"pkg.ui_mod": "ui", "pkg.cli_mod": "cli", "pkg.core_mod": "adapter"},
                "layer_violations": sample_inbound_core_v,
            },
            cached_analytics_state="fresh",
            topology_analytics={},
            topology_metrics_state="fresh",
            dependency_graph=None,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_inbound_core)
    res_inbound_core = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.core_mod", mode="minimal"))
    assert res_inbound_core["layer_guard"]["outbound_rules_defined"] is False
    assert res_inbound_core["layer_guard"]["outbound_violation_count"] == 0
    assert res_inbound_core["layer_guard"]["inbound_violation_count"] == 1
    assert res_inbound_core["layer_guard"]["suggested_next_tool"] == "get_layer_isolation"

    # 5. Deferred cached analytics -> layer_guard unavailable
    engine_deferred = SimpleNamespace(
        state=SimpleNamespace(
            modules=engine_fresh_clean.state.modules,
            cached_analytics={},
            cached_analytics_state="deferred",
            topology_analytics={},
            topology_metrics_state="deferred",
            dependency_graph=None,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_deferred)
    res_deferred = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
    assert res_deferred["layer_guard"]["available"] is False
    assert "deferred" in res_deferred["layer_guard"]["reason"]

    # 6. Stale cached analytics -> layer_guard unavailable
    engine_stale = SimpleNamespace(
        state=SimpleNamespace(
            modules=engine_fresh_clean.state.modules,
            cached_analytics={"layer_violations": sample_v},
            cached_analytics_state="stale",
            topology_analytics={},
            topology_metrics_state="stale",
            dependency_graph=None,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_stale)
    res_stale = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
    assert res_stale["layer_guard"]["available"] is False
    assert "stale" in res_stale["layer_guard"]["reason"]


def test_artifact_blast_radius_architecture_projection(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    from types import SimpleNamespace

    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {
                "pkg.core": "1/1",
                "pkg.same_layer": "2/1",
                "pkg.cross_ui": "3/1",
                "pkg.cross_cli": "4/1",
                "tests.test_pkg": "5/1",
                "pkg.unclassified": "6/1",
            },
            {
                "1/1": "pkg.core",
                "2/1": "pkg.same_layer",
                "3/1": "pkg.cross_ui",
                "4/1": "pkg.cross_cli",
                "5/1": "tests.test_pkg",
                "6/1": "pkg.unclassified",
            },
            {
                "pkg.core::func_clean": "A1/1",
                "pkg.core::func_mixed": "A2/1",
                "pkg.core::func_duplicate": "A3/1",
                "pkg.core::func_test_only": "A4/1",
            },
            {
                "A1/1": "pkg.core::func_clean",
                "A2/1": "pkg.core::func_mixed",
                "A3/1": "pkg.core::func_duplicate",
                "A4/1": "pkg.core::func_test_only",
            },
        ),
    )

    # 1. Fresh state with mixed consumers
    engine_fresh = SimpleNamespace(
        state=SimpleNamespace(
            artifacts={
                "pkg.core": {
                    "own_symbols": ["func_clean", "func_mixed", "func_duplicate", "func_test_only"],
                    "symbols": {"functions": ["func_clean", "func_mixed", "func_duplicate", "func_test_only"]},
                    "consumers": {
                        "func_clean": {
                            "consumers": ["pkg.core", "pkg.same_layer"],
                        },
                        "func_mixed": {
                            "consumers": [
                                "pkg.core",             # same-module (layer: core)
                                "pkg.same_layer",       # same-layer (layer: core)
                                "pkg.cross_ui",         # cross-layer (layer: ui)
                                "pkg.cross_cli",        # cross-layer (layer: cli)
                                "tests.test_pkg",       # test consumer (layer: tests)
                                "pkg.unclassified",     # unknown layer
                            ],
                        },
                        "func_duplicate": {
                            "consumers": [
                                "pkg.cross_ui",
                                "pkg.cross_ui",         # duplicated channel
                                "tests.test_pkg",
                                "tests.test_pkg",       # duplicated test channel
                                "pkg.core",
                            ],
                        },
                        "func_test_only": {
                            "consumers": ["tests.test_pkg"],
                        },
                    },
                }
            },
            cached_analytics={
                "module_layers": {
                    "pkg.core": "core",
                    "pkg.same_layer": "core",
                    "pkg.cross_ui": "ui",
                    "pkg.cross_cli": "cli",
                    "tests.test_pkg": "tests",
                    # pkg.unclassified omitted
                },
            },
            cached_analytics_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_fresh)

    # A. Clean artifact: same-module & same-layer only
    res_clean = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.core::func_clean",
            compact=False,
        )
    )
    arch_clean = res_clean["architecture"]
    assert arch_clean["available"] is True
    assert arch_clean["definer_layer"] == "core"
    assert arch_clean["consumer_layers"] == ["core"]
    assert arch_clean["same_module_consumer_count"] == 1
    assert arch_clean["same_layer_consumer_count"] == 1
    assert arch_clean["cross_layer_consumer_count"] == 0
    assert arch_clean["test_consumer_count"] == 0
    assert arch_clean["cross_layer_consumers"] is False
    assert "unknown_layer_consumer_count" not in arch_clean
    # Invariant: 1 + 1 + 0 + 0 + 0 == 2
    assert (
        arch_clean["same_module_consumer_count"]
        + arch_clean["same_layer_consumer_count"]
        + arch_clean["cross_layer_consumer_count"]
        + arch_clean["test_consumer_count"]
        + arch_clean.get("unknown_layer_consumer_count", 0)
    ) == res_clean["consumers"]["total"]

    # B. Mixed artifact: same-mod, same-layer, cross-layer, test, unknown
    res_mixed = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.core::func_mixed",
            compact=False,
        )
    )
    arch_mixed = res_mixed["architecture"]
    assert arch_mixed["available"] is True
    assert arch_mixed["definer_layer"] == "core"
    assert arch_mixed["consumer_layers"] == ["cli", "core", "tests", "ui"]
    assert arch_mixed["same_module_consumer_count"] == 1
    assert arch_mixed["same_layer_consumer_count"] == 1
    assert arch_mixed["cross_layer_consumer_count"] == 2
    assert arch_mixed["test_consumer_count"] == 1
    assert arch_mixed["cross_layer_consumers"] is True
    assert arch_mixed["unknown_layer_consumer_count"] == 1
    assert len(arch_mixed["cross_layer_sample"]["items"]) == 2
    # Ensure cross_layer_sample contains ONLY non-test modules
    assert all(it["layer"] != "tests" for it in arch_mixed["cross_layer_sample"]["items"])
    # Invariant: 1 + 1 + 2 + 1 + 1 == 6
    assert (
        arch_mixed["same_module_consumer_count"]
        + arch_mixed["same_layer_consumer_count"]
        + arch_mixed["cross_layer_consumer_count"]
        + arch_mixed["test_consumer_count"]
        + arch_mixed.get("unknown_layer_consumer_count", 0)
    ) == res_mixed["consumers"]["total"]

    # C. Test only artifact: test_consumer_count > 0, cross_layer_consumers is False
    res_test_only = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.core::func_test_only",
            compact=False,
        )
    )
    arch_test_only = res_test_only["architecture"]
    assert arch_test_only["same_module_consumer_count"] == 0
    assert arch_test_only["same_layer_consumer_count"] == 0
    assert arch_test_only["cross_layer_consumer_count"] == 0
    assert arch_test_only["test_consumer_count"] == 1
    assert arch_test_only["cross_layer_consumers"] is False
    assert "cross_layer_sample" not in arch_test_only

    # D. Duplicate consumers in channels -> counted exactly once
    res_dup = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.core::func_duplicate",
            compact=False,
        )
    )
    arch_dup = res_dup["architecture"]
    assert res_dup["consumers"]["total"] == 3  # pkg.core, pkg.cross_ui, tests.test_pkg (deduplicated)
    assert arch_dup["same_module_consumer_count"] == 1
    assert arch_dup["cross_layer_consumer_count"] == 1
    assert arch_dup["test_consumer_count"] == 1
    assert (
        arch_dup["same_module_consumer_count"]
        + arch_dup["same_layer_consumer_count"]
        + arch_dup["cross_layer_consumer_count"]
        + arch_dup["test_consumer_count"]
        + arch_dup.get("unknown_layer_consumer_count", 0)
    ) == 3

    # 2. Missing definer layer + known consumer layers
    engine_no_definer_layer = SimpleNamespace(
        state=SimpleNamespace(
            artifacts=engine_fresh.state.artifacts,
            cached_analytics={
                "module_layers": {
                    # pkg.core omitted!
                    "pkg.same_layer": "core",
                    "pkg.cross_ui": "ui",
                    "tests.test_pkg": "tests",
                },
            },
            cached_analytics_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_no_definer_layer)
    res_no_def = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.core::func_mixed",
            compact=False,
        )
    )
    arch_no_def = res_no_def["architecture"]
    assert arch_no_def["available"] is True
    assert arch_no_def["definer_layer"] is None
    assert arch_no_def["same_module_consumer_count"] == 1  # pkg.core == definer_module still counts as same_module!
    assert arch_no_def["test_consumer_count"] == 1         # tests.test_pkg (layer == "tests") counted as test!
    assert arch_no_def["same_layer_consumer_count"] == 0   # cannot be confirmed without definer layer
    assert arch_no_def["cross_layer_consumer_count"] == 0  # cannot be confirmed without definer layer
    assert arch_no_def["unknown_layer_consumer_count"] == 4 # remaining non-self, non-test consumers
    # Invariant: 1 + 0 + 0 + 1 + 4 == 6
    assert (
        arch_no_def["same_module_consumer_count"]
        + arch_no_def["same_layer_consumer_count"]
        + arch_no_def["cross_layer_consumer_count"]
        + arch_no_def["test_consumer_count"]
        + arch_no_def["unknown_layer_consumer_count"]
    ) == res_no_def["consumers"]["total"]

    # 3. Deferred / Stale cached analytics state -> available = False
    engine_deferred = SimpleNamespace(
        state=SimpleNamespace(
            artifacts=engine_fresh.state.artifacts,
            cached_analytics={},
            cached_analytics_state="deferred",
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_deferred)
    res_def = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.core::func_clean",
        )
    )
    assert res_def["architecture"]["available"] is False
    assert "deferred" in res_def["architecture"]["reason"]
    assert res_def["consumers"]["total"] == 2  # consumers contract remains fully functional


def test_artifact_blast_radius_downstream_module_reachability(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    from types import SimpleNamespace
    from contextor.core.domain.graph import ProjectGraph

    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {
                "pkg.definer": "1/1",
                "pkg.direct_a": "2/1",
                "pkg.downstream_b": "3/1",
                "pkg.downstream_c": "4/1",
                "tests.test_downstream": "5/1",
                "pkg.unclassified_downstream": "6/1",
                "pkg.zero_cons": "7/1",
            },
            {
                "1/1": "pkg.definer",
                "2/1": "pkg.direct_a",
                "3/1": "pkg.downstream_b",
                "4/1": "pkg.downstream_c",
                "5/1": "tests.test_downstream",
                "6/1": "pkg.unclassified_downstream",
                "7/1": "pkg.zero_cons",
            },
            {
                "pkg.definer::sym_zero": "A1/1",
                "pkg.definer::sym_chain": "A2/1",
                "pkg.definer::sym_self": "A3/1",
            },
            {
                "A1/1": "pkg.definer::sym_zero",
                "A2/1": "pkg.definer::sym_chain",
                "A3/1": "pkg.definer::sym_self",
            },
        ),
    )

    # Graph topology:
    # pkg.direct_a imports pkg.definer
    # pkg.downstream_b imports pkg.direct_a
    # pkg.downstream_c imports pkg.downstream_b (creates chain: definer <- direct_a <- downstream_b <- downstream_c)
    # tests.test_downstream imports pkg.downstream_b
    # pkg.unclassified_downstream imports pkg.downstream_c
    # Cycle: pkg.downstream_b imports pkg.downstream_c AND pkg.downstream_c imports pkg.downstream_b
    dep_graph = ProjectGraph(
        hard_edges={
            "pkg.direct_a": {"pkg.definer"},
            "pkg.downstream_b": {"pkg.direct_a", "pkg.downstream_c"},
            "pkg.downstream_c": {"pkg.downstream_b"},
            "tests.test_downstream": {"pkg.downstream_b"},
            "pkg.unclassified_downstream": {"pkg.downstream_c"},
            "pkg.definer": set(),
            "pkg.zero_cons": set(),
        },
        soft_edges={},
    )

    engine_fresh = SimpleNamespace(
        state=SimpleNamespace(
            artifacts={
                "pkg.definer": {
                    "own_symbols": ["sym_zero", "sym_chain", "sym_self"],
                    "symbols": {"functions": ["sym_zero", "sym_chain", "sym_self"]},
                    "consumers": {
                        "sym_zero": {"consumers": []},
                        "sym_chain": {"consumers": ["pkg.direct_a"]},
                        "sym_self": {"consumers": ["pkg.definer"]},
                    },
                }
            },
            cached_analytics={
                "module_layers": {
                    "pkg.definer": "core",
                    "pkg.direct_a": "adapter",
                    "pkg.downstream_b": "ui",
                    "pkg.downstream_c": "cli",
                    "tests.test_downstream": "tests",
                    # pkg.unclassified_downstream omitted
                },
            },
            cached_analytics_state="fresh",
            dependency_graph=dep_graph,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_fresh)

    # 1. Zero direct consumers -> downstream total = 0
    res_zero = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.definer::sym_zero",
            compact=False,
        )
    )
    reach_zero = res_zero["downstream_module_reachability"]
    assert reach_zero["available"] is True
    assert reach_zero["total_downstream_count"] == 0
    assert reach_zero["production_downstream_count"] == 0
    assert reach_zero["test_downstream_count"] == 0
    assert reach_zero["unknown_layer_downstream_count"] == 0

    # 2. Chain with cycle and layer classification:
    # Direct = {pkg.direct_a}
    # Downstream = {pkg.downstream_b, pkg.downstream_c, tests.test_downstream, pkg.unclassified_downstream} (total: 4)
    # Definer (pkg.definer) and direct (pkg.direct_a) are EXCLUDED from downstream
    res_chain = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.definer::sym_chain",
            compact=False,
        )
    )
    reach_chain = res_chain["downstream_module_reachability"]
    assert reach_chain["available"] is True
    assert reach_chain["total_downstream_count"] == 4
    assert reach_chain["layer_classification_available"] is True
    assert reach_chain["production_downstream_count"] == 2      # downstream_b (ui), downstream_c (cli)
    assert reach_chain["test_downstream_count"] == 1            # tests.test_downstream (tests)
    assert reach_chain["unknown_layer_downstream_count"] == 1   # pkg.unclassified_downstream
    assert reach_chain["production_downstream_sample"]["items"] == ["pkg.downstream_b", "pkg.downstream_c"]
    assert reach_chain["test_downstream_sample"]["items"] == ["tests.test_downstream"]

    # Invariant: production + test + unknown == total downstream
    assert (
        reach_chain["production_downstream_count"]
        + reach_chain["test_downstream_count"]
        + reach_chain["unknown_layer_downstream_count"]
    ) == reach_chain["total_downstream_count"]

    # Disjointness proof:
    direct_set = set(res_chain["consumers"]["items"])
    downstream_items = set(reach_chain["production_downstream_sample"]["items"]) | set(reach_chain["test_downstream_sample"]["items"])
    assert direct_set.isdisjoint(downstream_items)
    assert "pkg.definer" not in downstream_items

    # 3. Same-module direct consumer seed:
    # sym_self has direct = {pkg.definer}
    # Reverse reachability from pkg.definer reaches direct_a, downstream_b, downstream_c, test_downstream, unclassified_downstream
    # Downstream excludes pkg.definer -> total downstream = 5
    res_self = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.definer::sym_self",
            compact=False,
        )
    )
    reach_self = res_self["downstream_module_reachability"]
    assert reach_self["available"] is True
    assert reach_self["total_downstream_count"] == 5
    assert "pkg.definer" not in reach_self["production_downstream_sample"]["items"]

    # 4. Stale cached analytics:
    # Module reachability is still available because dependency_graph is present, but layer classification is unavailable
    engine_stale = SimpleNamespace(
        state=SimpleNamespace(
            artifacts=engine_fresh.state.artifacts,
            cached_analytics={"module_layers": {}},
            cached_analytics_state="stale",
            dependency_graph=dep_graph,
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_stale)
    res_stale = json.loads(
        mcp_server.get_artifact_blast_radius.fn(
            repo_path=str(root),
            artifact_name="pkg.definer::sym_chain",
            compact=False,
        )
    )
    reach_stale = res_stale["downstream_module_reachability"]
    assert reach_stale["available"] is True
    assert reach_stale["total_downstream_count"] == 4
    assert reach_stale["layer_classification_available"] is False
    assert "stale" in reach_stale["reason"]
    assert "production_downstream_count" not in reach_stale


def test_module_context_topology_provenance_and_freshness(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    from types import SimpleNamespace
    from contextor.core.domain.graph import ProjectGraph

    report = root / "graph.json"
    report.write_text(
        json.dumps({
            "modules": {
                "pkg.mod_a": {
                    "pagerank": 0.999,          # deliberately different from LIVE
                    "betweenness": 0.888,
                    "hub_score": 0.777,
                    "authority_score": 0.666,
                    "bridge_score": 0.555,
                    "risk_score": 0.444,
                    "layer": "saved_layer",
                },
                "pkg.mod_b": {
                    "pagerank": 0.111,
                },
            },
            "module_dependency_matrix": {},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(mcp_server, "_get_canonical_report", lambda _root, _name: report)

    monkeypatch.setattr(
        mcp_server,
        "_read_registries",
        lambda _root: (
            {"pkg.mod_a": "1/1", "pkg.mod_b": "2/1", "pkg.mod_c": "3/1"},
            {"1/1": "pkg.mod_a", "2/1": "pkg.mod_b", "3/1": "pkg.mod_c"},
            {},
            {},
        ),
    )

    dep_graph = ProjectGraph(
        hard_edges={
            "pkg.mod_a": {"pkg.mod_b"},
            "pkg.mod_c": {"pkg.mod_a"},
            "pkg.mod_b": set(),
        },
        soft_edges={},
    )

    # 1. Fresh state: LIVE topology overrides saved report
    engine_fresh = SimpleNamespace(
        state=SimpleNamespace(
            modules={"pkg.mod_a": object(), "pkg.mod_b": object(), "pkg.mod_c": object()},
            artifacts={},
            dependency_graph=dep_graph,
            topology_analytics={
                "pagerank": {"pkg.mod_a": 0.1234},
                "betweenness": {"pkg.mod_a": 0.2345},
                "hub_scores": {"pkg.mod_a": 0.3456},
                "authority_scores": {"pkg.mod_a": 0.4567},
                "bridge_scores": {"pkg.mod_a": 0.5678},
                "module_risk": {"pkg.mod_a": 0.6789},
                # pkg.mod_b partially present: only pagerank
                "pagerank": {"pkg.mod_a": 0.1234, "pkg.mod_b": 0.0555},
            },
            topology_metrics_state="fresh",
            cached_analytics={
                "module_layers": {"pkg.mod_a": "core"},
                "visibility": {"pkg.mod_a": "public"},
                "export_degree": {"pkg.mod_a": 5},
            },
            cached_analytics_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_fresh)

    # For pkg.mod_a: LIVE topology metrics override saved report
    res_a = json.loads(mcp_server.get_module_context.fn(repo_path=str(root), module_name="pkg.mod_a"))
    metrics_a = res_a["metrics"]
    assert metrics_a["fan_in"] == 1
    assert metrics_a["fan_out"] == 1
    assert metrics_a["pagerank"] == 0.1234      # LIVE, not saved 0.999!
    assert metrics_a["betweenness"] == 0.2345   # LIVE, not saved 0.888!
    assert metrics_a["hub_score"] == 0.3456     # LIVE, not saved 0.777!
    assert metrics_a["authority_score"] == 0.4567
    assert metrics_a["bridge_score"] == 0.5678
    assert metrics_a["risk_score"] == 0.6789
    assert metrics_a["layer"] == "core"
    assert res_a["metrics_source"] == "live_canonical_topology"
    assert res_a["degree_metrics_source"] == "live_canonical_graph"

    # For pkg.mod_c: Fresh state, but mod_c has no entries in topology_analytics -> NO 0.0 fake default
    res_c = json.loads(mcp_server.get_module_context.fn(repo_path=str(root), module_name="pkg.mod_c"))
    metrics_c = res_c["metrics"]
    assert metrics_c["fan_in"] == 0
    assert metrics_c["fan_out"] == 1
    assert "pagerank" not in metrics_c
    assert "betweenness" not in metrics_c
    assert "hub_score" not in metrics_c
    assert res_c["metrics_source"] == "live_canonical_graph"

    # 2. Stale state: NO saved report fallback even when saved_modules has pkg.mod_a
    engine_stale = SimpleNamespace(
        state=SimpleNamespace(
            modules=engine_fresh.state.modules,
            artifacts={},
            dependency_graph=dep_graph,
            topology_analytics=engine_fresh.state.topology_analytics,
            topology_metrics_state="stale",
            cached_analytics=engine_fresh.state.cached_analytics,
            cached_analytics_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_stale)
    res_stale = json.loads(mcp_server.get_module_context.fn(repo_path=str(root), module_name="pkg.mod_a"))
    metrics_stale = res_stale["metrics"]
    assert metrics_stale["fan_in"] == 1
    assert metrics_stale["fan_out"] == 1
    # Pagerank and betweenness from saved report MUST NOT be substituted!
    assert "pagerank" not in metrics_stale
    assert "betweenness" not in metrics_stale
    assert res_stale["metrics_source"] == "stale_topology_analytics"
    assert res_stale["degree_metrics_source"] == "live_canonical_graph"

    # 3. Deferred state: NO saved report fallback
    engine_deferred = SimpleNamespace(
        state=SimpleNamespace(
            modules=engine_fresh.state.modules,
            artifacts={},
            dependency_graph=dep_graph,
            topology_analytics={},
            topology_metrics_state="deferred",
            cached_analytics={},
            cached_analytics_state="deferred",
        )
    )
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: engine_deferred)
    res_def = json.loads(mcp_server.get_module_context.fn(repo_path=str(root), module_name="pkg.mod_a"))
    metrics_def = res_def["metrics"]
    assert metrics_def["fan_in"] == 1
    assert metrics_def["fan_out"] == 1
    assert "pagerank" not in metrics_def
    assert res_def["metrics_source"] == "deferred_topology_analytics"
    assert res_def["degree_metrics_source"] == "live_canonical_graph"

    # 4. Engine absent (report-only fallback) -> saved report behavior preserved
    monkeypatch.setattr(mcp_server, "_get_or_init_engine", lambda _root: None)
    res_report = json.loads(mcp_server.get_module_context.fn(repo_path=str(root), module_name="pkg.mod_a"))
    assert res_report["metrics"]["pagerank"] == 0.999
    assert res_report["metrics_source"] == "saved_graph_analytics"
    assert res_report["degree_metrics_source"] == "saved_graph_analytics"




