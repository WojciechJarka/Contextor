# CONTEXTOR_B0B_PACKAGE_INIT_IDENTITY_FIX

## FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\graph\resolver.py
- C:\Temp\Contextor_Repo\contextor\core\graph\graph.py
- C:\Temp\Contextor_Repo\contextor\mcp\tools\get_file_edit_context.py
- C:\Temp\Contextor_Repo\tests\test_resolver.py
- C:\Temp\Contextor_Repo\tests\test_mcp_regressions.py
- C:\Temp\Contextor_Repo\walkthrough.md (report only; excluded from source/test diff requirement)
Pre-existing modified C:\Temp\Contextor_Repo\README.md and C:\Temp\Contextor_Repo\CHANGELOG.md were preserved; neither was edited in this task.

## PRE_EDIT_LIVE_REVISION
Contextor MCP get_live_events: canonical revision 328; resync_required=false. HEAD=4951f3c3f29f329228dd9c40b90130c7baf80d81. All five authorized production/test files were clean before this task. Contextor implementation/source-range preflight returned complete selected functions and workspace_sync=verified. Exact approved anchors matched. ImportRef is a frozen dataclass with constructor fields module, level, names, is_from_import, is_local=False, type_only=False; the approved type(imp)(...) expression is compatible.

## APPROVED_PATCHES_APPLIED
A1: Added exact `candidate.__init__` trie lookup immediately after existing exact lookup in resolve_internal; returns existing canonical `__init__` identity as MODULE. No trie or registry change.
A2: Replaced one-result ImportRef loop with auditor-supplied variant loop only for relative `from . import ...` where module is None. Classification still uses original ImportRef. No other graph logic changed.
B: Removed default get_file_edit_context's `__init__` component pop. Minimal branch unchanged; response schema unchanged.

## PACKAGE_INIT_GRAPH_BEHAVIOR
CODE_PATH_PROVED and tested: `from .json import jsonify` targets indexed pkg.json.__init__ as kind=MODULE; direct and full graph contain hard edge. Ordinary `.app` remains pkg.app MODULE/hard. Missing package remains UNKNOWN. No fake pkg.json module key is created. The direct resolver/full graph agreement is tested.

## RELATIVE_MULTI_ALIAS_BEHAVIOR
Tested `from . import json, app, nonexistent`: two distinct hard targets pkg.json.__init__ and pkg.app, no nonexistent or self edge; set semantics prevent duplicates. Full build_graph and resolve_module_edges agree. Original ImportRef classification is preserved in code.

## NONPACKAGE_COMPATIBILITY
Existing resolver tests, indexed package/file distinction, ordinary file context, import tests, and selected incremental reverse graph test passed. New focused test confirms ordinary .app exact resolution, UNKNOWN missing target, existing nonpackage FALLBACK, and type-only package import remains soft.

## MCP_DEFAULT_MINIMAL_PARITY
New same-root real registry/module fixture indexes pkg/__init__.py as pkg.__init__. Both minimal and default calls return that canonical module ID; default status=available and freshness canonical_state=fresh. Ordinary pkg/example.py default resolution remains available with its own canonical ID. Fixture uses real PersistentIdentityRegistry and canonical Module keys; engine retrieval is isolated by monkeypatch, not identity mapping.

## EXACT_TARGETED_TEST_RESULTS
Command 1: `.venv\Scripts\python.exe -m pytest -q` with the three new tests in tests/test_resolver.py and new test in tests/test_mcp_regressions.py: 4 passed, 1 third-party AuthlibDeprecationWarning, 0 failed.
Command 2: complete tests/test_resolver.py plus tests/test_indexed_report_query.py::test_cli_file_and_cli_package_init_remain_distinct, tests/test_mcp_regressions.py::test_file_edit_context_live_revision_lifecycle, tests/mcp/tools/test_get_module_context.py::test_get_module_context__fuzzy_init_path_typo_suggestions: 13 passed, 1 same warning, 0 failed.
Command 3: complete tests/test_imports.py plus tests/test_incremental_reverse_context.py::test_new_importing_file_immediately_updates_forward_and_reverse_graph: 16 passed, 0 failed.
No full repository pytest run. The existing incremental case is ordinary-module behavior, not end-to-end package-init parity.

## PY_COMPILE
`.venv\Scripts\python.exe -m py_compile` on the three modified production files: exit 0.

## GIT_DIFF_CHECK
`git diff --check --` on all five modified source/test files: exit 0. Git emitted only Windows LF-to-CRLF conversion notices; no whitespace errors.

