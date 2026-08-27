"""
tests/test_collisions_live_lifecycle.py

Targeted tests for Canonical LIVE Lifecycle of Name Collisions & collision_facts.
Verifies:
1. Exact fact schema & extraction
2. Pure aggregator compute_collisions_from_facts parity with validate_name_collisions
3. Completeness predicate & missing vs valid empty facts
4. Location changes & additive RefreshPlanner merging
5. Early no-op prevention (body/class/constant edits)
6. Snapshot bootstrap freshness invariants
7. IncrementalAnalysisEngine real-time lifecycle & RAM-only recomputation
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from contextor.core.analysis.incremental.engine import IncrementalAnalysisEngine
from contextor.core.analysis.incremental.materialization import (
    collision_facts_complete,
    ensure_collisions,
    materialize_incremental_state,
)
from contextor.core.analysis.incremental.plan_executor import (
    CandidateState,
    execute_refresh_plan,
)
from contextor.core.analysis.incremental.preparation import (
    prepare_deleted_module_update,
    prepare_source_update,
)
from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.state_manager import (
    AnalysisResult,
    FileDelta,
    FileStateManager,
    RepositoryAnalysisState,
)
from contextor.core.domain.module import Module
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.validator.collisions import (
    compute_collisions_from_facts,
    extract_module_collision_facts,
    validate_name_collisions,
)


def test_fact_extraction_exact_schema():
    """Verify exact schema of extracted collision facts."""
    source = "class Service:\n    pass\n\ndef helper():\n    return 42\n\nMAX_RETRIES = 5\n_private = 1\nlocal_var = 2\n"
    tree = ast.parse(source)
    facts = extract_module_collision_facts(tree, "app.core", "/tmp/app/core.py")

    assert len(facts) == 3
    names = {f["name"] for f in facts}
    assert names == {"Service", "helper", "MAX_RETRIES"}

    service_fact = next(f for f in facts if f["name"] == "Service")
    assert service_fact["type"] == "class"
    assert service_fact["file"] == "app.core"
    assert service_fact["file_path"] == "/tmp/app/core.py"
    assert service_fact["code"] == "class Service:\n    pass"
    assert service_fact["line_start"] == 1

    var_fact = next(f for f in facts if f["name"] == "MAX_RETRIES")
    assert var_fact["type"] == "variable"
    assert var_fact["code"] == "MAX_RETRIES = 5"


def test_compute_collisions_from_facts_parity():
    """Verify that pure compute_collisions_from_facts matches validate_name_collisions."""
    src_a = "def process():\n    return 1\n"
    src_b = "def process():\n    return 2\n"
    src_c = "def unique_helper():\n    pass\n"

    tree_a = ast.parse(src_a)
    tree_b = ast.parse(src_b)
    tree_c = ast.parse(src_c)

    facts = {
        "mod_a": extract_module_collision_facts(tree_a, "mod_a", "/tmp/mod_a.py"),
        "mod_b": extract_module_collision_facts(tree_b, "mod_b", "/tmp/mod_b.py"),
        "mod_c": extract_module_collision_facts(tree_c, "mod_c", "/tmp/mod_c.py"),
    }

    errors = compute_collisions_from_facts(facts)
    assert len(errors) == 1
    err = errors[0]
    assert err.kind == "NAME_COLLISION"
    assert err.artifact_type == "function"
    assert err.nodes == ["mod_a", "mod_b"]
    assert err.is_identical is False

    with tempfile.TemporaryDirectory() as tmpdir:
        path_a = Path(tmpdir) / "mod_a.py"
        path_b = Path(tmpdir) / "mod_b.py"
        path_c = Path(tmpdir) / "mod_c.py"
        path_a.write_text(src_a, encoding="utf-8")
        path_b.write_text(src_b, encoding="utf-8")
        path_c.write_text(src_c, encoding="utf-8")

        # Parity check against validate_name_collisions
        modules = {
            "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(path_a), imports=[]),
            "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(path_b), imports=[]),
            "mod_c": Module(module_id="mod_c", path="mod_c.py", absolute_path=str(path_c), imports=[]),
        }
        legacy_errors = validate_name_collisions(modules)
        assert len(legacy_errors) == 1
        assert legacy_errors[0].message == err.message
        assert legacy_errors[0].kind == err.kind


def test_missing_vs_empty_policy():
    """Verify that old_collision_facts is None triggers changed=True, while valid empty facts do not."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "empty.py"
        file_path.write_text("# Only comments\n", encoding="utf-8")

        # 1. Legacy state: None -> new [] => changed = True
        prep_legacy = prepare_source_update(
            file_path=file_path,
            module_path="empty",
            is_new=False,
            old_module=None,
            old_artifacts={},
            old_usage=None,
            persistent_id="id_empty",
            old_collision_facts=None,
        )
        assert prep_legacy.new_collision_facts == []
        assert prep_legacy.collision_facts_changed is True

        # 2. Existing valid empty facts: [] -> new [] => changed = False
        prep_empty = prepare_source_update(
            file_path=file_path,
            module_path="empty",
            is_new=False,
            old_module=None,
            old_artifacts={},
            old_usage=None,
            persistent_id="id_empty",
            old_collision_facts=[],
        )
        assert prep_empty.new_collision_facts == []
        assert prep_empty.collision_facts_changed is False


