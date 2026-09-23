CPA10L1A_INCREMENTAL_TARGET_RESOLUTION_COMPLEXITY_COMPLETION

STATUS
STATUS=BLOCKED
BLOCK_REASON=The required targeted pytest set completed with one failure.

BASELINE
CPA10L1_RETAINED=YES
RECOVERY_ANALYSIS_JOB_ID=141459b50d3a471c8bbccc7a6521cb42
RECOVERY_ANALYSIS_STATUS=completed
RECOVERY_ANALYSIS_LIVE_PUBLISH_STATUS=success
RECOVERY_ANALYSIS_LIVE_PUBLISH_REVISION=1355
RECOVERY_ANALYSIS_SKIPPED_PYTHON_FILES=0
PRE_RECOVERY_WRITER_EVIDENCE=No active or pending mutation admission: authority_event_state.pending_index=[], pending_start_sequence=null, pending_end_sequence=null. The recorded source update operation u-13456-1045 ended and published revision 1354 before the current local writes.

FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\tests\test_incremental_plan_executor_complexity.py
WALKTHROUGH_REPORT=C:\Temp\Contextor_Repo\walkthrough.md

IMPLEMENTATION_RESULT
TRANSIENT_CONSUMER_TARGET_INDEX_IMPLEMENTED=YES
TRANSIENT_DOTTED_TARGET_INDEX_IMPLEMENTED=YES
TARGET_DOMAIN_PRECOMPUTED_ONCE=YES
CANONICAL_STATE_SCHEMA_CHANGED=NO
PERSISTENCE_CHANGED=NO
PLANNER_SEMANTICS_CHANGED=NO
DOTTED_AMBIGUITY_SEMANTICS_PRESERVED=YES
COW_ENTRY_COPY_PRESERVED=YES
FIX_DESIGNED_BY_AGENT=NO

COMPLEXITY_CONTRACT
INDEXED_REBUILD_FULL_MAP_SCAN=NO
INDEXED_REBUILD_TOP_LEVEL_COPY=NO
INDEXED_REBUILD_TARGET_DOMAIN_REBUILD=NO
INDEXED_RESOLUTION_TARGET_DOMAIN_SCAN=NO
The dotted index groups every canonical target by dotted spelling and preserves all candidates in sorted tuples. The resolver reads the supplied index for dotted names and keeps its legacy domain scan when no dotted index is supplied.

TARGETED_TEST_RESULTS
FULL_TARGET_DOMAIN_BUILD_COUNT_TEST=PASS
DOTTED_INDEX_BUILD_COUNT_TEST=PASS
CONSUMER_INDEX_BUILD_COUNT_TEST=PASS
PY_COMPILE=PASS
TARGETED_TESTS=FAIL
TARGETED_PYTEST_SUMMARY=1 failed, 140 passed in 131.92s
FAILING_TEST=tests/test_completeness_freshness_parity_proof.py::test_ambiguity_regression_real_backfill_path
FAILURE=Its monkeypatched ambiguous_resolve(target, candidate_consumption, candidate_artifacts) accepts only three parameters. The updated _rebuild_consumer_slice passes expected_targets and dotted_target_index keyword arguments, so unittest.mock raises TypeError for unexpected keyword argument expected_targets.
OUT_OF_SCOPE_FIX=The failing test is outside the allowed file list; no other source or test file was changed.
FULL_SUITE_RUN=NO

CONTEXTOR_VERIFICATION
WORKSPACE_SYNC=verified (both files, canonical revision 1355, provenance=live)
NAME_COLLISIONS=0 (fresh direct get_name_collisions projection)
SYNTAX_ERRORS=0 (fresh; both changed files have checked_and_none syntax diagnostics)
CYCLES=0 (fresh diagnostics summary)
RECOVERY_ANALYSIS=One authorized recovery full project analysis; completed and published successfully at revision 1355.
POST_TEST_CONTEXTOR_CHECKS=PASS

CODE_CHANGED=YES
TEST_CODE_CHANGED=YES
GIT_COMMIT_PERFORMED=NO
GIT_PUSH_PERFORMED=NO
GIT_MUTATION_PERFORMED=NO

FULL_DIFFS

