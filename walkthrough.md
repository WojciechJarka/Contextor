## TASK

CONTEXTOR_B0G4C38D4A_CYCLE_SEMANTICS_REPORT_PUBLICATION; strict controlled implementation. Evidence classes are indicated below. STOP after this stage.

## HEAD_BEFORE

112d16a8ff86e49ac4f1a13c644b3cd27a351946

## HEAD_AFTER

112d16a8ff86e49ac4f1a13c644b3cd27a351946

## GIT_STATUS

Pre-edit: clean. Post-edit before report:

```text
M contextor/core/api/facade.py
 M contextor/core/reporting_engine/io_manager.py
 M contextor/core/reporting_engine/pipeline.py
 M tests/test_cycle_semantics_full_integration.py
?? contextor/core/cycle_semantics/report_projection.py
?? tests/test_cycle_semantics_report_projection.py
```

## PRECHECK

DIRECT_EVIDENCE: Contextor MCP first; baseline LIVE revision 507, epoch 6b4c9554981b4b779b705089dac32739, continuous, resync_required=false, syntax=0 fresh, collisions=0 fresh, cycles=16 fresh. Current source anchors matched C38D3A. No initial Git changes.

## CONTEXTOR_DISCOVERY_COVERAGE

get_mcp_documentation; get_symbol_implementation for facade, pipeline, writer, public projection; get_module_context for pipeline, writer, public projection, header; get_file_edit_context for consumers/tests_covering and blast radius. Direct writer regression nodes selected from tests_covering and source. Post-edit six symbols verified with workspace_sync=verified at revision 514.

## FILES_CHANGED

- contextor/core/api/facade.py
- contextor/core/reporting_engine/pipeline.py
- contextor/core/reporting_engine/io_manager.py
- tests/test_cycle_semantics_full_integration.py
- contextor/core/cycle_semantics/report_projection.py
- tests/test_cycle_semantics_report_projection.py

walkthrough.md is report only.

## DIFF_BASELINE_METHOD

Exact pre-edit working-tree bytes of all four existing files were copied outside the repo before any D4A edit. Current-task diffs compare those copies to current bytes; new files compare against empty. Facade had CRLF in working tree while HEAD used LF; only LF-normalized content equals HEAD. This line-ending difference is not treated as a D4A edit.

contextor/core/api/facade.py: pre-edit bytes equal HEAD=False; LF-normalized equality=True
contextor/core/reporting_engine/pipeline.py: pre-edit bytes equal HEAD=True; LF-normalized equality=True
contextor/core/reporting_engine/io_manager.py: pre-edit bytes equal HEAD=True; LF-normalized equality=True
tests/test_cycle_semantics_full_integration.py: pre-edit bytes equal HEAD=True; LF-normalized equality=True

## SINGLE_CANONICAL_MATERIALIZATION

CODE_PATH_PROVED: facade passes the existing cycle_semantics object and freshness/reason to pipeline. Pipeline invokes pure builder and never rematerializes. Synthetic FULL call-count test: exactly 1 materialization.

## PURE_REPORT_PROJECTION

CONTRACT_PROVED: builder consumes immutable CycleSemanticsSnapshot or None and report_header. It validates freshness/reason and calls existing bounded public projection. No source reads, AST, graph construction, LIVE or persistence.

## REPORT_SCHEMA_VERSION

1.0.0

## REPORT_GENERATION_METADATA

Existing build_report_header(root_path, data_source="global") result is copied into dedicated JSON.

## SOURCE_EVIDENCE_PRESERVATION

graph_sha256, source fingerprints, source issues, source coverage/counts, snapshot schema, and runtime_execution_status copied from canonical FULL snapshot. Synthetic FULL test compares graph SHA and source fingerprints with canonical state.

## PARTIAL_EVIDENCE_POLICY

PARTIAL_SOURCE_EVIDENCE yields status=partial and retains coverage. Pure test passes.

## STALE_EVIDENCE_POLICY

Stale snapshot yields status=stale and retains historical issues. Pure test passes.

## MISSING_EVIDENCE_POLICY

None/deferred/None yields unavailable and projection=None; None/fresh is rejected. Synthetic materializer failure leaves structural FULL working and emits unavailable.

## UNVERIFIED_REPORT_LIVE_BINDING

publication_binding.status=UNVERIFIED_REPORT_VS_CANONICAL_LIVE; canonical_revision=null; live_revision=null. No separate LIVE revision inserted.

## NO_RUNTIME_IMPORT_EXECUTION

CONTRACT_PROVED by source and isolated builder cold-import test: no GUI, MCP, LIVE or analyzed repository module execution. No real Contextor FULL run. Runtime adoption remains UNKNOWN until reload.

## NO_REPORT_SOURCE_IO

CODE_PATH_PROVED: report builder only reads passed in-memory snapshot/header. No source_cohort, source file, indexer or second graph call added.

## CANONICAL_REPORT_FILE

output/<repo_name>_cycle_semantics.json; synthetic FULL verified existence and JSON.

## DATED_REPORT_SNAPSHOT

output/<repo_name>_<datestamp>/<repo_name>_cycle_semantics.json; synthetic FULL verified equivalent semantic content.

## LEGACY_REPORT_SCHEMA_PARITY

Dedicated JSON written after legacy report writes. No existing report payload was modified. Legacy negative assertion excludes only _cycle_semantics.json filenames; structural cycle assertions retained. Two direct writer regression tests passed.

## OPTIONAL_REPORT_FAILURE_ISOLATION

Builder ordinary projection exception yields projection_unavailable while preserving evidence; AnalysisCancelled propagates. Writer catches ordinary optional write error. Extra synthetic OSError test confirmed structure and summary survive. Its initial test harness wrapper lacked save_json log/label kwargs and failed; wrapper was fixed and the node passed. This was a test harness error.

## HISTORICAL_REPORT_AFTER_LIVE_CHANGE

Synthetic incremental update makes canonical semantic state stale while prior report bytes remain unchanged; report still says freshness_at_report_generation=fresh and LIVE binding unverified.

## TARGETED_TEST_RESULTS

Required five focused files plus two writer regression nodes: 81 passed in 21.31s. The subsequent added optional writer failure node: 1 passed in 2.27s after test-wrapper correction. 82 distinct passing nodes. Earlier two new files: 39 passed in 14.76s. No full suite or real repository FULL.

## REPORTING_REGRESSION_RESULTS

tests/test_io_manager.py::test_write_global_reports_uses_canonical_names and ::test_write_global_reports_emits_markdown_summary both included in 81-pass run.

## LIVE_AUTHORITY_BEFORE_AFTER

BEFORE same-task pre-edit authority identity: UNKNOWN (not captured). Historical prior-stage identity: repo_id ctx_8efc50d8; runtime_domain_id rd1_4bb21e833272147f29727f8174356b437bdb3dbcba1b2d4965637b97183f8654; service_instance_id 88e879fa630c41299f7ba675009e267f; lease_generation 32; service_pid 7840; process_start_identity 134367770052413468; endpoint_fingerprint e73abe0959388d48a8c7608c2d13ed8e150314242e23433d2a0c3b36ab316770. AFTER read-only IPC LiveStateClient(is_owner=False) authority_status matched endpoint and those nonsecret identity fields; root C:\Temp\Contextor_Repo. No owner request or reconciliation.

## LIVE_REVISION_BEFORE_AFTER

507 -> 514. desktop_watcher UPDATED events: 508 report_projection.py, 509 facade.py, 510 pipeline.py, 511 io_manager.py, 512 projection tests, 513 integration tests, 514 final integration test edit.

## ACTIVITY_EPOCH_BEFORE_AFTER

6b4c9554981b4b779b705089dac32739 -> unchanged.

## EVENT_CONTINUITY

continuous; resync_required=false after revision 514.

## WORKSPACE_SYNC

Contextor get_symbol_implementation state_freshness.workspace_sync=verified at revision 514 for all four production files and both test files. Module, graph, topology, cycle, collision and lineage families fresh.

## COLLISIONS_BEFORE_AFTER

0 -> 0, fresh.

## STRUCTURAL_CYCLES_BEFORE_AFTER

16 -> 16, fresh.

## NEW_IMPORT_CYCLES

0 additional structural cycle diagnostics by count. INFERENCE: count alone does not establish identical cycle membership; no graph policy or detector changed.

## MCP_SERVER_RESTART_REQUIRED

NO_AUTOMATIC_RESTART_IN_THIS_STAGE.

## DESKTOP_LIVE_RESTART_REQUIRED

YES_BEFORE_PRODUCTION_ACTIVATION.

## RUNTIME_CODE_ADOPTION_STATUS

UNKNOWN_UNTIL_RELOAD_VERIFIED. Source synchronization does not prove serving-process adoption.

## FINAL_VERDICT

B0G4C38D4A_PARTIAL: implementation, focused tests, watcher propagation and source sync passed, but same-task pre-edit authority identity was not captured. No restart, update_file, Git mutation, reader change, or real repository FULL. Stop and await proceduj.

## FULL_DIFFS

