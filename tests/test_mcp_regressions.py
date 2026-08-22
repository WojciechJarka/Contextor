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
from contextor.mcp import analysis_jobs
from contextor.mcp import query_helpers
from contextor.mcp import report_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools import get_layer_isolation as get_layer_isolation_module
from contextor.mcp.tools import update_file as update_file_module
from contextor.mcp.tools.get_file_edit_context import _static_test_reachability
from contextor.mcp.tools import lookup_index_entries as lookup_index_entries_tool
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
        artifact_consumption={
            "pkg.module::api": {
                "consumers": ["tests.test_module"],
                "channels": {"tests.test_module": ["direct_calls"]},
            }
        },
        artifact_consumption_state="fresh",
        metrics={"pkg.module": {"layer": "domain", "hub_score": 0.4}},
        layer_information={
            "layer_index": [{"layer": "pkg", "module_count": 2}],
            "hotspots": [{"module": "pkg.module", "score": 0.7}],
            "debt": {"score": 3},
            "summary_data": {"action_items": ["review pkg.module"]},
        },
    )
    return SimpleNamespace(state=state)


def _patch_empty_registries(monkeypatch):
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: ({}, {}, {}, {}))


def test_canonical_empty_consumers_do_not_fall_back_to_legacy_artifact_state():
    state = RepositoryAnalysisState(
        artifacts={
            "provider": {
                "own_symbols": ["foo"],
                "symbols": {"functions": ["foo"]},
                "consumers": {"foo": {"consumers": ["stale.consumer"]}},
            }
        },
        artifact_consumption={"provider::foo": {"consumers": [], "channels": {}}},
        artifact_consumption_state="fresh",
    )

    assert query_helpers.canonical_symbol_consumers(state, "provider", "foo") == []


@pytest.mark.parametrize("freshness", ["stale", "deferred"])
def test_consumer_queries_fail_closed_when_artifact_consumption_is_not_fresh(
    tmp_path, monkeypatch, freshness
):
    state = RepositoryAnalysisState(
        artifacts={
            "provider": {
                "own_symbols": ["foo"],
                "symbols": {"functions": ["foo"]},
            }
        },
        artifact_consumption={"provider::foo": {"consumers": ["stale.consumer"]}},
        artifact_consumption_state=freshness,
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    _patch_empty_registries(monkeypatch)

    artifacts = mcp_server.get_artifacts_for_module.fn(
        str(tmp_path), "provider", include_consumers=True
    )
    lookup = mcp_server.lookup_artifact_by_symbol.fn(str(tmp_path), "foo")
    blast = mcp_server.get_artifact_blast_radius.fn(str(tmp_path), "provider::foo")

    assert "unavailable or stale" in artifacts
    assert "unavailable or stale" in lookup
    assert "unavailable or stale" in blast
    assert "stale.consumer" not in artifacts + lookup + blast


def test_own_symbols_excludes_legacy_category_symbols_from_artifact_queries(
    tmp_path, monkeypatch
):
    state = RepositoryAnalysisState(
        artifacts={
            "provider": {
                "own_symbols": ["foo"],
                "symbols": {"functions": ["foo", "legacy_old"]},
            }
        },
        artifact_consumption={"provider::foo": {"consumers": [], "channels": {}}},
        artifact_consumption_state="fresh",
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    _patch_empty_registries(monkeypatch)

    assert query_helpers.canonical_symbol_catalog(state.artifacts["provider"]) == {
        "foo": "function"
    }
    artifacts = mcp_server.get_artifacts_for_module.fn(str(tmp_path), "provider")
    lookup = mcp_server.lookup_artifact_by_symbol.fn(str(tmp_path), "legacy_old")
    blast = mcp_server.get_artifact_blast_radius.fn(str(tmp_path), "legacy_old")

    assert "legacy_old" not in artifacts
    assert "No current artifacts" in lookup
    assert "not found" in blast


def test_stale_layer_snapshot_is_not_presented_after_incremental_update(
    tmp_path, monkeypatch
):
    from contextor.core.domain.graph import ProjectGraph

    state = RepositoryAnalysisState(
        modules={
            "provider": SimpleNamespace(module_id="1/1", path="provider.py"),
            "quality.scenario": SimpleNamespace(module_id="2/1", path="quality/scenario.py"),
        },
        artifacts={"provider": {"own_symbols": []}},
        metrics={"provider": {"betweenness": 0.9, "hub_score": 0.8}},
        topology_analytics={"module_risk": {"provider": 0.95}},
        topology_metrics_state="stale",
        cached_analytics={
            "module_layers": {"provider": "core", "quality.scenario": "tests"}
        },
        cached_analytics_state="fresh",
        dependency_graph=ProjectGraph(
            hard_edges={"quality.scenario": {"provider"}, "provider": set()},
            soft_edges={},
        ),
        layer_information={
            "summary_data": {"action_items": ["old action"]},
            "layer_index": [{"layer": "legacy", "module_count": 99}],
            "hotspots": [{"module": "provider", "score": 0.99}],
            "debt": {"score": 99},
        },
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    _patch_empty_registries(monkeypatch)

    architecture = json.loads(
        mcp_server.get_project_architecture.fn(str(tmp_path), compact=False)
    )
    edit_context = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(tmp_path), file_path="provider.py", compact=False
        )
    )

    assert architecture["action_items"]["available"] is False
    assert architecture["top_global_hotspots"]["available"] is False
    assert architecture["debt_summary"]["available"] is False
    assert architecture["layer_index"] == {
        "available": True,
        "items": [
            {"layer": "core", "module_count": 1},
            {"layer": "tests", "module_count": 1},
        ],
        "total": 2,
        "truncated": False,
    }
    assert "legacy" not in json.dumps(architecture)
    assert edit_context["risk_score"] is None
    assert edit_context["tests_covering"]["tests"][0]["module"] == "quality.scenario"


def test_minimal_file_context_fails_closed_without_usable_live_graph(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(query_helpers, "read_registries",
        lambda _root: ({"provider": "1/1"}, {"1/1": "provider"}, {}, {}),
    )
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda _root: IndexCatalog(
            modules={"1/1": "provider"},
            artifacts={},
            module_paths={"provider": "provider.py"},
            recovered_modules={},
            recovered_artifacts={},
        ),
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
    missing = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(tmp_path), target="1/1", mode="minimal"
        )
    )

    state = RepositoryAnalysisState(modules={"provider": object()})
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    missing_graph = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(tmp_path), target="1/1", mode="minimal"
        )
    )

    assert missing["status"] == "unavailable"
    assert missing_graph["status"] == "unavailable"
    assert "consumers" not in missing
    assert "tests_covering" not in missing_graph


def test_module_context_fails_closed_when_canonical_graph_is_missing(
    tmp_path, monkeypatch
):
    state = RepositoryAnalysisState(modules={"provider": object()})
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    monkeypatch.setattr(query_helpers, "read_registries",
        lambda _root: ({"provider": "1/1"}, {"1/1": "provider"}, {}, {}),
    )

    result = mcp_server.get_module_context.fn(str(tmp_path), "provider")

    assert "dependency graph is unavailable" in result
    assert "live_canonical_graph" not in result


def test_project_architecture_requires_present_complete_module_layers(
    tmp_path, monkeypatch
):
    state = RepositoryAnalysisState(
        modules={"provider": object()},
        cached_analytics_state="fresh",
        cached_analytics={},
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )

    missing = json.loads(mcp_server.get_project_architecture.fn(str(tmp_path)))
    state.cached_analytics = {"module_layers": {}}
    incomplete = json.loads(mcp_server.get_project_architecture.fn(str(tmp_path)))
    state.modules = {}
    fresh_empty = json.loads(mcp_server.get_project_architecture.fn(str(tmp_path)))

    assert missing["layer_index"]["available"] is False
    assert incomplete["layer_index"]["available"] is False
    assert fresh_empty["layer_index"] == {
        "available": True,
        "distribution": {},
        "total": 0,
        "truncated": False,
    }


def test_project_architecture_rejects_extra_deleted_module_layer(
    tmp_path, monkeypatch
):
    state = RepositoryAnalysisState(
        modules={"a": object(), "b": object()},
        cached_analytics_state="fresh",
        cached_analytics={
            "module_layers": {"a": "core", "b": "api", "deleted": "legacy"}
        },
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )

    result = json.loads(mcp_server.get_project_architecture.fn(str(tmp_path)))

    assert result["layer_index"]["available"] is False


def test_project_architecture_compact_layer_distribution_respects_max_items(
    tmp_path, monkeypatch
):
    state = RepositoryAnalysisState(
        modules={
            "pkg.adapter_a": object(),
            "pkg.adapter_b": object(),
            "pkg.engine": object(),
            "pkg.runtime": object(),
        },
        cached_analytics_state="fresh",
        cached_analytics={
            "module_layers": {
                "pkg.adapter_a": "adapter",
                "pkg.adapter_b": "adapter",
                "pkg.engine": "engine",
                "pkg.runtime": "runtime",
            }
        },
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )

    call1 = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
            compact=True,
            max_items=10,
            fields=["layer_index"],
        )
    )
    assert call1 == {
        "layer_index": {
            "available": True,
            "distribution": {
                "adapter": 2,
                "engine": 1,
                "runtime": 1,
            },
            "total": 3,
            "truncated": False,
        }
    }

    call2 = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
            compact=True,
            max_items=2,
            fields=["layer_index"],
        )
    )
    assert call2 == {
        "layer_index": {
            "available": True,
            "distribution": {
                "adapter": 2,
                "engine": 1,
            },
            "total": 3,
            "truncated": True,
            "expand": {
                "compact": False,
                "max_items": None,
            },
        }
    }

    call3 = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
            compact=True,
            max_items=0,
            fields=["layer_index"],
        )
    )
    assert call3 == {
        "layer_index": {
            "available": True,
            "distribution": {},
            "total": 3,
            "truncated": True,
            "expand": {
                "compact": False,
                "max_items": None,
            },
        }
    }

    call4 = json.loads(
        mcp_server.get_project_architecture.fn(
            repo_path=str(tmp_path),
            compact=False,
            max_items=None,
            fields=["layer_index"],
        )
    )
    assert call4 == {
        "layer_index": {
            "available": True,
            "items": [
                {"layer": "adapter", "module_count": 2},
                {"layer": "engine", "module_count": 1},
                {"layer": "runtime", "module_count": 1},
            ],
            "total": 3,
            "truncated": False,
        }
    }


