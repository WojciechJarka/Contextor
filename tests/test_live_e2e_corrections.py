import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers
from contextor.mcp.tools import (
    query_canonical_projection as query_canonical_projection_tool,
)
from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import (
    FileStateManager,
    RepositoryAnalysisState,
    load_engine_state,
    module_current_truth,
    save_engine_state,
)
from contextor.core.live_state import runtime as live_runtime
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)
from contextor.core import report_query
from contextor.core.report_query import IndexCatalog
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
)
from contextor.core.symbol_engine.indexer import index_repository


pytestmark = pytest.mark.live


@pytest.fixture
def authoritative_live_client(tmp_path, monkeypatch):
    from contextor.core.repository_identity import ensure_repository_identity

    # The analyzed repository is ``tmp_path``; runtime roots must be siblings
    # rather than children so RuntimeDomain containment checks remain active.
    monkeypatch.setenv(
        "CONTEXTOR_CACHE_DIR",
        str(tmp_path.parent / f"{tmp_path.name}-cache"),
    )
    monkeypatch.setenv(
        "CONTEXTOR_STATE_DIR",
        str(tmp_path.parent / f"{tmp_path.name}-state"),
    )
    ensure_repository_identity(tmp_path)

    client = live_runtime.connect_or_start(tmp_path)
    assert client is not None
    assert client.endpoint.runtime_domain_id
    assert client.endpoint.service_instance_id
    assert client.endpoint.lease_generation is not None
    assert client.endpoint.process_start_identity

    yield client

    try:
        client.request("shutdown")
    except (OSError, EOFError, ConnectionError):
        pass

    deadline = live_runtime.time.monotonic() + 5.0
    ep_file = live_runtime.endpoint_file(tmp_path)
    while ep_file.exists() and live_runtime.time.monotonic() < deadline:
        live_runtime.time.sleep(0.02)
    assert not ep_file.exists()


def _engine_for_file(tmp_path):
    source = tmp_path / "provider.py"
    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
    registry = PersistentIdentityRegistry(str(tmp_path))
    modules = index_repository(str(tmp_path)).modules
    artifacts, _ = collect_module_artifacts(modules, str(tmp_path))
    trie = build_trie(modules)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=artifacts,
        dependency_graph=build_graph(modules),
        trie=trie,
        package_root=detect_package_root(modules, trie),
    )
    manager = FileStateManager(str(tmp_path / ".state"))
    manager.update_state(str(source))
    return source, IncrementalAnalysisEngine(
        state, registry, manager, str(tmp_path)
    )


def _stale_mcp_state(tmp_path):
    module = SimpleNamespace(
        module_id="1/1",
        path="provider.py",
        absolute_path=str(tmp_path / "provider.py"),
        imports=[],
    )
    graph = SimpleNamespace(
        hard_edges={"provider": {"provider"}}, soft_edges={}
    )
    return RepositoryAnalysisState(
        modules={"provider": module},
        artifacts={
            "provider": {
                "own_symbols": ["helper"],
                "symbols": {
                    "functions": ["helper"],
                    "signatures": {"helper": "helper(value: int)"},
                },
            }
        },
        dependency_graph=graph,
        artifact_consumption={"provider::helper": {"consumers": [], "channels": {}}},
        artifact_consumption_state="fresh",
        module_parse_freshness={
            "provider": {
                "state": "stale",
                "error": "'(' was never closed",
                "line_number": 1,
                "column_number": 11,
            }
        },
    )


def test_syntax_error_marks_authoritative_last_known_good_and_recovery(tmp_path):
    source, engine = _engine_for_file(tmp_path)

    source.write_text("def helper(\n")
    failed = engine.update_file(str(source))

    assert failed.status == "SYNTAX_ERROR"
    assert module_current_truth(engine.state, "provider") == {
        "available": False,
        "state": "stale",
        "provenance": "last_known_good",
        "reason": "Current source could not be parsed; canonical facts are last-known-good.",
        "parse_failure": {
            "error": "'(' was never closed",
            "line_number": 1,
            "column_number": 11,
        },
    }
    assert "helper" in engine.state.artifacts["provider"]["own_symbols"]

    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
    recovered = engine.update_file(str(source))

    assert recovered.status == "RECOVERED"
    assert module_current_truth(engine.state, "provider") == {
        "available": True,
        "state": "fresh",
        "provenance": "current",
    }


