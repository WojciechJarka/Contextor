# CONTEXTOR_B0G1A_INITIALIZER_SELF_IMPORT_REGRESSION

## FILES_CHANGED

- C:\Temp\Contextor_Repo\contextor\core\graph\graph.py
- C:\Temp\Contextor_Repo\tests\test_resolver.py

C:\Temp\Contextor_Repo\walkthrough.md was overwritten for this report and is excluded from source/test change accounting. No other source or test file changed during B0G1A.

## PRE_PATCH_RED_TEST

DIRECT_EVIDENCE: test_initializer_self_import_binding_keeps_child_package_hard_edge, run alone before the production patch, FAILED as expected (1 failed). Actual extracted binding: facts["pkg.__init__"]["bindings"]["json"] == "pkg.json". Actual direct hard edge set was empty; expected {"pkg.json.__init__"}. The assertion failed at tests/test_resolver.py:175. This proves the B0G1 binding guard suppressed the initializer's own child-package dependency.

## PRODUCTION_BINDING_FACTS

Contextor MCP retrieved complete current implementations of resolve_module_edges and materialize_reexport_facts_by_module at pre-edit revision 342 with workspace_sync=verified. The real extractor represents the self import as binding json -> pkg.json. In the assignment fixture it represents runtime = object() as binding runtime -> pkg.runtime. In the three-name self import it represents json -> pkg.json, app -> pkg.app, nonexistent -> pkg.nonexistent. The test expectations use these actual production representations, not the earlier synthetic pkg.__init__.runtime spelling. get_module_blast_radius reported 20 direct graph-module consumers and 174 downstream consumers at revision 342; this is impact context, not runtime execution proof.

## EXACT_PATCH_APPLIED

The approved three-line guard in resolve_module_edges was replaced exactly with the auditor's package_init != module_id condition and comments. No other production resolution branch changed. resolve_internal, ImportRef, ResolutionResult, graph cache, reexport extractor and module identities were untouched.

## SELF_IMPORT_EDGE_RECOVERED

The real-fact self-import regression is GREEN. Direct resolve_module_edges and full build_graph both include HARD pkg.__init__ -> pkg.json.__init__, no SOFT edge, and no fabricated pkg.json module identity.

## REAL_ASSIGNMENT_SHADOWING

The separate real-fact assignment regression is GREEN. With pkg/__init__.py containing runtime = object() and pkg/runtime.py indexed, consumer.py from pkg import runtime has HARD {"pkg.__init__"} and SOFT empty. The actual extractor value is pkg.runtime; the test asserts that value.

## RELATIVE_MULTI_NAME_PARITY

The real-fact from . import json, app, nonexistent regression is GREEN. Direct resolver and full graph agree on HARD {"pkg.json.__init__", "pkg.app"}, SOFT empty. No pkg.__init__ self edge or unresolved pkg.nonexistent edge appears.

## B0B_B0G1_REGRESSIONS

The complete tests/test_resolver.py includes existing B0B concrete child-package resolution, relative multi-name, type-only and B0G1 named-child/initializer-shadowing tests. tests/test_graph_cache_bindings.py covers B0G1 cache invalidation. Both files passed together.

## TARGETED_TEST_RESULTS

Pre-patch named self-import test: 1 failed as expected. Post-patch three new named regressions: 3 passed. Final targeted command `.venv\Scripts\python.exe -m pytest -q tests/test_resolver.py tests/test_graph_cache_bindings.py`: 21 passed in 0.80s. No full suite, full analysis, Flask benchmark, Desktop/MCP parity test or manual update_file call was run.

## PY_COMPILE

`.venv\Scripts\python.exe -m py_compile contextor/core/graph/graph.py`: exit 0.

## GIT_DIFF_CHECK

`git diff --check -- contextor/core/graph/graph.py tests/test_resolver.py`: exit 0. Git only emitted local LF/CRLF conversion notices.

## LIVE_REVISION_BEFORE_AFTER

Pre-edit revision 342, continuity=continuous, resync_required=false. Desktop watcher recorded UPDATED events: revision 343 tests/test_resolver.py, revision 344 contextor/core/graph/graph.py, revision 345 tests/test_resolver.py. Final get_live_events(after_revision=345) returned no new events, latest_revision=345 and continuous continuity. These events establish source observation, not serving-process imported-code reload.

## WORKSPACE_SYNC_POSTCHECK

Contextor get_symbol_implementation(resolve_module_edges, mode=fetch, include=implementation) returned complete source with workspace_sync=verified at canonical revision 345 and contained the exact package_init != module_id condition. The unchanged materialize_reexport_facts_by_module was complete and workspace_sync=verified in precheck at revision 342. Source indexing is not byte-level runtime attestation.

## RESYNC_REQUIRED

false before and after the edit. LIVE event continuity was continuous.