def test_lookup_returns_symbol_facts_when_consumers_are_stale(tmp_path, monkeypatch):
    state = RepositoryAnalysisState(
        artifacts={
            "provider": {
                "own_symbols": ["foo"],
                "symbols": {"functions": ["foo"]},
            }
        },
        artifact_consumption_state="stale",
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    _patch_empty_registries(monkeypatch)

    result = json.loads(mcp_server.lookup_artifact_by_symbol.fn(str(tmp_path), "foo"))
    artifact = result["artifacts"]["provider::foo"]

    assert artifact["full_name"] == "provider::foo"
    assert artifact["kind"] == "function"
    assert artifact["consumers"]["available"] is False
    assert artifact["consumers"]["state"] == "stale"


def test_blast_radius_rejects_ambiguous_textual_leaf(tmp_path, monkeypatch):
    state = RepositoryAnalysisState(
        artifacts={
            "alpha": {"own_symbols": ["foo"], "symbols": {"functions": ["foo"]}},
            "beta": {"own_symbols": ["foo"], "symbols": {"functions": ["foo"]}},
        },
        artifact_consumption={
            "alpha::foo": {"consumers": [], "channels": {}},
            "beta::foo": {"consumers": [], "channels": {}},
        },
        artifact_consumption_state="fresh",
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    _patch_empty_registries(monkeypatch)

    ambiguous = json.loads(
        mcp_server.get_artifact_blast_radius.fn(str(tmp_path), "foo")
    )
    exact = json.loads(
        mcp_server.get_artifact_blast_radius.fn(str(tmp_path), "alpha::foo")
    )

    assert ambiguous["error"] == "Ambiguous canonical artifact identity."
    assert ambiguous["candidates"] == ["alpha::foo", "beta::foo"]
    assert exact["artifact"] == "alpha::foo"


def test_full_file_context_public_api_uses_canonical_symbol_domain(
    tmp_path, monkeypatch
):
    target = tmp_path / "provider.py"
    target.write_text("def foo():\n    pass\n", encoding="utf-8")
    state = RepositoryAnalysisState(
        modules={"provider": SimpleNamespace(module_id="1/1")},
        artifacts={
            "provider": {
                "own_symbols": ["foo"],
                "symbols": {"functions": ["foo", "legacy_old"]},
            }
        },
        dependency_graph=SimpleNamespace(hard_edges={}, soft_edges={}),
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    _patch_empty_registries(monkeypatch)

    result = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(tmp_path), file_path="provider.py", compact=False
        )
    )

    assert result["public_api"]["items"] == {"provider::foo": "provider::foo"}
    assert "legacy_old" not in json.dumps(result["public_api"])


def test_live_first_tools_work_without_any_saved_reports(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    target = repo / "pkg" / "module.py"
    target.parent.mkdir(parents=True)
    target.write_text("def api():\n    return 1\n", encoding="utf-8")
    engine = _live_engine_fixture()
    def reject_report_resolution(*_args, **_kwargs):
        raise AssertionError("normal MCP query must not resolve output reports")

    monkeypatch.setattr(report_helpers, "get_canonical_report", reject_report_resolution)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(query_helpers, "read_registries",
        lambda _root: (
            {"pkg.module": "1/1", "pkg.dep": "2/1", "tests.test_module": "3/1"},
            {"1/1": "pkg.module", "2/1": "pkg.dep", "3/1": "tests.test_module"},
            {"pkg.module::api": "A1/1"},
            {"A1/1": "pkg.module::api"},
        ),
    )

    architecture = json.loads(mcp_server.get_project_architecture.fn(str(repo)))
    assert architecture["top_global_hotspots"]["available"] is False
    assert architecture["debt_summary"]["available"] is False
    blast = json.loads(
        mcp_server.get_artifact_blast_radius.fn(str(repo), "pkg.module::api", compact=False)
    )
    edit = json.loads(
        mcp_server.get_file_edit_context.fn(
            str(repo), "pkg/module.py", compact=False, max_items=10
        )
    )
    module = json.loads(mcp_server.get_module_context.fn(str(repo), "pkg.module"))
    artifacts = json.loads(
        mcp_server.get_artifacts_for_module.fn(str(repo), "pkg.module", compact=False)
    )
    lookup = json.loads(
        mcp_server.lookup_artifact_by_symbol.fn(str(repo), "api", compact=False)
    )

    assert architecture["data_source"] == "live_canonical_state"
    assert architecture["module_count"] == 3
    assert blast["data_source"] == "live_canonical_state"
    assert blast["consumers"]["items"] == ["tests.test_module"]
    assert edit["dependency_data_source"] == "live_canonical_graph"
    assert edit["public_api"]["total"] == 1
    assert edit["tests_covering"]["available"] is True
    assert module["dependency_data_source"] == "live_canonical_graph"
    assert artifacts["artifacts"]["A1/1"]["consumers"]["items"] == [
        "tests.test_module"
    ]
    assert lookup["data_source"] == "live_canonical_state"
    assert lookup["artifacts"]["A1/1"]["consumers"]["items"] == [
        "tests.test_module"
    ]


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
    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        "contextor.core.live_state.connect_or_start",
        lambda _root, *args, **kwargs: client,
    )
    analysis_jobs._analysis_tasks.clear()
    analysis_jobs._analysis_jobs_by_repo.clear()

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

        task = analysis_jobs._analysis_tasks[first["job_id"]]
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

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", broken_worker)
    analysis_jobs._analysis_tasks.clear()
    analysis_jobs._analysis_jobs_by_repo.clear()

    async def scenario():
        accepted = json.loads(await mcp_server.analyze_project.fn(str(repo)))
        task = analysis_jobs._analysis_tasks[accepted["job_id"]]
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

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(
        "contextor.core.live_state.connect_or_start",
        lambda _root, *args, **kwargs: Client(),
    )
    analysis_jobs._analysis_tasks.clear()
    analysis_jobs._analysis_jobs_by_repo.clear()

    async def scenario():
        accepted = json.loads(await mcp_server.analyze_project.fn(str(repo)))
        task = analysis_jobs._analysis_tasks[accepted["job_id"]]
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
    analysis_jobs._write_analysis_job(
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
        analysis_jobs.ContextorFacade,
        "analyze_project",
        staticmethod(fake_analyze_project),
    )

    outcome = asyncio.run(analysis_jobs._run_analysis_worker("project", repo))

    assert outcome == {"skipped_python_files": skipped}


def test_analysis_status_bounds_and_exposes_skipped_python_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    job_id = "b" * 32
    analysis_jobs._write_analysis_job(
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

    monkeypatch.setattr(analysis_jobs, "_start_analysis_job", fake_start)

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

    monkeypatch.setattr(analysis_jobs, "_run_analysis_worker", fake_worker)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: object())
    analysis_jobs._analysis_tasks.clear()
    analysis_jobs._analysis_jobs_by_repo.clear()

    async def scenario():
        accepted = json.loads(await mcp_server.analyze_project.fn(str(repo)))
        await asyncio.to_thread(progress_written.wait)
        running = json.loads(
            mcp_server.get_analysis_status.fn(str(repo), accepted["job_id"])
        )
        assert running["status"] == "running"
        assert running["message"] == "Indexing 42 modules..."
        release.set()
        task = analysis_jobs._analysis_tasks[accepted["job_id"]]
        task.join(timeout=5)
        assert not task.is_alive()

    asyncio.run(scenario())


def test_output_guard_boundary_and_contract():
    from contextor.mcp.output_guard import guard_large_output, LARGE_OUTPUT_WARNING_BYTES

    # Exact threshold payload (15360 bytes)
    exact_payload = " " * LARGE_OUTPUT_WARNING_BYTES
    assert guard_large_output(exact_payload, allow_large_output=False, retry_instruction="test") == exact_payload

    # Above threshold (15361 bytes)
    over_payload = " " * (LARGE_OUTPUT_WARNING_BYTES + 1)
    res_warn = json.loads(guard_large_output(over_payload, allow_large_output=False, retry_instruction="retry now"))
    assert res_warn["status"] == "confirmation_required"
    assert res_warn["reason"] == "Estimated output exceeds the recommended context size."
    assert res_warn["estimated_output_bytes"] == LARGE_OUTPUT_WARNING_BYTES + 1
    assert res_warn["retry"] == {"allow_large_output": True}
    assert res_warn["retry_instruction"] == "retry now"

    # Override returns over_payload directly
    assert guard_large_output(over_payload, allow_large_output=True, retry_instruction="retry now") == over_payload


def test_get_analysis_status_large_output_preflight_gate(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    job_id = "a" * 32
    large_skipped = [
        {"path": f"pkg/sub/file_{i}.py", "reason": f"Syntax error on file {i}", "line_number": i, "column_number": 1}
        for i in range(250)
    ]
    job_payload = {
        "job_id": job_id,
        "operation": "project",
        "repo_path": str(repo),
        "target": None,
        "status": "completed",
        "created_at": "2026-08-20T00:00:00+00:00",
        "started_at": "2026-08-20T00:00:01+00:00",
        "completed_at": "2026-08-20T00:01:00+00:00",
        "updated_at": "2026-08-20T00:01:00+00:00",
        "message": "Done",
        "error": None,
        "live_publish_status": "success",
        "live_publish_revision": 1,
        "live_publish_warning": None,
        "skipped_python_files": large_skipped,
    }
    analysis_jobs._write_analysis_job(repo, job_payload)

    # 1. Default max_skipped_files=10 -> small output below threshold -> returns normally
    raw_default = mcp_server.get_analysis_status.fn(str(repo), job_id)
    res_default = json.loads(raw_default)
    assert res_default["status"] == "completed"
    assert len(res_default["analysis_coverage"]["skipped_python_files"]["items"]) == 10
    assert len(raw_default.encode("utf-8")) < 15360

    # 2. Unlimited max_skipped_files=None with allow_large_output=False -> confirmation_required
    raw_warn = mcp_server.get_analysis_status.fn(str(repo), job_id, max_skipped_files=None)
    warn = json.loads(raw_warn)
    assert warn["status"] == "confirmation_required"
    assert warn["reason"] == "Estimated output exceeds the recommended context size."
    assert warn["warning_threshold_bytes"] == 15360
    assert warn["warning_threshold_kib"] == 15.0
    assert warn["estimated_output_bytes"] > 15360
    assert warn["estimated_output_kib"] == warn["estimated_output_bytes"] / 1024
    assert warn["retry"] == {"allow_large_output": True}
    assert "repo_path" not in warn
    assert "job_id" not in warn
    assert "skipped_python_files" not in raw_warn
    assert "Repeat the same get_analysis_status call" in warn["retry_instruction"]
    assert len(raw_warn.encode("utf-8")) < 1024

    # 3. Unlimited max_skipped_files=None with allow_large_output=True -> full status
    raw_override = mcp_server.get_analysis_status.fn(str(repo), job_id, max_skipped_files=None, allow_large_output=True)
    override = json.loads(raw_override)
    assert override["status"] == "completed"
    assert len(override["analysis_coverage"]["skipped_python_files"]["items"]) == 250
    assert len(raw_override.encode("utf-8")) == warn["estimated_output_bytes"]


def test_lookup_index_entries_distinguishes_active_recovery_and_missing(
    tmp_path, monkeypatch
):
    catalog = IndexCatalog(
        modules={"1/1": "pkg.active"},
        artifacts={"A1/1": "pkg.active::run"},
        recovered_modules={"2/1": "pkg.removed"},
        recovered_artifacts={"A2/1": "pkg.removed::old"},
    )
    monkeypatch.setattr(
        lookup_index_entries_tool,
        "catalog_from_registry",
        lambda _root: catalog,
    )

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


def test_lookup_index_entries_large_output_preflight_gate(tmp_path, monkeypatch):
    # Construct a catalog where 200 modules generate ~18 KB of formatted JSON
    modules = {f"{i}/1": f"pkg.submodule.very_long_component_name_number_{i}" for i in range(200)}
    catalog = IndexCatalog(
        modules=modules,
        artifacts={},
    )
    monkeypatch.setattr(
        lookup_index_entries_tool,
        "catalog_from_registry",
        lambda _root: catalog,
    )

    ids = [f"{i}/1" for i in range(200)]
    ids_with_dup = ids + ["0/1", "1/1"]

    # 1. Above threshold with default allow_large_output=False -> confirmation_required without echoed IDs
    raw_warn = mcp_server.lookup_index_entries.fn(
        repo_path=str(tmp_path),
        ids=ids_with_dup,
    )
    warn = json.loads(raw_warn)
    assert warn["status"] == "confirmation_required"
    assert warn["reason"] == "Estimated lookup output exceeds the recommended context size."
    assert warn["requested_count"] == 202
    assert warn["warning_threshold_bytes"] == 15360
    assert warn["warning_threshold_kib"] == 15.0
    assert warn["estimated_output_bytes"] > 15360
    assert warn["estimated_output_kib"] == warn["estimated_output_bytes"] / 1024
    assert warn["retry"] == {
        "allow_large_output": True,
    }
    assert "ids" not in warn["retry"]
    assert "ids" not in warn
    assert "repo_path" not in warn["retry"]
    assert "repo_path" not in warn
    assert "retry_instruction" in warn
    assert "same repo_path and ids" in warn["retry_instruction"]
    assert "pkg.submodule" not in raw_warn
    # Warning response itself must remain compact and well below 15 KiB
    assert len(raw_warn.encode("utf-8")) < 1024

    # 2. Above threshold with allow_large_output=True -> full normal mapping
    raw_override = mcp_server.lookup_index_entries.fn(
        repo_path=str(tmp_path),
        ids=ids_with_dup,
        allow_large_output=True,
    )
    override = json.loads(raw_override)
    assert "status" not in override or override.get("status") != "confirmation_required"
    assert len(override) == 200
    assert override["0/1"] == {"name": "pkg.submodule.very_long_component_name_number_0", "status": "active"}
    assert len(raw_override.encode("utf-8")) == warn["estimated_output_bytes"]

    # 3. Below threshold (<15 KiB) with allow_large_output=False -> normal mapping directly
    small_ids = ["0/1", "1/1", "2/1"]
    raw_small_def = mcp_server.lookup_index_entries.fn(
        repo_path=str(tmp_path),
        ids=small_ids,
    )
    small_def = json.loads(raw_small_def)
    assert "status" not in small_def

    # 4. Below threshold with allow_large_output=True is semantically identical
    raw_small_override = mcp_server.lookup_index_entries.fn(
        repo_path=str(tmp_path),
        ids=small_ids,
        allow_large_output=True,
    )
    small_override = json.loads(raw_small_override)
    assert small_def == small_override



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
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: catalog,
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    raw = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="pkg/cli.py",
        report_path=str(report_path),
    )
    result = json.loads(raw)
    expected = query_indexed_report(report, "pkg/cli.py", catalog, repo_root=str(tmp_path))

    for k, v in expected["artifacts"].items():
        v["consumer_modules_truncated"] = False
        v["consumer_count"] = len(v.get("consumer_modules", []))
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
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: catalog,
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

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


def test_extract_indexed_report_context_nested_progressive_disclosure(tmp_path, monkeypatch):
    catalog = IndexCatalog(
        modules={
            "1/1": "main",
            "2/1": "pkg.c1",
            "3/1": "pkg.c2",
            "4/1": "pkg.c3",
            "5/1": "pkg.c4",
            "6/1": "pkg.c5",
        },
        artifacts={
            "A1/1": "main::service",
            "A2/1": "main::isolated",
        },
        module_paths={"main": "main.py"},
    )
    report = {
        "_format_version": "3",
        "artifacts": {
            "A1/1": {
                "definer_module": "1/1",
                "consumer_module_indices": ["2/1", "3/1", "4/1", "5/1", "6/1"],
                "consumer_count": 5,
            },
            "A2/1": {
                "definer_module": "1/1",
                "consumer_module_indices": [],
                "consumer_count": 0,
            },
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: catalog,
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    # 1. Default Resolved (cap 3)
    raw_default = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
    )
    res_default = json.loads(raw_default)
    art1 = res_default["artifacts"]["main::service"]
    assert art1["consumer_count"] == 5
    assert art1["consumer_modules"] == ["pkg.c1", "pkg.c2", "pkg.c3"]
    assert art1["consumer_modules_truncated"] is True

    art2 = res_default["artifacts"]["main::isolated"]
    assert art2["consumer_count"] == 0
    assert art2["consumer_modules"] == []
    assert art2["consumer_modules_truncated"] is False

    # Expand descriptor check
    assert "expand" in res_default
    exp = res_default["expand"]
    assert exp["available"] is True
    assert exp["retry_with_full_evidence"] == {
        "query": "main.py",
        "report_path": str(report_path),
        "resolve_indices": True,
        "public_api_only": False,
        "max_items": 20,
        "fields": None,
        "evidence_limit": None,
    }
    assert exp["retry_fully_lossless"] == {
        "query": "main.py",
        "report_path": str(report_path),
        "resolve_indices": True,
        "public_api_only": False,
        "max_items": None,
        "fields": None,
        "evidence_limit": None,
    }

    # 2. Default Indexed (cap 3)
    raw_indexed = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        resolve_indices=False,
    )
    res_indexed = json.loads(raw_indexed)
    art1_idx = res_indexed["artifacts"]["A1/1"]
    assert art1_idx["consumer_count"] == 5
    assert art1_idx["consumer_module_indices"] == ["2/1", "3/1", "4/1"]
    assert art1_idx["consumer_module_indices_truncated"] is True
    # Logical parity
    assert [catalog.modules[m] for m in art1_idx["consumer_module_indices"]] == art1["consumer_modules"]

    # 3. evidence_limit = 0
    raw_zero = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        evidence_limit=0,
    )
    res_zero = json.loads(raw_zero)
    assert res_zero["artifacts"]["main::service"]["consumer_modules"] == []
    assert res_zero["artifacts"]["main::service"]["consumer_count"] == 5
    assert res_zero["artifacts"]["main::service"]["consumer_modules_truncated"] is True
    assert res_zero["artifacts"]["main::isolated"]["consumer_modules_truncated"] is False

    # 4. evidence_limit = None (lossless evidence)
    raw_full = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        evidence_limit=None,
    )
    res_full = json.loads(raw_full)
    assert len(res_full["artifacts"]["main::service"]["consumer_modules"]) == 5
    assert res_full["artifacts"]["main::service"]["consumer_modules_truncated"] is False
    assert "expand" not in res_full

    # 5. Fully lossless: max_items=None, evidence_limit=None
    raw_lossless = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        max_items=None,
        evidence_limit=None,
    )
    res_lossless = json.loads(raw_lossless)
    assert res_lossless["artifact_count"] == 2
    assert len(res_lossless["artifacts"]["main::service"]["consumer_modules"]) == 5
    assert res_lossless["truncated"] is False
    assert "expand" not in res_lossless

    # 6. fields excluding artifacts => no expand descriptor
    raw_fields_no_art = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        fields=["resolution", "total_artifact_count"],
    )
    res_fields_no_art = json.loads(raw_fields_no_art)
    assert "expand" not in res_fields_no_art
    assert "artifacts" not in res_fields_no_art
    assert res_fields_no_art["total_artifact_count"] == 2

    # 7. fields including artifacts => expand descriptor is attached
    raw_fields_with_art = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        fields=["artifacts", "artifact_count"],
    )
    res_fields_with_art = json.loads(raw_fields_with_art)
    assert "expand" in res_fields_with_art
    assert "artifacts" in res_fields_with_art

    # 8. negative evidence_limit (Contextor convention: safe_limit = max(0, limit))
    raw_neg = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        evidence_limit=-1,
    )
    res_neg = json.loads(raw_neg)
    assert res_neg["artifacts"]["main::service"]["consumer_modules"] == []
    assert res_neg["artifacts"]["main::service"]["consumer_count"] == 5
    assert res_neg["artifacts"]["main::service"]["consumer_modules_truncated"] is True

    # 9. Non-default parameter preservation in expand retry descriptors
    raw_nondefault = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        resolve_indices=False,
        public_api_only=True,
        max_items=1,
        fields=["artifacts", "artifact_count"],
    )
    res_nondefault = json.loads(raw_nondefault)
    assert "expand" in res_nondefault
    exp_nd = res_nondefault["expand"]
    assert exp_nd["available"] is True
    assert exp_nd["retry_with_full_evidence"] == {
        "query": "main.py",
        "report_path": str(report_path),
        "resolve_indices": False,
        "public_api_only": True,
        "max_items": 1,
        "fields": ["artifacts", "artifact_count"],
        "evidence_limit": None,
    }
    assert exp_nd["retry_fully_lossless"] == {
        "query": "main.py",
        "report_path": str(report_path),
        "resolve_indices": False,
        "public_api_only": True,
        "max_items": None,
        "fields": ["artifacts", "artifact_count"],
        "evidence_limit": None,
    }


