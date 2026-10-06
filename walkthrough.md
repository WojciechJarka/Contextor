STATUS=STEP_PASS
HEAD_BEFORE=d206febc7c5f002a3423d6296c1410412d05f99b
HEAD_AFTER=d206febc7c5f002a3423d6296c1410412d05f99b
SOURCE_DRIFT=NONE
SHARED_REEXPORT_EXTRACTION_CONTRACT=PASS
REPEATED_ALL_CONTRACT=LAST_SUPPORTED_TOP_LEVEL_ASSIGNMENT_WINS
COMPACT_LEGACY_PARITY=PASS
DUPLICATE_HELPERS_REMOVED=YES
TEST_RESULTS=8/8 PASS
MCP_RESTART_REQUIRED=YES_BEFORE_AN_ALREADY_RUNNING_LONG_LIVED_MCP_PYTHON_PROCESS_EXECUTES_THE_CHANGED_IMPLEMENTATION; NOT_PERFORMED

# CPA_FILE_UPDATE_UNIFIED_REEXPORT_SEMANTICS

## Pre-edit evidence and scope

- HEAD before editing: d206febc7c5f002a3423d6296c1410412d05f99b.
- Git worktree was clean before editing; all four named files matched HEAD. No source drift in requested anchors.
- Contextor get_file_edit_context before editing reported canonical revision 1484, LIVE, workspace_sync=verified, syntax diagnostics fresh for shared.py, index.py and both target tests. It identified shared.py callers index.py and engine.py; index.py has eight static consumers including the compact semantic core test.
- No source outside the two requested production files and two requested test files was edited. No MCP update_file, restart, or full repository pytest suite was run.

## SHARED_REEXPORT_EXTRACTION_CONTRACT

- shared.py now owns the sole source-local _extract_reexport_facts and pure-RAM _assemble_reexport_map.
- On a cache miss, _build_reexport_map preserves the existing _REEXPORT_CACHE key and performs the current module iteration and ast_tree access, extracts one fact record per available AST, then invokes the shared assembler.
- The index compact path imports both shared helpers. extract_compact_reference_facts uses the shared source-local extractor without changing compact output shape.
- from_compact_facts retains missing/failure-envelope validation, selects facts only for current modules with status=available and dict facts, then passes facts.reexports to the shared assembler. status=unavailable remains excluded from assembly, as before.
- The shared extractor processes top-level assignments in source order. An unsupported assignment produces an empty explicit export set; a later supported assignment replaces it. No dynamic expression is evaluated.

## REPEATED_ALL_CONTRACT

- test_repeated_all_uses_last_assignment_consistently covers two literal top-level assignments and verifies only the final exported binding.
- test_repeated_all_dynamic_then_literal_uses_last_assignment covers an unsupported dynamic assignment followed by a literal assignment and verifies the latter controls the map.
- Both targeted tests passed.

## COMPACT_LEGACY_PARITY

- test_compact_and_ast_reexport_maps_are_identical_for_repeated_all builds compact current-run facts and compares RepositoryReferenceIndex.reexports with _build_reexport_map for the repeated-literal fixture.
- The new equality test passed. Existing requested alias/transitive, star, cycle, shadowing, and compact-vs-build regression nodes also passed.

## DUPLICATE_HELPERS_REMOVED

- Literal search found no _explicit_all in contextor/core.
- _extract_reexport_facts and _assemble_reexport_map each have one definition, in shared.py. index.py imports and calls them; it no longer defines local duplicates.
- _build_reexport_map remains in shared.py and uses both shared helpers on cache miss.

## TARGETED_TESTS

One physical Windows pytest command ran exactly these eight node IDs:

