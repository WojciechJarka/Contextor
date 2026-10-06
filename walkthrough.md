# CPA_SUITE_REPAIR_A2_COMPLETE_CANONICAL_FIXTURE_MIGRATION

STATUS=PARTIAL_BLOCKED_NONEMPTY_SYNTHETIC_FIXTURES
CLASSIFICATION=PARTIAL_FIXTURE_MIGRATION_WITH_NONEMPTY_SYNTHETIC_BLOCKERS_AND_ONE_REMAINING_STEP_A_SEMANTIC_FAILURE
HEAD_BEFORE=56bb40ea02598ef4c7f738dffd5a458477e41590
HEAD_AT_REPORT=56bb40ea02598ef4c7f738dffd5a458477e41590
WORKTREE_BASELINE=CLEAN_AT_A2_START; prior Step A changes were accepted and already present at HEAD
SOURCE_DRIFT=NONE; HEAD remained unchanged and each edited anchor was checked against the current file

CANONICAL_OWNER
- Canonical field: RepositoryAnalysisState.reexport_facts_by_module.
- Materializer owner: contextor.core.reference.shared::materialize_reexport_facts_by_module.
- Enforcement evidence: execute_refresh_plan rejected incomplete baselines in targeted tests; save_snapshot rejected incomplete baselines in targeted tests. No production file was changed.
CODE_PATH_PROVED=execute_refresh_plan validates the canonical map before candidate execution; save_snapshot validates it before persistence, as shown by direct targeted-test stack traces.
CONTRACT_PROVED=Canonical map must validate for all modules in RepositoryAnalysisState; source-backed extraction and compact index facts follow the user-locked A2 rules.
INFERENCE=NONE used to justify any synthetic nonempty fixture.

CONTEXTOR_DISCOVERY
- Contextor file-edit context was queried before each A2 file edit; reusable helpers were additionally checked for callers where applicable.
- During those pre-edit queries, Contextor returned canonical_state=fresh and workspace_sync=verified (observed revisions 1566 through 1582). This is pre-edit discovery evidence, not a post-edit freshness claim.
- Contextor tool documentation was read after a parameter-contract error and the file/helper calls were then made using the documented argument contract.

SYNTHETIC_LINEAGE_BLOCKER=PASS
TEST_NODE=tests/test_lineage_state_lifecycle.py::test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild
RESULT=1 passed
DIRECT_EVIDENCE=The exact authorized pkg empty fact was added to that state. The source path remains missing and no source file was created.

EXACT_103_NODE_ACCOUNTING
EXACT_STEP_A_NODE_COUNT=103
EXACT_NODE_IDENTITIES_RUN=103
PYTEST_CASES_PASSED=91
PYTEST_CASES_REMAINING_FAILED_OR_BLOCKED=12
ORIGINAL_STEP_A_NODE_IDENTITIES_REMAINING=12
PARAMETERIZED_NODE_ACCOUNTING=The five explicit <lambda>0 through <lambda>4 IDs were each selected and counted separately.

REPRO_CONTRACT
- Canonical RepositoryAnalysisState fixtures were migrated only in test files.
- Source-backed Modules use materialize_reexport_facts_by_module(modules).
- Index-backed fixtures pass repo_index.reference_facts_by_module to the materializer.
- Hand-built empty facts were added only to the five fixtures listed below whose module inputs/imports and artifact domains are empty and whose target does not exercise exports.
- No semantic assertions, expected freshness values, planner expectations, production logic, or production guards were edited.

SOURCE_BACKED_MIGRATIONS
- tests/test_channel_parity_and_cow.py: three affected direct source-backed states.
- tests/test_collisions_live_lifecycle.py: two source-backed incremental lifecycle states.
- tests/test_h2c_collision_equivalence.py: two source-backed states; both pass prep.new_reexport_facts to execute_refresh_plan. The missing-source case remains blocked because its mod_a fixture contains a function collision fact.
- tests/test_incremental_artifact_consumption.py: source-backed target/package states for the affected cases.
- tests/test_incremental_reverse_context.py: source-backed states use the materializer; index_repository-derived states reuse repo_index.reference_facts_by_module.
- tests/test_live_e2e_corrections.py: the shared _engine_for_file helper uses index compact facts. Contextor call-context evidence showed its three direct test callers.
- tests/test_no_double_parse.py, tests/test_parity_and_freshness_proof.py, tests/test_payload_isolation.py, tests/test_persistent_topology_provenance.py, tests/test_shadow_planning_integration.py, and tests/test_topology_bootstrap_and_consumer_truth.py: source-backed states use the materializer.
- tests/test_syntax_diagnostics_full_analysis.py: shared _live_syntax_fixture reuses index.reference_facts_by_module. Contextor call-context evidence showed three direct callers.

