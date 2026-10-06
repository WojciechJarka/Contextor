# CPA_SUITE_REPAIR_A3_SYNTHETIC_CANONICAL_REEXPORT_FIXTURES

STATUS=STEP_PASS
CLASSIFICATION=CANONICAL_REEXPORT_TEST_FIXTURE_MIGRATION_CERTIFIED
HEAD_BEFORE=d73cf09c1f59664c2c886978fab33d340b6b9934
HEAD_AT_REPORT=d73cf09c1f59664c2c886978fab33d340b6b9934
WORKTREE_BASELINE=CLEAN_AT_A3_START
SOURCE_DRIFT=NONE; all requested literal anchors matched before editing

CONTEXTOR_DISCOVERY
- Before edits, Contextor get_file_edit_context covered collisions, H2C, lineage lifecycle, and the matrix test file at canonical revision 1584; canonical_state=fresh, workspace_sync=verified, no syntax diagnostics.
- get_symbol_call_context confirmed 8 direct callers of _lineage_state_for_facts, including the requested lineage tests; 6 callers of _cross_source_facts, including both cross-source snapshot tests; and 14 callers of _lineage_slice, including the symbolic hydration test.
- Literal source/HEAD check followed Contextor discovery. HEAD was d73cf09c1f59664c2c886978fab33d340b6b9934 and the worktree was clean before A3 edits.
- No MCP update_file, production edit, runtime restart, or full repository analysis was used.

COLLISION_SYNTHETIC_FACTS
- test_plan_executor_missing_payload_fail_closed: added exactly a.X and b.X bindings alongside the represented X = 1 collision facts.
- test_missing_payload_transaction_failure: added exactly a.X alongside the represented X = 1 collision fact.
- Collision facts and expected failures were unchanged.

H2C_SYNTHETIC_FACT
- test_e2e_missing_source_fails_closed_no_blank_code_collision: retained mod_a's missing source and supplied its literal missing_partner -> mod_a.missing_partner fact; materialized only mod_b from its real source.
- The state now uses the explicit modules mapping and execute_refresh_plan receives prep.new_reexport_facts, matching the neighboring H2C fixtures.

LINEAGE_CROSS_SOURCE_FACTS
- Added _cross_source_reexport_facts() with only provider.target, consumer.exported -> provider.target, and consumer.value -> consumer.value.
- Applied it only to the round-trip test and all five explicit corrupt-origin parameter cases.

LINEAGE_INTERFACE_FACT
- Added exactly pkg.ping -> pkg.ping to the legacy interface descriptor snapshot fixture.

LINEAGE_SYMBOLIC_FACT
- Added exactly pkg.thing -> pkg.thing to the fresh-process symbolic-lineage fixture.
- No missing.py was created; lineage slice and subprocess proof were unchanged.

EXACT_11_RESULTS=PASS; 11 passed in 4.09s
EXACT_11_NODE_IDS
- tests/test_collisions_live_lifecycle.py::test_plan_executor_missing_payload_fail_closed
- tests/test_collisions_live_lifecycle.py::test_missing_payload_transaction_failure
- tests/test_h2c_collision_equivalence.py::test_e2e_missing_source_fails_closed_no_blank_code_collision
- tests/test_lineage_state_lifecycle.py::test_snapshot_round_trip_compact_origin_reresolves_without_source_work
- tests/test_lineage_state_lifecycle.py::test_snapshot_rejects_corrupt_compact_origin[<lambda>0]
- tests/test_lineage_state_lifecycle.py::test_snapshot_rejects_corrupt_compact_origin[<lambda>1]
- tests/test_lineage_state_lifecycle.py::test_snapshot_rejects_corrupt_compact_origin[<lambda>2]
- tests/test_lineage_state_lifecycle.py::test_snapshot_rejects_corrupt_compact_origin[<lambda>3]
- tests/test_lineage_state_lifecycle.py::test_snapshot_rejects_corrupt_compact_origin[<lambda>4]
- tests/test_lineage_state_lifecycle.py::test_snapshot_legacy_interface_descriptor_capability_fails_closed_without_dropping_payload
- tests/test_lineage_state_lifecycle.py::test_fresh_process_hydrates_materialized_symbolic_lineage_without_analysis

