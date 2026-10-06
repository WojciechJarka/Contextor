# CPA_SUITE_REPAIR_A_CANONICAL_REEXPORT_FIXTURE_MIGRATION

STATUS=PARTIAL_BLOCKED_SYNTHETIC_FIXTURES
CLASSIFICATION=PARTIAL_CANONICAL_REEXPORT_TEST_FIXTURE_MIGRATION
HEAD_BEFORE=1525bc9ab51b3a80cc51c8358139cfb23f5b1be6
HEAD_AT_REPORT=1525bc9ab51b3a80cc51c8358139cfb23f5b1be6
WORKTREE_BEFORE=Only walkthrough.md was modified by the prior report; all test/source paths in this task were clean against HEAD.
SOURCE_DRIFT=NONE_OBSERVED. Current Contextor LIVE revision 1551 reported canonical_state=fresh and workspace_sync=verified for relevant owners and test files. Exact current test anchors were inspected before editing and were at HEAD.

## MIGRATION_CONTRACT

Canonical owner: contextor.core.reference.shared::materialize_reexport_facts_by_module and ::validate_reexport_facts_by_module. The validator requires facts and modules to be dicts with exact matching module-key domains and valid fact shapes. save_snapshot and the incremental baseline guard consume this precondition. Production files were not changed.

Contextor evidence:
- get_mcp_documentation was read before using get_file_edit_context, get_artifact_blast_radius, get_symbol_call_context, and get_source_range contracts.
- get_artifact_blast_radius(materialize_reexport_facts_by_module) reported LIVE revision 1551, fresh/verified; direct consumers include contextor.core.api.facade and tests.test_mcp_incremental_hydration.
- Validator blast radius identified direct production consumers contextor.core.analysis.incremental.plan_executor, contextor.core.api.facade, contextor.core.lineage_query.backend, and contextor.core.live_state.store; canonical state freshness was fresh/verified at revision 1551.
- index_repository is owned by contextor.core.symbol_engine.indexer; Contextor reported its source fresh/verified and facade as the production consumer.
- Fresh Contextor call context was checked before modifying reusable helpers: _candidate has 4 test callers; bootstrap_state 18; _setup_engine 11; bootstrap_fresh_state 14; _bootstrap_state 9. These calls are intra-module static call facts at revision 1551, workspace_sync=verified. Affected reusable builders were migrated at their common canonical construction sites.
- contextor_fact_lineage v1 documents only artifact_consumption, syntax_diagnostics, and symbol_calls; it has no reexport-facts family. Re-export ownership was therefore checked with artifact blast radius plus exact source rather than claiming a lineage response for an unsupported family.
- The actual Module.ast_tree property delegates to _get_cached_ast; existing source paths yield the production cached AST. materialize_reexport_facts_by_module uses existing compact facts.reexports where supplied and otherwise that AST. No custom parser/extractor or hand-authored re-export fact was added.

No full analysis, MCP update_file, runtime restart, or full repository pytest suite was run.

## PARTIAL_CANDIDATE_PATCH

Applied exactly the requested _candidate() change in tests/test_incremental_phase_trace.py: added reexport_facts_by_module={} beside modules={} and changed no other content in that helper. The empty map matches the empty module domain.

The three required candidate nodes passed: 3 passed.

## INCREMENTAL_FIXTURE_MIGRATIONS

Migrated only the representative constructors/helper paths named in the prior failure evidence:

- test_channel_parity_all_channels: extracted the one-entry modules map and used the production materializer over its existing source-backed Module.
- test_case_1_add_consumer: extracted its one-entry modules map and used the production materializer over the existing target source.
- bootstrap_state in test_incremental_equivalence.py: reused the already-created repo_index.reference_facts_by_module.
- _setup_engine in test_incremental_local_metrics.py: retained its existing index object and reused its compact reference facts.
- test_new_importing_file_immediately_updates_forward_and_reverse_graph: retained its existing index object and reused its compact reference facts.
- bootstrap_fresh_state in test_live_state_consistency.py: reused the existing index's compact reference facts.
- test_scenario_a_add_consumer: extracted the one-entry modules map and used the production materializer over its existing target source.

