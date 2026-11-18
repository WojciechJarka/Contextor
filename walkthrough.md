# SP-T4-I2B5-I2 — Type Only Graph Refresh Scope

## PREFLIGHT

- DIRECT_EVIDENCE — HEAD before edits: 576b0060e632fae7d4f790dd93943aec9897e35b; branch main...origin/main; git status clean.
- DIRECT_EVIDENCE — pre-change LIVE revision 1436, provenance live, canonical_state=fresh, resync_required=false.
- DIRECT_EVIDENCE — target files type_only_policy.py and tests/test_p1d3_d2b2_type_only.py had workspace_sync=verified at revision 1436 and fresh checked_and_none syntax diagnostics.
- DIRECT_EVIDENCE — exact production anchors matched: the Module import at line 7; the existing reclassify_incremental_type_only ends at line 458, the file EOF. The test file imports dataclasses.replace and pytest; T51 ends at line 4049 of 4050, followed by EOF.
- DIRECT_EVIDENCE — _I1_SAFE contains pkg.a, pkg.b, and pkg.c for the supplied synthetic tests. No T52-T56 names or helper names existed before the append.
- CONTRACT_PROVED — RefreshPlan is frozen; its allowed patch families include modules, dependency_graph, cached_analytics, artifact_consumption, collision_facts, and collisions. Its allowed graph_recomputations include macro_metrics, reverse_blast_radius, advanced_graph_metrics, and cycles. Every family/recomputation string in the requested helper is in those current contract sets.
- CODE_PATH_PROVED — the current RefreshPlanner import-change paths include modules and dependency_graph and schedule graph recomputations; PlanExecutor pre-populates candidate.modules when the modules family is present, then applies dependency_graph, and refreshes graph-derived metrics/cycles. The new helper remains a pure planner and is not connected to update_file in this stage.
- DIRECT_EVIDENCE — Contextor file context reports one existing test consumer for type_only_policy.py. Lineage preview for reclassify_incremental_type_only showed large sections; fetching calls/connections was guarded by the MCP output-size confirmation. No production caller is changed in this task.
- DIRECT_EVIDENCE — repository virtual environment is CPython 3.15.2.

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE — added the RefreshPlan import immediately after the existing Module import.
- CODE_PATH_PROVED — appended the exact requested plan_type_only_graph_refresh implementation after reclassify_incremental_type_only. The existing reclassification function is unchanged.
- DIRECT_EVIDENCE — appended the two requested test helpers and T52-T56 verbatim at EOF. Existing tests are unchanged.
- DIRECT_EVIDENCE — no changes to engine.py, plan_executor.py, RefreshPlanner, graph construction, or runtime wiring. Production logic contains no repository module IDs; pkg.a/pkg.b/pkg.c occur only in the existing synthetic fixture/tests.

## LOCAL_GRAPH_SCOPE

- CODE_PATH_PROVED — unchanged module membership and equal imports returns the original plan object with full=False.
- CODE_PATH_PROVED — when imports change only for changed_module_id, the helper adds modules, dependency_graph, cached_analytics and the full graph-derived recomputation tuple while returning full=False.
- DIRECT_EVIDENCE — T52 and T53 assert the no-op and local-import cases, including that the input RefreshPlan remains empty.

## GLOBAL_GRAPH_SCOPE

- CODE_PATH_PROVED — any module membership change forces full=True. Import-list changes in a module other than changed_module_id also force full=True.
- DIRECT_EVIDENCE — T54 covers an import change in another module; T55 covers module addition and deletion.
- INFERENCE / SCOPE LIMIT — this helper compares module membership and imports only. It is scoped to type-only import planning and is not a substitute for RefreshPlanner's handling of unrelated Module field changes.
- DIRECT_EVIDENCE — force_full_graph is only returned as a planning decision here. Because integration is explicitly out of scope, this task does not prove that a runtime graph rebuild consumes the boolean.

## REFRESH_PLAN_CONTRACT

