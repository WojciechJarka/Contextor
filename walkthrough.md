# CPA_FILE_UPDATE_CANONICAL_REEXPORT_FACTS_END_TO_END

STATUS=FAIL
CLASSIFICATION=CANONICAL_PARITY_GATE_FAILED
HEAD_BEFORE=434ee8defe538977c55dc29135d2d9d948bc9642
HEAD_AT_REPORT=434ee8defe538977c55dc29135d2d9d948bc9642
ACCEPTED_PREEXISTING_WORKTREE=CLEAN_AT_START; HEAD_BEFORE had no tracked or untracked changes.
SOURCE_DRIFT=NONE; Contextor LIVE revision 1492 reported fresh/verified target-file context for shared.py, state_manager.py, facade.py, preparation.py, refresh_planner.py, plan_executor.py, engine.py, and the parity proof test; Git HEAD and exact anchors were checked before edits.

CANONICAL_REEXPORT_CONTRACT=PARTIALLY_IMPLEMENTED; canonical slice validator/materializer, RepositoryAnalysisState field, full-analysis installation, per-file extraction, planner family, RAM-only candidate executor, engine commit, and snapshot gates are present in the current uncommitted diff. Completion is not certified because the required full-parity gates failed.
CANONICAL_OWNER=RepositoryAnalysisState.reexport_facts_by_module; full-analysis producer/materializer is ContextorFacade.analyze_project using RepositoryIndex.reference_facts_by_module; incremental producer is prepare_source_update; executor assembles from candidate re-export slices; store enforces save/load completeness.
FULL_ANALYSIS_MATERIALIZATION=PASS for the new all-only fixture baseline: analyze_project returned no errors, hydration succeeded, and canonical re-export fact keys equalled module keys. Fresh full oracle was also materialized after incremental update.
DOMAIN_COVERAGE=PASS for the baseline and the named incremental add/change/delete gate.
SINGLE_FILE_EXTRACTION=PASS for the all-only update; the per-file re-export slice changed with only b.py changed.
REEXPORT_DELTA=PASS in the all-only gate; the plan included reexport_facts.
PLANNER_CONTRACT=PASS for the all-only gate; downstream consumer c was present in the execution recompute trace.
RAM_ONLY_EXECUTOR=PASS for the all-only update up to the subsequent parity assertion; one RAM assembler call received a complete dictionary domain, and the Module.ast_tree/_get_cached_ast guards observed no access.
SOURCE_IO_PROOF=The changed-file update completed while Module.ast_tree and _get_cached_ast were guarded to raise; the assembler spy received only canonical fact dictionaries. This proves zero AST-backed source access for incremental re-export map construction; the ordinary changed-file parse and file-state acknowledgement remain part of update_file.
INCREMENTAL_BUILD_REEXPORT_SOURCE_IO=ZERO
UNCHANGED_MODULE_AST_ACCESSES=ZERO
REEXPORT_FACT_DOMAIN_EQUALS_MODULE_DOMAIN=PASS
FULL_REEXPORT_PARITY=FAIL; the all-only fixture's reexport_facts equality assertion passed, but the required shared full-parity helper then failed in artifact_consumption. Other named full-parity gates also found artifact-consumption canonical mismatches.
FULL_PARITY_RESULTS=FAIL; exact captured mismatches are listed under DIRECT_EVIDENCE and TEST_RESULTS.
ADD_CHANGE_DELETE=PASS; test_reexport_canonical_domain_tracks_add_change_delete passed, including slice replacement and removal.
PARSE_FAILURE_LKG=PASS; test_reexport_facts_preserve_last_known_good_on_parse_failure passed.
SNAPSHOT_SCHEMA=PASS; current schema test and new persistence tests passed; read_metadata now accepts historical 1.3 in addition to 1.0, 1.1, 1.2, and current 1.4.
OLD_SNAPSHOT_REJECTION=PASS; a legacy RepositoryAnalysisState pickle without an instance reexport_facts_by_module field was rejected by load_snapshot.
OLD_CANONICAL_SNAPSHOT_WITHOUT_REEXPORT_FACTS=REJECTED
CURRENT_SNAPSHOT_ROUNDTRIP=PASS; nonempty current facts round-tripped under schema 1.4; incomplete RepositoryAnalysisState save was rejected.
CURRENT_SCHEMA=1.4
HYDRATION_ROUNDTRIP=INCOMPLETE; the named test updated and persisted successfully and get_or_init_engine returned a non-None IncrementalAnalysisEngine. The added assertion then failed with AttributeError because it accessed hydrated.engine.state; the returned object has no engine attribute, so the facts coverage assertion did not execute. No test change was made after the parity gate failure.
MCP_RESTART_REQUIRED=YES; production runtime/store code changed. No Desktop/MCP/backend restart was performed.
FULL_ANALYSIS_REQUIRED_AFTER_RESTART=YES

DIRECT_EVIDENCE:
- Contextor fact lineage for artifact_consumption at LIVE revision 1492 confirmed full installation by ContextorFacade.analyze_project, incremental installation by IncrementalAnalysisEngine._apply_delta_and_commit, persistence via save_engine_state/live_snapshot, and hydration via hydrate_repository_engine.
- The all-only regression's source guards and assembler spy completed without triggering either guarded AST access; the spy was called once with a dict covering the candidate module domain.
- The all-only parity helper passed its reexport_facts equality assertion, then failed while comparing artifact_consumption consumers: incremental=[] versus full=['c']; the helper's assertion did not print the target identity, so the exact target is UNKNOWN from this captured evidence.
- test_transitive_reexport_late_provider_matches_full_oracle failed artifact_consumption target-domain parity: incremental keys={'a::foo'}; full keys={'a::VALUE','a::foo','c::run'}.
- test_reexport_retarget_matches_full_oracle failed artifact_consumption target-domain parity: incremental keys={'a::foo','d::replacement'}; full additionally contained 'c::run'.
- test_natural_ambiguity_transition_matches_full_oracle_state had equal displayed target entries but artifact_consumption_state incremental='stale', full='fresh'.
- test_transitive_reexport_symbol_remove_matches_full_oracle failed its existing execution trace assertion: planned recompute_modules=('b',), observed execution_trace recompute_modules=('b','c').
CODE_PATH_PROVED=The current diff wires the shared validator/materializer into full analysis and persistence, and wires per-file facts through preparation, planning, candidate replacement, re-export map assembly, and canonical commit. Static literal search of plan_executor.py found _assemble_reexport_map once and found no _build_reexport_map, Module.ast_tree, or _get_cached_ast reference.
CONTRACT_PROVED=Schema 1.4 roundtrip, invalid-save rejection, legacy canonical snapshot rejection, add/change/delete coverage, and parse-failure LKG focused nodes passed.
INFERENCE=The failed artifact_consumption and ambiguity assertions prevent claiming the requested end-to-end canonical parity. No cause is inferred.
UNKNOWN=The exact artifact_consumption target for the all-only mismatch was not included in pytest's assertion output. Hydration facts were not directly asserted because the test stopped at the erroneous .engine access.

