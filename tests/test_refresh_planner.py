"""
tests/test_refresh_planner.py

Stage 3C.1a — Pure Unit Tests for RefreshPlanner with Clean Execution Contract.
"""

import pytest

from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.state_manager import FileDelta
from contextor.core.domain.refresh_plan import RefreshPlan
from contextor.core.domain.usage_facts import ModuleUsageFacts, UsageDelta


def test_1_body_only_direct_call_change():
    delta = FileDelta(module_path="app.service")
    usage_delta = UsageDelta(
        module_path="app.service",
        removed_direct_calls=("foo",),
        added_direct_calls=("bar",),
    )
    plan = RefreshPlanner.plan_refresh(delta, usage_delta=usage_delta)

    assert plan.reparse_modules == ()
    assert plan.recompute_modules == ()
    assert "module_usages" in plan.patch_families
    assert "artifact_consumption" in plan.patch_families
    assert plan.graph_recomputations == ()
    assert plan.refresh_completeness == "complete"
    assert plan.semantic_certainty == "statically_resolved"


def test_2_import_add():
    delta = FileDelta(module_path="app.service", imports_added=["target"])
    plan = RefreshPlanner.plan_refresh(delta)

    assert plan.reparse_modules == ()
    assert plan.recompute_modules == ()
    assert "dependency_graph" in plan.patch_families
    assert "macro_metrics" in plan.graph_recomputations
    assert plan.refresh_completeness == "complete"


def test_3_import_remove():
    delta = FileDelta(module_path="app.service", imports_removed=["target"])
    plan = RefreshPlanner.plan_refresh(delta)

    assert plan.reparse_modules == ()
    assert "dependency_graph" in plan.patch_families
    assert "macro_metrics" in plan.graph_recomputations


def test_4_symbol_add():
    delta = FileDelta(module_path="target", artifacts_added=["new_func"])
    plan = RefreshPlanner.plan_refresh(delta)

    assert plan.reparse_modules == ()
    assert plan.recompute_modules == ()
    assert "definitions" in plan.patch_families
    assert "identity_registry" in plan.patch_families


def test_5_symbol_remove():
    delta = FileDelta(module_path="target", artifacts_removed=["old_func"])
    state_usages = {
        "consumer": ModuleUsageFacts(direct_calls=("target.old_func",))
    }

    plan = RefreshPlanner.plan_refresh(delta, module_usages=state_usages)

    assert plan.reparse_modules == ()
    assert plan.recompute_modules == ("consumer",)
    assert "definitions" in plan.patch_families



def test_6_alias_retarget():
    delta = FileDelta(module_path="app.service")
    usage_delta = UsageDelta(
        module_path="app.service",
        removed_aliases=(("foo", "target.foo"),),
        added_aliases=(("foo", "target.bar"),),
    )
    plan = RefreshPlanner.plan_refresh(delta, usage_delta=usage_delta)

    assert plan.reparse_modules == ()
    assert "module_usages" in plan.patch_families


def test_7_reexport_retarget():
    delta = FileDelta(module_path="pkg.__init__", imports_changed=["impl_b"])
    plan = RefreshPlanner.plan_refresh(delta)

    assert plan.reparse_modules == ()
    assert "dependency_graph" in plan.patch_families


def test_8_module_add():
    delta = FileDelta(module_path="new_mod", is_new=True)
    plan = RefreshPlanner.plan_refresh(delta)

    assert plan.reparse_modules == ()
    assert "modules" in plan.patch_families
    assert "definitions" in plan.patch_families
    assert "macro_metrics" in plan.graph_recomputations


def test_9_module_delete():
    delta = FileDelta(module_path="target", is_deleted=True)
    state_usages = {
        "consumer": ModuleUsageFacts(direct_calls=("target.foo",))
    }

    plan = RefreshPlanner.plan_refresh(delta, module_usages=state_usages)

    assert plan.reparse_modules == ()
    assert plan.recompute_modules == ("consumer",)
    assert "modules" in plan.patch_families



def test_10_noop_delta():
    delta = FileDelta(module_path="app")
    plan = RefreshPlanner.plan_refresh(delta)

    assert plan.is_empty or plan.reparse_modules == ()


def test_11_invalid_type_bounds():
    with pytest.raises(ValueError):
        RefreshPlan(refresh_completeness="invalid_value")

    with pytest.raises(ValueError):
        RefreshPlan(patch_families=("invalid_family",))
