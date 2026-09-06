from types import SimpleNamespace

from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    build_syntax_diagnostics_from_index,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state import load_snapshot, save_snapshot
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.reporting_layer.artifact_usage_report import collect_module_artifacts
from contextor.core.symbol_engine.indexer import index_repository


def _index(*, modules=(), skipped=()):
    return SimpleNamespace(
        modules={f"module_{index}": SimpleNamespace(path=path) for index, path in enumerate(modules)},
        skipped=list(skipped),
    )


def test_full_analysis_materializes_checked_and_none_for_valid_python_path():
    facts, state = build_syntax_diagnostics_from_index(_index(modules=("pkg\\valid.py",)))

    assert state == "fresh"
    assert facts == {"pkg/valid.py": {"status": "checked_and_none", "errors": []}}


def test_full_analysis_materializes_syntax_error_without_module_identity():
    skipped = SimpleNamespace(
        path="broken.py",
        reason="is not valid Python (line 3, column 7: invalid syntax)",
        line_number=3,
        column_number=7,
    )

    facts, state = build_syntax_diagnostics_from_index(_index(skipped=(skipped,)))

    assert state == "fresh"
    assert facts == {
        "broken.py": {
            "status": "checked_with_errors",
            "errors": [{
                "message": "is not valid Python (line 3, column 7: invalid syntax)",
                "line_number": 3,
                "column_number": 7,
            }],
        }
    }


def test_full_analysis_mix_is_complete_when_every_path_has_explicit_fact():
    skipped = SimpleNamespace(
        path="pkg/broken.py",
        reason="is not valid Python (line 1: '(' was never closed)",
        line_number=1,
        column_number=None,
    )

    facts, state = build_syntax_diagnostics_from_index(
        _index(modules=("pkg/valid.py",), skipped=(skipped,))
    )

    assert state == "fresh"
    assert set(facts) == {"pkg/valid.py", "pkg/broken.py"}


def test_non_syntax_skipped_outcome_cannot_fabricate_checked_and_none():
    skipped = SimpleNamespace(
        path="unreadable.py",
        reason="could not be read (access denied)",
        line_number=None,
        column_number=None,
    )

    facts, state = build_syntax_diagnostics_from_index(_index(skipped=(skipped,)))

    assert state == "deferred"
    assert facts == {}


def test_syntax_diagnostics_snapshot_roundtrip_needs_no_source_reconstruction(tmp_path, monkeypatch):
    facts = {
        "broken.py": {
            "status": "checked_with_errors",
            "errors": [{"message": "invalid syntax", "line_number": 2, "column_number": 4}],
        }
    }
    state = RepositoryAnalysisState(
        syntax_diagnostics_by_path=facts,
        syntax_diagnostics_state="fresh",
    )
    save_snapshot(state, tmp_path, "syntax-state")

    monkeypatch.setattr(
        "contextor.core.source.ast.parse",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("hydration must not parse source")),
    )
    loaded, _ = load_snapshot(tmp_path, "syntax-state")

    assert loaded.syntax_diagnostics_by_path == facts
    assert loaded.syntax_diagnostics_state == "fresh"


def test_legacy_snapshot_marks_syntax_family_not_materialized(tmp_path):
    legacy = SimpleNamespace(modules={}, dependency_graph=None)
    save_snapshot(legacy, tmp_path, "legacy-syntax")

    loaded, _ = load_snapshot(tmp_path, "legacy-syntax")

    assert loaded.syntax_diagnostics_by_path == {}
    assert loaded.syntax_diagnostics_state == "not_materialized"