TEST_FILE=tests/test_completeness_freshness_parity_proof.py; tests/test_live_state_store.py; tests/test_mcp_incremental_hydration.py
TEST_NODE_ID=tests/test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle
TARGETED_TESTS:
- tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_late_provider_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_reexport_retarget_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_natural_ambiguity_transition_matches_full_oracle_state
- Requested test_transitive_symbol_remove_matches_full_oracle was absent; exact existing substitution run: tests/test_completeness_freshness_parity_proof.py::test_transitive_reexport_symbol_remove_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_reexport_all_only_change_is_ram_only_and_matches_full_oracle
- tests/test_completeness_freshness_parity_proof.py::test_reexport_canonical_domain_tracks_add_change_delete
- tests/test_completeness_freshness_parity_proof.py::test_reexport_facts_preserve_last_known_good_on_parse_failure
- tests/test_live_state_store.py::test_current_schema_14_splits_lineage_and_roundtrips
- tests/test_live_state_store.py::test_current_schema_reexport_facts_roundtrip
- tests/test_live_state_store.py::test_save_snapshot_rejects_incomplete_canonical_reexport_facts
- tests/test_live_state_store.py::test_legacy_canonical_snapshot_without_reexport_facts_is_rejected
- tests/test_live_state_store.py::test_legacy_dict_snapshot_returns_tuple
- tests/test_live_state_store.py::test_legacy_state_without_manifest_loads_with_empty_manifest
- tests/test_mcp_incremental_hydration.py::test_update_persist_restart_hydrate_keeps_live_reverse_context

TEST_RESULTS:
- FAIL: test_transitive_reexport_late_provider_matches_full_oracle (artifact_consumption target domain mismatch).
- FAIL: test_reexport_retarget_matches_full_oracle (artifact_consumption target domain mismatch).
- FAIL: test_natural_ambiguity_transition_matches_full_oracle_state (artifact_consumption_state stale vs fresh).
- FAIL: test_transitive_reexport_symbol_remove_matches_full_oracle (actual recompute trace ('b','c') vs expected ('b',)).
- FAIL: test_reexport_all_only_change_is_ram_only_and_matches_full_oracle (artifact_consumption consumer mismatch; reexport facts equality passed).
- PASS: test_reexport_canonical_domain_tracks_add_change_delete.
- PASS: test_reexport_facts_preserve_last_known_good_on_parse_failure.
- PASS: test_current_schema_14_splits_lineage_and_roundtrips.
- PASS: test_current_schema_reexport_facts_roundtrip.
- PASS: test_save_snapshot_rejects_incomplete_canonical_reexport_facts.
- PASS: test_legacy_canonical_snapshot_without_reexport_facts_is_rejected.
- PASS: test_legacy_dict_snapshot_returns_tuple.
- PASS: test_legacy_state_without_manifest_loads_with_empty_manifest.
- FAIL: test_update_persist_restart_hydrate_keeps_live_reverse_context (AttributeError at the newly added hydrated.engine.state access after successful update persistence and non-None get_or_init_engine result).
- Aggregate: 8 passed, 6 failed, 1 warning in 24.57s.
- git diff --check: no whitespace errors; Git emitted only working-copy LF-to-CRLF notices.
- Full repository pytest suite was not run.

FILES_CHANGED:
- contextor/core/reference/shared.py
- contextor/core/analysis/state_manager.py
- contextor/core/api/facade.py
- contextor/core/analysis/incremental/preparation.py
- contextor/core/domain/refresh_plan.py
- contextor/core/analysis/refresh_planner.py
- contextor/core/analysis/incremental/plan_executor.py
- contextor/core/analysis/incremental/engine.py
- contextor/core/live_state/store.py
- tests/test_completeness_freshness_parity_proof.py
- tests/test_live_state_store.py
- tests/test_mcp_incremental_hydration.py

NEXT=STOPPED_AT_FULL_PARITY_GATE; production/test changes remain uncommitted. No production/test edits were made after the failed parity results. Wait for the user command 'proceduj'.

## ACTUAL_DIFF / FULL_DIFF

diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 2b3d9bc..1c0a03b 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -520,6 +520,7 @@ class IncrementalAnalysisEngine:
                 affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                     file_path, delta, usage_delta, plan, [], {}, ModuleUsageFacts(),
                     new_collision_facts=None,
+                    new_reexport_facts=None,
                     syntax_source_path=source_path,
                     remove_syntax_fact=True,
                     clear_parse_module=module_path,
@@ -552,6 +553,11 @@ class IncrementalAnalysisEngine:
             old_artifacts = self.state.artifacts.get(module_path, {})
             old_usage = self.state.module_usages.get(module_path, ModuleUsageFacts()) if hasattr(self.state, "module_usages") and self.state.module_usages else ModuleUsageFacts()
             old_collision_facts = self.state.collision_facts.get(module_path) if hasattr(self.state, "collision_facts") and self.state.collision_facts else None
+            old_reexport_facts = (
+                self.state.reexport_facts_by_module.get(
+                    module_path
+                )
+            )
 
             prep = prepare_source_update(
                 file_path=file_path,
@@ -563,6 +569,7 @@ class IncrementalAnalysisEngine:
                 persistent_id=module_id,
                 old_collision_facts=old_collision_facts,
                 source_key=source_path,
+                old_reexport_facts=old_reexport_facts,
             )
 
             if prep.has_error:
@@ -611,6 +618,7 @@ class IncrementalAnalysisEngine:
             new_artifacts = prep.new_artifacts
             new_usage = prep.new_usage
             new_collision_facts = prep.new_collision_facts
