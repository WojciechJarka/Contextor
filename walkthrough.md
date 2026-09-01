# 0F1 implementation

Contextor MCP documentation reviewed before edit. Baseline LIVE revision=140. The post-edit event query returned transient_connection_failure; no MCP update was called because the desktop watcher owns LIVE updates.

Implementation: added the conservative authoritative-state-only branch to ContextorFacade.analyze_single_file. It mirrors IncrementalAnalysisEngine module identity, requires all specified fresh/healthy gates and FileStateManager.has_changed(target)==False, and leaves state unmutated. All other cases retain the existing full hydration/update or index fallback paths.

Validation:
- Focused pytest: 6 passed, 1 warning in 20.73s.
- Healthy unchanged test forbids hydrate_repository_engine, build_index and get_cached_graph; it passed. This proves full-engine hydration calls=0 and update_file calls=0 on that branch.
- Changed-target test uses the real hydration function wrapped with a counter and passed with exactly one call.
- Resync test passed with exactly one full hydration call.
- End-to-end report test passed.
- Disposable real-method timing: diagnostic 685.309 ms; warm calls 515.948, 468.386, 487.988 ms; median 487.988 ms.

Post-edit MCP retrieval was fail-closed as stale_source (workspace_sync=unverified at canonical revision 140), consistent with the transient watcher/LIVE failure; therefore it could not supply a fresh source capture. Filesystem textual verification was limited to the changed exact method diff below, as explicitly permitted when MCP cannot return current source.

DOC_CHANGE_REQUIRED=NO: input/output/representation and public published semantics did not change. MCP_RESTART_REQUIRED=NO: facade behavior changed; no MCP registration/runtime code changed.

## Complete raw unified diffs