def test_extract_indexed_report_context_representation_negotiation(tmp_path, monkeypatch):
    # Setup catalog with multiple artifacts to test auto above/below threshold and S2 parity
    catalog = IndexCatalog(
        modules={
            "1/1": "main",
            "2/1": "pkg.alpha",
            "3/1": "pkg.beta",
            "4/1": "pkg.gamma",
            "5/1": "pkg.delta",
            "6/1": "pkg.epsilon",
            "7/1": "pkg.zeta",
            "8/1": "pkg.eta",
        },
        artifacts={
            "A10/1": "main::art_ten",
            "A20/1": "main::art_twenty",
            "A30/1": "main::art_thirty",
            "A40/1": "main::art_forty",
            "A50/1": "main::art_fifty",
        },
        module_paths={"main": "main.py"},
    )
    # 5 artifacts with varying consumers
    report = {
        "_format_version": "3",
        "artifacts": {
            "A10/1": {
                "artifact_id": "A10/1",
                "definer_module": "1/1",
                "consumer_module_indices": ["2/1", "3/1", "4/1", "5/1", "6/1", "7/1", "8/1"],
                "consumer_count": 7,
            },
            "A20/1": {
                "artifact_id": "A20/1",
                "definer_module": "1/1",
                "consumer_module_indices": ["2/1", "3/1", "4/1", "5/1"],
                "consumer_count": 4,
            },
            "A30/1": {
                "artifact_id": "A30/1",
                "definer_module": "1/1",
                "consumer_module_indices": ["2/1", "3/1"],
                "consumer_count": 2,
            },
            "A40/1": {
                "artifact_id": "A40/1",
                "definer_module": "1/1",
                "consumer_module_indices": ["2/1"],
                "consumer_count": 1,
            },
            "A50/1": {
                "artifact_id": "A50/1",
                "definer_module": "1/1",
                "consumer_module_indices": [],
                "consumer_count": 0,
            },
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: catalog,
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    # 1. Invalid representation -> Fail-closed error
    raw_invalid = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        representation="xml",
    )
    res_invalid = json.loads(raw_invalid)
    assert "error" in res_invalid
    assert res_invalid["representation"] == "xml"
    assert res_invalid["allowed_representations"] == ["auto", "indexed", "named"]

    # 2. Legacy representation=None -> 100% legacy A12.3 behavior (no protocol metadata)
    raw_legacy = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        representation=None,
    )
    res_legacy = json.loads(raw_legacy)
    assert "representation" not in res_legacy
    assert "resolve_via" not in res_legacy
    assert "artifacts" in res_legacy
    assert "main::art_ten" in res_legacy["artifacts"]

    # 3. Explicit representation="named" -> Protocol metadata attached
    raw_named = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        representation="named",
    )
    res_named = json.loads(raw_named)
    assert res_named["representation"] == "named"
    assert "resolve_via" not in res_named
    assert "main::art_ten" in res_named["artifacts"]

    # 4. Explicit representation="indexed" -> Protocol metadata attached
    raw_indexed = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        representation="indexed",
    )
    res_indexed = json.loads(raw_indexed)
    assert res_indexed["representation"] == "indexed"
    assert res_indexed["resolve_via"] == "lookup_index_entries"
    assert "A10/1" in res_indexed["artifacts"]

    # 5. Deterministic Precedence over resolve_indices
    # representation="named" with resolve_indices=False -> resolved named
    raw_prec_named = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        resolve_indices=False,
        representation="named",
    )
    res_prec_named = json.loads(raw_prec_named)
    assert res_prec_named["representation"] == "named"
    assert "main::art_ten" in res_prec_named["artifacts"]

    # representation="indexed" with resolve_indices=True -> indexed
    raw_prec_indexed = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        resolve_indices=True,
        representation="indexed",
    )
    res_prec_indexed = json.loads(raw_prec_indexed)
    assert res_prec_indexed["representation"] == "indexed"
    assert res_prec_indexed["resolve_via"] == "lookup_index_entries"
    assert "A10/1" in res_prec_indexed["artifacts"]

    # 6. S2 Canonical Selection Parity between explicit named and indexed when truncated
    raw_named_cap2 = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        max_items=2,
        representation="named",
    )
    raw_indexed_cap2 = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        max_items=2,
        representation="indexed",
    )
    res_named_cap2 = json.loads(raw_named_cap2)
    res_indexed_cap2 = json.loads(raw_indexed_cap2)
    named_ids = [entry["artifact_id"] for entry in res_named_cap2["artifacts"].values()]
    indexed_ids = [entry["artifact_id"] for entry in res_indexed_cap2["artifacts"].values()]
    assert named_ids == indexed_ids == ["A10/1", "A20/1"]

    # 7. Auto Below Threshold (SMALL payload saves < 512 B) -> Direct Named Result
    raw_auto_small = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        max_items=1,
        evidence_limit=1,
        representation="auto",
    )
    res_auto_small = json.loads(raw_auto_small)
    assert res_auto_small["representation"] == "named"
    assert res_auto_small["requested_representation"] == "auto"
    assert "status" not in res_auto_small
    assert "main::art_ten" in res_auto_small["artifacts"]
    # Expand retains representation="auto" (E1)
    assert "expand" in res_auto_small
    assert res_auto_small["expand"]["retry_with_full_evidence"]["representation"] == "auto"
    assert res_auto_small["expand"]["retry_fully_lossless"]["representation"] == "auto"

    # 8. Auto Above Threshold (LARGE unclipped consumers save >= 512 B) -> Decision Response
    # Create large report with many consumers to exceed 512 B threshold
    (tmp_path / "large_main.py").write_text("# main\n", encoding="utf-8")
    large_catalog_modules = {
        f"{i}/1": f"deeply.nested.package.consumer_module_number_{i:03d}"
        for i in range(1, 100)
    }
    large_catalog_modules["100/1"] = "large_main"
    large_catalog = IndexCatalog(
        modules=large_catalog_modules,
        artifacts={"A999/1": "large_main::heavy_symbol"},
        module_paths={"large_main": "large_main.py"},
    )
    large_report = {
        "_format_version": "3",
        "artifacts": {
            "A999/1": {
                "artifact_id": "A999/1",
                "definer_module": "100/1",
                "consumer_module_indices": [f"{i}/1" for i in range(1, 80)],
                "consumer_count": 79,
            }
        },
    }
    large_report_path = tmp_path / "large_report.json"
    large_report_path.write_text(json.dumps(large_report), encoding="utf-8")
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: large_catalog,
    )

    raw_auto_large = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="large_main.py",
        report_path=str(large_report_path),
        evidence_limit=80,
        representation="auto",
    )
    res_auto_large = json.loads(raw_auto_large)
    assert res_auto_large["status"] == "representation_decision_required"
    assert res_auto_large["requested_representation"] == "auto"
    assert res_auto_large["total_artifact_count"] == 1
    assert res_auto_large["artifact_count"] == 1
    assert "sizes" in res_auto_large
    assert res_auto_large["sizes"]["bytes_saved"] >= 512
    assert "evidence" in res_auto_large
    assert len(res_auto_large["evidence"]) == 1
    assert res_auto_large["evidence"][0]["artifact_id"] == "A999/1"
    assert res_auto_large["evidence"][0]["artifact"] == "large_main::heavy_symbol"
    assert "options" in res_auto_large
    assert "named" in res_auto_large["options"]
    assert "indexed" in res_auto_large["options"]
    assert res_auto_large["options"]["named"]["representation"] == "named"
    assert res_auto_large["options"]["indexed"]["representation"] == "indexed"
    assert "expand" not in res_auto_large

    # 9. Executability of decision options and exact candidate sizes parity
    named_retry_kwargs = dict(res_auto_large["options"]["named"])
    indexed_retry_kwargs = dict(res_auto_large["options"]["indexed"])

    raw_named_exec = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path), **named_retry_kwargs
    )
    raw_indexed_exec = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path), **indexed_retry_kwargs
    )

    assert len(raw_named_exec.encode("utf-8")) == res_auto_large["sizes"]["named_bytes"]
    assert len(raw_indexed_exec.encode("utf-8")) == res_auto_large["sizes"]["indexed_bytes"]

    # 10. Fields without artifacts skips negotiation
    raw_fields_no_art = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="large_main.py",
        report_path=str(large_report_path),
        evidence_limit=50,
        fields=["resolution", "total_artifact_count"],
        representation="auto",
    )
    res_fields_no_art = json.loads(raw_fields_no_art)
    assert res_fields_no_art["representation"] == "named"
    assert res_fields_no_art["requested_representation"] == "auto"
    assert "status" not in res_fields_no_art
    assert "artifacts" not in res_fields_no_art
    assert res_fields_no_art["total_artifact_count"] == 1

    # 11. Explicit Lossless Named and Indexed
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: catalog,
    )
    raw_lossless_named = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        max_items=None,
        evidence_limit=None,
        representation="named",
    )
    res_lossless_named = json.loads(raw_lossless_named)
    assert res_lossless_named["representation"] == "named"
    assert res_lossless_named["artifact_count"] == 5
    assert res_lossless_named["total_artifact_count"] == 5
    assert res_lossless_named["truncated"] is False
    assert len(res_lossless_named["artifacts"]["main::art_ten"]["consumer_modules"]) == 7

    raw_lossless_indexed = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(report_path),
        max_items=None,
        evidence_limit=None,
        representation="indexed",
    )
    res_lossless_indexed = json.loads(raw_lossless_indexed)
    assert res_lossless_indexed["representation"] == "indexed"
    assert res_lossless_indexed["resolve_via"] == "lookup_index_entries"
    assert res_lossless_indexed["artifact_count"] == 5
    assert len(res_lossless_indexed["artifacts"]["A10/1"]["consumer_module_indices"]) == 7

    # 12. S2 canonical ordering vs legacy symbol-string ordering when truncated
    # Setup report where symbol-name order differs from artifact-id order:
    # A10/1 -> "main::zeta_symbol"
    # A20/1 -> "main::alpha_symbol"
    ordering_catalog = IndexCatalog(
        modules={"1/1": "main"},
        artifacts={"A10/1": "main::zeta_symbol", "A20/1": "main::alpha_symbol"},
        module_paths={"main": "main.py"},
    )
    ordering_report = {
        "_format_version": "3",
        "artifacts": {
            "A10/1": {"artifact_id": "A10/1", "definer_module": "1/1", "consumer_module_indices": [], "consumer_count": 0},
            "A20/1": {"artifact_id": "A20/1", "definer_module": "1/1", "consumer_module_indices": [], "consumer_count": 0},
        },
    }
    ordering_report_path = tmp_path / "ordering_report.json"
    ordering_report_path.write_text(json.dumps(ordering_report), encoding="utf-8")
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: ordering_catalog,
    )

    # Legacy: sorted by symbol string -> "main::alpha_symbol" (A20/1) comes first
    raw_ord_legacy = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(ordering_report_path),
        max_items=1,
        representation=None,
    )
    res_ord_legacy = json.loads(raw_ord_legacy)
    assert list(res_ord_legacy["artifacts"].keys()) == ["main::alpha_symbol"]

    # Explicit Named: sorted canonically by artifact ID -> "A10/1" ("main::zeta_symbol") comes first
    raw_ord_explicit_named = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(ordering_report_path),
        max_items=1,
        representation="named",
    )
    res_ord_explicit_named = json.loads(raw_ord_explicit_named)
    assert list(res_ord_explicit_named["artifacts"].keys()) == ["main::zeta_symbol"]

    # Explicit Indexed: sorted canonically by artifact ID -> "A10/1" comes first
    raw_ord_explicit_indexed = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(ordering_report_path),
        max_items=1,
        representation="indexed",
    )
    res_ord_explicit_indexed = json.loads(raw_ord_explicit_indexed)
    assert list(res_ord_explicit_indexed["artifacts"].keys()) == ["A10/1"]

    # 13. Decision evidence bounding: when max_items=1, evidence must have len=1 and be in selected scope
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: large_catalog,
    )
    raw_auto_large_cap1 = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="large_main.py",
        report_path=str(large_report_path),
        max_items=1,
        evidence_limit=80,
        representation="auto",
    )
    res_auto_large_cap1 = json.loads(raw_auto_large_cap1)
    assert res_auto_large_cap1["status"] == "representation_decision_required"
    assert res_auto_large_cap1["artifact_count"] == 1
    assert len(res_auto_large_cap1["evidence"]) == 1
    assert res_auto_large_cap1["evidence"][0]["artifact_id"] == "A999/1"

    # 14. Auto above threshold on multi-artifact order-mismatch fixture (CHECK 1)
    (tmp_path / "multi_mismatch.py").write_text("# multi\n", encoding="utf-8")
    multi_modules = {
        f"{i}/1": f"deeply.nested.package.consumer_module_number_{i:03d}"
        for i in range(1, 100)
    }
    multi_modules["100/1"] = "multi_mismatch"
    multi_catalog = IndexCatalog(
        modules=multi_modules,
        artifacts={
            "A10/1": "multi_mismatch::zeta_symbol",
            "A20/1": "multi_mismatch::beta_symbol",
            "A30/1": "multi_mismatch::alpha_symbol",
        },
        module_paths={"multi_mismatch": "multi_mismatch.py"},
    )
    multi_report = {
        "_format_version": "3",
        "artifacts": {
            "A10/1": {
                "artifact_id": "A10/1",
                "definer_module": "100/1",
                "consumer_module_indices": [f"{i}/1" for i in range(1, 40)],
                "consumer_count": 39,
            },
            "A20/1": {
                "artifact_id": "A20/1",
                "definer_module": "100/1",
                "consumer_module_indices": [f"{i}/1" for i in range(40, 80)],
                "consumer_count": 40,
            },
            "A30/1": {
                "artifact_id": "A30/1",
                "definer_module": "100/1",
                "consumer_module_indices": [],
                "consumer_count": 0,
            },
        },
    }
    multi_report_path = tmp_path / "multi_report.json"
    multi_report_path.write_text(json.dumps(multi_report), encoding="utf-8")
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: multi_catalog,
    )

    raw_auto_mismatch = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="multi_mismatch.py",
        report_path=str(multi_report_path),
        max_items=2,
        evidence_limit=40,
        representation="auto",
    )
    res_auto_mismatch = json.loads(raw_auto_mismatch)
    assert res_auto_mismatch["status"] == "representation_decision_required"
    assert res_auto_mismatch["total_artifact_count"] == 3
    assert res_auto_mismatch["artifact_count"] == 2
    assert res_auto_mismatch["sizes"]["bytes_saved"] >= 512

    # Options execution verification
    named_opt_exec = json.loads(
        mcp_server.extract_indexed_report_context.fn(
            repo_path=str(tmp_path), **res_auto_mismatch["options"]["named"]
        )
    )
    indexed_opt_exec = json.loads(
        mcp_server.extract_indexed_report_context.fn(
            repo_path=str(tmp_path), **res_auto_mismatch["options"]["indexed"]
        )
    )
    assert list(named_opt_exec["artifacts"].keys()) == [
        "multi_mismatch::zeta_symbol",
        "multi_mismatch::beta_symbol",
    ]
    assert list(indexed_opt_exec["artifacts"].keys()) == ["A10/1", "A20/1"]
    assert (
        [e["artifact_id"] for e in named_opt_exec["artifacts"].values()]
        == [e["artifact_id"] for e in indexed_opt_exec["artifacts"].values()]
        == ["A10/1", "A20/1"]
    )

    # 15. Execute E1 auto expansion with stateless renegotiation (CHECK 2)
    raw_auto_capped_evidence = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="multi_mismatch.py",
        report_path=str(multi_report_path),
        max_items=2,
        evidence_limit=0,
        representation="auto",
    )
    res_auto_capped = json.loads(raw_auto_capped_evidence)
    assert res_auto_capped["representation"] == "named"
    assert res_auto_capped["requested_representation"] == "auto"
    assert "expand" in res_auto_capped
    assert (
        res_auto_capped["expand"]["retry_with_full_evidence"]["representation"]
        == "auto"
    )

    # Executing retry_with_full_evidence renegotiates into decision response
    raw_retry_full = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        **res_auto_capped["expand"]["retry_with_full_evidence"],
    )
    res_retry_full = json.loads(raw_retry_full)
    assert res_retry_full["status"] == "representation_decision_required"
    assert res_retry_full["sizes"]["bytes_saved"] >= 512

    # Executing retry_fully_lossless under auto
    raw_retry_lossless = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        **res_auto_capped["expand"]["retry_fully_lossless"],
    )
    res_retry_lossless = json.loads(raw_retry_lossless)
    assert res_retry_lossless["status"] == "representation_decision_required"
    assert res_retry_lossless["total_artifact_count"] == 3

    # 16. Explicit expand preserves representation (CHECK 3)
    raw_named_capped = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="multi_mismatch.py",
        report_path=str(multi_report_path),
        max_items=2,
        evidence_limit=1,
        representation="named",
    )
    res_named_capped = json.loads(raw_named_capped)
    assert (
        res_named_capped["expand"]["retry_with_full_evidence"]["representation"]
        == "named"
    )
    assert (
        res_named_capped["expand"]["retry_fully_lossless"]["representation"]
        == "named"
    )
    named_expanded = json.loads(
        mcp_server.extract_indexed_report_context.fn(
            repo_path=str(tmp_path),
            **res_named_capped["expand"]["retry_with_full_evidence"],
        )
    )
    assert named_expanded["representation"] == "named"
    assert len(named_expanded["artifacts"]["multi_mismatch::zeta_symbol"]["consumer_modules"]) == 39

    raw_indexed_capped = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="multi_mismatch.py",
        report_path=str(multi_report_path),
        max_items=2,
        evidence_limit=1,
        representation="indexed",
    )
    res_indexed_capped = json.loads(raw_indexed_capped)
    assert (
        res_indexed_capped["expand"]["retry_with_full_evidence"]["representation"]
        == "indexed"
    )
    assert (
        res_indexed_capped["expand"]["retry_fully_lossless"]["representation"]
        == "indexed"
    )
    indexed_expanded = json.loads(
        mcp_server.extract_indexed_report_context.fn(
            repo_path=str(tmp_path),
            **res_indexed_capped["expand"]["retry_with_full_evidence"],
        )
    )
    assert indexed_expanded["representation"] == "indexed"
    assert indexed_expanded["resolve_via"] == "lookup_index_entries"
    assert len(indexed_expanded["artifacts"]["A10/1"]["consumer_module_indices"]) == 39

    # 17. Fields with artifacts in auto mode (CHECK 4)
    raw_auto_fields = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="multi_mismatch.py",
        report_path=str(multi_report_path),
        max_items=2,
        evidence_limit=40,
        fields=["artifacts", "artifact_count"],
        representation="auto",
    )
    res_auto_fields = json.loads(raw_auto_fields)
    assert res_auto_fields["status"] == "representation_decision_required"
    assert res_auto_fields["options"]["named"]["fields"] == ["artifacts", "artifact_count"]
    assert res_auto_fields["options"]["indexed"]["fields"] == ["artifacts", "artifact_count"]
    named_f_exec = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path), **res_auto_fields["options"]["named"]
    )
    indexed_f_exec = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path), **res_auto_fields["options"]["indexed"]
    )
    assert len(named_f_exec.encode("utf-8")) == res_auto_fields["sizes"]["named_bytes"]
    assert len(indexed_f_exec.encode("utf-8")) == res_auto_fields["sizes"]["indexed_bytes"]
    named_f_obj = json.loads(named_f_exec)
    assert set(named_f_obj.keys()) == {"artifacts", "artifact_count", "representation"}

    # 18. Scope mismatch failsafe (CHECK 5)
    import contextor.core.report_query as rq
    orig_rewrite = rq.rewrite_selected_indices

    call_count = 0

    def _mismatch_rewrite(blocks, cat, resolve_names=True):
        nonlocal call_count
        rewritten, diag = orig_rewrite(blocks, cat, resolve_names=resolve_names)
        if not resolve_names:
            call_count += 1
            # Mutate candidate generation (call 2) to force candidate mismatch
            if call_count == 2:
                rewritten = {k: v for k, v in list(rewritten.items())[:1]}
        return rewritten, diag

    monkeypatch.setattr(rq, "rewrite_selected_indices", _mismatch_rewrite)
    raw_mismatch_fallback = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="multi_mismatch.py",
        report_path=str(multi_report_path),
        max_items=2,
        evidence_limit=40,
        representation="auto",
    )
    res_mismatch_fallback = json.loads(raw_mismatch_fallback)
    assert "status" not in res_mismatch_fallback
    assert res_mismatch_fallback["representation"] == "named"
    assert res_mismatch_fallback["requested_representation"] == "auto"
    assert res_mismatch_fallback["artifact_count"] == 2
    monkeypatch.setattr(rq, "rewrite_selected_indices", orig_rewrite)

    # 19. Diagnostics preservation across query resolution (CHECK 6)
    diag_catalog = IndexCatalog(
        modules={"1/1": "main", "2/1": "pkg.c1"},
        artifacts={"A1/1": "main::art1", "A2/1": "main::art2", "A3/1": "main::art3"},
        module_paths={"main": "main.py"},
    )
    # Report where A3/1 has unknown module '99/1' in consumer_module_indices
    diag_report = {
        "_format_version": "3",
        "artifacts": {
            "A1/1": {"artifact_id": "A1/1", "definer_module": "1/1", "consumer_module_indices": ["2/1"], "consumer_count": 1},
            "A2/1": {"artifact_id": "A2/1", "definer_module": "1/1", "consumer_module_indices": [], "consumer_count": 0},
            "A3/1": {"artifact_id": "A3/1", "definer_module": "1/1", "consumer_module_indices": ["99/1"], "consumer_count": 1},
        }
    }
    diag_report_path = tmp_path / "diag_report.json"
    diag_report_path.write_text(json.dumps(diag_report), encoding="utf-8")
    monkeypatch.setattr(
        "contextor.core.report_query.catalog_from_registry",
        lambda *_args, **_kwargs: diag_catalog,
    )
    # Bounded query (max_items=1 selects only A1/1; A3/1 is outside bounded scope)
    raw_diag_named = mcp_server.extract_indexed_report_context.fn(
        repo_path=str(tmp_path),
        query="main.py",
        report_path=str(diag_report_path),
        max_items=1,
        representation="named",
    )
    res_diag_named = json.loads(raw_diag_named)
    assert res_diag_named["artifact_count"] == 1
    assert len(res_diag_named["diagnostics"]["dropped_references"]) == 1
    assert res_diag_named["diagnostics"]["dropped_references"][0]["artifact_id"] == "A3/1"





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
        report_helpers,
        "get_canonical_report",
        lambda _root, name: next(
            (path for suffix, path in reports.items() if name.endswith(suffix)), None
        ),
    )
    monkeypatch.setattr(query_helpers, "read_registries",
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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
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

    persisted = update_file_module._persist_live_engine(tmp_path, engine)

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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: True)
    monkeypatch.setattr(
        update_file_module,
        "_mcp_runtime_restart_required",
        lambda _path: False,
    )

    current = json.loads(
        mcp_server.update_file.fn(repo_path=str(repo), file_path=str(server_path))
    )
    assert current["runtime_restart_required"] is False
    assert "runtime_state" not in current

    monkeypatch.setattr(
        update_file_module,
        "_mcp_runtime_restart_required",
        lambda _path: True,
    )
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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(update_file_module, "_persist_live_engine", lambda *_args: True)

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
                "contextor.mcp_main",
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


