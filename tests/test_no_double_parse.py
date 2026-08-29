"""
tests/test_no_double_parse.py

Stage 3C.1a — Instrumented No-Double-Parse and Execution Contract Tests.
"""

import ast
from pathlib import Path
from unittest.mock import patch
import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.incremental.preparation import prepare_source_update
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def test_prepare_source_update_reads_and_parses_target_once(tmp_path):
    target = tmp_path / "target.py"
    target.write_text(
        "from dependency import item\n\nVALUE = item\n\ndef function():\n    return VALUE\n",
        encoding="utf-8",
    )

    read_calls = []
    original_read_text = Path.read_text

    def counted_read_text(path, *args, **kwargs):
        read_calls.append(path)
        return original_read_text(path, *args, **kwargs)

    with patch.object(Path, "read_text", new=counted_read_text):
        with patch("ast.parse", wraps=ast.parse) as mock_parse:
            result = prepare_source_update(
                target,
                "target",
                True,
                None,
                None,
                None,
            )

    assert result.error_status is None
    assert len(read_calls) == 1
    assert mock_parse.call_count == 1


def test_no_double_parse_on_modify(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo, bar\nfoo()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    state = RepositoryAnalysisState(modules={"target": m_target})
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    # Initial update
    engine.update_file(str(f_consumer))

    # Instrument ast.parse to count AST parses during MODIFY
    f_consumer.write_text("from target import foo, bar\nbar()\n", encoding="utf-8")
    with patch("ast.parse", wraps=ast.parse) as mock_parse:
        res = engine.update_file(str(f_consumer))
        # Consumer source is parsed during delta calculation
        assert mock_parse.call_count >= 1
        assert res.shadow_plan is not None
        # reparse_modules MUST be () so execution will not parse consumer a second time
        assert res.shadow_plan.reparse_modules == ()


def test_no_double_parse_on_add(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    state = RepositoryAnalysisState(modules={})
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    with patch("ast.parse", wraps=ast.parse) as mock_parse:
        res = engine.update_file(str(f_target))
        assert mock_parse.call_count >= 1
        assert res.shadow_plan is not None
        assert res.shadow_plan.reparse_modules == ()


def test_no_parse_on_delete(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    state = RepositoryAnalysisState(modules={"target": m_target})
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    f_target.unlink()
    with patch("ast.parse", wraps=ast.parse) as mock_parse:
        res = engine.update_file(str(f_target))
        # Deleted file is NOT parsed from disk
        assert mock_parse.call_count == 0
        assert res.shadow_plan is not None
        assert res.shadow_plan.reparse_modules == ()
