# CPA_FILE_UPDATE_PROPAGATION_GENERALITY_EVIDENCE_COMPLETION

STATUS=PARTIAL_DEFECT_CONFIRMED

HEAD_BEFORE=d3900e2c2affc244eddaf8ea97e97c4ed4dd90c4

ACCEPTED_PREEXISTING_WORKTREE=The previous three generality tests and fixpoint production implementation were accepted as pre-existing and are present in HEAD_BEFORE. The worktree was clean at task start. This task changes only those test cases as requested; no production file was changed.

SOURCE_DRIFT=NONE. The exact three requested test functions and replacement anchors were present at HEAD. Contextor revision 1480 reported the test module fresh with checked-and-none syntax diagnostics. The test-file diff passes `git diff --check -- tests/test_completeness_freshness_parity_proof.py` (Git only reports the working-copy LF-to-CRLF notice).

DIRECT_EVIDENCE=The only pytest invocation ran the three requested node IDs and returned `2 passed, 1 failed in 12.20s`. Symbol removal: seed `('b',)`, execution `('b',)`, full parity passed after removing the unnecessary `c` execution expectation. Re-export retarget: seed and execution `('c',)`, full parity passed. Ambiguity: `errors=[]`; both target entries and freshness were captured before the single snapshot assertion, which failed with incremental state `stale` and empty consumers versus full state `fresh` and consumer `consumer` on both targets.

CODE_PATH_PROVED=Contextor `contextor_fact_lineage` at revision 1480 returned fresh canonical `artifact_consumption` facts, no resync required, and identified `RepositoryAnalysisState.artifact_consumption` as owner; `ContextorFacade.analyze_project` as full materializer; `_rebuild_consumer_slice` as the incremental consumer-slice producer; `_apply_delta_and_commit` as incremental writer; and live-snapshot persistence/hydration. `get_symbol_lineage` resolved `_rebuild_consumer_slice` as active artifact `A2180/1` with complete lineage metadata.

CONTRACT_PROVED=Symbol removal reached and passed `_assert_full_parity` with seed `('b',)` and execution limited to `('b',)`. Retarget reached and passed its exact `('c',)` seed and execution assertions and `_assert_full_parity`. Ambiguity captured both requested canonical target keys and `artifact_consumption_state` from incremental and hydrated full state in one snapshot; the comparison directly failed.

INFERENCE=NONE.

UNKNOWN=In the ambiguity test, the final assertion comparing `result.artifact_consumption_state` to incremental state was not reached because the full snapshots differed. This does not affect the observed full-vs-incremental mismatch already shown for both canonical targets and freshness.

SYMBOL_REMOVE_PLAN=PASS; `result.shadow_plan.recompute_modules == ('b',)`.

SYMBOL_REMOVE_EXECUTION=PASS bounded execution; `result.execution_trace['recompute_modules'] == ('b',)`. The test no longer requires recomputing `c` for this removed-target case.

SYMBOL_REMOVE_FULL_PARITY=PASS. The canonical target `a::foo` was absent from both incremental and full state, and `_assert_full_parity` completed successfully.

SYMBOL_REMOVE_CLASSIFICATION=PASS_FULL_PARITY_BOUNDED_EXECUTION

REEXPORT_RETARGET_PLAN=PASS; `result.shadow_plan.recompute_modules == ('c',)`.

REEXPORT_RETARGET_EXECUTION=PASS; `result.execution_trace['recompute_modules'] == ('c',)`.

REEXPORT_RETARGET_INCREMENTAL_STATE=The test confirmed that `a::foo` no longer lists `b` or `c`, and `d::replacement` lists both `b` and `c` after retargeting `b.foo` to `d.replacement`.

REEXPORT_RETARGET_FULL_STATE=The fresh/full oracle completed without a validation error; `_assert_full_parity` confirmed the full canonical state equals the incremental state, including the retargeted consumer facts.

REEXPORT_RETARGET_FULL_PARITY=PASS

REEXPORT_RETARGET_CLASSIFICATION=PASS_FULL_PARITY

AMBIGUITY_INCREMENTAL_SNAPSHOT=`{'targets': {'pkg.a::B.foo': {'consumers': [], 'channels': {}}, 'pkg.a.B::foo': {'consumers': [], 'channels': {}}}, 'artifact_consumption_state': 'stale'}`

AMBIGUITY_FULL_SNAPSHOT=`{'targets': {'pkg.a::B.foo': {'consumers': ['consumer'], 'channels': {'consumer': ['direct_calls']}}, 'pkg.a.B::foo': {'consumers': ['consumer'], 'channels': {'consumer': ['direct_calls']}}}, 'artifact_consumption_state': 'fresh'}`

