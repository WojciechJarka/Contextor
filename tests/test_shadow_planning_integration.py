"""
tests/test_shadow_planning_integration.py

Stage 3C.1a — Shadow Planning Integration Tests against IncrementalAnalysisEngine.
"""

from pathlib import Path

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def test_shadow_plan_on_body_modify(tmp_path):
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

    res1 = engine.update_file(str(f_consumer))
    assert res1.shadow_plan is not None
    assert res1.shadow_plan.reparse_modules == ()

    # Body modify: foo() -> bar()
    f_consumer.write_text("from target import foo, bar\nbar()\n", encoding="utf-8")
    res2 = engine.update_file(str(f_consumer))

    assert res2.shadow_plan is not None
    assert res2.shadow_plan.reparse_modules == ()
    assert "consumer" not in res2.shadow_plan.recompute_modules


def test_shadow_plan_on_module_delete(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

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
    engine.update_file(str(f_consumer))

    # Delete target.py
    f_target.unlink()
    res = engine.update_file(str(f_target))

    assert res.shadow_plan is not None
    assert res.shadow_plan.reparse_modules == ()
    assert "consumer" in res.shadow_plan.recompute_modules