Complete current-task diffs for all six changed source/test files follow.

```diff
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1,34 +1,34 @@
-"""
-contextor/core/facade.py
-
-Orchestrator for the Contextor analysis pipeline.
-Exposes high-level operations for the presentation layer (GUI/CLI)
-so they don't have to couple with internal analyzers.
-"""
-
+"""
+contextor/core/facade.py
+
+Orchestrator for the Contextor analysis pipeline.
+Exposes high-level operations for the presentation layer (GUI/CLI)
+so they don't have to couple with internal analyzers.
+"""
+
 import json
 import os
 import time
 from pathlib import Path
-from typing import Any
-
-from contextor.core.errors import AnalysisCancelled, checkpoint
-from contextor.core.graph.cycles import detect_cycles
-from contextor.core.graph.graph import build_graph
-from contextor.core.graph.incremental import get_cached_graph
-from contextor.core.graph.metrics import compute_graph_metrics
-from contextor.core.hotspots import detect_hotspots
-from contextor.core.paths import DEFAULT_IGNORED_DIRS, output_dir, repo_key, state_dir
+from typing import Any
+
+from contextor.core.errors import AnalysisCancelled, checkpoint
+from contextor.core.graph.cycles import detect_cycles
+from contextor.core.graph.graph import build_graph
+from contextor.core.graph.incremental import get_cached_graph
+from contextor.core.graph.metrics import compute_graph_metrics
+from contextor.core.hotspots import detect_hotspots
+from contextor.core.paths import DEFAULT_IGNORED_DIRS, output_dir, repo_key, state_dir
 from contextor.core.reference.engine import reset_caches
 from contextor.core.reference.index import assemble_reference_index_or_fallback
 from contextor.core.runtime_trace import trace_event
-from contextor.core.reporting_engine.debt import compute_debt
-from contextor.core.reporting_engine.generators import (
-    generate_report,
-    generate_structure_report,
-    generate_summary_report,
-    slice_report_for_layer,
-)
+from contextor.core.reporting_engine.debt import compute_debt
+from contextor.core.reporting_engine.generators import (
+    generate_report,
+    generate_structure_report,
+    generate_summary_report,
+    slice_report_for_layer,
+)
 from contextor.core.reporting_engine.header import build_report_header
 from contextor.core.reporting_engine.canonical_artifacts import (
     canonical_artifact_report,
@@ -55,7 +55,7 @@
 from contextor.core.validator import validate
 from contextor.core.validator.collisions import (
     compute_collisions_from_facts,
-    materialize_canonical_collision_facts,
+    materialize_canonical_collision_facts,
     validate_name_collisions,
 )
 from contextor.core.live_state import (
@@ -153,40 +153,40 @@
     repo_name = Path(repo_path).name
     safe_name = repo_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
 
-    candidates = []
-
-    for base in (
-        Path(__file__).resolve().parents[2] / "ui",  # contextor/ui
-        Path(__file__).resolve().parents[3] / "ui",  # pre-rebrand <root>/ui
-    ):
-        candidates.append(base / f"exclude_state_{safe_name}.json")
-        candidates.append(base / "exclude_state.json")
-
-    return candidates
-
-
+    candidates = []
+
+    for base in (
+        Path(__file__).resolve().parents[2] / "ui",  # contextor/ui
+        Path(__file__).resolve().parents[3] / "ui",  # pre-rebrand <root>/ui
+    ):
+        candidates.append(base / f"exclude_state_{safe_name}.json")
+        candidates.append(base / "exclude_state.json")
+
+    return candidates
+
+
 def _load_excludes_for_repo(repo_path: str) -> tuple[list, set]:
-    """Helper to read soft excludes and auto-exclude dir names for a given repo.
-    Returns (excluded_paths, extra_ignored_dirs).
-    """
-
-    for state_file in [exclude_state_file(repo_path), *_legacy_exclude_files(repo_path)]:
-        if not state_file.exists():
-            continue
-
-        try:
-            with open(state_file, encoding="utf-8") as f:
-                data = json.load(f)
-        except (OSError, ValueError):
-            continue
-
-        excluded = data.get("excluded", [])
-        # Auto-exclude dir names stored by exclude_gui (pre-computed list)
-        extra_dirs = set(data.get("auto_exclude_dirs", DEFAULT_IGNORED_DIRS))
-
-        return excluded, extra_dirs
-
-    # Sensible defaults when no state file exists
+    """Helper to read soft excludes and auto-exclude dir names for a given repo.
+    Returns (excluded_paths, extra_ignored_dirs).
+    """
+
+    for state_file in [exclude_state_file(repo_path), *_legacy_exclude_files(repo_path)]:
+        if not state_file.exists():
+            continue
+
+        try:
+            with open(state_file, encoding="utf-8") as f:
+                data = json.load(f)
+        except (OSError, ValueError):
+            continue
+
+        excluded = data.get("excluded", [])
+        # Auto-exclude dir names stored by exclude_gui (pre-computed list)
+        extra_dirs = set(data.get("auto_exclude_dirs", DEFAULT_IGNORED_DIRS))
+
+        return excluded, extra_dirs
+
+    # Sensible defaults when no state file exists
     return [], set(DEFAULT_IGNORED_DIRS)
 
 
@@ -232,25 +232,25 @@
             known.add(normalized)
 
     return combined, extra_dirs
-
-
-def _log_skipped(skipped, log) -> None:
-    """
-    Reports files that carry a '.py' name but are not analyzable Python.
-    """
-
-    if not skipped or not log:
-        return
-
-    log(f"Skipped {len(skipped)} file(s) that are not analyzable Python:")
-
-    for item in skipped[:10]:
-        log(f"  - {item.path} ({item.reason})")
-
-    if len(skipped) > 10:
-        log(f"  … and {len(skipped) - 10} more (see the report)")
-
-
+
+
+def _log_skipped(skipped, log) -> None:
+    """
+    Reports files that carry a '.py' name but are not analyzable Python.
+    """
+
+    if not skipped or not log:
+        return
+
+    log(f"Skipped {len(skipped)} file(s) that are not analyzable Python:")
+
+    for item in skipped[:10]:
+        log(f"  - {item.path} ({item.reason})")
+
+    if len(skipped) > 10:
+        log(f"  … and {len(skipped) - 10} more (see the report)")
+
+
 def _initialize_repository_identity(repo_root: str | Path) -> PersistentIdentityRegistry:
     """Persist a repository identity before any analysis pipeline starts."""
 
@@ -650,9 +650,9 @@
         )
 
         component_started = time.monotonic()
-        previous_canonical_state = resolve_authoritative_repository_state(
-            path, _lease_held=True
-        )
+        previous_canonical_state = resolve_authoritative_repository_state(
+            path, _lease_held=True
+        )
         emit_stage_component_end(
             "identity_and_setup",
             "authoritative_state_resolution",
@@ -687,15 +687,15 @@
             progress_callback=index_progress,
         )
         modules = index.modules
-        from contextor.core.reference.shared import (
-            materialize_reexport_facts_by_module,
-        )
-        canonical_reexport_facts = (
-            materialize_reexport_facts_by_module(
-                modules,
-                index.reference_facts_by_module,
-            )
-        )
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
 
@@ -731,9 +731,9 @@
                 trie=trie,
                 package_root=package_root,
                 progress_callback=graph_progress,
-                reexport_facts_by_module=canonical_reexport_facts,
-            ),
-            reexport_facts_by_module=canonical_reexport_facts,
+                reexport_facts_by_module=canonical_reexport_facts,
+            ),
+            reexport_facts_by_module=canonical_reexport_facts,
         )
 
         emit_stage_end("graph", graph_started)
@@ -767,79 +767,79 @@
         )
 
         emit_stage_end("metrics", metrics_started)
-
-        cycle_semantics = None
-        cycle_semantics_state = "deferred"
-        cycle_semantics_invalidation_reason = None
-        semantic_started_ns = time.perf_counter_ns()
-
-        try:
-            from contextor.core.cycle_semantics.materialization import (
-                materialize_cycle_semantics,
-            )
-            from contextor.core.cycle_semantics.lifecycle import (
-                classify_full_cycle_semantics,
-            )
-
-            cycle_semantics = materialize_cycle_semantics(
-                path,
-                graph.hard_edges,
-                {
-                    module_id: module.path
-                    for module_id, module in modules.items()
-                },
-                index.source_fingerprints_by_module,
-            )
-
-            (
-                cycle_semantics_state,
-                cycle_semantics_invalidation_reason,
-            ) = classify_full_cycle_semantics(
-                cycle_semantics
-            )
-
-        except AnalysisCancelled:
-            raise
-
-        except Exception as exc:
-            cycle_semantics = None
-            cycle_semantics_state = "deferred"
-            cycle_semantics_invalidation_reason = None
-
-            if log:
-                log(
-                    "Warning: cycle-semantic materialization "
-                    "unavailable ("
-                    + type(exc).__name__
-                    + ")."
-                )
-
-            trace_event(
-                "FULL",
-                "CYCLE_SEMANTICS_MATERIALIZATION_ERROR",
-                status="deferred",
-                exception_class=type(exc).__name__,
-            )
-
-        finally:
-            trace_event(
-                "FULL",
-                "CYCLE_SEMANTICS_MATERIALIZATION",
-                elapsed_ms=(
-                    time.perf_counter_ns()
-                    - semantic_started_ns
-                ) / 1_000_000.0,
-                status=cycle_semantics_state,
-                count=(
-                    len(cycle_semantics.cyclic_modules)
-                    if cycle_semantics is not None
-                    else 0
-                ),
-                reason=(
-                    cycle_semantics_invalidation_reason
-                    or "NONE"
-                ),
-            )
+
+        cycle_semantics = None
+        cycle_semantics_state = "deferred"
+        cycle_semantics_invalidation_reason = None
+        semantic_started_ns = time.perf_counter_ns()
+
+        try:
+            from contextor.core.cycle_semantics.materialization import (
+                materialize_cycle_semantics,
+            )
+            from contextor.core.cycle_semantics.lifecycle import (
+                classify_full_cycle_semantics,
+            )
+
+            cycle_semantics = materialize_cycle_semantics(
+                path,
+                graph.hard_edges,
+                {
+                    module_id: module.path
+                    for module_id, module in modules.items()
+                },
+                index.source_fingerprints_by_module,
+            )
+
+            (
+                cycle_semantics_state,
+                cycle_semantics_invalidation_reason,
+            ) = classify_full_cycle_semantics(
+                cycle_semantics
+            )
+
+        except AnalysisCancelled:
+            raise
+
+        except Exception as exc:
+            cycle_semantics = None
+            cycle_semantics_state = "deferred"
+            cycle_semantics_invalidation_reason = None
+
+            if log:
+                log(
+                    "Warning: cycle-semantic materialization "
+                    "unavailable ("
+                    + type(exc).__name__
+                    + ")."
+                )
+
+            trace_event(
+                "FULL",
+                "CYCLE_SEMANTICS_MATERIALIZATION_ERROR",
+                status="deferred",
+                exception_class=type(exc).__name__,
+            )
+
+        finally:
+            trace_event(
+                "FULL",
+                "CYCLE_SEMANTICS_MATERIALIZATION",
+                elapsed_ms=(
+                    time.perf_counter_ns()
+                    - semantic_started_ns
+                ) / 1_000_000.0,
+                status=cycle_semantics_state,
+                count=(
+                    len(cycle_semantics.cyclic_modules)
+                    if cycle_semantics is not None
+                    else 0
+                ),
+                reason=(
+                    cycle_semantics_invalidation_reason
+                    or "NONE"
+                ),
+            )
 
         from datetime import datetime
         datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
@@ -868,6 +868,14 @@
             reference_index=reference_index,
             test_facts_by_path=index.test_facts_by_path,
             automatic_test_dirs=index.automatic_test_dirs,
+            cycle_semantics_report_requested=True,
+            cycle_semantics_snapshot=cycle_semantics,
+            cycle_semantics_freshness=(
+                cycle_semantics_state
+            ),
+            cycle_semantics_invalidation_reason=(
+                cycle_semantics_invalidation_reason
+            ),
         )
 
         emit_stage_end("reports", reports_started)
@@ -927,7 +935,7 @@
 
             if is_collision_complete:
                 canonical_collisions = compute_collisions_from_facts(cf)
-                cf = materialize_canonical_collision_facts(cf)
+                cf = materialize_canonical_collision_facts(cf)
                 collisions_state = "fresh"
             else:
                 canonical_collisions = []
@@ -1023,20 +1031,20 @@
             )
 
             component_started = time.monotonic()
-            from contextor.core.reference.shared import (
-                validate_reexport_facts_by_module,
-            )
-            if not validate_reexport_facts_by_module(
-                canonical_reexport_facts,
-                mods,
-            ):
-                raise RuntimeError(
-                    "Canonical re-export facts do not cover the current module domain."
-                )
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
-                reexport_facts_by_module=canonical_reexport_facts,
+                reexport_facts_by_module=canonical_reexport_facts,
                 dependency_graph=graph,
                 trie=getattr(analysis_result, "trie", None),
                 package_root=getattr(analysis_result, "package_root", ""),
@@ -1062,13 +1070,13 @@
                 topology_metrics_state="fresh",
                 cycles=getattr(analysis_result, "cycles", []),
                 cycles_state="fresh",
-                cycle_semantics=cycle_semantics,
-                cycle_semantics_state=(
-                    cycle_semantics_state
-                ),
-                cycle_semantics_invalidation_reason=(
-                    cycle_semantics_invalidation_reason
-                ),
+                cycle_semantics=cycle_semantics,
+                cycle_semantics_state=(
+                    cycle_semantics_state
+                ),
+                cycle_semantics_invalidation_reason=(
+                    cycle_semantics_invalidation_reason
+                ),
                 collision_facts=cf if isinstance(cf, dict) else {},
                 collisions=canonical_collisions,
                 collisions_state=collisions_state,
@@ -1084,15 +1092,15 @@
                 shared_usage_clusters_state="deferred",
             )
 
-            if getattr(analysis_result, "resync_required", False):
-                state.resync_required = True
-
-            from contextor.core.analysis.incremental.materialization import (
-                ensure_cached_analytics,
-            )
-
-            ensure_cached_analytics(state)
-
+            if getattr(analysis_result, "resync_required", False):
+                state.resync_required = True
+
+            from contextor.core.analysis.incremental.materialization import (
+                ensure_cached_analytics,
+            )
+
+            ensure_cached_analytics(state)
+
             emit_stage_component_end(
                 "canonical_materialization",
                 "state_construction",
@@ -1238,11 +1246,11 @@
                     if client is not None:
                         component_started = time.monotonic()
                         try:
-                            published = client.publish(
-                                state,
-                                origin=origin,
-                                acknowledge_installed=True,
-                            )
+                            published = client.publish(
+                                state,
+                                origin=origin,
+                                acknowledge_installed=True,
+                            )
                         finally:
                             publish_ms = (time.monotonic() - component_started) * 1000.0
                         component_started = time.monotonic()
@@ -1252,20 +1260,20 @@
                             and published.get("revision") is not None
                         ):
                             live_publish_revision = int(published["revision"])
-                            if published.get("resync_required") is True:
-                                live_publish_status = "recovery_required"
-                                live_publish_warning = (
-                                    published.get("warning")
-                                    or "LIVE recovery verification required."
-                                )
-                            else:
-                                live_publish_status = "success"
-                                live_publish_warning = (
-                                    "LIVE generation was already installed; "
-                                    "event origin is not verified."
-                                    if published.get("already_installed") is True
-                                    else None
-                                )
+                            if published.get("resync_required") is True:
+                                live_publish_status = "recovery_required"
+                                live_publish_warning = (
+                                    published.get("warning")
+                                    or "LIVE recovery verification required."
+                                )
+                            else:
+                                live_publish_status = "success"
+                                live_publish_warning = (
+                                    "LIVE generation was already installed; "
+                                    "event origin is not verified."
+                                    if published.get("already_installed") is True
+                                    else None
+                                )
                         else:
                             live_publish_status = "failed"
                             live_publish_revision = None
@@ -1399,45 +1407,45 @@
             result=f"total_ms={total_ms:.3f}",
         )
         return errors, analysis_result
-
-    @staticmethod
-    def analyze_layer(
-        root_dir: str,
-        layer_dir: str,
-        log=None,
-        progress_callback=None,
-        additional_excludes: list[str] | None = None,
-    ) -> str:
-        from contextor.core.analysis.full_analysis_lease import (
-            acquire_full_analysis,
-            release_full_analysis,
-        )
-
-        root_resolved, _ = _resolve_repository_target(
-            root_dir,
-            layer_dir,
-            target_kind="layer",
-        )
-
-        lease = acquire_full_analysis(
-            root_resolved,
-            owner="scoped_layer_analysis",
-            writer_kind="scoped_analysis",
-            timeout=10.0,
-        )
-        try:
-            return ContextorFacade._analyze_layer_uncoordinated(
-                root_dir,
-                layer_dir,
-                log=log,
-                progress_callback=progress_callback,
-                additional_excludes=additional_excludes,
-            )
-        finally:
-            release_full_analysis(lease)
-
-    @staticmethod
-    def _analyze_layer_uncoordinated(
+
+    @staticmethod
+    def analyze_layer(
+        root_dir: str,
+        layer_dir: str,
+        log=None,
+        progress_callback=None,
+        additional_excludes: list[str] | None = None,
+    ) -> str:
+        from contextor.core.analysis.full_analysis_lease import (
+            acquire_full_analysis,
+            release_full_analysis,
+        )
+
+        root_resolved, _ = _resolve_repository_target(
+            root_dir,
+            layer_dir,
+            target_kind="layer",
+        )
+
+        lease = acquire_full_analysis(
+            root_resolved,
+            owner="scoped_layer_analysis",
+            writer_kind="scoped_analysis",
+            timeout=10.0,
+        )
+        try:
+            return ContextorFacade._analyze_layer_uncoordinated(
+                root_dir,
+                layer_dir,
+                log=log,
+                progress_callback=progress_callback,
+                additional_excludes=additional_excludes,
+            )
+        finally:
+            release_full_analysis(lease)
+
+    @staticmethod
+    def _analyze_layer_uncoordinated(
         root_dir: str,
         layer_dir: str,
         log=None,
@@ -1456,18 +1464,18 @@
         progress.begin("Initializing repository identity")
         registry = _initialize_repository_identity(root_resolved)
         reset_caches()
-
-        if log:
-            log(f"Processing layer '{layer_name}' in project '{repo_name}'...")
+
+        if log:
+            log(f"Processing layer '{layer_name}' in project '{repo_name}'...")
         excludes, extra_dirs = _analysis_filters(
             str(root_resolved), additional_excludes
         )
         from contextor.core.graph.resolver import build_trie, detect_package_root
 
         collision_facts = None
-        authoritative_state = resolve_authoritative_repository_state(
-            root_resolved, _lease_held=True
-        )
+        authoritative_state = resolve_authoritative_repository_state(
+            root_resolved, _lease_held=True
+        )
         if authoritative_state is not None:
             progress.begin("Loading canonical LIVE context")
             state = authoritative_state.state
@@ -1499,13 +1507,13 @@
                 progress_callback=index_progress,
             )
             modules = index.modules
-            from contextor.core.reference.shared import (
-                materialize_reexport_facts_by_module,
-            )
-            canonical_reexport_facts = materialize_reexport_facts_by_module(
-                modules,
-                index.reference_facts_by_module,
-            )
+            from contextor.core.reference.shared import (
+                materialize_reexport_facts_by_module,
+            )
+            canonical_reexport_facts = materialize_reexport_facts_by_module(
+                modules,
+                index.reference_facts_by_module,
+            )
             trie = build_trie(modules.keys())
             package_root = detect_package_root(modules, trie)
             progress.begin("Resolving dependency graph")
@@ -1517,9 +1525,9 @@
                     trie=trie,
                     package_root=package_root,
                     progress_callback=graph_progress,
-                    reexport_facts_by_module=canonical_reexport_facts,
+                    reexport_facts_by_module=canonical_reexport_facts,
                 ),
-                reexport_facts_by_module=canonical_reexport_facts,
+                reexport_facts_by_module=canonical_reexport_facts,
             )
             skipped_files = getattr(index, "skipped", [])
             reference_index = assemble_reference_index_or_fallback(
@@ -1530,9 +1538,9 @@
             collision_facts = _assemble_layer_collision_facts(
                 modules, indexed_facts=index.collision_facts_by_module
             )
-
-        if log:
-            log("Calculating metrics and collisions for the full project...")
+
+        if log:
+            log("Calculating metrics and collisions for the full project...")
         metrics_progress = progress.begin("Computing metrics, cycles and debt")
         metrics, cycles, all_collisions, debt = _compute_metrics_and_debt(
             modules,
@@ -1540,21 +1548,21 @@
             progress_callback=metrics_progress,
             collision_facts=collision_facts,
         )
-
-        runtime = {"cache_hit": cache_hit}
-
-        if log:
-            log("Preparing data structures for slicing...")
+
+        runtime = {"cache_hit": cache_hit}
+
+        if log:
+            log("Preparing data structures for slicing...")
         progress.begin("Preparing report data structures")
         hotspots = detect_hotspots(graph.hard_edges)
-        global_summary = generate_summary_report(
-            metrics,
-            cycles,
-            debt,
-            collisions=all_collisions,
-            hotspots=hotspots,
-        )
-        global_structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
+        global_summary = generate_summary_report(
+            metrics,
+            cycles,
+            debt,
+            collisions=all_collisions,
+            hotspots=hotspots,
+        )
+        global_structure = generate_structure_report(graph.hard_edges, graph.soft_edges)
         artifacts_progress = progress.begin("Preparing artifact usage")
         if authoritative_state is not None:
             checkpoint(artifacts_progress, "Projecting canonical artifacts", 0, 1)
@@ -1570,47 +1578,47 @@
                 symbol_facts_by_module=getattr(index, "symbol_facts_by_module", None),
                 reference_index=reference_index,
             )
-        
+        
         from contextor.core.reporting_engine.dictionary import IndexDictionary
-        
+        
         progress.begin("Compacting and slicing layer reports")
         with registry.transaction():
-            index_dict = IndexDictionary(registry)
-            global_compact_artifacts = compact_artifact_report(global_artifacts, index_dict)
-
-            if log:
-                log(f"Slicing reports for layer: {layer_name}...")
-
-            # Build report_header once — same header for global summary and layer reports.
-            report_header = build_report_header(str(root_resolved), "global")
-            
-            layer_sliced_reports = slice_report_for_layer(
-            layer_path=str(layer_resolved),
-            root_path=str(root_resolved),
-            global_metrics=metrics,
-            global_structure=global_structure,
-            global_summary=global_summary,
-            global_artifacts=global_artifacts,
-            global_compact_artifacts=global_compact_artifacts,
-            global_hotspots=hotspots,
-            global_cycles=cycles,
-            global_collisions=all_collisions,
+            index_dict = IndexDictionary(registry)
+            global_compact_artifacts = compact_artifact_report(global_artifacts, index_dict)
+
+            if log:
+                log(f"Slicing reports for layer: {layer_name}...")
+
+            # Build report_header once — same header for global summary and layer reports.
+            report_header = build_report_header(str(root_resolved), "global")
+            
+            layer_sliced_reports = slice_report_for_layer(
+            layer_path=str(layer_resolved),
+            root_path=str(root_resolved),
+            global_metrics=metrics,
+            global_structure=global_structure,
+            global_summary=global_summary,
+            global_artifacts=global_artifacts,
+            global_compact_artifacts=global_compact_artifacts,
+            global_hotspots=hotspots,
+            global_cycles=cycles,
+            global_collisions=all_collisions,
             global_skipped_files=skipped_files,
-            report_header=report_header,
-            index_dict=index_dict,
-        )
-
-        if log:
-            log(f"Saving 5 layer reports for '{layer_name}'...")
-            
-        from datetime import datetime
-        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
-        
+            report_header=report_header,
+            index_dict=index_dict,
+        )
+
+        if log:
+            log(f"Saving 5 layer reports for '{layer_name}'...")
+            
+        from datetime import datetime
+        datestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
+        
         from contextor.core.reporting_engine.layer_pipeline import (
             execute_layer_pipeline,
         )
-        from contextor.core.reporting_engine.io_manager import write_layer_reports
-        
+        from contextor.core.reporting_engine.io_manager import write_layer_reports
+        
         progress.begin("Writing layer report bundle")
         execute_layer_pipeline(
             repo_name,
@@ -1627,76 +1635,76 @@
             datestamp=datestamp,
             log=log,
         )
-
-        # Absolute, so what the GUI shows the user is a path that exists.
-        pattern = str(output_dir() / f"{repo_name}_{layer_name}_*.json")
-
+
+        # Absolute, so what the GUI shows the user is a path that exists.
+        pattern = str(output_dir() / f"{repo_name}_{layer_name}_*.json")
+
         progress.begin("Finalizing layer analysis")
         progress.finish()
         if log:
-            log(f"Finished! Saved reports package: {pattern}")
-        return pattern
-
-    @staticmethod
-    def analyze_single_file(
-        file_path: str,
-        repo_root: str,
-        log=None,
-        progress_callback=None,
-        additional_excludes: list[str] | None = None,
-        publication_result: dict[str, Any] | None = None,
-    ) -> str:
-        if publication_result is not None:
-            publication_result.update(
-                status="not_attempted",
-                revision=None,
-                warning=None,
-            )
-        from contextor.core.analysis.full_analysis_lease import (
-            acquire_full_analysis,
-            release_full_analysis,
-        )
-
-        root_resolved, target = _resolve_repository_target(
-            repo_root,
-            file_path,
-            target_kind="file",
-        )
-        if target.suffix.lower() != ".py":
-            raise ValueError(
-                f"Selected file is not a Python file: {target}"
-            )
-
-        lease = acquire_full_analysis(
-            root_resolved,
-            owner="scoped_single_file_analysis",
-            writer_kind="scoped_analysis",
-            timeout=10.0,
-        )
-        try:
-            return ContextorFacade._analyze_single_file_uncoordinated(
-                file_path,
-                repo_root,
-                log=log,
-                progress_callback=progress_callback,
-                additional_excludes=additional_excludes,
-                publication_result=publication_result,
-            )
-        finally:
-            release_full_analysis(lease)
-
-    @staticmethod
-    def _analyze_single_file_uncoordinated(
+            log(f"Finished! Saved reports package: {pattern}")
+        return pattern
+
+    @staticmethod
+    def analyze_single_file(
         file_path: str,
         repo_root: str,
         log=None,
         progress_callback=None,
         additional_excludes: list[str] | None = None,
-        publication_result: dict[str, Any] | None = None,
+        publication_result: dict[str, Any] | None = None,
+    ) -> str:
+        if publication_result is not None:
+            publication_result.update(
+                status="not_attempted",
+                revision=None,
+                warning=None,
+            )
+        from contextor.core.analysis.full_analysis_lease import (
+            acquire_full_analysis,
+            release_full_analysis,
+        )
+
+        root_resolved, target = _resolve_repository_target(
+            repo_root,
+            file_path,
+            target_kind="file",
+        )
+        if target.suffix.lower() != ".py":
+            raise ValueError(
+                f"Selected file is not a Python file: {target}"
+            )
+
+        lease = acquire_full_analysis(
+            root_resolved,
+            owner="scoped_single_file_analysis",
+            writer_kind="scoped_analysis",
+            timeout=10.0,
+        )
+        try:
+            return ContextorFacade._analyze_single_file_uncoordinated(
+                file_path,
+                repo_root,
+                log=log,
+                progress_callback=progress_callback,
+                additional_excludes=additional_excludes,
+                publication_result=publication_result,
+            )
+        finally:
+            release_full_analysis(lease)
+
+    @staticmethod
+    def _analyze_single_file_uncoordinated(
+        file_path: str,
+        repo_root: str,
+        log=None,
+        progress_callback=None,
+        additional_excludes: list[str] | None = None,
+        publication_result: dict[str, Any] | None = None,
     ) -> str:
         """Analyzes a single file within the context of a project. Returns report output path."""
-        if publication_result is not None:
-            publication_result.update(status="not_attempted", revision=None, warning=None)
+        if publication_result is not None:
+            publication_result.update(status="not_attempted", revision=None, warning=None)
         progress = _StagedProgress(progress_callback, total_stages=11, log=log)
         progress.begin("Validating repository and file scope")
         root_resolved, file = _resolve_repository_target(
@@ -1708,9 +1716,9 @@
         registry = _initialize_repository_identity(root_resolved)
         repo_root = str(registry.repo_path.resolve())
         reset_caches()
-        if log:
-            log(f"Single file analysis: {file.name}")
-
+        if log:
+            log(f"Single file analysis: {file.name}")
+
         if log:
             log("Preparing project context...")
         excludes, extra_dirs = _analysis_filters(repo_root, additional_excludes)
@@ -1718,9 +1726,9 @@
         analysis_state = None
         state_only = False
 
-        resolved = resolve_authoritative_repository_state(
-            repo_root, _lease_held=True
-        )
+        resolved = resolve_authoritative_repository_state(
+            repo_root, _lease_held=True
+        )
 
         if resolved is not None:
             state = resolved.state
@@ -1772,7 +1780,7 @@
                         )
 
         if not state_only:
-            hydrated = hydrate_repository_engine(repo_root, _lease_held=True)
+            hydrated = hydrate_repository_engine(repo_root, _lease_held=True)
 
         if state_only:
             pass
@@ -1796,38 +1804,38 @@
             cache_hit = True
             if update_result.status == "UPDATED" and hydrated.client is not None:
                 try:
-                    published = hydrated.client.publish(
+                    published = hydrated.client.publish(
                         analysis_state,
                         origin="scoped_analysis",
                         timeout=5.0,
-                        acknowledge_installed=True,
+                        acknowledge_installed=True,
                     )
-                    if isinstance(published, dict) and published.get("status") == "ok":
-                        if published.get("resync_required") is True:
-                            status = "recovery_required"
-                            warning = published.get("warning") or "LIVE recovery verification required."
-                        else:
-                            status = "success"
-                            warning = (
-                                "LIVE generation was already installed; "
-                                "event origin is not verified."
-                                if published.get("already_installed") is True
-                                else None
-                            )
-                        revision = int(published["revision"]) if published.get("revision") is not None else None
-                    else:
-                        status = "failed"
-                        revision = None
-                        warning = (
-                            published.get("error") if isinstance(published, dict) else None
-                        ) or "Canonical LIVE service rejected publication."
-                    if publication_result is not None:
-                        publication_result.update(status=status, revision=revision, warning=warning)
-                    if status in {"failed", "recovery_required"} and log:
-                        log(f"[WARNING] Single-file LIVE publication: {warning}")
-                except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError) as exc:
-                    if publication_result is not None:
-                        publication_result.update(status="failed", revision=None, warning=f"{type(exc).__name__}: {exc}")
+                    if isinstance(published, dict) and published.get("status") == "ok":
+                        if published.get("resync_required") is True:
+                            status = "recovery_required"
+                            warning = published.get("warning") or "LIVE recovery verification required."
+                        else:
+                            status = "success"
+                            warning = (
+                                "LIVE generation was already installed; "
+                                "event origin is not verified."
+                                if published.get("already_installed") is True
+                                else None
+                            )
+                        revision = int(published["revision"]) if published.get("revision") is not None else None
+                    else:
+                        status = "failed"
+                        revision = None
+                        warning = (
+                            published.get("error") if isinstance(published, dict) else None
+                        ) or "Canonical LIVE service rejected publication."
+                    if publication_result is not None:
+                        publication_result.update(status=status, revision=revision, warning=warning)
+                    if status in {"failed", "recovery_required"} and log:
+                        log(f"[WARNING] Single-file LIVE publication: {warning}")
+                except (TimeoutError, OSError, EOFError, ConnectionError, RuntimeError) as exc:
+                    if publication_result is not None:
+                        publication_result.update(status="failed", revision=None, warning=f"{type(exc).__name__}: {exc}")
                     if log:
                         log("[WARNING] Updated single-file state could not be published to LIVE.")
             if log:
@@ -1843,28 +1851,28 @@
                 extra_ignored_dirs=extra_dirs,
                 progress_callback=index_progress,
             )
-            from contextor.core.reference.shared import (
-                materialize_reexport_facts_by_module,
-            )
-            canonical_reexport_facts = materialize_reexport_facts_by_module(modules)
+            from contextor.core.reference.shared import (
+                materialize_reexport_facts_by_module,
+            )
+            canonical_reexport_facts = materialize_reexport_facts_by_module(modules)
             graph_progress = progress.begin("Resolving dependency graph")
             graph, cache_hit = get_cached_graph(
                 modules,
-                lambda m: build_graph(
-                    m,
-                    progress_callback=graph_progress,
-                    reexport_facts_by_module=canonical_reexport_facts,
-                ),
-                reexport_facts_by_module=canonical_reexport_facts,
-            )
-
-        if log:
-            log("Generating global report (hotspots)...")
+                lambda m: build_graph(
+                    m,
+                    progress_callback=graph_progress,
+                    reexport_facts_by_module=canonical_reexport_facts,
+                ),
+                reexport_facts_by_module=canonical_reexport_facts,
+            )
+
+        if log:
+            log("Generating global report (hotspots)...")
         progress.begin("Generating global context")
         global_report = generate_report(graph, modules=modules, runtime={"cache_hit": cache_hit})
-
-        if log:
-            log("Fetching deep context for file...")
+
+        if log:
+            log("Fetching deep context for file...")
         progress.begin("Collecting deep file context")
         ctx = collect_all_contexts(
             file_path,
@@ -1888,16 +1896,16 @@
         with registry.transaction():
             index_dict = IndexDictionary(registry)
             report = generate_single_file_report(ctx, len(modules), index_dict=index_dict)
-
-        # Named after the module path, not the bare stem: two files called
-        # 'engine.py' in different packages used to overwrite each other.
-        try:
-            relative = file.resolve().relative_to(Path(repo_root).resolve())
-            slug = ".".join(relative.with_suffix("").parts)
-        except ValueError:
-            slug = file.stem
-
-        output = str(output_dir() / f"single_{slug}.json")
+
+        # Named after the module path, not the bare stem: two files called
+        # 'engine.py' in different packages used to overwrite each other.
+        try:
+            relative = file.resolve().relative_to(Path(repo_root).resolve())
+            slug = ".".join(relative.with_suffix("").parts)
+        except ValueError:
+            slug = file.stem
+
+        output = str(output_dir() / f"single_{slug}.json")
         from contextor.core.reporting_engine.dictionary import compact_recursively
         progress.begin("Writing JSON report snapshots")
         compact_report = compact_recursively(
@@ -1911,14 +1919,14 @@
         snapshot_dir = output_dir() / f"{Path(repo_root).resolve().name}_{datestamp}"
         snapshot_json = snapshot_dir / f"single_{slug}.json"
         save_single_file_report(compact_report, str(snapshot_json))
-
-
-
+
+
+
         # Graph analytics for the single analyzed module
         progress.begin("Generating graph analytics")
-        from contextor.core.reporting_engine.graph_analytics import generate_graph_analytics_report
-        from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report as _gen_art
-        try:
+        from contextor.core.reporting_engine.graph_analytics import generate_graph_analytics_report
+        from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report as _gen_art
+        try:
             if analysis_state is not None:
                 sf_artifact_data = canonical_artifact_report(
                     analysis_state.artifacts
@@ -1930,32 +1938,32 @@
                     runtime={"cache_hit": cache_hit},
                     progress_callback=progress.items,
                 )
-            target_module_id = None
-            # Find module_id matching the analyzed file
-            file_resolved = file.resolve()
-            for mid, mod in modules.items():
-                mod_path = Path(getattr(mod, "absolute_path", None) or getattr(mod, "path", ""))
-                if mod_path.resolve() == file_resolved:
-                    target_module_id = mid
-                    break
-
-            scope_mods = {target_module_id} if target_module_id else None
-            # Include direct neighbors for useful matrix
-            if scope_mods and target_module_id:
-                from contextor.core.graph.graph import build_graph as _bg
-                hard_e = graph.hard_edges
-                neighbors = set(hard_e.get(target_module_id, []))
-                for src, tgts in hard_e.items():
-                    if target_module_id in tgts:
-                        neighbors.add(src)
-                scope_mods = {target_module_id} | neighbors
-
+            target_module_id = None
+            # Find module_id matching the analyzed file
+            file_resolved = file.resolve()
+            for mid, mod in modules.items():
+                mod_path = Path(getattr(mod, "absolute_path", None) or getattr(mod, "path", ""))
+                if mod_path.resolve() == file_resolved:
+                    target_module_id = mid
+                    break
+
+            scope_mods = {target_module_id} if target_module_id else None
+            # Include direct neighbors for useful matrix
+            if scope_mods and target_module_id:
+                from contextor.core.graph.graph import build_graph as _bg
+                hard_e = graph.hard_edges
+                neighbors = set(hard_e.get(target_module_id, []))
+                for src, tgts in hard_e.items():
+                    if target_module_id in tgts:
+                        neighbors.add(src)
+                scope_mods = {target_module_id} | neighbors
+
             ga_data = generate_graph_analytics_report(
-                artifact_data=sf_artifact_data,
-                hard_edges=graph.hard_edges,
-                soft_edges=graph.soft_edges,
-                modules=modules,
-                index_dict=index_dict,
+                artifact_data=sf_artifact_data,
+                hard_edges=graph.hard_edges,
+                soft_edges=graph.soft_edges,
+                modules=modules,
+                index_dict=index_dict,
                 scope="single_file",
                 scope_modules=scope_mods,
                 progress_callback=progress.items,
@@ -1971,10 +1979,10 @@
                 encoding="utf-8",
             ) as f_ga:
                 _json.dump(ga_data, f_ga, indent=2, ensure_ascii=False)
-        except Exception as _ga_err:
-            if log:
-                log(f"[WARNING] graph_analytics skipped for single file: {_ga_err}")
-
+        except Exception as _ga_err:
+            if log:
+                log(f"[WARNING] graph_analytics skipped for single file: {_ga_err}")
+
         progress.begin("Writing Markdown context")
         md_output = str(output_dir() / f"single_{slug}_llm_context.md")
         generate_llm_markdown(report, md_output)
@@ -1982,9 +1990,9 @@
             report,
             str(snapshot_dir / f"single_{slug}_llm_context.md"),
         )
-
+
         progress.begin("Finalizing single-file analysis")
         progress.finish()
         if log:
-            log("Single file report and MD bundle saved successfully.")
-        return output
+            log("Single file report and MD bundle saved successfully.")
+        return output
```

