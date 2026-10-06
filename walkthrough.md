# CPA_FILE_UPDATE_CANONICAL_REEXPORT_PARITY_FOCUSED_RETRY

STATUS=BLOCKED_AFTER_FOCUSED_RETRY
HEAD=6195fcddd6fcb3929f6ec71dbe7c67a2ce811115
RETRY_BASELINE=ACCEPTED_PREVIOUS_STEP_WORKTREE; retry-only baseline copies are in C:\Temp\Contextor_Reexport_Parity_Focused_Retry_Baseline. The three copies were compared against the current files to isolate this retry's hunks.
SOURCE_DRIFT=NONE for the retry anchors; the requested target-sync, hydration assertion, and parity assertion anchors matched the accepted retry baseline.
ROOT_CAUSE_CONFIRMED=YES; direct source inspection showed canonical target synchronization nested after the unconditional RuntimeError raise in the re-export validation failure branch. It was unreachable for a valid candidate.
CANONICAL_TARGET_SYNC=RESTORED to the non-delete branch, before expected_targets/recompute. The focused parity gate still fails for the all-only consumer entry described below; no further diagnosis or patch was attempted.
HYDRATION_TEST_FIX=PASS; the focused hydration node completed with the hydrated IncrementalAnalysisEngine accessed through hydrated.state, and the canonical re-export fact-domain assertion passed.
FIRST_RETRY_RESULTS:
- PASS: tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_late_provider_matches_full_oracle
- PASS: tests/test_completeness_freshness_parity_proof.py::test_reexport_retarget_matches_full_oracle
- PASS: tests/test_completeness_freshness_parity_proof.py::test_natural_ambiguity_transition_matches_full_oracle_state
- PASS: tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_symbol_remove_matches_full_oracle; the bounded execution assertion observed ('b',).
- FAIL: tests/test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle
- PASS: tests/test_mcp_incremental_hydration.py::test_update_persist_restart_hydrate_keeps_live_reverse_context
Aggregate: 5 passed, 1 failed, 1 warning in 25.41s.
TEST_RESULT=FAIL; stopped immediately after the first-six retry gate failed.
SECOND_RETRY_RESULTS=NOT_RUN; prohibited by the retry contract after any first-six failure.
TEST_NODE_ID=tests/test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle
PARITY_RESULTS=FAIL for artifact_consumption consumer parity in the all-only node. Its reexport_facts equality assertion passed first; artifact_consumption key-domain equality also passed first.
FAILING_ASSERTION=sorted incremental consumers equals sorted full-oracle consumers in _assert_full_parity.
TARGET_IDENTITY=b::__all__
INCREMENTAL_ENTRY=consumer field observed as []; other entry fields were not emitted in the captured failure output.
FULL_ENTRY=consumer field observed as ['c']; other entry fields were not emitted in the captured failure output.
SHADOW_PLAN=Observed assertion passed that reexport_facts is in result.shadow_plan.patch_families; complete shadow-plan value was not emitted and is UNKNOWN_NOT_CAPTURED.
EXECUTION_TRACE=Observed assertion passed that 'c' is in result.execution_trace['recompute_modules']; complete trace value was not emitted and is UNKNOWN_NOT_CAPTURED.
ARTIFACT_CONSUMPTION_STATE=Key-domain equality assertion passed and target b::__all__ is present in both domains; exact full dictionaries/channels were not emitted and are UNKNOWN_NOT_CAPTURED.
REEXPORT_FACTS_EQUALITY=PASS for incremental canonical state vs full oracle in the all-only node.
RELEVANT_CANDIDATE_TARGET_DOMAIN=The assembler spy assertion passed that it received a dict whose keys equal set(engine.state.modules); artifact_consumption domains matched between incremental and oracle, and both include b::__all__. The complete target set was not emitted and is UNKNOWN_NOT_CAPTURED.
SOURCE_IO_PROOF=In the all-only node, the Module.ast_tree and _get_cached_ast guards recorded no access; the RAM assembler spy ran once and received the complete candidate facts domain. These assertions passed before the later artifact_consumption parity failure.
FILES_CHANGED_IN_RETRY:
- contextor/core/analysis/incremental/plan_executor.py
- tests/test_completeness_freshness_parity_proof.py
- tests/test_mcp_incremental_hydration.py
MCP_RESTART_REQUIRED=YES_AFTER_PRODUCTION_CODE_CHANGE; no Desktop/MCP/backend restart was performed in this retry.
FULL_ANALYSIS_REQUIRED_AFTER_RESTART=YES per the accepted schema 1.4 snapshot migration policy; it was not performed in this retry.
CLASSIFICATION=CANONICAL_PARITY_GATE_FAILED
DIRECT_EVIDENCE:
- The retry-only patch comparison used the saved accepted-baseline copies and confirmed only the three listed files have retry hunks.
- The all-only node passed its re-export facts equality check, artifact-consumption key-domain equality check, re-export patch-family check, downstream recompute membership check, assembler spy checks, and guarded AST-access checks before failing on the consumer comparison.
- The failing diagnostic identified target b::__all__, incremental consumers [], and full consumers ['c'].
- The test process result was 5 passed and 1 failed; no second retry set or git diff --check was run.
CODE_PATH_PROVED=The target-sync block now executes in the non-delete branch before expected target-domain construction. The parity helper compares canonical consumer lists against the full oracle.
CONTRACT_PROVED=The listed successful focused nodes and the passing assertions preceding the all-only consumer assertion are direct test evidence only.
INFERENCE=No cause for the remaining b::__all__ consumer mismatch is inferred.
UNKNOWN=Full shadow_plan, full execution_trace, complete artifact_consumption entries/channels, and the complete candidate target set were not present in captured pytest output. They are not reconstructed or guessed.
FILES_CHANGED_IN_RETRY=Only the three files listed above; walkthrough.md is the report artifact.
MCP_RESTART_PERFORMED=NO
FULL_REPOSITORY_PYTEST=NOT_RUN

