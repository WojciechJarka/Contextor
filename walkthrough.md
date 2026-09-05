# get_file_edit_context(mode=minimal): confirmed registry/discovery optimization

Implementation dataflow was rechecked through active Contextor MCP at LIVE revision 226 before edits. The fresh minimal path now acquires one LIVE engine, opens one PersistentIdentityRegistry.read_transaction(), projects maps and IndexCatalog from that same loaded generation, and supplies complete authoritative canonical module paths to the report_query-owned catalog projection. Missing/incomplete canonical paths retain the existing discover_module_paths fallback.

Real MCP baseline authority remains 5667 ms median (raw 8294,5489,5667); it was not replaced with a harness measurement. Focused tests validate ownership and semantics but loaded MCP code has not been restarted, so runtime performance certification is pending.

Pre child-attribution baseline: read_registries median=1751.942 ms; catalog_from_registry median=3197.546 ms; discover_module_paths median=2099.584 ms; mutating transaction median=689.334 ms. Earlier controlled experiments established catalog supplied-path semantic parity=true and delta=1816.985 ms, and shared registry projection parity=true. Post-change focused ownership assertions: fresh minimal query mutating transaction count=0, read_transaction count=1, discover_module_paths count=0, response resolved module/file parity retained. Post timing harness was not rerun because its direct in-process LIVE acquisition cannot safely attach to the active runtime; do not interpret this as certified MCP recovery.

Transaction design: read_transaction preserves lock, interrupted-transaction recovery, _load_all, repair/fail-closed behavior, then unlocks without json.dumps, temporary writes, fsync, journal, or replace. Existing transaction() is unchanged. No existing read-only accessor was found; read_transaction is the narrow owner API.

Focused pytest command:
  .venv\\Scripts\\python.exe -m pytest -q tests/mcp/tools/test_minimal_registry_read_path.py tests/test_persistent_registry.py tests/test_mcp_regressions.py -k "minimal or persistent_registry"
Result: 11 passed, 83 deselected, 1 warning in 16.03s.

LIVE evidence: get_live_events(after_revision=226) returned revision=230, continuity=continuous, resync_required=false. Revisions 227-230 were watcher-originated updates for the three production files and focused test. No MCP update_file call was made.

MCP_RESTART_REQUIRED=YES
LIVE_RESTART_REQUIRED=NO
RUNTIME_PERFORMANCE_CERTIFICATION_PENDING=YES
FILES_CHANGED=contextor/core/reporting_engine/persistent_registry.py; contextor/core/report_query.py; contextor/mcp/tools/get_file_edit_context.py; tests/mcp/tools/test_minimal_registry_read_path.py
FULL_SUITE_RUN_BY_AGENT=NO

## COMPLETE RAW UNIFIED DIFF

