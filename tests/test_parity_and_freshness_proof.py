"""
tests/test_parity_and_freshness_proof.py

Stage 3B.2a — Artifact Consumption Parity & Freshness Proof Tests.
"""

import ast
from pathlib import Path

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module
from contextor.core.reference.engine import extract_module_usage_facts
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def normalize_consumption(artifact_consumption: dict) -> set:
    """
    Normalizes artifact_consumption dictionary into a set of tuples:
    (target_artifact, consumer_module)
    """
    relations = set()
    for target, entry in (artifact_consumption or {}).items():
        for consumer in entry.get("consumers", []):
            relations.add((target, consumer))
    return relations


def test_scenario_a_add_consumer(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[])

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

    inc_relations = normalize_consumption(engine.state.artifact_consumption)
    assert ("target::foo", "consumer") in inc_relations


def test_scenario_b_modify_body_only(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo, bar\nfoo()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[])
    state = RepositoryAnalysisState(modules={"target": m_target, "consumer": m_consumer})
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
    assert ("target::foo", "consumer") in normalize_consumption(engine.state.artifact_consumption)

    # Modify body: foo() -> bar()
    f_consumer.write_text("from target import foo, bar\nbar()\n", encoding="utf-8")
    engine.update_file(str(f_consumer))

    triples = set()
    for target, entry in engine.state.artifact_consumption.items():
        for cons, chs in entry.get("channels", {}).items():
            for ch in chs:
                triples.add((target, cons, ch))

    assert ("target::foo", "consumer", "direct_calls") not in triples
    assert ("target::bar", "consumer", "direct_calls") in triples


def test_scenario_c_delete_consumer(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[])
    state = RepositoryAnalysisState(modules={"target": m_target, "consumer": m_consumer})
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
    assert ("target::foo", "consumer") in normalize_consumption(engine.state.artifact_consumption)

    f_consumer.unlink()
    engine.update_file(str(f_consumer))
    assert ("target::foo", "consumer") not in normalize_consumption(engine.state.artifact_consumption)


def test_scenario_h_inheritance_usage(tmp_path):
    f_base = tmp_path / "base.py"
    f_base.write_text("class BaseWidget: pass\n", encoding="utf-8")
    f_child = tmp_path / "child.py"
    f_child.write_text("from base import BaseWidget\nclass ChildWidget(BaseWidget): pass\n", encoding="utf-8")

    m_base = Module(module_id="base", path="base.py", absolute_path=str(f_base), imports=[])
    state = RepositoryAnalysisState(modules={"base": m_base})
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_base))
    engine.update_file(str(f_child))
    assert ("base::BaseWidget", "child") in normalize_consumption(engine.state.artifact_consumption)


def test_definer_deletion_parity(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[])
    state = RepositoryAnalysisState(modules={"target": m_target, "consumer": m_consumer})
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
    assert ("target::foo", "consumer") in normalize_consumption(engine.state.artifact_consumption)

    # Delete target.py
    f_target.unlink()
    engine.update_file(str(f_target))
    assert "target::foo" not in engine.state.artifact_consumption


def test_copy_on_write_atomicity(tmp_path):
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
    engine.update_file(str(f_target))

    old_consumption_obj = engine.state.artifact_consumption
    assert "consumer" not in old_consumption_obj.get("target::foo", {}).get("consumers", [])

    engine.update_file(str(f_consumer))

    # Old reference must remain untouched by consumer addition (COW immutability)
    assert engine.state.artifact_consumption is not old_consumption_obj
    assert "consumer" not in old_consumption_obj.get("target::foo", {}).get("consumers", [])
    assert "consumer" in engine.state.artifact_consumption.get("target::foo", {}).get("consumers", [])
