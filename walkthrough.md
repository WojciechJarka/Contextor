# CPA_SUITE_REPAIR_B_LEGACY_TEST_CONTRACT_MIGRATION

STATUS=STEP_PASS
CLASSIFICATION=FULL_SUITE_LEGACY_TEST_CONTRACT_MIGRATION_CERTIFIED
HEAD_BEFORE=236465e8833f39aa4e5936f3d5ee47561e744d9f
HEAD_AT_REPORT=236465e8833f39aa4e5936f3d5ee47561e744d9f
WORKTREE_BASELINE=CLEAN_AT_STEP_B_START
PRE_STEP_B_DIFF_BASELINE_SAVED=C:\Temp\CPA_SUITE_REPAIR_B_PRE_STEP_BASELINE
PRE_STEP_B_UNSTAGED_DIFF_SHA256=E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
PRE_STEP_B_STAGED_DIFF_SHA256=E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855
PRE_STEP_B_FILE_SNAPSHOTS=six exact target test files copied before first edit

CONTEXTOR_DISCOVERY
- Queried get_file_edit_context for all six target test modules and the production owner modules plan_executor.py, refresh_planner.py, live_state/store.py, reference/shared.py, and incremental/materialization.py.
- All returned canonical_state=fresh and workspace_sync=verified at canonical_revision=1587, with no syntax diagnostics.
- get_symbol_call_context proved _rebuild_consumer_slice is called twice by execute_refresh_plan and directly uses _resolve_canonical_target_keys; the singular helper delegates to the plural helper.
- load_snapshot calls _normalize_reexport_facts_state and emits load phase trace events.
- _build_reexport_map calls _extract_reexport_facts and _assemble_reexport_map; materialize_reexport_facts_by_module validates and extracts canonical facts.
- RefreshPlanner.plan_refresh was queried as the definitions patch planning owner.
- No production files, runtime processes, or repository-wide analysis were changed or started.

PRIVATE_REBUILD_CONTRACT
- Updated only the targeted private-helper test to consume the current single return value and pass reexport_facts_by_module={} plus module_export_surfaces={}.
- No production defaults or tuple return were added.

BACKFILL_RESOLVER_CONTRACT
- Replaced the synthetic singular-resolver ambiguity injection with an AssertionError guard against use of the singular compatibility helper.
- The test now asserts fresh incremental state, the exact pkg.impl_a::foo consumer/channel projection, and parity with fresh full analysis.

MULTI_IDENTITY_EXECUTION_CONTRACT
- Replaced the stale-state assertion with checks that both a::b.c and a.b::c receive the app direct_calls consumer while coverage and state remain fresh.

MULTI_IDENTITY_RECOMPUTE_CONTRACT
- Replaced the sticky stale-latch expectation with checks that both exact identities receive other_consumer during recompute and remain fresh through the clean patch.

LIVE_STORE_TIMING_CONTRACT
- Added normalize_reexport_facts_state to the exact ordered phase component list; no timing implementation changed.

REFERENCE_FUSION_CONTRACT
- The test materializes indexed.modules plus indexed.reference_facts_by_module before passing canonical facts to _assemble_reexport_map; production helper input semantics were unchanged.

REFRESH_PLAN_CONTRACT
- Updated the body-only retarget expected patch families to include definitions alongside module_usages, artifact_consumption, and cached_analytics.

TARGETED_STEP_B_TESTS=7
TARGETED_STEP_B_PASSED=7
TARGETED_STEP_B_FAILED=0
TARGETED_7_RESULTS=7 passed in 13.52s
TARGETED_NODE_IDS
- tests/test_incremental_plan_executor_complexity.py::test_indexed_rebuild_uses_precomputed_indexes_without_full_scan
- tests/test_completeness_freshness_parity_proof.py::test_incremental_backfill_does_not_use_singular_compatibility_resolver
- tests/test_matrix_clusters_ram_parity.py::test_multi_identity_execution_projects_all_exact_targets_and_stays_fresh
- tests/test_matrix_clusters_ram_parity.py::test_multi_identity_recompute_stays_fresh_across_clean_later_patch
- tests/test_live_state_store.py::test_split_snapshot_load_emits_non_overlapping_phase_timings
- tests/test_reference_fusion_integration.py::test_compact_reexport_oracle_and_artifact_output_parity
- tests/test_refresh_plan_execution.py::test_case_a_body_only_retarget

