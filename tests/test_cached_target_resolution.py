"""
tests/test_cached_target_resolution.py

Stage 3B.1b — Final Bootstrap and Cached-Resolution Parity Proof Tests.
"""

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.domain.module import Module
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.live_state.store import load_snapshot, save_snapshot
from contextor.core.reference.engine import _build_reexport_map, extract_module_usage_facts
from contextor.core.reference.resolution import _resolve_alias, _resolve_reexport
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def resolve_cached_target(symbol_name: str, consumer_facts: ModuleUsageFacts, reexports: dict) -> str:
    """
    Production-equivalent target resolution purely from cached ModuleUsageFacts and reexports.
    """
    resolved_alias = _resolve_alias(symbol_name, dict(consumer_facts.aliases))
    return _resolve_reexport(resolved_alias, reexports)


# ==========================================================
# PARITY CASES A - F
# ==========================================================


def test_case_a_name_collision():
    # module_a: def foo()
    # module_b: def foo()
    # consumer: from module_a import foo; foo()
    code_consumer = "from module_a import foo\nfoo()\n"
    tree = ast.parse(code_consumer)
    facts = extract_module_usage_facts("consumer", tree)

    resolved = resolve_cached_target("foo", facts, reexports={})
    assert resolved == "module_a.foo"
    assert resolved != "module_b.foo"


def test_case_b_module_alias():
    # consumer: import pkg.sub as alias; alias.foo()
    code_consumer = "import pkg.sub as alias\nalias.foo()\n"
    tree = ast.parse(code_consumer)
    facts = extract_module_usage_facts("consumer", tree)

    resolved = resolve_cached_target("alias.foo", facts, reexports={})
    assert resolved == "pkg.sub.foo"


def test_case_c_imported_symbol_alias():
    # consumer: from pkg import foo as bar; bar()
    code_consumer = "from pkg import foo as bar\nbar()\n"
    tree = ast.parse(code_consumer)
    facts = extract_module_usage_facts("consumer", tree)

    resolved = resolve_cached_target("bar", facts, reexports={})
    assert resolved == "pkg.foo"


def test_case_d_fully_qualified_call():
    # consumer: import pkg.mod; pkg.mod.foo()
    code_consumer = "import pkg.mod\npkg.mod.foo()\n"
    tree = ast.parse(code_consumer)
    facts = extract_module_usage_facts("consumer", tree)

    resolved = resolve_cached_target("pkg.mod.foo", facts, reexports={})
    assert resolved == "pkg.mod.foo"


def test_case_e_reexport(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    f_init = pkg_dir / "__init__.py"
    f_init.write_text("from .impl import foo\n", encoding="utf-8")
    f_impl = pkg_dir / "impl.py"
    f_impl.write_text("def foo(): pass\n", encoding="utf-8")

    from contextor.core.domain.imports import ImportRef
    imp_init = ImportRef(module=".impl", level=1, names=["foo"], is_from_import=True)
    m_init = Module(module_id="pkg.__init__", path="pkg/__init__.py", absolute_path=str(f_init), imports=[imp_init])
    m_impl = Module(module_id="pkg.impl", path="pkg/impl.py", absolute_path=str(f_impl), imports=[])

    modules = {"pkg.__init__": m_init, "pkg.impl": m_impl}

    reexports = _build_reexport_map(modules)

    code_consumer = "from pkg import foo\nfoo()\n"
    tree_consumer = ast.parse(code_consumer)
    facts_consumer = extract_module_usage_facts("consumer", tree_consumer)

    resolved = resolve_cached_target("foo", facts_consumer, reexports)
    assert resolved == "pkg.impl.foo"



def test_case_f_direct_imported_call():
    # consumer: from pkg.mod import foo; foo()
    code_consumer = "from pkg.mod import foo\nfoo()\n"
    tree_consumer = ast.parse(code_consumer)
    facts_consumer = extract_module_usage_facts("consumer", tree_consumer)

    resolved = resolve_cached_target("foo", facts_consumer, reexports={})
    assert resolved == "pkg.mod.foo"


# ==========================================================
# NO UNCHANGED SOURCE REREAD INVARIANT
# ==========================================================


def test_no_unchanged_source_reread_during_target_resolution(tmp_path):
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from module_a import foo\nfoo()\n", encoding="utf-8")

    tree = ast.parse(f_consumer.read_text(encoding="utf-8"))
    facts = extract_module_usage_facts("consumer", tree)

    state = RepositoryAnalysisState(
        module_usages={"consumer": facts}
    )

    # Resolution using RAM facts must succeed even if opening consumer file raises OSError
    with patch.object(Path, "read_text", side_effect=OSError("Disk read prohibited!")):
        ram_facts = state.module_usages["consumer"]
        target = resolve_cached_target("foo", ram_facts, reexports={})
        assert target == "module_a.foo"


def test_bootstrap_no_duplicate_repo_wide_source_reread(tmp_path):
    f1 = tmp_path / "mod_a.py"
    f1.write_text("def foo(): pass\n", encoding="utf-8")

    m1 = Module(module_id="mod_a", path="mod_a.py", absolute_path=str(f1), imports=[])
    state = RepositoryAnalysisState(modules={"mod_a": m1})

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Pre-populate module_usages as normal full analysis does
    state.module_usages["mod_a"] = extract_module_usage_facts("mod_a", m1.ast_tree)

    # When IncrementalAnalysisEngine initializes over already-populated state, ZERO source reads occur
    with patch.object(Path, "read_text", side_effect=AssertionError("Source read prohibited on populated state!")):
        engine = IncrementalAnalysisEngine(
            state,
            PersistentIdentityRegistry(str(tmp_path)),
            FileStateManager(str(cache_dir)),
            str(tmp_path),
        )
        assert set(engine.state.module_usages.keys()) == set(engine.state.modules.keys())