def test_mcp_worker_preserves_pool_policy_and_restores_environment(
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
        calls.append(
            (
                file_path,
                repo_path,
                log,
                additional_excludes,
                os.environ.get("CONTEXTOR_DISABLE_PROCESS_POOL"),
            )
        )
        assert os.environ["CONTEXTOR_MCP_PROCESS_REGISTRY"] == str(
            mcp_process_registry.registry_dir(repo)
        )

    monkeypatch.setattr(ContextorFacade, "analyze_single_file", fake_analysis)
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", "original-cache")
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    monkeypatch.delenv("CONTEXTOR_MCP_PROCESS_REGISTRY", raising=False)

    asyncio.run(analysis_jobs._run_analysis_worker("single_file", repo, target))

    assert calls == [(str(target), str(repo), analysis_jobs._stderr_log, None, None)]
    assert os.environ["CONTEXTOR_CACHE_DIR"] == "original-cache"
    assert "CONTEXTOR_DISABLE_PROCESS_POOL" not in os.environ
    assert "CONTEXTOR_MCP_PROCESS_REGISTRY" not in os.environ

    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    asyncio.run(analysis_jobs._run_analysis_worker("single_file", repo, target))
    assert os.environ["CONTEXTOR_DISABLE_PROCESS_POOL"] == "1"
    assert calls[-1] == (
        str(target),
        str(repo),
        analysis_jobs._stderr_log,
        None,
        "1",
    )


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
        analysis_jobs._run_analysis_worker(
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

    result = update_file_module._semantic_artifact_diff(old, new)

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

    result = update_file_module._semantic_artifact_diff(old, new)

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

    compact = update_file_module._semantic_diff_view(diff, max_items=1, compact=True)
    full = update_file_module._semantic_diff_view(diff, max_items=1, compact=False)

    assert compact["symbols_added"] == {"total": 2, "truncated": True}
    assert "items" not in compact["signatures_changed"]
    assert full["symbols_added"]["items"] == ["a"]
    assert full["signatures_changed"]["items"] == {
        "a": {"before": "def a()", "after": "def a(value)"}
    }
    assert full["affected_symbols"]["total"] == 3
    assert full["affected_symbols"]["truncated"] is True


def test_artifact_lookup_ignores_stale_registry_entries(tmp_path, monkeypatch):
    engine = SimpleNamespace(state=RepositoryAnalysisState(
        artifacts={"pkg.module": {
            "symbols": {"functions": ["target"]},
            "own_symbols": ["target"],
        }},
        artifact_consumption={
            "pkg.module::target": {
                "consumers": ["pkg.first", "pkg.second"],
                "channels": {},
            }
        },
        artifact_consumption_state="fresh",
    ))
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(query_helpers, "read_registries",
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
    assert result["data_source"] == "live_canonical_state"

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
        report_helpers,
        "get_canonical_report",
        lambda _root, name: paths.get(name),
    )
    monkeypatch.setattr(query_helpers, "read_registries",
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
    from contextor.core.domain.graph import ProjectGraph

    engine = SimpleNamespace(state=RepositoryAnalysisState(
        modules={
            "pkg.module": SimpleNamespace(module_id="1/1"),
            "pkg.dep": object(),
            "pkg.other": object(),
            "tests.test_module": object(),
            "tests.test_other": object(),
        },
        artifacts={"pkg.module": {
            "own_symbols": ["api", "other"],
            "symbols": {"functions": ["api", "other"]},
        }},
        dependency_graph=ProjectGraph(
            hard_edges={
                "pkg.module": {"pkg.dep", "pkg.other"},
                "tests.test_module": {"pkg.module"},
                "tests.test_other": {"pkg.module"},
            },
            soft_edges={},
        ),
        metrics={"pkg.module": {"layer": "domain"}},
    ))
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

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
    assert result["public_api"]["unresolved_ids"] == []
    assert result["public_api"]["unresolved_total"] == 0
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
        "unresolved_total": 0,
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
    monkeypatch.setattr(report_helpers, "get_canonical_report", lambda *_: report)
    monkeypatch.setattr(query_helpers, "read_registries",
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
        artifact_consumption = {"pkg.module::unused": {"consumers": [], "channels": {}}}
        artifact_consumption_state = "fresh"

    class Engine:
        state = State()

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: Engine())

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
        "consumers": {"total": 0, "truncated": False, "evidence": []},
    }


def test_artifacts_for_module_uses_live_state_without_compact_report(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(report_helpers, "get_canonical_report", lambda *_: None)
    monkeypatch.setattr(query_helpers, "read_registries",
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
        artifact_consumption = {"pkg.module::run": {"consumers": [], "channels": {}}}
        artifact_consumption_state = "fresh"

    class Engine:
        state = State()

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: Engine())

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
        "consumers": {"total": 0, "truncated": False, "evidence": []},
    }


def test_artifacts_for_module_bounds_nested_consumers(tmp_path, monkeypatch):
    state = RepositoryAnalysisState(
        modules={"pkg.module": object()},
        artifacts={"pkg.module": {
            "own_symbols": ["run"],
            "symbols": {"functions": ["run"]},
        }},
        artifact_consumption={
            "pkg.module::run": {
                "consumers": ["pkg.first", "pkg.second"],
                "channels": {},
            }
        },
        artifact_consumption_state="fresh",
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    monkeypatch.setattr(query_helpers, "read_registries",
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
    selected, total, truncated = query_helpers.bounded_items(
        ["first", "second", "third"], 2
    )

    assert selected == ["first", "second"]
    assert total == 3
    assert truncated is True

    unbounded, unbounded_total, unbounded_truncated = query_helpers.bounded_items(
        ["first", "second", "third"], None
    )
    assert unbounded == ["first", "second", "third"]
    assert unbounded_total == 3
    assert unbounded_truncated is False


def test_layer_cluster_ids_are_resolved_without_an_extra_lookup():
    result = get_layer_isolation_module._resolve_cluster_ids(
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

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: Engine())

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

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: Engine())

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

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: Engine())
    monkeypatch.setattr(
        report_helpers, "get_canonical_report", lambda _root, _name: report
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
        "evidence": {"pkg.caller": ["hard_dependency"]},
        "total": 1,
        "truncated": False,
    }
    assert result["dependencies_outbound_who_i_call"] == {
        "evidence": {
            "pkg.dependency": ["hard_dependency"],
            "pkg.optional": ["soft_dependency"],
        },
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
    assert "expand" not in full["dependencies_inbound_who_calls_me"]
    assert full["dependencies_outbound_who_i_call"]["expand"] == {
        "compact": False,
        "max_items": None,
    }

    compact_limited = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(tmp_path),
            module_name="pkg.new",
            max_items=1,
            fields=["dependencies_outbound_who_i_call"],
        )
    )
    assert compact_limited["dependencies_outbound_who_i_call"] == {
        "evidence": {"pkg.dependency": ["hard_dependency"]},
        "total": 2,
        "truncated": True,
        "expand": {
            "compact": False,
            "max_items": None,
        },
    }

    compact_zero = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(tmp_path),
            module_name="pkg.new",
            max_items=0,
            fields=["dependencies_outbound_who_i_call"],
        )
    )
    assert compact_zero["dependencies_outbound_who_i_call"] == {
        "evidence": {},
        "total": 2,
        "truncated": True,
        "expand": {
            "compact": False,
            "max_items": None,
        },
    }

    invalid = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(tmp_path),
            module_name="pkg.new",
            fields=["unknown_field"],
        )
    )
    assert invalid["error"] == "Unsupported fields for get_module_context"
    assert invalid["unknown_fields"] == ["unknown_field"]