CHANGED_FILE_REGRESSION=PASS
CHANGED_FILE_REGRESSION_FAILED=0
CHANGED_FILE_REGRESSION_RESULT=138 passed in 134.23s
CHANGED_FILE_REGRESSION_MODULES
- tests/test_incremental_plan_executor_complexity.py
- tests/test_completeness_freshness_parity_proof.py
- tests/test_matrix_clusters_ram_parity.py
- tests/test_live_state_store.py
- tests/test_reference_fusion_integration.py
- tests/test_refresh_plan_execution.py

CANONICAL_REEXPORT_GUARD_FAILURES=0
OLD_AMBIGUITY_STALE_EXPECTATIONS_REMAINING=0
OLD_SINGULAR_BACKFILL_INJECTION_REMAINING=0
OLD_REBUILD_TUPLE_CONTRACT_REMAINING=0
OLD_REEXPORT_COMPACT_HELPER_INPUT_REMAINING=0
OLD_STORE_PHASE_LIST_REMAINING=0
OLD_DEFINITIONS_PATCH_EXPECTATION_REMAINING=0
PRODUCTION_FILES_CHANGED=NONE
UNEXPECTED_FAILURES=0
FULL_REPOSITORY_SUITE=NOT_RUN

CERTIFICATION
STATUS=STEP_PASS
CLASSIFICATION=FULL_SUITE_LEGACY_TEST_CONTRACT_MIGRATION_CERTIFIED
All seven targeted contracts and all six changed test modules pass. The only working-tree changes for this step are the six listed test files plus walkthrough.md as the required report.

FILES_CHANGED_CURRENT_STEP_B
- tests/test_incremental_plan_executor_complexity.py
- tests/test_completeness_freshness_parity_proof.py
- tests/test_matrix_clusters_ram_parity.py
- tests/test_live_state_store.py
- tests/test_reference_fusion_integration.py
- tests/test_refresh_plan_execution.py

FULL_DIFFS_CURRENT_STEP_B