def test_location_change_triggers_collision_refresh():
    """Verify that location shifts (e.g. comment/import added above symbol) trigger collision facts changed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "service.py"
        file_path.write_text("def process():\n    return 1\n", encoding="utf-8")

        prep1 = prepare_source_update(
            file_path=file_path,
            module_path="service",
            is_new=False,
            old_module=None,
            old_artifacts={},
            old_usage=None,
            persistent_id="id_service",
            old_collision_facts=None,
        )
        old_facts = prep1.new_collision_facts
        assert old_facts[0]["line_start"] == 1

        # Add 3 comment lines above definition (shifts line_start from 1 to 4)
        file_path.write_text("# Line 1\n# Line 2\n# Line 3\ndef process():\n    return 1\n", encoding="utf-8")
        prep2 = prepare_source_update(
            file_path=file_path,
            module_path="service",
            is_new=False,
            old_module=None,
            old_artifacts={},
            old_usage=None,
            persistent_id="id_service",
            old_collision_facts=old_facts,
        )
        assert prep2.new_collision_facts[0]["line_start"] == 4
        assert prep2.collision_facts_changed is True


def test_collision_planning_additive_ordered_merge():
    """Verify that RefreshPlanner merges collision_facts and collisions additively in canonical order."""
    delta = FileDelta(module_path="mod_a", artifacts_changed=["process"])
    # 1. Without collision change
    plan_no_col = RefreshPlanner.plan_refresh(delta, collision_facts_changed=False)
    assert "collision_facts" not in plan_no_col.patch_families
    assert "collisions" not in plan_no_col.patch_families

    # 2. With collision change
    plan_col = RefreshPlanner.plan_refresh(delta, collision_facts_changed=True)
    assert "definitions" in plan_col.patch_families
    assert "collision_facts" in plan_col.patch_families
    assert "collisions" in plan_col.patch_families
    # Assert canonical order: definitions comes before collision_facts, and collision_facts before collisions
    idx_def = plan_col.patch_families.index("definitions")
    idx_cf = plan_col.patch_families.index("collision_facts")
    idx_c = plan_col.patch_families.index("collisions")
    assert idx_def < idx_cf < idx_c


def test_early_noop_prevention_on_body_and_constant_edits():
    """Verify that body/constant edits with empty FileDelta are NOT swallowed when collision facts differ."""
    delta_empty = FileDelta(module_path="mod_a")  # is_empty == True
    usage_empty = None

    # When collision_facts_changed = True, planner MUST return non-empty plan
    plan = RefreshPlanner.plan_refresh(
        delta=delta_empty,
        usage_delta=usage_empty,
        collision_facts_changed=True,
    )
    assert plan.is_empty is False
    assert plan.patch_families == ("collision_facts", "collisions")


def test_completeness_helper_and_materialization():
    """Verify collision_facts_complete and ensure_collisions behave properly in RAM."""
    # 1. Incomplete state
    state = RepositoryAnalysisState(
        modules={
            "a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[]),
            "b": Module(module_id="b", path="b.py", absolute_path="/tmp/b.py", imports=[]),
        },
        collision_facts={"a": []},  # missing "b"
        collisions_state="deferred",
    )
    assert collision_facts_complete(state) is False
    ensure_collisions(state)
    assert state.collisions_state == "deferred"

    # 2. Complete state
    state.collision_facts["b"] = [
        {"name": "X", "type": "variable", "file": "b", "file_path": "/tmp/b.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}
    ]
    assert collision_facts_complete(state) is True
    ensure_collisions(state)
    assert state.collisions_state == "fresh"
    assert state.collisions == []  # 0 collisions because only 1 module defines X

    # 3. Complete state with a collision (when deferred -> recomputes to fresh)
    state.collision_facts["a"] = [
        {"name": "X", "type": "variable", "file": "a", "file_path": "/tmp/a.py", "code": "X = 2", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}
    ]
    state.collisions_state = "deferred"
    ensure_collisions(state)
    assert state.collisions_state == "fresh"
    assert len(state.collisions) == 1
    assert state.collisions[0].kind == "NAME_COLLISION"

    # 4. Stale state preserved
    state.collisions_state = "stale"
    ensure_collisions(state)
    assert state.collisions_state == "stale"


def test_incremental_engine_end_to_end_collision_lifecycle():
    """End-to-end test of IncrementalAnalysisEngine updating files and managing collisions lifecycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        file_a = root / "mod_a.py"
        file_b = root / "mod_b.py"

        file_a.write_text("def run_task():\n    return 'a'\n", encoding="utf-8")
        file_b.write_text("def other_task():\n    return 'b'\n", encoding="utf-8")

        tree_a = ast.parse(file_a.read_text(encoding="utf-8"))
        tree_b = ast.parse(file_b.read_text(encoding="utf-8"))

        state = RepositoryAnalysisState(
            modules={
                "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[]),
                "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(file_b), imports=[]),
            },
            collision_facts={
                "mod_a": extract_module_collision_facts(tree_a, "mod_a", str(file_a)),
                "mod_b": extract_module_collision_facts(tree_b, "mod_b", str(file_b)),
            },
            collisions=[],
            collisions_state="fresh",
        )

        state_mgr = FileStateManager(str(root / ".cache"))
        state_mgr.update_state(str(file_a))
        state_mgr.update_state(str(file_b))

        registry = PersistentIdentityRegistry(str(root))

        engine = IncrementalAnalysisEngine(
            state=state,
            registry=registry,
            state_manager=state_mgr,
            root_path=str(root),
        )

        # 1. Introduce collision in mod_b: change other_task -> run_task
        file_b.write_text("def run_task():\n    return 'b'\n", encoding="utf-8")
        result = engine.update_file(str(file_b))

        assert result.status == "UPDATED"
        assert result.collisions_state == "fresh"
        assert len(engine.state.collisions) == 1
        assert engine.state.collisions[0].kind == "NAME_COLLISION"
        assert engine.state.collisions[0].nodes == ["mod_a", "mod_b"]

        # 2. Modify body only in mod_b (returns 'b_v2') -> collision still detected, fresh state
        file_b.write_text("def run_task():\n    return 'b_v2'\n", encoding="utf-8")
        result_body = engine.update_file(str(file_b))
        assert result_body.status == "UPDATED"
        assert result_body.collisions_state == "fresh"
        assert len(engine.state.collisions) == 1

        # 3. Resolve collision in mod_b: change run_task -> unique_b
        file_b.write_text("def unique_b():\n    return 'b_v2'\n", encoding="utf-8")
        result_res = engine.update_file(str(file_b))
        assert result_res.status == "UPDATED"
        assert result_res.collisions_state == "fresh"
        assert len(engine.state.collisions) == 0