```diff
warning: in the working copy of 'contextor/core/report_query.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/core/reporting_engine/persistent_registry.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'contextor/mcp/tools/get_file_edit_context.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/contextor/core/report_query.py b/contextor/core/report_query.py
index accb9df..ee71d5d 100644
--- a/contextor/core/report_query.py
+++ b/contextor/core/report_query.py
@@ -53,6 +53,50 @@ class IndexCatalog:
     recovered_artifacts: Mapping[str, str] | None = None
 
 
+def registry_maps_from_state(state: Mapping[str, Any]) -> tuple[dict, dict, dict, dict]:
+    """Project registry identity maps from one already-loaded generation."""
+
+    modules = state.get("module_registry", {})
+    artifacts = state.get("artifact_registry", {})
+    return (
+        dict(modules.get("path_to_id", {})),
+        dict(modules.get("id_to_path", {})),
+        dict(artifacts.get("path_to_id", {})),
+        dict(artifacts.get("id_to_path", {})),
+    )
+
+
+def catalog_from_registry_state(
+    state: Mapping[str, Any],
+    module_paths: Mapping[str, str] | None = None,
+) -> IndexCatalog:
+    """Build an IndexCatalog from one already-loaded registry generation."""
+
+    _, modules, _, artifacts = registry_maps_from_state(state)
+    recovered_modules = {
+        str(obj_id): entry.get("path")
+        for obj_id, entry in state.get("module_recovery", {}).items()
+        if isinstance(entry, dict) and entry.get("path")
+    }
+    recovered_artifacts = {
+        str(obj_id): entry.get("name")
+        for obj_id, entry in state.get("artifact_recovery", {}).items()
+        if isinstance(entry, dict) and entry.get("name")
+    }
+    active_modules = {str(key): value for key, value in modules.items() if value}
+    return IndexCatalog(
+        modules=active_modules,
+        artifacts={str(key): value for key, value in artifacts.items() if value},
+        module_paths=(
+            dict(module_paths)
+            if module_paths is not None
+            else None
+        ),
+        recovered_modules=recovered_modules,
+        recovered_artifacts=recovered_artifacts,
+    )
+
+
 def catalog_from_registry(
     repo_path: str,
     module_paths: Mapping[str, str] | None = None,
@@ -64,32 +108,19 @@ def catalog_from_registry(
     )
 
     registry = PersistentIdentityRegistry(repo_path)
-    with registry.transaction():
-        state = registry._state
-        modules = dict(state.get("module_registry", {}).get("id_to_path", {}))
-        artifacts = dict(state.get("artifact_registry", {}).get("id_to_path", {}))
-        recovered_modules = {
-            str(obj_id): entry.get("path")
-            for obj_id, entry in state.get("module_recovery", {}).items()
-            if isinstance(entry, dict) and entry.get("path")
-        }
-        recovered_artifacts = {
-            str(obj_id): entry.get("name")
-            for obj_id, entry in state.get("artifact_recovery", {}).items()
-            if isinstance(entry, dict) and entry.get("name")
-        }
-    active_modules = {str(key): value for key, value in modules.items() if value}
+    with registry.read_transaction():
+        catalog = catalog_from_registry_state(registry._state, module_paths=module_paths)
     resolved_module_paths = (
         dict(module_paths)
         if module_paths is not None
-        else discover_module_paths(repo_path, active_modules.values())
+        else discover_module_paths(repo_path, catalog.modules.values())
     )
     return IndexCatalog(
-        modules=active_modules,
-        artifacts={str(key): value for key, value in artifacts.items() if value},
+        modules=catalog.modules,
+        artifacts=catalog.artifacts,
         module_paths=resolved_module_paths,
-        recovered_modules=recovered_modules,
-        recovered_artifacts=recovered_artifacts,
+        recovered_modules=catalog.recovered_modules,
+        recovered_artifacts=catalog.recovered_artifacts,
     )
 
 
diff --git a/contextor/core/reporting_engine/persistent_registry.py b/contextor/core/reporting_engine/persistent_registry.py
index dd2b1fe..9008bd3 100644
--- a/contextor/core/reporting_engine/persistent_registry.py
+++ b/contextor/core/reporting_engine/persistent_registry.py
@@ -254,6 +254,25 @@ class PersistentIdentityRegistry:
             self._in_transaction = False
             self._unlock()
 
+    @contextmanager
+    def read_transaction(self):
+        """Load one recovered registry generation without committing it."""
+
+        if self._in_transaction:
+            yield
+            return
+
+        self._lock()
+        self._in_transaction = True
+
+        try:
+            self._recover_transaction()
+            self._load_all()
+            yield
+        finally:
+            self._in_transaction = False
+            self._unlock()
+
     # ---- Logic Methods ----
 
     def _allocate_slot(self, kind: str) -> str:
diff --git a/contextor/mcp/tools/get_file_edit_context.py b/contextor/mcp/tools/get_file_edit_context.py
index a92d884..9cb4eb8 100644
--- a/contextor/mcp/tools/get_file_edit_context.py
+++ b/contextor/mcp/tools/get_file_edit_context.py
@@ -46,6 +46,24 @@ def _static_test_reachability(
     ]
 
 
+def _canonical_module_paths(root: Path, state, required_modules: set[str]) -> dict[str, str] | None:
+    """Return complete, repository-relative canonical paths or fail safe."""
+
+    result: dict[str, str] = {}
+    for module_name in required_modules:
+        module = (getattr(state, "modules", {}) or {}).get(module_name)
+        raw_path = getattr(module, "absolute_path", None) or getattr(module, "path", None)
+        if not raw_path:
+            return None
+        candidate = Path(raw_path)
+        try:
+            relative = candidate.resolve().relative_to(root).as_posix()
+        except ValueError:
+            return None
+        result[module_name] = relative
+    return result
+
+
 def get_file_edit_context(
     repo_path: str,
     file_path: str = "",
@@ -69,10 +87,29 @@ def get_file_edit_context(
         )
 
     # Read registries & catalog for canonical resolution
-    from contextor.core.report_query import IndexCatalog, catalog_from_registry, resolve_index_query
+    from contextor.core.report_query import IndexCatalog, catalog_from_registry, catalog_from_registry_state, registry_maps_from_state, resolve_index_query
 
-    mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
-    catalog = catalog_from_registry(str(root))
+    minimal_engine = mcp_runtime.get_or_init_engine(root) if mode == "minimal" else None
+    if mode == "minimal":
+        from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
+
+        registry = PersistentIdentityRegistry(str(root))
+        with registry.read_transaction():
+            mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = registry_maps_from_state(registry._state)
+            module_paths = None
+            if minimal_engine and not getattr(minimal_engine.state, "resync_required", False):
+                module_paths = _canonical_module_paths(root, minimal_engine.state, set(mod_id_to_path.values()))
+            catalog = catalog_from_registry_state(registry._state, module_paths=module_paths)
+            if catalog.module_paths is None:
+                catalog = catalog_from_registry(str(root))
+        if not catalog.modules:
+            # Preserve the established fail-safe path when the on-disk registry
+            # has no active generation (including isolated embedders).
+            mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
+            catalog = catalog_from_registry(str(root))
+    else:
+        mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
+        catalog = catalog_from_registry(str(root))
     if not catalog.modules and mod_id_to_path:
         catalog = IndexCatalog(
             modules=mod_id_to_path,
@@ -183,7 +220,7 @@ def get_file_edit_context(
             module_id = top["id"]
             file_path_resolved = (catalog.module_paths or {}).get(module_name) or module_name.replace(".", "/") + ".py"
 
-            engine = mcp_runtime.get_or_init_engine(root)
+            engine = minimal_engine
             if not engine or getattr(engine.state, "resync_required", False):
                 return json.dumps(
                     {
```