- CONTRACT_PROVED — added patch family and graph recomputation values match RefreshPlan's current VALID_PATCH_FAMILIES and VALID_GRAPH_RECOMPUTATIONS.
- CODE_PATH_PROVED — the helper uses a separate list and dataclasses.replace to create a new RefreshPlan; it does not mutate the input plan. Existing refresh_completeness, semantic_certainty, and reason values are retained by replace.
- CODE_PATH_PROVED — the helper enforces dependency_graph before cached_analytics. PlanExecutor's family loop uses that order for graph inputs before analytics.
- DIRECT_EVIDENCE — T56 checks preserved plan metadata and verifies that the original plan's patch_families and graph_recomputations remain unchanged.

## NEGATIVE_AND_COW_REGRESSIONS

- DIRECT_EVIDENCE — the requested exact-type validation rejects invalid outer inputs and module mappings before membership/import comparison. The exact test addition does not add cases for malformed outer inputs.
- INFERENCE / REVIEW NOTE — the helper checks that mapping keys are strings and values are Module instances, but does not check that each key equals Module.module_id or validate each item inside Module.imports. Whether malformed mappings/import records can reach a future caller is UNKNOWN; no production caller is connected in this stage. The tests use canonical indexer-produced module mappings.
- DIRECT_EVIDENCE — T35-T51 regression tests and T52-T56 new tests passed. T53/T56 verify input RefreshPlan copy-on-write behavior; T52 verifies the no-op returns the same object.

## TARGETED_TESTS

- DIRECT_EVIDENCE — ran CPython 3.15.2 from the repository .venv, using explicit test nodes for T35-T56 in tests/test_p1d3_d2b2_type_only.py.
- DIRECT_EVIDENCE — result: 28 passed in 9.40s. Parametrized existing/new nodes expanded to 28 cases.
- DIRECT_EVIDENCE — no full pytest suite was run.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE — canonical LIVE revision 1438, provenance live, canonical_state=fresh, resync_required=false.
- DIRECT_EVIDENCE — continuous desktop_watcher events: revision 1437 UPDATED type_only_policy.py; revision 1438 UPDATED tests/test_p1d3_d2b2_type_only.py.
- DIRECT_EVIDENCE — workspace_sync=verified for both changed files at revision 1438.
- DIRECT_EVIDENCE — both files have fresh checked_and_none syntax diagnostics with errors=[]. Global syntax error count is 0 and fresh.
- DIRECT_EVIDENCE — graph and cycles are fresh.
- UNKNOWN — workspace sync proves disk/LIVE source freshness, not that a running process adopted the new code. Runtime adoption was not checked. No restart or MCP update_file was performed.

## FINAL_VERDICT

I2B5_I2_PASS

The specified pure graph-refresh planner and tests are present, the focused regressions pass, and post-change LIVE checks are fresh. This verdict covers planning scope only; it does not claim Incremental update_file integration or runtime graph rebuild behavior.

## FILES_CHANGED

- contextor/core/analysis/incremental/type_only_policy.py
- tests/test_p1d3_d2b2_type_only.py

walkthrough.md is overwritten as the required report artifact and is not counted as an implementation/test file.

## FULL_DIFFS

Complete changed-line diff from git diff --unified=0:

### contextor/core/analysis/incremental/type_only_policy.py