def test_module_context_compact_max_items_none_caps_evidence_to_three(
    tmp_path, monkeypatch
):
    class Graph:
        hard_edges = {
            "pkg.mod": {"pkg.a", "pkg.b", "pkg.c", "pkg.d"},
        }
        soft_edges = {}

    class State:
        modules = {"pkg.mod": object()}
        artifacts = {}
        dependency_graph = Graph()

    class Engine:
        state = State()

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: Engine())

    result = json.loads(
        mcp_server.get_module_context.fn(
            repo_path=str(tmp_path),
            module_name="pkg.mod",
            compact=True,
            max_items=None,
            fields=["dependencies_outbound_who_i_call"],
        )
    )
    assert result["dependencies_outbound_who_i_call"] == {
        "evidence": {
            "pkg.a": ["hard_dependency"],
            "pkg.b": ["hard_dependency"],
            "pkg.c": ["hard_dependency"],
        },
        "total": 4,
        "truncated": True,
        "expand": {
            "compact": False,
            "max_items": None,
        },
    }


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

    monkeypatch.setattr(report_helpers, "get_canonical_report", canonical)
    monkeypatch.setattr(query_helpers, "read_registries",
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
    monkeypatch.setattr(report_helpers, "resolve_output_dir", lambda: reports)
    monkeypatch.setattr(query_helpers, "read_registries",
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
        report_helpers,
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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

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

    monkeypatch.setattr(report_helpers, "get_canonical_report", canonical)
    state = RepositoryAnalysisState(
        modules={"a": object(), "b": object()},
        layer_information={
            "summary_data": {"action_items": ["a", "b"]},
            "layer_index": [{"layer": "a"}, {"layer": "b"}],
            "hotspots": [{"module": "a"}, {"module": "b"}],
            "debt": {"total_score": 1},
        },
    )
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=state),
    )

    architecture = json.loads(mcp_server.get_project_architecture.fn(
        repo_path=str(tmp_path), max_items=1, compact=False,
        fields=["action_items", "top_global_hotspots"],
    ))
    assert architecture["action_items"]["available"] is False
    assert architecture["top_global_hotspots"]["available"] is False

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

    result = _static_test_reachability(
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
        report_helpers, "get_canonical_report", lambda _root, name: reports.get(name)
    )
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: ({}, {}, {}, {}))

    result = mcp_server.get_file_edit_context.fn(
        repo_path=str(repo), file_path="missing.py"
    )

    assert "No usable canonical LIVE state" in result