Representative incremental gate result: all 7 required nodes pass. The initial invocation had 4 pass and 3 baseline-guard failures; after migrating those three source-backed fixtures, the three failed nodes were rerun and passed. The other four had already passed in that same gate invocation.

## SNAPSHOT_FIXTURE_MIGRATIONS

Migrated these source-backed snapshot constructors with the production materializer:

- test_persisted_fresh_cycles_preserved_across_restart: existing app.a and app.b files.
- test_stale_non_empty_snapshot_restart_and_consumer_guard: existing app.core, app.utils, and app.main files.
- test_materialized_empty_symbol_calls_survive_snapshot_without_rebuild: existing empty.py file.

Migrated tests/test_live_watcher_startup_reconciliation.py::_bootstrap_state by retaining its existing repo_index and passing repo_index.reference_facts_by_module to the materializer. The required startup node test_startup_reconciles_offline_add_modify_delete_and_is_idempotent passed its save_snapshot precondition and test assertions.

One required snapshot representative remains blocked: test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild. It uses a synthetic Module whose path does not exist and supplies no compact re-export envelope. The exact evidence is in BLOCKED_SYNTHETIC_FIXTURES.

## SOURCE_BACKED_MATERIALIZATION

Six directly constructed source-backed maps were passed to materialize_reexport_facts_by_module(modules). Five index-backed fixture paths reused the already available compact reference_facts_by_module. No manual empty facts were assigned to a non-empty source-backed state; the only literal empty re-export map is the requested test double with modules={}.

## COMPACT_FACT_REUSE

- tests/test_incremental_equivalence.py::bootstrap_state
- tests/test_incremental_local_metrics.py::_setup_engine
- tests/test_incremental_reverse_context.py::test_new_importing_file_immediately_updates_forward_and_reverse_graph
- tests/test_live_state_consistency.py::bootstrap_fresh_state
- tests/test_live_watcher_startup_reconciliation.py::_bootstrap_state

Each path passes the index object's existing reference_facts_by_module into the canonical materializer; no second index build or source/AST extraction was added for those fixtures.

## BLOCKED_SYNTHETIC_FIXTURES

BLOCKED_SYNTHETIC_REEXPORT_FIXTURE=1 observed in the required representative gates
FULL_PATH=tests/test_lineage_state_lifecycle.py
TEST_NODE=tests/test_lineage_state_lifecycle.py::test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild
MODULE_ID=pkg
MODULE_VALUE=Module(module_id="pkg", path="pkg.py", absolute_path="C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-84\test_real_hydration_normalizes0\repo\does-not-exist.py", imports=[])
ABSOLUTE_PATH=C:\Users\DafoO\AppData\Local\Temp\pytest-of-DafoO\pytest-84\test_real_hydration_normalizes0\repo\does-not-exist.py
ARTIFACT_SHAPE=RepositoryAnalysisState.modules has only key "pkg"; artifacts defaults empty; reexport_facts_by_module defaults {}; no compact reference envelope is supplied. module_usages contains symbol-call facts, which are a separate family.
WHY_MATERIALIZER_CANNOT_BE_USED=Module.ast_tree calls _get_cached_ast; Path.stat fails for this absent file and returns None. With no compact facts, the production materializer cannot produce a canonical fact and raises. No semantics were invented and the fixture was not changed.

The exact total number of synthetic blockers across all 103 baseline nodes is UNKNOWN because the supplied full-suite discovery contains aggregate failure counts but no per-node list. The one blocker above is directly observed in this step.

## REPRESENTATIVE_INCREMENTAL_GATES

Required command used one physical PowerShell line:
& .\.venv\Scripts\python.exe -m pytest tests/test_channel_parity_and_cow.py::test_channel_parity_all_channels tests/test_incremental_artifact_consumption.py::test_case_1_add_consumer tests/test_incremental_equivalence.py::test_incremental_add_imported_module tests/test_incremental_local_metrics.py::test_stage2c_add_isolated_module_macro_metrics tests/test_incremental_reverse_context.py::test_new_importing_file_immediately_updates_forward_and_reverse_graph tests/test_live_state_consistency.py::test_import_mutation tests/test_parity_and_freshness_proof.py::test_scenario_a_add_consumer