INDEX_BACKED_MIGRATIONS
- tests/test_incremental_reverse_context.py: repo_index-derived state fixtures pass repo_index.reference_facts_by_module.
- tests/test_live_e2e_corrections.py::_engine_for_file: passes the index's compact facts.
- tests/test_syntax_diagnostics_full_analysis.py::_live_syntax_fixture: passes the index's compact facts.
INDEX_BACKED_FIXTURES_REUSE_COMPACT_FACTS=YES

SYNTHETIC_EMPTY_MIGRATIONS
MANUAL_SYNTHETIC_EMPTY_FACTS=5
1. tests/test_lineage_state_lifecycle.py::test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild — pkg, imports=[], no artifact/export payload; exact requested fact.
2. tests/test_graph_only_live_analytics.py::test_snapshot_backward_and_forward_compatibility — a, imports=[], artifacts absent; topology snapshot compatibility only.
3. tests/test_live_state_ipc.py::test_startup_backfill_preserves_filestate_content_and_revision_parity — a.py, SimpleNamespace() with no import entries, artifacts absent; startup backfill parity only.
4. tests/test_live_state_ipc.py::test_startup_backfill_failure_leaves_previous_generation_authoritative — same empty synthetic module domain as item 3.
5. tests/test_matrix_clusters_ram_parity.py::test_early_ambiguity_in_recompute_phase_is_sticky_across_clean_later_patch — other_consumer, imports=[], no artifacts entry/definition; only a direct-call usage record is represented, while the target is ambiguity handling rather than export semantics.

BLOCKED_NONEMPTY_SYNTHETIC_FIXTURES
COUNT=11 exact node identities in five fixture groups. No empty bindings were invented.

GROUP 1
FULL_PATH=tests/test_collisions_live_lifecycle.py
TEST_NODE=tests/test_collisions_live_lifecycle.py::test_plan_executor_missing_payload_fail_closed
MODULE_ID=a; MODULE_VALUE=Module(module_id='a', path='a.py', absolute_path='/tmp/a.py', imports=[])
IMPORTS=[]
ARTIFACTS=collision_facts contains X, type=variable, file=a, file_path=/tmp/a.py, code='X = 1', line 1.
MODULE_ID=b; MODULE_VALUE=Module(module_id='b', path='b.py', absolute_path='/tmp/b.py', imports=[])
IMPORTS=[]
ARTIFACTS=collision_facts contains X, type=variable, file=b, file_path=/tmp/b.py, code='X = 1', line 1.
WHY_EMPTY_FACT_IS_NOT_PROVABLY_CANONICAL=Both synthetic modules represent nonempty variable definitions and the test checks collision patch failure behavior.
DIRECT_EVIDENCE=execute_refresh_plan stops at the canonical re-export baseline guard before the expected ValueError assertion.

GROUP 2
FULL_PATH=tests/test_collisions_live_lifecycle.py
TEST_NODE=tests/test_collisions_live_lifecycle.py::test_missing_payload_transaction_failure
MODULE_ID=a; MODULE_VALUE=Module(module_id='a', path='a.py', absolute_path='/tmp/a.py', imports=[])
IMPORTS=[]
ARTIFACTS=collision_facts contains X, type=variable, file=a, file_path=/tmp/a.py, code='X = 1', line 1.
WHY_EMPTY_FACT_IS_NOT_PROVABLY_CANONICAL=The fixture represents a nonempty variable definition and tests collision-fact transaction behavior.
DIRECT_EVIDENCE=execute_refresh_plan stops at the canonical re-export baseline guard before the expected transaction ValueError.

GROUP 3
FULL_PATH=tests/test_h2c_collision_equivalence.py
TEST_NODE=tests/test_h2c_collision_equivalence.py::test_e2e_missing_source_fails_closed_no_blank_code_collision
MODULE_ID=mod_a; MODULE_VALUE=Module(module_id='mod_a', path='mod_a_deleted.py', absolute_path=<temporary-root>/mod_a_deleted.py, imports=[]); source does not exist.
IMPORTS=[]
ARTIFACTS=collision_facts contains missing_partner, type=function, file=mod_a, file_path=<temporary-root>/mod_a_deleted.py, code='', line 1-2. mod_b has real source and can be materialized.
WHY_EMPTY_FACT_IS_NOT_PROVABLY_CANONICAL=mod_a has an explicit nonempty function-definition collision fact; replacing it with empty bindings would discard represented semantics.
DIRECT_EVIDENCE=execute_refresh_plan rejects the incomplete map before the test's deferred-collision assertions.

