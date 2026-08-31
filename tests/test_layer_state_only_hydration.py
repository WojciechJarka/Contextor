from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import contextor.core.api.facade as facade
import contextor.core.live_state.hydration as hydration
from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.repository_identity import RepositoryIdentity


def _state(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("def sample():\n    return 1\n", encoding="utf-8")
    module = Module("sample", "sample.py", str(path), [])
    graph = SimpleNamespace(hard_edges={"sample": set()}, soft_edges={"sample": set()})
    return RepositoryAnalysisState(
        modules={"sample": module},
        dependency_graph=graph,
        artifacts={"sample": []},
        collision_facts={"sample": []},
        collisions_state="fresh",
    )


def _patch_resolution_dependencies(monkeypatch, root, *, live=None, snapshot=None):
    identity = RepositoryIdentity("ctx_test", str(root.resolve()), root.name)
    monkeypatch.setattr("contextor.core.repository_identity.read_repository_identity", lambda _: identity)
    monkeypatch.setattr("contextor.core.live_state.store.migrate_legacy_snapshot", lambda _: root / "cache")
    monkeypatch.setattr("contextor.core.live_state.store.read_metadata", lambda _: SimpleNamespace(state_id="state"))
    monkeypatch.setattr("contextor.core.analysis.state_manager.load_engine_state", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr("contextor.core.live_state.runtime.connect", lambda _: live)


def test_resolver_prefers_valid_live_state_over_snapshot(tmp_path, monkeypatch):
    live_state, snapshot_state = _state(tmp_path), _state(tmp_path)
    client = SimpleNamespace(
        ping=lambda: {"revision": 7},
        snapshot=lambda: {"state": live_state, "revision": 8},
    )
    _patch_resolution_dependencies(monkeypatch, tmp_path, live=client, snapshot=snapshot_state)

    resolved = hydration.resolve_authoritative_repository_state(tmp_path)

    assert resolved.state is live_state
    assert resolved.source == "live_service"
    assert resolved.revision == 8


def test_resolver_uses_snapshot_when_live_is_unavailable(tmp_path, monkeypatch):
    snapshot_state = _state(tmp_path)
    _patch_resolution_dependencies(monkeypatch, tmp_path, snapshot=snapshot_state)

    resolved = hydration.resolve_authoritative_repository_state(tmp_path)

    assert resolved.state is snapshot_state
    assert resolved.source == "snapshot"


def test_invalid_authoritative_state_keeps_layer_on_indexed_fallback(tmp_path, monkeypatch):
    _patch_resolution_dependencies(monkeypatch, tmp_path, snapshot=RepositoryAnalysisState())
    assert hydration.resolve_authoritative_repository_state(tmp_path) is None


def test_full_hydrator_still_constructs_an_incremental_engine(tmp_path, monkeypatch):
    state = _state(tmp_path)
    resolved = hydration.AuthoritativeRepositoryState(
        state=state, client=None, revision=3, source="snapshot", cache_dir=tmp_path / "cache"
    )
    calls = []
    monkeypatch.setattr(hydration, "resolve_authoritative_repository_state", lambda _: resolved)

    class Engine:
        def __init__(self, *args):
            calls.append(args)

    monkeypatch.setattr("contextor.core.analysis.incremental_engine.IncrementalAnalysisEngine", Engine)
    monkeypatch.setattr("contextor.core.reporting_engine.persistent_registry.PersistentIdentityRegistry", lambda _: object())
    monkeypatch.setattr("contextor.core.analysis.state_manager.FileStateManager", lambda _: object())

    hydrated = hydration.hydrate_repository_engine(tmp_path)

    assert isinstance(hydrated.engine, Engine)
    assert len(calls) == 1


def test_layer_uses_state_directly_without_full_engine_hydration(tmp_path, monkeypatch):
    layer = tmp_path / "layer"
    layer.mkdir()
    state = _state(layer)
    resolved = hydration.AuthoritativeRepositoryState(
        state=state, client=None, revision=3, source="snapshot", cache_dir=tmp_path / "cache"
    )
    monkeypatch.setattr(facade, "resolve_authoritative_repository_state", lambda _: resolved)
    monkeypatch.setattr(facade, "hydrate_repository_engine", lambda _: (_ for _ in ()).throw(AssertionError("full hydration used")))
    monkeypatch.setattr(facade, "_initialize_repository_identity", lambda _: SimpleNamespace(transaction=lambda: nullcontext()))
    monkeypatch.setattr(facade, "reset_caches", lambda: None)
    monkeypatch.setattr(facade, "_analysis_filters", lambda *args: (set(), set()))
    monkeypatch.setattr(facade, "_compute_metrics_and_debt", lambda *args, **kwargs: ({}, [], [], {}))
    monkeypatch.setattr(facade, "detect_hotspots", lambda *_: [])
    monkeypatch.setattr(facade, "generate_summary_report", lambda *args, **kwargs: {})
    monkeypatch.setattr(facade, "generate_structure_report", lambda *args, **kwargs: {})
    monkeypatch.setattr(facade, "canonical_artifact_report", lambda artifacts: {"artifacts": artifacts})
    monkeypatch.setattr(facade, "compact_artifact_report", lambda *args: {})
    monkeypatch.setattr(facade, "build_report_header", lambda *args: {})
    monkeypatch.setattr(facade, "slice_report_for_layer", lambda **kwargs: {"summary": kwargs["global_summary"]})
    monkeypatch.setattr("contextor.core.reporting_engine.dictionary.IndexDictionary", lambda _: object())
    monkeypatch.setattr("contextor.core.reporting_engine.layer_pipeline.execute_layer_pipeline", lambda *args, **kwargs: None)
    monkeypatch.setattr("contextor.core.reporting_engine.io_manager.write_layer_reports", lambda **kwargs: None)

    facade.ContextorFacade.analyze_layer(str(tmp_path), str(layer))