```diff
--- a/contextor/core/reporting_engine/pipeline.py
+++ b/contextor/core/reporting_engine/pipeline.py
@@ -23,7 +23,7 @@
 import time
 from pathlib import Path
 
-from contextor.core.errors import checkpoint
+from contextor.core.errors import AnalysisCancelled, checkpoint
 from contextor.core.program_log import log_program_event
 from contextor.core.runtime_trace import trace_event
 
@@ -53,6 +53,10 @@
     reference_index=None,
     test_facts_by_path: dict[str, dict] | None = None,
     automatic_test_dirs=None,
+    cycle_semantics_report_requested: bool = False,
+    cycle_semantics_snapshot=None,
+    cycle_semantics_freshness: str = "deferred",
+    cycle_semantics_invalidation_reason: str | None = None,
 ):
     """
     Execute the complete global report pipeline.
@@ -191,6 +195,40 @@
         root_path,
         data_source="global",
     )
+
+    semantic_report = None
+    if cycle_semantics_report_requested:
+        from contextor.core.cycle_semantics.report_projection import (
+            build_cycle_semantics_report,
+        )
+
+        try:
+            semantic_report = build_cycle_semantics_report(
+                cycle_semantics_snapshot,
+                cycle_semantics_freshness,
+                cycle_semantics_invalidation_reason,
+                report_header=report_header,
+            )
+        except AnalysisCancelled:
+            raise
+        except Exception as exc:
+            if log:
+                log(
+                    "Warning: cycle semantics report projection "
+                    "unavailable (" + type(exc).__name__ + ")."
+                )
+            trace_event(
+                "FULL",
+                "CYCLE_SEMANTICS_REPORT_PROJECTION_ERROR",
+                status="deferred",
+                exception_class=type(exc).__name__,
+            )
+            semantic_report = build_cycle_semantics_report(
+                None,
+                "deferred",
+                None,
+                report_header=report_header,
+            )
 
     # ------------------------------------------------------
     # SUMMARY
@@ -507,6 +545,8 @@
             graph_analytics_data
         ),
     }
+    if cycle_semantics_report_requested:
+        reports_data["cycle_semantics"] = semantic_report
 
     # ------------------------------------------------------
     # WRITE GLOBAL REPORTS
```