def test_affected_mcp_queries_fail_closed_on_parse_stale_state(
    tmp_path, monkeypatch
):
    state = _stale_mcp_state(tmp_path)
    engine = SimpleNamespace(state=state)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(query_helpers, "read_registries",
        lambda _root: (
            {"provider": "1/1"},
            {"1/1": "provider"},
            {"provider::helper": "A1/1"},
            {"A1/1": "provider::helper"},
        ),
    )
    monkeypatch.setattr(
        report_query,
        "catalog_from_registry",
        lambda _root: IndexCatalog(
            modules={"1/1": "provider"},
            artifacts={"A1/1": "provider::helper"},
            module_paths={"provider": "provider.py"},
            recovered_modules={},
            recovered_artifacts={},
        ),
    )
    original_resolver = report_query.resolve_index_query
    monkeypatch.setattr(
        report_query,
        "resolve_index_query",
        lambda query, catalog, repo_root=None: (
            {
                "matches": [
                    {
                        "id": "1/1",
                        "name": "provider",
                        "kind": "module",
                    }
                ]
            }
            if query in {"provider", "provider.py"}
            else original_resolver(query, catalog, repo_root=repo_root)
        ),
    )

    calls = [
        ("module", lambda: mcp_server.get_module_context.fn(str(tmp_path), "provider")),
        ("file", lambda: mcp_server.get_file_edit_context.fn(
            str(tmp_path), "provider.py"
        )),
        ("minimal", lambda: mcp_server.get_file_edit_context.fn(
            str(tmp_path), target="provider", mode="minimal"
        )),
        ("artifacts", lambda: mcp_server.get_artifacts_for_module.fn(
            str(tmp_path), "provider"
        )),
        ("lookup", lambda: mcp_server.lookup_artifact_by_symbol.fn(
            str(tmp_path), "helper"
        )),
        ("blast", lambda: mcp_server.get_artifact_blast_radius.fn(
            str(tmp_path), "provider::helper"
        )),
    ]

    for name, call in calls:
        result = json.loads(call())
        assert result["status"] == "stale", (name, result)
        assert result["available"] is False
        assert result["provenance"] == "last_known_good"
        assert result["parse_failure"]["line_number"] == 1
        assert "live_canonical" not in json.dumps(result)


def test_canonical_projections_reject_stale_module_facts(tmp_path, monkeypatch):
    state = _stale_mcp_state(tmp_path)
    monkeypatch.setattr(
        mcp_runtime,
        "get_or_init_engine",
        lambda _root: SimpleNamespace(state=state),
    )
    base = {
        "schema_version": "1.0",
        "language_version": "1.0",
        "filters": [],
        "select": [],
        "limit": 20,
    }

    for root in ("modules", "artifacts", "dependencies"):
        result = json.loads(
            mcp_server.query_canonical_projection.fn(
                str(tmp_path), {**base, "root": root}
            )
        )
        assert result["status"] == "stale"
        assert result["available"] is False
        assert result["provenance"] == "last_known_good"


def test_minimal_valid_syntax_error_query_repair_query_flow(
    tmp_path, monkeypatch
):
    source, engine = _engine_for_file(tmp_path)
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
    monkeypatch.setattr(query_helpers, "read_registries",
        lambda _root: (
            {"provider": "1/1"},
            {"1/1": "provider"},
            {"provider::helper": "A1/1"},
            {"A1/1": "provider::helper"},
        ),
    )
    monkeypatch.setattr(
        report_query,
        "catalog_from_registry",
        lambda _root: IndexCatalog(
            modules={"1/1": "provider"},
            artifacts={"A1/1": "provider::helper"},
            module_paths={"provider": "provider.py"},
            recovered_modules={},
            recovered_artifacts={},
        ),
    )

    valid = json.loads(
        mcp_server.get_module_context.fn(str(tmp_path), "provider")
    )
    assert valid["dependency_data_source"] == "live_canonical_graph"

    source.write_text("def helper(\n")
    assert engine.update_file(str(source)).status == "SYNTAX_ERROR"
    stale = json.loads(
        mcp_server.get_module_context.fn(str(tmp_path), "provider")
    )
    assert stale["status"] == "stale"
    assert stale["provenance"] == "last_known_good"

    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
    assert engine.update_file(str(source)).status == "RECOVERED"
    recovered = json.loads(
        mcp_server.get_module_context.fn(str(tmp_path), "provider")
    )
    assert recovered["dependency_data_source"] == "live_canonical_graph"
    assert "status" not in recovered