EXACT_103_RESULTS=102 PASS; 1 expected semantic failure; all 103 original identities were run in per-file batches using explicit parameter IDs.
PER_FILE_RESULTS
- tests/test_channel_parity_and_cow.py: 4 passed
- tests/test_collisions_live_lifecycle.py: 4 passed
- tests/test_cycles_live_lifecycle.py: 1 passed
- tests/test_graph_only_live_analytics.py: 1 passed
- tests/test_h2c_collision_equivalence.py: 3 passed
- tests/test_incremental_artifact_consumption.py: 7 passed
- tests/test_incremental_equivalence.py: 11 passed
- tests/test_incremental_local_metrics.py: 11 passed
- tests/test_incremental_phase_trace.py: 3 passed
- tests/test_incremental_reverse_context.py: 7 passed
- tests/test_lineage_state_lifecycle.py: 9 passed
- tests/test_live_e2e_corrections.py: 3 passed
- tests/test_live_state_consistency.py: 9 passed
- tests/test_live_state_ipc.py: 2 passed
- tests/test_live_watcher_startup_reconciliation.py: 10 passed
- tests/test_matrix_clusters_ram_parity.py: 0 passed; 1 failed at the reclassified legacy expectation
- tests/test_no_double_parse.py: 2 passed
- tests/test_parity_and_freshness_proof.py: 6 passed
- tests/test_payload_isolation.py: 1 passed
- tests/test_persistent_topology_provenance.py: 2 passed
- tests/test_shadow_planning_integration.py: 2 passed
- tests/test_symbol_call_facts.py: 1 passed
- tests/test_syntax_diagnostics_full_analysis.py: 2 passed
- tests/test_topology_bootstrap_and_consumer_truth.py: 1 passed

CANONICAL_GUARD_FAILURES_REMAINING=0
DIRECT_EVIDENCE=All 102 passing identities completed without either canonical re-export baseline/persistence guard message. The single remaining failure reached the unchanged semantic assertion and reported expected 'stale', actual 'fresh'.
RECLASSIFIED_STEP_B_NODE=tests/test_matrix_clusters_ram_parity.py::test_early_ambiguity_in_recompute_phase_is_sticky_across_clean_later_patch; unchanged; failure at tests/test_matrix_clusters_ram_parity.py:570 is expected stale / actual fresh.
STEP_B_NODE_COUNT=7
PRODUCTION_FILES_CHANGED=NONE
CHANGED_FILE_REGRESSION=NOT_RUN; the prior A2 condition required 103/103 PASS, which is not met; A3's explicit acceptance criterion is 102 PASS plus this known Step B expectation failure.
FULL_SUITE=NOT_RUN

CERTIFICATION
STATUS=STEP_PASS
CLASSIFICATION=CANONICAL_REEXPORT_TEST_FIXTURE_MIGRATION_CERTIFIED
CONTRACT=all 11 baseline blockers now pass; original 103 results are 102 PASS plus only the specified reclassified Step B expectation failure; no production changes.

FILES_CHANGED_CURRENT_A3
- tests/test_collisions_live_lifecycle.py
- tests/test_h2c_collision_equivalence.py
- tests/test_lineage_state_lifecycle.py

FULL_DIFFS_CURRENT_A3