& .\.venv\Scripts\python.exe -m pytest -q tests/test_reexport_reference_semantics.py::test_repeated_all_uses_last_assignment_consistently tests/test_reexport_reference_semantics.py::test_repeated_all_dynamic_then_literal_uses_last_assignment tests/test_reference_fusion_semantic_core.py::test_compact_and_ast_reexport_maps_are_identical_for_repeated_all tests/test_reexport_reference_semantics.py::test_transitive_aliased_reexport_resolves_to_original_artifact tests/test_reexport_reference_semantics.py::test_star_reexport_uses_explicit_all_and_remains_transitive tests/test_reexport_reference_semantics.py::test_cyclic_reexports_are_not_resolved_arbitrarily tests/test_reexport_reference_semantics.py::test_local_definition_shadows_earlier_imported_binding tests/test_reference_fusion_semantic_core.py::test_ast_build_exactly_equals_compact_facts_build

## TEST_RESULTS

- Result: 8 passed in 3.76s.
- Full repository pytest suite: not run.
- git diff --check: exit code 0; Git emitted only its Windows LF-to-CRLF working-copy advisory for modified text files.

## LIVE AND RESTART

- A single get_live_events query after pre-edit revision 1484 showed desktop_watcher update events for the changed Python/test paths, with latest revision 1491 and continuity=continuous, resync_required=false.
- Post-edit get_file_edit_context for shared.py reported canonical_revision=1491, provenance=live, workspace_sync=verified, no warnings.
- The watcher events establish canonical LIVE source updates. They do not establish that a pre-existing long-lived Python MCP process reloaded imported code. No restart was performed; restart is required before certifying changed implementation execution in such an already-running process. Pytest used a fresh process.

## FILES_CHANGED

- C:/Temp/Contextor_Repo/contextor/core/reference/shared.py
- C:/Temp/Contextor_Repo/contextor/core/reference/index.py
- C:/Temp/Contextor_Repo/tests/test_reexport_reference_semantics.py
- C:/Temp/Contextor_Repo/tests/test_reference_fusion_semantic_core.py

FINAL_PASS_FOR_FILE_UPDATE_COMPLETENESS=NOT_CLAIMED

## ACTUAL_DIFF/FULL_DIFF

The following is the complete Git diff from HEAD for every changed production/test file. walkthrough.md is the report and is excluded.


### contextor/core/reference/shared.py