RETRY_PATCH_ONLY

--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -765,6 +765,20 @@ def execute_refresh_plan(
         if "module_usages" in plan.patch_families and new_usage is not None:
             candidate.module_usages[delta.module_path] = new_usage
 
+        # Ensure canonical targets for delta.module_path exist in candidate.artifact_consumption
+        mod_art = candidate.artifacts.get(delta.module_path, {})
+        if isinstance(mod_art, dict):
+            current_targets = canonical_artifact_consumption_targets({delta.module_path: mod_art})
+            for t_key in current_targets:
+                if t_key not in candidate.artifact_consumption:
+                    candidate.artifact_consumption[t_key] = {"consumers": [], "channels": {}}
+            for art_key in list(candidate.artifact_consumption.keys()):
+                if (
+                    art_key.startswith(f"{delta.module_path}::")
+                    or art_key.startswith(f"{mod_id}::")
+                ) and art_key not in current_targets:
+                    candidate.artifact_consumption.pop(art_key, None)
+
     if not delta.is_deleted and "reexport_facts" in plan.patch_families:
         if new_reexport_facts is None:
             raise ValueError(
@@ -783,20 +797,6 @@ def execute_refresh_plan(
             "Candidate re-export facts do not cover the candidate module domain."
         )
 
-        # Ensure canonical targets for delta.module_path exist in candidate.artifact_consumption
-        mod_art = candidate.artifacts.get(delta.module_path, {})
-        if isinstance(mod_art, dict):
-            current_targets = canonical_artifact_consumption_targets({delta.module_path: mod_art})
-            for t_key in current_targets:
-                if t_key not in candidate.artifact_consumption:
-                    candidate.artifact_consumption[t_key] = {"consumers": [], "channels": {}}
-            for art_key in list(candidate.artifact_consumption.keys()):
-                if (
-                    art_key.startswith(f"{delta.module_path}::")
-                    or art_key.startswith(f"{mod_id}::")
-                ) and art_key not in current_targets:
-                    candidate.artifact_consumption.pop(art_key, None)
-
     expected_targets = canonical_artifact_consumption_targets(
         candidate.artifacts
     )

--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -73,7 +73,15 @@ def _assert_full_parity(incremental_state: RepositoryAnalysisState, oracle_state
     assert set(incremental_state.artifact_consumption.keys()) == set(oracle_state.artifact_consumption.keys())
     for target, ora_entry in oracle_state.artifact_consumption.items():
         inc_entry = incremental_state.artifact_consumption.get(target, {})
-        assert sorted(inc_entry.get("consumers", [])) == sorted(ora_entry.get("consumers", []))
+        assert sorted(
+            inc_entry.get("consumers", [])
+        ) == sorted(
+            ora_entry.get("consumers", [])
+        ), (
+            f"Target '{target}' consumers mismatch: "
+            f"incremental={inc_entry.get('consumers', [])!r}, "
+            f"full={ora_entry.get('consumers', [])!r}"
+        )
         inc_channels = inc_entry.get("channels", {})
         ora_channels = ora_entry.get("channels", {})
         assert set(inc_channels.keys()) == set(ora_channels.keys()), (

--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -134,8 +134,8 @@ def test_update_persist_restart_hydrate_keeps_live_reverse_context(tmp_path, mon
     hydrated = mcp_runtime.get_or_init_engine(repo.resolve())
     assert hydrated is not None
     assert validate_reexport_facts_by_module(
-        hydrated.engine.state.reexport_facts_by_module,
-        hydrated.engine.state.modules,
+        hydrated.state.reexport_facts_by_module,
+        hydrated.state.modules,
     )
     context = json.loads(
         mcp_server.get_file_edit_context.fn(