Final per-node status after allowed fixture migrations:
- test_channel_parity_all_channels PASS
- test_case_1_add_consumer PASS
- test_incremental_add_imported_module PASS
- test_stage2c_add_isolated_module_macro_metrics PASS
- test_new_importing_file_immediately_updates_forward_and_reverse_graph PASS
- test_import_mutation PASS
- test_scenario_a_add_consumer PASS

Initial execution of the exact seven-node gate yielded 4 passed and 3 failures at the unchanged canonical baseline guard. The three source-backed direct fixtures were migrated with the existing materializer and rerun; all three passed. Final representative gate: 7/7 passed.

## REPRESENTATIVE_SNAPSHOT_GATES

Required snapshot nodes plus one _bootstrap_state startup node were invoked together on one physical PowerShell line.

Final per-node status:
- test_persisted_fresh_cycles_preserved_across_restart PASS after source-backed materialization.
- test_real_hydration_normalizes_legacy_lineage_absence_without_source_rebuild BLOCKED at the expected save_snapshot guard for the missing-source synthetic fixture above.
- test_stale_non_empty_snapshot_restart_and_consumer_guard PASS after source-backed materialization.
- test_materialized_empty_symbol_calls_survive_snapshot_without_rebuild PASS after source-backed materialization.
- test_startup_reconciles_offline_add_modify_delete_and_is_idempotent PASS; canonical save precondition passed.

The first five-node run yielded one pass and four precondition failures. Three source-backed constructors were migrated and their nodes rerun in the focused six-node retry; all three passed. The missing-source lineage node remains blocked. No production code or test assertion was changed.

## CLUSTER_WIDE_TARGETED_REGRESSION

NOT RUN. The required snapshot representative gate is not fully passable because the lineage fixture is explicitly blocked by the no-source/no-compact-facts contract. The task requires stopping at that fixture rather than designing a new fact source. Therefore the conditional cluster-wide regression for every changed test file was not entered. No tests/ directory positional argument and no full suite were used.

## EXPECTED_OUT_OF_SCOPE_FAILURES

The six STEP B nodes remain untouched and were not rerun:
- tests/test_incremental_plan_executor_complexity.py::test_indexed_rebuild_uses_precomputed_indexes_without_full_scan
- tests/test_completeness_freshness_parity_proof.py::test_ambiguity_regression_real_backfill_path
- tests/test_matrix_clusters_ram_parity.py::test_ambiguity_execution_semantic_regression_fails_closed
- tests/test_live_state_store.py::test_split_snapshot_load_emits_non_overlapping_phase_timings
- tests/test_reference_fusion_integration.py::test_compact_reexport_oracle_and_artifact_output_parity
- tests/test_refresh_plan_execution.py::test_case_a_body_only_retarget

## UNEXPECTED_FAILURES

UNEXPECTED_NEW_FAILURES=0. Every observed failure in representative gates was the exact canonical re-export baseline/save precondition, and each was either repaired using the authorized materializer or classified as the single observed synthetic blocker. The other six known suite signatures remain outside this task.

## CERTIFICATION

PARTIAL_CANDIDATE_MIGRATION=PASS
INCREMENTAL_REEXPORT_BASELINE_FIXTURES_MIGRATED=PARTIAL (all 7 representative gates pass; exact 71-node membership was not supplied)
SNAPSHOT_REEXPORT_BASELINE_FIXTURES_MIGRATED=PARTIAL_BLOCKED_SYNTHETIC_FIXTURES (4 source-backed representative gates pass; 1 is blocked)
PRODUCTION_GUARD_CHANGED=NO
PRODUCTION_FILES_CHANGED=NONE
MANUAL_EMPTY_FACTS_FOR_SOURCE_BACKED_MODULES=ZERO
SOURCE_BACKED_FIXTURES_USE_CANONICAL_MATERIALIZER=YES
SCOPE=all source-backed fixtures changed in this task; full-cluster membership remains unavailable
KNOWN_103_FAILURE_CLUSTER_REPAIRED=PARTIAL
BLOCKED_SYNTHETIC_REEXPORT_FIXTURES=1 observed; total cluster count UNKNOWN
UNEXPECTED_NEW_FAILURES=0