GROUP 4 — seven exact nodes share _lineage_state_for_facts
FULL_PATH=tests/test_lineage_state_lifecycle.py
TEST_NODE=tests/test_lineage_state_lifecycle.py::test_snapshot_round_trip_compact_origin_reresolves_without_source_work; tests/test_lineage_state_lifecycle.py::test_snapshot_rejects_corrupt_compact_origin[<lambda>0]; [<lambda>1]; [<lambda>2]; [<lambda>3]; [<lambda>4]; tests/test_lineage_state_lifecycle.py::test_snapshot_legacy_interface_descriptor_capability_fails_closed_without_dropping_payload
MODULE_ID=provider; MODULE_VALUE=Module(module_id='provider', path='provider.py', absolute_path='/provider.py', imports=[])
IMPORTS=[]
ARTIFACTS=own_symbols={'target'}; consumer has own_symbols=set().
MODULE_ID=consumer; MODULE_VALUE=Module(module_id='consumer', path='consumer.py', absolute_path='/consumer.py', imports=[])
IMPORTS=[]
ARTIFACTS=own_symbols=set(); provider's target is a represented definition.
WHY_EMPTY_FACT_IS_NOT_PROVABLY_CANONICAL=The synthetic fixture has nonempty definition/artifact semantics and compact lineage facts; the canonical empty rule forbids dropping the represented target.
DIRECT_EVIDENCE=save_snapshot rejects each state at the canonical re-export baseline guard before lineage round-trip/corruption assertions.

GROUP 5
FULL_PATH=tests/test_lineage_state_lifecycle.py
TEST_NODE=tests/test_lineage_state_lifecycle.py::test_fresh_process_hydrates_materialized_symbolic_lineage_without_analysis
MODULE_ID=pkg; MODULE_VALUE=Module(module_id='pkg', path='pkg.py', absolute_path=<temporary-repo>/missing.py, imports=[]); source does not exist.
IMPORTS=[]
ARTIFACTS=state.artifacts is absent/empty; lineage_facts_by_source contains a materialized anchor/flow with SemanticEndpoint('A1') and a MaterializedSymbolicRef target.
WHY_EMPTY_FACT_IS_NOT_PROVABLY_CANONICAL=There is no source or compact re-export index proving the module has no definition/export semantics; the fixture materializes a symbol endpoint and external symbolic target. Treating this as empty would be an unsupported semantic assumption.
DIRECT_EVIDENCE=save_snapshot rejects the state before the fresh-process hydration assertions.

PER_FILE_NODE_RESULTS
| Exact target test file | PASS | Remaining blocked/failing | Result |
|---|---:|---:|---|
| tests/test_channel_parity_and_cow.py | 4 | 0 | PASS |
| tests/test_collisions_live_lifecycle.py | 2 | 2 | 2 synthetic nonempty blockers |
| tests/test_cycles_live_lifecycle.py | 1 | 0 | PASS |
| tests/test_graph_only_live_analytics.py | 1 | 0 | PASS |
| tests/test_h2c_collision_equivalence.py | 2 | 1 | 1 synthetic nonempty blocker |
| tests/test_incremental_artifact_consumption.py | 7 | 0 | PASS |
| tests/test_incremental_equivalence.py | 11 | 0 | PASS |
| tests/test_incremental_local_metrics.py | 11 | 0 | PASS |
| tests/test_incremental_phase_trace.py | 3 | 0 | PASS |
| tests/test_incremental_reverse_context.py | 7 | 0 | PASS |
| tests/test_lineage_state_lifecycle.py | 1 | 8 | 8 synthetic nonempty blockers |
| tests/test_live_e2e_corrections.py | 3 | 0 | PASS |
| tests/test_live_state_consistency.py | 9 | 0 | PASS |
| tests/test_live_state_ipc.py | 2 | 0 | PASS |
| tests/test_live_watcher_startup_reconciliation.py | 10 | 0 | PASS |
| tests/test_matrix_clusters_ram_parity.py | 0 | 1 | Existing Step A assertion failure |
| tests/test_no_double_parse.py | 2 | 0 | PASS |
| tests/test_parity_and_freshness_proof.py | 6 | 0 | PASS |
| tests/test_payload_isolation.py | 1 | 0 | PASS |
| tests/test_persistent_topology_provenance.py | 2 | 0 | PASS |
| tests/test_shadow_planning_integration.py | 2 | 0 | PASS |
| tests/test_symbol_call_facts.py | 1 | 0 | PASS |
| tests/test_syntax_diagnostics_full_analysis.py | 2 | 0 | PASS |
| tests/test_topology_bootstrap_and_consumer_truth.py | 1 | 0 | PASS |
| TOTAL | 91 | 12 | 103 exact identities |

STEP_A_SEMANTIC_FAILURE_REMAINS
TEST_NODE=tests/test_matrix_clusters_ram_parity.py::test_early_ambiguity_in_recompute_phase_is_sticky_across_clean_later_patch
DIRECT_EVIDENCE=After adding the permitted empty canonical fact for other_consumer, execution passes the canonical baseline guard and reaches the unchanged assertion at line 570. Expected artifact_consumption_state='stale'; actual value='fresh'.
CLASSIFICATION=EXISTING_STEP_A_NODE_ASSERTION_FAILURE_AFTER_FIXTURE_GUARD_CLEARANCE
UNKNOWN=The current evidence does not establish why the expected stale state was not produced. No assertion or production behavior was changed.

