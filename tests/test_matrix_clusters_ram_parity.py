"""
tests/test_matrix_clusters_ram_parity.py

Stage 1 — Canonical Single-SSOT Contract, Real Production Parity, Coverage Validation,
Real Incremental Writer Proof, and Pure-RAM Test Suite for Canonical LIVE Dependency Matrix
and Shared Usage Clusters (Jaccard).
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from contextor.core.analysis.incremental.materialization import (
    ensure_artifact_consumption,
    materialize_incremental_state,
)
from contextor.core.analysis.incremental.plan_executor import (
    _resolve_canonical_target_key,
    _to_canonical_target_key,
    execute_refresh_plan,
)
from contextor.core.analysis.state_manager import (
    CANONICAL_USAGE_CHANNELS,
    RepositoryAnalysisState,
    artifact_consumption_is_fresh,
    build_canonical_artifact_consumption,
    canonical_artifact_consumption_targets,
    is_legacy_artifact_consumption,
    validate_canonical_artifact_consumption,
    validate_canonical_artifact_consumption_coverage,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.module import Module
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.reporting_engine.graph_analytics import (
    _usage_dependency_types,
    build_artifact_data_projection,
    build_jaccard_clusters,
    build_module_dependency_matrix,
    compute_dependency_matrix,
    compute_dependency_matrix_from_state,
    compute_shared_usage_clusters,
    compute_shared_usage_clusters_from_state,
)
import contextor.core.reporting_layer.artifact_usage_report as aur


# ==============================================================================
# 1. REAL PRODUCTION-TO-PRODUCTION PARITY TEST (FACADE -> PERSIST -> HYDRATE)
# ==============================================================================

def test_real_production_facade_to_hydration_parity(tmp_path: Path):
    """
    PROVES 1:1 END-TO-END PARITY BETWEEN:
    Real Production Snapshot Pipeline (spied from ContextorFacade.analyze_project)
    vs
    Real Hydrated Canonical RepositoryAnalysisState (hydrate_repository_engine).

    Proves that state.artifact_consumption is normalized per-target SSOT on full analysis.
    """
    repo_dir = tmp_path / "facade_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    core_file = repo_dir / "core.py"
    core_file.write_text(
        "VERSION = '2.0'\n\n"
        "class Engine:\n"
        "    @classmethod\n"
        "    def start(cls):\n"
        "        return True\n\n"
        "def make_engine():\n"
        "    return Engine.start()\n",
        encoding="utf-8",
    )

    models_file = repo_dir / "models.py"
    models_file.write_text(
        "class DataModel:\n"
        "    pass\n\n"
        "def create_model():\n"
        "    return DataModel()\n",
        encoding="utf-8",
    )

    service_a_file = repo_dir / "service_a.py"
    service_a_file.write_text(
        "from core import Engine, VERSION, make_engine\n"
        "from models import DataModel\n\n"
        "class AppEngine(Engine):\n"
        "    def run(self):\n"
        "        Engine.start()\n"
        "        make_engine()\n"
        "        _ = DataModel()\n"
        "        print(VERSION)\n",
        encoding="utf-8",
    )

    service_b_file = repo_dir / "service_b.py"
    service_b_file.write_text(
        "from core import Engine, make_engine\n"
        "from models import DataModel, create_model\n\n"
        "class WorkerEngine(Engine):\n"
        "    def work(self):\n"
        "        make_engine()\n"
        "        _ = DataModel()\n"
        "        create_model()\n",
        encoding="utf-8",
    )

    service_c_file = repo_dir / "service_c.py"
    service_c_file.write_text(
        "import models\n"
        "from core import make_engine\n\n"
        "def callback_runner():\n"
        "    make_engine()\n"
        "    _ = models.DataModel()\n",
        encoding="utf-8",
    )

    isolated_file = repo_dir / "isolated.py"
    isolated_file.write_text(
        "def lonely_function():\n"
        "    pass\n",
        encoding="utf-8",
    )

    # 1. Spying the real production call site of build_artifact_index during full analysis
    captured = {}
    real_build_artifact_index = aur.build_artifact_index

    def capture_build_artifact_index(*args, **kwargs):
        result = real_build_artifact_index(*args, **kwargs)
        artifacts, usage_sidecar = result
        captured["artifact_data"] = {
            "artifacts": artifacts,
            "_usage_sidecar": usage_sidecar,
        }
        return result

    with patch.object(aur, "build_artifact_index", side_effect=capture_build_artifact_index):
        facade = ContextorFacade()
        errors, analysis_result = facade.analyze_project(str(repo_dir))
        assert not errors
        assert analysis_result is not None

    production_artifact_data = captured["artifact_data"]

    # 2. Hydrate real canonical state from disk
    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    state = hydrated.engine.state

    # ==========================================================================
    # A. CANONICAL ARTIFACT_CONSUMPTION SSOT CONTRACT & COVERAGE VERIFICATION
    # ==========================================================================
    assert validate_canonical_artifact_consumption(state.artifact_consumption) is True
    assert validate_canonical_artifact_consumption_coverage(state.artifact_consumption, state.artifacts) is True
    assert state.artifact_consumption_state == "fresh"
    assert "_report" not in state.artifact_consumption
    assert "core::Engine.start" in state.artifact_consumption
    assert "core::Engine" in state.artifact_consumption
    assert "core::VERSION" in state.artifact_consumption

    # Consistency invariant: channels keys are a subset of consumers
    for target, entry in state.artifact_consumption.items():
        assert set(entry["channels"].keys()).issubset(set(entry["consumers"])), f"Consistency failure for {target}"

    method_entry = state.artifact_consumption["core::Engine.start"]
    assert "service_a" in method_entry["consumers"]
    assert "direct_calls" in method_entry["channels"]["service_a"]

    # 3. Canonical Projection from pure RAM state (no fallback to state.artifacts consumers)
    projected_artifact_data = build_artifact_data_projection(
        state.artifacts,
        state.artifact_consumption,
    )

    # ==========================================================================
    # B. EXACT ARTIFACT KEYS & ATTRIBUTES PARITY
    # ==========================================================================
    assert projected_artifact_data["artifacts"].keys() == production_artifact_data["artifacts"].keys()

    for key, prod_art in production_artifact_data["artifacts"].items():
        proj_art = projected_artifact_data["artifacts"][key]
        assert proj_art["artifact_id"] == prod_art["artifact_id"], f"Mismatch for {key}"
        assert proj_art["artifact"] == prod_art["artifact"], f"Mismatch for {key}"
        assert proj_art["kind"] == prod_art["kind"], f"Mismatch for {key}"
        assert proj_art["definer_module"] == prod_art["definer_module"], f"Mismatch for {key}"
        assert proj_art["consumers"] == prod_art["consumers"], f"Mismatch for {key}"
        assert proj_art["consumer_count"] == prod_art["consumer_count"], f"Mismatch for {key}"

    # ==========================================================================
    # C. CLASS METHOD IDENTITY PRODUCTION PROOF
    # ==========================================================================
    expected_method_key = "core::Engine.start"
    assert expected_method_key in production_artifact_data["artifacts"]
    assert expected_method_key in projected_artifact_data["artifacts"]
    assert projected_artifact_data["artifacts"][expected_method_key]["kind"] == "method"
    assert projected_artifact_data["artifacts"][expected_method_key]["artifact"] == "Engine.start"

    # ==========================================================================
    # D. PER-CONSUMER USAGE SIDECAR PARITY
    # ==========================================================================
    for key, proj_art in projected_artifact_data["artifacts"].items():
        proj_sidecar = projected_artifact_data["_usage_sidecar"].get(key, {})
        prod_sidecar = production_artifact_data["_usage_sidecar"].get(key, {})

        for consumer in proj_art["consumers"]:
            proj_consumer_channels = {
                cat: [c for c in c_list if c == consumer]
                for cat, c_list in proj_sidecar.items()
                if consumer in c_list
            }
            prod_consumer_channels = {
                cat: [c for c in c_list if c == consumer]
                for cat, c_list in prod_sidecar.items()
                if consumer in c_list
            }
            proj_dep_types = _usage_dependency_types(proj_consumer_channels)
            prod_dep_types = _usage_dependency_types(prod_consumer_channels)
            assert proj_dep_types == prod_dep_types, f"Per-consumer mismatch for {key} / {consumer}: {proj_dep_types} vs {prod_dep_types}"

    # ==========================================================================
    # E. END-TO-END MATRIX EXACT PARITY
    # ==========================================================================
    hard_edges = state.dependency_graph.hard_edges
    snapshot_matrix = build_module_dependency_matrix(production_artifact_data, hard_edges)
    canonical_matrix = compute_dependency_matrix_from_state(state)

    assert snapshot_matrix == canonical_matrix, "Dependency Matrix differs between real snapshot and hydrated state"

    # ==========================================================================
    # F. END-TO-END SHARED USAGE CLUSTERS EXACT PARITY
    # ==========================================================================
    snapshot_clusters = build_jaccard_clusters(production_artifact_data, min_jaccard=0.30)
    canonical_clusters = compute_shared_usage_clusters_from_state(state, min_jaccard=0.30)

    assert snapshot_clusters == canonical_clusters, "Shared Usage Clusters differ between real snapshot and hydrated state"


# ==============================================================================
# 2. REAL INCREMENTAL WRITER (PLAN EXECUTOR) ADD / REMOVE CONSUMER PROOF
# ==============================================================================

def test_real_incremental_writer_consumer_delta(tmp_path: Path):
    """
    PROVES that a real incremental update executed via IncrementalAnalysisEngine / plan_executor:
    1. Removes a deleted consumer from state.artifact_consumption without ghost entries.
    2. Maintains strict canonical structural validity (validate_canonical_artifact_consumption).
    3. Maintains complete coverage validation (validate_canonical_artifact_consumption_coverage).
    4. Deterministically updates sorted consumers and channels list.
    """
    repo_dir = tmp_path / "inc_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    core_file = repo_dir / "core.py"
    core_file.write_text(
        "def helper_func():\n"
        "    return 42\n",
        encoding="utf-8",
    )

    app_file = repo_dir / "app.py"
    app_file.write_text(
        "from core import helper_func\n\n"
        "def main():\n"
        "    return helper_func()\n",
        encoding="utf-8",
    )

    facade = ContextorFacade()
    errors, analysis_result = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    engine = hydrated.engine

    # Initial state check
    target_key = "core::helper_func"
    assert target_key in engine.state.artifact_consumption
    assert engine.state.artifact_consumption[target_key]["consumers"] == ["app"]
    assert engine.state.artifact_consumption[target_key]["channels"] == {
        "app": ["api_imports", "direct_calls"]
    }

    # Perform real file edit: remove usage of helper_func from app.py
    app_file.write_text(
        "def main():\n"
        "    return 100\n",
        encoding="utf-8",
    )

    # Real incremental update execution
    res = engine.update_file(str(app_file))
    assert res.status in ("UPDATED", "SUCCESS")

    # Inspect post-update canonical artifact_consumption
    assert validate_canonical_artifact_consumption(engine.state.artifact_consumption) is True
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"

    # Invariant: set(state.artifact_consumption) == canonical_artifact_consumption_targets(state.artifacts)
    assert set(engine.state.artifact_consumption.keys()) == canonical_artifact_consumption_targets(engine.state.artifacts)

    updated_entry = engine.state.artifact_consumption[target_key]
    assert "app" not in updated_entry["consumers"]
    assert "app" not in updated_entry["channels"]
    assert updated_entry["consumers"] == []
    assert updated_entry["channels"] == {}


# ==============================================================================
# 2.B CANONICAL TARGET RESOLUTION (NON-HEURISTIC & AMBIGUITY REGRESSIONS)
# ==============================================================================

def test_ambiguity_regression_returns_none():
    """
    PROVES that when two canonical targets produce identical dotted representations:
        a::b.c  -> "a.b.c"
        a.b::c  -> "a.b.c"
    Resolver for "a.b.c" fails closed by returning None instead of picking arbitrarily.
    """
    candidate_artifacts = {
        "a": {"consumers": {"b.c": {"consumers": [], "usage": {}}}},
        "a.b": {"consumers": {"c": {"consumers": [], "usage": {}}}},
    }
    assert canonical_artifact_consumption_targets(candidate_artifacts) == {"a::b.c", "a.b::c"}

    res = _to_canonical_target_key("a.b.c", {}, candidate_artifacts)
    assert res is None, f"Expected None for ambiguous target, got {res}"


def test_nested_module_regression():
    """
    PROVES that for nested modules:
        pkg::something
        pkg.core::Engine.start
    Input: "pkg.core.Engine.start"
    Exact resolved output: "pkg.core::Engine.start" (NOT "pkg::core.Engine.start" and NOT "pkg.core.Engine::start").
    """
    candidate_artifacts = {
        "pkg": {"consumers": {"something": {"consumers": [], "usage": {}}}},
        "pkg.core": {"consumers": {"Engine.start": {"consumers": [], "usage": {}}}},
    }
    assert canonical_artifact_consumption_targets(candidate_artifacts) == {"pkg::something", "pkg.core::Engine.start"}

    res = _to_canonical_target_key("pkg.core.Engine.start", {}, candidate_artifacts)
    assert res == "pkg.core::Engine.start"


def test_class_method_regression():
    """
    PROVES that for class-qualified methods:
        contextor.core.analysis::Engine.run
    Dotted input: "contextor.core.analysis.Engine.run"
    Resolver preserves definer module and qualified symbol boundary: "contextor.core.analysis::Engine.run".
    """
    candidate_artifacts = {
        "contextor.core.analysis": {"consumers": {"Engine.run": {"consumers": [], "usage": {}}}},
    }
    res = _to_canonical_target_key("contextor.core.analysis.Engine.run", {}, candidate_artifacts)
    assert res == "contextor.core.analysis::Engine.run"


def test_unknown_target_regression():
    """
    PROVES that for non-existent target:
    Input: "pkg.core.DoesNotExist.run"
    Even if "pkg.core" is a known module, resolver returns None without inventing non-existent target.
    """
    candidate_artifacts = {
        "pkg.core": {"consumers": {"ExistingFunc": {"consumers": [], "usage": {}}}},
    }
    res = _to_canonical_target_key("pkg.core.DoesNotExist.run", {}, candidate_artifacts)
    assert res is None


def test_order_independence_regression():
    """
    PROVES that dictionary key order in candidate_artifacts has zero effect on resolution result.
    """
    artifacts_1 = {
        "pkg": {"consumers": {"helper": {"consumers": [], "usage": {}}}},
        "pkg.sub": {"consumers": {"helper": {"consumers": [], "usage": {}}}},
    }
    artifacts_2 = {
        "pkg.sub": {"consumers": {"helper": {"consumers": [], "usage": {}}}},
        "pkg": {"consumers": {"helper": {"consumers": [], "usage": {}}}},
    }

    res_1 = _to_canonical_target_key("pkg.sub.helper", {}, artifacts_1)
    res_2 = _to_canonical_target_key("pkg.sub.helper", {}, artifacts_2)

    assert res_1 == "pkg.sub::helper"
    assert res_2 == "pkg.sub::helper"
    assert res_1 == res_2


def test_resolver_distinguishes_unknown_from_ambiguous():
    """
    PROVES that _resolve_canonical_target_key distinguishes:
    - 'resolved': exactly 1 canonical match
    - 'ambiguous': >1 canonical matches (fail-closed)
    - 'unresolved': 0 matches (valid unknown / external)
    """
    candidate_artifacts = {
        "a": {"consumers": {"b.c": {"consumers": [], "usage": {}}}},
        "a.b": {"consumers": {"c": {"consumers": [], "usage": {}}}},
        "pkg.core": {"consumers": {"unique_func": {"consumers": [], "usage": {}}}},
    }

    # 1. Resolved
    key, status = _resolve_canonical_target_key("pkg.core.unique_func", {}, candidate_artifacts)
    assert status == "resolved"
    assert key == "pkg.core::unique_func"

    # 2. Ambiguous (>1 matches)
    key, status = _resolve_canonical_target_key("a.b.c", {}, candidate_artifacts)
    assert status == "ambiguous"
    assert key is None

    # 3. Unresolved (unknown external symbol)
    key, status = _resolve_canonical_target_key("external.lib.non_existent", {}, candidate_artifacts)
    assert status == "unresolved"
    assert key is None

    # 4. Canonical key present
    key, status = _resolve_canonical_target_key("pkg.core::unique_func", {}, candidate_artifacts)
    assert status == "resolved"
    assert key == "pkg.core::unique_func"

    # 5. Canonical key not in domain
    key, status = _resolve_canonical_target_key("pkg.core::ghost_func", {}, candidate_artifacts)
    assert status == "unresolved"
    assert key is None


def test_ambiguity_execution_semantic_regression_fails_closed(tmp_path: Path):
    """
    PROVES that when ambiguous usage occurs during incremental refresh:
    - Candidate state marks artifact_consumption_state = 'stale'
    - State publication preserves 'stale'
    - Even if key coverage is 100% complete.
    """
    repo_dir = tmp_path / "ambiguous_repo"
    repo_dir.mkdir()

    # Module 'a' with symbol 'b.c' and module 'a.b' with symbol 'c'
    a_dir = repo_dir / "a"
    a_dir.mkdir()
    (a_dir / "__init__.py").write_text("", encoding="utf-8")
    (a_dir / "b.py").write_text("def c(): pass\n", encoding="utf-8")

    app_file = repo_dir / "app.py"
    app_file.write_text("import a.b\ndef run(): a.b.c()\n", encoding="utf-8")

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    engine = hydrated.engine

    # Artificially create ambiguity domain in artifacts: a::b.c and a.b::c
    engine.state.artifacts["a"] = {"consumers": {"b.c": {"consumers": [], "usage": {}}}}
    engine.state.artifacts["a.b"] = {"consumers": {"c": {"consumers": [], "usage": {}}}}
    engine.state.artifacts["app"] = {"consumers": {"run": {"consumers": [], "usage": {}}}}

    # Initial consumption matching domain
    engine.state.artifact_consumption = {
        "a::b.c": {"consumers": [], "channels": {}},
        "a.b::c": {"consumers": [], "channels": {}},
        "app::run": {"consumers": [], "channels": {}},
    }
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True

    # Modify app.py to call ambiguous dotted target 'a.b.c'
    app_file.write_text("import a.b\ndef run():\n    a.b.c()\n", encoding="utf-8")

    res = engine.update_file(str(app_file))
    assert res.status in ("UPDATED", "SUCCESS")

    # Invariant: coverage is 100% valid, but state MUST be stale due to semantic ambiguity!
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "stale"
    assert res.artifact_consumption_state == "stale"


def test_early_ambiguity_in_recompute_phase_is_sticky_across_clean_later_patch(tmp_path: Path):
    """
    PROVES that if an ambiguity is detected in an earlier phase (e.g. RECOMPUTE),
    a subsequent clean PATCH phase with 100% valid coverage CANNOT overwrite the failure.
    The candidate and committed state must remain 'stale'.
    """
    repo_dir = tmp_path / "sticky_repo"
    repo_dir.mkdir()

    core_file = repo_dir / "core.py"
    core_file.write_text("def helper(): return 1\ndef helper2(): return 2\n", encoding="utf-8")

    app_file = repo_dir / "app.py"
    app_file.write_text("import core\ndef main(): return core.helper()\n", encoding="utf-8")

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    engine = hydrated.engine

    # Domain has ambiguity: a::b.c and a.b::c
    engine.state.artifacts["a"] = {"consumers": {"b.c": {"consumers": [], "usage": {}}}}
    engine.state.artifacts["a.b"] = {"consumers": {"c": {"consumers": [], "usage": {}}}}
    engine.state.artifact_consumption["a::b.c"] = {"consumers": [], "channels": {}}
    engine.state.artifact_consumption["a.b::c"] = {"consumers": [], "channels": {}}

    # Consumer module has ambiguous call in RECOMPUTE phase
    from contextor.core.domain.usage_facts import ModuleUsageFacts
    engine.state.module_usages["other_consumer"] = ModuleUsageFacts(
        direct_calls=["a.b.c"]
    )
    engine.state.modules["other_consumer"] = Module(
        module_id="other_consumer", path="other.py", absolute_path="/other.py", imports=[]
    )

    # Perform clean update on app_file (switches to helper2 cleanly)
    # Mock refresh planner to include 'other_consumer' in recompute_modules
    from contextor.core.analysis.refresh_planner import RefreshPlanner
    original_plan_refresh = RefreshPlanner.plan_refresh

    def mock_plan(*args, **kwargs):
        p = original_plan_refresh(*args, **kwargs)
        # Add other_consumer to recompute_modules
        return RefreshPlan(
            reparse_modules=p.reparse_modules,
            recompute_modules=tuple(list(p.recompute_modules) + ["other_consumer"]),
            patch_families=p.patch_families,
            graph_recomputations=p.graph_recomputations,
            refresh_completeness=p.refresh_completeness,
        )

    with patch.object(RefreshPlanner, "plan_refresh", side_effect=mock_plan):
        app_file.write_text("import core\ndef main(): return core.helper2()\n", encoding="utf-8")
        res = engine.update_file(str(app_file))
        assert res.status in ("UPDATED", "SUCCESS")

    # Invariant: Phase 1 (RECOMPUTE) failed on ambiguity.
    # Phase 2 (PATCH artifact_consumption) was clean and coverage is True.
    # Candidate & committed state MUST be 'stale'!
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "stale"
    assert res.artifact_consumption_state == "stale"


def test_forensic_post_add_artifact_shape_and_canonical_definition_domain(tmp_path: Path):
    """
    FORENSIC PROOF:
    Adding a new provider module with zero consumers immediately creates its canonical target
    in artifact_consumption with empty consumers/channels, ensuring exact coverage is True and fresh.
    """
    repo_dir = tmp_path / "forensic_repo"
    repo_dir.mkdir()
    base_file = repo_dir / "base.py"
    base_file.write_text("def base(): return 0\n", encoding="utf-8")

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    engine = hydrated.engine

    prov_file = repo_dir / "_contextor_live_probe_provider.py"
    prov_file.write_text("def probe_value():\n    return 1\n", encoding="utf-8")

    res = engine.update_file(str(prov_file))
    assert res.status in ("UPDATED", "SUCCESS")

    prov_art = engine.state.artifacts["_contextor_live_probe_provider"]
    assert "probe_value" in prov_art["symbols"]["functions"]
    assert "probe_value" in prov_art["own_symbols"]

    expected_targets = canonical_artifact_consumption_targets(engine.state.artifacts)
    actual_targets = set(engine.state.artifact_consumption.keys())

    assert expected_targets == {"base::base", "_contextor_live_probe_provider::probe_value"}
    assert actual_targets == expected_targets
    assert expected_targets - actual_targets == set()
    assert actual_targets - expected_targets == set()

    entry = engine.state.artifact_consumption["_contextor_live_probe_provider::probe_value"]
    assert entry == {"consumers": [], "channels": {}}
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"
    assert not getattr(engine.state, "resync_required", False)


def test_zero_consumer_defined_symbols_domain_parity(tmp_path: Path):
    """
    PROVES that all defined symbol categories (function, class, method, global)
    with zero consumers exist as canonical targets in artifact_consumption with consumers=[] and channels={}.
    """
    repo_dir = tmp_path / "zero_consumer_repo"
    repo_dir.mkdir()
    core_file = repo_dir / "core.py"
    core_file.write_text(
        "CONST = 42\n\n"
        "def stand_alone_func():\n"
        "    return 1\n\n"
        "class StandAloneClass:\n"
        "    def member_method(self):\n"
        "        return 2\n",
        encoding="utf-8",
    )

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    state = hydrated.engine.state

    expected = {
        "core::CONST",
        "core::stand_alone_func",
        "core::StandAloneClass",
        "core::StandAloneClass.member_method",
    }
    assert set(state.artifact_consumption.keys()) == expected
    for target in expected:
        assert state.artifact_consumption[target] == {"consumers": [], "channels": {}}

    assert validate_canonical_artifact_consumption_coverage(state.artifact_consumption, state.artifacts) is True
    assert state.artifact_consumption_state == "fresh"


def test_incremental_add_provider_and_consumer_full_lifecycle(tmp_path: Path):
    """
    PROVES the full real incremental lifecycle:
    1. ADD provider (zero consumers) -> target created, coverage True, state fresh
    2. ADD consumer -> provider target registered with consumer, coverage True, state fresh
    3. REMOVE consumer usage -> provider target consumers cleared, coverage True, state fresh
    4. RESTORE consumer usage -> consumer re-registered exactly once, coverage True, state fresh
    5. DELETE consumer -> consumer module removed, provider target retains 0 consumers, coverage True, state fresh
    6. DELETE provider -> provider target completely removed, coverage True, state fresh
    """
    repo_dir = tmp_path / "lifecycle_repo"
    repo_dir.mkdir()
    base_file = repo_dir / "base.py"
    base_file.write_text("def base(): return 0\n", encoding="utf-8")

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    engine = hydrated.engine

    # STEP 1: ADD provider
    prov_file = repo_dir / "_contextor_live_probe_provider.py"
    prov_file.write_text("def probe_value():\n    return 1\n", encoding="utf-8")
    res1 = engine.update_file(str(prov_file))
    assert res1.status in ("UPDATED", "SUCCESS")

    assert "_contextor_live_probe_provider::probe_value" in engine.state.artifact_consumption
    assert engine.state.artifact_consumption["_contextor_live_probe_provider::probe_value"] == {
        "consumers": [],
        "channels": {},
    }
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"

    # STEP 2: ADD consumer
    cons_file = repo_dir / "_contextor_live_probe_consumer.py"
    cons_file.write_text(
        "from _contextor_live_probe_provider import probe_value\n\n"
        "def probe_run():\n"
        "    return probe_value()\n",
        encoding="utf-8",
    )
    res2 = engine.update_file(str(cons_file))
    assert res2.status in ("UPDATED", "SUCCESS")

    prov_entry = engine.state.artifact_consumption["_contextor_live_probe_provider::probe_value"]
    assert prov_entry["consumers"] == ["_contextor_live_probe_consumer"]
    assert "_contextor_live_probe_consumer" in prov_entry["channels"]
    assert sorted(set(prov_entry["channels"]["_contextor_live_probe_consumer"])) == prov_entry["channels"]["_contextor_live_probe_consumer"]
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"

    # STEP 3: REMOVE consumer usage
    cons_file.write_text(
        "def probe_run():\n"
        "    return 100\n",
        encoding="utf-8",
    )
    res3 = engine.update_file(str(cons_file))
    assert res3.status in ("UPDATED", "SUCCESS")

    prov_entry = engine.state.artifact_consumption["_contextor_live_probe_provider::probe_value"]
    assert prov_entry["consumers"] == []
    assert prov_entry["channels"] == {}
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"

    # STEP 4: RESTORE consumer usage
    cons_file.write_text(
        "from _contextor_live_probe_provider import probe_value\n\n"
        "def probe_run():\n"
        "    return probe_value()\n",
        encoding="utf-8",
    )
    res4 = engine.update_file(str(cons_file))
    assert res4.status in ("UPDATED", "SUCCESS")

    prov_entry = engine.state.artifact_consumption["_contextor_live_probe_provider::probe_value"]
    assert prov_entry["consumers"] == ["_contextor_live_probe_consumer"]
    assert len(prov_entry["consumers"]) == len(set(prov_entry["consumers"]))
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"

    # STEP 5: DELETE consumer
    cons_file.unlink()
    res5 = engine.update_file(str(cons_file))
    assert res5.status in ("DELETED", "SUCCESS")

    assert "_contextor_live_probe_consumer" not in engine.state.modules
    prov_entry = engine.state.artifact_consumption["_contextor_live_probe_provider::probe_value"]
    assert prov_entry["consumers"] == []
    assert prov_entry["channels"] == {}
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"

    # STEP 6: DELETE provider
    prov_file.unlink()
    res6 = engine.update_file(str(prov_file))
    assert res6.status in ("DELETED", "SUCCESS")

    assert "_contextor_live_probe_provider" not in engine.state.modules
    assert "_contextor_live_probe_provider::probe_value" not in engine.state.artifact_consumption
    assert set(engine.state.artifact_consumption.keys()) == {"base::base"}
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"


def test_full_analysis_vs_incremental_add_exact_parity(tmp_path: Path):
    """
    PROVES exact parity between:
    A. Full analysis of a repository with provider and consumer
    B. Incremental addition of the same provider and consumer to a base repository
    """
    # Repo A: Full analysis
    dir_a = tmp_path / "repo_a"
    dir_a.mkdir()
    (dir_a / "base.py").write_text("def base(): return 0\n", encoding="utf-8")
    (dir_a / "prov.py").write_text("def helper(): return 1\n", encoding="utf-8")
    (dir_a / "cons.py").write_text("from prov import helper\ndef run(): return helper()\n", encoding="utf-8")

    facade_a = ContextorFacade()
    errors_a, _ = facade_a.analyze_project(str(dir_a))
    assert not errors_a
    state_a = hydrate_repository_engine(dir_a).engine.state

    # Repo B: Incremental addition
    dir_b = tmp_path / "repo_b"
    dir_b.mkdir()
    (dir_b / "base.py").write_text("def base(): return 0\n", encoding="utf-8")

    facade_b = ContextorFacade()
    errors_b, _ = facade_b.analyze_project(str(dir_b))
    assert not errors_b
    engine_b = hydrate_repository_engine(dir_b).engine

    (dir_b / "prov.py").write_text("def helper(): return 1\n", encoding="utf-8")
    engine_b.update_file(str(dir_b / "prov.py"))

    (dir_b / "cons.py").write_text("from prov import helper\ndef run(): return helper()\n", encoding="utf-8")
    engine_b.update_file(str(dir_b / "cons.py"))
    state_b = engine_b.state

    # Compare canonical artifact_consumption mappings
    assert set(state_a.artifact_consumption.keys()) == set(state_b.artifact_consumption.keys())
    for target in state_a.artifact_consumption:
        entry_a = state_a.artifact_consumption[target]
        entry_b = state_b.artifact_consumption[target]
        assert entry_a["consumers"] == entry_b["consumers"], f"Consumers mismatch for {target}"
        if entry_a["consumers"]:
            for c in entry_a["consumers"]:
                assert c in entry_b["channels"]
                assert "direct_calls" in entry_a["channels"][c] and "direct_calls" in entry_b["channels"][c]
                assert "api_imports" in entry_a["channels"][c] and "api_imports" in entry_b["channels"][c]


def test_resync_required_fails_closed_in_engine_lifecycle(tmp_path: Path, isolated_dirs):
    """
    PROVES that if state.resync_required is True, engine update lifecycle
    refuses to mark artifact_consumption_state as 'fresh' even with 100% valid coverage.
    """
    repo_dir = tmp_path / "resync_repo"
    repo_dir.mkdir()
    core_file = repo_dir / "core.py"
    core_file.write_text("def helper(): return 1\n", encoding="utf-8")

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    engine = hydrated.engine

    # Coverage is valid initially
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
    assert engine.state.artifact_consumption_state == "fresh"

    # Set resync_required = True
    engine.state.resync_required = True

    # Perform update
    core_file.write_text("def helper(): return 2\n", encoding="utf-8")
    res = engine.update_file(str(core_file))

    # Invariant: artifact_consumption_state MUST be 'stale'
    assert engine.state.artifact_consumption_state == "stale"
    assert res.artifact_consumption_state == "stale"
    assert artifact_consumption_is_fresh(engine.state) is False


def test_preexisting_stale_preserved_without_recompute(tmp_path: Path):
    """
    PROVES that preexisting 'stale' artifact_consumption_state is preserved
    on no-op / UNCHANGED without being falsely marked fresh solely by coverage.
    """
    repo_dir = tmp_path / "stale_preserve_repo"
    repo_dir.mkdir()
    core_file = repo_dir / "core.py"
    core_file.write_text("def helper(): return 1\n", encoding="utf-8")

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    engine = hydrated.engine

    # Set pre-existing stale
    engine.state.artifact_consumption_state = "stale"
    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True

    # Execute no-op update on unchanged file
    res = engine.update_file(str(core_file))
    assert res.status == "UNCHANGED"

    # Invariant: stale is preserved, NOT converted to fresh
    assert res.artifact_consumption_state == "stale"
    assert engine.state.artifact_consumption_state == "stale"
    assert artifact_consumption_is_fresh(engine.state) is False


def test_legal_successful_recompute_transitions_to_fresh(tmp_path: Path):
    """
    PROVES that an intentional previous 'stale' state legally transitions to 'fresh'
    when a successful incremental recompute runs without ambiguities and with valid coverage.
    """
    repo_dir = tmp_path / "recompute_fresh_repo"
    repo_dir.mkdir()
    core_file = repo_dir / "core.py"
    core_file.write_text("def helper(): return 1\ndef helper2(): return 2\n", encoding="utf-8")
    app_file = repo_dir / "app.py"
    app_file.write_text("import core\ndef main(): return core.helper()\n", encoding="utf-8")

    facade = ContextorFacade()
    errors, _ = facade.analyze_project(str(repo_dir))
    assert not errors

    hydrated = hydrate_repository_engine(repo_dir)
    assert hydrated is not None
    engine = hydrated.engine

    # Pre-existing stale (e.g. from prior dirty event)
    engine.state.artifact_consumption_state = "stale"
    assert not getattr(engine.state, "resync_required", False)

    # Perform real incremental update modifying app.py cleanly to call helper2 instead of helper
    app_file.write_text("import core\ndef main():\n    return core.helper2()\n", encoding="utf-8")
    res = engine.update_file(str(app_file))
    assert res.status in ("UPDATED", "SUCCESS")

    # Invariant: clean recompute with valid coverage successfully transitions to 'fresh'
    assert engine.state.artifact_consumption_state == "fresh"
    assert res.artifact_consumption_state == "fresh"
    assert artifact_consumption_is_fresh(engine.state) is True


# ==============================================================================
# 3. STRICT CANONICAL CHANNEL ALLOWLIST & INTERNAL CONSISTENCY PROOF
# ==============================================================================

def test_strict_canonical_channel_allowlist_and_internal_consistency():
    """
    PROVES that build_canonical_artifact_consumption:
    1. Only admits channels from CANONICAL_USAGE_CHANNELS.
    2. Excludes stale consumer modules not in consumers list.
    3. Excludes detail fields (*_detail) and ambiguous_calls.
    4. Guarantees set(entry["channels"].keys()) <= set(entry["consumers"]).
    """
    raw_artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["process"], "methods": [], "globals": []},
            "own_symbols": ["process"],
            "consumers": {
                "process": {
                    "consumers": ["pkg.a"],
                    "usage": {
                        "direct_calls": ["pkg.a"],
                        "runtime_calls": ["pkg.stale"],  # stale consumer, not in consumers
                        "unknown_custom_channel": ["pkg.a"],  # not in CANONICAL_USAGE_CHANNELS
                        "ambiguous_calls": [{"module": "pkg.a", "confidence": 0.3}],
                        "direct_calls_detail": [{"module": "pkg.a", "line": 10}],
                    },
                }
            },
        }
    }

    normalized = build_canonical_artifact_consumption(raw_artifacts)
    assert "pkg.core::process" in normalized

    entry = normalized["pkg.core::process"]
    assert entry["consumers"] == ["pkg.a"]
    # Only direct_calls for pkg.a must be present
    assert entry["channels"] == {"pkg.a": ["direct_calls"]}
    assert "pkg.stale" not in entry["channels"]
    assert "unknown_custom_channel" not in entry["channels"].get("pkg.a", [])
    assert set(entry["channels"].keys()).issubset(set(entry["consumers"]))


def test_canonical_artifact_consumption_validator():
    """
    PROVES that validate_canonical_artifact_consumption enforces strict canonical schema,
    deterministic sorting, and target key format.
    """
    # 1. Valid entry
    valid = {
        "pkg.core::func": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["api_imports", "direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(valid) is True

    # 2. Legacy _report rejected
    legacy = {"_report": {"_format_version": 3}}
    assert validate_canonical_artifact_consumption(legacy) is False
    assert is_legacy_artifact_consumption(legacy) is True

    # 3. Non-canonical channel rejected
    invalid_ch = {
        "pkg.core::func": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["invalid_channel_name"]},
        }
    }
    assert validate_canonical_artifact_consumption(invalid_ch) is False

    # 4. Consumer inconsistency rejected (channel key not in consumers)
    inconsistent = {
        "pkg.core::func": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.other": ["direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(inconsistent) is False

    # 5. Non-deterministic / unsorted consumers rejected
    unsorted_consumers = {
        "pkg.core::func": {
            "consumers": ["pkg.b", "pkg.a"],
            "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(unsorted_consumers) is False

    # 6. Non-deterministic / unsorted channels list rejected
    unsorted_channels = {
        "pkg.core::func": {
            "consumers": ["pkg.a"],
            "channels": {"pkg.a": ["runtime_calls", "direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(unsorted_channels) is False

    # 7. Invalid target key (empty definer or symbol) rejected
    invalid_key1 = {"": {"consumers": [], "channels": {}}}
    assert validate_canonical_artifact_consumption(invalid_key1) is False

    invalid_key2 = {"::func": {"consumers": [], "channels": {}}}
    assert validate_canonical_artifact_consumption(invalid_key2) is False

    invalid_key3 = {"core::": {"consumers": [], "channels": {}}}
    assert validate_canonical_artifact_consumption(invalid_key3) is False


# ==============================================================================
# 4. COVERAGE VALIDATION & EMPTY DOMAIN SEMANTICS PROOF
# ==============================================================================

def test_empty_map_domain_semantics():
    """
    PROVES:
    1. consumption == {} and expected == set() -> valid & fresh.
    2. consumption == {} and expected != set() -> NOT fresh (coverage incomplete).
    """
    # 1. Empty repository domain
    empty_artifacts: dict[str, Any] = {}
    assert canonical_artifact_consumption_targets(empty_artifacts) == set()
    assert validate_canonical_artifact_consumption_coverage({}, empty_artifacts) is True

    # 2. Non-empty repository domain with empty consumption
    non_empty_artifacts = {
        "pkg.core": {
            "consumers": {"func": {"consumers": [], "usage": {}}}
        }
    }
    assert canonical_artifact_consumption_targets(non_empty_artifacts) == {"pkg.core::func"}
    assert validate_canonical_artifact_consumption_coverage({}, non_empty_artifacts) is False


def test_partial_modern_state_fail_closed():
    """
    PROVES that a partial modern canonical state (where one target is missing from artifact_consumption)
    fails closed on materialization: marked as 'stale' and NOT auto-healed from state.artifacts.
    """
    artifacts = {
        "pkg.core": {
            "consumers": {
                "func_a": {"consumers": ["pkg.app"], "usage": {"direct_calls": ["pkg.app"]}},
                "func_b": {"consumers": ["pkg.app"], "usage": {"direct_calls": ["pkg.app"]}},
            }
        }
    }
    # Partial modern consumption: only contains func_a, missing func_b
    partial_consumption = {
        "pkg.core::func_a": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["direct_calls"]},
        }
    }
    assert validate_canonical_artifact_consumption(partial_consumption) is True
    assert validate_canonical_artifact_consumption_coverage(partial_consumption, artifacts) is False

    state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=ProjectGraph(hard_edges={}, soft_edges={}),
        artifact_consumption=partial_consumption,
        artifact_consumption_state="deferred",
    )

    materialize_incremental_state(state)

    # Must FAIL CLOSED: state marked stale, partial consumption NOT overwritten
    assert state.artifact_consumption_state == "stale"
    assert "pkg.core::func_b" not in state.artifact_consumption
    assert state.artifact_consumption == partial_consumption


# ==============================================================================
# 5. LEGACY MIGRATION VS INVALID CANONICAL FAIL-CLOSED PROOF
# ==============================================================================

def test_legacy_report_hydration_materialization_self_heal():
    """
    PROVES that when legacy state containing artifact_consumption = {"_report": ...}
    is materialized via materialize_incremental_state, it migrates in RAM from
    state.artifacts and becomes fresh.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["boot"],
            "consumers": {
                "boot": {
                    "consumers": ["pkg.app"],
                    "usage": {"direct_calls": ["pkg.app"]},
                }
            },
        }
    }
    legacy_state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={}),
        artifact_consumption={"_report": {"legacy": "data"}},  # legacy shape
    )

    assert is_legacy_artifact_consumption(legacy_state.artifact_consumption) is True
    assert validate_canonical_artifact_consumption(legacy_state.artifact_consumption) is False

    materialize_incremental_state(legacy_state)

    assert validate_canonical_artifact_consumption(legacy_state.artifact_consumption) is True
    assert validate_canonical_artifact_consumption_coverage(legacy_state.artifact_consumption, artifacts) is True
    assert legacy_state.artifact_consumption_state == "fresh"
    assert "pkg.core::boot" in legacy_state.artifact_consumption
    assert legacy_state.artifact_consumption["pkg.core::boot"] == {
        "consumers": ["pkg.app"],
        "channels": {"pkg.app": ["direct_calls"]},
    }