```diff
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index 66faef5..5cb0e90 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -1898,24 +1898,33 @@ def test_definition_add_backfill_without_reread(tmp_path):
     _assert_full_parity(engine.state, oracle)
 
 
-def test_ambiguity_regression_real_backfill_path(tmp_path):
+def test_incremental_backfill_does_not_use_singular_compatibility_resolver(
+    tmp_path,
+):
     """
-    Proves that when a definition or provider update encounters ambiguity during backfill:
-    1. The ambiguous candidate slice is rejected in transactional fashion.
-    2. artifact_consumption_state fails closed to 'stale'.
-    3. Failure is sticky and no arbitrary target is bound.
+    Proves that incremental backfill is owned by the plural exact-target
+    resolver. The singular compatibility resolver must not participate
+    in consumer rebuilding, and incremental state must match fresh full
+    analysis.
     """
     pkg_dir = tmp_path / "pkg"
     pkg_dir.mkdir()
 
     f_consumer = tmp_path / "consumer.py"
-    f_consumer.write_text("from pkg.impl_a import foo\nfoo()\n", encoding="utf-8")
+    f_consumer.write_text(
+        "from pkg.impl_a import foo\nfoo()\n",
+        encoding="utf-8",
+    )
 
     f_provider = pkg_dir / "impl_a.py"
-    f_provider.write_text("def bar(): pass\n", encoding="utf-8")
+    f_provider.write_text(
+        "def bar(): pass\n",
+        encoding="utf-8",
+    )
 
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
+
     engine = IncrementalAnalysisEngine(
         RepositoryAnalysisState(modules={}),
         PersistentIdentityRegistry(str(tmp_path)),
@@ -1925,39 +1934,46 @@ def test_ambiguity_regression_real_backfill_path(tmp_path):
     engine.update_file(str(f_consumer))
     engine.update_file(str(f_provider))
 
-    # Now modify provider to add def foo(), but simulate ambiguity during resolution
-    f_provider.write_text("def bar(): pass\ndef foo(): pass\n", encoding="utf-8")
+    f_provider.write_text(
+        "def bar(): pass\ndef foo(): pass\n",
+        encoding="utf-8",
+    )
 
-    from contextor.core.analysis.incremental import plan_executor
-    original_resolve = plan_executor._resolve_canonical_target_key
-
-    def ambiguous_resolve(
-        target,
-        candidate_consumption,
-        candidate_artifacts,
-        expected_targets=None,
-        dotted_target_index=None,
+    with patch(
+        "contextor.core.analysis.incremental.plan_executor."
+        "_resolve_canonical_target_key",
+        side_effect=AssertionError(
+            "singular compatibility resolver must not drive "
+            "incremental consumer backfill"
+        ),
     ):
-        if target and "foo" in target:
-            return None, "ambiguous"
-        return original_resolve(
-            target,
-            candidate_consumption,
-            candidate_artifacts,
-            expected_targets=expected_targets,
-            dotted_target_index=dotted_target_index,
-        )
-
-    with patch("contextor.core.analysis.incremental.plan_executor._resolve_canonical_target_key", side_effect=ambiguous_resolve):
         res = engine.update_file(str(f_provider))
 
-    # Assert fail-closed state
-    assert res.artifact_consumption_state == "stale"
-    assert engine.state.artifact_consumption_state == "stale"
+    assert res.artifact_consumption_state == "fresh"
+    assert engine.state.artifact_consumption_state == "fresh"
+
+    entry = engine.state.artifact_consumption[
+        "pkg.impl_a::foo"
+    ]
+
+    assert entry["consumers"] == [
+        "consumer",
+    ]
+    assert set(
+        entry["channels"]["consumer"]
+    ) == {
+        "api_imports",
+        "direct_calls",
+    }
 
-    # Assert no arbitrary binding occurred for consumer
-    for target_key, entry in engine.state.artifact_consumption.items():
-        assert "consumer" not in entry.get("consumers", [])
+    oracle = _build_full_static_state(
+        tmp_path
+    )
+
+    _assert_full_parity(
+        engine.state,
+        oracle,
+    )
 
 
 def test_unresolved_target_never_appears(tmp_path):
diff --git a/tests/test_incremental_plan_executor_complexity.py b/tests/test_incremental_plan_executor_complexity.py
index d72d728..cda5595 100644
--- a/tests/test_incremental_plan_executor_complexity.py
+++ b/tests/test_incremental_plan_executor_complexity.py
@@ -80,39 +80,38 @@ def test_indexed_rebuild_uses_precomputed_indexes_without_full_scan(
         fail_target_rebuild,
     )
 
-    rebuilt, is_ambiguous = (
-        plan_executor._rebuild_consumer_slice(
-            consumer="consumer",
-            consumer_facts=usage,
-            candidate_consumption=consumption,
-            candidate_artifacts={
-                "provider": {
-                    "own_symbols": [
-                        "foo",
-                        "bar",
-                    ],
-                },
+    rebuilt = plan_executor._rebuild_consumer_slice(
+        consumer="consumer",
+        consumer_facts=usage,
+        candidate_consumption=consumption,
+        candidate_artifacts={
+            "provider": {
+                "own_symbols": [
+                    "foo",
+                    "bar",
+                ],
             },
-            reexports={},
-            expected_targets=_NoIterSet(
-                {
-                    "provider::foo",
-                    "provider::bar",
-                }
+        },
+        reexports={},
+        reexport_facts_by_module={},
+        module_export_surfaces={},
+        expected_targets=_NoIterSet(
+            {
+                "provider::foo",
+                "provider::bar",
+            }
+        ),
+        dotted_target_index={
+            "provider.foo": (
+                "provider::foo",
             ),
-            dotted_target_index={
-                "provider.foo": (
-                    "provider::foo",
-                ),
-                "provider.bar": (
-                    "provider::bar",
-                ),
-            },
-            consumer_target_index=consumer_target_index,
-        )
+            "provider.bar": (
+                "provider::bar",
+            ),
+        },
+        consumer_target_index=consumer_target_index,
     )
 
-    assert is_ambiguous is False
     assert rebuilt is consumption
 
     assert rebuilt[
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 52dd44b..1e556a8 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -420,6 +420,7 @@ def test_split_snapshot_load_emits_non_overlapping_phase_timings(tmp_path):
         "normalize_symbol_call_facts",
         "normalize_lineage_facts_state",
         "normalize_lineage_query_index_state",
+        "normalize_reexport_facts_state",
         "post_normalization_finalize",
     ]
 
diff --git a/tests/test_matrix_clusters_ram_parity.py b/tests/test_matrix_clusters_ram_parity.py
index 7fd9f4c..835f9b3 100644
--- a/tests/test_matrix_clusters_ram_parity.py
+++ b/tests/test_matrix_clusters_ram_parity.py
@@ -441,96 +441,223 @@ def test_resolver_distinguishes_unknown_from_ambiguous():
     assert key is None
 
 
-def test_ambiguity_execution_semantic_regression_fails_closed(tmp_path: Path):
+def test_multi_identity_execution_projects_all_exact_targets_and_stays_fresh(
+    tmp_path: Path,
+):
     """
-    PROVES that when ambiguous usage occurs during incremental refresh:
-    - Candidate state marks artifact_consumption_state = 'stale'
-    - State publication preserves 'stale'
-    - Even if key coverage is 100% complete.
+    PROVES that a complete dotted spelling resolving to multiple exact
+    canonical identities is projected to every exact identity and remains
+    fresh when canonical coverage is complete.
     """
     repo_dir = tmp_path / "ambiguous_repo"
     repo_dir.mkdir()
 
-    # Module 'a' with symbol 'b.c' and module 'a.b' with symbol 'c'
     a_dir = repo_dir / "a"
     a_dir.mkdir()
-    (a_dir / "__init__.py").write_text("", encoding="utf-8")
-    (a_dir / "b.py").write_text("def c(): pass\n", encoding="utf-8")
+    (a_dir / "__init__.py").write_text(
+        "",
+        encoding="utf-8",
+    )
+    (a_dir / "b.py").write_text(
+        "def c(): pass\n",
+        encoding="utf-8",
+    )
 
     app_file = repo_dir / "app.py"
-    app_file.write_text("import a.b\ndef run(): a.b.c()\n", encoding="utf-8")
+    app_file.write_text(
+        "import a.b\ndef run(): a.b.c()\n",
+        encoding="utf-8",
+    )
 
     facade = ContextorFacade()
-    errors, _ = facade.analyze_project(str(repo_dir))
+    errors, _ = facade.analyze_project(
+        str(repo_dir)
+    )
     assert not errors
 
     hydrated = hydrate_repository_engine(repo_dir)
     assert hydrated is not None
     engine = hydrated.engine
 
-    # Artificially create ambiguity domain in artifacts: a::b.c and a.b::c
-    engine.state.artifacts["a"] = {"consumers": {"b.c": {"consumers": [], "usage": {}}}}
-    engine.state.artifacts["a.b"] = {"consumers": {"c": {"consumers": [], "usage": {}}}}
-    engine.state.artifacts["app"] = {"consumers": {"run": {"consumers": [], "usage": {}}}}
+    engine.state.artifacts["a"] = {
+        "consumers": {
+            "b.c": {
+                "consumers": [],
+                "usage": {},
+            }
+        }
+    }
+    engine.state.artifacts["a.b"] = {
+        "consumers": {
+            "c": {
+                "consumers": [],
+                "usage": {},
+            }
+        }
+    }
+    engine.state.artifacts["app"] = {
+        "consumers": {
+            "run": {
+                "consumers": [],
+                "usage": {},
+            }
+        }
+    }
 
-    # Initial consumption matching domain
     engine.state.artifact_consumption = {
-        "a::b.c": {"consumers": [], "channels": {}},
-        "a.b::c": {"consumers": [], "channels": {}},
-        "app::run": {"consumers": [], "channels": {}},
+        "a::b.c": {
+            "consumers": [],
+            "channels": {},
+        },
+        "a.b::c": {
+            "consumers": [],
+            "channels": {},
+        },
+        "app::run": {
+            "consumers": [],
+            "channels": {},
+        },
     }
-    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
 
-    # Modify app.py to call ambiguous dotted target 'a.b.c'
-    app_file.write_text("import a.b\ndef run():\n    a.b.c()\n", encoding="utf-8")
+    assert (
+        validate_canonical_artifact_consumption_coverage(
+            engine.state.artifact_consumption,
+            engine.state.artifacts,
+        )
+        is True
+    )
 
-    res = engine.update_file(str(app_file))
-    assert res.status in ("UPDATED", "SUCCESS")
+    app_file.write_text(
+        "import a.b\ndef run():\n    a.b.c()\n",
+        encoding="utf-8",
+    )
 
-    # Invariant: coverage is 100% valid, but state MUST be stale due to semantic ambiguity!
-    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
-    assert engine.state.artifact_consumption_state == "stale"
-    assert res.artifact_consumption_state == "stale"
+    res = engine.update_file(
+        str(app_file)
+    )
 
+    assert res.status in (
+        "UPDATED",
+        "SUCCESS",
+    )
 
-def test_early_ambiguity_in_recompute_phase_is_sticky_across_clean_later_patch(tmp_path: Path):
-    """
-    PROVES that if an ambiguity is detected in an earlier phase (e.g. RECOMPUTE),
-    a subsequent clean PATCH phase with 100% valid coverage CANNOT overwrite the failure.
-    The candidate and committed state must remain 'stale'.
+    assert (
+        validate_canonical_artifact_consumption_coverage(
+            engine.state.artifact_consumption,
+            engine.state.artifacts,
+        )
+        is True
+    )
+
+    assert engine.state.artifact_consumption_state == "fresh"
+    assert res.artifact_consumption_state == "fresh"
+
+    for target_key in (
+        "a::b.c",
+        "a.b::c",
+    ):
+        entry = engine.state.artifact_consumption[
+            target_key
+        ]
+
+        assert "app" in entry[
+            "consumers"
+        ]
+        assert entry[
+            "channels"
+        ][
+            "app"
+        ] == [
+            "direct_calls",
+        ]
+
+
+def test_multi_identity_recompute_stays_fresh_across_clean_later_patch(
+    tmp_path: Path,
+):
+    """
+    PROVES that plural exact-target projection during RECOMPUTE remains
+    valid across a later clean PATCH phase. No ambiguity-stale latch is
+    produced because every exact canonical identity is retained.
     """
     repo_dir = tmp_path / "sticky_repo"
     repo_dir.mkdir()
 
     core_file = repo_dir / "core.py"
-    core_file.write_text("def helper(): return 1\ndef helper2(): return 2\n", encoding="utf-8")
+    core_file.write_text(
+        "def helper(): return 1\n"
+        "def helper2(): return 2\n",
+        encoding="utf-8",
+    )
 
     app_file = repo_dir / "app.py"
-    app_file.write_text("import core\ndef main(): return core.helper()\n", encoding="utf-8")
+    app_file.write_text(
+        "import core\n"
+        "def main(): return core.helper()\n",
+        encoding="utf-8",
+    )
 
     facade = ContextorFacade()
-    errors, _ = facade.analyze_project(str(repo_dir))
+    errors, _ = facade.analyze_project(
+        str(repo_dir)
+    )
     assert not errors
 
     hydrated = hydrate_repository_engine(repo_dir)
     assert hydrated is not None
     engine = hydrated.engine
 
-    # Domain has ambiguity: a::b.c and a.b::c
-    engine.state.artifacts["a"] = {"consumers": {"b.c": {"consumers": [], "usage": {}}}}
-    engine.state.artifacts["a.b"] = {"consumers": {"c": {"consumers": [], "usage": {}}}}
-    engine.state.artifact_consumption["a::b.c"] = {"consumers": [], "channels": {}}
-    engine.state.artifact_consumption["a.b::c"] = {"consumers": [], "channels": {}}
+    engine.state.artifacts["a"] = {
+        "consumers": {
+            "b.c": {
+                "consumers": [],
+                "usage": {},
+            }
+        }
+    }
+    engine.state.artifacts["a.b"] = {
+        "consumers": {
+            "c": {
+                "consumers": [],
+                "usage": {},
+            }
+        }
+    }
 
-    # Consumer module has ambiguous call in RECOMPUTE phase
-    from contextor.core.domain.usage_facts import ModuleUsageFacts
-    engine.state.module_usages["other_consumer"] = ModuleUsageFacts(
-        direct_calls=["a.b.c"]
+    engine.state.artifact_consumption[
+        "a::b.c"
+    ] = {
+        "consumers": [],
+        "channels": {},
+    }
+    engine.state.artifact_consumption[
+        "a.b::c"
+    ] = {
+        "consumers": [],
+        "channels": {},
+    }
+
+    from contextor.core.domain.usage_facts import (
+        ModuleUsageFacts,
+    )
+    engine.state.module_usages[
+        "other_consumer"
+    ] = ModuleUsageFacts(
+        direct_calls=[
+            "a.b.c",
+        ]
     )
-    engine.state.modules["other_consumer"] = Module(
-        module_id="other_consumer", path="other.py", absolute_path="/other.py", imports=[]
+    engine.state.modules[
+        "other_consumer"
+    ] = Module(
+        module_id="other_consumer",
+        path="other.py",
+        absolute_path="/other.py",
+        imports=[],
     )
-    engine.state.reexport_facts_by_module["other_consumer"] = {
+    engine.state.reexport_facts_by_module[
+        "other_consumer"
+    ] = {
         "exporter": "other_consumer",
         "explicit_all": None,
         "bindings": {},
@@ -538,37 +665,100 @@ def test_early_ambiguity_in_recompute_phase_is_sticky_across_clean_later_patch(t
     }
     with engine.registry.transaction():
         engine.registry.sync_with_workspace(
-            set(engine.state.modules),
-            aur.collect_qualified_artifact_identities(engine.state.artifacts),
+            set(
+                engine.state.modules
+            ),
+            aur.collect_qualified_artifact_identities(
+                engine.state.artifacts
+            ),
         )
 
-    # Perform clean update on app_file (switches to helper2 cleanly)
-    # Mock refresh planner to include 'other_consumer' in recompute_modules
-    from contextor.core.analysis.refresh_planner import RefreshPlanner
-    original_plan_refresh = RefreshPlanner.plan_refresh
+    from contextor.core.analysis.refresh_planner import (
+        RefreshPlanner,
+    )
+
+    original_plan_refresh = (
+        RefreshPlanner.plan_refresh
+    )
 
     def mock_plan(*args, **kwargs):
-        p = original_plan_refresh(*args, **kwargs)
-        # Add other_consumer to recompute_modules
+        plan = original_plan_refresh(
+            *args,
+            **kwargs,
+        )
+
         return RefreshPlan(
-            reparse_modules=p.reparse_modules,
-            recompute_modules=tuple(list(p.recompute_modules) + ["other_consumer"]),
-            patch_families=p.patch_families,
-            graph_recomputations=p.graph_recomputations,
-            refresh_completeness=p.refresh_completeness,
+            reparse_modules=(
+                plan.reparse_modules
+            ),
+            recompute_modules=tuple(
+                list(
+                    plan.recompute_modules
+                )
+                + [
+                    "other_consumer",
+                ]
+            ),
+            patch_families=(
+                plan.patch_families
+            ),
+            graph_recomputations=(
+                plan.graph_recomputations
+            ),
+            refresh_completeness=(
+                plan.refresh_completeness
+            ),
         )
 
-    with patch.object(RefreshPlanner, "plan_refresh", side_effect=mock_plan):
-        app_file.write_text("import core\ndef main(): return core.helper2()\n", encoding="utf-8")
-        res = engine.update_file(str(app_file))
-        assert res.status in ("UPDATED", "SUCCESS")
+    with patch.object(
+        RefreshPlanner,
+        "plan_refresh",
+        side_effect=mock_plan,
+    ):
+        app_file.write_text(
+            "import core\n"
+            "def main(): return core.helper2()\n",
+            encoding="utf-8",
+        )
 
-    # Invariant: Phase 1 (RECOMPUTE) failed on ambiguity.
-    # Phase 2 (PATCH artifact_consumption) was clean and coverage is True.
-    # Candidate & committed state MUST be 'stale'!
-    assert validate_canonical_artifact_consumption_coverage(engine.state.artifact_consumption, engine.state.artifacts) is True
-    assert engine.state.artifact_consumption_state == "stale"
-    assert res.artifact_consumption_state == "stale"
+        res = engine.update_file(
+            str(app_file)
+        )
+
+    assert res.status in (
+        "UPDATED",
+        "SUCCESS",
+    )
+
+    assert (
+        validate_canonical_artifact_consumption_coverage(
+            engine.state.artifact_consumption,
+            engine.state.artifacts,
+        )
+        is True
+    )
+
+    assert engine.state.artifact_consumption_state == "fresh"
+    assert res.artifact_consumption_state == "fresh"
+
+    for target_key in (
+        "a::b.c",
+        "a.b::c",
+    ):
+        entry = engine.state.artifact_consumption[
+            target_key
+        ]
+
+        assert "other_consumer" in entry[
+            "consumers"
+        ]
+        assert entry[
+            "channels"
+        ][
+            "other_consumer"
+        ] == [
+            "direct_calls",
+        ]
 
 
 def test_forensic_post_add_artifact_shape_and_canonical_definition_domain(tmp_path: Path):
diff --git a/tests/test_reference_fusion_integration.py b/tests/test_reference_fusion_integration.py
index a3553cc..384160d 100644
--- a/tests/test_reference_fusion_integration.py
+++ b/tests/test_reference_fusion_integration.py
@@ -7,7 +7,10 @@ from contextor.core.reference.index import (
     _assemble_reexport_map,
     assemble_reference_index_or_fallback,
 )
-from contextor.core.reference.shared import _build_reexport_map
+from contextor.core.reference.shared import (
+    _build_reexport_map,
+    materialize_reexport_facts_by_module,
+)
 from contextor.core.reporting_layer.artifact_usage_report import (
     generate_artifact_usage_report,
 )
@@ -213,8 +216,17 @@ def test_compact_reexport_oracle_and_artifact_output_parity(
     )
     indexed = indexer.index_repository(str(root))
 
-    assert _assemble_reexport_map(indexed.reference_facts_by_module) == (
-        _build_reexport_map(indexed.modules)
+    reexport_facts_by_module = (
+        materialize_reexport_facts_by_module(
+            indexed.modules,
+            indexed.reference_facts_by_module,
+        )
+    )
+
+    assert _assemble_reexport_map(
+        reexport_facts_by_module
+    ) == _build_reexport_map(
+        indexed.modules
     )
     passed = assemble_reference_index_or_fallback(
         indexed.modules, str(root), indexed.reference_facts_by_module
diff --git a/tests/test_refresh_plan_execution.py b/tests/test_refresh_plan_execution.py
index 9bdc957..ba8e893 100644
--- a/tests/test_refresh_plan_execution.py
+++ b/tests/test_refresh_plan_execution.py
@@ -93,7 +93,16 @@ def test_case_a_body_only_retarget(tmp_path):
     # Plan vs Execution Equality
     assert trace["reparse_modules"] == res.shadow_plan.reparse_modules == ()
     assert trace["recompute_modules"] == res.shadow_plan.recompute_modules == ()
-    assert set(trace["patch_families"]) == set(res.shadow_plan.patch_families) == {"module_usages", "artifact_consumption", "cached_analytics"}
+    assert set(
+        trace["patch_families"]
+    ) == set(
+        res.shadow_plan.patch_families
+    ) == {
+        "definitions",
+        "module_usages",
+        "artifact_consumption",
+        "cached_analytics",
+    }
 
     assert trace["graph_recomputations"] == res.shadow_plan.graph_recomputations == ()
```