## PRODUCTION_SCOPE
Only the three authorized production owners changed. Contextor preflight minimal context: resolver direct consumers 3/transitive 172; graph direct consumers 18/transitive 170; get_file_edit_context direct consumers 7/transitive 39. Those are canonical reachability counts, not a claim of manually verified semantic completeness. No module renaming, global trie rewrite, registry identity change, public schema change or unrelated refactor.

## EXTERNAL_BENCHMARK_UNCHANGED
Flask HEAD remains d086db856be187255b8ec61ef409357393020f32. Git status shows only pre-existing untracked `.contextor/` benchmark artifacts. No Flask source/oracle change, reanalysis or rebenchmark.

## LIVE_REVISION_BEFORE_AFTER
Before 328; after 333. `get_live_events(after_revision=328,limit=null)` returned continuity=continuous, resync_required=false, exactly five `desktop_watcher` update_file UPDATED events: 329 resolver.py; 330 graph.py; 331 get_file_edit_context.py; 332 test_resolver.py; 333 test_mcp_regressions.py. No manual update_file call.

## WORKSPACE_SYNC_POSTCHECK
Contextor get_symbol_implementation returned patched resolve_internal and resolve_module_edges at revision 333 with workspace_sync=verified. get_source_range returned patched get_file_edit_context lines 439-450; get_module_context for its module reported canonical_state=fresh, workspace_sync=verified, revision 333. This proves source indexing/sync, not imported-code reload of the existing serving MCP process.

## RESYNC_REQUIRED
false after revision 333; event continuity continuous from pre-edit revision 328.

## RESTART_REQUIRED
YES_FOR_RUNTIME_CERTIFICATION. The user must manually restart affected MCP/LIVE serving processes before certifying runtime execution of changed server/graph code. No restart was performed here.

## UNTESTED_BOUNDARIES
End-to-end incremental package-init graph parity: NOT_TESTED; direct resolver/full graph parity is tested. External Flask B0 rebenchmark: NOT_RUN. Existing serving-process imported-code freshness: NOT_CERTIFIED. No full suite run.

## FINAL_VERDICT
B0B_IMPLEMENTATION_PASS within targeted code/test scope. Runtime and external benchmark certification remain separate gates.

## FULL_DIFFS
Actual complete diffs for every modified production/test file follow. walkthrough.md is the report and is excluded. README.md and CHANGELOG.md are pre-existing unrelated changes and excluded.