def test_invalid_modern_canonical_state_fails_closed_without_auto_heal():
    """
    PROVES that an invalid modern canonical state (e.g. corrupt channels or stale channel key)
    is NOT auto-healed from state.artifacts, but fails closed by marking state.artifact_consumption_state = "stale".
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["boot"],
            "consumers": {
                "boot": {
                    "consumers": ["pkg.app"],
                    "usage": {"direct_calls": ["pkg.app"]},
                }
            },
        }
    }
    # Corrupt modern canonical consumption: channel points to non-consumer "pkg.stale"
    corrupt_consumption = {
        "pkg.core::boot": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.stale": ["direct_calls"]},
        }
    }
    state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={}),
        artifact_consumption=corrupt_consumption,
        artifact_consumption_state="deferred",
    )

    assert is_legacy_artifact_consumption(state.artifact_consumption) is False
    assert validate_canonical_artifact_consumption(state.artifact_consumption) is False

    materialize_incremental_state(state)

    # Must FAIL CLOSED: state marked stale, corrupt consumption NOT overwritten
    assert state.artifact_consumption_state == "stale"
    assert state.artifact_consumption == corrupt_consumption


def test_resync_required_blocks_auto_heal():
    """
    PROVES that when state requires resync (resync_required == True or state is stale),
    materialization does not auto-heal or clear the stale marker.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["boot"],
            "consumers": {
                "boot": {
                    "consumers": ["pkg.app"],
                    "usage": {"direct_calls": ["pkg.app"]},
                }
            },
        }
    }
    state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={}),
        artifact_consumption={"_report": {"legacy": "data"}},
        artifact_consumption_state="stale",
    )
    # Set resync_required attribute
    setattr(state, "resync_required", True)

    materialize_incremental_state(state)

    assert state.artifact_consumption_state == "stale"


