from types import SimpleNamespace

from contextor.core.analysis.state_manager import (
    RepositoryAnalysisState,
    build_syntax_diagnostics_from_index,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state import load_snapshot, save_snapshot
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
