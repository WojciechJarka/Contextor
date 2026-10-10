import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from contextor import mcp_server
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp import query_helpers
from contextor.mcp import report_helpers
from contextor.mcp.tools import (
    query_canonical_projection as query_canonical_projection_tool,
)
from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import (
    FileStateManager,
    RepositoryAnalysisState,
    load_engine_state,
    mark_module_parse_failure,
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
from contextor.core.reference.shared import materialize_reexport_facts_by_module


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
    repo_index = index_repository(str(tmp_path))
    modules = repo_index.modules
    artifacts, _ = collect_module_artifacts(modules, str(tmp_path))
    trie = build_trie(modules)
    state = RepositoryAnalysisState(
        modules=dict(modules),
        reexport_facts_by_module=materialize_reexport_facts_by_module(
            modules, repo_index.reference_facts_by_module
        ),
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


@pytest.mark.parametrize(
    "raw_map",
    [None, False, 0, [], "", "bad", 17, ["bad"]],
    ids=repr,
)
def test_module_current_truth_rejects_malformed_whole_map_without_mutation(raw_map):
    state = SimpleNamespace(module_parse_freshness=raw_map)

    truth = module_current_truth(state, "provider")

    assert truth == {
        "available": False,
        "state": "unavailable",
        "provenance": "untrusted",
        "reason": "Canonical module parse freshness metadata is invalid or untrusted.",
    }
    assert state.module_parse_freshness is raw_map


@pytest.mark.parametrize(
    "entry",
    [None, False, 17, [], "bad", {}, {"state": None}, {"state": False}, {"state": "unknown"}],
    ids=repr,
)
def test_module_current_truth_rejects_malformed_entry_without_mutation(entry):
    raw_map = {"provider": entry}
    state = SimpleNamespace(module_parse_freshness=raw_map)

    truth = module_current_truth(state, "provider")

    assert truth["available"] is False
    assert truth["state"] == "unavailable"
    assert truth["provenance"] == "untrusted"
    assert "parse_failure" not in truth
    assert state.module_parse_freshness is raw_map
    assert state.module_parse_freshness["provider"] is entry


def test_module_current_truth_keeps_valid_and_legacy_absence_contract():
    for state in (
        SimpleNamespace(),
        SimpleNamespace(module_parse_freshness={}),
        SimpleNamespace(module_parse_freshness={"other": {"state": "stale"}}),
        SimpleNamespace(module_parse_freshness={"provider": {"state": "fresh"}}),
    ):
        assert module_current_truth(state, "provider") == {
            "available": True,
            "state": "fresh",
            "provenance": "current",
        }

    stale_entry = {
        "state": "stale",
        "error": "invalid syntax",
        "line_number": 2,
        "column_number": 3,
    }
    stale = SimpleNamespace(module_parse_freshness={"provider": stale_entry})
    assert module_current_truth(stale, "provider") == {
        "available": False,
        "state": "stale",
        "provenance": "last_known_good",
        "reason": "Current source could not be parsed; canonical facts are last-known-good.",
        "parse_failure": {
            "error": "invalid syntax",
            "line_number": 2,
            "column_number": 3,
        },
    }
    assert stale.module_parse_freshness["provider"] is stale_entry


def test_module_truth_unavailable_distinguishes_untrusted_from_lkg():
    state = SimpleNamespace(module_parse_freshness={"provider": {"state": "stale"}})
    stale = query_helpers.module_truth_unavailable(state, "provider")
    assert stale["status"] == "stale"
    assert stale["provenance"] == "last_known_good"
    assert stale["parse_failure"] == {}

    entry = {"state": "unknown"}
    state.module_parse_freshness = {"provider": entry}
    untrusted = query_helpers.module_truth_unavailable(state, "provider")
    assert untrusted["status"] == "unavailable"
    assert untrusted["available"] is False
    assert untrusted["provenance"] == "untrusted"
    assert "parse_failure" not in untrusted
    assert state.module_parse_freshness["provider"] is entry


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


@pytest.mark.parametrize(
    "raw_map",
    [{"provider": {"state": "unknown"}}, ["bad"]],
    ids=["malformed_entry", "malformed_whole_map"],
)
def test_malformed_parse_freshness_snapshot_roundtrip_remains_untrusted(tmp_path, raw_map):
    _source, engine = _engine_for_file(tmp_path)
    engine.state.module_parse_freshness = raw_map
    original_map = engine.state.module_parse_freshness

    cache = tmp_path / "cache"
    assert save_engine_state(engine.state, str(cache), "state-malformed")
    loaded = load_engine_state(str(cache), "state-malformed")

    assert loaded is not None
    assert loaded.module_parse_freshness == raw_map
    assert module_current_truth(loaded, "provider")["state"] == "unavailable"
    assert module_current_truth(loaded, "provider")["provenance"] == "untrusted"
    assert engine.state.module_parse_freshness is original_map


def test_reading_malformed_parse_freshness_does_not_claim_recovery(tmp_path):
    source, engine = _engine_for_file(tmp_path)
    entry = {"state": "unknown"}
    engine.state.module_parse_freshness = {"provider": entry}

    assert module_current_truth(engine.state, "provider")["state"] == "unavailable"
    assert engine.state.module_parse_freshness["provider"] is entry
    source.write_text(
        "def helper(value: int) -> int:\n    return value + 1\n# verified parse\n"
    )
    result = engine.update_file(str(source))
    assert result.status != "RECOVERED"
    assert module_current_truth(engine.state, "provider")["state"] == "fresh"


def test_mark_module_parse_failure_rejects_untrusted_target_entry():
    entry = {"state": "unknown"}
    raw_map = {"provider": entry}
    state = SimpleNamespace(module_parse_freshness=raw_map)

    with pytest.raises(
        ValueError,
        match="Canonical module parse freshness is untrusted",
    ):
        mark_module_parse_failure(
            state,
            "provider",
            error="invalid syntax",
            line_number=1,
            column_number=1,
        )

    assert state.module_parse_freshness is raw_map
    assert state.module_parse_freshness["provider"] is entry
    assert module_current_truth(state, "provider")["provenance"] == "untrusted"


@pytest.mark.parametrize(
    "raw_map",
    [None, [("provider", {"state": "stale"})]],
    ids=["falsey_none", "truthy_coercible_pairs"],
)
def test_syntax_failure_rejects_malformed_whole_parse_freshness_map(
    tmp_path,
    raw_map,
):
    source, engine = _engine_for_file(tmp_path)
    engine.state.module_parse_freshness = raw_map
    original_modules = engine.state.modules
    original_artifacts = engine.state.artifacts
    source.write_text("def broken(\n")

    with pytest.raises(
        ValueError,
        match="Canonical module_parse_freshness is invalid",
    ):
        engine.update_file(str(source))

    assert engine.state.module_parse_freshness is raw_map
    assert engine.state.modules is original_modules
    assert engine.state.artifacts is original_artifacts
    assert module_current_truth(engine.state, "provider")["state"] == "unavailable"
    assert module_current_truth(engine.state, "unrelated")["state"] == "unavailable"


def test_syntax_failure_does_not_promote_untrusted_target_entry_to_lkg(tmp_path):
    source, engine = _engine_for_file(tmp_path)
    entry = {"state": "unknown"}
    raw_map = {"provider": entry}
    engine.state.module_parse_freshness = raw_map
    source.write_text("def broken(\n")

    with pytest.raises(
        ValueError,
        match="Canonical module parse freshness is untrusted",
    ):
        engine.update_file(str(source))

    assert engine.state.module_parse_freshness is raw_map
    assert engine.state.module_parse_freshness["provider"] is entry
    assert module_current_truth(engine.state, "provider")["provenance"] == "untrusted"


def test_semantic_noop_rejects_malformed_parse_freshness_map(tmp_path):
    source, engine = _engine_for_file(tmp_path)
    raw_map = None
    engine.state.module_parse_freshness = raw_map
    original_modules = engine.state.modules
    source.write_text(
        "def helper(value: int) -> int:\n    return value + 1\n# semantically unchanged\n"
    )

    with pytest.raises(
        ValueError,
        match="Canonical module_parse_freshness is invalid",
    ):
        engine.update_file(str(source))

    assert engine.state.module_parse_freshness is raw_map
    assert engine.state.modules is original_modules
    assert module_current_truth(engine.state, "provider")["state"] == "unavailable"
    assert module_current_truth(engine.state, "unrelated")["state"] == "unavailable"


@pytest.mark.parametrize(
    ("operation", "raw_map"),
    [
        ("updated", False),
        ("deleted", [("provider", {"state": "stale"})]),
    ],
    ids=["ordinary_update", "module_delete"],
)
def test_updated_and_deleted_candidates_reject_malformed_parse_freshness(
    tmp_path,
    operation,
    raw_map,
):
    source, engine = _engine_for_file(tmp_path)
    engine.state.module_parse_freshness = raw_map
    original_modules = engine.state.modules
    original_artifacts = engine.state.artifacts
    if operation == "updated":
        source.write_text(
            "def helper(value: int) -> int:\n    return value + 2\n"
        )
    else:
        source.unlink()

    with pytest.raises(
        ValueError,
        match="Canonical module_parse_freshness is invalid",
    ):
        engine.update_file(str(source))

    assert engine.state.module_parse_freshness is raw_map
    assert engine.state.modules is original_modules
    assert engine.state.artifacts is original_artifacts
    assert module_current_truth(engine.state, "provider")["state"] == "unavailable"


def test_successful_update_preserves_unrelated_malformed_parse_entry(tmp_path):
    source, engine = _engine_for_file(tmp_path)
    unrelated_entry = {"state": "unknown"}
    raw_map = {"unrelated": unrelated_entry}
    engine.state.module_parse_freshness = raw_map
    source.write_text(
        "def helper(value: int) -> int:\n    return value + 2\n"
    )

    result = engine.update_file(str(source))

    assert result.status == "UPDATED"
    assert engine.state.module_parse_freshness == raw_map
    assert engine.state.module_parse_freshness is not raw_map
    assert engine.state.module_parse_freshness["unrelated"] is unrelated_entry
    assert module_current_truth(engine.state, "provider")["state"] == "fresh"
    assert module_current_truth(engine.state, "unrelated")["provenance"] == "untrusted"


def test_early_unchanged_keeps_untrusted_target_marker_without_parsing(
    tmp_path,
    monkeypatch,
):
    source, engine = _engine_for_file(tmp_path)
    entry = {"state": "unknown"}
    raw_map = {"provider": entry}
    engine.state.module_parse_freshness = raw_map

    def unexpected_parse(**_kwargs):
        pytest.fail("early UNCHANGED must not parse the source")

    monkeypatch.setattr(
        "contextor.core.analysis.incremental.engine.prepare_source_update",
        unexpected_parse,
    )

    result = engine.update_file(str(source))

    assert result.status == "UNCHANGED"
    assert engine.state.module_parse_freshness is raw_map
    assert engine.state.module_parse_freshness["provider"] is entry
    assert module_current_truth(engine.state, "provider")["provenance"] == "untrusted"


def test_malformed_snapshot_map_rejects_hydrated_syntax_update(tmp_path):
    source, engine = _engine_for_file(tmp_path)
    raw_map = [("provider", {"state": "stale"})]
    engine.state.module_parse_freshness = raw_map
    cache = tmp_path / "cache"
    assert save_engine_state(engine.state, str(cache), "state-malformed-update")
    loaded = load_engine_state(str(cache), "state-malformed-update")
    assert loaded is not None
    original_map = loaded.module_parse_freshness
    original_modules = loaded.modules
    source.write_text("def broken(\n")
    hydrated_engine = IncrementalAnalysisEngine(
        loaded,
        engine.registry,
        engine.state_manager,
        str(tmp_path),
    )

    with pytest.raises(
        ValueError,
        match="Canonical module_parse_freshness is invalid",
    ):
        hydrated_engine.update_file(str(source))

    assert loaded.module_parse_freshness is original_map
    assert loaded.modules is original_modules
    assert module_current_truth(loaded, "provider")["state"] == "unavailable"
    previous_generation = load_engine_state(str(cache), "state-malformed-update")
    assert previous_generation is not None
    assert previous_generation.module_parse_freshness == raw_map


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
    monkeypatch.setattr(
        report_helpers,
        "get_canonical_report",
        lambda _root, _filename: None,
    )

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

    assert architecture["status"] == "partial"
    assert (
        architecture["live_state"]["state_freshness"]["canonical_state"]
        == "stale"
    )
    assert architecture["live_state"]["parse_stale_modules"]["provider"][
        "provenance"
    ] == "last_known_good"
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


def test_verified_client_transport_rejection_serializes_bounded_trace(
    tmp_path, monkeypatch, authoritative_live_client
):
    from contextor.core.runtime_trace import finish_desktop_trace_session, start_desktop_trace_session
    import contextor.core.runtime_trace as trace

    endpoint = authoritative_live_client.endpoint
    trace_logs = tmp_path / "isolated-trace"
    monkeypatch.setattr(trace, "runtime_logs_dir", lambda: trace_logs)
    finish_desktop_trace_session()
    path = start_desktop_trace_session()
    assert path is not None

    class RefusingClient:
        def __init__(self, _endpoint):
            pass

        def authority_status(self):
            raise ConnectionRefusedError(10061, "refused")

    identity = live_runtime.read_repository_identity(tmp_path)
    assert identity is not None
    domain = live_runtime._production_domain(identity)
    manager = live_runtime.RuntimeLeaseManager(domain)
    monkeypatch.setattr(live_runtime, "LiveStateClient", RefusingClient)
    try:
        assert live_runtime._verified_existing_client(tmp_path, identity, domain, manager) is None
    finally:
        finish_desktop_trace_session()

    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    event = next(item for item in records if item.get("ev") == "LIVE_CONNECT_REJECT")
    assert event["reason_code"] == "AUTHORITY_STATUS_TRANSPORT_ERROR"
    assert event["exception_class"] == "ConnectionRefusedError"
    assert "winerror" not in event
    assert "authkey" not in json.dumps(event).lower()
    assert "owner_token" not in json.dumps(event).lower()


def test_trace_failure_cannot_change_transient_connection_result(
    tmp_path, monkeypatch, authoritative_live_client
):
    endpoint = authoritative_live_client.endpoint
    monkeypatch.setattr(live_runtime, "_verified_existing_client", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(live_runtime, "_read_endpoint", lambda _root, **_kwargs: endpoint)
    monkeypatch.setattr(live_runtime, "_is_pid_alive", lambda _pid: True)
    monkeypatch.setattr(live_runtime.time, "sleep", lambda _delay: None)
    import contextor.core.runtime_trace as trace

    monkeypatch.setattr(trace, "trace_event", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("trace unavailable")))

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