```diff
--- a/contextor/core/reporting_engine/io_manager.py
+++ b/contextor/core/reporting_engine/io_manager.py
@@ -149,3 +149,29 @@
         if snapshot_prefix:
             save_json(reports_data["summary"], f"{snapshot_prefix}_summary.json", log=log, label="summary snapshot")
             _save_markdown(_summary_markdown(f"Project report: {repo_name}", reports_data["summary"]), f"{snapshot_prefix}_summary.md")
+
+    if "cycle_semantics" in reports_data:
+        try:
+            save_json(
+                reports_data["cycle_semantics"],
+                f"output/{repo_name}_cycle_semantics.json",
+                log=log,
+                label="cycle semantics report",
+            )
+
+            if snapshot_prefix:
+                save_json(
+                    reports_data["cycle_semantics"],
+                    f"{snapshot_prefix}_cycle_semantics.json",
+                    log=log,
+                    label="cycle semantics snapshot",
+                )
+
+        except Exception as exc:
+            if log:
+                log(
+                    "Warning: cycle semantics report "
+                    "write failed ("
+                    + type(exc).__name__
+                    + ")."
+                )
```

```diff
--- a/tests/test_cycle_semantics_full_integration.py
+++ b/tests/test_cycle_semantics_full_integration.py
@@ -3,6 +3,7 @@
 from __future__ import annotations
 
 import hashlib
+import json
 from dataclasses import replace
 from pathlib import Path
 from time import perf_counter_ns
@@ -295,4 +296,143 @@
     assert reports
     assert state.cycles_state == "fresh" and state.cycles
     assert result.cycles == state.cycles
-    assert all("cycle_semantics" not in report.read_text(encoding="utf-8") for report in reports)
+    legacy_reports = [
+        report for report in reports
+        if not report.name.endswith("_cycle_semantics.json")
+    ]
+    assert legacy_reports
+    assert all(
+        "cycle_semantics" not in report.read_text(encoding="utf-8")
+        for report in legacy_reports
+    )
+    assert (output / "repo_cycle_semantics.json").is_file()
+    assert (output / "repo_structure.json").is_file()
+    assert (output / "repo_name_collisions.json").is_file()
+    assert (output / "repo_summary.json").is_file()
+
+
+def _semantic_report_paths(root: Path) -> tuple[Path, Path]:
+    output = root.parent / "output"
+    canonical = output / "repo_cycle_semantics.json"
+    dated = list(output.glob("repo_*/repo_cycle_semantics.json"))
+    assert len(dated) == 1
+    return canonical, dated[0]
+
+
+def test_d4a_full_writes_semantic_report(pair_repo) -> None:
+    state, _ = _run_full(pair_repo)
+    canonical, dated = _semantic_report_paths(pair_repo)
+    assert canonical.is_file() and dated.is_file()
+    report = json.loads(canonical.read_text(encoding="utf-8"))
+    snapshot_report = json.loads(dated.read_text(encoding="utf-8"))
+    assert report["semantic_evidence"] == snapshot_report["semantic_evidence"]
+    assert report["projection"] == snapshot_report["projection"]
+    assert report["report_header"]
+    assert report["semantic_evidence"]["graph_sha256"] == state.cycle_semantics.graph_sha256
+    assert report["semantic_evidence"]["source_fingerprints"] == [
+        {"module_id": module, "sha256": digest}
+        for module, digest in state.cycle_semantics.observed_source_fingerprints
+    ]
+    assert report["projection"]["summary"]["cyclic_scc_total"] == 1
+    assert report["publication_binding"] == {
+        "status": "UNVERIFIED_REPORT_VS_CANONICAL_LIVE",
+        "canonical_revision": None,
+        "live_revision": None,
+    }
+
+
+def test_d4a_materialization_failure_report_is_unavailable(pair_repo, monkeypatch) -> None:
+    def fail(*args, **kwargs):
+        raise ValueError("synthetic materialization failure")
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.materialization.materialize_cycle_semantics", fail,
+    )
+    state, _ = _run_full(pair_repo)
+    canonical, _ = _semantic_report_paths(pair_repo)
+    report = json.loads(canonical.read_text(encoding="utf-8"))
+    assert state.cycles_state == "fresh" and state.cycles
+    assert state.cycle_semantics is None
+    assert report["status"] == "unavailable"
+    assert report["semantic_evidence"]["available"] is False
+    assert report["projection"] is None
+
+
+def test_d4a_report_does_not_rematerialize(pair_repo, monkeypatch) -> None:
+    import contextor.core.cycle_semantics.materialization as materialization
+    original = materialization.materialize_cycle_semantics
+    calls = []
+    def counted(*args, **kwargs):
+        calls.append(1)
+        return original(*args, **kwargs)
+    monkeypatch.setattr(materialization, "materialize_cycle_semantics", counted)
+    state, _ = _run_full(pair_repo)
+    canonical, _ = _semantic_report_paths(pair_repo)
+    assert len(calls) == 1
+    assert state.cycle_semantics is not None
+    assert json.loads(canonical.read_text(encoding="utf-8"))["status"] == "ok"
+
+
+def test_d4a_report_is_historical_after_incremental_edit(pair_repo) -> None:
+    state, _ = _run_full(pair_repo)
+    assert state.cycle_semantics_state == "fresh"
+    canonical, _ = _semantic_report_paths(pair_repo)
+    before = canonical.read_bytes()
+    hydrated = hydrate_repository_engine(pair_repo)
+    assert hydrated is not None
+    engine = hydrated.engine
+    source = pair_repo / "pkg" / "a.py"
+    source.write_text("import pkg.b\ndef fa():\n    return 10\n", encoding="utf-8")
+    engine.update_file(str(source.resolve()))
+    assert engine.state.cycle_semantics_state == "stale"
+    assert canonical.read_bytes() == before
+    report = json.loads(before)
+    assert report["semantic_evidence"]["freshness_at_report_generation"] == "fresh"
+    assert report["publication_binding"]["status"] == "UNVERIFIED_REPORT_VS_CANONICAL_LIVE"
+
+
+def test_d4a_optional_report_projection_failure(pair_repo, monkeypatch) -> None:
+    import contextor.core.cycle_semantics.materialization as materialization
+    original = materialization.materialize_cycle_semantics
+    calls = []
+    def counted(*args, **kwargs):
+        calls.append(1)
+        return original(*args, **kwargs)
+    def fail_projection(*args, **kwargs):
+        raise RuntimeError("synthetic projection failure")
+    monkeypatch.setattr(materialization, "materialize_cycle_semantics", counted)
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.report_projection.project_cycle_semantics",
+        fail_projection,
+    )
+    state, _ = _run_full(pair_repo)
+    canonical, _ = _semantic_report_paths(pair_repo)
+    report = json.loads(canonical.read_text(encoding="utf-8"))
+    assert len(calls) == 1
+    assert state.cycles_state == "fresh" and state.cycles
+    assert report["status"] == "projection_unavailable"
+    assert report["projection"] is None
+    assert report["semantic_evidence"]["available"] is True
+    assert (pair_repo.parent / "output" / "repo_structure.json").is_file()
+
+
+def test_d4a_optional_report_write_failure_preserves_legacy_reports(
+    pair_repo, monkeypatch,
+) -> None:
+    import contextor.core.reporting_engine.io_manager as io_manager
+
+    original = io_manager.save_json
+
+    def fail_semantic_only(data, path, **kwargs):
+        if str(path).endswith("_cycle_semantics.json"):
+            raise OSError("synthetic semantic report write failure")
+        return original(data, path, **kwargs)
+
+    monkeypatch.setattr(io_manager, "save_json", fail_semantic_only)
+    state, result = _run_full(pair_repo)
+    output = pair_repo.parent / "output"
+    assert state.cycles_state == "fresh" and state.cycles
+    assert state.cycle_semantics_state == "fresh"
+    assert result.cycles == state.cycles
+    assert (output / "repo_structure.json").is_file()
+    assert (output / "repo_summary.json").is_file()
+    assert not (output / "repo_cycle_semantics.json").exists()
```