def test_live_events_retries_same_owner_and_preserves_journal(
    tmp_path, monkeypatch, authoritative_live_client
):
    endpoint = authoritative_live_client.endpoint

    class Client:
        def __init__(self):
            self.endpoint = endpoint

        def get_events(self, after_revision=None, limit=20):
            return {
                "status": "ok",
                "revision": 42,
                "events": [{"revision": 42, "status": "UPDATED"}],
                "total": 1,
                "truncated": False,
            }

    attempts = iter([None, Client()])
    monkeypatch.setattr(
        live_runtime, "_verified_existing_client", lambda *_args, **_kwargs: next(attempts)
    )
    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: endpoint)
    monkeypatch.setattr(live_runtime.time, "sleep", lambda _delay: None)

    result = json.loads(mcp_server.get_live_events.fn(str(tmp_path)))

    assert result["status"] == "ok"
    assert result["revision"] == 42
    assert result["events"][0]["revision"] == 42


def test_live_events_distinguishes_transient_owner_from_absence(
    tmp_path, monkeypatch, authoritative_live_client
):
    endpoint = authoritative_live_client.endpoint
    monkeypatch.setattr(live_runtime, "_verified_existing_client", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(live_runtime.time, "sleep", lambda _delay: None)
    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: endpoint)
    monkeypatch.setattr(live_runtime, "_is_pid_alive", lambda _pid: True)

    transient = json.loads(mcp_server.get_live_events.fn(str(tmp_path)))
    assert transient["status"] == "transient_connection_failure"

    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: None)
    absent = json.loads(mcp_server.get_live_events.fn(str(tmp_path)))
    assert absent["status"] == "no_live_service"


def test_parse_freshness_survives_snapshot_hydration_and_recovers(tmp_path):
    source, engine = _engine_for_file(tmp_path)
    source.write_text("def helper(\n")
    assert engine.update_file(str(source)).status == "SYNTAX_ERROR"

    cache = tmp_path / "cache"
    assert save_engine_state(engine.state, str(cache), "state-1")
    loaded = load_engine_state(str(cache), "state-1")

    assert loaded is not None
    assert module_current_truth(loaded, "provider")["parse_failure"] == {
        "error": "'(' was never closed",
        "line_number": 1,
        "column_number": 11,
    }

    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
    hydrated_engine = IncrementalAnalysisEngine(
        loaded, engine.registry, engine.state_manager, str(tmp_path)
    )
    assert hydrated_engine.update_file(str(source)).status == "RECOVERED"
    assert module_current_truth(loaded, "provider")["provenance"] == "current"


def test_global_search_and_static_context_do_not_leak_parse_stale_truth(
    tmp_path, monkeypatch
):
    source = tmp_path / "provider.py"
    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
    state = _stale_mcp_state(tmp_path)
    engine = SimpleNamespace(
        state=state,
        registry=SimpleNamespace(
            get_module_id=lambda name: "1/1",
            get_module_path=lambda value: "provider",
        ),
    )
    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)

    architecture = json.loads(
        mcp_server.get_project_architecture.fn(str(tmp_path))
    )
    search = json.loads(
        mcp_server.search_artifacts.fn(str(tmp_path), "helper")
    )
    implementation = json.loads(
        mcp_server.get_symbol_implementation.fn(
            str(tmp_path),
            "helper",
            ["provider.py"],
            mode="fetch",
            include=["static_context"],
        )
    )

    assert architecture["status"] == "stale"
    assert search["status"] == "stale"
    assert implementation["static_context"]["status"] == "stale"
    assert implementation["static_context"]["provenance"] == "last_known_good"


