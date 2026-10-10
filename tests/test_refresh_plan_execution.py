"""
tests/test_refresh_plan_execution.py

Stage 3C.2 — RefreshPlan Execution Integration Tests.
Cases A through G with Plan-vs-Execution Equality & Full Rebuild Parity Oracle.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
from contextor.core.api.facade import ContextorFacade
from contextor.core.domain.module import Module
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry


def _build_full_static_state(repo_dir: Path) -> RepositoryAnalysisState:
    """Canonical Oracle: builds fresh full static RepositoryAnalysisState via real production ContextorFacade."""
    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors, errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None

    return hydrated.engine.state


def _assert_state_parity(incremental_state: RepositoryAnalysisState, oracle_state: RepositoryAnalysisState):
    """Asserts exact semantic parity between incremental state and full static rebuild oracle."""
    assert set(incremental_state.modules.keys()) == set(oracle_state.modules.keys())
    assert set(incremental_state.artifacts.keys()) == set(oracle_state.artifacts.keys())
    assert set(incremental_state.module_usages.keys()) == set(oracle_state.module_usages.keys())

    # ModuleUsageFacts parity
    for mod_name, inc_facts in incremental_state.module_usages.items():
        ora_facts = oracle_state.module_usages[mod_name]
        assert inc_facts.direct_calls == ora_facts.direct_calls
        assert inc_facts.qualified_refs == ora_facts.qualified_refs
        assert inc_facts.imports == ora_facts.imports
        assert inc_facts.aliases == ora_facts.aliases

    # Artifact consumption parity (exact target set, exact consumers, and exact channel sets)
    assert set(incremental_state.artifact_consumption.keys()) == set(oracle_state.artifact_consumption.keys())
    for target, ora_entry in oracle_state.artifact_consumption.items():
        inc_entry = incremental_state.artifact_consumption.get(target, {})
        assert sorted(inc_entry.get("consumers", [])) == sorted(ora_entry.get("consumers", []))
        inc_channels = inc_entry.get("channels", {})
        ora_channels = ora_entry.get("channels", {})
        assert set(inc_channels.keys()) == set(ora_channels.keys()), (
            f"Target '{target}' channel consumers mismatch: inc={inc_channels} vs ora={ora_channels}"
        )
        for consumer in ora_channels.keys():
            assert set(inc_channels[consumer]) == set(ora_channels[consumer]), (
                f"Target '{target}', Consumer '{consumer}' channel mismatch: "
                f"incremental={inc_channels.get(consumer)} vs full={ora_channels.get(consumer)}"
            )

    # Cycles parity
    assert incremental_state.cycles == oracle_state.cycles
    assert incremental_state.cycles_state == oracle_state.cycles_state


def test_case_a_body_only_retarget(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from target import foo, bar\nfoo()\n", encoding="utf-8")

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

    # Modify body: foo() -> bar()
    f_consumer.write_text("from target import foo, bar\nbar()\n", encoding="utf-8")
    res = engine.update_file(str(f_consumer))

    assert res.shadow_plan is not None
    assert res.execution_trace is not None
    trace = res.execution_trace

    # Plan vs Execution Equality
    assert trace["reparse_modules"] == res.shadow_plan.reparse_modules == ()
    assert trace["recompute_modules"] == res.shadow_plan.recompute_modules == ()
    assert set(
        trace["patch_families"]
    ) == set(
        res.shadow_plan.patch_families
    ) == {
        "definitions",
        "module_usages",
        "artifact_consumption",
        "cached_analytics",
    }

    assert trace["graph_recomputations"] == res.shadow_plan.graph_recomputations == ()

    # Full rebuild parity
    oracle = _build_full_static_state(tmp_path)
    _assert_state_parity(engine.state, oracle)


def test_case_b_import_change(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    f_other = tmp_path / "other.py"
    f_other.write_text("def baz(): pass\n", encoding="utf-8")
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

    # Add import
    f_consumer.write_text("import target\nimport other\ntarget.foo()\nother.baz()\n", encoding="utf-8")
    res = engine.update_file(str(f_consumer))

    trace = res.execution_trace
    assert trace["reparse_modules"] == res.shadow_plan.reparse_modules == ()
    assert "dependency_graph" in trace["patch_families"]
    assert "macro_metrics" in trace["graph_recomputations"]
    assert "reverse_blast_radius" in trace["graph_recomputations"]
    assert "cycles" in trace["graph_recomputations"]

    oracle = _build_full_static_state(tmp_path)
    _assert_state_parity(engine.state, oracle)


def test_case_c_reexport_retarget(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    f_init = pkg_dir / "__init__.py"
    f_init.write_text("from pkg.impl_a import foo_a as foo\n", encoding="utf-8")
    f_impl_a = pkg_dir / "impl_a.py"
    f_impl_a.write_text("def foo_a(): return 'impl_a'\n", encoding="utf-8")
    f_impl_b = pkg_dir / "impl_b.py"
    f_impl_b.write_text("def foo_b(): return 'impl_b'\n", encoding="utf-8")
    f_consumer = tmp_path / "consumer.py"
    f_consumer.write_text("from pkg import foo\nfoo()\n", encoding="utf-8")

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )
    engine.update_file(str(f_impl_a))
    engine.update_file(str(f_impl_b))
    engine.update_file(str(f_init))
    engine.update_file(str(f_consumer))

    # Retarget re-export: impl_a.foo_a -> impl_b.foo_b
    f_init.write_text("from pkg.impl_b import foo_b as foo\n", encoding="utf-8")
    res = engine.update_file(str(f_init))

    trace = res.execution_trace
    assert trace["reparse_modules"] == ()
    assert "consumer" in trace["recompute_modules"]

    oracle = _build_full_static_state(tmp_path)
    _assert_state_parity(engine.state, oracle)


def test_case_d_symbol_removal(tmp_path):
    f_target = tmp_path / "target.py"
    f_target.write_text("def foo(): pass\ndef bar(): pass\n", encoding="utf-8")
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

    # Remove symbol bar
    f_target.write_text("def foo(): pass\n", encoding="utf-8")
    res = engine.update_file(str(f_target))

    trace = res.execution_trace
    assert trace["reparse_modules"] == ()
    assert "definitions" in trace["patch_families"]

    oracle = _build_full_static_state(tmp_path)
    _assert_state_parity(engine.state, oracle)


def test_case_e_module_add(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    engine = IncrementalAnalysisEngine(
        RepositoryAnalysisState(modules={}),
        PersistentIdentityRegistry(str(tmp_path)),
        FileStateManager(str(cache_dir)),
        str(tmp_path),
    )

    f_new = tmp_path / "new_module.py"
    f_new.write_text("def helper(): pass\n", encoding="utf-8")
    res = engine.update_file(str(f_new))

    trace = res.execution_trace
    assert trace["reparse_modules"] == ()
    assert "modules" in trace["patch_families"]
    assert "macro_metrics" in trace["graph_recomputations"]
    assert "cycles" in trace["graph_recomputations"]

    oracle = _build_full_static_state(tmp_path)
    _assert_state_parity(engine.state, oracle)


def test_case_f_module_delete(tmp_path):
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

    # Delete target.py
    f_target.unlink()
    res = engine.update_file(str(f_target))

    trace = res.execution_trace
    assert trace["reparse_modules"] == ()
    assert "consumer" in trace["recompute_modules"]
    assert "modules" in trace["patch_families"]
    assert "cycles" in trace["graph_recomputations"]

    oracle = _build_full_static_state(tmp_path)
    _assert_state_parity(engine.state, oracle)


def test_case_g_noop_unchanged(tmp_path):
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

    # Re-saving same content
    res = engine.update_file(str(f_target))
    assert res.status == "UNCHANGED"


@pytest.mark.parametrize(
    "raw_map",
    [
        None,
        False,
        0,
        "",
        [],
        (),
        set(),
        ["bad"],
        17,
        [("provider", {"state": "stale"})],
    ],
    ids=repr,
)
def test_prepare_candidate_state_rejects_malformed_parse_freshness_maps(raw_map):
    state = RepositoryAnalysisState()
    state.module_parse_freshness = raw_map

    with pytest.raises(
        ValueError,
        match="Canonical module_parse_freshness is invalid",
    ):
        _prepare_candidate_state(state)

    assert state.module_parse_freshness is raw_map


def test_prepare_candidate_state_preserves_legacy_and_valid_parse_freshness_cow():
    legacy_state = RepositoryAnalysisState()
    del legacy_state.module_parse_freshness

    legacy_candidate = _prepare_candidate_state(legacy_state)

    assert legacy_candidate.module_parse_freshness == {}

    empty_state = RepositoryAnalysisState(module_parse_freshness={})
    empty_candidate = _prepare_candidate_state(empty_state)

    assert empty_candidate.module_parse_freshness == {}
    assert empty_candidate.module_parse_freshness is not empty_state.module_parse_freshness

    fresh_entry = {"state": "fresh"}
    stale_entry = {"state": "stale", "error": "invalid syntax"}
    malformed_entry = {"state": "unknown"}
    raw_map = {
        "fresh": fresh_entry,
        "stale": stale_entry,
        "malformed": malformed_entry,
    }
    state = RepositoryAnalysisState(module_parse_freshness=raw_map)

    candidate = _prepare_candidate_state(state)

    assert candidate.module_parse_freshness == raw_map
    assert candidate.module_parse_freshness is not raw_map
    assert candidate.module_parse_freshness["fresh"] is fresh_entry
    assert candidate.module_parse_freshness["stale"] is stale_entry
    assert candidate.module_parse_freshness["malformed"] is malformed_entry
    assert state.module_parse_freshness is raw_map