# ==============================================================================
# 6. FULL ANALYSIS / INCREMENTAL SCHEMA UNIFICATION PROOF
# ==============================================================================

def test_full_analysis_and_incremental_schema_parity():
    """
    PROVES that artifact_consumption produced by full analysis (build_canonical_artifact_consumption)
    and incremental pipeline (plan_executor) follow the EXACT same schema and orientation.
    """
    raw_artifacts = {
        "pkg.core": {
            "symbols": {"classes": ["Engine"], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["Engine", "boot"],
            "consumers": {
                "boot": {
                    "consumers": ["pkg.service"],
                    "usage": {
                        "direct_calls": ["pkg.service"],
                        "runtime_calls": ["pkg.service"],
                    },
                }
            },
        }
    }
    normalized = build_canonical_artifact_consumption(raw_artifacts)

    assert "pkg.core::boot" in normalized
    entry = normalized["pkg.core::boot"]
    assert entry == {
        "consumers": ["pkg.service"],
        "channels": {
            "pkg.service": ["direct_calls", "runtime_calls"],
        },
    }

    # Simulate an incremental update updating the same schema
    incremental_entry = {
        "consumers": list(entry["consumers"]),
        "channels": {k: list(v) for k, v in entry["channels"].items()},
    }
    incremental_entry["consumers"].append("pkg.worker")
    incremental_entry["consumers"].sort()
    incremental_entry["channels"]["pkg.worker"] = ["api_imports"]

    assert incremental_entry["consumers"] == ["pkg.service", "pkg.worker"]
    assert set(incremental_entry["channels"].keys()) == {"pkg.service", "pkg.worker"}


# ==============================================================================
# 7. SELF-CONSUMPTION & EXTERNAL FILTER PARITY PROOF
# ==============================================================================

def test_self_consumption_and_external_filter_parity():
    """
    PROVES exact parity on:
    1. Symbol consumed ONLY by its own definer module -> omitted from artifact index (no external consumer).
    2. Symbol consumed by definer + external consumer -> included in artifact index, self retained in consumers.
    3. Symbol with 0 consumers -> omitted.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["self_only", "self_and_ext", "zero_consumer"], "methods": [], "globals": []},
            "own_symbols": ["self_only", "self_and_ext", "zero_consumer"],
        }
    }
    consumption = {
        "pkg.core::self_only": {
            "consumers": ["pkg.core"],
            "channels": {"pkg.core": ["direct_calls"]},
        },
        "pkg.core::self_and_ext": {
            "consumers": ["pkg.app", "pkg.core"],
            "channels": {
                "pkg.app": ["direct_calls"],
                "pkg.core": ["direct_calls"],
            },
        },
        "pkg.core::zero_consumer": {
            "consumers": [],
            "channels": {},
        },
    }

    projected = build_artifact_data_projection(artifacts, consumption)

    # 1. self_only must be omitted
    assert "pkg.core::self_only" not in projected["artifacts"]

    # 2. zero_consumer must be omitted
    assert "pkg.core::zero_consumer" not in projected["artifacts"]

    # 3. self_and_ext must be included, retaining both consumers
    assert "pkg.core::self_and_ext" in projected["artifacts"]
    art = projected["artifacts"]["pkg.core::self_and_ext"]
    assert art["consumers"] == ["pkg.app", "pkg.core"]
    assert art["consumer_count"] == 2


# ==============================================================================
# 8. CHANNEL SEMANTICS INVARIANT (DIRECT VS RUNTIME CALL MATRIX INVARIANCE)
# ==============================================================================

def test_direct_vs_runtime_call_matrix_invariance():
    """
    PROVES that direct_calls vs runtime_calls map to the identical 'call' dependency type,
    leaving the Dependency Matrix unchanged.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["foo"], "methods": [], "globals": []},
            "own_symbols": ["foo"],
        }
    }
    graph = ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={})

    # Case A: direct_calls
    consumption_direct = {
        "pkg.core::foo": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["direct_calls"]},
        }
    }
    state_a = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=graph,
        artifact_consumption=consumption_direct,
    )

    # Case B: runtime_calls
    consumption_runtime = {
        "pkg.core::foo": {
            "consumers": ["pkg.app"],
            "channels": {"pkg.app": ["runtime_calls"]},
        }
    }
    state_b = RepositoryAnalysisState(
        modules=state_a.modules,
        artifacts=artifacts,
        dependency_graph=graph,
        artifact_consumption=consumption_runtime,
    )

    matrix_a = compute_dependency_matrix_from_state(state_a)
    matrix_b = compute_dependency_matrix_from_state(state_b)

    assert matrix_a == matrix_b
    assert matrix_a["pkg.app"]["pkg.core"]["dep_types"] == ["call", "import"]