```diff
diff --git a/tests/test_collisions_live_lifecycle.py b/tests/test_collisions_live_lifecycle.py
index cc19e56..990d048 100644
--- a/tests/test_collisions_live_lifecycle.py
+++ b/tests/test_collisions_live_lifecycle.py
@@ -335,6 +335,24 @@ def test_plan_executor_missing_payload_fail_closed():
             "a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[]),
             "b": Module(module_id="b", path="b.py", absolute_path="/tmp/b.py", imports=[]),
         },
+        reexport_facts_by_module={
+            "a": {
+                "exporter": "a",
+                "explicit_all": None,
+                "bindings": {
+                    "X": "a.X",
+                },
+                "star_sources": [],
+            },
+            "b": {
+                "exporter": "b",
+                "explicit_all": None,
+                "bindings": {
+                    "X": "b.X",
+                },
+                "star_sources": [],
+            },
+        },
         collision_facts={
             "a": [{"name": "X", "type": "variable", "file": "a", "file_path": "/tmp/a.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}],
             "b": [{"name": "X", "type": "variable", "file": "b", "file_path": "/tmp/b.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}],
@@ -509,6 +527,16 @@ def test_missing_payload_transaction_failure():
         modules={
             "a": Module(module_id="a", path="a.py", absolute_path="/tmp/a.py", imports=[]),
         },
+        reexport_facts_by_module={
+            "a": {
+                "exporter": "a",
+                "explicit_all": None,
+                "bindings": {
+                    "X": "a.X",
+                },
+                "star_sources": [],
+            },
+        },
         collision_facts={
             "a": [{"name": "X", "type": "variable", "file": "a", "file_path": "/tmp/a.py", "code": "X = 1", "line_start": 1, "line_end": 1, "col_start": 0, "col_end": 5}],
         },
diff --git a/tests/test_h2c_collision_equivalence.py b/tests/test_h2c_collision_equivalence.py
index c258e08..905736b 100644
--- a/tests/test_h2c_collision_equivalence.py
+++ b/tests/test_h2c_collision_equivalence.py
@@ -829,12 +829,31 @@ def test_e2e_missing_source_fails_closed_no_blank_code_collision():
 
         mod_a = Module(module_id="mod_a", path="mod_a_deleted.py", absolute_path=str(path_a_nonexistent), imports=[])
         mod_b = Module(module_id="mod_b", path="mod_b.py", absolute_path=str(path_b), imports=[])
+        modules = {
+            "mod_a": mod_a,
+            "mod_b": mod_b,
+        }
 
         # A has unmaterialized fact with non-existent file path
         facts_a = [{"name": "missing_partner", "type": "function", "file": "mod_a", "file_path": str(path_a_nonexistent), "code": "", "line_start": 1, "line_end": 2, "col_start": 0, "col_end": 15}]
 
         state = RepositoryAnalysisState(
-            modules={"mod_a": mod_a, "mod_b": mod_b},
+            modules=modules,
+            reexport_facts_by_module={
+                "mod_a": {
+                    "exporter": "mod_a",
+                    "explicit_all": None,
+                    "bindings": {
+                        "missing_partner": "mod_a.missing_partner",
+                    },
+                    "star_sources": [],
+                },
+                **materialize_reexport_facts_by_module(
+                    {
+                        "mod_b": mod_b,
+                    }
+                ),
+            },
             collision_facts={"mod_a": facts_a, "mod_b": []},
             collisions_state="fresh",
             collisions=[],
@@ -868,6 +887,7 @@ def test_e2e_missing_source_fails_closed_no_blank_code_collision():
             root_path=str(root),
             file_path=str(path_b),
             new_collision_facts=prep.new_collision_facts,
+            new_reexport_facts=prep.new_reexport_facts,
         )
 
         candidate = outcome.candidate_state
diff --git a/tests/test_lineage_state_lifecycle.py b/tests/test_lineage_state_lifecycle.py
index 209b53c..33e8500 100644
--- a/tests/test_lineage_state_lifecycle.py
+++ b/tests/test_lineage_state_lifecycle.py
@@ -631,6 +631,28 @@ def _cross_source_facts():
     }
 
 
+def _cross_source_reexport_facts():
+    return {
+        "provider": {
+            "exporter": "provider",
+            "explicit_all": ["target"],
+            "bindings": {
+                "target": "provider.target",
+            },
+            "star_sources": [],
+        },
+        "consumer": {
+            "exporter": "consumer",
+            "explicit_all": ["exported"],
+            "bindings": {
+                "exported": "provider.target",
+                "value": "consumer.value",
+            },
+            "star_sources": [],
+        },
+    }
+
+
 def _lineage_state_for_facts(facts, registry, modules, artifacts):
     index = SimpleNamespace(
         modules=modules,
@@ -724,6 +746,9 @@ def test_snapshot_round_trip_compact_origin_reresolves_without_source_work(tmp_p
         {"provider::target": "A:provider/1"},
     )
     state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    state.reexport_facts_by_module = (
+        _cross_source_reexport_facts()
+    )
     save_snapshot(state, tmp_path, "compact-origin")
     loaded, _ = load_snapshot(tmp_path, expected_state_id="compact-origin")
     consumer = loaded.lineage_facts_by_source["consumer.py"]
@@ -780,6 +805,9 @@ def test_snapshot_rejects_corrupt_compact_origin(tmp_path, origins):
         {"provider::target": "A:provider/1"},
     )
     state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    state.reexport_facts_by_module = (
+        _cross_source_reexport_facts()
+    )
     source_slice = state.lineage_facts_by_source["consumer.py"]
     origin = source_slice.semantic_endpoint_origins[0]
     object.__setattr__(source_slice, "semantic_endpoint_origins", origins(origin))
@@ -1388,6 +1416,16 @@ def test_fresh_process_hydrates_materialized_symbolic_lineage_without_analysis(
     )
     state = RepositoryAnalysisState(
         modules={"pkg": Module(module_id="pkg", path="pkg.py", absolute_path=str(repo / "missing.py"), imports=[])},
+        reexport_facts_by_module={
+            "pkg": {
+                "exporter": "pkg",
+                "explicit_all": None,
+                "bindings": {
+                    "thing": "pkg.thing",
+                },
+                "star_sources": [],
+            },
+        },
         dependency_graph=ProjectGraph(hard_edges={"pkg": set()}, soft_edges={"pkg": set()}),
         lineage_facts_by_source={"pkg.py": source},
         lineage_facts_state="fresh",
@@ -1461,6 +1499,16 @@ def test_snapshot_legacy_interface_descriptor_capability_fails_closed_without_dr
         {"pkg": "M:pkg/1"}, {"pkg::ping": "A:pkg.ping/1"}
     )
     state = _lineage_state_for_facts(facts, registry, modules, artifacts)
+    state.reexport_facts_by_module = {
+        "pkg": {
+            "exporter": "pkg",
+            "explicit_all": None,
+            "bindings": {
+                "ping": "pkg.ping",
+            },
+            "star_sources": [],
+        },
+    }
     source_slice = state.lineage_facts_by_source["pkg.py"]
     assert source_slice.manifest.interface_descriptors_materialized is True
     assert source_slice.interface_descriptors
```