def test_artifact_blast_radius_does_not_fallback_to_compact_report(
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
    monkeypatch.setattr(report_helpers, "get_canonical_report", lambda *_: report)
    monkeypatch.setattr(query_helpers, "read_registries",
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

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)

    result = mcp_server.get_artifact_blast_radius.fn(
        repo_path=str(tmp_path), artifact_name="target", max_items=0
    )

    assert "No usable canonical LIVE state" in result


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
    mcp_runtime._live_engine_revisions[str(root)] = 42
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(query_helpers, "read_registries",
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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(query_helpers, "read_registries",
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
            artifact_consumption={
                "pkg.module::hello": {"consumers": ["consumer.mod"], "channels": {}},
                "pkg.module::WorldClass": {"consumers": [], "channels": {}},
                "pkg.module::WorldClass.analyze": {"consumers": [], "channels": {}},
                "pkg.module::WorldClass._add_row": {"consumers": [], "channels": {}},
                "pkg.module::WorldClass.__init__": {"consumers": [], "channels": {}},
            },
            artifact_consumption_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(query_helpers, "read_registries",
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
    mcp_runtime._live_engine_revisions.clear()
    mcp_runtime._live_engines.clear()

    # 1. Hydrated metadata revision -> minimal pre-edit returns exact persisted revision
    monkeypatch.setattr(core_live_state, "connect", lambda _r: None)
    monkeypatch.setattr(core_repo_id, "read_repository_identity", lambda r: SimpleNamespace(repo_id=f"id_{r.name}", root_path=str(r)))
    monkeypatch.setattr(core_live_state, "migrate_legacy_snapshot", lambda r: str(r / ".contextor"))
    monkeypatch.setattr(core_live_state, "read_metadata", lambda _c: LiveStateMetadata(revision=366, state_id="s366"))
    monkeypatch.setattr(core_state_mgr, "load_engine_state", lambda _c, _sid, **_kw: engine1.state)
    monkeypatch.setattr(query_helpers, "read_registries", lambda _r: ({"r1.mod": "1/1"}, {"1/1": "r1.mod"}, {}, {}))

    res1 = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root1),
            target="r1.mod",
            mode="minimal",
        )
    )
    assert res1["live_revision"] == 366
    assert mcp_runtime._live_engine_revisions[str(root1)] == 366

    # 2. No metadata / revision -> null
    mcp_runtime._live_engine_revisions.clear()
    mcp_runtime._live_engines.clear()
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
    mcp_runtime._live_engine_revisions[str(root1)] = 367
    res_active = json.loads(
        mcp_server.get_file_edit_context.fn(
            repo_path=str(root1),
            target="r1.mod",
            mode="minimal",
        )
    )
    assert res_active["live_revision"] == 367

    # 4. Hydration does not increment revision
    assert mcp_runtime._live_engine_revisions[str(root1)] == 367

    # 5. Two repo roots retain independent revision values
    monkeypatch.setattr(core_live_state, "read_metadata", lambda c: LiveStateMetadata(revision=500, state_id="s500") if "repo2" in str(c) else LiveStateMetadata(revision=366, state_id="s366"))
    monkeypatch.setattr(core_state_mgr, "load_engine_state", lambda c, _sid, **_kw: engine2.state if "repo2" in str(c) else engine1.state)
    monkeypatch.setattr(query_helpers, "read_registries", lambda r: ({"r2.mod": "2/1"}, {"2/1": "r2.mod"}, {}, {}) if "repo2" in str(r) else ({"r1.mod": "1/1"}, {"1/1": "r1.mod"}, {}, {}))

    mcp_runtime._live_engine_revisions.clear()
    mcp_runtime._live_engines.clear()

    res_r1 = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root1), target="r1.mod", mode="minimal"))
    res_r2 = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root2), target="r2.mod", mode="minimal"))
    assert res_r1["live_revision"] == 366
    assert res_r2["live_revision"] == 500
    assert mcp_runtime._live_engine_revisions[str(root1)] == 366
    assert mcp_runtime._live_engine_revisions[str(root2)] == 500

    # 6. Rejected / invalid hydration does not publish invalid revision
    mcp_runtime._live_engine_revisions[str(root1)] = 999
    monkeypatch.setattr(core_state_mgr, "load_engine_state", lambda _c, _sid, **_kw: None)
    mcp_runtime._live_engines.clear()
    engine_rejected = mcp_runtime.get_or_init_engine(root1)
    assert engine_rejected is None
    assert str(root1) not in mcp_runtime._live_engine_revisions

    # 7. Legacy get_file_edit_context contract unchanged
    monkeypatch.setattr(core_state_mgr, "load_engine_state", lambda _c, _sid, **_kw: engine1.state)
    mcp_runtime._live_engine_revisions[str(root1)] = 366
    legacy_res = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root1), file_path="r1/mod.py"))
    assert "public_api" in legacy_res
    assert "live_revision" not in legacy_res


def test_file_edit_context_layer_guard(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    from types import SimpleNamespace
    empty_graph = SimpleNamespace(hard_edges={}, soft_edges={})

    # Mock registries
    monkeypatch.setattr(query_helpers, "read_registries",
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
            dependency_graph=empty_graph,
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_fresh_clean)

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
            dependency_graph=empty_graph,
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_with_v)

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
            dependency_graph=empty_graph,
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_inbound_core)
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
            dependency_graph=empty_graph,
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_deferred)
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
            dependency_graph=empty_graph,
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_stale)
    res_stale = json.loads(mcp_server.get_file_edit_context.fn(repo_path=str(root), target="pkg.ui_mod", mode="minimal"))
    assert res_stale["layer_guard"]["available"] is False
    assert "stale" in res_stale["layer_guard"]["reason"]


def test_artifact_blast_radius_architecture_projection(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    from types import SimpleNamespace

    monkeypatch.setattr(query_helpers, "read_registries",
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
            artifact_consumption={
                "pkg.core::func_clean": {"consumers": ["pkg.core", "pkg.same_layer"], "channels": {}},
                "pkg.core::func_mixed": {"consumers": ["pkg.core", "pkg.cross_cli", "pkg.cross_ui", "pkg.same_layer", "pkg.unclassified", "tests.test_pkg"], "channels": {}},
                "pkg.core::func_duplicate": {"consumers": ["pkg.core", "pkg.cross_ui", "tests.test_pkg"], "channels": {}},
                "pkg.core::func_test_only": {"consumers": ["tests.test_pkg"], "channels": {}},
            },
            artifact_consumption_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_fresh)

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
            artifact_consumption=engine_fresh.state.artifact_consumption,
            artifact_consumption_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_no_definer_layer)
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
            artifact_consumption=engine_fresh.state.artifact_consumption,
            artifact_consumption_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_deferred)
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

    monkeypatch.setattr(query_helpers, "read_registries",
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
            artifact_consumption={
                "pkg.definer::sym_zero": {"consumers": [], "channels": {}},
                "pkg.definer::sym_chain": {"consumers": ["pkg.direct_a"], "channels": {}},
                "pkg.definer::sym_self": {"consumers": ["pkg.definer"], "channels": {}},
            },
            artifact_consumption_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_fresh)

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
            artifact_consumption=engine_fresh.state.artifact_consumption,
            artifact_consumption_state="fresh",
        )
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_stale)
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
    monkeypatch.setattr(report_helpers, "get_canonical_report", lambda _root, _name: report)

    monkeypatch.setattr(query_helpers, "read_registries",
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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_fresh)

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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_stale)
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
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine_deferred)
    res_def = json.loads(mcp_server.get_module_context.fn(repo_path=str(root), module_name="pkg.mod_a"))
    metrics_def = res_def["metrics"]
    assert metrics_def["fan_in"] == 1
    assert metrics_def["fan_out"] == 1
    assert "pagerank" not in metrics_def
    assert res_def["metrics_source"] == "deferred_topology_analytics"
    assert res_def["degree_metrics_source"] == "live_canonical_graph"

    # 4. Engine absent -> fail closed without report fallback.
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: None)
    res_report = mcp_server.get_module_context.fn(
        repo_path=str(root), module_name="pkg.mod_a"
    )
    assert "No usable canonical LIVE state" in res_report