EXACT_STEP_A_ACCEPTANCE=NOT_MET
EXACT_STEP_A_ORIGINAL_FAILURES_REMAINING=12 (11 are blocked at canonical baseline due to nonempty synthetic semantics; one reaches a semantic assertion and fails)
CHANGED_FILE_REGRESSION=NOT_RUN; the contract gates it on all 103 exact nodes passing, which did not occur.

EXPECTED_STEP_B_FAILURES=6; all six named STEP B node IDs were left untouched and were not run.
UNEXPECTED_FAILURES=1 existing STEP A semantic assertion failure described above.
UNEXPECTED_NEW_FAILURES=0; the failing identity was already part of the original 103 target set.

CERTIFICATION
SYNTHETIC_LINEAGE_BLOCKER=PASS
EXACT_STEP_A_NODE_COUNT=103
EXACT_STEP_A_ORIGINAL_FAILURES_REMAINING=12
SOURCE_BACKED_FIXTURES_USE_MATERIALIZER=YES
INDEX_BACKED_FIXTURES_REUSE_COMPACT_FACTS=YES
MANUAL_SOURCE_BACKED_REEXPORT_FACTS=ZERO
MANUAL_SYNTHETIC_EMPTY_FACTS=5
BLOCKED_NONEMPTY_SYNTHETIC_FIXTURES=11
PRODUCTION_FILES_CHANGED=NONE
PRODUCTION_GUARDS_CHANGED=NO
EXPECTED_STEP_B_FAILURES=6
UNEXPECTED_NEW_FAILURES=0
CLASSIFICATION=NOT_CERTIFIED; bounded A2 fixture migration is partial and one Step A semantic assertion remains failing.

FILES_CHANGED_CURRENT_A2
- tests/test_channel_parity_and_cow.py
- tests/test_collisions_live_lifecycle.py
- tests/test_graph_only_live_analytics.py
- tests/test_h2c_collision_equivalence.py
- tests/test_incremental_artifact_consumption.py
- tests/test_incremental_reverse_context.py
- tests/test_lineage_state_lifecycle.py
- tests/test_live_e2e_corrections.py
- tests/test_live_state_ipc.py
- tests/test_matrix_clusters_ram_parity.py
- tests/test_no_double_parse.py
- tests/test_parity_and_freshness_proof.py
- tests/test_payload_isolation.py
- tests/test_persistent_topology_provenance.py
- tests/test_shadow_planning_integration.py
- tests/test_syntax_diagnostics_full_analysis.py
- tests/test_topology_bootstrap_and_consumer_truth.py
PRODUCTION_FILES_CHANGED=NONE
STEP_B_NODE_EDITS=NONE (test_matrix_clusters_ram_parity.py changes only the distinct Step A node; the forbidden Step B node remains unchanged)