+            new_reexport_facts = prep.new_reexport_facts
 
             from contextor.core.analysis.refresh_planner import RefreshPlanner
             plan = RefreshPlanner.plan_refresh(
@@ -669,6 +677,7 @@ class IncrementalAnalysisEngine:
             affected_set, blast_radius_complete, execution_trace = self._apply_delta_and_commit(
                 file_path, delta, usage_delta, plan, new_imports, new_artifacts, new_usage,
                 new_collision_facts=new_collision_facts,
+                new_reexport_facts=new_reexport_facts,
                 extracted_lineage_facts=prep.extracted_lineage_facts,
                 syntax_source_path=source_path,
                 syntax_fact=checked_and_none,
@@ -758,6 +767,7 @@ class IncrementalAnalysisEngine:
         mod_artifacts: dict,
         new_usage: Any,
         new_collision_facts: Optional[List[Dict[str, Any]]] = None,
+        new_reexport_facts: Optional[Dict[str, Any]] = None,
         extracted_lineage_facts: Any | None = None,
         syntax_source_path: str | None = None,
         syntax_fact: Dict[str, Any] | None = None,
@@ -784,6 +794,7 @@ class IncrementalAnalysisEngine:
                 root_path=self.root_path,
                 file_path=file_path,
                 new_collision_facts=new_collision_facts,
+                new_reexport_facts=new_reexport_facts,
             )
         except Exception as exc:
             _trace_incremental_phase(
@@ -942,6 +953,9 @@ class IncrementalAnalysisEngine:
         if clear_parse_module is not None:
             clear_module_parse_failure(candidate, clear_parse_module)
         self.state.modules = candidate.modules
+        self.state.reexport_facts_by_module = (
+            candidate.reexport_facts_by_module
+        )
         self.state.artifacts = candidate.artifacts
         self.state.module_parse_freshness = candidate.module_parse_freshness
         self.state.syntax_diagnostics_by_path = candidate.syntax_diagnostics_by_path
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 6283c9f..0ec7b72 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -27,7 +27,10 @@ from contextor.core.domain.module import Module
 from contextor.core.domain.refresh_plan import RefreshPlan
 from contextor.core.domain.usage_facts import ModuleUsageFacts
 from contextor.core.graph.graph import build_trie, detect_package_root, build_graph, resolve_module_edges
-from contextor.core.reference.engine import _build_reexport_map
+from contextor.core.reference.shared import (
+    _assemble_reexport_map,
+    validate_reexport_facts_by_module,
+)
 from contextor.core.reference.resolution import _resolve_alias, _resolve_reexport
 from contextor.core.reporting_layer.artifact_usage_report import (
     collect_qualified_artifact_identities,
@@ -41,6 +44,7 @@ class CandidateState:
     architectural model during RefreshPlan execution before commit.
     """
     modules: Dict[str, Any]
+    reexport_facts_by_module: Dict[str, Dict[str, Any]]
     artifacts: Dict[str, Any]
     module_parse_freshness: Dict[str, Dict[str, Any]]
     syntax_diagnostics_by_path: Dict[str, Dict[str, Any]]
@@ -599,6 +603,14 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
     """Initializes Copy-on-Write candidate state from current canonical state."""
     return CandidateState(
         modules=dict(state.modules),
+        reexport_facts_by_module=dict(
+            getattr(
+                state,
+                "reexport_facts_by_module",
+                {},
+            )
+            or {}
+        ),
         artifacts=dict(state.artifacts),
         module_parse_freshness=dict(getattr(state, "module_parse_freshness", {}) or {}),
         syntax_diagnostics_by_path=dict(getattr(state, "syntax_diagnostics_by_path", {}) or {}),
@@ -675,6 +687,7 @@ def execute_refresh_plan(
     root_path: Path,
     file_path: str,
     new_collision_facts: Optional[List[Dict[str, Any]]] = None,
+    new_reexport_facts: Optional[Dict[str, Any]] = None,
 ) -> PlanExecutionOutcome:
     """
     Executes the phases of a RefreshPlan (REPARSE, RECOMPUTE, PATCH, GRAPH)
@@ -684,6 +697,15 @@ def execute_refresh_plan(
     mod_id = Path(delta.module_path).stem if delta.module_path.endswith(".py") else delta.module_path
     old_graph = state.dependency_graph
 
+    if not validate_reexport_facts_by_module(
+        state.reexport_facts_by_module,
+        state.modules,
+    ):
+        raise RuntimeError(
+            "Canonical re-export facts baseline is incomplete; "
+            "fresh full analysis is required."
+        )
+
     # 1. PREPARE candidate state
     candidate = _prepare_candidate_state(state)
     matrix_inputs_changed = bool(
@@ -708,6 +730,14 @@ def execute_refresh_plan(
     if delta.is_deleted:
         candidate.modules.pop(mod_id, None)
         candidate.modules.pop(delta.module_path, None)
+        candidate.reexport_facts_by_module.pop(
+            mod_id,
+            None,
+        )
+        candidate.reexport_facts_by_module.pop(
+            delta.module_path,
+            None,
+        )
         candidate.artifacts.pop(mod_id, None)
         candidate.artifacts.pop(delta.module_path, None)
         candidate.module_usages.pop(delta.module_path, None)
@@ -735,6 +765,24 @@ def execute_refresh_plan(
         if "module_usages" in plan.patch_families and new_usage is not None:
             candidate.module_usages[delta.module_path] = new_usage
 
+    if not delta.is_deleted and "reexport_facts" in plan.patch_families:
+        if new_reexport_facts is None:
+            raise ValueError(
+                f"Planned reexport_facts patch for '{delta.module_path}' "
+                "requires non-None new_reexport_facts."
+            )
+        candidate.reexport_facts_by_module[
+            delta.module_path
+        ] = new_reexport_facts
+
+    if not validate_reexport_facts_by_module(
+        candidate.reexport_facts_by_module,
+        candidate.modules,
+    ):
+        raise RuntimeError(
+            "Candidate re-export facts do not cover the candidate module domain."
+        )
+
         # Ensure canonical targets for delta.module_path exist in candidate.artifact_consumption
         mod_art = candidate.artifacts.get(delta.module_path, {})
         if isinstance(mod_art, dict):
@@ -764,6 +812,15 @@ def execute_refresh_plan(
     for reparse_mod in plan.reparse_modules:
         executed_reparse.append(reparse_mod)
 
+    reexports = None
+    if (
+        plan.recompute_modules
+        or "artifact_consumption" in plan.patch_families
+    ):
+        reexports = _assemble_reexport_map(
+            candidate.reexport_facts_by_module
+        )
+
     # 3. RECOMPUTE - re-evaluate planned cached modules in RAM without source I/O
     executed_recompute: List[str] = []
     if plan.recompute_modules:
@@ -771,8 +828,6 @@ def execute_refresh_plan(
             _find_dependent_consumers,
         )
 
-        new_reexports = _build_reexport_map(candidate.modules)
-
         recompute_queue = deque(plan.recompute_modules)
         scheduled_recompute = set(plan.recompute_modules)
         processed_recompute: Set[str] = set()
@@ -802,7 +857,7 @@ def execute_refresh_plan(
                 consumer_facts=consumer_facts,
                 candidate_consumption=candidate.artifact_consumption,
                 candidate_artifacts=candidate.artifacts,
-                reexports=new_reexports,
+                reexports=reexports,
                 expected_targets=expected_targets,
                 dotted_target_index=dotted_target_index,
                 consumer_target_index=consumer_target_index,
@@ -859,6 +914,9 @@ def execute_refresh_plan(
         elif family == "module_usages":
             executed_patch_families.append("module_usages")
 
+        elif family == "reexport_facts":
+            executed_patch_families.append("reexport_facts")
+
         elif family == "dependency_graph":
             if delta.is_deleted or delta.is_new:
                 new_trie = build_trie(candidate.modules.keys())
@@ -877,7 +935,6 @@ def execute_refresh_plan(
             executed_patch_families.append("dependency_graph")
 
         elif family == "artifact_consumption":
-            new_reexports = _build_reexport_map(candidate.modules)
             if delta.is_deleted:
                 # Remove delta.module_path from all remaining targets
                 for t_key, entry in list(candidate.artifact_consumption.items()):
@@ -893,7 +950,7 @@ def execute_refresh_plan(
                     consumer_facts=new_usage,
                     candidate_consumption=candidate.artifact_consumption,
                     candidate_artifacts=candidate.artifacts,
-                    reexports=new_reexports,
+                    reexports=reexports,
                     expected_targets=expected_targets,
                     dotted_target_index=dotted_target_index,
                     consumer_target_index=consumer_target_index,
diff --git a/contextor/core/analysis/incremental/preparation.py b/contextor/core/analysis/incremental/preparation.py
index be9dfd1..5287885 100644
--- a/contextor/core/analysis/incremental/preparation.py
+++ b/contextor/core/analysis/incremental/preparation.py
@@ -16,6 +16,7 @@ from contextor.core.analysis.state_manager import FileDelta
 from contextor.core.analysis.lineage_extraction import extract_lineage_source_facts
 from contextor.core.domain.lineage_facts import ExtractedLineageSourceFacts
 from contextor.core.domain.usage_facts import ModuleUsageFacts, diff_usage_facts
+from contextor.core.reference.shared import _extract_reexport_facts
 from contextor.core.source import SourceError, parse_source_with_fingerprint
 
 
@@ -33,6 +34,7 @@ class PreparedSourceUpdate:
     new_collision_facts: Optional[List[Dict[str, Any]]] = None
     collision_facts_changed: bool = False
     extracted_lineage_facts: Optional[ExtractedLineageSourceFacts] = None
+    new_reexport_facts: Optional[Dict[str, Any]] = None
     error_status: Optional[str] = None
     error_message: Optional[str] = None
     line_number: Optional[int] = None
@@ -152,6 +154,7 @@ def prepare_source_update(
     persistent_id: Optional[str] = None,
     old_collision_facts: Optional[List[Dict[str, Any]]] = None,
     source_key: str | None = None,
+    old_reexport_facts: Optional[Dict[str, Any]] = None,
 ) -> PreparedSourceUpdate:
     """
     Parses and extracts all necessary facts from a changed/added source file,
@@ -180,6 +183,24 @@ def prepare_source_update(
             column_number=exc.column_number,
         )
 
+    try:
+        new_reexport_facts = _extract_reexport_facts(
+            module_path,
+            parsed_tree,
+        )
+    except Exception as exc:
+        return PreparedSourceUpdate(
+            module_path=module_path,
+            is_new=is_new,
+            new_imports=[],
+            new_artifacts={},
+            new_usage=None,
+            delta=FileDelta(module_path=module_path, is_new=is_new),
+            usage_delta=None,
+            error_status="ERROR",
+            error_message=f"re-export extraction failed: {exc}",
+        )
+
     extracted_lineage_facts = None
     if source_key is not None:
         try:
@@ -276,6 +297,13 @@ def prepare_source_update(
         new_imports=new_imports,
         new_artifacts_dict=new_artifacts,
     )
+    if (
+        not is_new
+        and old_reexport_facts != new_reexport_facts
+    ):
+        delta.metadata_changes[
+            "reexport_facts_changed"
+        ] = True
 
     # 6. Extract Usage facts & UsageDelta
     from contextor.core.reference.engine import extract_module_usage_facts
@@ -298,6 +326,7 @@ def prepare_source_update(
         new_collision_facts=new_collision_facts,
         collision_facts_changed=collision_facts_changed,
         extracted_lineage_facts=extracted_lineage_facts,
+        new_reexport_facts=new_reexport_facts,
     )
 
 
diff --git a/contextor/core/analysis/refresh_planner.py b/contextor/core/analysis/refresh_planner.py
index be5deeb..8b200ab 100644
--- a/contextor/core/analysis/refresh_planner.py
+++ b/contextor/core/analysis/refresh_planner.py
@@ -94,6 +94,12 @@ class RefreshPlanner:
 
         module_path = delta.module_path if delta else (usage_delta.module_path if usage_delta else "")
         usages = module_usages if module_usages is not None else {}
+        has_reexport_facts_change = bool(
+            delta
+            and delta.metadata_changes.get(
+                "reexport_facts_changed"
+            )
+        )
         identity_registry_required = bool(
             delta
             and (
@@ -120,6 +126,7 @@ class RefreshPlanner:
                 "definitions",
                 "identity_registry",
                 "module_usages",
+                "reexport_facts",
                 "dependency_graph",
                 "artifact_consumption",
                 "cached_analytics",
@@ -146,6 +153,7 @@ class RefreshPlanner:
                 "definitions",
                 "identity_registry",
                 "module_usages",
+                "reexport_facts",
                 "dependency_graph",
                 "artifact_consumption",
                 "cached_analytics",
@@ -196,6 +204,11 @@ class RefreshPlanner:
                         recompute_set.add(c_path)
 
             patch_families = ["definitions", "module_usages", "artifact_consumption"]
+            if has_reexport_facts_change:
+                patch_families.insert(
+                    patch_families.index("artifact_consumption"),
+                    "reexport_facts",
+                )
             graph_recomputations = []
             if has_import_changes:
                 patch_families.extend(["modules", "dependency_graph"])
@@ -224,6 +237,11 @@ class RefreshPlanner:
                 "artifact_consumption",
                 "cached_analytics",
             ]
+            if has_reexport_facts_change:
+                patch_families.insert(
+                    patch_families.index("artifact_consumption"),
+                    "reexport_facts",
+                )
             if collision_facts_changed:
                 patch_families.extend(["collision_facts", "collisions"])
 
@@ -242,6 +260,11 @@ class RefreshPlanner:
             recompute_set = _find_dependent_consumers(module_path, usages)
 
             patch_families = ["definitions", "identity_registry", "module_usages", "artifact_consumption"]
+            if has_reexport_facts_change:
+                patch_families.insert(
+                    patch_families.index("artifact_consumption"),
+                    "reexport_facts",
+                )
             if bool(delta.artifacts_added or delta.artifacts_removed) or (usage_delta and not usage_delta.is_empty):
                 patch_families.append("cached_analytics")
             if collision_facts_changed:
@@ -265,12 +288,33 @@ class RefreshPlanner:
         )
 
         patch_families = []
+        recompute_set = (
+            _find_dependent_consumers(
+                module_path,
+                usages,
+            )
+            if has_reexport_facts_change
+            else set()
+        )
         if has_symbol_payload_change:
             patch_families.append("definitions")
         if has_usage:
             patch_families.extend(
                 ["module_usages", "artifact_consumption", "cached_analytics"]
             )
+        if has_reexport_facts_change:
+            if "reexport_facts" not in patch_families:
+                if "artifact_consumption" in patch_families:
+                    patch_families.insert(
+                        patch_families.index("artifact_consumption"),
+                        "reexport_facts",
+                    )
+                else:
+                    patch_families.append("reexport_facts")
+            if "artifact_consumption" not in patch_families:
+                patch_families.append("artifact_consumption")
+            if "cached_analytics" not in patch_families:
+                patch_families.append("cached_analytics")
         if collision_facts_changed:
             patch_families.extend(["collision_facts", "collisions"])
 
@@ -278,12 +322,14 @@ class RefreshPlanner:
             reason = f"Body/usage change in '{module_path}'."
         elif has_symbol_payload_change:
             reason = f"Definition payload change in '{module_path}'."
+        elif has_reexport_facts_change:
+            reason = f"Re-export facts change in '{module_path}'."
         else:
             reason = f"Collision facts update for '{module_path}'."
 
         return RefreshPlan(
             reparse_modules=(),
-            recompute_modules=(),
+            recompute_modules=tuple(sorted(recompute_set)),
             patch_families=compose_patch_families(patch_families),
             graph_recomputations=(),
             refresh_completeness="complete",
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 656e638..e2ed0fc 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -85,6 +85,7 @@ class RepositoryAnalysisState:
     """Canonical runtime state of the repository analysis."""
     modules: Dict[str, Any] = field(default_factory=dict)
     artifacts: Dict[str, Any] = field(default_factory=dict)
+    reexport_facts_by_module: Dict[str, Dict[str, Any]] = field(default_factory=dict)
     dependency_graph: Optional[Any] = None
     artifact_consumption: Dict[str, Any] = field(default_factory=dict)
     artifact_consumption_state: str = "deferred"
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 1feadcb..e905851 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -683,6 +683,15 @@ class ContextorFacade:
             progress_callback=index_progress,
         )
         modules = index.modules
+        from contextor.core.reference.shared import (
+            materialize_reexport_facts_by_module,
+        )
+        canonical_reexport_facts = (
+            materialize_reexport_facts_by_module(
+                modules,
+                index.reference_facts_by_module,
+            )
+        )
 
         emit_stage_end("indexing", indexing_started)
 
@@ -934,9 +943,20 @@ class ContextorFacade:
             )
 
             component_started = time.monotonic()
+            from contextor.core.reference.shared import (
+                validate_reexport_facts_by_module,
+            )
+            if not validate_reexport_facts_by_module(
+                canonical_reexport_facts,
+                mods,
+            ):
+                raise RuntimeError(
+                    "Canonical re-export facts do not cover the current module domain."
+                )
             state = RepositoryAnalysisState(
                 modules=mods,
                 artifacts=raw_artifacts,
+                reexport_facts_by_module=canonical_reexport_facts,
                 dependency_graph=graph,
                 trie=getattr(analysis_result, "trie", None),
                 package_root=getattr(analysis_result, "package_root", ""),
diff --git a/contextor/core/domain/refresh_plan.py b/contextor/core/domain/refresh_plan.py
index 17fdcfc..23a6cd9 100644
--- a/contextor/core/domain/refresh_plan.py
+++ b/contextor/core/domain/refresh_plan.py
@@ -17,6 +17,7 @@ VALID_PATCH_FAMILIES = {
     "modules",
     "definitions",
     "module_usages",
+    "reexport_facts",
     "artifact_consumption",
     "dependency_graph",
     "identity_registry",
diff --git a/contextor/core/live_state/store.py b/contextor/core/live_state/store.py
index 3b395e7..2fb6986 100644
--- a/contextor/core/live_state/store.py
+++ b/contextor/core/live_state/store.py
@@ -38,7 +38,7 @@ from contextor.core.domain.lineage_facts import (
     SurfaceKind,
 )
 
-LIVE_STATE_SCHEMA_VERSION = "1.3"
+LIVE_STATE_SCHEMA_VERSION = "1.4"
 LINEAGE_MANIFEST_SCHEMA_VERSION = "1.0"
 
 LINEAGE_VALIDATION_CACHE_SCHEMA_VERSION = "2"
@@ -118,6 +118,41 @@ def _normalize_symbol_call_facts(state: Any) -> Any:
     return state
 
 
+def _normalize_reexport_facts_state(
+    state: Any,
+) -> Any:
+    if state is None:
+        return state
+
+    from contextor.core.analysis.state_manager import (
+        RepositoryAnalysisState,
+    )
+    from contextor.core.reference.shared import (
+        validate_reexport_facts_by_module,
+    )
+
+    if not isinstance(state, RepositoryAnalysisState):
+        return state
+
+    if (
+        "reexport_facts_by_module" not in vars(state)
+        or not validate_reexport_facts_by_module(
+            getattr(
+                state,
+                "reexport_facts_by_module",
+                None,
+            ),
+            getattr(state, "modules", None),
+        )
+    ):
+        raise pickle.UnpicklingError(
+            "Canonical re-export facts are missing or incomplete; "
+            "fresh full analysis is required."
+        )
+
+    return state
+
+
 def _revalidate_lineage_span(span: Any) -> SourceSpan:
     if not isinstance(span, SourceSpan):
         raise pickle.UnpicklingError("Invalid lineage SourceSpan.")
@@ -1382,6 +1417,7 @@ def read_metadata(cache_dir: str | Path) -> LiveStateMetadata | None:
             "1.0",
             "1.1",
             "1.2",
+            "1.3",
             LIVE_STATE_SCHEMA_VERSION,
         }:
             return None
@@ -1438,6 +1474,26 @@ def save_snapshot(
 ) -> LiveStateMetadata:
     """Atomically publish a complete snapshot and monotonically increasing revision."""
 
+    from contextor.core.analysis.state_manager import (
+        RepositoryAnalysisState,
+    )
+    from contextor.core.reference.shared import (
+        validate_reexport_facts_by_module,
+    )
+
+    if isinstance(state, RepositoryAnalysisState) and not validate_reexport_facts_by_module(
+        getattr(
+            state,
+            "reexport_facts_by_module",
+            None,
+        ),
+        state.modules,
+    ):
+        raise ValueError(
+            "Cannot persist RepositoryAnalysisState with incomplete "
+            "canonical re-export facts."
+        )
+
     state_file, meta_file, lock_file = _paths(cache_dir)
     state_file.parent.mkdir(parents=True, exist_ok=True)
     lock_fd = _acquire_lock(lock_file)
@@ -1975,6 +2031,16 @@ def load_snapshot(
                 repo_id=expected_repo_id,
             )
 
+            phase_started = time.monotonic()
+            state_obj = _normalize_reexport_facts_state(
+                state_obj
+            )
+            _trace_snapshot_load_phase(
+                "normalize_reexport_facts_state",
+                phase_started,
+                repo_id=expected_repo_id,
+            )
+
             phase_started = time.monotonic()
             state_revision = (
                 state_obj.get("revision") if isinstance(state_obj, dict)
@@ -2109,6 +2175,9 @@ def load_snapshot(
                 _normalize_symbol_call_facts(payload)
             )
         )
+        payload = _normalize_reexport_facts_state(
+            payload
+        )
         if payload is not None and hasattr(payload, "__dict__"):
             if not hasattr(payload, "module_usages"):
                 try:
diff --git a/contextor/core/reference/shared.py b/contextor/core/reference/shared.py
index 1e81f39..92423a0 100644
--- a/contextor/core/reference/shared.py
+++ b/contextor/core/reference/shared.py
@@ -11,13 +11,21 @@ This module must NOT depend on reference.engine or reference.index.
 from __future__ import annotations
 
 import ast
-from typing import Any
+from typing import Any, Mapping
 
 from .resolution import _absolute_import_module
 
 MAX_USAGE_DETAILS = 15
 
 _REEXPORT_CACHE: dict = {}
+_REEXPORT_FACT_KEYS = frozenset(
+    {
+        "exporter",
+        "explicit_all",
+        "bindings",
+        "star_sources",
+    }
+)
 
 
 def reset_reexport_cache() -> None:
@@ -30,6 +38,129 @@ def _export_module_name(module_id: str) -> str:
     return module_id.removesuffix(".__init__")
 
 
+def _is_valid_reexport_fact(
+    module_id: str,
+    fact: Any,
+) -> bool:
+    if not isinstance(module_id, str) or not module_id:
+        return False
+
+    if not isinstance(fact, dict):
+        return False
+
+    if set(fact) != _REEXPORT_FACT_KEYS:
+        return False
+
+    if fact.get("exporter") != _export_module_name(module_id):
+        return False
+
+    explicit_all = fact.get("explicit_all")
+    if explicit_all is not None:
+        if not isinstance(explicit_all, list):
+            return False
+        if not all(
+            isinstance(item, str)
+            for item in explicit_all
+        ):
+            return False
+
+    bindings = fact.get("bindings")
+    if not isinstance(bindings, dict):
+        return False
+    if not all(
+        isinstance(local, str)
+        and isinstance(target, str)
+        for local, target in bindings.items()
+    ):
+        return False
+
+    star_sources = fact.get("star_sources")
+    if not isinstance(star_sources, list):
+        return False
+    if not all(
+        isinstance(source, str)
+        for source in star_sources
+    ):
+        return False
+
+    return True
+
+
+def validate_reexport_facts_by_module(
+    facts_by_module: Any,
+    modules: Any,
+) -> bool:
+    if not isinstance(facts_by_module, dict):
+        return False
+
+    if not isinstance(modules, dict):
+        return False
+
+    if set(facts_by_module) != set(modules):
+        return False
+
+    return all(
+        _is_valid_reexport_fact(
+            module_id,
+            facts_by_module[module_id],
+        )
+        for module_id in modules
+    )
+
+
+def materialize_reexport_facts_by_module(
+    modules: dict,
+    compact_reference_facts: Mapping[str, Any] | None = None,
+) -> dict[str, dict[str, Any]]:
+    result: dict[str, dict[str, Any]] = {}
+    compact_facts = compact_reference_facts or {}
+
+    for module_id, module in modules.items():
+        envelope = compact_facts.get(module_id)
+        fact = None
+        if isinstance(envelope, Mapping) and envelope.get("status") == "available":
+            facts = envelope.get("facts")
+            if isinstance(facts, Mapping):
+                compact_fact = facts.get("reexports")
+                if _is_valid_reexport_fact(module_id, compact_fact):
+                    fact = compact_fact
+
+        if fact is None:
+            tree = getattr(module, "ast_tree", None)
+            if tree is None:
+                raise RuntimeError(
+                    "Canonical re-export facts unavailable for module "
+                    f"'{module_id}'."
+                )
+            fact = _extract_reexport_facts(module_id, tree)
+            if not _is_valid_reexport_fact(module_id, fact):
+                raise RuntimeError(
+                    "Canonical re-export facts unavailable for module "
+                    f"'{module_id}'."
+                )
+
+        result[module_id] = {
+            "exporter": fact["exporter"],
+            "explicit_all": (
+                None
+                if fact["explicit_all"] is None
+                else list(fact["explicit_all"])
+            ),
+            "bindings": dict(fact["bindings"]),
+            "star_sources": list(fact["star_sources"]),
+        }
+
+    if not validate_reexport_facts_by_module(
+        result,
+        modules,
+    ):
+        raise RuntimeError(
+            "Canonical re-export facts do not cover the current module domain."
+        )
+
+    return result
+
+
 def _extract_reexport_facts(
     module_id: str,
     tree: Any,
diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index 76c19d1..f69af1b 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -63,7 +63,13 @@ def _assert_full_parity(incremental_state: RepositoryAnalysisState, oracle_state
         assert inc_facts.imports == ora_facts.imports
         assert inc_facts.aliases == ora_facts.aliases
 
-    # 4. Artifact Consumption (exact target set, exact consumers, and exact channel sets)
+    # 4. Canonical re-export facts
+    assert (
+        incremental_state.reexport_facts_by_module
+        == oracle_state.reexport_facts_by_module
+    )
+
+    # 5. Artifact Consumption (exact target set, exact consumers, and exact channel sets)
     assert set(incremental_state.artifact_consumption.keys()) == set(oracle_state.artifact_consumption.keys())
     for target, ora_entry in oracle_state.artifact_consumption.items():
         inc_entry = incremental_state.artifact_consumption.get(target, {})
@@ -79,13 +85,13 @@ def _assert_full_parity(incremental_state: RepositoryAnalysisState, oracle_state
                 f"incremental={inc_channels.get(consumer)} vs full={ora_channels.get(consumer)}"
             )
 
-    # 5. Dependency Graph
+    # 6. Dependency Graph
     if oracle_state.dependency_graph is not None:
         assert incremental_state.dependency_graph is not None
         assert incremental_state.dependency_graph.hard_edges == oracle_state.dependency_graph.hard_edges
         assert incremental_state.dependency_graph.soft_edges == oracle_state.dependency_graph.soft_edges
 
-    # 6. Macro Graph Metrics
+    # 7. Macro Graph Metrics
     if oracle_state.metrics is not None:
         assert incremental_state.metrics is not None
         assert incremental_state.metrics == oracle_state.metrics
@@ -1326,6 +1332,194 @@ def test_reexport_retarget_matches_full_oracle(tmp_path):
     )
 
 
+def test_reexport_all_only_change_is_ram_only_and_matches_full_oracle(
+    tmp_path,
+    monkeypatch,
+):
+    provider = tmp_path / "a.py"
+    reexporter = tmp_path / "b.py"
+    consumer = tmp_path / "c.py"
+    provider.write_text(
+        "def foo():\n"
+        "    return 1\n",
+        encoding="utf-8",
+    )
+    reexporter.write_text(
+        "from a import foo\n"
+        "__all__ = ['foo']\n",
+        encoding="utf-8",
+    )
+    consumer.write_text(
+        "from b import *\n"
+        "\n"
+        "def run():\n"
+        "    return foo()\n",
+        encoding="utf-8",
+    )
+    for index in range(1, 4):
+        (tmp_path / f"noise_{index}.py").write_text(
+            f"VALUE_{index} = {index}\n",
+            encoding="utf-8",
+        )
+
+    errors, _ = ContextorFacade().analyze_project(
+        str(tmp_path)
+    )
+    assert not errors, errors
+    hydrated = hydrate_repository_engine(tmp_path)
+    assert hydrated is not None
+    engine = hydrated.engine
+    state = engine.state
+    assert set(state.reexport_facts_by_module) == set(
+        state.modules
+    )
+    assert state.reexport_facts_by_module["b"]["explicit_all"] == [
+        "foo"
+    ]
+
+    reexporter.write_text(
+        "from a import foo\n"
+        "__all__ = []\n",
+        encoding="utf-8",
+    )
+
+    from contextor.core.analysis.incremental import plan_executor
+    import contextor.core.domain.module as module_domain
+
+    assembled_domains = []
+    ast_accesses = []
+    original_assembler = plan_executor._assemble_reexport_map
+
+    def assemble_spy(facts_by_module):
+        assert isinstance(facts_by_module, dict)
+        assert set(facts_by_module) == set(engine.state.modules)
+        assembled_domains.append(deepcopy(facts_by_module))
+        return original_assembler(facts_by_module)
+
+    def fail_ast_access(*args, **kwargs):
+        ast_accesses.append((args, kwargs))
+        raise AssertionError(
+            "incremental re-export execution accessed Module.ast_tree"
+        )
+
+    with (
+        patch.object(
+            plan_executor,
+            "_assemble_reexport_map",
+            side_effect=assemble_spy,
+        ),
+        patch.object(
+            Module,
+            "ast_tree",
+            new=property(fail_ast_access),
+        ),
+        patch.object(
+            module_domain,
+            "_get_cached_ast",
+            side_effect=fail_ast_access,
+        ),
+    ):
+        result = engine.update_file(str(reexporter))
+
+    assert ast_accesses == []
+    assert len(assembled_domains) == 1
+    assert set(assembled_domains[0]) == set(engine.state.modules)
+    assert all(
+        isinstance(fact, dict)
+        for fact in assembled_domains[0].values()
+    )
+    assert "reexport_facts" in result.shadow_plan.patch_families
+    assert "c" in result.execution_trace["recompute_modules"]
+
+    oracle = _build_full_static_state(tmp_path)
+    _assert_full_parity(engine.state, oracle)
+
+
+def test_reexport_canonical_domain_tracks_add_change_delete(tmp_path):
+    provider = tmp_path / "a.py"
+    reexporter = tmp_path / "b.py"
+    cache_dir = tmp_path / "cache"
+    cache_dir.mkdir()
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(modules={}),
+        PersistentIdentityRegistry(str(tmp_path)),
+        FileStateManager(str(cache_dir)),
+        str(tmp_path),
+    )
+
+    def assert_domain():
+        assert set(engine.state.reexport_facts_by_module) == set(
+            engine.state.modules
+        )
+
+    provider.write_text(
+        "def foo():\n"
+        "    return 1\n",
+        encoding="utf-8",
+    )
+    engine.update_file(str(provider))
+    assert_domain()
+
+    reexporter.write_text(
+        "from a import foo\n",
+        encoding="utf-8",
+    )
+    engine.update_file(str(reexporter))
+    assert_domain()
+    old_slice = deepcopy(
+        engine.state.reexport_facts_by_module["b"]
+    )
+
+    reexporter.write_text(
+        "from a import foo as bar\n",
+        encoding="utf-8",
+    )
+    changed = engine.update_file(str(reexporter))
+    assert changed.status == "UPDATED"
+    assert_domain()
+    assert engine.state.reexport_facts_by_module["b"] != old_slice
+
+    reexporter.unlink()
+    deleted = engine.update_file(str(reexporter))
+    assert deleted.status == "DELETED"
+    assert_domain()
+    assert "b" not in engine.state.reexport_facts_by_module
+
+
+def test_reexport_facts_preserve_last_known_good_on_parse_failure(
+    tmp_path,
+):
+    reexporter = tmp_path / "b.py"
+    cache_dir = tmp_path / "cache"
+    cache_dir.mkdir()
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(modules={}),
+        PersistentIdentityRegistry(str(tmp_path)),
+        FileStateManager(str(cache_dir)),
+        str(tmp_path),
+    )
+    reexporter.write_text(
+        "from a import foo\n",
+        encoding="utf-8",
+    )
+    initial = engine.update_file(str(reexporter))
+    assert initial.status == "UPDATED"
+    old_slice = deepcopy(
+        engine.state.reexport_facts_by_module["b"]
+    )
+
+    reexporter.write_text(
+        "def foo(:\n"
+        "    return 1\n",
+        encoding="utf-8",
+    )
+    failed = engine.update_file(str(reexporter))
+
+    assert failed.status == "SYNTAX_ERROR"
+    assert engine.state.reexport_facts_by_module["b"] == old_slice
+    assert engine.state.module_parse_freshness["b"]["state"] == "stale"
+
+
 def test_natural_ambiguity_transition_matches_full_oracle_state(
     tmp_path,
 ):
diff --git a/tests/test_live_state_store.py b/tests/test_live_state_store.py
index 8d8ad88..52dd44b 100644
--- a/tests/test_live_state_store.py
+++ b/tests/test_live_state_store.py
@@ -179,7 +179,7 @@ def test_exact_snapshot_revision_binds_embedded_state_and_metadata(tmp_path):
     assert metadata.revision == loaded_metadata.revision == loaded.revision == 1
 
 
-def test_exact_schema_13_splits_lineage_and_roundtrips(tmp_path):
+def test_current_schema_14_splits_lineage_and_roundtrips(tmp_path):
     import json
     import pickle
 
@@ -202,7 +202,7 @@ def test_exact_schema_13_splits_lineage_and_roundtrips(tmp_path):
         },
     )
 
-    assert metadata.schema_version == "1.3"
+    assert metadata.schema_version == "1.4"
     assert metadata.lineage_manifest_file
 
     with (
@@ -280,6 +280,95 @@ def test_exact_schema_13_splits_lineage_and_roundtrips(tmp_path):
     )
 
 
+def test_current_schema_reexport_facts_roundtrip(tmp_path):
+    facts = {
+        "pkg.mod": {
+            "exporter": "pkg.mod",
+            "explicit_all": None,
+            "bindings": {},
+            "star_sources": [],
+        }
+    }
+    state = RepositoryAnalysisState(
+        modules={"pkg.mod": SimpleNamespace()},
+        reexport_facts_by_module=facts,
+    )
+
+    metadata = save_snapshot(
+        state,
+        tmp_path,
+        "reexport-roundtrip",
+    )
+    loaded, loaded_metadata = load_snapshot(
+        tmp_path,
+        "reexport-roundtrip",
+    )
+
+    assert metadata.schema_version == "1.4"
+    assert loaded_metadata.schema_version == "1.4"
+    assert loaded.reexport_facts_by_module == facts
+
+
+def test_save_snapshot_rejects_incomplete_canonical_reexport_facts(
+    tmp_path,
+):
+    state = RepositoryAnalysisState(
+        modules={"pkg.mod": SimpleNamespace()},
+        reexport_facts_by_module={},
+    )
+
+    with pytest.raises(
+        ValueError,
+        match=(
+            "Cannot persist RepositoryAnalysisState with incomplete "
+            "canonical re-export facts"
+        ),
+    ):
+        save_snapshot(
+            state,
+            tmp_path,
+            "incomplete-reexport",
+        )
+
+
+def test_legacy_canonical_snapshot_without_reexport_facts_is_rejected(
+    tmp_path,
+):
+    import json
+    import pickle
+
+    state = RepositoryAnalysisState(
+        modules={"pkg.mod": SimpleNamespace()},
+        reexport_facts_by_module={
+            "pkg.mod": {
+                "exporter": "pkg.mod",
+                "explicit_all": None,
+                "bindings": {},
+                "star_sources": [],
+            }
+        },
+    )
+    del vars(state)["reexport_facts_by_module"]
+    (tmp_path / "engine_state.pkl").write_bytes(
+        pickle.dumps(state)
+    )
+    (tmp_path / "engine_state.meta.json").write_text(
+        json.dumps(
+            {
+                "schema_version": "1.3",
+                "state_id": "legacy-canonical",
+                "revision": 1,
+            }
+        ),
+        encoding="utf-8",
+    )
+
+    assert load_snapshot(
+        tmp_path,
+        "legacy-canonical",
+    ) is None
+
+
 def test_split_snapshot_load_emits_non_overlapping_phase_timings(tmp_path):
     import contextor.core.runtime_trace as runtime_trace
 
diff --git a/tests/test_mcp_incremental_hydration.py b/tests/test_mcp_incremental_hydration.py
index 54d1db4..7b032a7 100644
--- a/tests/test_mcp_incremental_hydration.py
+++ b/tests/test_mcp_incremental_hydration.py
@@ -18,6 +18,10 @@ from contextor.core.reporting_layer.artifact_usage_report import (
     collect_qualified_artifact_identities,
 )
 from contextor.core.symbol_engine.indexer import index_repository
+from contextor.core.reference.shared import (
+    materialize_reexport_facts_by_module,
+    validate_reexport_facts_by_module,
+)
 from contextor.core.live_state import CanonicalLiveServer, LiveStateClient
 
 pytestmark = pytest.mark.live
@@ -64,13 +68,19 @@ def test_update_persist_restart_hydrate_keeps_live_reverse_context(tmp_path, mon
     repo.mkdir()
     provider = repo / "provider.py"
     provider.write_text("def run():\n    return 1\n", encoding="utf-8")
-    modules = index_repository(str(repo)).modules
+    index = index_repository(str(repo))
+    modules = index.modules
+    reexport_facts_by_module = materialize_reexport_facts_by_module(
+        modules,
+        index.reference_facts_by_module,
+    )
     artifacts, failures = collect_module_artifacts(modules, str(repo))
     assert not failures
     trie = build_trie(modules)
     package_root = detect_package_root(modules, trie)
     state = RepositoryAnalysisState(
         modules=dict(modules),
+        reexport_facts_by_module=reexport_facts_by_module,
         artifacts=artifacts,
         dependency_graph=build_graph(modules, trie=trie, package_root=package_root),
         trie=trie,
@@ -123,6 +133,10 @@ def test_update_persist_restart_hydrate_keeps_live_reverse_context(tmp_path, mon
     mcp_runtime._live_engines.clear()
     hydrated = mcp_runtime.get_or_init_engine(repo.resolve())
     assert hydrated is not None
+    assert validate_reexport_facts_by_module(
+        hydrated.engine.state.reexport_facts_by_module,
+        hydrated.engine.state.modules,
+    )
     context = json.loads(
         mcp_server.get_file_edit_context.fn(
             repo_path=str(repo), file_path="provider.py", compact=False
END_ACTUAL_DIFF
