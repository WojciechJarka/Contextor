# CONTEXTOR_B0G1_PACKAGE_CHILD_GRAPH_REPAIR

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\core\graph\graph.py
- C:\Temp\Contextor_Repo\contextor\core\graph\incremental.py
- C:\Temp\Contextor_Repo\contextor\core\api\facade.py
- C:\Temp\Contextor_Repo\contextor\core\facts\build.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\tests\test_resolver.py
- C:\Temp\Contextor_Repo\tests\test_graph_cache_bindings.py

Only these seven source/test files changed in this task. C:\Temp\Contextor_Repo\walkthrough.md was overwritten as the report and is excluded from source/test change accounting.

## GITHUB_VS_LOCAL_SOURCE_PRECHECK

DIRECT_EVIDENCE: local HEAD before edits was 44436c30daacbd484ce60a6c8b2cf36b6226cc16; git status showed only walkthrough.md modified and git diff of all six authorized tracked source/test files was empty. Contextor MCP returned complete pre-edit resolve_module_edges, _hash_modules, get_cached_graph, resolve_internal and materialize_reexport_facts_by_module with workspace_sync=verified at LIVE revision 334. Local functions and call-site anchors matched the auditor-provided literal B0G1 source contract: B0B import_variants loop present, cache keyed only by modules/imports, full facade reexport materialization before graph, layer/single fallback without fact pass-through, standalone build_graph call, and incremental graph family calls. The GitHub revision used by the auditor was not supplied; remote GitHub commit identity was not independently certified. No approved local anchor mismatch was found.

CONTEXTOR_DISCOVERY: get_symbol_lineage for contextor.core.graph.graph::resolve_module_edges established exact artifact A580/1 and caller/return connections. get_module_blast_radius for contextor.core.graph.graph showed build_graph with 19 direct consumers and 174 downstream consumers, and resolve_module_edges with 2 direct consumers and 190 downstream consumers (canonical revision 334). contextor_fact_lineage does not support family=graph (allowed families: artifact_consumption, syntax_diagnostics, symbol_calls). No graph fact lineage claim is based on that unsupported request.

## PRE_EDIT_LIVE_REVISION

334; get_live_events after 334 reported continuity=continuous and resync_required=false.

## PACKAGE_INIT_EDGE_RETENTION

CODE_PATH_PROVED: resolve_module_edges now resolves the original ImportRef first and records a MODULE result for pkg.__init__ as a hard edge unless type_only. It evaluates names after the initializer edge. Existing from .json import jsonify still resolves the concrete pkg.json.__init__ and remains hard. test_resolver.py covers both.

## NAMED_CHILD_EDGE_RETENTION

CODE_PATH_PROVED: each original imported name is tested against an independently indexed child identity. An unbound named child produces an additional SOFT edge for from pkg import child, while pkg.__init__ remains HARD. Aliases do not replace ImportRef.names. Unresolved names and self edges are skipped. The AST-empty initializer case and mixed named import regression passed.

## EXPLICIT_BINDING_SHADOWING

CODE_PATH_PROVED: canonical initializer facts are consulted through bindings before considering a same-named child. A positively bound name suppresses the additional child edge. The test supplies a canonical binding fact explicitly. __all__ is not used as an explicit named-import filter. Dynamic package attributes that static facts cannot prove remain uncertain.

## RELATIVE_IMPORT_COMPATIBILITY

CODE_PATH_PROVED: from . import json, app, nonexistent evaluates names separately. Indexed children remain HARD for non-type-only relative sibling imports; unresolved names add nothing; _add_edge and the explicit checks avoid self edges. A positively bound same-name child is suppressed. Existing B0B relative and child-package tests remain green.

## HARD_SOFT_CONTRACT

MODULE initializer = HARD except type_only; FALLBACK = SOFT; uncertain named child = SOFT; exact relative sibling child = HARD except type_only; UNKNOWN ignored. A child file alone is not promoted to HARD for from pkg import child. The tests exercise these distinctions.

## GRAPH_CACHE_BINDING_INVALIDATION