FULL_DIFFS_CURRENT_A2
```diff
diff --git a/tests/test_channel_parity_and_cow.py b/tests/test_channel_parity_and_cow.py
index cb4cafe..5c69483 100644
--- a/tests/test_channel_parity_and_cow.py
+++ b/tests/test_channel_parity_and_cow.py
@@ -94,7 +94,11 @@ def test_channel_transition_direct_to_callback(tmp_path):
     f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -128,7 +132,11 @@ def test_cow_immutability_non_empty_old_state(tmp_path):
     f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -179,7 +187,11 @@ def test_unrelated_relation_preservation(tmp_path):
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
     m_other = Module(module_id="other", path="other.py", absolute_path=str(f_other), imports=[])
 
-    state = RepositoryAnalysisState(modules={"target": m_target, "other": m_other})
+    modules = {"target": m_target, "other": m_other}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
diff --git a/tests/test_collisions_live_lifecycle.py b/tests/test_collisions_live_lifecycle.py
index 23e72b2..cc19e56 100644
--- a/tests/test_collisions_live_lifecycle.py
+++ b/tests/test_collisions_live_lifecycle.py
@@ -41,6 +41,7 @@ from contextor.core.analysis.state_manager import (
     RepositoryAnalysisState,
 )
 from contextor.core.domain.module import Module
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.validator.collisions import (
@@ -274,11 +275,13 @@ def test_incremental_engine_end_to_end_collision_lifecycle():
         tree_a = ast.parse(file_a.read_text(encoding="utf-8"))
         tree_b = ast.parse(file_b.read_text(encoding="utf-8"))
 
+        modules = {
+            "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[]),
+            "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(file_b), imports=[]),
+        }
         state = RepositoryAnalysisState(
-            modules={
-                "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[]),
-                "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(file_b), imports=[]),
-            },
+            modules=modules,
+            reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
             collision_facts={
                 "mod_a": extract_module_collision_facts(tree_a, "mod_a", str(file_a)),
                 "mod_b": extract_module_collision_facts(tree_b, "mod_b", str(file_b)),
@@ -466,11 +469,13 @@ def test_deferred_recovery_when_final_missing_fact_delivered():
         tree_a = ast.parse(file_a.read_text(encoding="utf-8"))
 
         # Incomplete initial state: missing mod_b fact, state is deferred
+        modules = {
+            "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[]),
+            "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(file_b), imports=[]),
+        }
         state = RepositoryAnalysisState(
-            modules={
-                "mod_a": Module(module_id="mod_a", path="mod_a.py", absolute_path=str(file_a), imports=[]),
-                "mod_b": Module(module_id="mod_b", path="mod_b.py", absolute_path=str(file_b), imports=[]),
-            },
+            modules=modules,
+            reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
             collision_facts={
                 "mod_a": extract_module_collision_facts(tree_a, "mod_a", str(file_a)),
             },
diff --git a/tests/test_graph_only_live_analytics.py b/tests/test_graph_only_live_analytics.py
index 082a23c..d201593 100644
--- a/tests/test_graph_only_live_analytics.py
+++ b/tests/test_graph_only_live_analytics.py
@@ -281,6 +281,14 @@ def test_snapshot_backward_and_forward_compatibility(tmp_path):
     # 1. State WITH topology_analytics
     state = RepositoryAnalysisState(
         modules={"a": Module("a", "a.py", "/a.py", [])},
+        reexport_facts_by_module={
+            "a": {
+                "exporter": "a",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            }
+        },
         topology_analytics={"pagerank": {"a": 1.0}},
     )
     meta = save_snapshot(state, cache_dir, "test_state", repo_id="repo1", root_path=str(tmp_path))
diff --git a/tests/test_h2c_collision_equivalence.py b/tests/test_h2c_collision_equivalence.py
index 4010b01..c258e08 100644
--- a/tests/test_h2c_collision_equivalence.py
+++ b/tests/test_h2c_collision_equivalence.py
@@ -20,6 +20,7 @@ from unittest.mock import MagicMock, patch
 import pytest
 
 from contextor.core.domain.module import Module
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.domain.validation import ValidationError
 from contextor.core.validator.collisions import (
     CollisionFact,
@@ -680,13 +681,15 @@ def test_e2e_hydrated_clean_and_edit_b_identical_foo():
 
         mod_a = Module(module_id="mod_a", path="mod_a.py", absolute_path=str(path_a), imports=[])
         mod_b = Module(module_id="mod_b", path="mod_b.py", absolute_path=str(path_b), imports=[])
+        modules = {"mod_a": mod_a, "mod_b": mod_b}
 
         # Hydrated state where A.shared_processor was persisted as clean (code="")
         facts_a = [{"name": "shared_processor", "type": "function", "file": "mod_a", "file_path": str(path_a), "code": "", "line_start": 1, "line_end": 2, "col_start": 0, "col_end": 20}]
         facts_b_old = []
 
         state = RepositoryAnalysisState(
-            modules={"mod_a": mod_a, "mod_b": mod_b},
+            modules=modules,
+            reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
             collision_facts={"mod_a": facts_a, "mod_b": facts_b_old},
             collisions_state="fresh",
             collisions=[],
@@ -720,6 +723,7 @@ def test_e2e_hydrated_clean_and_edit_b_identical_foo():
             root_path=str(root),
             file_path=str(path_b),
             new_collision_facts=prep.new_collision_facts,
+            new_reexport_facts=prep.new_reexport_facts,
         )
 
         candidate = outcome.candidate_state
@@ -752,13 +756,15 @@ def test_e2e_hydrated_clean_and_edit_b_conflicting_foo():
 
         mod_a = Module(module_id="mod_a", path="mod_a.py", absolute_path=str(path_a), imports=[])
         mod_b = Module(module_id="mod_b", path="mod_b.py", absolute_path=str(path_b), imports=[])
+        modules = {"mod_a": mod_a, "mod_b": mod_b}
 
         # Hydrated state where A.process_item has code=""
         facts_a = [{"name": "process_item", "type": "function", "file": "mod_a", "file_path": str(path_a), "code": "", "line_start": 1, "line_end": 2, "col_start": 0, "col_end": 23}]
         facts_b_old = []
 
         state = RepositoryAnalysisState(
-            modules={"mod_a": mod_a, "mod_b": mod_b},
+            modules=modules,
+            reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
             collision_facts={"mod_a": facts_a, "mod_b": facts_b_old},
             collisions_state="fresh",
             collisions=[],
@@ -792,6 +798,7 @@ def test_e2e_hydrated_clean_and_edit_b_conflicting_foo():
             root_path=str(root),
             file_path=str(path_b),
             new_collision_facts=prep.new_collision_facts,
+            new_reexport_facts=prep.new_reexport_facts,
         )
 
         candidate = outcome.candidate_state
diff --git a/tests/test_incremental_artifact_consumption.py b/tests/test_incremental_artifact_consumption.py
index 5fee154..07d1f95 100644
--- a/tests/test_incremental_artifact_consumption.py
+++ b/tests/test_incremental_artifact_consumption.py
@@ -99,8 +99,10 @@ def test_case_2_modify_call_target(tmp_path):
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
 
+    modules = {"target": m_target}
     state = RepositoryAnalysisState(
-        modules={"target": m_target},
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
         artifacts={"target": {"symbols": {"functions": ["foo", "bar"]}, "own_symbols": ["foo", "bar"]}},
     )
     cache_dir = tmp_path / "cache"
@@ -139,8 +141,10 @@ def test_case_3_delete_consumer(tmp_path):
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
 
+    modules = {"target": m_target}
     state = RepositoryAnalysisState(
-        modules={"target": m_target},
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
     )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
@@ -171,7 +175,11 @@ def test_case_4_alias_resolution(tmp_path):
     f_consumer.write_text("from target import foo as local\nlocal()\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -194,7 +202,11 @@ def test_case_5_qualified_call(tmp_path):
     f_consumer.write_text("import target\ntarget.foo()\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -221,7 +233,11 @@ def test_case_6_name_collision(tmp_path):
 
     m_a = Module(module_id="mod_a", path="mod_a.py", absolute_path=str(f_a), imports=[])
     m_b = Module(module_id="mod_b", path="mod_b.py", absolute_path=str(f_b), imports=[])
-    state = RepositoryAnalysisState(modules={"mod_a": m_a, "mod_b": m_b})
+    modules = {"mod_a": m_a, "mod_b": m_b}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -262,11 +278,15 @@ def test_case_7_reexport_retarget_no_reread(tmp_path):
     m_impl_a = Module(module_id="pkg.impl_a", path="pkg/impl_a.py", absolute_path=str(f_impl_a), imports=[])
     m_impl_b = Module(module_id="pkg.impl_b", path="pkg/impl_b.py", absolute_path=str(f_impl_b), imports=[])
 
-    state = RepositoryAnalysisState(modules={
+    modules = {
         "pkg.__init__": m_init,
         "pkg.impl_a": m_impl_a,
         "pkg.impl_b": m_impl_b,
-    })
+    }
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
diff --git a/tests/test_incremental_reverse_context.py b/tests/test_incremental_reverse_context.py
index d8567b1..0cbfe69 100644
--- a/tests/test_incremental_reverse_context.py
+++ b/tests/test_incremental_reverse_context.py
@@ -68,13 +68,17 @@ def test_deleted_file_reports_all_removed_definition_artifacts(tmp_path):
         "class Worker:\n    def execute(self):\n        return run()\n",
         encoding="utf-8",
     )
-    modules = index_repository(str(tmp_path)).modules
+    repo_index = index_repository(str(tmp_path))
+    modules = repo_index.modules
     artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
     assert not failures
     trie = build_trie(modules)
     package_root = detect_package_root(modules, trie)
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=artifacts,
         dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
         trie=trie,
@@ -206,13 +210,17 @@ def test_update_file_returns_fresh_blast_radius_for_modified_provider(tmp_path):
     consumer = tmp_path / "consumer.py"
     consumer.write_text("from provider import run\nrun()\n", encoding="utf-8")
     
-    modules = index_repository(str(tmp_path)).modules
+    repo_index = index_repository(str(tmp_path))
+    modules = repo_index.modules
     artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
     assert not failures
     trie = build_trie(modules)
     package_root = detect_package_root(modules, trie)
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=artifacts,
         dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
         trie=trie,
@@ -244,13 +252,17 @@ def test_update_file_returns_fresh_blast_radius_for_deleted_file(tmp_path):
     consumer = tmp_path / "consumer.py"
     consumer.write_text("from provider import run\nrun()\n", encoding="utf-8")
     
-    modules = index_repository(str(tmp_path)).modules
+    repo_index = index_repository(str(tmp_path))
+    modules = repo_index.modules
     artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
     assert not failures
     trie = build_trie(modules)
     package_root = detect_package_root(modules, trie)
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=artifacts,
         dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
         trie=trie,
@@ -280,13 +292,17 @@ def test_update_file_add_module_resolving_dependency(tmp_path):
     consumer = tmp_path / "consumer.py"
     consumer.write_text("from provider import run\nrun()\n", encoding="utf-8")
     
-    modules = index_repository(str(tmp_path)).modules
+    repo_index = index_repository(str(tmp_path))
+    modules = repo_index.modules
     artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
     assert not failures
     trie = build_trie(modules)
     package_root = detect_package_root(modules, trie)
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=artifacts,
         dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
         trie=trie,
@@ -322,6 +338,9 @@ def test_update_file_missing_graph_evidence_is_deferred_and_empty_affected_modul
         registry.sync_with_workspace({"sample"}, {"sample::run": "A1/1"})
     state = RepositoryAnalysisState(
         modules={"sample": module},
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            {"sample": module}
+        ),
         artifacts={},
         dependency_graph=None,
         trie={},
@@ -368,6 +387,9 @@ def test_update_file_delete_with_missing_old_graph_is_deferred_despite_rebuilt_n
 
     state = RepositoryAnalysisState(
         modules={"mod_a": module_a, "mod_b": module_b},
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            {"mod_a": module_a, "mod_b": module_b}
+        ),
         artifacts={},
         dependency_graph=None,  # Missing OLD graph
         trie={},
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index b441b08..209b53c 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -444,6 +444,14 @@ def test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild
     )
     state = RepositoryAnalysisState(
         modules={"pkg": module},
+        reexport_facts_by_module={
+            "pkg": {
+                "exporter": "pkg",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            }
+        },
         dependency_graph=ProjectGraph(
             hard_edges={"pkg": set()},
             soft_edges={"pkg": set()},
diff --git a/tests/test_live_e2e_corrections.py b/tests/test_live_e2e_corrections.py
index 423442c..f9e5992 100644
--- a/tests/test_live_e2e_corrections.py
+++ b/tests/test_live_e2e_corrections.py
@@ -30,6 +30,7 @@ from contextor.core.reporting_layer.artifact_usage_report import (
     collect_module_artifacts,
 )
 from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 
 pytestmark = pytest.mark.live
@@ -76,11 +77,15 @@ def _engine_for_file(tmp_path):
     source = tmp_path / "provider.py"
     source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
     registry = PersistentIdentityRegistry(str(tmp_path))
-    modules = index_repository(str(tmp_path)).modules
+    repo_index = index_repository(str(tmp_path))
+    modules = repo_index.modules
     artifacts, _ = collect_module_artifacts(modules, str(tmp_path))
     trie = build_trie(modules)
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=artifacts,
         dependency_graph=build_graph(modules),
         trie=trie,
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index 1de3660..4094cc6 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -1305,7 +1305,17 @@ def test_startup_backfill_preserves_filestate_content_and_revision_parity(tmp_pa
     ensure_repository_identity(repo)
     monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
     cache = repo_cache_dir(repo)
-    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
+    state = RepositoryAnalysisState(
+        modules={"a.py": SimpleNamespace()},
+        reexport_facts_by_module={
+            "a.py": {
+                "exporter": "a.py",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            }
+        },
+    )
     state.revision = 1
     identity = ensure_repository_identity(repo)[0]
     metadata = save_snapshot(
@@ -1382,7 +1392,17 @@ def test_startup_backfill_failure_leaves_previous_generation_authoritative(tmp_p
     identity = ensure_repository_identity(repo)[0]
     monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
     cache = repo_cache_dir(repo)
-    state = RepositoryAnalysisState(modules={"a.py": SimpleNamespace()})
+    state = RepositoryAnalysisState(
+        modules={"a.py": SimpleNamespace()},
+        reexport_facts_by_module={
+            "a.py": {
+                "exporter": "a.py",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            }
+        },
+    )
     state.revision = 1
     metadata = save_snapshot(state, cache, "sid", repo_id=identity.repo_id, root_path=identity.root_path)
     manager = FileStateManager(str(cache))
diff --git a/tests/test_matrix_clusters_ram_parity.py b/tests/test_matrix_clusters_ram_parity.py
index a66f81c..7fd9f4c 100644
--- a/tests/test_matrix_clusters_ram_parity.py
+++ b/tests/test_matrix_clusters_ram_parity.py
@@ -530,6 +530,12 @@ def test_early_ambiguity_in_recompute_phase_is_sticky_across_clean_later_patch(t
     engine.state.modules["other_consumer"] = Module(
         module_id="other_consumer", path="other.py", absolute_path="/other.py", imports=[]
     )
+    engine.state.reexport_facts_by_module["other_consumer"] = {
+        "exporter": "other_consumer",
+        "explicit_all": None,
+        "bindings": {},
+        "star_sources": [],
+    }
     with engine.registry.transaction():
         engine.registry.sync_with_workspace(
             set(engine.state.modules),
diff --git a/tests/test_no_double_parse.py b/tests/test_no_double_parse.py
index 5194b14..2fb91da 100644
--- a/tests/test_no_double_parse.py
+++ b/tests/test_no_double_parse.py
@@ -14,6 +14,7 @@ from contextor.core.analysis.incremental.preparation import prepare_source_updat
 from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
 from contextor.core.domain.module import Module
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 
 def test_prepare_source_update_reads_one_raw_snapshot_and_parses_once(tmp_path):
@@ -53,7 +54,11 @@ def test_no_double_parse_on_modify(tmp_path):
     f_consumer.write_text("from target import foo, bar\nfoo()\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -105,7 +110,11 @@ def test_no_parse_on_delete(tmp_path):
     f_target.write_text("def foo(): pass\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
diff --git a/tests/test_parity_and_freshness_proof.py b/tests/test_parity_and_freshness_proof.py
index 598e934..113b25f 100644
--- a/tests/test_parity_and_freshness_proof.py
+++ b/tests/test_parity_and_freshness_proof.py
@@ -68,7 +68,11 @@ def test_scenario_b_modify_body_only(tmp_path):
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
     m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target, "consumer": m_consumer})
+    modules = {"target": m_target, "consumer": m_consumer}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -104,7 +108,11 @@ def test_scenario_c_delete_consumer(tmp_path):
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
     m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target, "consumer": m_consumer})
+    modules = {"target": m_target, "consumer": m_consumer}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -130,7 +138,11 @@ def test_scenario_h_inheritance_usage(tmp_path):
     f_child.write_text("from base import BaseWidget\nclass ChildWidget(BaseWidget): pass\n", encoding="utf-8")
 
     m_base = Module(module_id="base", path="base.py", absolute_path=str(f_base), imports=[])
-    state = RepositoryAnalysisState(modules={"base": m_base})
+    modules = {"base": m_base}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -153,7 +165,11 @@ def test_definer_deletion_parity(tmp_path):
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
     m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target, "consumer": m_consumer})
+    modules = {"target": m_target, "consumer": m_consumer}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -180,7 +196,11 @@ def test_copy_on_write_atomicity(tmp_path):
     f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
diff --git a/tests/test_payload_isolation.py b/tests/test_payload_isolation.py
index 60aad10..90bec3a 100644
--- a/tests/test_payload_isolation.py
+++ b/tests/test_payload_isolation.py
@@ -15,6 +15,7 @@ from contextor.core.analysis.state_manager import FileStateManager, RepositoryAn
 from contextor.core.domain.module import Module
 from contextor.core.domain.refresh_plan import RefreshPlan
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 
 def test_shadow_plan_repr_false():
@@ -30,7 +31,11 @@ def test_mcp_update_file_payload_isolation(tmp_path):
     f_target.write_text("def foo(): pass\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
diff --git a/tests/test_persistent_topology_provenance.py b/tests/test_persistent_topology_provenance.py
index 68cb57e..34092bf 100644
--- a/tests/test_persistent_topology_provenance.py
+++ b/tests/test_persistent_topology_provenance.py
@@ -126,6 +126,7 @@ def test_fresh_snapshot_restart_preservation(tmp_path):
 
     state = RepositoryAnalysisState(
         modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
         dependency_graph=graph,
         metrics=metrics,
         topology_analytics=topo,
diff --git a/tests/test_shadow_planning_integration.py b/tests/test_shadow_planning_integration.py
index 381fdc2..17073ef 100644
--- a/tests/test_shadow_planning_integration.py
+++ b/tests/test_shadow_planning_integration.py
@@ -12,6 +12,7 @@ from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
 from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
 from contextor.core.domain.module import Module
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 
 def test_shadow_plan_on_body_modify(tmp_path):
@@ -21,7 +22,11 @@ def test_shadow_plan_on_body_modify(tmp_path):
     f_consumer.write_text("from target import foo, bar\nfoo()\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
@@ -52,7 +57,11 @@ def test_shadow_plan_on_module_delete(tmp_path):
     f_consumer.write_text("from target import foo\nfoo()\n", encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
diff --git a/tests/test_syntax_diagnostics_full_analysis.py b/tests/test_syntax_diagnostics_full_analysis.py
index c399ace..f0b95d4 100644
--- a/tests/test_syntax_diagnostics_full_analysis.py
+++ b/tests/test_syntax_diagnostics_full_analysis.py
@@ -14,6 +14,7 @@ from contextor.core.live_state import load_snapshot, save_snapshot
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.reporting_layer.artifact_usage_report import collect_module_artifacts
 from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 
 def _index(*, modules=(), skipped=()):
@@ -178,6 +179,9 @@ def _live_syntax_fixture(tmp_path, *, family_state="fresh"):
     facts, _ = build_syntax_diagnostics_from_index(index)
     state = RepositoryAnalysisState(
         modules=dict(index.modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            index.modules, index.reference_facts_by_module
+        ),
         artifacts=artifacts,
         dependency_graph=build_graph(index.modules),
         trie=trie,
diff --git a/tests/test_topology_bootstrap_and_consumer_truth.py b/tests/test_topology_bootstrap_and_consumer_truth.py
index 2dea1b4..6fb0a10 100644
--- a/tests/test_topology_bootstrap_and_consumer_truth.py
+++ b/tests/test_topology_bootstrap_and_consumer_truth.py
@@ -24,6 +24,7 @@ from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.graph.metrics import compute_graph_metrics
 from contextor.core.live_state.store import save_snapshot, load_snapshot
 from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.mcp_server import get_module_context
 from contextor.mcp.runtime import _live_engines
@@ -196,6 +197,7 @@ def test_new_snapshot_save_and_restart(tmp_path):
         dependency_graph=graph,
         metrics=metrics,
         topology_analytics=topo,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
     )
 
     save_snapshot(state, cache_dir, "new_snap", repo_id="repo1", root_path=str(tmp_path))
```