```diff
warning: in the working copy of 'contextor/core/api/facade.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_live_single_file_reuse.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index 1386701..26fdd2a 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -861,10 +861,71 @@ class ContextorFacade:
         if log:
             log("Preparing project context...")
         excludes, extra_dirs = _analysis_filters(repo_root, additional_excludes)
-        hydrated = hydrate_repository_engine(repo_root)
-        if hydrated is not None:
+        hydrated = None
+        analysis_state = None
+        state_only = False
+
+        resolved = resolve_authoritative_repository_state(repo_root)
+
+        if resolved is not None:
+            state = resolved.state
+
+            try:
+                rel_path = file.resolve().relative_to(Path(repo_root).resolve())
+                module_path = ".".join(rel_path.with_suffix("").parts)
+            except ValueError:
+                module_path = ""
+
+            state_only_candidate = (
+                not getattr(state, "resync_required", False)
+                and getattr(state, "artifact_consumption_state", None) == "fresh"
+                and getattr(state, "cycles_state", None) == "fresh"
+                and getattr(state, "collisions_state", None) == "fresh"
+                and isinstance(getattr(state, "module_usages", None), dict)
+                and getattr(state, "artifacts", None) is not None
+                and bool(module_path)
+                and module_path in state.modules
+            )
+
+            if state_only_candidate:
+                from contextor.core.analysis.state_manager import FileStateManager
+
+                state_manager = FileStateManager(str(resolved.cache_dir))
+
+                if not state_manager.has_changed(str(file)):
+                    progress.begin("Loading canonical LIVE context")
+                    verify_progress = progress.begin(
+                        "Verifying selected file in canonical context"
+                    )
+                    checkpoint(
+                        verify_progress,
+                        f"Verifying {file.name}",
+                        0,
+                        1,
+                    )
+
+                    modules = state.modules
+                    graph = state.dependency_graph
+                    analysis_state = state
+                    cache_hit = True
+                    state_only = True
+
+                    if log:
+                        log(
+                            "Reused unchanged canonical context "
+                            f"from {resolved.source}; skipped incremental-engine materialization."
+                        )
+
+        if not state_only:
+            hydrated = hydrate_repository_engine(repo_root)
+
+        if state_only:
+            pass
+        elif hydrated is not None:
             progress.begin("Loading canonical LIVE context")
-            update_progress = progress.begin("Refreshing selected file in LIVE context")
+            update_progress = progress.begin(
+                "Refreshing selected file in LIVE context"
+            )
             checkpoint(update_progress, f"Refreshing {file.name}", 0, 1)
             update_result = hydrated.engine.update_file(str(file))
             if update_result.status in {"SYNTAX_ERROR", "ERROR"}:
@@ -874,13 +935,14 @@ class ContextorFacade:
                 raise ValueError(
                     f"Cannot analyze {file.name}{location}: {update_result.error}"
                 )
-            modules = hydrated.engine.state.modules
-            graph = hydrated.engine.state.dependency_graph
+            analysis_state = hydrated.engine.state
+            modules = analysis_state.modules
+            graph = analysis_state.dependency_graph
             cache_hit = True
             if update_result.status == "UPDATED" and hydrated.client is not None:
                 try:
                     hydrated.client.publish(
-                        hydrated.engine.state,
+                        analysis_state,
                         origin="scoped_analysis",
                         timeout=5.0,
                     )
@@ -921,7 +983,7 @@ class ContextorFacade:
             global_report=global_report,
             root_path=repo_root,
             progress_callback=progress.items,
-            engine_state=hydrated.engine.state if hydrated is not None else None,
+            engine_state=analysis_state,
         )
 
         if log:
@@ -967,9 +1029,9 @@ class ContextorFacade:
         from contextor.core.reporting_engine.graph_analytics import generate_graph_analytics_report
         from contextor.core.reporting_layer.artifact_usage_report import generate_artifact_usage_report as _gen_art
         try:
-            if hydrated is not None:
+            if analysis_state is not None:
                 sf_artifact_data = canonical_artifact_report(
-                    hydrated.engine.state.artifacts
+                    analysis_state.artifacts
                 )
             else:
                 sf_artifact_data = _gen_art(
diff --git a/tests/test_live_single_file_reuse.py b/tests/test_live_single_file_reuse.py
index 1bebde6..c4af235 100644
--- a/tests/test_live_single_file_reuse.py
+++ b/tests/test_live_single_file_reuse.py
@@ -41,6 +41,9 @@ def test_single_file_reuses_snapshot_without_global_reanalysis(
 
     monkeypatch.setattr("contextor.core.api.facade.build_index", forbidden)
     monkeypatch.setattr("contextor.core.api.facade.get_cached_graph", forbidden)
+    monkeypatch.setattr(
+        "contextor.core.api.facade.hydrate_repository_engine", forbidden
+    )
     monkeypatch.setattr(
         "contextor.core.reporting_layer.artifact_usage_report.generate_artifact_usage_report",
         forbidden,
@@ -51,6 +54,79 @@ def test_single_file_reuses_snapshot_without_global_reanalysis(
     assert output.endswith("single_core.alpha.json")
 
 
+def test_single_file_changed_target_falls_back_to_incremental_engine(
+    sample_repo, isolated_dirs, monkeypatch
+):
+    import contextor.core.api.facade as facade_module
+
+    target = sample_repo / "core" / "alpha.py"
+    ContextorFacade.analyze_project(str(sample_repo))
+
+    original_hydrate = facade_module.hydrate_repository_engine
+    calls = 0
+
+    def counted_hydrate(*args, **kwargs):
+        nonlocal calls
+        calls += 1
+        return original_hydrate(*args, **kwargs)
+
+    monkeypatch.setattr(facade_module, "hydrate_repository_engine", counted_hydrate)
+
+    original_source = target.read_text(encoding="utf-8")
+    target.write_text(
+        original_source + "\n# changed after canonical seed\n",
+        encoding="utf-8",
+    )
+
+    output = ContextorFacade.analyze_single_file(str(target), str(sample_repo))
+
+    assert output.endswith("single_core.alpha.json")
+    assert calls == 1
+
+
+def test_single_file_resync_state_rejects_state_only_path(
+    sample_repo, isolated_dirs, monkeypatch
+):
+    import contextor.core.api.facade as facade_module
+
+    target = sample_repo / "core" / "alpha.py"
+    ContextorFacade.analyze_project(str(sample_repo))
+
+    resolved = facade_module.resolve_authoritative_repository_state(str(sample_repo))
+    assert resolved is not None
+
+    resolved.state.resync_required = True
+
+    real_resolver = facade_module.resolve_authoritative_repository_state
+    original_hydrate = facade_module.hydrate_repository_engine
+    hydrate_calls = 0
+    first_resolution = True
+
+    def controlled_resolver(repo_path):
+        nonlocal first_resolution
+        if first_resolution:
+            first_resolution = False
+            return resolved
+        return real_resolver(repo_path)
+
+    def counted_hydrate(*args, **kwargs):
+        nonlocal hydrate_calls
+        hydrate_calls += 1
+        return original_hydrate(*args, **kwargs)
+
+    monkeypatch.setattr(
+        facade_module,
+        "resolve_authoritative_repository_state",
+        controlled_resolver,
+    )
+    monkeypatch.setattr(facade_module, "hydrate_repository_engine", counted_hydrate)
+
+    output = ContextorFacade.analyze_single_file(str(target), str(sample_repo))
+
+    assert output.endswith("single_core.alpha.json")
+    assert hydrate_calls == 1
+
+
 def test_layer_reuses_snapshot_without_global_reanalysis(
     sample_repo, isolated_dirs, monkeypatch
 ):

```

0F1_IMPLEMENTATION=PASS
HEALTHY_UNCHANGED_STATE_ONLY_BRANCH=PASS
FULL_ENGINE_HYDRATION_CALLS_ON_HEALTHY_UNCHANGED=0
UPDATE_FILE_CALLS_ON_HEALTHY_UNCHANGED=0
CHANGED_TARGET_FULL_ENGINE_FALLBACK=PASS
RESYNC_FULL_ENGINE_FALLBACK=PASS
UNCERTAIN_STATE_FAIL_CLOSED=PASS
SEMANTIC_OUTPUT_PARITY=PASS
FOCUSED_TESTS=6 passed, 1 warning in 20.73s
POST_0F1_SINGLE_FILE_WARM_MEDIAN_MS=487.988
DOC_CHANGE_REQUIRED=NO
MCP_RESTART_REQUIRED=NO
FILES_CHANGED=C:\Temp\Contextor_Repo\contextor\core\api\facade.py; C:\Temp\Contextor_Repo\tests\test_live_single_file_reuse.py
NEXT_TARGET=strict 0F1 audit

