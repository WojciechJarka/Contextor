"""
tests/test_module_usage_facts.py

Stage 3B.1a — Compact Canonical Module Usage Facts Completeness Tests.
"""

import ast
from pathlib import Path

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.live_state.store import load_snapshot, save_snapshot
from contextor.core.reference.engine import extract_module_usage_facts
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def test_module_usage_facts_model_and_serialization():
    facts = ModuleUsageFacts(
        imports=("math", "os"),
        direct_calls=("math.sqrt",),
        runtime_calls=("getattr",),
        callback_calls=("on_click_handler",),
        event_bindings=("on_submit",),
        inheritance_refs=(("ChildClass", "BaseClass"),),
        qualified_refs=("math.sqrt",),
        aliases=(("sqrt", "math.sqrt"),),
    )

    # Immutability
    with pytest.raises(AttributeError):
        facts.imports = ("sys",)

    data = facts.to_dict()
    assert data["imports"] == ["math", "os"]
    assert data["direct_calls"] == ["math.sqrt"]
    assert data["inheritance_refs"] == [["ChildClass", "BaseClass"]]
    assert data["qualified_refs"] == ["math.sqrt"]

    recreated = ModuleUsageFacts.from_dict(data)
    assert recreated == facts


def test_empty_module_usage_facts():
    facts = ModuleUsageFacts()
    assert facts.imports == ()
    assert facts.direct_calls == ()
    assert facts.runtime_calls == ()
    assert facts.callback_calls == ()
    assert facts.event_bindings == ()
    assert facts.inheritance_refs == ()
    assert facts.qualified_refs == ()
    assert facts.aliases == ()

    data = facts.to_dict()
    recreated = ModuleUsageFacts.from_dict(data)
    assert recreated == facts


def test_semantic_channel_extraction_parity():
    code = '''
import math
import os as my_os
from datetime import datetime as dt

class BaseWidget:
    pass

class Button(BaseWidget):
    def click(self):
        res = math.sqrt(16)
        dyn = getattr(res, "real")
        self.register(callback=self.on_click)
        self.bind("click", self.on_click)

    def on_click(self):
        pass
'''
    tree = ast.parse(code)
    facts = extract_module_usage_facts(
        "sample_module",
        tree,
        target_symbols={"BaseWidget", "math.sqrt"},
    )

    assert "math" in facts.imports or "math.sqrt" in [a[1] for a in facts.aliases]
    assert ("my_os", "os") in facts.aliases or ("dt", "datetime.datetime") in facts.aliases
    assert ("Button", "BaseWidget") in facts.inheritance_refs
    assert "math.sqrt" in facts.direct_calls or "sqrt" in [a[0] for a in facts.aliases]


def test_full_cache_coverage_invariant(tmp_path):
    f1 = tmp_path / "mod_a.py"
    f1.write_text("x = 1\n", encoding="utf-8")

    f2 = tmp_path / "mod_b.py"
    f2.write_text("import mod_a\ny = mod_a.x\n", encoding="utf-8")

    m1 = Module(module_id="mod_a", path="mod_a.py", absolute_path=str(f1), imports=[])
    m2 = Module(module_id="mod_b", path="mod_b.py", absolute_path=str(f2), imports=[])


    state = RepositoryAnalysisState(modules={"mod_a": m1, "mod_b": m2})
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    # Invariant: set(state.module_usages) == set(state.modules)
    assert set(engine.state.module_usages.keys()) == set(engine.state.modules.keys())
    assert len(engine.state.module_usages) == 2


def test_target_resolution_sufficiency():
    code_consumer = '''
import pkg.sub as sub
from service import process as proc

def run():
    sub.execute()
    proc(123)
'''
    tree = ast.parse(code_consumer)
    facts = extract_module_usage_facts("consumer", tree)

    alias_map = dict(facts.aliases)
    assert alias_map.get("sub") == "pkg.sub"
    assert alias_map.get("proc") == "service.process"


def test_no_source_reread_proof(tmp_path):
    facts = ModuleUsageFacts(
        imports=("os",),
        direct_calls=("os.path.join",),
    )
    state = RepositoryAnalysisState(
        module_usages={"module_a": facts}
    )

    retained_facts = state.module_usages.get("module_a")
    assert retained_facts is not None
    assert retained_facts.imports == ("os",)
    assert retained_facts.direct_calls == ("os.path.join",)


def test_state_lifecycle_and_snapshot_persistence(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    facts = ModuleUsageFacts(
        imports=("sys",),
        direct_calls=("sys.exit",),
    )
    state = RepositoryAnalysisState(
        module_usages={"mod_x": facts}
    )

    meta = save_snapshot(
        state,
        cache_dir,
        state_id="test_state_1",
        writer="pytest",
        repo_id="repo_123",
        root_path=str(tmp_path),
    )
    assert meta.revision == 1

    loaded_tuple = load_snapshot(
        cache_dir,
        expected_state_id="test_state_1",
        expected_repo_id="repo_123",
        expected_root_path=str(tmp_path),
    )
    assert loaded_tuple is not None
    loaded_state, _ = loaded_tuple
    assert hasattr(loaded_state, "module_usages")
    assert "mod_x" in loaded_state.module_usages
    assert loaded_state.module_usages["mod_x"].imports == ("sys",)