def test_same_owner_identity_allows_transient_classification(
    tmp_path, monkeypatch, authoritative_live_client
):
    endpoint = authoritative_live_client.endpoint
    monkeypatch.setattr(live_runtime, "_verified_existing_client", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: endpoint)
    monkeypatch.setattr(live_runtime, "_is_pid_alive", lambda _pid: True)
    monkeypatch.setattr(live_runtime.time, "sleep", lambda _delay: None)

    client, status = live_runtime.connect_existing_with_status(tmp_path)

    assert client is None
    assert status == "transient_connection_failure"


def test_same_pid_with_changed_owner_identity_is_not_transient(
    tmp_path, monkeypatch, authoritative_live_client
):
    original = authoritative_live_client.endpoint
    replacement = replace(original, owner_token="changed-owner-token")
    endpoints = iter([original, replacement])
    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: next(endpoints))
    monkeypatch.setattr(live_runtime, "_verified_existing_client", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(live_runtime.time, "sleep", lambda _delay: None)

    _, status = live_runtime.connect_existing_with_status(
        tmp_path, attempts=1
    )

    assert status == "owner_identity_changed"


def test_live_pid_with_mismatched_repository_identity_is_not_transient(
    tmp_path, monkeypatch, authoritative_live_client
):
    endpoint = replace(
        authoritative_live_client.endpoint,
        repo_id="other-repository-id",
    )
    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: endpoint)

    _, status = live_runtime.connect_existing_with_status(tmp_path)

    assert status == "endpoint_identity_unverified"


def test_matching_owner_retry_success_preserves_revision_and_journal(
    tmp_path, monkeypatch, authoritative_live_client
):
    endpoint = authoritative_live_client.endpoint

    class Client:
        def __init__(self):
            self.endpoint = endpoint

        def get_events(self, after_revision=None, limit=20):
            return {
                "status": "ok",
                "revision": 77,
                "events": [{"revision": 77, "status": "UPDATED"}],
                "total": 1,
                "truncated": False,
            }

    attempts = iter([None, Client()])
    monkeypatch.setattr(
        live_runtime, "_verified_existing_client", lambda *_args, **_kwargs: next(attempts)
    )
    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: endpoint)
    monkeypatch.setattr(live_runtime.time, "sleep", lambda _delay: None)

    result = json.loads(mcp_server.get_live_events.fn(str(tmp_path)))

    assert result["status"] == "ok"
    assert result["revision"] == 77
    assert result["events"][0]["revision"] == 77


def test_get_live_events_adapter_after_revision_validation(tmp_path, monkeypatch):
    class MockClient:
        def get_events(self, after_revision=None, limit=20):
            return {
                "status": "ok",
                "revision": 10,
                "latest_revision": 10,
                "earliest_retained_revision": 1,
                "continuity": "continuous",
                "resync_required": False,
                "resync_reason": None,
                "events": [],
                "total": 0,
                "truncated": False,
            }

    monkeypatch.setattr(
        "contextor.core.live_state.runtime.connect_existing_with_status",
        lambda _root: (MockClient(), "ok"),
    )

    # 1. Non-integer and bool cursors return invalid_after_revision without exception
    for invalid in ["1", 1.5, True, False, [1], {"a": 1}]:
        res = json.loads(mcp_server.get_live_events.fn(str(tmp_path), after_revision=invalid))
        assert res == {"status": "error", "error": "invalid_after_revision"}

    # 2. Valid integer cursors (0, -1, -999) are passed through to client
    res_zero = json.loads(mcp_server.get_live_events.fn(str(tmp_path), after_revision=0))
    assert res_zero["status"] == "ok"

    res_neg = json.loads(mcp_server.get_live_events.fn(str(tmp_path), after_revision=-1))
    assert res_neg["status"] == "ok"

    res_neg999 = json.loads(mcp_server.get_live_events.fn(str(tmp_path), after_revision=-999))
    assert res_neg999["status"] == "ok"