def test_real_index_repository_materializes_source_scoped_syntax_facts(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    (tmp_path / "valid.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")

    index = index_repository(str(tmp_path))

    assert {module.path for module in index.modules.values()} == {"valid.py"}
    assert len(index.skipped) == 1
    skipped = index.skipped[0]
    assert skipped.path == "broken.py"
    assert "is not valid Python" in skipped.reason
    assert (skipped.line_number, skipped.column_number) == (1, 11)

    facts, state = build_syntax_diagnostics_from_index(index)

    assert state == "fresh"
    assert facts["valid.py"] == {"status": "checked_and_none", "errors": []}
    assert facts["broken.py"]["status"] == "checked_with_errors"
    assert facts["broken.py"]["errors"][0] == {
        "message": skipped.reason,
        "line_number": 1,
        "column_number": 11,
    }
    assert all("\\" not in path and not path.startswith(("/", "C:/")) for path in facts)
    assert "broken" not in index.modules
    assert "module_name" not in facts["broken.py"]


def test_real_facade_materializes_real_index_syntax_facts(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    (tmp_path / "valid.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def broken(\n", encoding="utf-8")

    errors, _ = ContextorFacade.analyze_project(str(tmp_path))

    assert errors == []
    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    state = hydrated.engine.state
    assert state.syntax_diagnostics_state == "fresh"
    assert state.syntax_diagnostics_by_path["valid.py"] == {
        "status": "checked_and_none",
        "errors": [],
    }
    assert state.syntax_diagnostics_by_path["broken.py"]["status"] == "checked_with_errors"


def _live_syntax_fixture(tmp_path, *, family_state="fresh"):
    source = tmp_path / "provider.py"
    source.write_text("def value():\n    return 1\n", encoding="utf-8")
    registry = PersistentIdentityRegistry(str(tmp_path))
    index = index_repository(str(tmp_path))
    artifacts, _ = collect_module_artifacts(index.modules, str(tmp_path))
    trie = build_trie(index.modules)
    facts, _ = build_syntax_diagnostics_from_index(index)
    state = RepositoryAnalysisState(
        modules=dict(index.modules),
        artifacts=artifacts,
        dependency_graph=build_graph(index.modules),
        trie=trie,
        package_root=detect_package_root(index.modules, trie),
        syntax_diagnostics_by_path=facts,
        syntax_diagnostics_state=family_state,
    )
    manager = FileStateManager(str(tmp_path / ".state"))
    manager.update_state(str(source))

    def updater(candidate, file_path):
        return IncrementalAnalysisEngine(candidate, registry, manager, str(tmp_path)).update_file(file_path)

    server = CanonicalLiveServer(state, updater=updater)
    return source, server, state


def test_live_incremental_syntax_lifecycle_is_source_scoped_and_revision_atomic(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    source, server, _ = _live_syntax_fixture(tmp_path)
    try:
        source.write_text("def value():\n    return 2\n", encoding="utf-8")
        valid = server._dispatch({"operation": "update_file", "file_path": str(source), "origin": "desktop_watcher"})
        assert valid["revision"] == 1
        assert valid["result"].status == "UPDATED"
        assert server._state.syntax_diagnostics_state == "fresh"
        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
            "status": "checked_and_none", "errors": []
        }

        source.write_text("def value(\n", encoding="utf-8")
        broken = server._dispatch({"operation": "update_file", "file_path": str(source), "origin": "desktop_watcher"})
        assert broken["revision"] == 2
        assert broken["result"].status == "SYNTAX_ERROR"
        assert server._state.syntax_diagnostics_state == "fresh"
        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
            "status": "checked_with_errors",
            "errors": [{
                "message": "'(' was never closed",
                "line_number": 1,
                "column_number": 10,
            }],
        }
        assert server._state.module_parse_freshness["provider"]["state"] == "stale"
        assert "value" in server._state.artifacts["provider"]["own_symbols"]

        source.write_text("def value():\n    return 3\n", encoding="utf-8")
        repaired = server._dispatch({"operation": "update_file", "file_path": str(source), "origin": "desktop_watcher"})
        assert repaired["revision"] == 3
        assert repaired["result"].status == "RECOVERED"
        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
            "status": "checked_and_none", "errors": []
        }
        assert server._state.module_parse_freshness == {}

        added = tmp_path / "added.py"
        added.write_text("answer = 42\n", encoding="utf-8")
        new_valid = server._dispatch({"operation": "update_file", "file_path": str(added), "origin": "desktop_watcher"})
        assert new_valid["revision"] == 4
        assert server._state.syntax_diagnostics_by_path["added.py"] == {
            "status": "checked_and_none", "errors": []
        }

        broken_added = tmp_path / "new_broken.py"
        broken_added.write_text("def missing(\n", encoding="utf-8")
        new_invalid = server._dispatch({"operation": "update_file", "file_path": str(broken_added), "origin": "desktop_watcher"})
        assert new_invalid["revision"] == 5
        assert new_invalid["result"].status == "SYNTAX_ERROR"
        assert server._state.syntax_diagnostics_by_path["new_broken.py"]["status"] == "checked_with_errors"
        assert "new_broken" not in server._state.modules

        added.unlink()
        deleted = server._dispatch({"operation": "update_file", "file_path": str(added), "origin": "desktop_watcher"})
        assert deleted["revision"] == 6
        assert deleted["result"].status == "DELETED"
        assert "added.py" not in server._state.syntax_diagnostics_by_path

        events = server._dispatch({"operation": "get_events", "after_revision": 0, "limit": None})
        assert any(
            event["origin"] == "desktop_watcher" and event["status"] == "SYNTAX_ERROR"
            for event in events["events"]
        )
    finally:
        server.close()


def test_incremental_update_does_not_promote_unmaterialized_syntax_family(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    source, server, _ = _live_syntax_fixture(tmp_path, family_state="not_materialized")
    try:
        source.write_text("def value():\n    return 2\n", encoding="utf-8")
        response = server._dispatch({"operation": "update_file", "file_path": str(source), "origin": "desktop_watcher"})
        assert response["status"] == "ok"
        assert server._state.syntax_diagnostics_state == "not_materialized"
        assert server._state.syntax_diagnostics_by_path["provider.py"]["status"] == "checked_and_none"
    finally:
        server.close()


def test_live_persistence_failure_does_not_publish_half_updated_syntax_fact(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    source, _server, state = _live_syntax_fixture(tmp_path)
    registry = PersistentIdentityRegistry(str(tmp_path))
    manager = FileStateManager(str(tmp_path / ".failure-state"))
    # Capture R0 while the source is valid; the subsequent write must be a
    # real valid-to-SyntaxError transition for the incremental producer.
    manager.update_state(str(source))
    source.write_text("def value(\n", encoding="utf-8")
    captured = {}

    def updater(candidate, file_path):
        return IncrementalAnalysisEngine(candidate, registry, manager, str(tmp_path)).update_file(file_path)

    def failing_persister(candidate, revision):
        captured["syntax_status"] = candidate.syntax_diagnostics_by_path["provider.py"]["status"]
        captured["parse_freshness"] = candidate.module_parse_freshness["provider"]["state"]
        captured["revision"] = revision
        raise OSError("persistence failed")

    server = CanonicalLiveServer(
        state,
        updater=updater,
        persister=failing_persister,
    )
    try:
        response = server._dispatch({"operation": "update_file", "file_path": str(source), "origin": "desktop_watcher"})
        assert response["status"] == "error"
        assert response["revision"] == 0
        assert captured == {
            "syntax_status": "checked_with_errors",
            "parse_freshness": "stale",
            "revision": 1,
        }
        assert server._state.syntax_diagnostics_by_path["provider.py"] == {
            "status": "checked_and_none", "errors": []
        }
        assert server._state.module_parse_freshness == {}
    finally:
        server.close()