```diff
diff --git a/contextor/core/reference/shared.py b/contextor/core/reference/shared.py
index a6c8b2b..1e81f39 100644
--- a/contextor/core/reference/shared.py
+++ b/contextor/core/reference/shared.py
@@ -25,107 +25,276 @@ def reset_reexport_cache() -> None:
     _REEXPORT_CACHE.clear()
 
 
-def _explicit_all(tree: Any) -> set[str] | None:
-    """Extract explicit __all__ string sequence if defined in AST root."""
-    for node in getattr(tree, "body", []):
-        if not isinstance(node, ast.Assign):
-            continue
-        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
-            continue
-        if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
-            return {
-                item.value
-                for item in node.value.elts
-                if isinstance(item, ast.Constant) and isinstance(item.value, str)
-            }
-        return set()
-    return None
-
-
 def _export_module_name(module_id: str) -> str:
     """Normalize package __init__ module ID to parent package identity."""
     return module_id.removesuffix(".__init__")
 
 
-def _build_reexport_map(modules: dict) -> dict[str, str]:
-    """Build cycle-safe transitive identities for top-level ImportFrom re-exports."""
-    cache_key = (id(modules), len(modules))
-    cached = _REEXPORT_CACHE.get(cache_key)
-    if cached is not None:
-        return cached
+def _extract_reexport_facts(
+    module_id: str,
+    tree: Any,
+) -> dict[str, Any]:
+    """
+    Extract source-local inputs required for global re-export assembly.
+
+    Top-level __all__ follows Python execution order: when assigned
+    repeatedly, the last supported assignment is authoritative.
+    """
+    exporter = _export_module_name(module_id)
+    explicit_all: list[str] | None = None
+    bindings: dict[str, str] = {}
+    star_sources: list[str] = []
+
+    for node in getattr(tree, "body", []):
+        if isinstance(node, ast.Assign) and any(
+            isinstance(target, ast.Name)
+            and target.id == "__all__"
+            for target in node.targets
+        ):
+            if isinstance(
+                node.value,
+                (
+                    ast.List,
+                    ast.Tuple,
+                    ast.Set,
+                ),
+            ):
+                explicit_all = [
+                    item.value
+                    for item in node.value.elts
+                    if isinstance(item, ast.Constant)
+                    and isinstance(item.value, str)
+                ]
+            else:
+                explicit_all = []
+
+        if isinstance(node, ast.ImportFrom):
+            source = _absolute_import_module(
+                module_id,
+                node.module,
+                node.level or 0,
+            )
+
+            for item in node.names:
+                if item.name == "*":
+                    star_sources.append(source)
+                else:
+                    bindings[
+                        item.asname or item.name
+                    ] = f"{source}.{item.name}"
+
+        elif isinstance(
+            node,
+            (
+                ast.FunctionDef,
+                ast.AsyncFunctionDef,
+                ast.ClassDef,
+            ),
+        ):
+            bindings[node.name] = (
+                f"{exporter}.{node.name}"
+            )
+
+        elif isinstance(
+            node,
+            (
+                ast.Assign,
+                ast.AnnAssign,
+            ),
+        ):
+            targets = (
+                node.targets
+                if isinstance(node, ast.Assign)
+                else [node.target]
+            )
+            value = node.value
 
+            for target in targets:
+                if (
+                    not isinstance(target, ast.Name)
+                    or target.id == "__all__"
+                ):
+                    continue
+
+                if (
+                    isinstance(value, ast.Name)
+                    and value.id in bindings
+                ):
+                    bindings[target.id] = bindings[
+                        value.id
+                    ]
+                else:
+                    bindings[target.id] = (
+                        f"{exporter}.{target.id}"
+                    )
+
+    return {
+        "exporter": exporter,
+        "explicit_all": explicit_all,
+        "bindings": bindings,
+        "star_sources": star_sources,
+    }
+
+
+def _assemble_reexport_map(
+    reexport_facts_by_module: dict[str, dict[str, Any]],
+) -> dict[str, str]:
+    """
+    Assemble cycle-safe transitive re-export identities from complete
+    source-local re-export facts.
+
+    Performs no source or filesystem I/O.
+    """
     raw: dict[str, str] = {}
     module_exports: dict[str, dict[str, str]] = {}
-    star_imports: list[tuple[str, str, set[str] | None]] = []
+    star_imports: list[
+        tuple[str, str, set[str] | None]
+    ] = []
 
-    for module_id, module in modules.items():
-        tree = getattr(module, "ast_tree", None)
-        if tree is None:
-            continue
-        exporter = _export_module_name(module_id)
-        allowed = _explicit_all(tree)
-        bindings: dict[str, str] = {}
-        for node in tree.body:
-            if isinstance(node, ast.ImportFrom):
-                source = _absolute_import_module(
-                    module_id, node.module, node.level or 0
-                )
-                for item in node.names:
-                    if item.name == "*":
-                        star_imports.append((exporter, source, allowed))
-                        continue
-                    bindings[item.asname or item.name] = f"{source}.{item.name}"
-            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
-                bindings[node.name] = f"{exporter}.{node.name}"
-            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
-                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
-                value = node.value
-                for target in targets:
-                    if not isinstance(target, ast.Name) or target.id == "__all__":
-                        continue
-                    if isinstance(value, ast.Name) and value.id in bindings:
-                        bindings[target.id] = bindings[value.id]
-                    else:
-                        bindings[target.id] = f"{exporter}.{target.id}"
-
-        visible_bindings = {}
-        for local, target in bindings.items():
-            if allowed is not None and local not in allowed:
+    for reexport in reexport_facts_by_module.values():
+        exporter = reexport["exporter"]
+        explicit_all = reexport["explicit_all"]
+        allowed = (
+            None
+            if explicit_all is None
+            else set(explicit_all)
+        )
+
+        visible_bindings: dict[str, str] = {}
+
+        for local, target in reexport[
+            "bindings"
+        ].items():
+            if (
+                allowed is not None
+                and local not in allowed
+            ):
                 continue
-            if allowed is None and local.startswith("_"):
+
+            if (
+                allowed is None
+                and local.startswith("_")
+            ):
                 continue
+
             visible_bindings[local] = target
+
             key = f"{exporter}.{local}"
+
             if key != target:
                 raw[key] = target
-        module_exports[exporter] = visible_bindings
+
+        module_exports[exporter] = (
+            visible_bindings
+        )
+
+        for source in reexport[
+            "star_sources"
+        ]:
+            star_imports.append(
+                (
+                    exporter,
+                    source,
+                    allowed,
+                )
+            )
 
     changed = True
+
     while changed:
         changed = False
+
         for exporter, source, allowed in star_imports:
-            for local, target in list(module_exports.get(source, {}).items()):
-                if allowed is not None and local not in allowed:
+            for local, target in list(
+                module_exports.get(
+                    source,
+                    {},
+                ).items()
+            ):
+                if (
+                    allowed is not None
+                    and local not in allowed
+                ):
                     continue
-                if allowed is None and local.startswith("_"):
+
+                if (
+                    allowed is None
+                    and local.startswith("_")
+                ):
                     continue
+
                 key = f"{exporter}.{local}"
+
                 if key not in raw:
                     raw[key] = target
-                    module_exports.setdefault(exporter, {})[local] = target
+                    module_exports.setdefault(
+                        exporter,
+                        {},
+                    )[local] = target
                     changed = True
 
-    resolved = {}
+    resolved: dict[str, str] = {}
+
     for key, initial in raw.items():
         target = initial
         visited = {key}
-        while target in raw and target not in visited:
+
+        while (
+            target in raw
+            and target not in visited
+        ):
             visited.add(target)
             target = raw[target]
+
         if target not in visited:
             resolved[key] = target
 
-    _REEXPORT_CACHE[cache_key] = resolved
+    return resolved
+
+
+def _build_reexport_map(
+    modules: dict,
+) -> dict[str, str]:
+    """Build cycle-safe transitive identities for top-level re-exports."""
+    cache_key = (
+        id(modules),
+        len(modules),
+    )
+
+    cached = _REEXPORT_CACHE.get(
+        cache_key
+    )
+
+    if cached is not None:
+        return cached
+
+    reexport_facts_by_module = {}
+
+    for module_id, module in modules.items():
+        tree = getattr(
+            module,
+            "ast_tree",
+            None,
+        )
+
+        if tree is None:
+            continue
+
+        reexport_facts_by_module[
+            module_id
+        ] = _extract_reexport_facts(
+            module_id,
+            tree,
+        )
+
+    resolved = _assemble_reexport_map(
+        reexport_facts_by_module
+    )
+
+    _REEXPORT_CACHE[
+        cache_key
+    ] = resolved
+
     return resolved
 
 
```

