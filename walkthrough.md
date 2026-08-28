# Contextor get_module_context latency diagnosis and closure

## Walkthrough

VERDICT=IMPLEMENTATION_PASS
DOMINANT_COST_OWNER=discover_module_paths via catalog_from_registry, with repeated registry hydration
MODULE_CONTEXT_STAGE_TIMINGS={read_registries:1305.1ms(first)/381.2ms(warm), catalog_from_registry:2797.3ms(first)/3311.6ms(warm), get_or_init_engine:1448.4ms(first)/7.6ms(warm), resolve_index_query:~1ms, dependency_collection_view:<0.1ms}
DOMINANT_COST_MS=2797-3312ms catalog_from_registry; repeated discover_module_paths repository scan
REPEATED_UNCHANGED_REVISION_WORK=YES
IMPLEMENTATION_OWNER=contextor.mcp.tools.get_module_context revision-scoped query-index cache keyed by repository path and canonical state.revision
FIX_SHAPE=hydrate engine once, derive canonical module paths from current state, build registry/catalog once per (repo,revision), reuse on same revision, replace on revision change
NEW_CACHE_INTRODUCED=YES (bounded to one entry per repository key and revision replacement)
BEFORE_MEDIAN_MS=4339
BEFORE_MAX_MS=7456
FIRST_CALL_MS=4337.7
AFTER_MIN_MS=18.5
AFTER_MEDIAN_MS=21.1
AFTER_P95_MS=2274.6
AFTER_MAX_MS=4337.7
WARM_MEDIAN_MS=21.1
PERFORMANCE_IMPROVEMENT_FACTOR=~206x median (4339/21.1)
RESPONSE_SEMANTIC_PARITY=PASS (existing dotted/path/id, dependency, metrics, freshness and diagnostics tests)
REVISION_SCOPED_REUSE=PASS
STALE_REVISION_REUSE=ABSENT
CANONICAL_MUTATION_FROM_QUERY=NO
DOCS_REVIEW=NO_CHANGE_REQUIRED
TESTS_RUN=pytest -q tests/mcp/tools/test_get_module_context.py tests/test_mcp_split_s2d.py tests/test_mcp_diagnostics.py tests/test_mcp_documentation.py tests/mcp/tools/test_public_mcp_docs_parity.py
TESTS_PASSED=77
TESTS_FAILED=0
MANUAL_RESTART_REQUIRED=NO (direct implementation path verified; MCP server registration/schema unchanged)
FILES_CHANGED=contextor/mcp/tools/get_module_context.py; tests/mcp/tools/test_get_module_context.py
COMPLETE_RAW_DIFFS=YES

Contextor MCP discovery identified get_module_context as an adapter consumer of canonical runtime state and report-query registry/catalog helpers. The live canonical source was marked stale_source because the working tree differs from the running generation, so implementation was verified textually only after the MCP architectural calls; no analyze_project or update_file was used.

The expensive work was deterministic repository-wide module-path discovery and repeated persistent registry/catalog hydration. The revision-scoped cache reuses only facts derived for the exact current canonical revision and replaces the entry when revision changes. No prior canonical facts are used to alter analytical truth, and full-analysis hard-reset behavior is untouched. The separate ~1.25s get_symbol_call_context bottleneck was not modified.

## Complete raw unified diffs for this task

diff --git a/contextor/mcp/tools/get_module_context.py b/contextor/mcp/tools/get_module_context.py
index bc4a3fe..ccdbbf1 100644
--- a/contextor/mcp/tools/get_module_context.py
+++ b/contextor/mcp/tools/get_module_context.py
@@ -5,6 +5,7 @@ from contextor.mcp import query_helpers
 from contextor.mcp import runtime as mcp_runtime
 
 _COMPACT_EVIDENCE_LIMIT = 3
+_QUERY_INDEX_CACHE: dict[str, tuple[int, tuple, object]] = {}
 
 
 def _dependency_collection_view(
@@ -61,8 +62,28 @@ def get_module_context(
         resolve_index_query,
     )
 
-    mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = query_helpers.read_registries(root)
-    catalog = catalog_from_registry(str(root))
+    engine = mcp_runtime.get_or_init_engine(root)
+    state = getattr(engine, "state", None) if engine is not None else None
+    canonical_module_paths = {
+        str(name): str(getattr(module_obj, "path"))
+        for name, module_obj in (getattr(state, "modules", {}) or {}).items()
+        if getattr(module_obj, "path", None)
+    }
+    cache_key = str(root)
+    revision = getattr(state, "revision", None)
+    cached = _QUERY_INDEX_CACHE.get(cache_key)
+    if cached is not None and cached[0] == revision:
+        registries = cached[1]
+        catalog = cached[2]
+    else:
+        registries = query_helpers.read_registries(root)
+        catalog = catalog_from_registry(
+            str(root),
+            module_paths=canonical_module_paths or None,
+        )
+        if revision is not None:
+            _QUERY_INDEX_CACHE[cache_key] = (revision, registries, catalog)
+    mod_path_to_id, mod_id_to_path, art_path_to_id, art_id_to_path = registries
     if not catalog.modules and mod_id_to_path:
         catalog = IndexCatalog(
             modules=mod_id_to_path,
@@ -133,7 +154,6 @@ def get_module_context(
         else:
             module_name = input_query
 
-    engine = mcp_runtime.get_or_init_engine(root)
     if not engine or getattr(engine.state, "resync_required", False):
         return "Error: No usable canonical LIVE state. Run analyze_project first."
 
diff --git a/tests/mcp/tools/test_get_module_context.py b/tests/mcp/tools/test_get_module_context.py
index 8258183..dbd283a 100644
--- a/tests/mcp/tools/test_get_module_context.py
+++ b/tests/mcp/tools/test_get_module_context.py
@@ -505,6 +505,26 @@ def test_get_module_context__fuzzy_windows_init_path_typo_suggestions(tmp_path,
     assert top["module_id"] == "13/1"
 
 
+def test_get_module_context_revision_scoped_query_index_rebuilds_on_revision_change(tmp_path, monkeypatch):
+    state = _setup_module_context_state(monkeypatch)
+    state.revision = 101
+    original_read = query_helpers.read_registries
+    read_calls = []
+
+    def counted_read(root):
+        read_calls.append(root)
+        return original_read(root)
+
+    monkeypatch.setattr(query_helpers, "read_registries", counted_read)
+    get_module_context(str(tmp_path), module_name="pkg.mod_a")
+    get_module_context(str(tmp_path), module_name="pkg.mod_a")
+    assert len(read_calls) == 1
+
+    state.revision = 102
+    get_module_context(str(tmp_path), module_name="pkg.mod_a")
+    assert len(read_calls) == 2
+
+
 def test_get_module_context__normalize_module_path_to_dotted_unit():
     from contextor.core.report_query import normalize_module_path_to_dotted
 