```diff
--- /dev/null
+++ b/contextor/core/cycle_semantics/report_projection.py
@@ -0,0 +1,185 @@
+"""Historical FULL report projection for cycle semantics.
+
+This module consumes canonical immutable evidence.
+It performs no source reads, AST parsing, graph
+construction, LIVE access or persistence.
+
+A completed report is not an atomic certificate
+of the subsequently published LIVE revision.
+"""
+
+from __future__ import annotations
+
+from contextor.core.errors import AnalysisCancelled
+
+from .contracts import CycleSemanticsSnapshot
+from .public_projection import project_cycle_semantics
+
+
+CYCLE_SEMANTICS_REPORT_SCHEMA_VERSION = "1.0.0"
+
+REPORT_LIVE_BINDING_STATUS = (
+    "UNVERIFIED_REPORT_VS_CANONICAL_LIVE"
+)
+
+
+def build_cycle_semantics_report(
+    snapshot: CycleSemanticsSnapshot | None,
+    freshness: str,
+    invalidation_reason: str | None,
+    *,
+    report_header: dict,
+) -> dict:
+    """Project one FULL semantic result as historical evidence."""
+
+    if type(report_header) is not dict:
+        raise TypeError(
+            "report_header must be a dictionary"
+        )
+
+    if freshness not in (
+        "fresh",
+        "stale",
+        "deferred",
+    ):
+        raise ValueError(
+            "Unsupported semantic freshness state"
+        )
+
+    if snapshot is not None and type(snapshot) is not (
+        CycleSemanticsSnapshot
+    ):
+        raise TypeError(
+            "Expected CycleSemanticsSnapshot"
+        )
+
+    if snapshot is None and (
+        freshness != "deferred"
+        or invalidation_reason is not None
+    ):
+        raise ValueError(
+            "Missing semantic evidence cannot be certified"
+        )
+
+    if (
+        freshness == "fresh"
+        and invalidation_reason is not None
+    ):
+        raise ValueError(
+            "Fresh semantic evidence cannot have an invalidation reason"
+        )
+
+    evidence = {
+        "available": snapshot is not None,
+        "freshness_at_report_generation": freshness,
+        "invalidation_reason": invalidation_reason,
+        "snapshot_schema_version": (
+            snapshot.schema_version
+            if snapshot is not None
+            else None
+        ),
+        "graph_sha256": (
+            snapshot.graph_sha256
+            if snapshot is not None
+            else None
+        ),
+        "cyclic_module_count": (
+            snapshot.cyclic_module_count
+            if snapshot is not None
+            else None
+        ),
+        "observed_source_count": (
+            snapshot.observed_source_count
+            if snapshot is not None
+            else None
+        ),
+        "unobserved_source_count": (
+            snapshot.unobserved_source_count
+            if snapshot is not None
+            else None
+        ),
+        "coverage_status": (
+            snapshot.coverage_status
+            if snapshot is not None
+            else None
+        ),
+        "source_snapshot_binding": (
+            snapshot.source_snapshot_binding
+            if snapshot is not None
+            else None
+        ),
+        "runtime_execution_status": (
+            snapshot.runtime_execution_status
+            if snapshot is not None
+            else None
+        ),
+        "source_fingerprints": (
+            [
+                {
+                    "module_id": module,
+                    "sha256": digest,
+                }
+                for module, digest in (
+                    snapshot.observed_source_fingerprints
+                )
+            ]
+            if snapshot is not None
+            else []
+        ),
+        "source_issues": (
+            [
+                {
+                    "module_id": module,
+                    "reason": reason,
+                }
+                for module, reason in snapshot.source_issues
+            ]
+            if snapshot is not None
+            else []
+        ),
+    }
+
+    result = {
+        "schema_version": (
+            CYCLE_SEMANTICS_REPORT_SCHEMA_VERSION
+        ),
+        "report_header": dict(report_header),
+        "publication_binding": {
+            "status": REPORT_LIVE_BINDING_STATUS,
+            "canonical_revision": None,
+            "live_revision": None,
+        },
+        "status": (
+            "unavailable"
+            if snapshot is None
+            else "stale"
+            if freshness == "stale"
+            else "deferred"
+            if freshness == "deferred"
+            else "partial"
+            if snapshot.coverage_status
+            == "PARTIAL_SOURCE_EVIDENCE"
+            else "ok"
+        ),
+        "semantic_evidence": evidence,
+        "projection": None,
+        "projection_error": None,
+    }
+
+    if snapshot is None:
+        return result
+
+    try:
+        result["projection"] = project_cycle_semantics(
+            snapshot.import_sites,
+            snapshot.conditional_discovery,
+        )
+    except AnalysisCancelled:
+        raise
+    except Exception as exc:
+        result["status"] = "projection_unavailable"
+        result["projection_error"] = (
+            type(exc).__name__
+        )
+
+    return result
```