~~~~diff
diff --git a/contextor/core/analysis/incremental/type_only_policy.py b/contextor/core/analysis/incremental/type_only_policy.py
index 78521d7..2260b3f 100644
--- a/contextor/core/analysis/incremental/type_only_policy.py
+++ b/contextor/core/analysis/incremental/type_only_policy.py
@@ -7,0 +8 @@ from contextor.core.domain.module import Module
+from contextor.core.domain.refresh_plan import RefreshPlan
@@ -458,0 +460,108 @@ def reclassify_incremental_type_only(
+
+
+def plan_type_only_graph_refresh(
+    plan: RefreshPlan,
+    *,
+    changed_module_id: str,
+    previous_modules: dict[str, Module],
+    classified_modules: dict[str, Module],
+) -> tuple[RefreshPlan, bool]:
+    """Expand existing refresh families for changed import semantics."""
+    if (
+        type(plan) is not RefreshPlan
+        or type(changed_module_id) is not str
+        or not changed_module_id
+        or type(previous_modules) is not dict
+        or type(classified_modules) is not dict
+    ):
+        raise TypeError("Invalid type-only graph planning inputs")
+
+    for modules in (previous_modules, classified_modules):
+        if any(
+            type(module_id) is not str
+            or type(module) is not Module
+            or type(module.imports) is not list
+            for module_id, module in modules.items()
+        ):
+            raise TypeError("Invalid type-only module mapping")
+
+    before_ids = set(previous_modules)
+    after_ids = set(classified_modules)
+
+    membership_changed = before_ids != after_ids
+
+    import_changes = {
+        module_id
+        for module_id in before_ids & after_ids
+        if (
+            previous_modules[module_id].imports
+            != classified_modules[module_id].imports
+        )
+    }
+
+    if not membership_changed and not import_changes:
+        return plan, False
+
+    force_full_graph = (
+        membership_changed
+        or any(
+            module_id != changed_module_id
+            for module_id in import_changes
+        )
+    )
+
+    families = list(plan.patch_families)
+
+    if "modules" not in families:
+        families.insert(0, "modules")
+
+    if "dependency_graph" not in families:
+        insertion = next(
+            (
+                families.index(name)
+                for name in (
+                    "artifact_consumption",
+                    "cached_analytics",
+                    "collision_facts",
+                    "collisions",
+                )
+                if name in families
+            ),
+            len(families),
+        )
+        families.insert(insertion, "dependency_graph")
+
+    if "cached_analytics" not in families:
+        insertion = next(
+            (
+                families.index(name)
+                for name in ("collision_facts", "collisions")
+                if name in families
+            ),
+            len(families),
+        )
+        families.insert(insertion, "cached_analytics")
+
+    if (
+        families.index("dependency_graph")
+        > families.index("cached_analytics")
+    ):
+        raise ValueError(
+            "Dependency graph must precede cached analytics"
+        )
+
+    graph_recomputations = (
+        "macro_metrics",
+        "reverse_blast_radius",
+        "advanced_graph_metrics",
+        "cycles",
+    )
+
+    return (
+        replace(
+            plan,
+            patch_families=tuple(families),
+            graph_recomputations=graph_recomputations,
+        ),
+        force_full_graph,
+    )
diff --git a/tests/test_p1d3_d2b2_type_only.py b/tests/test_p1d3_d2b2_type_only.py
index 61fea0e..0057522 100644
--- a/tests/test_p1d3_d2b2_type_only.py
+++ b/tests/test_p1d3_d2b2_type_only.py
@@ -4050,0 +4051,187 @@ def test_sp_t4_i2b5_i1_t51_candidate_is_not_published(
+
+def _i2b5_i2_fixture(tmp_path):
+    root = write_synthetic_repository(
+        tmp_path / "repo", _I1_SAFE
+    )
+    index, _ = _index_graph(root)
+    return dict(index.modules)
+
+
+def _i2b5_i2_change_guard(modules):
+    changed = dict(modules)
+    current = changed["pkg.a"]
+    changed["pkg.a"] = replace(
+        current,
+        imports=[
+            replace(ref, type_only=False)
+            if ref.module == "pkg.b" else ref
+            for ref in current.imports
+        ],
+    )
+    return changed
+
+
+def test_sp_t4_i2b5_i2_t52_no_graph_delta(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.domain.refresh_plan import RefreshPlan
+    from contextor.core.analysis.incremental.type_only_policy import (
+        plan_type_only_graph_refresh,
+    )
+
+    modules = _i2b5_i2_fixture(tmp_path)
+    plan = RefreshPlan()
+
+    result, full = plan_type_only_graph_refresh(
+        plan,
+        changed_module_id="pkg.c",
+        previous_modules=modules,
+        classified_modules=dict(modules),
+    )
+
+    assert result is plan
+    assert full is False
+    assert result.is_empty
+
+
+def test_sp_t4_i2b5_i2_t53_local_import_delta(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.domain.refresh_plan import RefreshPlan
+    from contextor.core.analysis.incremental.type_only_policy import (
+        plan_type_only_graph_refresh,
+    )
+
+    before = _i2b5_i2_fixture(tmp_path)
+    after = _i2b5_i2_change_guard(before)
+    plan = RefreshPlan()
+
+    result, full = plan_type_only_graph_refresh(
+        plan,
+        changed_module_id="pkg.a",
+        previous_modules=before,
+        classified_modules=after,
+    )
+
+    assert full is False
+    assert "modules" in result.patch_families
+    assert "dependency_graph" in result.patch_families
+    assert "cached_analytics" in result.patch_families
+    assert result.patch_families.index(
+        "dependency_graph"
+    ) < result.patch_families.index("cached_analytics")
+    assert result.graph_recomputations == (
+        "macro_metrics",
+        "reverse_blast_radius",
+        "advanced_graph_metrics",
+        "cycles",
+    )
+    assert plan.is_empty
+
+
+def test_sp_t4_i2b5_i2_t54_unrelated_import_delta(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.domain.refresh_plan import RefreshPlan
+    from contextor.core.analysis.incremental.type_only_policy import (
+        plan_type_only_graph_refresh,
+    )
+
+    before = _i2b5_i2_fixture(tmp_path)
+    after = _i2b5_i2_change_guard(before)
+
+    result, full = plan_type_only_graph_refresh(
+        RefreshPlan(),
+        changed_module_id="pkg.c",
+        previous_modules=before,
+        classified_modules=after,
+    )
+
+    assert full is True
+    assert "dependency_graph" in result.patch_families
+    assert "cycles" in result.graph_recomputations
+
+
+@pytest.mark.parametrize("deleted", [False, True])
+def test_sp_t4_i2b5_i2_t55_module_membership(
+    tmp_path, isolated_dirs, deleted,
+):
+    from contextor.core.domain.refresh_plan import RefreshPlan
+    from contextor.core.analysis.incremental.type_only_policy import (
+        plan_type_only_graph_refresh,
+    )
+
+    before = _i2b5_i2_fixture(tmp_path)
+    after = dict(before)
+
+    if deleted:
+        after.pop("pkg.c")
+    else:
+        after["other"] = replace(
+            after["pkg.c"],
+            module_id="other",
+        )
+
+    result, full = plan_type_only_graph_refresh(
+        RefreshPlan(),
+        changed_module_id=(
+            "pkg.c" if deleted else "other"
+        ),
+        previous_modules=before,
+        classified_modules=after,
+    )
+
+    assert full is True
+    assert "dependency_graph" in result.patch_families
+
+
+def test_sp_t4_i2b5_i2_t56_preserve_plan_contract(
+    tmp_path, isolated_dirs,
+):
+    from contextor.core.domain.refresh_plan import RefreshPlan
+    from contextor.core.analysis.incremental.type_only_policy import (
+        plan_type_only_graph_refresh,
+    )
+
+    before = _i2b5_i2_fixture(tmp_path)
+    after = _i2b5_i2_change_guard(before)
+
+    plan = RefreshPlan(
+        patch_families=(
+            "definitions",
+            "artifact_consumption",
+            "cached_analytics",
+        ),
+        graph_recomputations=("cycles",),
+        refresh_completeness="conservative",
+        semantic_certainty="runtime_unresolved",
+        reason="synthetic",
+    )
+
+    result, full = plan_type_only_graph_refresh(
+        plan,
+        changed_module_id="pkg.c",
+        previous_modules=before,
+        classified_modules=after,
+    )
+
+    assert full is True
+    assert result.refresh_completeness == "conservative"
+    assert result.semantic_certainty == "runtime_unresolved"
+    assert result.reason == "synthetic"
+    assert result.patch_families.index(
+        "dependency_graph"
+    ) < result.patch_families.index("cached_analytics")
+    assert result.graph_recomputations == (
+        "macro_metrics",
+        "reverse_blast_radius",
+        "advanced_graph_metrics",
+        "cycles",
+    )
+    assert plan.patch_families == (
+        "definitions",
+        "artifact_consumption",
+        "cached_analytics",
+    )
+    assert plan.graph_recomputations == ("cycles",)
+

~~~~