### contextor/core/reference/index.py

```diff
diff --git a/contextor/core/reference/index.py b/contextor/core/reference/index.py
index 71c23d3..8e7888a 100644
--- a/contextor/core/reference/index.py
+++ b/contextor/core/reference/index.py
@@ -31,7 +31,9 @@ from .resolution import (
     _resolve_reexport,
 )
 from .shared import (
+    _assemble_reexport_map,
     _empty_reference,
+    _extract_reexport_facts,
     _normalize_references,
 )
 from .visitor import _is_event_binding_call
@@ -302,61 +304,6 @@ class SinglePassConsumerVisitor(ast.NodeVisitor):
         self.class_stack.pop()
 
 
-def _extract_reexport_facts(
-    module_id: str,
-    tree: ast.AST,
-) -> dict[str, Any]:
-    """Extract JSON-safe, source-local inputs for global re-export assembly."""
-    exporter = module_id.removesuffix(".__init__")
-    explicit_all: list[str] | None = None
-    bindings: dict[str, str] = {}
-    star_sources: list[str] = []
-
-    for node in getattr(tree, "body", []):
-        if isinstance(node, ast.Assign) and any(
-            isinstance(target, ast.Name) and target.id == "__all__"
-            for target in node.targets
-        ):
-            if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
-                explicit_all = [
-                    item.value
-                    for item in node.value.elts
-                    if isinstance(item, ast.Constant)
-                    and isinstance(item.value, str)
-                ]
-            else:
-                explicit_all = []
-
-        if isinstance(node, ast.ImportFrom):
-            source = _absolute_import_module(
-                module_id, node.module, node.level or 0
-            )
-            for item in node.names:
-                if item.name == "*":
-                    star_sources.append(source)
-                else:
-                    bindings[item.asname or item.name] = f"{source}.{item.name}"
-        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
-            bindings[node.name] = f"{exporter}.{node.name}"
-        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
-            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
-            value = node.value
-            for target in targets:
-                if not isinstance(target, ast.Name) or target.id == "__all__":
-                    continue
-                if isinstance(value, ast.Name) and value.id in bindings:
-                    bindings[target.id] = bindings[value.id]
-                else:
-                    bindings[target.id] = f"{exporter}.{target.id}"
-
-    return {
-        "exporter": exporter,
-        "explicit_all": explicit_all,
-        "bindings": bindings,
-        "star_sources": star_sources,
-    }
-
-
 def extract_compact_reference_facts(
     module_id: str,
     module: Any = None,
@@ -412,60 +359,6 @@ def extract_compact_reference_facts(
         }
 
 
-def _assemble_reexport_map(compact_facts: dict[str, dict[str, Any]]) -> dict[str, str]:
-    """Assemble cycle-safe transitive re-exports from source-local facts."""
-    raw: dict[str, str] = {}
-    module_exports: dict[str, dict[str, str]] = {}
-    star_imports: list[tuple[str, str, set[str] | None]] = []
-
-    for envelope in compact_facts.values():
-        if envelope["status"] != "available":
-            continue
-        reexport = envelope["facts"]["reexports"]
-        exporter = reexport["exporter"]
-        explicit_all = reexport["explicit_all"]
-        allowed = None if explicit_all is None else set(explicit_all)
-        visible_bindings: dict[str, str] = {}
-        for local, target in reexport["bindings"].items():
-            if allowed is not None and local not in allowed:
-                continue
-            if allowed is None and local.startswith("_"):
-                continue
-            visible_bindings[local] = target
-            key = f"{exporter}.{local}"
-            if key != target:
-                raw[key] = target
-        module_exports[exporter] = visible_bindings
-        for source in reexport["star_sources"]:
-            star_imports.append((exporter, source, allowed))
-
-    changed = True
-    while changed:
-        changed = False
-        for exporter, source, allowed in star_imports:
-            for local, target in list(module_exports.get(source, {}).items()):
-                if allowed is not None and local not in allowed:
-                    continue
-                if allowed is None and local.startswith("_"):
-                    continue
-                key = f"{exporter}.{local}"
-                if key not in raw:
-                    raw[key] = target
-                    module_exports.setdefault(exporter, {})[local] = target
-                    changed = True
-
-    resolved: dict[str, str] = {}
-    for key, initial in raw.items():
-        target = initial
-        visited = {key}
-        while target in raw and target not in visited:
-            visited.add(target)
-            target = raw[target]
-        if target not in visited:
-            resolved[key] = target
-    return resolved
-
-
 class RepositoryReferenceIndex:
     """
     Run-scoped repository-wide reference index built in a single AST pass.
@@ -544,7 +437,22 @@ class RepositoryReferenceIndex:
             )
             raise RuntimeError(f"Compact reference extraction failed: {details}")
 
-        reexports = _assemble_reexport_map(compact_facts)
+        reexport_facts_by_module = {
+            module_id: envelope["facts"]["reexports"]
+            for module_id, envelope in compact_facts.items()
+            if (
+                module_id in modules
+                and envelope.get("status") == "available"
+                and isinstance(
+                    envelope.get("facts"),
+                    dict,
+                )
+            )
+        }
+
+        reexports = _assemble_reexport_map(
+            reexport_facts_by_module
+        )
 
         direct_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
         instance_calls_by_target: dict[str, list[tuple[str, Optional[int], Optional[str]]]] = defaultdict(list)
```