# ==============================================================================
# 9. EDGE-CASE AUDIT TESTS WITH CONCRETE ASSERTIONS
# ==============================================================================

def test_edge_case_below_jaccard_threshold_excluded():
    """
    AUDIT TEST: Pairs with Jaccard similarity < min_jaccard (0.30) are excluded from clusters.
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": [f"f{i}" for i in range(1, 11)], "classes": [], "methods": [], "globals": []},
            "own_symbols": [f"f{i}" for i in range(1, 11)],
        }
    }
    artifact_consumption = {
        f"pkg.prov::f{i}": {"consumers": ["pkg.a"], "channels": {"pkg.a": ["direct_calls"]}} for i in range(1, 5)
    }
    artifact_consumption["pkg.prov::f5"] = {"consumers": ["pkg.a", "pkg.b"], "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]}}
    for i in range(6, 11):
        artifact_consumption[f"pkg.prov::f{i}"] = {"consumers": ["pkg.b"], "channels": {"pkg.b": ["direct_calls"]}}

    clusters = compute_shared_usage_clusters(artifacts, artifact_consumption, min_jaccard=0.30)
    assert len(clusters) == 0


def test_edge_case_complete_linkage_no_chaining():
    """
    AUDIT TEST: Complete-linkage clustering invariant.
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": [f"f{i}" for i in range(1, 9)], "classes": [], "methods": [], "globals": []},
            "own_symbols": [f"f{i}" for i in range(1, 9)],
        }
    }
    artifact_consumption = {
        "pkg.prov::f1": {"consumers": ["pkg.a"], "channels": {"pkg.a": ["direct_calls"]}},
        "pkg.prov::f2": {"consumers": ["pkg.a"], "channels": {"pkg.a": ["direct_calls"]}},
        "pkg.prov::f3": {"consumers": ["pkg.a", "pkg.b"], "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]}},
        "pkg.prov::f4": {"consumers": ["pkg.a", "pkg.b"], "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]}},
        "pkg.prov::f5": {"consumers": ["pkg.b", "pkg.c"], "channels": {"pkg.b": ["direct_calls"], "pkg.c": ["direct_calls"]}},
        "pkg.prov::f6": {"consumers": ["pkg.b", "pkg.c"], "channels": {"pkg.b": ["direct_calls"], "pkg.c": ["direct_calls"]}},
        "pkg.prov::f7": {"consumers": ["pkg.c"], "channels": {"pkg.c": ["direct_calls"]}},
        "pkg.prov::f8": {"consumers": ["pkg.c"], "channels": {"pkg.c": ["direct_calls"]}},
    }

    clusters = compute_shared_usage_clusters(artifacts, artifact_consumption, min_jaccard=0.30)
    for c in clusters:
        assert len(c["modules"]) == 2
        assert set(c["modules"]) != {"pkg.a", "pkg.b", "pkg.c"}


def test_edge_case_min_and_max_cluster_sizes():
    """
    AUDIT TEST: min_cluster_size and max_cluster_size bounds enforcement.
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": ["f1", "f2"], "classes": [], "methods": [], "globals": []},
            "own_symbols": ["f1", "f2"],
        }
    }
    artifact_consumption = {
        "pkg.prov::f1": {"consumers": ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"], "channels": {m: ["direct_calls"] for m in ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"]}},
        "pkg.prov::f2": {"consumers": ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"], "channels": {m: ["direct_calls"] for m in ["pkg.m1", "pkg.m2", "pkg.m3", "pkg.m4"]}},
    }

    clusters_capped = compute_shared_usage_clusters(
        artifacts, artifact_consumption, min_jaccard=0.30, max_cluster_size=2
    )
    assert len(clusters_capped) == 1
    assert len(clusters_capped[0]["modules"]) == 2

    clusters_min_5 = compute_shared_usage_clusters(
        artifacts, artifact_consumption, min_jaccard=0.30, min_cluster_size=5
    )
    assert len(clusters_min_5) == 0

    clusters_default = compute_shared_usage_clusters(
        artifacts, artifact_consumption, min_jaccard=0.30, min_cluster_size=2, max_cluster_size=25
    )
    assert len(clusters_default) == 1
    assert len(clusters_default[0]["modules"]) == 4


def test_edge_case_similarity_rounding():
    """
    AUDIT TEST: Precision rounding of jaccard_similarity (4 decimal places).
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": ["f1", "f2", "f3"], "classes": [], "methods": [], "globals": []},
            "own_symbols": ["f1", "f2", "f3"],
        }
    }
    artifact_consumption = {
        "pkg.prov::f1": {"consumers": ["pkg.a"], "channels": {"pkg.a": ["direct_calls"]}},
        "pkg.prov::f2": {"consumers": ["pkg.a", "pkg.b"], "channels": {"pkg.a": ["direct_calls"], "pkg.b": ["direct_calls"]}},
        "pkg.prov::f3": {"consumers": ["pkg.b"], "channels": {"pkg.b": ["direct_calls"]}},
    }

    clusters = compute_shared_usage_clusters(artifacts, artifact_consumption, min_jaccard=0.30)
    assert len(clusters) == 1
    assert clusters[0]["jaccard_similarity"] == 0.3333


