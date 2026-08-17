"""
tests/test_completeness_freshness_parity_proof.py

Stage 3C.2a — Execution Completeness, Freshness & Full-State Parity Proof Tests.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine, IncrementalUpdateResult
from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState, FileDelta
from contextor.core.domain.module import Module
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.domain.usage_facts import ModuleUsageFacts, UsageDelta
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def _build_full_static_state(repo_dir: Path) -> RepositoryAnalysisState:
    """Canonical Oracle: builds fresh full static RepositoryAnalysisState by analyzing all files from clean state."""
    state = RepositoryAnalysisState(modules={})
    cache_dir = repo_dir / "cache_oracle"
    cache_dir.mkdir(exist_ok=True)
    reg_dir = repo_dir / "reg_oracle"
    reg_dir.mkdir(exist_ok=True)
    engine = IncrementalAnalysisEngine(
        state,
        PersistentIdentityRegistry(str(reg_dir)),
        FileStateManager(str(cache_dir)),
        str(repo_dir),
    )
    for py_file in sorted(repo_dir.rglob("*.py")):
        if any(part in {".git", ".venv", "__pycache__", "cache", "cache_oracle", "reg_oracle"} for part in py_file.parts):
            continue
        engine.update_file(str(py_file))
    return engine.state


def _assert_full_parity(incremental_state: RepositoryAnalysisState, oracle_state: RepositoryAnalysisState):
    """Asserts full canonical parity across all plan-controlled families."""
    # 1. Modules
    assert set(incremental_state.modules.keys()) == set(oracle_state.modules.keys())

    # 2. Definitions / Artifacts
    assert set(incremental_state.artifacts.keys()) == set(oracle_state.artifacts.keys())
    for mod_key, inc_art in incremental_state.artifacts.items():
        ora_art = oracle_state.artifacts[mod_key]
        assert inc_art.get("symbols") == ora_art.get("symbols")
        assert inc_art.get("own_symbols") == ora_art.get("own_symbols")

    # 3. ModuleUsageFacts
    assert set(incremental_state.module_usages.keys()) == set(oracle_state.module_usages.keys())
    for mod_name, inc_facts in incremental_state.module_usages.items():
        ora_facts = oracle_state.module_usages[mod_name]
        assert inc_facts.direct_calls == ora_facts.direct_calls
        assert inc_facts.qualified_refs == ora_facts.qualified_refs
        assert inc_facts.imports == ora_facts.imports
        assert inc_facts.aliases == ora_facts.aliases

    # 4. Artifact Consumption (with channels)
    for target, ora_entry in oracle_state.artifact_consumption.items():
        inc_entry = incremental_state.artifact_consumption.get(target, {})
        assert sorted(inc_entry.get("consumers", [])) == sorted(ora_entry.get("consumers", []))
        assert inc_entry.get("channels", {}) == ora_entry.get("channels", {})

    # 5. Dependency Graph
    if oracle_state.dependency_graph is not None:
        assert incremental_state.dependency_graph is not None
        assert incremental_state.dependency_graph.hard_edges == oracle_state.dependency_graph.hard_edges
        assert incremental_state.dependency_graph.soft_edges == oracle_state.dependency_graph.soft_edges

    # 6. Macro Graph Metrics
    if oracle_state.metrics is not None:
        assert incremental_state.metrics is not None
        assert incremental_state.metrics == oracle_state.metrics


def test_full_canonical_parity_import_and_graph(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_other = tmp_path / "other.py"
    f_other.write_text("def bar(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("import target\ntarget.foo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    engine.update_file(str(f_other))
    engine.update_file(str(f_consumer))

    # Add second import
    f_consumer.write_text("import target\nimport other\ntarget.foo()\nother.bar()\n", encoding="utf-8")
    res = engine.update_file(str(f_consumer))

    assert res.graph_state == "fresh"
    assert res.dependencies_state == "fresh"
    assert res.blast_radius_state == "fresh"
    assert res.artifact_consumption_state == "fresh"

    oracle = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle)


def test_full_canonical_parity_module_add_and_delete(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    res_add = engine.update_file(str(f_consumer))

    assert res_add.graph_state == "fresh"
    assert res_add.artifact_consumption_state == "fresh"

    oracle_add = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle_add)

    # Delete target
    f_target.unlink()
    res_del = engine.update_file(str(f_target))

    assert res_del.graph_state == "fresh"
    assert res_del.artifact_consumption_state == "fresh"

    oracle_del = _build_full_static_state(tmp_path)
    _assert_full_parity(engine.state, oracle_del)


def test_requires_resync_handling(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))

    # Mock RefreshPlanner to return requires_resync plan
    resync_plan = RefreshPlan(
        reparse_modules=(),
        recompute_modules=(),
        patch_families=("module_usages",),
        graph_recomputations=(),
        refresh_completeness="requires_resync",
        reason="Structural resync required",
    )
    with patch.object(RefreshPlanner, "plan_refresh", return_value=resync_plan):
        f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
        res = engine.update_file(str(f_target))

        assert res.graph_state == "stale"
        assert res.dependencies_state == "stale"
        assert res.blast_radius_state == "deferred"
        assert res.artifact_consumption_state == "stale"
        assert res.shadow_plan.refresh_completeness == "requires_resync"


def test_runtime_unresolved_handling(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))

    # Plan with runtime_unresolved certainty but complete refresh
    runtime_plan = RefreshPlan(
        reparse_modules=(),
        recompute_modules=(),
        patch_families=("module_usages", "artifact_consumption"),
        graph_recomputations=(),
        refresh_completeness="complete",
        semantic_certainty="runtime_unresolved",
        reason="Dynamic reflection unresolved",
    )
    with patch.object(RefreshPlanner, "plan_refresh", return_value=runtime_plan):
        f_target.write_text("def foo(): pass\ndef dynamic_call(): pass\n", encoding="utf-8")
        res = engine.update_file(str(f_target))

        assert res.artifact_consumption_state == "fresh"
        assert res.shadow_plan.semantic_certainty == "runtime_unresolved"


def test_cow_atomicity_across_families(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))
    engine.update_file(str(f_consumer))

    old_modules = engine.state.modules
    old_artifacts = engine.state.artifacts
    old_usages = engine.state.module_usages
    old_consumption = engine.state.artifact_consumption
    old_entry = old_consumption.get("target.foo", {})
    old_consumers = list(old_entry.get("consumers", []))

    # Modify consumer
    f_consumer.write_text("def own_func(): pass\n", encoding="utf-8")
    engine.update_file(str(f_consumer))

    # Assert old retained references were not mutated
    assert "target" in old_modules
    assert "target" in old_artifacts
    assert "consumer" in old_usages
    assert old_entry.get("consumers") == old_consumers


def test_fail_closed_on_unsupported_plan_item(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_target))

    # Mock RefreshPlan with unsupported patch family
    bad_plan = MagicMock()
    bad_plan.reparse_modules = ()
    bad_plan.recompute_modules = ()
    bad_plan.patch_families = ("unsupported_future_family",)
    bad_plan.graph_recomputations = ()
    bad_plan.refresh_completeness = "complete"

    with patch.object(RefreshPlanner, "plan_refresh", return_value=bad_plan):
        f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported patch family"):
            engine._apply_delta_and_commit(
                str(f_target),
                FileDelta(module_path="target"),
                UsageDelta(module_path="target"),
                bad_plan,
                [],
                {},
                ModuleUsageFacts(),
            )