Full cluster certification remains partial: the supplied discovery did not contain exact membership for the 71/29 aggregate failures, and the required snapshot sample exposed the one explicitly unrepairable synthetic fixture.

## FILES_CHANGED

- tests/test_channel_parity_and_cow.py
- tests/test_cycles_live_lifecycle.py
- tests/test_incremental_artifact_consumption.py
- tests/test_incremental_equivalence.py
- tests/test_incremental_local_metrics.py
- tests/test_incremental_phase_trace.py
- tests/test_incremental_reverse_context.py
- tests/test_live_state_consistency.py
- tests/test_live_watcher_startup_reconciliation.py
- tests/test_parity_and_freshness_proof.py
- tests/test_persistent_topology_provenance.py
- tests/test_symbol_call_facts.py

walkthrough.md is the report file and is excluded from FILES_CHANGED.
## FULL_DIFFS

diff --git a/tests/test_channel_parity_and_cow.py b/tests/test_channel_parity_and_cow.py
index 2ca32ed..cb4cafe 100644
--- a/tests/test_channel_parity_and_cow.py
+++ b/tests/test_channel_parity_and_cow.py
@@ -11,6 +11,7 @@ import pytest
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
 from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
 from contextor.core.domain.module import Module
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 
 
@@ -52,7 +53,11 @@ class ChildClass(BaseClass):
 """, encoding="utf-8")
 
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
diff --git a/tests/test_cycles_live_lifecycle.py b/tests/test_cycles_live_lifecycle.py
index 6765a01..1b927b3 100644
--- a/tests/test_cycles_live_lifecycle.py
+++ b/tests/test_cycles_live_lifecycle.py
@@ -25,6 +25,7 @@ from contextor.core.domain.imports import ImportRef
 from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.graph.cycles import detect_cycles
 from contextor.core.live_state.store import save_snapshot, load_snapshot
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 
 
@@ -222,6 +223,7 @@ def test_persisted_fresh_cycles_preserved_across_restart(tmp_path):
 
     state = RepositoryAnalysisState(
         modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
         dependency_graph=graph,
         cycles=cycles_expected,
         cycles_state="fresh",
diff --git a/tests/test_incremental_artifact_consumption.py b/tests/test_incremental_artifact_consumption.py
index 4e1b761..5fee154 100644
--- a/tests/test_incremental_artifact_consumption.py
+++ b/tests/test_incremental_artifact_consumption.py
@@ -17,6 +17,7 @@ from contextor.core.domain.graph import ProjectGraph
 from contextor.core.domain.module import Module
 from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.reference.engine import extract_module_usage_facts
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 from contextor.core.reference.engine import _build_reexport_map
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
@@ -61,8 +62,10 @@ def test_case_1_add_consumer(tmp_path):
     imp_c = ImportRef(module="target", level=0, names=["foo"], is_from_import=True)
     m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[imp_c])
 
+    modules = {"target": m_target}
     state = RepositoryAnalysisState(
-        modules={"target": m_target},
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
         artifacts={"target": {"symbols": {"functions": ["foo"]}, "own_symbols": ["foo"]}},
     )
     cache_dir = tmp_path / "cache"
diff --git a/tests/test_incremental_equivalence.py b/tests/test_incremental_equivalence.py
index cf90f27..ec6cf3c 100644
--- a/tests/test_incremental_equivalence.py
+++ b/tests/test_incremental_equivalence.py
@@ -7,6 +7,7 @@ from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.core.symbol_engine.indexer import index_repository
 from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 pytestmark = pytest.mark.live
 
@@ -30,6 +31,9 @@ def bootstrap_state(root_path: Path, registry: PersistentIdentityRegistry) -> Re
     
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=module_artifacts,
         dependency_graph=graph,
         trie=trie,
diff --git a/tests/test_incremental_local_metrics.py b/tests/test_incremental_local_metrics.py
index 5782218..d90ea96 100644
--- a/tests/test_incremental_local_metrics.py
+++ b/tests/test_incremental_local_metrics.py
@@ -21,6 +21,7 @@ from contextor.core.reporting_layer.artifact_usage_report import (
     collect_qualified_artifact_identities,
 )
 from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor import mcp_server
 from contextor.mcp import runtime as mcp_runtime
 
@@ -357,7 +358,8 @@ def _setup_engine(tmp_path):
     target = tmp_path / "target.py"
     target.write_text("def target_fn():\n    return 2\n", encoding="utf-8")
 
-    modules = index_repository(str(tmp_path)).modules
+    repo_index = index_repository(str(tmp_path))
+    modules = repo_index.modules
     artifacts, _ = collect_module_artifacts(modules, str(tmp_path))
     trie = build_trie(modules)
     package_root = detect_package_root(modules, trie)
@@ -367,6 +369,9 @@ def _setup_engine(tmp_path):
 
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=artifacts,
         dependency_graph=graph,
         trie=trie,
diff --git a/tests/test_incremental_phase_trace.py b/tests/test_incremental_phase_trace.py
index 87a6eb0..48071f3 100644
--- a/tests/test_incremental_phase_trace.py
+++ b/tests/test_incremental_phase_trace.py
@@ -41,7 +41,8 @@ class FakeStateManager:
 
 def _candidate():
     return SimpleNamespace(
-        modules={}, artifacts={}, module_parse_freshness={},
+        modules={}, reexport_facts_by_module={},
+        artifacts={}, module_parse_freshness={},
         syntax_diagnostics_by_path={}, syntax_diagnostics_state="fresh",
         dependency_graph=None, metrics={}, topology_analytics={},
         cached_analytics={}, dependency_matrix={}, dependency_matrix_state="deferred",
diff --git a/tests/test_incremental_reverse_context.py b/tests/test_incremental_reverse_context.py
index be1fc2a..d8567b1 100644
--- a/tests/test_incremental_reverse_context.py
+++ b/tests/test_incremental_reverse_context.py
@@ -12,6 +12,7 @@ from contextor.core.reporting_layer.artifact_usage_report import (
 )
 from contextor.core.domain.graph import ProjectGraph
 from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 pytestmark = pytest.mark.live
 
@@ -19,13 +20,17 @@ pytestmark = pytest.mark.live
 def test_new_importing_file_immediately_updates_forward_and_reverse_graph(tmp_path):
     provider = tmp_path / "provider.py"
     provider.write_text("def run():\n    return 1\n", encoding="utf-8")
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
diff --git a/tests/test_live_state_consistency.py b/tests/test_live_state_consistency.py
index 1146dc8..f3a6b64 100644
--- a/tests/test_live_state_consistency.py
+++ b/tests/test_live_state_consistency.py
@@ -13,6 +13,7 @@ from contextor.core.reporting_engine.persistent_registry import PersistentIdenti
 from contextor.core.symbol_engine.indexer import index_repository
 from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
 from contextor.core.reporting_layer.artifact_usage_report import collect_module_artifacts, build_artifact_index
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 
 pytestmark = pytest.mark.live
 
@@ -38,6 +39,9 @@ def bootstrap_fresh_state(root_path: Path) -> RepositoryAnalysisState:
     
     return RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=module_artifacts,
         dependency_graph=graph,
         trie=trie,
diff --git a/tests/test_live_watcher_startup_reconciliation.py b/tests/test_live_watcher_startup_reconciliation.py
index a209aaa..35d44fd 100644
--- a/tests/test_live_watcher_startup_reconciliation.py
+++ b/tests/test_live_watcher_startup_reconciliation.py
@@ -12,6 +12,7 @@ from contextor.core.analysis.state_manager import (
     RepositoryAnalysisState,
 )
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.api.facade import exclude_state_file
 from contextor.core.graph.graph import build_graph, build_trie, detect_package_root
 from contextor.core.live_state.ipc import CanonicalLiveServer, LiveStateClient
@@ -119,11 +120,15 @@ def _real_watcher_runtime(tmp_path, updater):
 
 def _bootstrap_state(repo):
     registry = PersistentIdentityRegistry(str(repo))
-    modules = index_repository(str(repo)).modules
+    repo_index = index_repository(str(repo))
+    modules = repo_index.modules
     artifacts, _ = collect_module_artifacts(modules, str(repo))
     trie = build_trie(modules)
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=materialize_reexport_facts_by_module(
+            modules, repo_index.reference_facts_by_module
+        ),
         artifacts=artifacts,
         dependency_graph=build_graph(modules),
         trie=trie,
diff --git a/tests/test_parity_and_freshness_proof.py b/tests/test_parity_and_freshness_proof.py
index 08d3e0c..598e934 100644
--- a/tests/test_parity_and_freshness_proof.py
+++ b/tests/test_parity_and_freshness_proof.py
@@ -14,6 +14,7 @@ from contextor.core.analysis.state_manager import FileStateManager, RepositoryAn
 from contextor.core.domain.imports import ImportRef
 from contextor.core.domain.module import Module
 from contextor.core.reference.engine import extract_module_usage_facts
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 
 
@@ -38,7 +39,11 @@ def test_scenario_a_add_consumer(tmp_path):
     m_target = Module(module_id="target", path="target.py", absolute_path=str(f_target), imports=[])
     m_consumer = Module(module_id="consumer", path="consumer.py", absolute_path=str(f_consumer), imports=[])
 
-    state = RepositoryAnalysisState(modules={"target": m_target})
+    modules = {"target": m_target}
+    state = RepositoryAnalysisState(
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
+    )
     cache_dir = tmp_path / "cache"
     cache_dir.mkdir()
 
diff --git a/tests/test_persistent_topology_provenance.py b/tests/test_persistent_topology_provenance.py
index ef6033e..68cb57e 100644
--- a/tests/test_persistent_topology_provenance.py
+++ b/tests/test_persistent_topology_provenance.py
@@ -26,6 +26,7 @@ from contextor.core.domain.imports import ImportRef
 from contextor.core.graph.metrics import compute_graph_metrics
 from contextor.core.live_state.store import save_snapshot, load_snapshot
 from contextor.core.reporting_engine.graph_analytics import compute_topology_analytics
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 from contextor.mcp_server import get_module_context
 from contextor.mcp.runtime import _live_engines
@@ -71,6 +72,7 @@ def test_stale_non_empty_snapshot_restart_and_consumer_guard(tmp_path):
     # State has non-empty topology analytics, but is explicitly marked STALE
     state = RepositoryAnalysisState(
         modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
         dependency_graph=graph,
         metrics=metrics,
         topology_analytics=topo,
diff --git a/tests/test_symbol_call_facts.py b/tests/test_symbol_call_facts.py
index 7f5aeff..6e579ca 100644
--- a/tests/test_symbol_call_facts.py
+++ b/tests/test_symbol_call_facts.py
@@ -21,6 +21,7 @@ from contextor.core.domain import usage_facts as usage_facts_module
 from contextor.core.live_state import store as live_store
 from contextor.core.live_state.store import load_snapshot, save_snapshot
 from contextor.core.reference.engine import extract_module_usage_facts
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.reference.visitor import SymbolReferenceVisitor
 from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 
@@ -415,8 +416,10 @@ def test_legacy_existing_usage_is_backfilled_once_and_unrelated_is_preserved(tmp
 def test_materialized_empty_symbol_calls_survive_snapshot_without_rebuild(tmp_path):
     source = tmp_path / "empty.py"
     source.write_text("def empty():\n    pass\n", encoding="utf-8")
+    modules = {"empty": Module("empty", "empty.py", str(source), [])}
     state = RepositoryAnalysisState(
-        modules={"empty": Module("empty", "empty.py", str(source), [])},
+        modules=modules,
+        reexport_facts_by_module=materialize_reexport_facts_by_module(modules),
         module_usages={
             "empty": extract_module_usage_facts("empty", "def empty():\n    pass\n")
         },