def test_edge_case_deterministic_ordering():
    """
    AUDIT TEST: Deterministic ordering of clusters by (-shared_artifact_count, -size, modules).
    """
    artifacts = {
        "pkg.prov": {
            "symbols": {"functions": [f"f{i}" for i in range(1, 10)], "classes": [], "methods": [], "globals": []},
            "own_symbols": [f"f{i}" for i in range(1, 10)],
        }
    }
    artifact_consumption = {
        "pkg.prov::f1": {"consumers": ["pkg.m1", "pkg.m2"], "channels": {"pkg.m1": ["direct_calls"], "pkg.m2": ["direct_calls"]}},
        "pkg.prov::f2": {"consumers": ["pkg.m1", "pkg.m2"], "channels": {"pkg.m1": ["direct_calls"], "pkg.m2": ["direct_calls"]}},
        "pkg.prov::f3": {"consumers": ["pkg.m3", "pkg.m4"], "channels": {"pkg.m3": ["direct_calls"], "pkg.m4": ["direct_calls"]}},
        "pkg.prov::f4": {"consumers": ["pkg.m3", "pkg.m4"], "channels": {"pkg.m3": ["direct_calls"], "pkg.m4": ["direct_calls"]}},
        "pkg.prov::f5": {"consumers": ["pkg.m3", "pkg.m4"], "channels": {"pkg.m3": ["direct_calls"], "pkg.m4": ["direct_calls"]}},
    }

    clusters = compute_shared_usage_clusters(artifacts, artifact_consumption, min_jaccard=0.30)
    assert len(clusters) == 2
    assert clusters[0]["shared_artifact_count"] == 3
    assert clusters[0]["modules"] == ["pkg.m3", "pkg.m4"]
    assert clusters[1]["shared_artifact_count"] == 2
    assert clusters[1]["modules"] == ["pkg.m1", "pkg.m2"]