### tests/test_reexport_reference_semantics.py

```diff
diff --git a/tests/test_reexport_reference_semantics.py b/tests/test_reexport_reference_semantics.py
index 166918e..843a2a7 100644
--- a/tests/test_reexport_reference_semantics.py
+++ b/tests/test_reexport_reference_semantics.py
@@ -163,3 +163,70 @@ def test_compact_artifact_pipeline_attributes_reexport_consumers_to_origin(
     assert not failures
     assert artifacts["provider::run"]["consumers"] == ["consumer", "facade"]
     assert artifacts["provider::run"]["consumer_count"] == 2
+
+
+
+def test_repeated_all_uses_last_assignment_consistently(
+    tmp_path,
+):
+    (tmp_path / "provider.py").write_text(
+        "def first():\n"
+        "    return 1\n"
+        "\n"
+        "def second():\n"
+        "    return 2\n",
+        encoding="utf-8",
+    )
+
+    (tmp_path / "facade.py").write_text(
+        "from provider import first, second\n"
+        "__all__ = ['first']\n"
+        "__all__ = ['second']\n",
+        encoding="utf-8",
+    )
+
+    modules = index_repository(
+        str(tmp_path)
+    ).modules
+
+    legacy_mapping = _build_reexport_map(
+        modules
+    )
+
+    assert (
+        "facade.first"
+        not in legacy_mapping
+    )
+    assert (
+        legacy_mapping["facade.second"]
+        == "provider.second"
+    )
+
+
+def test_repeated_all_dynamic_then_literal_uses_last_assignment(
+    tmp_path,
+):
+    (tmp_path / "provider.py").write_text(
+        "def run():\n"
+        "    return 1\n",
+        encoding="utf-8",
+    )
+
+    (tmp_path / "facade.py").write_text(
+        "from provider import run\n"
+        "__all__ = make_exports()\n"
+        "__all__ = ['run']\n",
+        encoding="utf-8",
+    )
+
+    modules = index_repository(
+        str(tmp_path)
+    ).modules
+
+    mapping = _build_reexport_map(
+        modules
+    )
+
+    assert mapping["facade.run"] == (
+        "provider.run"
+    )
```