```diff
diff --git a/contextor/core/graph/graph.py b/contextor/core/graph/graph.py
index f2acc62..8f2cb00 100644
--- a/contextor/core/graph/graph.py
+++ b/contextor/core/graph/graph.py
@@ -200,30 +200,50 @@ def resolve_module_edges(module_id: str, module, trie, package_root: str) -> tup
     )
 
     for imp in imports:
-        try:
-            result = resolve_internal(
-                imp,
-                trie,
-                current_module_id=module_id,
-                package_root=package_root,
-            )
-        except Exception:
-            continue
-
-        if result.kind == "UNKNOWN" or not result.target_module:
-            continue
-
-        target = result.target_module
-        if target == module_id:
-            continue
-
-        if _is_type_only_import(imp):
-            _add_edge(soft, module_id, target)
-            continue
-
-        if result.kind == "MODULE":
-            _add_edge(hard, module_id, target)
-        elif result.kind == "FALLBACK":
-            _add_edge(soft, module_id, target)
+        if (
+            imp.is_from_import
+            and imp.level > 0
+            and imp.module is None
+        ):
+            import_variants = [
+                type(imp)(
+                    module=name,
+                    level=imp.level,
+                    names=[],
+                    is_from_import=True,
+                    is_local=imp.is_local,
+                )
+                for name in sorted(set(imp.names))
+                if name != "*"
+            ]
+        else:
+            import_variants = [imp]
+
+        for import_variant in import_variants:
+            try:
+                result = resolve_internal(
+                    import_variant,
+                    trie,
+                    current_module_id=module_id,
+                    package_root=package_root,
+                )
+            except Exception:
+                continue
+
+            if result.kind == "UNKNOWN" or not result.target_module:
+                continue
+
+            target = result.target_module
+            if target == module_id:
+                continue
+
+            if _is_type_only_import(imp):
+                _add_edge(soft, module_id, target)
+                continue
+
+            if result.kind == "MODULE":
+                _add_edge(hard, module_id, target)
+            elif result.kind == "FALLBACK":
+                _add_edge(soft, module_id, target)
 
     return hard[module_id], soft[module_id]
diff --git a/contextor/core/graph/resolver.py b/contextor/core/graph/resolver.py
index 58464cd..2527751 100644
--- a/contextor/core/graph/resolver.py
+++ b/contextor/core/graph/resolver.py
@@ -279,6 +279,20 @@ def resolve_internal(
             kind="MODULE",
         )
 
+    # Package directories are indexed through their
+    # concrete __init__.py module, not as implicit
+    # module identities.
+    if candidate:
+        package_init = _trie_lookup(
+            f"{candidate}.__init__",
+            trie,
+        )
+        if package_init:
+            return ResolutionResult(
+                target_module=package_init,
+                kind="MODULE",
+            )
+
     # ------------------------------------------------------
     # prefix fallback
     # ------------------------------------------------------
diff --git a/contextor/mcp/tools/get_file_edit_context.py b/contextor/mcp/tools/get_file_edit_context.py
index 860d776..f289bfa 100644
--- a/contextor/mcp/tools/get_file_edit_context.py
+++ b/contextor/mcp/tools/get_file_edit_context.py
@@ -442,8 +442,6 @@ def get_file_edit_context(
     parts = list(rel_path.parts)
     if parts and parts[-1].endswith(".py"):
         parts[-1] = parts[-1][:-3]
-        if parts[-1] == "__init__":
-            parts.pop()
 
     module_name = ".".join(parts)
     effective_file_or_target = query_input
diff --git a/tests/test_mcp_regressions.py b/tests/test_mcp_regressions.py
index c120742..c9e5d62 100644
--- a/tests/test_mcp_regressions.py
+++ b/tests/test_mcp_regressions.py
@@ -5193,6 +5193,66 @@ def test_file_edit_context_live_revision_lifecycle(tmp_path, monkeypatch):
     assert "live_revision" not in legacy_res
 
 
+def test_file_edit_context_default_preserves_package_init_identity(tmp_path, monkeypatch):
+    from contextor.core.domain.graph import ProjectGraph
+    from contextor.core.domain.module import Module
+
+    root = tmp_path / "repo"
+    package = root / "pkg"
+    package.mkdir(parents=True)
+    init_file = package / "__init__.py"
+    ordinary_file = package / "example.py"
+    init_file.write_text("VALUE = 1\n", encoding="utf-8")
+    ordinary_file.write_text("VALUE = 2\n", encoding="utf-8")
+
+    registry = PersistentIdentityRegistry(str(root))
+    with registry.transaction():
+        registry.sync_with_workspace({"pkg.__init__", "pkg.example"}, set())
+    package_id = registry.get_module_id("pkg.__init__")
+    ordinary_id = registry.get_module_id("pkg.example")
+
+    state = RepositoryAnalysisState(
+        modules={
+            "pkg.__init__": Module("pkg.__init__", "pkg/__init__.py", str(init_file), []),
+            "pkg.example": Module("pkg.example", "pkg/example.py", str(ordinary_file), []),
+        },
+        artifacts={},
+        dependency_graph=ProjectGraph(
+            hard_edges={"pkg.__init__": set(), "pkg.example": set()},
+            soft_edges={"pkg.__init__": set(), "pkg.example": set()},
+        ),
+    )
+    engine = SimpleNamespace(state=state, state_manager=SimpleNamespace(state_id="fixture"))
+    monkeypatch.setattr(mcp_runtime, "_get_or_init_engine_snapshot", lambda _root: (engine, 1))
+    monkeypatch.setattr(mcp_runtime, "get_or_init_engine", lambda _root: engine)
+
+    minimal = json.loads(
+        mcp_server.get_file_edit_context.fn(
+            repo_path=str(root), file_path="pkg/__init__.py", mode="minimal"
+        )
+    )
+    default = json.loads(
+        mcp_server.get_file_edit_context.fn(
+            repo_path=str(root), file_path="pkg/__init__.py", mode=None
+        )
+    )
+    ordinary = json.loads(
+        mcp_server.get_file_edit_context.fn(
+            repo_path=str(root), file_path="pkg/example.py", mode=None
+        )
+    )
+
+    assert minimal["module"] == "pkg.__init__"
+    assert minimal["module_id"] == package_id
+    assert default["status"] == "available"
+    assert default["module"] == "pkg.__init__"
+    assert default["module_id"] == minimal["module_id"]
+    assert default["state_freshness"]["canonical_state"] == "fresh"
+    assert ordinary["status"] == "available"
+    assert ordinary["module"] == "pkg.example"
+    assert ordinary["module_id"] == ordinary_id
+
+
 def test_file_edit_context_layer_guard(monkeypatch, tmp_path):
     root = tmp_path / "repo"
     root.mkdir()
diff --git a/tests/test_resolver.py b/tests/test_resolver.py
index 36b729d..266ea0c 100644
--- a/tests/test_resolver.py
+++ b/tests/test_resolver.py
@@ -2,13 +2,17 @@
 Import resolution: exact matches, fallbacks and package-root detection.
 """
 
+from pathlib import Path
+
 from contextor.core.domain.imports import ImportRef
 from contextor.core.domain.module import Module
+from contextor.core.graph.graph import build_graph, resolve_module_edges
 from contextor.core.graph.resolver import (
     build_trie,
     detect_package_root,
     resolve_internal,
 )
+from contextor.core.symbol_engine.indexer import read_imports
 
 MODULES = ["core.alpha", "core.beta", "ui.app"]
 
@@ -99,3 +103,83 @@ def test_package_root_detection_yields_none_without_evidence():
     }
 
     assert detect_package_root(modules, _trie()) is None
+
+
+def _package_modules(tmp_path: Path, importer_source: str):
+    package = tmp_path / "pkg"
+    json_package = package / "json"
+    json_package.mkdir(parents=True)
+    importer = package / "__init__.py"
+    importer.write_text(importer_source, encoding="utf-8")
+    (json_package / "__init__.py").write_text("def jsonify(): pass\n", encoding="utf-8")
+    (package / "app.py").write_text("class Flask: pass\n", encoding="utf-8")
+    imports, error = read_imports(importer)
+    assert error is None
+    assert imports is not None
+    modules = {
+        "pkg.__init__": Module("pkg.__init__", "pkg/__init__.py", str(importer), imports),
+        "pkg.json.__init__": Module(
+            "pkg.json.__init__", "pkg/json/__init__.py", str(json_package / "__init__.py"), []
+        ),
+        "pkg.app": Module("pkg.app", "pkg/app.py", str(package / "app.py"), []),
+    }
+    return modules, imports
+
+
+def test_relative_package_init_import_produces_hard_edge(tmp_path):
+    modules, imports = _package_modules(
+        tmp_path,
+        "from .json import jsonify as jsonify\nfrom .app import Flask as Flask\n",
+    )
+    trie = build_trie(modules)
+    json_result = resolve_internal(imports[0], trie, "pkg.__init__", None)
+    app_result = resolve_internal(imports[1], trie, "pkg.__init__", None)
+    assert (json_result.kind, json_result.target_module) == ("MODULE", "pkg.json.__init__")
+    assert (app_result.kind, app_result.target_module) == ("MODULE", "pkg.app")
+    hard, soft = resolve_module_edges("pkg.__init__", modules["pkg.__init__"], trie, None)
+    assert hard == {"pkg.json.__init__", "pkg.app"}
+    assert soft == set()
+    graph = build_graph(modules)
+    assert graph.hard_edges["pkg.__init__"] == hard
+    assert graph.soft_edges["pkg.__init__"] == soft
+    assert "pkg.json" not in modules
+    assert resolve_internal(ImportRef("missing", 1, [], True), trie, "pkg.__init__", None).kind == "UNKNOWN"
+
+
+def test_relative_from_import_multiple_package_targets(tmp_path):
+    modules, imports = _package_modules(tmp_path, "from . import json, app, nonexistent\n")
+    trie = build_trie(modules)
+    assert len(imports) == 1
+    assert imports[0].module is None
+    hard, soft = resolve_module_edges("pkg.__init__", modules["pkg.__init__"], trie, None)
+    assert hard == {"pkg.json.__init__", "pkg.app"}
+    assert soft == set()
+    assert "pkg.__init__" not in hard
+    assert "pkg.nonexistent" not in hard
+    graph = build_graph(modules)
+    assert graph.hard_edges["pkg.__init__"] == hard
+    assert graph.soft_edges["pkg.__init__"] == soft
+
+
+def test_relative_package_import_preserves_nonpackage_behavior(tmp_path):
+    modules, imports = _package_modules(tmp_path, "from .app import Flask\n")
+    trie = build_trie(modules)
+    app_result = resolve_internal(imports[0], trie, "pkg.__init__", None)
+    assert (app_result.kind, app_result.target_module) == ("MODULE", "pkg.app")
+    assert resolve_internal(ImportRef("missing", 1, [], True), trie, "pkg.__init__", None).kind == "UNKNOWN"
+    fallback = resolve_internal(
+        ImportRef("other", 0, ["app"], True),
+        build_trie(["other.app"]),
+        "pkg.__init__",
+        None,
+    )
+    assert (fallback.kind, fallback.target_module) == ("FALLBACK", "other.app")
+    soft_module = Module(
+        "pkg.__init__",
+        "pkg/__init__.py",
+        modules["pkg.__init__"].absolute_path,
+        [ImportRef("json", 1, ["jsonify"], True, type_only=True)],
+    )
+    hard, soft = resolve_module_edges("pkg.__init__", soft_module, trie, None)
+    assert hard == set()
+    assert soft == {"pkg.json.__init__"}
```