FULL_DIFF: C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
~~~diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index c04a55a..9ba2c1b 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -150,11 +150,49 @@ def _build_consumer_target_index(
     return index
 
 
+def _build_dotted_target_index(
+    expected_targets: Set[str],
+) -> Dict[str, Tuple[str, ...]]:
+    """
+    Builds one transient lookup from dotted target spelling to all
+    canonical targets that share that spelling.
+
+    Multiple canonical candidates are preserved so ambiguity semantics
+    remain identical to the legacy linear scan.
+    """
+    grouped: Dict[str, List[str]] = {}
+
+    for canonical in expected_targets:
+        definer, sep, symbol = canonical.partition("::")
+        if not sep:
+            continue
+
+        dotted = f"{definer}.{symbol}"
+        grouped.setdefault(
+            dotted,
+            [],
+        ).append(
+            canonical
+        )
+
+    return {
+        dotted: tuple(
+            sorted(
+                targets
+            )
+        )
+        for dotted, targets in grouped.items()
+    }
+
+
 def _resolve_canonical_target_key(
     target: Optional[str],
     candidate_consumption: Mapping[str, Any],
     candidate_artifacts: Mapping[str, Any],
     expected_targets: Optional[Set[str]] = None,
+    dotted_target_index: Optional[
+        Mapping[str, Tuple[str, ...]]
+    ] = None,
 ) -> Tuple[Optional[str], str]:
     """
     Resolves a target string against the canonical target domain.
@@ -177,15 +215,29 @@ def _resolve_canonical_target_key(
             return target, "resolved"
         return None, "unresolved"
 
-    # Exact dotted representation match against real canonical targets
-    matches: List[str] = []
-    for canonical in expected_targets:
-        definer, sep, symbol = canonical.partition("::")
-        if not sep:
-            continue
+    if dotted_target_index is not None:
+        matches = tuple(
+            dotted_target_index.get(
+                target,
+                (),
+            )
+        )
+    else:
+        fallback_matches: List[str] = []
 
-        if f"{definer}.{symbol}" == target:
-            matches.append(canonical)
+        for canonical in expected_targets:
+            definer, sep, symbol = canonical.partition("::")
+            if not sep:
+                continue
+
+            if f"{definer}.{symbol}" == target:
+                fallback_matches.append(
+                    canonical
+                )
+
+        matches = tuple(
+            fallback_matches
+        )
 
     if len(matches) == 1:
         return matches[0], "resolved"
@@ -212,6 +264,9 @@ def _rebuild_consumer_slice(
     candidate_artifacts: Mapping[str, Any],
     reexports: Mapping[str, str],
     expected_targets: Optional[Set[str]] = None,
+    dotted_target_index: Optional[
+        Mapping[str, Tuple[str, ...]]
+    ] = None,
     consumer_target_index: Optional[Dict[str, Set[str]]] = None,
 ) -> Tuple[Dict[str, Any], bool]:
     """
@@ -277,6 +332,7 @@ def _rebuild_consumer_slice(
             candidate_consumption,
             candidate_artifacts,
             expected_targets=expected_targets,
+            dotted_target_index=dotted_target_index,
         )
 
         if status == "ambiguous":
@@ -603,6 +659,9 @@ def execute_refresh_plan(
     expected_targets = canonical_artifact_consumption_targets(
         candidate.artifacts
     )
+    dotted_target_index = _build_dotted_target_index(
+        expected_targets
+    )
     consumer_target_index = _build_consumer_target_index(
         candidate.artifact_consumption
     )
@@ -627,6 +686,7 @@ def execute_refresh_plan(
                     candidate_artifacts=candidate.artifacts,
                     reexports=new_reexports,
                     expected_targets=expected_targets,
+                    dotted_target_index=dotted_target_index,
                     consumer_target_index=consumer_target_index,
                 )
                 if is_ambig:
@@ -694,6 +754,7 @@ def execute_refresh_plan(
                     candidate_artifacts=candidate.artifacts,
                     reexports=new_reexports,
                     expected_targets=expected_targets,
+                    dotted_target_index=dotted_target_index,
                     consumer_target_index=consumer_target_index,
                 )
                 if is_ambig:
~~~

FULL_DIFF: C:\Temp\Contextor_Repo\tests\test_incremental_plan_executor_complexity.py
~~~diff
diff --git a/tests/test_incremental_plan_executor_complexity.py b/tests/test_incremental_plan_executor_complexity.py
index 17f0793..d72d728 100644
--- a/tests/test_incremental_plan_executor_complexity.py
+++ b/tests/test_incremental_plan_executor_complexity.py
@@ -25,7 +25,15 @@ class _NoFullScanDict(dict):
         )
 
 
-def test_indexed_rebuild_uses_precomputed_domain_without_full_scan(
+class _NoIterSet(set):
+    def __iter__(self):
+        raise AssertionError(
+            "indexed dotted resolution must not scan "
+            "the full canonical target domain"
+        )
+
+
+def test_indexed_rebuild_uses_precomputed_indexes_without_full_scan(
     monkeypatch: pytest.MonkeyPatch,
 ) -> None:
     consumption = _NoFullScanDict(
@@ -86,9 +94,19 @@ def test_indexed_rebuild_uses_precomputed_domain_without_full_scan(
                 },
             },
             reexports={},
-            expected_targets={
-                "provider::foo",
-                "provider::bar",
+            expected_targets=_NoIterSet(
+                {
+                    "provider::foo",
+                    "provider::bar",
+                }
+            ),
+            dotted_target_index={
+                "provider.foo": (
+                    "provider::foo",
+                ),
+                "provider.bar": (
+                    "provider::bar",
+                ),
             },
             consumer_target_index=consumer_target_index,
         )
@@ -124,7 +142,33 @@ def test_indexed_rebuild_uses_precomputed_domain_without_full_scan(
     }
 
 
-def test_execute_refresh_plan_builds_target_domain_once_for_many_consumers(
+def test_precomputed_dotted_index_preserves_ambiguity() -> None:
+    expected_targets = {
+        "pkg.a::B.foo",
+        "pkg.a.B::foo",
+    }
+
+    dotted_target_index = (
+        plan_executor._build_dotted_target_index(
+            expected_targets
+        )
+    )
+
+    target, status = (
+        plan_executor._resolve_canonical_target_key(
+            "pkg.a.B.foo",
+            candidate_consumption={},
+            candidate_artifacts={},
+            expected_targets=expected_targets,
+            dotted_target_index=dotted_target_index,
+        )
+    )
+
+    assert target is None
+    assert status == "ambiguous"
+
+
+def test_execute_refresh_plan_builds_full_indexes_once_for_many_consumers(
     monkeypatch: pytest.MonkeyPatch,
     tmp_path: Path,
 ) -> None:
@@ -176,22 +220,66 @@ def test_execute_refresh_plan_builds_target_domain_once_for_many_consumers(
         plan_executor
         .canonical_artifact_consumption_targets
     )
-    target_domain_calls = 0
+    original_dotted_index = (
+        plan_executor
+        ._build_dotted_target_index
+    )
+    original_consumer_index = (
+        plan_executor
+        ._build_consumer_target_index
+    )
+
+    full_target_domain_calls = 0
+    dotted_index_calls = 0
+    consumer_index_calls = 0
 
     def counted_targets(
         artifacts,
     ):
-        nonlocal target_domain_calls
-        target_domain_calls += 1
+        nonlocal full_target_domain_calls
+
+        if set(artifacts) == {
+            "provider",
+        }:
+            full_target_domain_calls += 1
+
         return original_targets(
             artifacts
         )
 
+    def counted_dotted_index(
+        expected_targets,
+    ):
+        nonlocal dotted_index_calls
+        dotted_index_calls += 1
+        return original_dotted_index(
+            expected_targets
+        )
+
+    def counted_consumer_index(
+        consumption,
+    ):
+        nonlocal consumer_index_calls
+        consumer_index_calls += 1
+        return original_consumer_index(
+            consumption
+        )
+
     monkeypatch.setattr(
         plan_executor,
         "canonical_artifact_consumption_targets",
         counted_targets,
     )
+    monkeypatch.setattr(
+        plan_executor,
+        "_build_dotted_target_index",
+        counted_dotted_index,
+    )
+    monkeypatch.setattr(
+        plan_executor,
+        "_build_consumer_target_index",
+        counted_consumer_index,
+    )
 
     outcome = plan_executor.execute_refresh_plan(
         state=state,
@@ -215,7 +303,9 @@ def test_execute_refresh_plan_builds_target_domain_once_for_many_consumers(
         ),
     )
 
-    assert target_domain_calls == 1
+    assert full_target_domain_calls == 1
+    assert dotted_index_calls == 1
+    assert consumer_index_calls == 1
 
     assert state.artifact_consumption[
         "provider::foo"
~~~

