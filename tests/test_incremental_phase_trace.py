from contextlib import contextmanager
from importlib import import_module
from types import SimpleNamespace

import pytest

from contextor.core.analysis.state_manager import FileDelta, RepositoryAnalysisState


engine_module = import_module("contextor.core.analysis.incremental.engine")


class FakeRegistry:
    def __init__(self, *, omit=None):
        self.omit = omit
        self._state = {
            "artifact_registry": {"path_to_id": {}},
        }

    @contextmanager
    def transaction(self):
        yield

    @contextmanager
    def read_transaction(self):
        yield

    def sync_with_workspace(self, _modules, artifacts):
        for artifact in artifacts:
            if artifact != self.omit:
                self._state["artifact_registry"]["path_to_id"][artifact] = "A1/1"


class FakeStateManager:
    def __init__(self):
        self.paths = []

    def update_state(self, path):
        self.paths.append(path)


def _candidate():
    return SimpleNamespace(
        modules={}, artifacts={}, module_parse_freshness={},
        syntax_diagnostics_by_path={}, syntax_diagnostics_state="fresh",
        dependency_graph=None, metrics={}, topology_analytics={},
        cached_analytics={}, dependency_matrix={}, dependency_matrix_state="deferred",
        shared_usage_clusters=[], shared_usage_clusters_state="deferred",
        topology_metrics_state="deferred", cached_analytics_state="deferred",
        cycles=[], cycles_state="deferred", collision_facts={}, collisions=[],
        collisions_state="deferred", artifact_consumption={},
        artifact_consumption_state="stale", module_usages={},
        lineage_facts_by_source={}, lineage_facts_state="fresh",
        lineage_facts_semantic_version="1", lineage_owner_source_index={},
        lineage_source_owner_index={}, lineage_query_index_state="fresh",
        lineage_semantic_anchor_bindings_complete=True, trie=None,
        package_root="",
    )


def _engine(registry):
    engine = engine_module.IncrementalAnalysisEngine.__new__(
        engine_module.IncrementalAnalysisEngine
    )
    engine.state = RepositoryAnalysisState()
    engine.state.resync_required = False
    engine.registry = registry
    engine.state_manager = FakeStateManager()
    engine.root_path = None
    return engine


def _outcome(candidate, *, identity_sync_required, artifacts=None):
    return SimpleNamespace(
        candidate_state=candidate,
        affected_modules=set(),
        blast_radius_complete=False,
        execution_trace={
            "patch_families": ("definitions",),
            "recompute_modules": (),
            "graph_recomputations": (),
        },
        identity_sync_required=identity_sync_required,
        all_modules=set(),
        current_artifacts=set() if artifacts is None else set(artifacts),
    )


def _capture(monkeypatch):
    events = []
    monkeypatch.setattr(
        engine_module,
        "trace_event",
        lambda _domain, event, **fields: events.append((event, fields)),
    )
    return events


def _run(engine, delta, *, extracted_lineage_facts="facts"):
    return engine._apply_delta_and_commit(
        "target.py", delta, None, SimpleNamespace(), [], {}, None,
        extracted_lineage_facts=extracted_lineage_facts,
        syntax_source_path="target.py", syntax_fact={"status": "checked_and_none"},
        clear_parse_module="target",
    )


def _names(events):
    return [event for event, _fields in events]


def test_identity_sync_success_emits_order_and_no_missing_owners(monkeypatch):
    events = _capture(monkeypatch)
    registry = FakeRegistry()
    engine = _engine(registry)
    candidate = _candidate()
    monkeypatch.setattr(
        engine_module, "execute_refresh_plan",
        lambda **_kwargs: _outcome(candidate, identity_sync_required=True, artifacts={"pkg::new"}),
    )
    lineage_calls = []
    engine._update_candidate_lineage_slice = lambda *_args, **kwargs: lineage_calls.append(kwargs)

    _run(engine, FileDelta(module_path="target"))

    assert _names(events) == [
        "INCREMENTAL_EXECUTE_PLAN_START", "INCREMENTAL_EXECUTE_PLAN_END",
        "INCREMENTAL_REGISTRY_SYNC_START", "INCREMENTAL_REGISTRY_SYNC_END",
        "INCREMENTAL_LINEAGE_START", "INCREMENTAL_LINEAGE_END",
        "INCREMENTAL_FILE_STATE_START", "INCREMENTAL_FILE_STATE_END",
    ]
    assert events[3][1]["count"] == 0
    assert lineage_calls == [{"source_path": "target.py", "extracted_lineage_facts": "facts", "delete": False, "rematerialize_all": True}]


def test_identity_sync_lineage_failure_propagates_without_file_state(monkeypatch):
    events = _capture(monkeypatch)
    engine = _engine(FakeRegistry())
    candidate = _candidate()
    monkeypatch.setattr(
        engine_module, "execute_refresh_plan",
        lambda **_kwargs: _outcome(candidate, identity_sync_required=True, artifacts={"pkg::new"}),
    )

    def fail_lineage(*_args, **_kwargs):
        raise ValueError("owner-failure")

    engine._update_candidate_lineage_slice = fail_lineage

    with pytest.raises(ValueError, match="owner-failure"):
        _run(engine, FileDelta(module_path="target"))

    assert _names(events) == [
        "INCREMENTAL_EXECUTE_PLAN_START", "INCREMENTAL_EXECUTE_PLAN_END",
        "INCREMENTAL_REGISTRY_SYNC_START", "INCREMENTAL_REGISTRY_SYNC_END",
        "INCREMENTAL_LINEAGE_START", "INCREMENTAL_LINEAGE_FAIL",
    ]
    assert events[-1][1]["error"] == "owner-failure"
    assert engine.state_manager.paths == []


def test_non_identity_path_emits_skip_and_default_lineage_scope(monkeypatch):
    events = _capture(monkeypatch)
    engine = _engine(FakeRegistry())
    candidate = _candidate()
    monkeypatch.setattr(
        engine_module, "execute_refresh_plan",
        lambda **_kwargs: _outcome(candidate, identity_sync_required=False),
    )
    lineage_calls = []
    engine._update_candidate_lineage_slice = lambda *_args, **kwargs: lineage_calls.append(kwargs)

    _run(engine, FileDelta(module_path="target"))

    names = _names(events)
    assert "INCREMENTAL_REGISTRY_SYNC_SKIP" in names
    assert "INCREMENTAL_REGISTRY_SYNC_START" not in names
    assert "INCREMENTAL_REGISTRY_SYNC_END" not in names
    assert lineage_calls == [{"source_path": "target.py", "extracted_lineage_facts": "facts", "delete": False}]
    assert names[-2:] == ["INCREMENTAL_FILE_STATE_START", "INCREMENTAL_FILE_STATE_END"]


def test_registry_diagnostic_gap_is_observed_without_repair_or_raise(monkeypatch):
    events = _capture(monkeypatch)
    missing = "pkg::missing"
    engine = _engine(FakeRegistry(omit=missing))
    candidate = _candidate()
    monkeypatch.setattr(
        engine_module, "execute_refresh_plan",
        lambda **_kwargs: _outcome(candidate, identity_sync_required=True, artifacts={missing}),
    )
    engine._update_candidate_lineage_slice = lambda *_args, **_kwargs: None

    _run(engine, FileDelta(module_path="target"))

    registry_end = next(fields for event, fields in events if event == "INCREMENTAL_REGISTRY_SYNC_END")
    assert registry_end["count"] == 1
    assert registry_end["result"] == "missing_after_sync=pkg::missing"
    assert missing not in engine.registry._state["artifact_registry"]["path_to_id"]