def test_blast_radius_consumer_representation_and_progressive_disclosure(
    tmp_path, monkeypatch
):
    import inspect
    from types import SimpleNamespace
    from contextor.mcp.tools import get_artifact_blast_radius as blast_tool

    # A. Public signature preserves existing args, representation is last with default "named"
    sig = inspect.signature(blast_tool.get_artifact_blast_radius)
    param_names = list(sig.parameters.keys())
    assert param_names == ["repo_path", "artifact_name", "max_items", "compact", "fields", "representation", "artifact"]
    assert sig.parameters["representation"].default == "named"

    # Setup state with 15 consumers for pkg.core::target_func
    consumer_names = [f"pkg.consumer_{i:02d}" for i in range(1, 16)]
    mod_path_to_id = {f"pkg.consumer_{i:02d}": f"{100+i}/1" for i in range(1, 16)}
    mod_path_to_id["pkg.core"] = "1/1"
    mod_id_to_path = {v: k for k, v in mod_path_to_id.items()}
    art_path_to_id = {"pkg.core::target_func": "A100/1"}
    art_id_to_path = {"A100/1": "pkg.core::target_func"}

    state = SimpleNamespace(
        artifacts={
            "pkg.core": {
                "symbols": {"functions": ["target_func"]},
                "own_symbols": ["target_func"],
            }
        },
        artifact_consumption={
            "pkg.core::target_func": {
                "consumers": consumer_names,
                "channels": {},
            }
        },
        artifact_consumption_state="fresh",
        cached_analytics={},
        cached_analytics_state="deferred",
        resync_required=False,
    )
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )

    # B. Default compact named: max 3 evidence, truthful truncated, named-preserving expand
    res_b = json.loads(
        blast_tool.get_artifact_blast_radius(str(tmp_path), "pkg.core::target_func")
    )
    c_b = res_b["consumers"]
    assert c_b["total"] == 15
    assert c_b["truncated"] is True
    assert len(c_b["evidence"]) == 3
    assert c_b["evidence"] == consumer_names[:3]
    assert c_b["expand"] == {"compact": False, "max_items": None, "representation": "named"}
    assert "items" not in c_b

    # C. Compact max_items=1, 0, None
    res_c1 = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, max_items=1
        )
    )["consumers"]
    assert len(res_c1["evidence"]) == 1
    assert res_c1["truncated"] is True

    res_c0 = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, max_items=0
        )
    )["consumers"]
    assert len(res_c0["evidence"]) == 0
    assert res_c0["truncated"] is True

    res_cn = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, max_items=None
        )
    )["consumers"]
    assert len(res_cn["evidence"]) == 3
    assert res_cn["truncated"] is True

    # D. Compact indexed: ID evidence + metadata + indexed-preserving expand
    res_d = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, representation="indexed"
        )
    )["consumers"]
    assert res_d["representation"] == "indexed"
    assert res_d["index_kind"] == "module"
    assert res_d["resolve_via"] == "lookup_index_entries"
    assert res_d["total"] == 15
    assert res_d["truncated"] is True
    assert res_d["evidence"] == ["101/1", "102/1", "103/1"]
    assert res_d["expand"] == {"compact": False, "max_items": None, "representation": "indexed"}

    # E. Compact indexed missing mapping -> structured fail-closed
    incomplete_mod_path_to_id = dict(mod_path_to_id)
    del incomplete_mod_path_to_id["pkg.consumer_02"]
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (incomplete_mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )
    res_e = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, representation="indexed"
        )
    )
    assert "error" in res_e
    assert res_e["missing_modules"] == ["pkg.consumer_02"]
    assert res_e["suggested_action"] == "Use representation='named' or re-run analysis."

    # Restore complete mapping
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )

    # F. Compact auto -> direct named evidence, requested auto, zero decision
    res_f = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, representation="auto"
        )
    )["consumers"]
    assert res_f["representation"] == "named"
    assert res_f["requested_representation"] == "auto"
    assert len(res_f["evidence"]) == 3
    assert res_f["evidence"] == consumer_names[:3]
    assert res_f["truncated"] is True
    assert res_f["expand"] == {"compact": False, "max_items": None, "representation": "auto"}
    assert "status" not in res_f

    # G. Full bounded named -> existing items semantics + truthful expand
    res_g = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=5, representation="named"
        )
    )["consumers"]
    assert res_g["total"] == 15
    assert res_g["truncated"] is True
    assert res_g["items"] == consumer_names[:5]
    assert res_g["expand"] == {"compact": False, "max_items": None, "representation": "named"}

    # H. Full lossless named -> all names, truncated false, no expand
    res_h = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=None, representation="named"
        )
    )["consumers"]
    assert res_h["total"] == 15
    assert res_h["truncated"] is False
    assert res_h["items"] == consumer_names
    assert "expand" not in res_h

    # I. Full bounded indexed -> same selected semantic identities as named after resolving IDs
    res_i = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=5, representation="indexed"
        )
    )["consumers"]
    assert res_i["representation"] == "indexed"
    assert res_i["items"] == [f"{100+i}/1" for i in range(1, 6)]
    assert res_i["total"] == 15
    assert res_i["truncated"] is True
    assert res_i["expand"] == {"compact": False, "max_items": None, "representation": "indexed"}

    # J. Full lossless indexed -> all IDs, truncated false
    res_j = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=None, representation="indexed"
        )
    )["consumers"]
    assert res_j["representation"] == "indexed"
    assert res_j["items"] == [f"{100+i}/1" for i in range(1, 16)]
    assert res_j["total"] == 15
    assert res_j["truncated"] is False
    assert "expand" not in res_j

    # K. Full auto incomplete mapping -> named fallback, no mixed identities
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (incomplete_mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )
    res_k = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=5, representation="auto"
        )
    )["consumers"]
    assert res_k["representation"] == "named"
    assert res_k["requested_representation"] == "auto"
    assert res_k["indexed_representation_available"] is False
    assert res_k["reason"] == "missing_module_ids"
    assert res_k["items"] == consumer_names[:5]
    assert res_k["truncated"] is True

    # Restore complete mapping
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )

    # L. Full auto below threshold -> direct named
    # With default 512 B threshold, synthetic short names have saving < 512 B -> direct named
    res_l = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=None, representation="auto"
        )
    )["consumers"]
    assert res_l["representation"] == "named"
    assert res_l["requested_representation"] == "auto"
    assert res_l["items"] == consumer_names
    assert "status" not in res_l
    assert "sizes" not in res_l

    # M. Full auto above threshold -> exact decision_required union
    # Lower threshold to trigger decision branch deterministically with short synthetic names
    monkeypatch.setattr(blast_tool, "_AUTO_NEGOTIATION_MIN_BYTES_SAVED", 5)
    res_m = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=None, representation="auto"
        )
    )["consumers"]
    assert res_m["status"] == "representation_decision_required"
    assert res_m["requested_representation"] == "auto"
    assert res_m["total"] == 15
    assert res_m["decision_scope_count"] == 15
    assert len(res_m["evidence"]) == 3
    assert res_m["evidence"] == consumer_names[:3]
    assert res_m["truncated"] is True  # 15 > 3
    assert "items" not in res_m

    # Exact final-shape candidate calculation for full scope
    named_candidate_m = {
        "total": 15,
        "truncated": False,
        "items": consumer_names,
    }
    indexed_candidate_m = {
        "representation": "indexed",
        "index_kind": "module",
        "resolve_via": "lookup_index_entries",
        "total": 15,
        "truncated": False,
        "items": [f"{100+i}/1" for i in range(1, 16)],
    }
    expected_named_bytes_m = len(json.dumps(named_candidate_m, indent=2, ensure_ascii=False).encode("utf-8"))
    expected_indexed_bytes_m = len(json.dumps(indexed_candidate_m, indent=2, ensure_ascii=False).encode("utf-8"))
    expected_bytes_saved_m = expected_named_bytes_m - expected_indexed_bytes_m
    expected_percent_saved_m = round((expected_bytes_saved_m / expected_named_bytes_m) * 100, 1)

    assert res_m["sizes"] == {
        "named_bytes": expected_named_bytes_m,
        "indexed_bytes": expected_indexed_bytes_m,
        "bytes_saved": expected_bytes_saved_m,
        "percent_saved": expected_percent_saved_m,
    }
    assert "named" in res_m["options"]
    assert "indexed" in res_m["options"]
    assert "bounded_named" in res_m["options"]
    assert res_m["options"]["named"] == {"representation": "named", "compact": False, "max_items": None}
    assert res_m["options"]["indexed"] == {"representation": "indexed", "compact": False, "max_items": None}
    assert res_m["options"]["bounded_named"] == {"representation": "named", "compact": False, "max_items": 10}

    # Direct execution of retry descriptor kwargs gives exact lossless indexed result
    indexed_retry_kwargs_m = res_m["options"]["indexed"]
    retry_result_m = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path),
            "pkg.core::target_func",
            **indexed_retry_kwargs_m,
        )
    )
    assert retry_result_m["consumers"] == res_j

    # N. Decision full scope -> no expand
    assert "expand" not in res_m

    # O. Decision bounded scope (max_items=12 < total=15) -> expand present to full auto
    res_o = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=12, representation="auto"
        )
    )["consumers"]
    assert res_o["status"] == "representation_decision_required"
    assert res_o["decision_scope_count"] == 12
    assert res_o["expand"] == {"compact": False, "max_items": None, "representation": "auto"}
    assert "bounded_named" in res_o["options"]
    assert res_o["options"]["indexed"] == {"representation": "indexed", "compact": False, "max_items": 12}

    # Direct execution of bounded retry descriptor kwargs gives exact bounded indexed result
    indexed_retry_kwargs_o = res_o["options"]["indexed"]
    retry_result_o = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path),
            "pkg.core::target_func",
            **indexed_retry_kwargs_o,
        )
    )
    expected_bounded_indexed_o = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path),
            "pkg.core::target_func",
            compact=False,
            max_items=12,
            representation="indexed",
        )
    )["consumers"]
    assert retry_result_o["consumers"] == expected_bounded_indexed_o

    # Exact final-shape candidate calculation for bounded scope including expand
    named_candidate_o = {
        "total": 15,
        "truncated": True,
        "items": consumer_names[:12],
        "expand": {"compact": False, "max_items": None, "representation": "named"},
    }
    indexed_candidate_o = {
        "representation": "indexed",
        "index_kind": "module",
        "resolve_via": "lookup_index_entries",
        "total": 15,
        "truncated": True,
        "items": [f"{100+i}/1" for i in range(1, 13)],
        "expand": {"compact": False, "max_items": None, "representation": "indexed"},
    }
    expected_named_bytes_o = len(json.dumps(named_candidate_o, indent=2, ensure_ascii=False).encode("utf-8"))
    expected_indexed_bytes_o = len(json.dumps(indexed_candidate_o, indent=2, ensure_ascii=False).encode("utf-8"))
    expected_bytes_saved_o = expected_named_bytes_o - expected_indexed_bytes_o
    expected_percent_saved_o = round((expected_bytes_saved_o / expected_named_bytes_o) * 100, 1)

    assert res_o["sizes"] == {
        "named_bytes": expected_named_bytes_o,
        "indexed_bytes": expected_indexed_bytes_o,
        "bytes_saved": expected_bytes_saved_o,
        "percent_saved": expected_percent_saved_o,
    }

    # P. bounded_named option only when decision_scope_count > 10
    monkeypatch.setattr(blast_tool, "_AUTO_NEGOTIATION_MIN_BYTES_SAVED", -50)
    res_p = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=8, representation="auto"
        )
    )["consumers"]
    assert res_p["status"] == "representation_decision_required"
    assert res_p["decision_scope_count"] == 8
    assert "bounded_named" not in res_p["options"]

    # Q. Invalid representation deterministic error
    res_q = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", representation="xml"
        )
    )
    assert res_q["error"] == "Unsupported representation for get_artifact_blast_radius"
    assert res_q["representation"] == "xml"
    assert res_q["allowed_representations"] == ["auto", "indexed", "named"]

    # R. Fields excluding consumers does not trigger decision/sizing and preserves projection
    res_r = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=None, representation="auto", fields=["artifact", "kind"]
        )
    )
    assert set(res_r.keys()) == {"artifact", "kind"}
    assert res_r["artifact"] == "pkg.core::target_func"
    assert res_r["kind"] == "function"

    # S. Compact expand preserves fields
    res_s_named = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, fields=["consumers"]
        )
    )["consumers"]
    assert res_s_named["expand"] == {
        "compact": False,
        "max_items": None,
        "representation": "named",
        "fields": ["consumers"],
    }

    res_s_indexed = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, representation="indexed", fields=["consumers"]
        )
    )["consumers"]
    assert res_s_indexed["expand"] == {
        "compact": False,
        "max_items": None,
        "representation": "indexed",
        "fields": ["consumers"],
    }

    res_s_auto = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=True, representation="auto", fields=["consumers"]
        )
    )["consumers"]
    assert res_s_auto["expand"] == {
        "compact": False,
        "max_items": None,
        "representation": "auto",
        "fields": ["consumers"],
    }

    # T. Decision options preserve consumers-only projection
    monkeypatch.setattr(blast_tool, "_AUTO_NEGOTIATION_MIN_BYTES_SAVED", 5)
    res_t = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=None, representation="auto", fields=["consumers"]
        )
    )
    assert set(res_t.keys()) == {"consumers"}
    c_t = res_t["consumers"]
    assert c_t["status"] == "representation_decision_required"
    assert c_t["options"]["named"]["fields"] == ["consumers"]
    assert c_t["options"]["indexed"]["fields"] == ["consumers"]
    assert c_t["options"]["bounded_named"]["fields"] == ["consumers"]

    # Execute options.indexed directly
    retry_t = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path),
            "pkg.core::target_func",
            **c_t["options"]["indexed"],
        )
    )
    assert set(retry_t.keys()) == {"consumers"}
    expected_explicit_t = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path),
            "pkg.core::target_func",
            compact=False,
            max_items=None,
            representation="indexed",
            fields=["consumers"],
        )
    )
    assert retry_t == expected_explicit_t

    # U. Multi-field projection preserved in retry descriptor
    res_u = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=None, representation="auto", fields=["artifact", "consumers"]
        )
    )
    assert set(res_u.keys()) == {"artifact", "consumers"}
    assert res_u["artifact"] == "pkg.core::target_func"
    c_u = res_u["consumers"]
    assert c_u["options"]["named"]["fields"] == ["artifact", "consumers"]
    assert c_u["options"]["indexed"]["fields"] == ["artifact", "consumers"]
    assert c_u["options"]["bounded_named"]["fields"] == ["artifact", "consumers"]

    retry_u = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path),
            "pkg.core::target_func",
            **c_u["options"]["indexed"],
        )
    )
    assert set(retry_u.keys()) == {"artifact", "consumers"}
    assert retry_u["artifact"] == "pkg.core::target_func"
    assert retry_u["consumers"] == res_j

    # V. Bounded expand + exact sizing with fields
    res_v = json.loads(
        blast_tool.get_artifact_blast_radius(
            str(tmp_path), "pkg.core::target_func", compact=False, max_items=12, representation="auto", fields=["consumers"]
        )
    )["consumers"]
    assert res_v["status"] == "representation_decision_required"
    assert res_v["decision_scope_count"] == 12
    assert res_v["expand"] == {
        "compact": False,
        "max_items": None,
        "representation": "auto",
        "fields": ["consumers"],
    }
    assert res_v["options"]["named"]["fields"] == ["consumers"]
    assert res_v["options"]["indexed"]["fields"] == ["consumers"]
    assert res_v["options"]["bounded_named"]["fields"] == ["consumers"]

    # Exact candidate sizing with fields in expand
    named_candidate_v = {
        "total": 15,
        "truncated": True,
        "items": consumer_names[:12],
        "expand": {
            "compact": False,
            "max_items": None,
            "representation": "named",
            "fields": ["consumers"],
        },
    }
    indexed_candidate_v = {
        "representation": "indexed",
        "index_kind": "module",
        "resolve_via": "lookup_index_entries",
        "total": 15,
        "truncated": True,
        "items": [f"{100+i}/1" for i in range(1, 13)],
        "expand": {
            "compact": False,
            "max_items": None,
            "representation": "indexed",
            "fields": ["consumers"],
        },
    }
    expected_named_bytes_v = len(json.dumps(named_candidate_v, indent=2, ensure_ascii=False).encode("utf-8"))
    expected_indexed_bytes_v = len(json.dumps(indexed_candidate_v, indent=2, ensure_ascii=False).encode("utf-8"))
    expected_bytes_saved_v = expected_named_bytes_v - expected_indexed_bytes_v
    expected_percent_saved_v = round((expected_bytes_saved_v / expected_named_bytes_v) * 100, 1)

    assert res_v["sizes"] == {
        "named_bytes": expected_named_bytes_v,
        "indexed_bytes": expected_indexed_bytes_v,
        "bytes_saved": expected_bytes_saved_v,
        "percent_saved": expected_percent_saved_v,
    }