### tests/test_reference_fusion_semantic_core.py

```diff
diff --git a/tests/test_reference_fusion_semantic_core.py b/tests/test_reference_fusion_semantic_core.py
index cc8dd14..d7e5950 100644
--- a/tests/test_reference_fusion_semantic_core.py
+++ b/tests/test_reference_fusion_semantic_core.py
@@ -7,6 +7,9 @@ from contextor.core.reference.index import (
     SinglePassConsumerVisitor,
     extract_compact_reference_facts,
 )
+from contextor.core.reference.shared import (
+    _build_reexport_map,
+)
 from contextor.core.symbol_engine.indexer import index_repository
 
 
@@ -141,3 +144,46 @@ def test_compact_build_rejects_missing_module_facts(tmp_path):
         RepositoryReferenceIndex.from_compact_facts(
             modules, str(tmp_path), compact
         )
+
+
+
+def test_compact_and_ast_reexport_maps_are_identical_for_repeated_all(
+    tmp_path,
+):
+    (tmp_path / "provider.py").write_text(
+        "def first():\n"
+        "    return 1\n"
+        "\n"
+        "def second():\n"
+        "    return 2\n",
+        encoding="utf-8",
+    )
+
+    (tmp_path / "facade.py").write_text(
+        "from provider import first, second\n"
+        "__all__ = ['first']\n"
+        "__all__ = ['second']\n",
+        encoding="utf-8",
+    )
+
+    modules = index_repository(
+        str(tmp_path)
+    ).modules
+
+    compact = {
+        module_id: extract_compact_reference_facts(
+            module_id,
+            module,
+        )
+        for module_id, module in modules.items()
+    }
+
+    compact_index = RepositoryReferenceIndex.from_compact_facts(
+        modules,
+        str(tmp_path),
+        compact,
+    )
+
+    assert _build_reexport_map(
+        modules
+    ) == compact_index.reexports
```
