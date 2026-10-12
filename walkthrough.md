# CONTEXTOR_B0G2A_PACKAGE_INIT_INCREMENTAL_GRAPH_PARITY

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\core\analysis\refresh_planner.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\tests\test_package_initializer_graph_refresh.py

C:\Temp\Contextor_Repo\walkthrough.md is the task report and is excluded from source/test change accounting. No other source or test file changed.

## SOURCE_AND_GITHUB_PRECHECK

CURRENT_HEAD before editing: c587f1d01125c2bcb9c8caf0138f2e20a666106d. Worktree was clean and local diffs for all three authorized files were empty. Contextor MCP first returned complete RefreshPlanner.plan_refresh at LIVE revision 345 with workspace_sync=verified. It returned complete source in contiguous line ranges for execute_refresh_plan (plan_executor.py:768-1294) and engine.update_file (engine.py:453-736); the ranges were complete and not previews. Current executor graph branch called build_graph with candidate.reexport_facts_by_module, but only for add/delete. Source anchors matched the supplied B0G2A contract. No mismatch was found. The auditor's exact GitHub commit identity was not supplied, so independent remote commit identity is UNKNOWN; this did not affect matching the explicit local anchors.

Contextor blast-radius projections at pre-edit revision 345 reported 10 direct and 181 downstream consumers for refresh_planner and plan_executor modules. These are indexed dependency projections, not a runtime execution result.

## PRE_EDIT_LIVE_REVISION

345; get_live_events(after_revision=345) reported continuous continuity and resync_required=false.

## PLANNER_BRANCH_COVERAGE

RefreshPlanner.plan_refresh defines package_initializer_graph_change only when module_path ends in .__init__ and canonical delta metadata says reexport_facts_changed. The exact requested behavior is present in branches 4, 6 and 7. Branch 5 was left unchanged. No-op, module addition and deletion branches retain their prior behavior.

Tests use real FileDelta, UsageDelta and RefreshPlanner:

- A binding-only metadata change reaches branch 7 and includes reexport_facts, dependency_graph, artifact_consumption, cached_analytics, and exactly the four requested graph recomputations.
- B a symbol change reaches branch 6 and preserves definitions/identity_registry work while adding dependency_graph and the four recomputations.
- C an alias/reexport change without import changes reaches branch 4, preserving prior patch families while adding graph work.
- D ordinary module reexport metadata retains previous behavior and does not force dependency_graph.
- E initializer import change reaches branch 5 with one dependency_graph and one of each recomputation.

## INITIALIZER_BINDING_CHANGE_CONTRACT

The full graph is now scheduled on canonical reexport-fact changes to an existing package initializer even if its imports and artifact payload are otherwise unchanged. The planner adds the dependency_graph family before artifact_consumption and preserves the existing reexport/consumption/analytics families and recomputation set.

## EXECUTOR_FULL_GRAPH_REBUILD

For dependency_graph, execute_refresh_plan rebuilds when a module is new, deleted, or the changed module is a package initializer with reexport_facts_changed metadata. The rebuild uses candidate.modules, a trie/package root for that candidate, and candidate.reexport_facts_by_module. The ordinary existing-file else branch still calls resolve_module_edges only for the changed source module.

## COW_PRESERVATION

CODE_PATH_PROVED: _prepare_candidate_state creates a CandidateState copy; execute_refresh_plan assigns the rebuilt ProjectGraph to candidate.dependency_graph. IncrementalAnalysisEngine._apply_delta_and_commit receives that outcome and only later publishes candidate.dependency_graph and candidate.reexport_facts_by_module onto self.state in the canonical publication section. The integration regression drives the normal engine.update_file path and observes the committed state. No separate persistence or schema code changed.

## REAL_ENGINE_INCREMENTAL_TEST

The new integration test creates a temporary filesystem repository with pkg/__init__.py, pkg/child.py, consumer.py and unrelated.py. It uses index_repository, actual materialize_reexport_facts_by_module, build_graph, collect_module_artifacts, PersistentIdentityRegistry, FileStateManager and the real IncrementalAnalysisEngine. Neither planner nor graph builder is mocked.

Initial graph: consumer hard-depends on pkg.__init__ and soft-depends on pkg.child. Changing only pkg/__init__.py to child = 123 and calling engine.update_file returns UPDATED with fresh graph, fresh dependencies and fresh blast radius. Removing the assignment and updating again restores the prior child edge.