## RESTART_REQUIRED

YES_FOR_RUNTIME_CERTIFICATION. graph.py changed. No MCP, LIVE or Desktop process restart was performed. The current serving process is not certified to have imported this edit.

## REMAINING_SEMANTIC_AMBIGUITIES

This exact patch addresses initializer self-import versus other-importer shadowing only. B0G2 incoming-importer propagation and full Desktop/MCP/incremental canonical parity remain outside this gate. Dynamic initializer bindings not established by static facts remain uncertain. No full runtime or benchmark conclusion follows from these targeted tests.

## FINAL_VERDICT

B0G1A_TARGETED_PASS. Await "proceduj".

## FULL_DIFFS

Complete actual diffs for both modified files:

```diff
diff --git a/contextor/core/graph/graph.py b/contextor/core/graph/graph.py
index a0d6227..6fa4c88 100644
--- a/contextor/core/graph/graph.py
+++ b/contextor/core/graph/graph.py
@@ -251,9 +251,14 @@ def resolve_module_edges(
             if not imported_name or imported_name == "*":
                 continue
 
-            # Explicit initializer bindings take precedence
-            # over a same-named indexed child module.
-            if imported_name in bindings:
+            # A package initializer may itself bind a name
+            # through "from . import child". Such a binding
+            # must not hide the initializer's own import edge.
+            # Other importers still honor initializer shadowing.
+            if (
+                imported_name in bindings
+                and package_init != module_id
+            ):
                 continue
 
             child_name = f"{package_name}.{imported_name}"
diff --git a/tests/test_resolver.py b/tests/test_resolver.py
index 2c57d69..26d7f28 100644
--- a/tests/test_resolver.py
+++ b/tests/test_resolver.py
@@ -12,6 +12,7 @@ from contextor.core.graph.resolver import (
     detect_package_root,
     resolve_internal,
 )
+from contextor.core.reference.shared import materialize_reexport_facts_by_module
 from contextor.core.symbol_engine.indexer import read_imports
 
 MODULES = ["core.alpha", "core.beta", "ui.app"]
@@ -161,6 +162,58 @@ def test_relative_from_import_multiple_package_targets(tmp_path):
     assert graph.soft_edges["pkg.__init__"] == soft
 
 
+def test_initializer_self_import_binding_keeps_child_package_hard_edge(tmp_path):
+    modules, _ = _package_modules(tmp_path, "from . import json as json\n")
+    facts = materialize_reexport_facts_by_module(modules)
+    assert facts["pkg.__init__"]["bindings"]["json"] == "pkg.json"
+
+    trie = build_trie(modules)
+    hard, soft = resolve_module_edges(
+        "pkg.__init__", modules["pkg.__init__"], trie, None, facts
+    )
+    graph = build_graph(modules, reexport_facts_by_module=facts)
+    assert hard == {"pkg.json.__init__"}
+    assert soft == set()
+    assert graph.hard_edges["pkg.__init__"] == hard
+    assert graph.soft_edges["pkg.__init__"] == soft
+    assert "pkg.json" not in modules
+
+
+def test_initializer_real_assignment_shadows_same_named_child(tmp_path):
+    modules, _ = _named_package_modules(
+        tmp_path, "from pkg import runtime\n", "runtime = object()\n"
+    )
+    facts = materialize_reexport_facts_by_module(modules)
+    assert facts["pkg.__init__"]["bindings"]["runtime"] == "pkg.runtime"
+
+    hard, soft = resolve_module_edges(
+        "consumer", modules["consumer"], build_trie(modules), None, facts
+    )
+    assert hard == {"pkg.__init__"}
+    assert soft == set()
+
+
+def test_initializer_real_multi_name_bindings_keep_indexed_child_edges(tmp_path):
+    modules, _ = _package_modules(tmp_path, "from . import json, app, nonexistent\n")
+    facts = materialize_reexport_facts_by_module(modules)
+    assert facts["pkg.__init__"]["bindings"] == {
+        "json": "pkg.json",
+        "app": "pkg.app",
+        "nonexistent": "pkg.nonexistent",
+    }
+
+    hard, soft = resolve_module_edges(
+        "pkg.__init__", modules["pkg.__init__"], build_trie(modules), None, facts
+    )
+    graph = build_graph(modules, reexport_facts_by_module=facts)
+    assert hard == {"pkg.json.__init__", "pkg.app"}
+    assert soft == set()
+    assert "pkg.__init__" not in hard
+    assert "pkg.nonexistent" not in hard | soft
+    assert graph.hard_edges["pkg.__init__"] == hard
+    assert graph.soft_edges["pkg.__init__"] == soft
+
+
 def test_relative_package_import_preserves_nonpackage_behavior(tmp_path):
     modules, imports = _package_modules(tmp_path, "from .app import Flask\n")
     trie = build_trie(modules)
```