_hash_modules accepts optional reexport_facts_by_module and appends a deterministic sorted initializer binding/star-source signature. get_cached_graph forwards it while retaining the old two-argument call. Focused tests prove a cache miss and different graph after a binding-only change, a hit for identical bindings, and legacy call compatibility. LRU ownership, eviction and return shape were unchanged.

## FULL_ANALYSIS_FACT_PASS_THROUGH

ContextorFacade.analyze_project passes already materialized canonical_reexport_facts to both get_cached_graph and the build_graph builder closure. The existing progress callback and cache-hit branch remain.

## LAYER_SINGLE_FALLBACK_CONSISTENCY

Fresh-index analyze_layer fallback materializes shared reexport facts using index.reference_facts_by_module and passes them to cache and graph. Fresh-index analyze_single_file fallback uses the established materialize_reexport_facts_by_module(modules) AST fallback and passes the same facts to cache and graph. Authoritative-state reuse branches were not changed. The targeted layer fallback test passed; no full GUI/MCP analysis was run.

## STANDALONE_GRAPH_CONSISTENCY

build_repository_context obtains reexport facts via contextor.core.reference.shared.materialize_reexport_facts_by_module after build_index and passes them to build_graph. RepositoryContext shape is unchanged. This call path was source-verified and syntax-compiled, not exercised by a dedicated new integration test.

## INCREMENTAL_SHARED_GRAPH_OWNER

The dependency_graph patch family passes candidate.reexport_facts_by_module to build_graph for add/delete and to resolve_module_edges for an existing modified module. Existing candidate graph COW publication flow remains. RefreshPlanner and importer-wide invalidation were not changed.

## TARGETED_TEST_RESULTS

Latest command: .venv Python pytest -q tests/test_resolver.py tests/test_graph_cache_bindings.py tests/test_layer_state_only_hydration.py::test_invalid_authoritative_state_keeps_layer_on_indexed_fallback => 19 passed. Earlier selected ordinary/import/incremental graph command (tests/test_imports.py, two tests/test_pipeline.py graph nodes, two tests/test_graph_only_live_analytics.py import-delta nodes, one tests/test_incremental_reverse_context.py node) => 20 passed. The first 18-pass run preceded the final exact mixed-import fixture adjustment; the later 19-pass run supersedes it. No full suite, full GUI/MCP analysis, or Flask benchmark was run.

## PY_COMPILE

.venv Python -m py_compile for all five modified production owners: exit 0.

## GIT_DIFF_CHECK

git diff --check scoped to the six tracked production/test files: exit 0. The new test file has no trailing whitespace (checked in the complete new-file diff). Git emitted only LF/CRLF conversion notices. The report file contains literal diff text and is excluded from source/test whitespace judgment.

## LIVE_REVISION_BEFORE_AFTER

334 -> 342. get_live_events(after_revision=334) returned eight continuous desktop_watcher UPDATED events: 335 graph.py, 336 graph/incremental.py, 337 facade.py, 338 facts/build.py, 339 plan_executor.py, 340 test_resolver.py, 341 test_graph_cache_bindings.py, 342 test_resolver.py. Final get_live_events(after_revision=342) showed no further revisions and continuity=continuous. These events prove watcher observation and canonical revision progression, not reload of imported Python code.

## WORKSPACE_SYNC_POSTCHECK

At revision 342, Contextor get_symbol_implementation returned complete fetches with workspace_sync=verified for edited resolve_module_edges, _hash_modules and build_repository_context; all contained the new argument. get_source_range returned exact current post-edit ranges for all three facade call sites, plan_executor's graph branch, and build_graph/resolve_module_edges. No retrieval was treated as complete when it returned confirmation_required. Serving-process imported-code freshness was not attested.

## RESYNC_REQUIRED

false before and after edits; LIVE event continuity continuous. Canonical revision 342 at final read.

## RESTART_REQUIRED

