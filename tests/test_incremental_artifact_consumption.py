"""
tests/test_incremental_artifact_consumption.py

Stage 3B.2 — Incremental Artifact Consumption Delta Integration Tests.
"""

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.reference.engine import extract_module_usage_facts

from contextor.core.reference.engine import _build_reexport_map
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def test_case_1_add_consumer(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    imp_c = ImportRef(module="target", level=0, names=["foo"], is_from_import=True)
    m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[imp_c])

    state = RepositoryAnalysisState(
        modules={"target": m_target},
        artifacts={"target": {"symbols": {"functions": ["foo"]}, "own_symbols": ["foo"]}},
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    engine.update_file(str(f_target))

    # Perform ADD of consumer
    res = engine.update_file(str(f_consumer))
    assert res.status == "UPDATED"
    assert res.artifact_consumption_state == "fresh"

    target_entry = engine.state.artifact_consumption.get("target::foo")
    assert target_entry is not None
    assert "consumer" in target_entry["consumers"]


def test_case_2_modify_call_target(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo, bar\nfoo()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])

    state = RepositoryAnalysisState(
        modules={"target": m_target},
        artifacts={"target": {"symbols": {"functions": ["foo", "bar"]}, "own_symbols": ["foo", "bar"]}},
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))

    # First update to populate initial consumer state
    engine.update_file(str(f_consumer))

    assert "consumer" in engine.state.artifact_consumption["target::foo"]["consumers"]

    # Modify consumer.py: foo() -> bar()
    f_consumer.write_text("from target import foo, bar\nbar()\n", encoding="utf-8")
    engine.update_file(str(f_consumer))

    foo_channels = engine.state.artifact_consumption.get("target::foo", {}).get("channels", {}).get("consumer", [])
    bar_channels = engine.state.artifact_consumption.get("target::bar", {}).get("channels", {}).get("consumer", [])

    assert "direct_calls" not in foo_channels
    assert "direct_calls" in bar_channels


def test_case_3_delete_consumer(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])

    state = RepositoryAnalysisState(
        modules={"target": m_target},
    )
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    engine.update_file(str(f_consumer))
    assert "consumer" in engine.state.artifact_consumption.get("target::foo", {}).get("consumers", [])

    # Delete consumer file
    f_consumer.unlink()
    engine.update_file(str(f_consumer))

    foo_consumers = engine.state.artifact_consumption.get("target::foo", {}).get("consumers", [])
    assert "consumer" not in foo_consumers


def test_case_4_alias_resolution(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo as local\nlocal()\n", encoding="utf-8")

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
    engine.update_file(str(f_target))
    engine.update_file(str(f_consumer))
    assert "consumer" in engine.state.artifact_consumption.get("target::foo", {}).get("consumers", [])


def test_case_5_qualified_call(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import target\ntarget.foo()\n", encoding="utf-8")

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
    engine.update_file(str(f_target))
    engine.update_file(str(f_consumer))
    assert "consumer" in engine.state.artifact_consumption.get("target::foo", {}).get("consumers", [])


def test_case_6_name_collision(tmp_path):
    f_a = tmp_path / "mod_a.py"
    f_a.write_text("def foo(): pass\n", encoding="utf-8")

    f_b = tmp_path / "mod_b.py"
    f_b.write_text("def foo(): pass\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from mod_a import foo\nfoo()\n", encoding="utf-8")

    m_a = Module(module_id="mod_a", path="mod_a.py", absolute_path=str(f_a), imports=[])
    m_b = Module(module_id="mod_b", path="mod_b.py", absolute_path=str(f_b), imports=[])
    state = RepositoryAnalysisState(modules={"mod_a": m_a, "mod_b": m_b})
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_a))
    engine.update_file(str(f_b))
    engine.update_file(str(f_consumer))

    a_consumers = engine.state.artifact_consumption.get("mod_a::foo", {}).get("consumers", [])
    b_consumers = engine.state.artifact_consumption.get("mod_b::foo", {}).get("consumers", [])

    assert "consumer" in a_consumers
    assert "consumer" not in b_consumers


def test_case_7_reexport_retarget_no_reread(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    f_init = pkg_dir / "__init__.py"
    f_init.write_text("from .impl_a import foo\n", encoding="utf-8")

    f_impl_a = pkg_dir / "impl_a.py"
    f_impl_a.write_text("def foo(): pass\n", encoding="utf-8")

    f_impl_b = pkg_dir / "impl_b.py"
    f_impl_b.write_text("def foo(): pass\n", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from pkg import foo\nfoo()\n", encoding="utf-8")

    imp_init = ImportRef(module=".impl_a", level=1, names=["foo"], is_from_import=True)
    m_init = Module(module_id="pkg.__init__", path="pkg/__init__.py", absolute_path=str(f_init), imports=[imp_init])
    m_impl_a = Module(module_id="pkg.impl_a", path="pkg/impl_a.py", absolute_path=str(f_impl_a), imports=[])
    m_impl_b = Module(module_id="pkg.impl_b", path="pkg/impl_b.py", absolute_path=str(f_impl_b), imports=[])

    state = RepositoryAnalysisState(modules={
        "pkg.__init__": m_init,
        "pkg.impl_a": m_impl_a,
        "pkg.impl_b": m_impl_b,
    })
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_impl_a))
    engine.update_file(str(f_impl_b))
    engine.update_file(str(f_init))
    engine.update_file(str(f_consumer))

    assert "consumer" in engine.state.artifact_consumption.get("pkg.impl_a::foo", {}).get("consumers", [])

    # Retarget re-export in pkg/__init__.py
    f_init.write_text("from .impl_b import foo\n", encoding="utf-8")
    imp_init_b = ImportRef(module=".impl_b", level=1, names=["foo"], is_from_import=True)

    # Prove consumer.py source is NOT reread/reparsed during pkg/__init__.py update
    with patch("contextor.core.reference.engine.extract_module_usage_facts", wraps=extract_module_usage_facts) as mock_extract:
        engine.update_file(str(f_init))
        # Ensure extract_module_usage_facts was called ONLY for pkg.__init__ and NOT for consumer
        extracted_modules = [call[0][0] for call in mock_extract.call_args_list]
        assert "consumer" not in extracted_modules
        assert "pkg.__init__" in extracted_modules

    impl_a_consumers = engine.state.artifact_consumption.get("pkg.impl_a::foo", {}).get("consumers", [])
    impl_b_consumers = engine.state.artifact_consumption.get("pkg.impl_b::foo", {}).get("consumers", [])

    assert "consumer" not in impl_a_consumers
    assert "consumer" in impl_b_consumers