AMBIGUITY_VALIDATION_ERRORS=`errors=[]`; the full analysis hydrated successfully, and both target keys plus freshness were included in the failing assertion output.

AMBIGUITY_CLASSIFICATION=CONFIRMED_CANONICAL_PARITY_DEFECT

TEST_RESULTS=One physical pytest command with exactly the three requested node IDs; exit code 1; `2 passed, 1 failed in 12.20s`. No other tests or full suite were run. No test expectation or production code was changed after the failure.

CLASSIFICATION_PER_TEST=
- `test_transitive_reexport_symbol_remove_matches_full_oracle`: `PASS_FULL_PARITY_BOUNDED_EXECUTION`
- `test_reexport_retarget_matches_full_oracle`: `PASS_FULL_PARITY`
- `test_natural_ambiguity_transition_matches_full_oracle_state`: `CONFIRMED_CANONICAL_PARITY_DEFECT`

LIVE_EVIDENCE=Pre-edit revision was 1480. After the edit, `get_live_events(after_revision=1480)` returned revision 1481 with `origin=desktop_watcher`, `status=UPDATED` for the test file, `continuity=continuous`, and `resync_required=false`. No MCP `update_file` call, restart, or full analysis of the Contextor repository was performed. Full analyses occurred only in the tests' `tmp_path` directories.

FILES_CHANGED=
- `tests/test_completeness_freshness_parity_proof.py`

## ACTUAL_DIFF — tests/test_completeness_freshness_parity_proof.py

```diff
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index ae5ccf1..cc61d80 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -1205,7 +1205,6 @@ def test_transitive_reexport_symbol_remove_matches_full_oracle(tmp_path):
         "recompute_modules"
     ] == (
         "b",
-        "c",
     )
 
     assert "a::foo" not in engine.state.artifact_consumption
@@ -1229,7 +1228,7 @@ def test_reexport_retarget_matches_full_oracle(tmp_path):
         encoding="utf-8",
     )
     f_d.write_text(
-        "def foo():\n"
+        "def replacement():\n"
         "    return 'd'\n",
         encoding="utf-8",
     )
@@ -1270,7 +1269,7 @@ def test_reexport_retarget_matches_full_oracle(tmp_path):
     }
 
     f_reexport.write_text(
-        "from d import foo\n",
+        "from d import replacement as foo\n",
         encoding="utf-8",
     )
 
@@ -1300,7 +1299,7 @@ def test_reexport_retarget_matches_full_oracle(tmp_path):
 
     assert set(
         engine.state.artifact_consumption[
-            "d::foo"
+            "d::replacement"
         ]["consumers"]
     ) == {
         "b",
@@ -1372,37 +1371,41 @@ def test_natural_ambiguity_transition_matches_full_oracle_state(
     assert hydrated is not None
     oracle = hydrated.engine.state
 
-    for target_key in (
+    target_keys = (
         "pkg.a::B.foo",
         "pkg.a.B::foo",
-    ):
-        incremental_entry = engine.state.artifact_consumption.get(
-            target_key,
-            {},
-        )
-        oracle_entry = oracle.artifact_consumption.get(
-            target_key,
-            {},
-        )
+    )
 
-        assert (
-            incremental_entry
-            == oracle_entry
-        ), (
-            "ambiguity canonical entry differs from fresh full oracle: "
-            f"target={target_key!r}, "
-            f"incremental={incremental_entry!r}, "
-            f"full={oracle_entry!r}, "
-            f"errors={errors!r}"
-        )
+    incremental_snapshot = {
+        "targets": {
+            target_key: engine.state.artifact_consumption.get(
+                target_key,
+                {},
+            )
+            for target_key in target_keys
+        },
+        "artifact_consumption_state": (
+            engine.state.artifact_consumption_state
+        ),
+    }
 
-    assert (
-        engine.state.artifact_consumption_state
-        == oracle.artifact_consumption_state
-    ), (
-        "ambiguity freshness differs from fresh full oracle: "
-        f"incremental={engine.state.artifact_consumption_state!r}, "
-        f"full={oracle.artifact_consumption_state!r}, "
+    full_snapshot = {
+        "targets": {
+            target_key: oracle.artifact_consumption.get(
+                target_key,
+                {},
+            )
+            for target_key in target_keys
+        },
+        "artifact_consumption_state": (
+            oracle.artifact_consumption_state
+        ),
+    }
+
+    assert incremental_snapshot == full_snapshot, (
+        "ambiguity canonical state differs from fresh full oracle: "
+        f"incremental={incremental_snapshot!r}, "
+        f"full={full_snapshot!r}, "
         f"errors={errors!r}"
     )
 
```
