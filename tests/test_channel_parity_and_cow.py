"""
tests/test_channel_parity_and_cow.py

Stage 3B.2b — Channel-Parity & Copy-On-Write Final Proof Tests.
"""

from pathlib import Path

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def normalize_channel_aware(artifact_consumption: dict) -> set:
    """
    Normalizes artifact_consumption dictionary into a set of 3-tuples:
    (target_artifact, consumer_module, usage_channel)
    """
    triples = set()
    for target, entry in (artifact_consumption or {}).items():
        channels_map = entry.get("channels", {})
        for consumer, channels in channels_map.items():
            for ch in channels:
                triples.add((target, consumer, ch))
    return triples


def test_channel_parity_all_channels(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("""
def direct_fn(): pass
def callback_fn(): pass
def event_fn(): pass
class BaseClass: pass
""", encoding="utf-8")

    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("""
from target import direct_fn, callback_fn, event_fn, BaseClass
import target

_ref = target.direct_fn
direct_fn()
some_api(callback=callback_fn)
emitter.subscribe('click', event_fn)

class ChildClass(BaseClass):
    pass
""", encoding="utf-8")

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

    triples = normalize_channel_aware(engine.state.artifact_consumption)

    # A. api_imports
    assert ("target::direct_fn", "consumer", "api_imports") in triples
    # B. direct_calls
    assert ("target::direct_fn", "consumer", "direct_calls") in triples
    # C. qualified_refs
    assert ("target::direct_fn", "consumer", "qualified_refs") in triples
    # E. callback_calls
    assert ("target::callback_fn", "consumer", "callback_calls") in triples
    # F. event_bindings
    assert ("target::event_fn", "consumer", "event_bindings") in triples
    # G. inheritance
    assert ("target::BaseClass", "consumer", "inheritance") in triples


def test_channel_transition_direct_to_callback(tmp_path):
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

    # Initial state: direct_calls
    engine.update_file(str(f_target))
    engine.update_file(str(f_consumer))
    triples_before = normalize_channel_aware(engine.state.artifact_consumption)
    assert ("target::foo", "consumer", "direct_calls") in triples_before
    assert ("target::foo", "consumer", "callback_calls") not in triples_before

    # Transition: foo() -> register(callback=foo)
    f_consumer.write_text("from target import foo\nregister(callback=foo)\n", encoding="utf-8")
    engine.update_file(str(f_consumer))

    triples_after = normalize_channel_aware(engine.state.artifact_consumption)
    assert ("target::foo", "consumer", "direct_calls") not in triples_after
    assert ("target::foo", "consumer", "callback_calls") in triples_after


def test_cow_immutability_non_empty_old_state(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
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

    # Step 1: Populate initial non-empty state
    engine.update_file(str(f_target))
    engine.update_file(str(f_consumer))
    old_state_ref = engine.state.artifact_consumption
    old_entry_ref = old_state_ref["target::foo"]
    old_consumers_list = old_entry_ref["consumers"]
    old_channels_dict = old_entry_ref["channels"]

    # Step 2: Mutate consumer to call bar() instead of foo()
    f_consumer.write_text("from target import bar\nbar()\n", encoding="utf-8")
    engine.update_file(str(f_consumer))

    new_state_ref = engine.state.artifact_consumption

    # Verify identity separation (Copy-On-Write)
    assert old_state_ref is not new_state_ref
    assert "target::foo" in old_state_ref
    assert "consumer" in old_state_ref["target::foo"]["consumers"]

    # Verify target::foo entry in old_state_ref was NOT mutated in place
    assert old_entry_ref["consumers"] is old_consumers_list
    assert old_entry_ref["channels"] is old_channels_dict
    assert "consumer" in old_consumers_list


def test_unrelated_relation_preservation(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_other = tmp_path / "other.py"
    f_other.write_text("def bar(): pass\n", encoding="utf-8")

    f_consumer_a = tmp_path / "consumer_a.py"
    f_consumer_a.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    f_consumer_b = tmp_path / "consumer_b.py"
    f_consumer_b.write_text("from other import bar\nbar()\n", encoding="utf-8")

    m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
    m_other = Module(module_id="other", path="other.py", absolute_path=str(f_other), imports=[])

    state = RepositoryAnalysisState(modules={"target": m_target, "other": m_other})
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    engine.update_file(str(f_target))
    engine.update_file(str(f_other))
    engine.update_file(str(f_consumer_a))
    engine.update_file(str(f_consumer_b))

    other_bar_entry_before = engine.state.artifact_consumption.get("other::bar")
    assert other_bar_entry_before is not None
    assert "consumer_b" in other_bar_entry_before["consumers"]

    # Modify ONLY consumer_a.py
    f_consumer_a.write_text("from target import foo\nregister(callback=foo)\n", encoding="utf-8")
    engine.update_file(str(f_consumer_a))

    other_bar_entry_after = engine.state.artifact_consumption.get("other::bar")

    # Unrelated relation other::bar MUST remain semantically identical
    assert other_bar_entry_after == other_bar_entry_before
    assert "consumer_b" in other_bar_entry_after["consumers"]