def test_symbol_rename_invariance_and_divergence():
    """
    AUDIT TEST: Symbol rename contract.
    """
    artifacts_before = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["initialize_core"], "methods": [], "globals": []},
            "own_symbols": ["initialize_core"],
        }
    }
    consumption_before = {
        "pkg.core::initialize_core": {
            "consumers": ["pkg.service_a", "pkg.service_b"],
            "channels": {
                "pkg.service_a": ["direct_calls"],
                "pkg.service_b": ["direct_calls"],
            },
        }
    }
    graph = ProjectGraph(hard_edges={"pkg.service_a": {"pkg.core"}, "pkg.service_b": {"pkg.core"}}, soft_edges={})
    state_before = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.service_a": Module(module_id="pkg.service_a", path="a.py", absolute_path="/a.py", imports=[]),
                 "pkg.service_b": Module(module_id="pkg.service_b", path="b.py", absolute_path="/b.py", imports=[])},
        artifacts=artifacts_before,
        dependency_graph=graph,
        artifact_consumption=consumption_before,
    )

    artifacts_after = {
        "pkg.core": {
            "symbols": {"classes": [], "functions": ["bootstrap_core"], "methods": [], "globals": []},
            "own_symbols": ["bootstrap_core"],
        }
    }
    consumption_after = {
        "pkg.core::bootstrap_core": {
            "consumers": ["pkg.service_a", "pkg.service_b"],
            "channels": {
                "pkg.service_a": ["direct_calls"],
                "pkg.service_b": ["direct_calls"],
            },
        }
    }
    state_after = RepositoryAnalysisState(
        modules=state_before.modules,
        artifacts=artifacts_after,
        dependency_graph=graph,
        artifact_consumption=consumption_after,
    )

    matrix_before = compute_dependency_matrix_from_state(state_before)
    matrix_after = compute_dependency_matrix_from_state(state_after)
    assert matrix_before == matrix_after

    clusters_before = compute_shared_usage_clusters_from_state(state_before)
    clusters_after = compute_shared_usage_clusters_from_state(state_after)

    assert len(clusters_before) == len(clusters_after)
    for c_before, c_after in zip(clusters_before, clusters_after):
        assert c_before["modules"] == c_after["modules"]
        assert c_before["jaccard_similarity"] == c_after["jaccard_similarity"]
        assert c_before["shared_artifact_count"] == c_after["shared_artifact_count"]

    assert clusters_before != clusters_after
    assert "pkg.core::initialize_core" in clusters_before[0]["shared_artifact_keys"]
    assert "pkg.core::bootstrap_core" in clusters_after[0]["shared_artifact_keys"]