```diff
--- /dev/null
+++ b/tests/test_cycle_semantics_report_projection.py
@@ -0,0 +1,212 @@
+"""Pure historical report projection from immutable cycle evidence."""
+
+from __future__ import annotations
+
+import hashlib
+import subprocess
+import sys
+from dataclasses import replace
+
+import pytest
+
+from contextor.core.cycle_semantics.conditional_discovery import ConditionalDiscoveryReport
+from contextor.core.cycle_semantics.contracts import (
+    UNVERIFIED_RUNTIME_EXECUTION,
+    UNVERIFIED_SOURCE_BINDING,
+    CycleSemanticsSnapshot,
+    fingerprint_hard_edges,
+)
+from contextor.core.cycle_semantics.edge_sites import (
+    CyclicImportSiteReport,
+    HardEdgeSiteEvidence,
+    SCCImportSiteEvidence,
+)
+from contextor.core.cycle_semantics.report_projection import (
+    REPORT_LIVE_BINDING_STATUS,
+    build_cycle_semantics_report,
+)
+from contextor.core.cycle_semantics.scc import CyclicImportComponent, ImportCycleTopology
+from contextor.core.errors import AnalysisCancelled
+
+
+HEADER = {"schema_version": "1.0", "generated_at": "synthetic-time", "data_source": "global"}
+
+
+def _snapshot(*, cyclic: bool = True) -> CycleSemanticsSnapshot:
+    if cyclic:
+        members = ("pkg.a", "pkg.b")
+        edges = (("pkg.a", "pkg.b"), ("pkg.b", "pkg.a"))
+        hard_edges = {"pkg.a": {"pkg.b"}, "pkg.b": {"pkg.a"}}
+        components = (CyclicImportComponent(
+            members=members, internal_edges=edges, kind="MULTI_NODE_SCC",
+        ),)
+        site_components = (SCCImportSiteEvidence(
+            members=members,
+            internal_edges=tuple(
+                HardEdgeSiteEvidence(source, target, "UNRESOLVED", ())
+                for source, target in edges
+            ),
+            matched_edge_count=0,
+            unresolved_edge_count=2,
+        ),)
+    else:
+        members = ()
+        edges = ()
+        hard_edges = {}
+        components = ()
+        site_components = ()
+    topology = ImportCycleTopology(
+        node_count=len(members), hard_edge_count=len(edges),
+        total_scc_count=(1 if cyclic else 0), cyclic_components=components,
+    )
+    sites = CyclicImportSiteReport(topology=topology, components=site_components)
+    discovery = ConditionalDiscoveryReport(
+        candidates=(), examined_outgoing_count=0,
+        unavailable_source_modules=(), unresolved_lexical_edge_count=len(edges),
+        coverage_status="NO_CONDITIONAL_CANDIDATES",
+    )
+    return CycleSemanticsSnapshot(
+        graph_sha256=fingerprint_hard_edges(hard_edges),
+        cyclic_modules=members,
+        observed_source_fingerprints=tuple(
+            (module, hashlib.sha256(module.encode()).hexdigest()) for module in members
+        ),
+        source_issues=(), coverage_status="FILESYSTEM_STABLE_NON_ATOMIC",
+        source_snapshot_binding=UNVERIFIED_SOURCE_BINDING,
+        runtime_execution_status=UNVERIFIED_RUNTIME_EXECUTION,
+        import_sites=sites, conditional_discovery=discovery,
+    )
+
+
+def _build(snapshot, freshness="fresh", reason=None):
+    return build_cycle_semantics_report(
+        snapshot, freshness, reason, report_header=HEADER,
+    )
+
+
+def test_complete_cycle_report_has_bounded_projection_and_evidence() -> None:
+    snapshot = _snapshot()
+    report = _build(snapshot)
+    assert report["schema_version"] == "1.0.0"
+    assert report["status"] == "ok"
+    assert report["projection"]["summary"]["cyclic_scc_total"] == 1
+    assert report["projection"]["components"]
+    assert report["semantic_evidence"]["cyclic_module_count"] == 2
+    assert report["semantic_evidence"]["observed_source_count"] == 2
+    assert report["semantic_evidence"]["source_fingerprints"] == [
+        {"module_id": module, "sha256": digest}
+        for module, digest in snapshot.observed_source_fingerprints
+    ]
+    assert report["semantic_evidence"]["graph_sha256"] == snapshot.graph_sha256
+
+
+def test_complete_empty_cycle_report_is_not_unavailable() -> None:
+    report = _build(_snapshot(cyclic=False))
+    assert report["status"] == "ok"
+    assert report["semantic_evidence"]["cyclic_module_count"] == 0
+    assert report["projection"]["summary"]["cyclic_scc_total"] == 0
+
+
+def test_missing_evidence_is_unavailable() -> None:
+    report = _build(None, "deferred")
+    assert report["status"] == "unavailable"
+    assert report["semantic_evidence"]["available"] is False
+    assert report["projection"] is None
+
+
+def test_missing_evidence_cannot_be_fresh() -> None:
+    with pytest.raises(ValueError, match="Missing semantic evidence"):
+        _build(None, "fresh")
+
+
+def test_fresh_evidence_cannot_have_invalidation_reason() -> None:
+    with pytest.raises(ValueError, match="Fresh semantic evidence"):
+        _build(_snapshot(), "fresh", "SOURCE_CHANGED")
+
+
+def test_stale_report_preserves_historical_issues() -> None:
+    original = _snapshot()
+    snapshot = replace(
+        original,
+        observed_source_fingerprints=original.observed_source_fingerprints[1:],
+        source_issues=(("pkg.a", "CANONICAL_FINGERPRINT_MISMATCH"),),
+        coverage_status="PARTIAL_SOURCE_EVIDENCE",
+    )
+    report = _build(snapshot, "stale", "SOURCE_CHANGED")
+    assert report["status"] == "stale"
+    assert report["semantic_evidence"]["available"] is True
+    assert report["semantic_evidence"]["source_issues"] == [
+        {"module_id": "pkg.a", "reason": "CANONICAL_FINGERPRINT_MISMATCH"}
+    ]
+    assert report["semantic_evidence"]["freshness_at_report_generation"] == "stale"
+
+
+def test_partial_current_report_preserves_coverage() -> None:
+    original = _snapshot()
+    snapshot = replace(
+        original,
+        observed_source_fingerprints=original.observed_source_fingerprints[1:],
+        source_issues=(("pkg.a", "SOURCE_FILE_LIMIT"),),
+        coverage_status="PARTIAL_SOURCE_EVIDENCE",
+    )
+    report = _build(snapshot)
+    assert report["status"] == "partial"
+    assert report["semantic_evidence"]["coverage_status"] == "PARTIAL_SOURCE_EVIDENCE"
+    assert report["semantic_evidence"]["unobserved_source_count"] == 1
+
+
+def test_projection_failure_preserves_evidence(monkeypatch) -> None:
+    def fail(*args, **kwargs):
+        raise RuntimeError("projection failed")
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.report_projection.project_cycle_semantics", fail,
+    )
+    snapshot = _snapshot()
+    report = _build(snapshot)
+    assert report["status"] == "projection_unavailable"
+    assert report["projection_error"] == "RuntimeError"
+    assert report["semantic_evidence"]["graph_sha256"] == snapshot.graph_sha256
+    assert report["projection"] is None
+
+
+def test_projection_cancellation_propagates(monkeypatch) -> None:
+    def cancel(*args, **kwargs):
+        raise AnalysisCancelled()
+    monkeypatch.setattr(
+        "contextor.core.cycle_semantics.report_projection.project_cycle_semantics", cancel,
+    )
+    with pytest.raises(AnalysisCancelled):
+        _build(_snapshot())
+
+
+def test_header_and_snapshot_are_not_mutated() -> None:
+    snapshot = _snapshot()
+    before = dict(HEADER)
+    report = _build(snapshot)
+    report["report_header"]["generated_at"] = "changed"
+    assert HEADER == before
+    assert snapshot.source_issues == ()
+    assert snapshot.cyclic_modules == ("pkg.a", "pkg.b")
+
+
+def test_publication_binding_is_explicitly_unverified() -> None:
+    report = _build(_snapshot())
+    assert report["publication_binding"] == {
+        "status": REPORT_LIVE_BINDING_STATUS,
+        "canonical_revision": None,
+        "live_revision": None,
+    }
+
+
+def test_report_builder_cold_import_is_isolated() -> None:
+    code = (
+        "import sys; import contextor.core.cycle_semantics.report_projection; "
+        "assert not any(name == prefix or name.startswith(prefix + '.') "
+        "for prefix in ('contextor.ui', 'contextor.repo_generator', "
+        "'contextor.mcp', 'contextor.core.live_state') for name in sys.modules)"
+    )
+    result = subprocess.run(
+        [sys.executable, "-B", "-c", code],
+        capture_output=True, text=True, check=False,
+    )
+    assert result.returncode == 0, result.stderr
```