def test_plan_executor_missing_payload_fail_closed():
    """Verify that execute_refresh_plan raises ValueError when new_collision_facts is None on planned patch."""
    state = RepositoryAnalysisState(
        modules={
            "a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[]),
            "b": Module(module_id="b", path="b.py", absolute_path="/tmp/b.py", imports=[]),
        },
        collision_facts={
            "a": [{"name": "X", "type": "variable", "file": "a", "file_path": "/tmp/a.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}],
            "b": [{"name": "X", "type": "variable", "file": "b", "file_path": "/tmp/b.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}],
        },
        collisions_state="fresh",
    )

    plan = RefreshPlanner.plan_refresh(
        delta=FileDelta(module_path="a"),
        collision_facts_changed=True,
    )
    assert "collision_facts" in plan.patch_families
    assert "collisions" in plan.patch_families

    with pytest.raises(ValueError, match="requires non-None new_collision_facts"):
        execute_refresh_plan(
            state=state,
            delta=FileDelta(module_path="a"),
            usage_delta=None,
            plan=plan,
            new_imports=[],
            new_artifacts={},
            new_usage=ModuleUsageFacts(),
            root_path=Path("/tmp"),
            file_path="/tmp/a.py",
            new_collision_facts=None,
        )


def test_malformed_fact_schema_invalidates_completeness():
    """Verify that malformed facts in collision_facts fail completeness validation."""
    # 1. Invalid artifact type (e.g. 'module' or 'constant' instead of 'variable')
    state_invalid_type = RepositoryAnalysisState(
        modules={"a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[])},
        collision_facts={"a": [{"name": "X", "type": "invalid_kind", "file": "a", "file_path": "/tmp/a.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}]},
        collisions_state="fresh",
    )
    assert collision_facts_complete(state_invalid_type) is False

    # 2. Mismatched module key vs fact['file']
    state_mismatched_key = RepositoryAnalysisState(
        modules={"a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[])},
        collision_facts={"a": [{"name": "X", "type": "variable", "file": "wrong_module", "file_path": "/tmp/a.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}]},
        collisions_state="fresh",
    )
    assert collision_facts_complete(state_mismatched_key) is False

    # 3. Missing required key (e.g. line_start missing)
    state_missing_key = RepositoryAnalysisState(
        modules={"a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[])},
        collision_facts={"a": [{"name": "X", "type": "variable", "file": "a", "file_path": "/tmp/a.py", "code": "X = 1"}]},
        collisions_state="fresh",
    )
    assert collision_facts_complete(state_missing_key) is False


def test_zero_freshness_inference_from_field_presence():
    """Verify that IncrementalUpdateResult never infers 'fresh' from hasattr(state, 'collisions')."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        file_a = root / "mod_a.py"
        file_a.write_text("X = 1\n", encoding="utf-8")

        state = RepositoryAnalysisState(
            modules={"mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[])},
            collisions=[],  # field present
            collisions_state="deferred",  # explicit deferred
        )

        state_mgr = FileStateManager(str(root / ".cache"))
        state_mgr.update_state(str(file_a))

        engine = IncrementalAnalysisEngine(
            state=state,
            registry=PersistentIdentityRegistry(str(root)),
            state_manager=state_mgr,
            root_path=str(root),
        )

        # UNCHANGED query
        res = engine.update_file(str(file_a))
        assert res.status == "UNCHANGED"
        assert res.collisions_state == "deferred"


def test_full_pipeline_missing_ast_safe_fallback():
    """Verify execute_global_pipeline executes safely when one module has missing AST."""
    from contextor.core.domain.graph import ProjectGraph
    from contextor.core.reporting_engine.pipeline import execute_global_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        file_a = root / "mod_a.py"
        file_a.write_text("X = 1\n", encoding="utf-8")
        non_existent_file = root / "missing.py"

        modules = {
            "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[]),
            "missing": Module(module_id="missing", path="missing.py", absolute_path=str(non_existent_file), imports=[]),
        }
        graph = ProjectGraph(hard_edges={"mod_a": set(), "missing": set()}, soft_edges={})

        report_result = execute_global_pipeline(
            repo_name="test_repo",
            modules=modules,
            graph=graph,
            metrics={},
            cycles=[],
            debt={},
            runtime={"cache_hit": False},
            root_path=str(root),
            collisions=None,
        )

        assert "_analysis_result" in report_result
        analysis_result = report_result["_analysis_result"]
        # Incomplete extraction -> collision_facts is None, but snapshot report produced 0 collisions safely
        assert analysis_result.collision_facts is None
        assert analysis_result.collisions == []


def test_deferred_recovery_when_final_missing_fact_delivered():
    """Deferred state transitions to fresh when the final missing module fact is incrementally delivered."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        file_a = root / "mod_a.py"
        file_b = root / "mod_b.py"

        file_a.write_text("def collision_target():\n    return 1\n", encoding="utf-8")
        file_b.write_text("def collision_target():\n    return 2\n", encoding="utf-8")

        tree_a = ast.parse(file_a.read_text(encoding="utf-8"))

        # Incomplete initial state: missing mod_b fact, state is deferred
        state = RepositoryAnalysisState(
            modules={
                "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[]),
                "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(file_b), imports=[]),
            },
            collision_facts={
                "mod_a": extract_module_collision_facts(tree_a, "mod_a", str(file_a)),
            },
            collisions=[],
            collisions_state="deferred",
        )

        state_mgr = FileStateManager(str(root / ".cache"))
        state_mgr.update_state(str(file_a))
        # mod_b not yet registered in state_mgr so update_file sees it as changed

        engine = IncrementalAnalysisEngine(
            state=state,
            registry=PersistentIdentityRegistry(str(root)),
            state_manager=state_mgr,
            root_path=str(root),
        )

        # Update mod_b -> delivers missing collision fact -> coverage complete -> collisions computed -> fresh!
        res = engine.update_file(str(file_b))
        assert res.status == "UPDATED"
        assert res.collisions_state == "fresh"
        assert len(engine.state.collisions) == 1
        assert engine.state.collisions[0].kind == "NAME_COLLISION"
        assert engine.state.collisions[0].nodes == ["mod_a", "mod_b"]


def test_missing_payload_transaction_failure():
    """Planned collision_facts patch with new_collision_facts=None fails transaction without mutating state."""
    state = RepositoryAnalysisState(
        modules={
            "a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[]),
        },
        collision_facts={
            "a": [{"name": "X", "type": "variable", "file": "a", "file_path": "/tmp/a.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}],
        },
        collisions=[],
        collisions_state="fresh",
    )

    plan = RefreshPlanner.plan_refresh(
        delta=FileDelta(module_path="a"),
        collision_facts_changed=True,
    )
    assert "collision_facts" in plan.patch_families

    try:
        execute_refresh_plan(
            state=state,
            delta=FileDelta(module_path="a"),
            usage_delta=None,
            plan=plan,
            new_imports=[],
            new_artifacts={},
            new_usage=ModuleUsageFacts(),
            root_path=Path("/tmp"),
            file_path="/tmp/a.py",
            new_collision_facts=None,
        )
        assert False, "Expected ValueError on missing collision_facts payload"
    except ValueError as exc:
        assert "requires non-None new_collision_facts" in str(exc)

    # Canonical state untouched
    assert state.collisions_state == "fresh"
    assert len(state.collision_facts["a"]) == 1


def test_historical_patch_families_ordering_preserved():
    """Pre-existing planner inputs without collision changes return exact historical tuples."""
    from contextor.core.domain.usage_facts import UsageDelta

    # 1. Alias change with imports
    delta_alias = FileDelta(module_path="mod_a", imports_added=["other"])
    usage_alias = UsageDelta(module_path="mod_a", added_aliases={"foo": "bar"})
    plan_alias = RefreshPlanner.plan_refresh(delta_alias, usage_delta=usage_alias, collision_facts_changed=False)
    assert plan_alias.patch_families == (
        "definitions",
        "module_usages",
        "artifact_consumption",
        "modules",
        "dependency_graph",
        "cached_analytics",
    )

    # 2. Symbol add/remove
    delta_sym = FileDelta(module_path="mod_a", artifacts_added=["MyClass"])
    plan_sym = RefreshPlanner.plan_refresh(delta_sym, collision_facts_changed=False)
    assert plan_sym.patch_families == (
        "definitions",
        "identity_registry",
        "module_usages",
        "artifact_consumption",
        "cached_analytics",
    )

    # 3. Body-only usage change
    usage_body = UsageDelta(module_path="mod_a", added_direct_calls={"target"})
    plan_body = RefreshPlanner.plan_refresh(delta=None, usage_delta=usage_body, collision_facts_changed=False)
    assert plan_body.patch_families == (
        "module_usages",
        "artifact_consumption",
        "cached_analytics",
    )


def test_missing_ast_snapshot_report_parity():
    """Snapshot report retains valid collisions from parseable modules when 1 module has missing AST."""
    from contextor.core.domain.graph import ProjectGraph
    from contextor.core.reporting_engine.pipeline import execute_global_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        file_a = root / "mod_a.py"
        file_b = root / "mod_b.py"
        file_missing = root / "missing.py"

        file_a.write_text("def common_func():\n    return 'a'\n", encoding="utf-8")
        file_b.write_text("def common_func():\n    return 'b'\n", encoding="utf-8")

        modules = {
            "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[]),
            "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(file_b), imports=[]),
            "missing": Module(module_id="missing", path="missing.py", absolute_path=str(file_missing), imports=[]),
        }
        graph = ProjectGraph(hard_edges={"mod_a": set(), "mod_b": set(), "missing": set()}, soft_edges={})

        report_result = execute_global_pipeline(
            repo_name="test_repo",
            modules=modules,
            graph=graph,
            metrics={},
            cycles=[],
            debt={},
            runtime={"cache_hit": False},
            root_path=str(root),
            collisions=None,
        )

        assert "_analysis_result" in report_result
        analysis_result = report_result["_analysis_result"]
        # But snapshot-visible collisions match legacy behavior: found collision between mod_a and mod_b!
        assert len(analysis_result.collisions) == 1
        assert analysis_result.collisions[0].kind == "NAME_COLLISION"
        assert analysis_result.collisions[0].nodes == ["mod_a", "mod_b"]


def test_fact_field_type_validation():
    """Verify that malformed field types in facts fail collision_facts_complete."""
    # Non-int line_start
    state_bad_line = RepositoryAnalysisState(
        modules={"a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[])},
        collision_facts={"a": [{"name": "X", "type": "variable", "file": "a", "file_path": "/tmp/a.py", "code": "X = 1", "line_start": "not_an_int", "line_end": 1, "col_start": 0, "col_end": 5}]},
        collisions_state="fresh",
    )
    assert collision_facts_complete(state_bad_line) is False

    # Boolean line_start (isinstance(True, int) is True, but not isinstance(True, bool))
    state_bool_line = RepositoryAnalysisState(
        modules={"a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[])},
        collision_facts={"a": [{"name": "X", "type": "variable", "file": "a", "file_path": "/tmp/a.py", "code": "X = 1", "line_start": True, "line_end": 1, "col_start": 0, "col_end": 5}]},
        collisions_state="fresh",
    )
    assert collision_facts_complete(state_bool_line) is False

    # Non-string file_path
    state_bad_file_path = RepositoryAnalysisState(
        modules={"a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[])},
        collision_facts={"a": [{"name": "X", "type": "variable", "file": "a", "file_path": 12345, "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}]},
        collisions_state="fresh",
    )
    assert collision_facts_complete(state_bad_file_path) is False


def test_canonical_collisions_provenance_independent_of_supplied_report_collisions():
    """Verify that canonical state collisions strictly derive from collision_facts through full ContextorFacade production path."""
    from unittest.mock import patch
    from contextor.core.api.facade import ContextorFacade
    from contextor.core.validator.collisions import ValidationError, compute_collisions_from_facts
    import contextor.core.api.facade as facade_module

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        file_a = root / "mod_a.py"
        file_b = root / "mod_b.py"

        # Source code has NO collisions: unique function names
        file_a.write_text("def unique_func_a():\n    return 'a'\n", encoding="utf-8")
        file_b.write_text("def unique_func_b():\n    return 'b'\n", encoding="utf-8")

        mock_reporting_collision = ValidationError(
            kind="NAME_COLLISION",
            message="Mock reporting collision",
            nodes=["mod_a", "mod_b"],
            code_snippets={},
            artifact_type="function",
            is_identical=False,
        )

        real_compute = facade_module._compute_metrics_and_debt

        def fake_compute_metrics_and_debt(modules, graph, progress_callback=None, *args, **kwargs):
            metrics, cycles, _, debt = real_compute(modules, graph, progress_callback, *args, **kwargs)
            # Inject fake reporting collisions into the pipeline
            return metrics, cycles, [mock_reporting_collision], debt

        with patch.object(facade_module, "_compute_metrics_and_debt", side_effect=fake_compute_metrics_and_debt):
            errors, analysis_result = ContextorFacade.analyze_project(str(root))

        # 1. Snapshot report visible output respects supplied reporting collisions
        summary = getattr(analysis_result, "summary_data", {})
        assert summary.get("collision_count") == 1
        assert getattr(analysis_result, "collisions", []) == [mock_reporting_collision]

        # 2. Production canonical state created and persisted by ContextorFacade
        from contextor.core.live_state import hydrate_repository_engine
        hydrated = hydrate_repository_engine(root)
        assert hydrated is not None
        state = hydrated.engine.state

        # Requirements:
        # A. collisions_state == "fresh"
        assert state.collisions_state == "fresh"
        # B. state.collisions == compute_collisions_from_facts(state.collision_facts)
        assert state.collisions == compute_collisions_from_facts(state.collision_facts)
        assert state.collisions == []  # Real facts have 0 collisions
        # C. state.collisions != supplied_reporting_collisions
        assert state.collisions != [mock_reporting_collision]


def test_collision_only_update_reason_narrative():
    """Verify that collision-only update with empty UsageDelta gets 'Collision facts update' reason."""
    from contextor.core.domain.usage_facts import UsageDelta

    delta = FileDelta(module_path="mod_a")
    empty_usage = UsageDelta(module_path="mod_a")

    plan = RefreshPlanner.plan_refresh(
        delta=delta,
        usage_delta=empty_usage,
        collision_facts_changed=True,
    )
    assert "Collision facts update" in plan.reason
    assert "Body-only usage change" not in plan.reason