## FRESH_FULL_GRAPH_ORACLE

After each incremental update the test independently calls index_repository on the current files, materializes actual canonical reexport facts, builds a fresh graph, then compares the exact hard_edges and soft_edges maps against engine.state.dependency_graph. It also compares canonical reexport facts and module identity sets. Both the binding-add and binding-removal states match.

## CONSUMER_EDGE_BEFORE_AFTER

Before binding assignment: hard consumer -> pkg.__init__; soft consumer -> pkg.child.

After child = 123: hard consumer -> pkg.__init__ remains; soft consumer -> pkg.child is absent.

After removing the assignment: the soft consumer -> pkg.child edge returns; the hard initializer edge remains.

## AFFECTED_SET

For both changes, engine.update_file reports blast_radius_state=fresh and affected_modules contains consumer. The explicit freshness assertion prevents treating deferred/incomplete affected-set evidence as complete.

## UNRELATED_MODULE_ISOLATION

For both changes, unrelated is absent from affected_modules. Its hard and soft edge sets remain exactly equal to their pre-update values.

## TARGETED_TEST_RESULTS

Final targeted command used repository .venv Python and included:
tests/test_package_initializer_graph_refresh.py;
tests/test_refresh_planner.py;
tests/test_resolver.py;
tests/test_graph_cache_bindings.py;
tests/test_incremental_reverse_context.py::test_new_importing_file_immediately_updates_forward_and_reverse_graph;
tests/test_graph_only_live_analytics.py::test_case_b_import_add_recomputes_with_parity;
tests/test_graph_only_live_analytics.py::test_case_c_import_remove_recomputes_with_parity.

Result: 43 passed in 6.85s. No full repository suite, full analysis, Flask benchmark, or full GUI/MCP analysis was run.

## PY_COMPILE

.venv Python py_compile for refresh_planner.py and incremental/plan_executor.py: exit 0.

## GIT_DIFF_CHECK

git diff --check scoped to both production owners and the new test: exit 0. Only LF/CRLF working-copy notices were emitted.

## LIVE_REVISION_BEFORE_AFTER

345 -> 349. Continuous desktop_watcher UPDATED events:
- 346 refresh_planner.py
- 347 incremental/plan_executor.py
- 348 test_package_initializer_graph_refresh.py
- 349 test_package_initializer_graph_refresh.py

The final event query reported no additional events, continuous continuity and resync_required=false. Watcher events confirm source observation; they do not attest serving-process reload.

## WORKSPACE_SYNC_POSTCHECK

At canonical revision 349, Contextor get_symbol_implementation returned complete current RefreshPlanner.plan_refresh and execute_refresh_plan source with workspace_sync=verified. It also returned complete update_file and _apply_delta_and_commit source with workspace_sync=verified; _prepare_candidate_state was complete and verified. get_source_range returned the exact executor rebuild condition and pass-through. No truncated retrieval was treated as complete.

## RESYNC_REQUIRED

false before and after; event continuity continuous at final LIVE revision 349.

## RESTART_REQUIRED

YES_FOR_RUNTIME_CERTIFICATION. Production Python planner/executor code changed. No MCP, LIVE or Desktop process was restarted; serving-process imported-code freshness is not certified.

## REMAINING_DESKTOP_MCP_PARITY_GATE

This verifies the shared IncrementalAnalysisEngine path in isolated filesystem fixtures. It does not certify Desktop watcher versus MCP transport behavior, full canonical fact-family parity, or full GUI/MCP analysis parity. Those gates remain separate.

## FINAL_VERDICT

B0G2A_INCREMENTAL_GRAPH_PARITY_PASS for the specified initializer-binding incremental graph contract and targeted suite. It does not certify all canonical fact families, LIVE transport behavior, or complete Desktop/MCP parity. Await "proceduj".

## FULL_DIFFS

Complete actual diffs for all three changed source/test files:

```diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 1dd62d4..b039797 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -1013,7 +1013,18 @@ def execute_refresh_plan(
             executed_patch_families.append("reexport_facts")
 
         elif family == "dependency_graph":
-            if delta.is_deleted or delta.is_new:
+            if (
+                delta.is_deleted
+                or delta.is_new
+                or (
+                    delta.module_path.endswith(".__init__")
+                    and bool(
+                        delta.metadata_changes.get(
+                            "reexport_facts_changed"
+                        )
+                    )
+                )
+            ):
                 new_trie = build_trie(candidate.modules.keys())
                 new_package_root = detect_package_root(candidate.modules, new_trie)
                 new_graph = build_graph(
diff --git a/contextor/core/analysis/refresh_planner.py b/contextor/core/analysis/refresh_planner.py
index c8aedd6..973211f 100644
--- a/contextor/core/analysis/refresh_planner.py
+++ b/contextor/core/analysis/refresh_planner.py
@@ -111,6 +111,10 @@ class RefreshPlanner:
                 "reexport_facts_changed"
             )
         )
+        package_initializer_graph_change = (
+            module_path.endswith(".__init__")
+            and has_reexport_facts_change
+        )
         identity_registry_required = bool(
             delta
             and (
@@ -224,6 +228,22 @@ class RefreshPlanner:
             if has_import_changes:
                 patch_families.extend(["modules", "dependency_graph"])
                 graph_recomputations.extend(["macro_metrics", "reverse_blast_radius", "advanced_graph_metrics", "cycles"])
+            if (
+                package_initializer_graph_change
+                and "dependency_graph" not in patch_families
+            ):
+                patch_families.insert(
+                    patch_families.index("artifact_consumption"),
+                    "dependency_graph",
+                )
+                for item in (
+                    "macro_metrics",
+                    "reverse_blast_radius",
+                    "advanced_graph_metrics",
+                    "cycles",
+                ):
+                    if item not in graph_recomputations:
+                        graph_recomputations.append(item)
             patch_families.append("cached_analytics")
             if collision_facts_changed:
                 patch_families.extend(["collision_facts", "collisions"])
@@ -276,6 +296,18 @@ class RefreshPlanner:
                     patch_families.index("artifact_consumption"),
                     "reexport_facts",
                 )
+            graph_recomputations = ()
+            if package_initializer_graph_change:
+                patch_families.insert(
+                    patch_families.index("artifact_consumption"),
+                    "dependency_graph",
+                )
+                graph_recomputations = (
+                    "macro_metrics",
+                    "reverse_blast_radius",
+                    "advanced_graph_metrics",
+                    "cycles",
+                )
             if bool(delta.artifacts_added or delta.artifacts_removed) or (usage_delta and not usage_delta.is_empty):
                 patch_families.append("cached_analytics")
             if collision_facts_changed:
@@ -285,7 +317,7 @@ class RefreshPlanner:
                 reparse_modules=(),
                 recompute_modules=tuple(sorted(recompute_set)),
                 patch_families=compose_patch_families(patch_families),
-                graph_recomputations=(),
+                graph_recomputations=graph_recomputations,
                 refresh_completeness="complete",
                 semantic_certainty="statically_resolved",
                 reason=f"Artifact definitions change in '{module_path}'.",
@@ -329,6 +361,25 @@ class RefreshPlanner:
         if collision_facts_changed:
             patch_families.extend(["collision_facts", "collisions"])
 
+        graph_recomputations = ()
+        if package_initializer_graph_change:
+            if "dependency_graph" not in patch_families:
+                insert_at = (
+                    patch_families.index("artifact_consumption")
+                    if "artifact_consumption" in patch_families
+                    else len(patch_families)
+                )
+                patch_families.insert(
+                    insert_at,
+                    "dependency_graph",
+                )
+            graph_recomputations = (
+                "macro_metrics",
+                "reverse_blast_radius",
+                "advanced_graph_metrics",
+                "cycles",
+            )
+
         if has_usage:
             reason = f"Body/usage change in '{module_path}'."
         elif has_symbol_payload_change:
@@ -342,7 +393,7 @@ class RefreshPlanner:
             reparse_modules=(),
             recompute_modules=tuple(sorted(recompute_set)),
             patch_families=compose_patch_families(patch_families),
-            graph_recomputations=(),
+            graph_recomputations=graph_recomputations,
             refresh_completeness="complete",
             semantic_certainty="statically_resolved",
             reason=reason,
diff --git a/tests/test_package_initializer_graph_refresh.py b/tests/test_package_initializer_graph_refresh.py
new file mode 100644
index 0000000..05eb9c9
--- /dev/null
+++ b/tests/test_package_initializer_graph_refresh.py
@@ -0,0 +1,234 @@
+from pathlib import Path
+
+import pytest
+
+from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+from contextor.core.analysis.refresh_planner import RefreshPlanner
+from contextor.core.analysis.state_manager import (
+    FileDelta,
+    FileStateManager,
+    RepositoryAnalysisState,
+)
+from contextor.core.domain.usage_facts import UsageDelta
+from contextor.core.graph.graph import (
+    build_graph,
+    build_trie,
+    detect_package_root,
+)
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
+from contextor.core.reporting_engine.persistent_registry import (
+    PersistentIdentityRegistry,
+)
+from contextor.core.reporting_layer.artifact_usage_report import (
+    collect_module_artifacts,
+    collect_qualified_artifact_identities,
+)
+from contextor.core.symbol_engine.indexer import index_repository
+
+
+pytestmark = pytest.mark.live
+
+GRAPH_RECOMPUTATIONS = (
+    "macro_metrics",
+    "reverse_blast_radius",
+    "advanced_graph_metrics",
+    "cycles",
+)
+
+
+def _initializer_delta(**kwargs):
+    metadata_changes = kwargs.pop(
+        "metadata_changes",
+        {"reexport_facts_changed": True},
+    )
+    return FileDelta(
+        module_path="pkg.__init__",
+        metadata_changes=metadata_changes,
+        **kwargs,
+    )
+
+
+def test_binding_only_package_initializer_change_plans_graph_refresh():
+    plan = RefreshPlanner.plan_refresh(_initializer_delta())
+
+    assert set(plan.patch_families) == {
+        "reexport_facts",
+        "dependency_graph",
+        "artifact_consumption",
+        "cached_analytics",
+    }
+    assert plan.patch_families.count("dependency_graph") == 1
+    assert plan.graph_recomputations == GRAPH_RECOMPUTATIONS
+
+
+def test_package_initializer_symbol_change_keeps_registry_work_and_refreshes_graph():
+    plan = RefreshPlanner.plan_refresh(
+        _initializer_delta(artifacts_changed=["child"])
+    )
+
+    assert "definitions" in plan.patch_families
+    assert "identity_registry" in plan.patch_families
+    assert "reexport_facts" in plan.patch_families
+    assert "dependency_graph" in plan.patch_families
+    assert plan.patch_families.count("dependency_graph") == 1
+    assert plan.graph_recomputations == GRAPH_RECOMPUTATIONS
+
+
+def test_initializer_alias_retarget_preserves_operations_and_refreshes_graph():
+    usage_delta = UsageDelta(
+        module_path="pkg.__init__",
+        removed_aliases=(("child", "pkg.child"),),
+        added_aliases=(("child", "pkg.child_alias"),),
+    )
+    plan = RefreshPlanner.plan_refresh(
+        _initializer_delta(), usage_delta=usage_delta
+    )
+
+    assert {"definitions", "module_usages", "reexport_facts", "dependency_graph", "artifact_consumption", "cached_analytics"} <= set(plan.patch_families)
+    assert plan.patch_families.count("dependency_graph") == 1
+    assert plan.graph_recomputations == GRAPH_RECOMPUTATIONS
+
+
+def test_ordinary_module_reexport_change_keeps_previous_graph_semantics():
+    plan = RefreshPlanner.plan_refresh(
+        FileDelta(
+            module_path="pkg.child",
+            metadata_changes={"reexport_facts_changed": True},
+        )
+    )
+
+    assert "reexport_facts" in plan.patch_families
+    assert "artifact_consumption" in plan.patch_families
+    assert "cached_analytics" in plan.patch_families
+    assert "dependency_graph" not in plan.patch_families
+    assert plan.graph_recomputations == ()
+
+
+def test_initializer_import_change_does_not_duplicate_graph_work():
+    plan = RefreshPlanner.plan_refresh(
+        _initializer_delta(imports_changed=["pkg.child"])
+    )
+
+    assert plan.patch_families.count("dependency_graph") == 1
+    assert plan.graph_recomputations == GRAPH_RECOMPUTATIONS
+    assert all(plan.graph_recomputations.count(item) == 1 for item in GRAPH_RECOMPUTATIONS)
+
+
+def _fresh_graph(repo: Path):
+    repo_index = index_repository(str(repo))
+    modules = repo_index.modules
+    facts = materialize_reexport_facts_by_module(
+        modules,
+        repo_index.reference_facts_by_module,
+    )
+    trie = build_trie(modules.keys())
+    package_root = detect_package_root(modules, trie)
+    graph = build_graph(
+        modules,
+        trie=trie,
+        package_root=package_root,
+        reexport_facts_by_module=facts,
+    )
+    return modules, facts, graph
+
+
+def _make_real_engine(repo: Path, cache_dir: Path):
+    repo_index = index_repository(str(repo))
+    modules = repo_index.modules
+    artifacts, failures = collect_module_artifacts(modules, str(repo))
+    assert not failures
+    facts = materialize_reexport_facts_by_module(
+        modules,
+        repo_index.reference_facts_by_module,
+    )
+    trie = build_trie(modules.keys())
+    package_root = detect_package_root(modules, trie)
+    graph = build_graph(
+        modules,
+        trie=trie,
+        package_root=package_root,
+        reexport_facts_by_module=facts,
+    )
+    state = RepositoryAnalysisState(
+        modules=dict(modules),
+        reexport_facts_by_module=facts,
+        artifacts=artifacts,
+        dependency_graph=graph,
+        trie=trie,
+        package_root=package_root,
+        artifact_consumption={},
+    )
+
+    registry = PersistentIdentityRegistry(str(repo))
+    with registry.transaction():
+        registry.sync_with_workspace(
+            set(modules),
+            collect_qualified_artifact_identities(artifacts),
+        )
+
+    state_manager = FileStateManager(str(cache_dir))
+    for path in repo.rglob("*.py"):
+        state_manager.update_state(str(path))
+    return IncrementalAnalysisEngine(
+        state,
+        registry,
+        state_manager,
+        str(repo),
+    )
+
+
+def _assert_graph_matches_fresh(engine, repo):
+    fresh_modules, fresh_facts, fresh_graph = _fresh_graph(repo)
+    assert engine.state.dependency_graph.hard_edges == fresh_graph.hard_edges
+    assert engine.state.dependency_graph.soft_edges == fresh_graph.soft_edges
+    assert engine.state.reexport_facts_by_module == fresh_facts
+    assert set(engine.state.modules) == set(fresh_modules)
+    return fresh_graph
+
+
+def test_initializer_binding_updates_incremental_graph_and_recovers_child_edge(tmp_path):
+    repo = tmp_path / "repo"
+    package = repo / "pkg"
+    package.mkdir(parents=True)
+    initializer = package / "__init__.py"
+    initializer.write_text("", encoding="utf-8")
+    (package / "child.py").write_text("VALUE = 1\n", encoding="utf-8")
+    (repo / "consumer.py").write_text(
+        "from pkg import child\nchild.VALUE\n",
+        encoding="utf-8",
+    )
+    (repo / "unrelated.py").write_text("VALUE = 2\n", encoding="utf-8")
+
+    engine = _make_real_engine(repo, tmp_path / "cache")
+    initial_graph = engine.state.dependency_graph
+    assert initial_graph.hard_edges["consumer"] == {"pkg.__init__"}
+    assert initial_graph.soft_edges["consumer"] == {"pkg.child"}
+
+    initializer.write_text("child = 123\n", encoding="utf-8")
+    result = engine.update_file(str(initializer))
+
+    assert result.status == "UPDATED"
+    assert result.graph_state == "fresh"
+    assert result.dependencies_state == "fresh"
+    assert result.blast_radius_state == "fresh"
+    assert "dependency_graph" in result.shadow_plan.patch_families
+    assert "consumer" in result.affected_modules
+    assert "unrelated" not in result.affected_modules
+    assert engine.state.dependency_graph.hard_edges["consumer"] == {"pkg.__init__"}
+    assert engine.state.dependency_graph.soft_edges["consumer"] == set()
+    assert engine.state.dependency_graph.hard_edges["unrelated"] == initial_graph.hard_edges["unrelated"]
+    assert engine.state.dependency_graph.soft_edges["unrelated"] == initial_graph.soft_edges["unrelated"]
+    _assert_graph_matches_fresh(engine, repo)
+
+    initializer.write_text("", encoding="utf-8")
+    result = engine.update_file(str(initializer))
+
+    assert result.status == "UPDATED"
+    assert result.graph_state == "fresh"
+    assert result.dependencies_state == "fresh"
+    assert result.blast_radius_state == "fresh"
+    assert "consumer" in result.affected_modules
+    assert "unrelated" not in result.affected_modules
+    assert engine.state.dependency_graph.hard_edges["consumer"] == {"pkg.__init__"}
+    assert engine.state.dependency_graph.soft_edges["consumer"] == {"pkg.child"}
+    _assert_graph_matches_fresh(engine, repo)
```