YES_FOR_RUNTIME_CERTIFICATION. Edited graph/facade/incremental production code needs a manual serving-process reload before real runtime certification. No agent restart was performed; source indexing and watcher updates alone do not prove imported-code reload.

## UNTREATED_INCREMENTAL_PROPAGATION

The incoming-importer recomputation when an initializer binding changes is deliberately outside B0G1. RefreshPlanner was unchanged. B0G2 must adjudicate that separate propagation contract; this targeted pass does not certify it.

## UNTREATED_DESKTOP_MCP_INTEGRATION_PARITY

No full Desktop versus MCP canonical-output equality test or incremental versus fresh-FULL parity test ran here. B0F identified those as release gates. Shared function calls and these targeted regressions are not sufficient to certify entrypoint parity.

## FINAL_VERDICT

B0G1_TARGETED_IMPLEMENTATION_PASS. Scope is the auditor's intermediate graph repair only. B0E closure and Desktop/MCP release parity remain uncertified. Await "proceduj".

## FULL_DIFFS

The following are complete actual source/test diffs for all seven task-changed files. The new test file is shown as a complete /dev/null diff.

```diff
diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 1238cd2..1dd62d4 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -1016,7 +1016,12 @@ def execute_refresh_plan(
             if delta.is_deleted or delta.is_new:
                 new_trie = build_trie(candidate.modules.keys())
                 new_package_root = detect_package_root(candidate.modules, new_trie)
-                new_graph = build_graph(candidate.modules, trie=new_trie, package_root=new_package_root)
+                new_graph = build_graph(
+                    candidate.modules,
+                    trie=new_trie,
+                    package_root=new_package_root,
+                    reexport_facts_by_module=candidate.reexport_facts_by_module,
+                )
                 candidate.trie = new_trie
                 candidate.package_root = new_package_root
                 candidate.dependency_graph = new_graph
@@ -1025,7 +1030,13 @@ def execute_refresh_plan(
                 new_package_root = candidate.package_root
                 curr_graph = candidate.dependency_graph
                 if curr_graph:
-                    hard, soft = resolve_module_edges(delta.module_path, candidate.modules[delta.module_path], new_trie, new_package_root)
+                    hard, soft = resolve_module_edges(
+                        delta.module_path,
+                        candidate.modules[delta.module_path],
+                        new_trie,
+                        new_package_root,
+                        candidate.reexport_facts_by_module,
+                    )
                     candidate.dependency_graph = curr_graph.with_module_edges(delta.module_path, hard, soft)
             executed_patch_families.append("dependency_graph")
 
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index d41b17a..0c043d1 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -730,7 +730,9 @@ class ContextorFacade:
                 trie=trie,
                 package_root=package_root,
                 progress_callback=graph_progress,
-            )
+                reexport_facts_by_module=canonical_reexport_facts,
+            ),
+            reexport_facts_by_module=canonical_reexport_facts,
         )
 
         emit_stage_end("graph", graph_started)
@@ -1408,6 +1410,13 @@ class ContextorFacade:
                 progress_callback=index_progress,
             )
             modules = index.modules
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
@@ -1419,7 +1428,9 @@ class ContextorFacade:
                     trie=trie,
                     package_root=package_root,
                     progress_callback=graph_progress,
+                    reexport_facts_by_module=canonical_reexport_facts,
                 ),
+                reexport_facts_by_module=canonical_reexport_facts,
             )
             skipped_files = getattr(index, "skipped", [])
             reference_index = assemble_reference_index_or_fallback(
@@ -1743,10 +1754,19 @@ class ContextorFacade:
                 extra_ignored_dirs=extra_dirs,
                 progress_callback=index_progress,
             )
+            from contextor.core.reference.shared import (
+                materialize_reexport_facts_by_module,
+            )
+            canonical_reexport_facts = materialize_reexport_facts_by_module(modules)
             graph_progress = progress.begin("Resolving dependency graph")
             graph, cache_hit = get_cached_graph(
                 modules,
-                lambda m: build_graph(m, progress_callback=graph_progress),
+                lambda m: build_graph(
+                    m,
+                    progress_callback=graph_progress,
+                    reexport_facts_by_module=canonical_reexport_facts,
+                ),
+                reexport_facts_by_module=canonical_reexport_facts,
             )
 
         if log:
diff --git a/contextor/core/facts/build.py b/contextor/core/facts/build.py
index 4a162b2..f023573 100644
--- a/contextor/core/facts/build.py
+++ b/contextor/core/facts/build.py
@@ -35,6 +35,9 @@ Does not include:
 from contextor.core.graph.graph import (
     build_graph,
 )
+from contextor.core.reference.shared import (
+    materialize_reexport_facts_by_module,
+)
 from contextor.core.symbol_engine.indexer import (
     build_index,
 )
@@ -69,12 +72,16 @@ def build_repository_context(
     # ------------------------------------------------------
 
     modules = build_index(root_path)
+    reexport_facts_by_module = materialize_reexport_facts_by_module(modules)
 
     # ------------------------------------------------------
     # DEPENDENCY GRAPH
     # ------------------------------------------------------
 
-    graph = build_graph(modules)
+    graph = build_graph(
+        modules,
+        reexport_facts_by_module=reexport_facts_by_module,
+    )
 
     # ------------------------------------------------------
     # SYMBOL INDEX
diff --git a/contextor/core/graph/graph.py b/contextor/core/graph/graph.py
index 8f2cb00..a0d6227 100644
--- a/contextor/core/graph/graph.py
+++ b/contextor/core/graph/graph.py
@@ -113,6 +113,7 @@ def build_graph(
     trie: dict | None = None,
     package_root: str | None = None,
     progress_callback=None,
+    reexport_facts_by_module: dict | None = None,
 ) -> ProjectGraph:
     """
     Builds the dependency graph from parsed modules.
@@ -167,7 +168,9 @@ def build_graph(
         # Import order does not affect graph
         # --------------------------------------------------
 
-        hard_targets, soft_targets = resolve_module_edges(module_id, module, trie, package_root)
+        hard_targets, soft_targets = resolve_module_edges(
+            module_id, module, trie, package_root, reexport_facts_by_module
+        )
         
         for target in hard_targets:
             _add_edge(hard_edges, module_id, target)
@@ -179,7 +182,13 @@ def build_graph(
         soft_edges={key: value for key, value in sorted(soft_edges.items())},
     )
 
-def resolve_module_edges(module_id: str, module, trie, package_root: str) -> tuple[set[str], set[str]]:
+def resolve_module_edges(
+    module_id: str,
+    module,
+    trie,
+    package_root: str,
+    reexport_facts_by_module: dict | None = None,
+) -> tuple[set[str], set[str]]:
     """
     Resolves outgoing hard and soft dependencies for a single module.
     Extracted as a canonical unit of graph resolution for use in both
@@ -200,50 +209,91 @@ def resolve_module_edges(module_id: str, module, trie, package_root: str) -> tup
     )
 
     for imp in imports:
+        try:
+            result = resolve_internal(
+                imp,
+                trie,
+                current_module_id=module_id,
+                package_root=package_root,
+            )
+        except Exception:
+            continue
+
+        if result.target_module and result.kind != "UNKNOWN":
+            target = result.target_module
+            if target != module_id:
+                if _is_type_only_import(imp):
+                    _add_edge(soft, module_id, target)
+                elif result.kind == "MODULE":
+                    _add_edge(hard, module_id, target)
+                elif result.kind == "FALLBACK":
+                    _add_edge(soft, module_id, target)
+
+        if not imp.is_from_import or not imp.names:
+            continue
+
+        package_init = result.target_module
         if (
-            imp.is_from_import
-            and imp.level > 0
-            and imp.module is None
+            result.kind != "MODULE"
+            or not package_init
+            or not package_init.endswith(".__init__")
         ):
-            import_variants = [
-                type(imp)(
-                    module=name,
-                    level=imp.level,
-                    names=[],
-                    is_from_import=True,
-                    is_local=imp.is_local,
-                )
-                for name in sorted(set(imp.names))
-                if name != "*"
-            ]
-        else:
-            import_variants = [imp]
+            continue
+
+        package_name = package_init.removesuffix(".__init__")
+        package_facts = (
+            (reexport_facts_by_module or {}).get(package_init)
+            or {}
+        )
+        bindings = package_facts.get("bindings") or {}
+
+        for imported_name in sorted(set(imp.names)):
+            if not imported_name or imported_name == "*":
+                continue
+
+            # Explicit initializer bindings take precedence
+            # over a same-named indexed child module.
+            if imported_name in bindings:
+                continue
+
+            child_name = f"{package_name}.{imported_name}"
+            child_import = type(imp)(
+                module=child_name,
+                level=0,
+                names=[],
+                is_from_import=False,
+                is_local=imp.is_local,
+                type_only=imp.type_only,
+            )
 
-        for import_variant in import_variants:
             try:
-                result = resolve_internal(
-                    import_variant,
+                child_result = resolve_internal(
+                    child_import,
                     trie,
                     current_module_id=module_id,
-                    package_root=package_root,
+                    package_root=None,
                 )
             except Exception:
                 continue
 
-            if result.kind == "UNKNOWN" or not result.target_module:
+            if (
+                child_result.kind != "MODULE"
+                or not child_result.target_module
+                or child_result.target_module == module_id
+                or child_result.target_module == package_init
+            ):
                 continue
 
-            target = result.target_module
-            if target == module_id:
-                continue
+            child_target = child_result.target_module
 
             if _is_type_only_import(imp):
-                _add_edge(soft, module_id, target)
-                continue
-
-            if result.kind == "MODULE":
-                _add_edge(hard, module_id, target)
-            elif result.kind == "FALLBACK":
-                _add_edge(soft, module_id, target)
+                _add_edge(soft, module_id, child_target)
+            elif imp.module is None and imp.level > 0:
+                # Explicit relative sibling import.
+                _add_edge(hard, module_id, child_target)
+            else:
+                # Named package member: preserve possible
+                # child dependency conservatively.
+                _add_edge(soft, module_id, child_target)
 
     return hard[module_id], soft[module_id]
diff --git a/contextor/core/graph/incremental.py b/contextor/core/graph/incremental.py
index 87e99e1..51eb6a6 100644
--- a/contextor/core/graph/incremental.py
+++ b/contextor/core/graph/incremental.py
@@ -88,7 +88,10 @@ def _serialize_import(imp) -> tuple:
 # ==========================================================
 
 
-def _hash_modules(modules: dict) -> str:
+def _hash_modules(
+    modules: dict,
+    reexport_facts_by_module=None,
+) -> str:
     """
     Generates a deterministic hash of the module index.
 
@@ -122,6 +125,25 @@ def _hash_modules(modules: dict) -> str:
             )
         )
 
+    for module_id in sorted(
+        (reexport_facts_by_module or {}).keys()
+    ):
+        if not module_id.endswith(".__init__"):
+            continue
+
+        facts = reexport_facts_by_module[module_id] or {}
+        bindings = facts.get("bindings") or {}
+        star_sources = facts.get("star_sources") or []
+
+        parts.append(
+            (
+                "PACKAGE_EXPORT_BINDINGS",
+                module_id,
+                tuple(sorted(bindings.items())),
+                tuple(sorted(star_sources)),
+            )
+        )
+
     raw = repr(parts)
 
     return hashlib.sha256(raw.encode("utf-8")).hexdigest()
@@ -167,7 +189,12 @@ def _cache_put(key: str, graph: ProjectGraph):
 # ==========================================================
 
 
-def get_cached_graph(modules: dict, builder_fn) -> tuple[ProjectGraph, bool]:
+def get_cached_graph(
+    modules: dict,
+    builder_fn,
+    *,
+    reexport_facts_by_module=None,
+) -> tuple[ProjectGraph, bool]:
     """
     Returns a ProjectGraph and information
     whether the result came from the cache.
@@ -198,7 +225,7 @@ def get_cached_graph(modules: dict, builder_fn) -> tuple[ProjectGraph, bool]:
 
     """
 
-    cache_key = _hash_modules(modules)
+    cache_key = _hash_modules(modules, reexport_facts_by_module)
 
     cached = _cache_get(cache_key)
 
diff --git a/tests/test_resolver.py b/tests/test_resolver.py
index 266ea0c..2c57d69 100644
--- a/tests/test_resolver.py
+++ b/tests/test_resolver.py
@@ -183,3 +183,110 @@ def test_relative_package_import_preserves_nonpackage_behavior(tmp_path):
     hard, soft = resolve_module_edges("pkg.__init__", soft_module, trie, None)
     assert hard == set()
     assert soft == {"pkg.json.__init__"}
+
+
+def _named_package_modules(
+    tmp_path: Path,
+    importer_source: str,
+    init_source: str = "",
+    child_name: str = "runtime",
+):
+    package = tmp_path / "pkg"
+    package.mkdir()
+    initializer = package / "__init__.py"
+    initializer.write_text(init_source, encoding="utf-8")
+    child = package / f"{child_name}.py"
+    child.write_text("VALUE = 1\n", encoding="utf-8")
+    importer = tmp_path / "consumer.py"
+    importer.write_text(importer_source, encoding="utf-8")
+    imports, error = read_imports(importer)
+    assert error is None
+    assert imports is not None
+    modules = {
+        "pkg.__init__": Module("pkg.__init__", "pkg/__init__.py", str(initializer), []),
+        f"pkg.{child_name}": Module(
+            f"pkg.{child_name}", f"pkg/{child_name}.py", str(child), []
+        ),
+        "consumer": Module("consumer", "consumer.py", str(importer), imports),
+    }
+    return modules, imports
+
+
+def test_named_child_keeps_initializer_and_soft_child_edges(tmp_path):
+    modules, imports = _named_package_modules(
+        tmp_path, "from pkg import runtime as mcp_runtime\n"
+    )
+    assert imports[0].names == ["runtime"]
+    trie = build_trie(modules)
+    hard, soft = resolve_module_edges("consumer", modules["consumer"], trie, None)
+    assert hard == {"pkg.__init__"}
+    assert soft == {"pkg.runtime"}
+    assert hard | soft <= modules.keys()
+
+
+def test_initializer_binding_shadows_same_named_child(tmp_path):
+    modules, _ = _named_package_modules(
+        tmp_path, "from pkg import runtime\n", "runtime = object()\n"
+    )
+    facts = {"pkg.__init__": {"bindings": {"runtime": "pkg.__init__.runtime"}}}
+    hard, soft = resolve_module_edges(
+        "consumer", modules["consumer"], build_trie(modules), None, facts
+    )
+    assert hard == {"pkg.__init__"}
+    assert soft == set()
+
+
+def test_mixed_named_import_preserves_only_unbound_indexed_child(tmp_path):
+    modules, _ = _named_package_modules(
+        tmp_path,
+        "from pkg import exported_symbol, child, nonexistent\n",
+        "exported_symbol = 1\n",
+        child_name="child",
+    )
+    facts = {"pkg.__init__": {"bindings": {"exported_symbol": "pkg.__init__.exported_symbol"}}}
+    hard, soft = resolve_module_edges(
+        "consumer", modules["consumer"], build_trie(modules), None, facts
+    )
+    assert hard == {"pkg.__init__"}
+    assert soft == {"pkg.child"}
+
+
+def test_relative_named_import_shadows_indexed_child_when_bound(tmp_path):
+    modules, imports = _named_package_modules(tmp_path, "from . import runtime\n")
+    modules["pkg.consumer"] = Module(
+        "pkg.consumer", "pkg/consumer.py", modules["consumer"].absolute_path, imports
+    )
+    del modules["consumer"]
+    facts = {"pkg.__init__": {"bindings": {"runtime": "pkg.__init__.runtime"}}}
+    hard, soft = resolve_module_edges(
+        "pkg.consumer", modules["pkg.consumer"], build_trie(modules), None, facts
+    )
+    assert hard == {"pkg.__init__"}
+    assert soft == set()
+
+
+def test_type_only_named_package_dependencies_are_soft(tmp_path):
+    modules, imports = _named_package_modules(tmp_path, "from pkg import runtime\n")
+    original = imports[0]
+    modules["consumer"] = Module(
+        "consumer",
+        "consumer.py",
+        modules["consumer"].absolute_path,
+        [ImportRef(original.module, original.level, original.names, True, type_only=True)],
+    )
+    hard, soft = resolve_module_edges(
+        "consumer", modules["consumer"], build_trie(modules), None
+    )
+    assert hard == set()
+    assert soft == {"pkg.__init__", "pkg.runtime"}
+
+
+def test_full_graph_matches_direct_resolver_for_named_package(tmp_path):
+    modules, _ = _named_package_modules(tmp_path, "from pkg import runtime\n")
+    facts = {"pkg.__init__": {"bindings": {}}}
+    direct_hard, direct_soft = resolve_module_edges(
+        "consumer", modules["consumer"], build_trie(modules), None, facts
+    )
+    graph = build_graph(modules, reexport_facts_by_module=facts)
+    assert graph.hard_edges["consumer"] == direct_hard
+    assert graph.soft_edges["consumer"] == direct_soft
diff --git a/tests/test_graph_cache_bindings.py b/tests/test_graph_cache_bindings.py
new file mode 100644
index 0000000..2db21e7
--- /dev/null
+++ b/tests/test_graph_cache_bindings.py
@@ -0,0 +1,68 @@
+from contextor.core.domain.imports import ImportRef
+from contextor.core.domain.module import Module
+from contextor.core.graph.graph import build_graph
+from contextor.core.graph.incremental import _CACHE, get_cached_graph
+
+
+def test_package_binding_change_invalidates_graph_cache():
+    modules = {
+        "pkg.__init__": Module("pkg.__init__", "pkg/__init__.py", "/pkg/__init__.py", []),
+        "pkg.child": Module("pkg.child", "pkg/child.py", "/pkg/child.py", []),
+        "consumer": Module(
+            "consumer",
+            "consumer.py",
+            "/consumer.py",
+            [ImportRef("pkg", 0, ["child"], True)],
+        ),
+    }
+    unbound = {"pkg.__init__": {"bindings": {}, "star_sources": []}}
+    bound = {
+        "pkg.__init__": {
+            "bindings": {"child": "pkg.__init__.child"},
+            "star_sources": [],
+        }
+    }
+
+    def build(facts):
+        return get_cached_graph(
+            modules,
+            lambda current: build_graph(
+                current, reexport_facts_by_module=facts
+            ),
+            reexport_facts_by_module=facts,
+        )
+
+    original_cache = _CACHE.copy()
+    try:
+        _CACHE.clear()
+        first, first_hit = build(unbound)
+        same, same_hit = build(unbound)
+        changed, changed_hit = build(bound)
+        repeated, repeated_hit = build(bound)
+        assert first_hit is False
+        assert same_hit is True
+        assert same is first
+        assert changed_hit is False
+        assert changed.soft_edges["consumer"] == set()
+        assert first.soft_edges["consumer"] == {"pkg.child"}
+        assert repeated_hit is True
+        assert repeated is changed
+        assert len(_CACHE) == 2
+    finally:
+        _CACHE.clear()
+        _CACHE.update(original_cache)
+
+
+def test_legacy_two_argument_graph_cache_call_remains_supported():
+    modules = {"empty": Module("empty", "empty.py", "/empty.py", [])}
+    original_cache = _CACHE.copy()
+    try:
+        _CACHE.clear()
+        first, first_hit = get_cached_graph(modules, build_graph)
+        second, second_hit = get_cached_graph(modules, build_graph)
+        assert first_hit is False
+        assert second_hit is True
+        assert second is first
+    finally:
+        _CACHE.clear()
+        _CACHE.update(original_cache)
```