def test_get_artifacts_for_module_representation_and_progressive_disclosure(
    tmp_path, monkeypatch
):
    from contextor.mcp.tools import get_artifacts_for_module as gam_tool
    from contextor.mcp.tools import get_artifact_blast_radius as blast_tool
    from contextor.mcp import representation as mcp_rep
    import inspect

    # 1. Signature check: representation is last parameter, default 'named'
    sig = inspect.signature(gam_tool.get_artifacts_for_module)
    params = list(sig.parameters.values())
    assert params[-1].name == "representation"
    assert params[-1].default == "named"

    # Unsupported representation error
    unsupported = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", representation="xml")
    )
    assert unsupported == {
        "error": "Unsupported representation for get_artifacts_for_module",
        "representation": "xml",
        "allowed_representations": ["auto", "indexed", "named"],
    }

    # Setup state with 15 symbols and consumer relationships
    # Symbols: s01..s15
    # s01..s05 have high fan-in (consumers: mod_01..mod_20)
    # s06..s15 have 0 consumers
    symbols_list = [f"s{i:02d}" for i in range(1, 16)]
    consumer_map = {}
    for i in range(1, 6):
        sym = f"s{i:02d}"
        consumer_map[f"pkg.core::{sym}"] = [f"consumer.pkg_{j:02d}" for j in range(1, 10 + i * 2 + 1)]
    for i in range(6, 16):
        sym = f"s{i:02d}"
        consumer_map[f"pkg.core::{sym}"] = []

    signatures_dict = {s: f"def {s}() -> None" for s in symbols_list}

    state = RepositoryAnalysisState(
        modules={"pkg.core": SimpleNamespace(module_id="10/1", path="pkg/core.py")},
        artifacts={
            "pkg.core": {
                "own_symbols": symbols_list,
                "symbols": {
                    "functions": symbols_list,
                    "signatures": signatures_dict,
                },
            }
        },
        artifact_consumption={
            k: {"consumers": v, "channels": {}} for k, v in consumer_map.items()
        },
        artifact_consumption_state="fresh",
    )

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))

    # Registries: all consumers have module IDs 101/1..130/1
    mod_path_to_id = {"pkg.core": "10/1"}
    mod_id_to_path = {"10/1": "pkg.core"}
    for j in range(1, 30):
        c_name = f"consumer.pkg_{j:02d}"
        c_id = f"{100+j}/1"
        mod_path_to_id[c_name] = c_id
        mod_id_to_path[c_id] = c_name

    art_path_to_id = {}
    art_id_to_path = {}
    for idx, s in enumerate(symbols_list, 1):
        full = f"pkg.core::{s}"
        aid = f"A{idx}/1"
        art_path_to_id[full] = aid
        art_id_to_path[aid] = full

    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path),
    )

    # 2. Compact limits (0, 1, 5, 10, 50, None) and evidence_limits (0, 1, 3, 20, None)
    # Default compact (limit=50, evidence_limit=20): capped at 10 salience items, 3 evidence items each
    res_default = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core")
    )
    assert res_default["artifact_count"] == 10
    assert res_default["total_artifact_count"] == 15
    assert res_default["truncated"] is True
    assert "expand" in res_default
    assert res_default["expand"] == {
        "compact": False,
        "limit": 50,
        "evidence_limit": 20,
        "include_consumers": True,
        "symbol_filter": "",
        "representation": "named",
    }
    # 5. Salience ordering: top 5 high-fan-in symbols (s05, s04, s03, s02, s01) are in first 5 slots!
    selected_keys = list(res_default["artifacts"].keys())
    assert [res_default["artifacts"][k]["symbol"] for k in selected_keys[:5]] == ["s05", "s04", "s03", "s02", "s01"]
    # 4. Nested truthful truncation and max 3 evidence
    art_s05 = res_default["artifacts"]["A5/1"]
    assert art_s05["consumers"]["total"] == 20
    assert art_s05["consumers"]["truncated"] is True
    assert len(art_s05["consumers"]["evidence"]) == 3

    # compact limit=0
    res_lim0 = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", limit=0))
    assert res_lim0["artifact_count"] == 0
    assert res_lim0["truncated"] is True
    assert "expand" not in res_lim0  # requested 0, returned 0 -> presentation_truncated=False

    # compact limit=1
    res_lim1 = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", limit=1))
    assert res_lim1["artifact_count"] == 1
    assert "expand" not in res_lim1  # requested 1, returned 1 -> presentation_truncated=False

    # compact limit=5
    res_lim5 = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", limit=5))
    assert res_lim5["artifact_count"] == 5
    assert "expand" not in res_lim5  # requested 5, returned 5 -> presentation_truncated=False

    # compact limit=None
    res_lim_none = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", limit=None))
    assert res_lim_none["artifact_count"] == 10
    assert res_lim_none["expand"]["limit"] is None

    # evidence_limit=0
    res_ev0 = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", evidence_limit=0))
    assert res_ev0["artifacts"]["A5/1"]["consumers"] == {"total": 20, "truncated": True, "evidence": []}

    # 6. include_consumers=False: alphabetical + zero consumer lookup
    lookup_calls = []
    real_consumers = query_helpers.canonical_symbol_consumers
    def tracked_consumers(*args):
        lookup_calls.append(args)
        return real_consumers(*args)
    monkeypatch.setattr(query_helpers, "canonical_symbol_consumers", tracked_consumers)

    res_no_cons = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", include_consumers=False)
    )
    assert len(lookup_calls) == 0
    # Alphabetical order: s01..s10
    assert [item["symbol"] for item in res_no_cons["artifacts"].values()] == [f"s{i:02d}" for i in range(1, 11)]

    # 7. symbol_filter before total/ranking
    res_filtered = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", symbol_filter="s05")
    )
    assert res_filtered["total_artifact_count"] == 1
    assert res_filtered["artifact_count"] == 1
    assert res_filtered["truncated"] is False
    assert "expand" not in res_filtered

    # 8. Presentation-truncated expand eligibility cases A-E:
    # Case A: total=15, compact=True, limit=50 -> artifact_count=10, expand present
    res_a = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=True, limit=50))
    assert res_a["artifact_count"] == 10 and res_a["truncated"] is True and "expand" in res_a
    # Case B: total=15, compact=True, limit=None -> artifact_count=10, expand present
    res_b = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=True, limit=None))
    assert res_b["artifact_count"] == 10 and res_b["truncated"] is True and "expand" in res_b
    # Case C: total=15, compact=True, limit=5 -> artifact_count=5, truncated=True, NO expand
    res_c = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=True, limit=5))
    assert res_c["artifact_count"] == 5 and res_c["truncated"] is True and "expand" not in res_c
    # Case D: total=15, compact=False, limit=5 -> artifact_count=5, truncated=True, NO expand
    res_d = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=False, limit=5))
    assert res_d["artifact_count"] == 5 and res_d["truncated"] is True and "expand" not in res_d
    # Case E: total=2 (small module), compact=True, limit=50 -> artifact_count=2, truncated=False, NO expand
    state_small = RepositoryAnalysisState(
        modules={"pkg.small": SimpleNamespace(module_id="20/1", path="pkg/small.py")},
        artifacts={"pkg.small": {"symbols": {"functions": ["f1", "f2"]}}},
        artifact_consumption={"pkg.small::f1": {"consumers": [], "channels": {}}, "pkg.small::f2": {"consumers": [], "channels": {}}},
        artifact_consumption_state="fresh",
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state_small))
    res_e = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.small", compact=True, limit=50))
    assert res_e["artifact_count"] == 2 and res_e["truncated"] is False and "expand" not in res_e

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))

    # 9. Direct executable expand
    expanded = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", **res_a["expand"])
    )
    assert expanded["artifact_count"] == 15
    assert expanded["truncated"] is False

    # 10. Lossless named
    res_lossless_named = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=False, limit=None, evidence_limit=None, representation="named")
    )
    assert res_lossless_named["artifact_count"] == 15
    assert "consumer_representation" not in res_lossless_named
    assert res_lossless_named["artifacts"]["A5/1"]["consumers"]["items"] == consumer_map["pkg.core::s05"]

    # 11. Lossless indexed + 12. M2 consumer_representation metadata
    res_lossless_indexed = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=False, limit=None, evidence_limit=None, representation="indexed")
    )
    assert res_lossless_indexed["consumer_representation"] == {
        "representation": "indexed",
        "index_kind": "module",
        "resolve_via": "lookup_index_entries",
    }
    assert res_lossless_indexed["artifacts"]["A5/1"]["consumers"]["items"] == [
        mod_path_to_id[m] for m in consumer_map["pkg.core::s05"]
    ]

    # 13. Zero-consumer indexed/auto no-op: no metadata
    state_zero_cons = RepositoryAnalysisState(
        modules={"pkg.zero": SimpleNamespace(module_id="30/1", path="pkg/zero.py")},
        artifacts={"pkg.zero": {"symbols": {"functions": ["z1", "z2"]}}},
        artifact_consumption={"pkg.zero::z1": {"consumers": [], "channels": {}}, "pkg.zero::z2": {"consumers": [], "channels": {}}},
        artifact_consumption_state="fresh",
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state_zero_cons))
    res_zero_idx = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.zero", compact=False, representation="indexed"))
    assert "consumer_representation" not in res_zero_idx
    res_zero_auto = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.zero", compact=False, representation="auto"))
    assert "consumer_representation" not in res_zero_auto

    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))

    # 14. Selected-scope-only missing mapping & 15. Missing mapping outside scope does not fail & 16. Exact missing-ID error shape
    # Remove mapping for consumer.pkg_19 (only in s05, which is outside limit=1 for symbol s01)
    mod_path_incomplete = dict(mod_path_to_id)
    del mod_path_incomplete["consumer.pkg_19"]
    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: (mod_path_incomplete, mod_id_to_path, art_path_to_id, art_id_to_path))

    # Query s01 (does not contain consumer.pkg_19) -> succeeds!
    res_s01 = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", symbol_filter="s01", compact=False, representation="indexed"))
    assert "consumer_representation" in res_s01

    # Query s05 (contains consumer.pkg_19) -> exact error shape!
    res_s05_err = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", symbol_filter="s05", compact=False, representation="indexed"))
    assert res_s05_err == {
        "error": "Cannot fulfill indexed representation for get_artifacts_for_module",
        "reason": "missing_module_ids",
        "missing_module_names": ["consumer.pkg_19"],
        "representation": "indexed",
    }
    assert "missing_modules" not in res_s05_err
    assert "suggested_action" not in res_s05_err

    monkeypatch.setattr(query_helpers, "read_registries", lambda _root: (mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path))

    # 17. fields excluding artifacts zero artifact/signature/consumer shaping
    lookup_calls.clear()
    res_fields_mod = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", fields=["module", "module_id"], representation="auto")
    )
    assert res_fields_mod == {"module": "pkg.core", "module_id": "10/1"}
    assert len(lookup_calls) == 0

    # 18. Compact auto: zero byte sizing, returns named compact evidence
    res_compact_auto = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=True, representation="auto")
    )
    assert res_compact_auto["consumer_representation"] == {
        "representation": "named",
        "requested_representation": "auto",
    }
    assert res_compact_auto["artifacts"]["A5/1"]["consumers"]["evidence"] == consumer_map["pkg.core::s05"][:3]

    # 19. Full auto below-threshold direct named (small consumer payload)
    # Query with symbol_filter="s01" (total 12 consumers)
    res_below = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", symbol_filter="s01", compact=False, representation="auto")
    )
    assert res_below["consumer_representation"] == {
        "representation": "named",
        "requested_representation": "auto",
    }

    # 20. Full auto decision branch (15 symbols with large consumer payload, bytes_saved >= 512)
    # 21. Exact final candidate sizes & 22. Decision exact mandatory key set
    res_dec = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=False, limit=None, evidence_limit=None, representation="auto")
    )
    assert res_dec["status"] == "representation_decision_required"
    assert res_dec["requested_representation"] == "auto"
    assert res_dec["module"] == "pkg.core"
    assert res_dec["module_id"] == "10/1"
    assert res_dec["total_artifact_count"] == 15
    assert res_dec["decision_scope_count"] == 15
    assert res_dec["scope_truncated"] is False
    assert res_dec["truncated"] is True
    # 23. Evidence max 3 and exact salience symbols
    assert len(res_dec["evidence"]) == 3
    assert [item["symbol"] for item in res_dec["evidence"]] == ["s05", "s04", "s03"]
    # Key set verification (11 mandatory keys)
    assert set(res_dec.keys()) == {
        "status", "requested_representation", "module", "module_id",
        "total_artifact_count", "truncated", "decision_scope_count",
        "scope_truncated", "evidence", "sizes", "options",
    }
    assert "artifacts" not in res_dec
    assert "artifact_count" not in res_dec
    assert "expand" not in res_dec

    # Exact sizing calculations
    expected_named_cand = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=False, limit=None, evidence_limit=None, representation="named"))
    expected_indexed_cand = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=False, limit=None, evidence_limit=None, representation="indexed"))
    calc_sizes = mcp_rep.representation_size_stats(expected_named_cand, expected_indexed_cand)
    assert res_dec["sizes"] == calc_sizes
    assert res_dec["sizes"]["bytes_saved"] >= mcp_rep.AUTO_NEGOTIATION_MIN_BYTES_SAVED

    # 25. Options named / indexed exact executable kwargs & 26. bounded_named
    assert "named" in res_dec["options"]
    assert "indexed" in res_dec["options"]
    assert "bounded_named" in res_dec["options"]
    assert res_dec["options"]["bounded_named"]["limit"] == 10
    assert res_dec["options"]["bounded_named"]["evidence_limit"] == 5

    # Direct retry execution
    retry_named = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", **res_dec["options"]["named"]))
    assert retry_named["artifact_count"] == 15
    assert "consumer_representation" not in retry_named

    retry_indexed = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", **res_dec["options"]["indexed"]))
    assert retry_indexed["artifact_count"] == 15
    assert retry_indexed["consumer_representation"]["representation"] == "indexed"

    # 27. fields=["artifacts"] decision + direct retries
    res_dec_f = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=False, limit=None, evidence_limit=None, representation="auto", fields=["artifacts"])
    )
    assert res_dec_f["status"] == "representation_decision_required"
    assert res_dec_f["options"]["named"]["fields"] == ["artifacts"]
    assert res_dec_f["options"]["indexed"]["fields"] == ["artifacts"]

    retry_named_f = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", **res_dec_f["options"]["named"]))
    assert list(retry_named_f.keys()) == ["artifacts"]

    retry_indexed_f = json.loads(gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", **res_dec_f["options"]["indexed"]))
    assert set(retry_indexed_f.keys()) == {"artifacts", "consumer_representation"}

    # 28. fields=["artifacts"] compact protocol metadata preservation
    res_f_named_comp = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=True, limit=50, fields=["artifacts"], representation="named")
    )
    assert set(res_f_named_comp.keys()) == {"artifacts", "expand"}
    assert res_f_named_comp["expand"]["fields"] == ["artifacts"]

    res_f_idx_comp = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=True, limit=50, fields=["artifacts"], representation="indexed")
    )
    assert set(res_f_idx_comp.keys()) == {"artifacts", "expand", "consumer_representation"}
    assert res_f_idx_comp["expand"]["fields"] == ["artifacts"]

    res_f_bnd_comp = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", compact=True, limit=5, fields=["artifacts"], representation="named")
    )
    assert set(res_f_bnd_comp.keys()) == {"artifacts"}

    res_f_expanded = json.loads(
        gam_tool.get_artifacts_for_module(str(tmp_path), "pkg.core", **res_f_named_comp["expand"])
    )
    assert list(res_f_expanded.keys()) == ["artifacts"]
    assert len(res_f_expanded["artifacts"]) == 15

    # 29. Helper sizing used by get_artifacts_for_module confirmed via calc_sizes
    # 30. A3 blast-radius regression protection
    blast_res = json.loads(
        blast_tool.get_artifact_blast_radius(str(tmp_path), "pkg.core::s05", compact=False, max_items=None, representation="named")
    )
    assert blast_res["consumers"]["total"] == 20
    assert len(blast_res["consumers"]["items"]) == 20


