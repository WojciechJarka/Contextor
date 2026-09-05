# Fallback-lock verification

DECISION=PASS

Exact active MCP source evidence: PersistentIdentityRegistry._lock opens the same .lock file and takes msvcrt.LK_LOCK on Windows; _unlock uses LK_UNLCK and closes that instance's file handle. read_transaction only treats self._in_transaction as reentrant. catalog_from_registry creates a new PersistentIdentityRegistry and opens its own read_transaction. Therefore separate same-repo instances have no explicit reentrancy mechanism; calling catalog_from_registry inside another instance's read_transaction may block on the same non-reentrant file lock.

Fallback dataflow is now: first registry instance read_transaction -> maps/catalog projection only -> lock released -> if canonical module paths unavailable/incomplete, catalog_from_registry -> second read_transaction -> discover_module_paths. There is no same-repo nested lock. Relative canonical module.path is resolved from root / candidate before repo-relative POSIX conversion; absolute paths are resolved directly and both fail safe if outside root.

Focused tests:
  .venv\Scripts\python.exe -m pytest -q tests/mcp/tools/test_minimal_registry_read_path.py tests/test_persistent_registry.py tests/test_mcp_regressions.py -k "minimal or persistent_registry"
  git diff --check
Result: 13 passed, 83 deselected, 1 warning in 12.07s; diff check passed (only CRLF warnings). Tests cover fresh fast path counts, incomplete-path fallback without concurrent nested read locks, relative canonical path from repo root, no read commit side effects, existing minimal resolution behavior, interrupted recovery and mutating transaction regressions.

LIVE evidence: get_live_events(after_revision=230) returned revisions 233-234, but continuity=gap and resync_required=true with event_retention_gap. The watcher event for the focused test is present. This is a natural retention gap, not evidence of code failure; no MCP update_file was called.

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO
RUNTIME_PERFORMANCE_CERTIFICATION_PENDING=YES
FILES_CHANGED=contextor/core/reporting_engine/persistent_registry.py; contextor/core/report_query.py; contextor/mcp/tools/get_file_edit_context.py; tests/mcp/tools/test_minimal_registry_read_path.py
FULL_SUITE_RUN_BY_AGENT=NO

## COMPLETE RAW UNIFIED DIFF

```diff
warning: in the working copy of 'contextor/mcp/tools/get_file_edit_context.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/mcp/tools/test_minimal_registry_read_path.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/mcp/tools/get_file_edit_context.py b/contextor/mcp/tools/get_file_edit_context.py
index 9cb4eb8..d4c2255 100644
--- a/contextor/mcp/tools/get_file_edit_context.py
+++ b/contextor/mcp/tools/get_file_edit_context.py
@@ -57,7 +57,8 @@ def _canonical_module_paths(root: Path, state, required_modules: set[str]) -> di
             return None
         candidate = Path(raw_path)
         try:
-            relative = candidate.resolve().relative_to(root).as_posix()
+            resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
+            relative = resolved.relative_to(root).as_posix()
         except ValueError:
             return None
         result[module_name] = relative
@@ -94,14 +95,16 @@ def get_file_edit_context(
         from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
 
         registry = PersistentIdentityRegistry(str(root))
+        needs_discovery_fallback = False
         with registry.read_transaction():
             mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = registry_maps_from_state(registry._state)
             module_paths = None
             if minimal_engine and not getattr(minimal_engine.state, "resync_required", False):
                 module_paths = _canonical_module_paths(root, minimal_engine.state, set(mod_id_to_path.values()))
             catalog = catalog_from_registry_state(registry._state, module_paths=module_paths)
-            if catalog.module_paths is None:
-                catalog = catalog_from_registry(str(root))
+            needs_discovery_fallback = catalog.module_paths is None
+        if needs_discovery_fallback:
+            catalog = catalog_from_registry(str(root))
         if not catalog.modules:
             # Preserve the established fail-safe path when the on-disk registry
             # has no active generation (including isolated embedders).
diff --git a/tests/mcp/tools/test_minimal_registry_read_path.py b/tests/mcp/tools/test_minimal_registry_read_path.py
index cea2f7c..a68cd70 100644
--- a/tests/mcp/tools/test_minimal_registry_read_path.py
+++ b/tests/mcp/tools/test_minimal_registry_read_path.py
@@ -50,3 +50,65 @@ def test_fresh_minimal_query_uses_one_read_transaction_and_no_discovery(tmp_path
     assert result["resolved_as"] == "module"
     assert result["file"] == "pkg/module.py"
     assert counts == {"read": 1, "write": 0, "discover": 0}
+
+
+def test_incomplete_canonical_paths_fallback_runs_after_first_read_lock(tmp_path, monkeypatch):
+    registry = PersistentIdentityRegistry(str(tmp_path))
+    with registry.transaction():
+        registry._state["module_registry"]["path_to_id"] = {"pkg.module": "1/1"}
+        registry._state["module_registry"]["id_to_path"] = {"1/1": "pkg.module"}
+
+    state = RepositoryAnalysisState(modules={"pkg.module": object()})
+    state.resync_required = False
+    engine = SimpleNamespace(state=state)
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+
+    active_reads = {"value": 0, "nested": False, "discover": 0}
+    original_read = PersistentIdentityRegistry.read_transaction
+
+    def tracked_read(self):
+        manager = original_read(self)
+        class Scope:
+            def __enter__(_self):
+                active_reads["value"] += 1
+                if active_reads["value"] > 1:
+                    active_reads["nested"] = True
+                return manager.__enter__()
+            def __exit__(_self, *args):
+                try:
+                    return manager.__exit__(*args)
+                finally:
+                    active_reads["value"] -= 1
+        return Scope()
+
+    monkeypatch.setattr(PersistentIdentityRegistry, "read_transaction", tracked_read)
+    monkeypatch.setattr(
+        "contextor.core.report_query.discover_module_paths",
+        lambda _root, modules: active_reads.__setitem__("discover", active_reads["discover"] + 1)
+        or {"pkg.module": "pkg/module.py"},
+    )
+
+    result = json.loads(get_file_edit_context(str(tmp_path), target="pkg.module", mode="minimal"))
+
+    assert result["status"] == "unavailable"
+    assert active_reads == {"value": 0, "nested": False, "discover": 1}
+
+
+def test_canonical_relative_path_is_resolved_from_repo_root(tmp_path, monkeypatch):
+    source = tmp_path / "pkg" / "module.py"
+    source.parent.mkdir()
+    source.write_text("x = 1\n", encoding="utf-8")
+    registry = PersistentIdentityRegistry(str(tmp_path))
+    with registry.transaction():
+        registry._state["module_registry"]["path_to_id"] = {"pkg.module": "1/1"}
+        registry._state["module_registry"]["id_to_path"] = {"1/1": "pkg.module"}
+    module = Module(module_id="pkg.module", path="pkg/module.py", absolute_path="", imports=[])
+    state = RepositoryAnalysisState(modules={"pkg.module": module})
+    state.dependency_graph = SimpleNamespace(hard_edges={}, soft_edges={})
+    state.cached_analytics_state = "deferred"
+    state.topology_metrics_state = "deferred"
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state))
+
+    result = json.loads(get_file_edit_context(str(tmp_path), target="pkg.module", mode="minimal"))
+
+    assert result["file"] == "pkg/module.py"
```