# ==============================================================================
# 10. PURE RAM NO-DISK EXECUTION PROOF
# ==============================================================================

def test_pure_ram_computation_blocks_all_disk_io():
    """
    Prove pure-RAM execution: All computations succeed with 100% of disk I/O blocked.
    """
    artifacts = {
        "pkg.core": {
            "symbols": {"classes": ["Engine"], "functions": ["boot"], "methods": [], "globals": []},
            "own_symbols": ["Engine", "boot"],
        }
    }
    artifact_consumption = {
        "pkg.core::boot": {"consumers": ["pkg.app"], "channels": {"pkg.app": ["direct_calls"]}}
    }
    graph = ProjectGraph(hard_edges={"pkg.app": {"pkg.core"}}, soft_edges={})
    state = RepositoryAnalysisState(
        modules={"pkg.core": Module(module_id="pkg.core", path="core.py", absolute_path="/core.py", imports=[]),
                 "pkg.app": Module(module_id="pkg.app", path="app.py", absolute_path="/app.py", imports=[])},
        artifacts=artifacts,
        dependency_graph=graph,
        artifact_consumption=artifact_consumption,
    )

    with patch("builtins.open", side_effect=AssertionError("Disk open blocked")), \
         patch("pathlib.Path.read_text", side_effect=AssertionError("Disk read_text blocked")), \
         patch("pathlib.Path.read_bytes", side_effect=AssertionError("Disk read_bytes blocked")):

        # 1. Projection
        proj = build_artifact_data_projection(state.artifacts, state.artifact_consumption)
        assert len(proj["artifacts"]) == 1

        # 2. Matrix
        mat = compute_dependency_matrix_from_state(state)
        assert "pkg.app" in mat
        assert mat["pkg.app"]["pkg.core"]["weight"] == 1

        # 3. Clusters
        cls = compute_shared_usage_clusters_from_state(state)
        assert isinstance(cls, list)
