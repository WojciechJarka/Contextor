# C16-B03-P1D3G18-P2-P2

## HEAD_BEFORE/AFTER

`8fd5f39b7fe3b297366ed1f7a05c6b31d6fe4aee` before and after. Initial worktree was clean. No commit or push.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_graph_consistency.py`
- `tests/test_cycle_semantics_package_graph_external_boundary.py`

`walkthrough.md` was overwritten as the required report.

## CPYTHON_IDENTITY

Repository `.venv\Scripts\python.exe`: CPython 3.15.2.

## TARGETED_TEST_RESULTS

Exact three requested modules: **48 passed in 7.74s**, exit code 0. `git diff --check` exited 0.

## IMPORT_IDENTITY_CONTRACT

DIRECT_EVIDENCE: `ExternalImportScopeRecord` now appends `site_ordinal`, `alias_ordinal`, `local_binding`, and ordered `from_members`. Site ordinals derive from import AST nodes sorted by `(lineno, col_offset)`. Each external `ast.Import` alias gets its alias index and actual local binding. Each external `ast.ImportFrom` remains one module-load record with all requested member bindings in source order. Existing lexical scope and legacy external tuple meanings are unchanged. This is source-site identity evidence only; it gives no execution or resolver authority.

## SCC_REPLAY

DIRECT_EVIDENCE: Read-only replay of revision 1088 using current AST, indexed graph, optional source closures and updated classifier. SCC1: 44 members, 201 selected modules, 605 legacy external records, 605 scope records, 605 distinct statement sites, 227 distinct `ast.Import` alias identities, 4 namespace records. SCC2: 9 members, 221 selected modules, 723 legacy external records, 723 scope records, 723 distinct statement sites, 308 distinct `ast.Import` alias identities, 4 namespace records. Every record's site ordinal, line, column, alias/member identity and binding matched its source AST: 0 identity errors. Legacy projection had 0 missing and 0 extra records in both SCCs. Both classifier and `analyze_cycle_scenarios` retained `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`; scenario coverage `NONE`. SCC cohorts overlap.

## SOURCE_BINDING

DIRECT_EVIDENCE: Snapshot metadata and metadata-selected FileState JSON agreed on revision 1088 and state_id `20261106_195021`. Current SHA-256 matched FileState for all 221 selected source files in the union; 0 missing or mismatched. An initial replay aborted on a generation consistency assertion while the writer advanced revision; no unbound result was used. The subsequent complete replay was bound to revision 1088.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP returned canonical revision 1088, `canonical_state=fresh`, `workspace_sync=verified`, no advisory warning, syntax errors 0, structural DFS cycles 16, active warning count 16, model_pass_count 0, and `cycle_semantics=stale` for both modified modules. No production FULL or runtime restart occurred. MCP does not prove that the active backend process adopted the changed classifier; local replay used the current repository interpreter.

## REMAINING_UNKNOWN_GATES

Namespace resolution and external import execution remain unmodeled. No MODEL_PASS or optional /3 receipt was claimed. Active runtime code adoption was not certified.

## FULL_DIFFS

Complete actual Git diff follows.

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index d0a2601..5c4e23c 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -24,6 +24,10 @@ class ExternalImportScopeRecord:
     target: str
     primary_scope: str
     ancestry_flags: tuple[str, ...]
+    site_ordinal: int
+    alias_ordinal: int | None = None
+    local_binding: str | None = None
+    from_members: tuple[tuple[str, str], ...] = ()
 
 
 @dataclass(frozen=True)
@@ -39,7 +43,7 @@ class PackageGraphConsistency:
 
 def _external_import_scope_index(
     tree: ast.Module,
-) -> dict[int, tuple[str, tuple[str, ...]]]:
+) -> dict[int, tuple[str, tuple[str, ...], int]]:
     """Classify lexical import locations, never execution safety."""
     parents: dict[int, ast.AST | None] = {id(tree): None}
 
@@ -52,11 +56,21 @@ def _external_import_scope_index(
     loop_types = (ast.For, ast.AsyncFor, ast.While)
     with_types = (ast.With, ast.AsyncWith)
 
-    result: dict[int, tuple[str, tuple[str, ...]]] = {}
+    result: dict[int, tuple[str, tuple[str, ...], int]] = {}
+
+    import_nodes = sorted(
+        (
+            node
+            for node in ast.walk(tree)
+            if isinstance(node, (ast.Import, ast.ImportFrom))
+        ),
+        key=lambda node: (
+            node.lineno,
+            node.col_offset,
+        ),
+    )
 
-    for node in ast.walk(tree):
-        if not isinstance(node, (ast.Import, ast.ImportFrom)):
-            continue
+    for site_ordinal, node in enumerate(import_nodes):
 
         ancestors: list[ast.AST] = []
         parent = parents.get(id(node))
@@ -123,7 +137,11 @@ def _external_import_scope_index(
         if any(isinstance(item, ast.Match) for item in ancestors):
             flags.append("MATCH")
 
-        result[id(node)] = (primary, tuple(flags))
+        result[id(node)] = (
+            primary,
+            tuple(flags),
+            site_ordinal,
+        )
 
     return result
 
@@ -429,7 +447,7 @@ def assess_package_graph_consistency(
                 continue
 
             if isinstance(node, ast.Import):
-                for alias in node.names:
+                for alias_ordinal, alias in enumerate(node.names):
                     if not all(part.isidentifier() for part in alias.name.split(".")):
                         return unknown("UNSUPPORTED_IMPORT_FORM")
                     resolved = target(alias.name)
@@ -446,16 +464,21 @@ def assess_package_graph_consistency(
                         unmodeled_external_imports.append(
                             (module_id, node.lineno, "import", alias.name)
                         )
-                        primary, flags = scope_index[id(node)]
+                        primary, flags, site_ordinal = scope_index[id(node)]
                         external_scopes.append(
                             ExternalImportScopeRecord(
-                                module_id,
-                                node.lineno,
-                                node.col_offset,
-                                "import",
-                                alias.name,
-                                primary,
-                                flags,
+                                importer=module_id,
+                                line=node.lineno,
+                                column=node.col_offset,
+                                form="import",
+                                target=alias.name,
+                                primary_scope=primary,
+                                ancestry_flags=flags,
+                                site_ordinal=site_ordinal,
+                                alias_ordinal=alias_ordinal,
+                                local_binding=(
+                                    alias.asname or alias.name.split(".")[0]
+                                ),
                             )
                         )
                         continue
@@ -511,16 +534,24 @@ def assess_package_graph_consistency(
                     unmodeled_external_imports.append(
                         (module_id, node.lineno, "from", base)
                     )
-                    primary, flags = scope_index[id(node)]
+                    primary, flags, site_ordinal = scope_index[id(node)]
                     external_scopes.append(
                         ExternalImportScopeRecord(
-                            module_id,
-                            node.lineno,
-                            node.col_offset,
-                            "from",
-                            base,
-                            primary,
-                            flags,
+                            importer=module_id,
+                            line=node.lineno,
+                            column=node.col_offset,
+                            form="from",
+                            target=base,
+                            primary_scope=primary,
+                            ancestry_flags=flags,
+                            site_ordinal=site_ordinal,
+                            from_members=tuple(
+                                (
+                                    alias.name,
+                                    alias.asname or alias.name,
+                                )
+                                for alias in node.names
+                            ),
                         )
                     )
                     continue
@@ -614,6 +645,12 @@ def assess_package_graph_consistency(
                 row.column,
                 row.primary_scope,
                 row.ancestry_flags,
+                row.site_ordinal,
+                (
+                    row.alias_ordinal
+                    if row.alias_ordinal is not None
+                    else -1
+                ),
             ),
         )
     )
diff --git a/tests/test_cycle_semantics_package_graph_external_boundary.py b/tests/test_cycle_semantics_package_graph_external_boundary.py
index 3863fc7..089dbf8 100644
--- a/tests/test_cycle_semantics_package_graph_external_boundary.py
+++ b/tests/test_cycle_semantics_package_graph_external_boundary.py
@@ -243,3 +243,95 @@ def test_g18_p2_p1_deterministic_scope_records():
 
     assert first == second
     assert first.external_scope_records == second.external_scope_records
+
+
+def test_g18_p2_p2_repeated_target_alias_identity():
+    result = _check(
+        "import os as first, os as second\n"
+    )
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+
+    records = result.external_scope_records
+    assert len(records) == 2
+    assert {row.site_ordinal for row in records} == {0}
+    assert [row.alias_ordinal for row in records] == [0, 1]
+    assert [row.local_binding for row in records] == [
+        "first", "second"
+    ]
+    assert [row.target for row in records] == ["os", "os"]
+
+
+def test_g18_p2_p2_from_member_identity():
+    result = _check(
+        "from collections import Counter as C, deque\n"
+    )
+
+    records = result.external_scope_records
+    assert len(records) == 1
+    assert records[0].site_ordinal == 0
+    assert records[0].alias_ordinal is None
+    assert records[0].local_binding is None
+    assert records[0].from_members == (
+        ("Counter", "C"),
+        ("deque", "deque"),
+    )
+
+
+def test_g18_p2_p2_lexical_not_ast_walk_order():
+    result = _check(
+        "def deferred():\n"
+        "    import os\n"
+        "import json\n"
+    )
+
+    ordered = sorted(
+        result.external_scope_records,
+        key=lambda row: row.site_ordinal,
+    )
+
+    assert [
+        (row.target, row.site_ordinal)
+        for row in ordered
+    ] == [
+        ("os", 0),
+        ("json", 1),
+    ]
+
+
+def test_g18_p2_p2_same_line_separate_sites():
+    result = _check(
+        "import pathlib; import pathlib\n"
+    )
+
+    records = result.external_scope_records
+    assert len(records) == 2
+    assert {row.site_ordinal for row in records} == {0, 1}
+    assert len({row.column for row in records}) == 2
+
+
+def test_g18_p2_p2_legacy_projection_unchanged():
+    result = _check(
+        "import os as first, os as second\n"
+        "from collections import Counter, deque\n"
+    )
+
+    projected = tuple(sorted(
+        (row.importer, row.line, row.form, row.target)
+        for row in result.external_scope_records
+    ))
+
+    assert projected == tuple(sorted(
+        result.unmodeled_external_imports
+    ))
+
+
+def test_g18_p2_p2_unknown_stays_fail_closed():
+    result = _check(
+        "import os\n"
+        "import pkg.missing\n"
+    )
+
+    assert result.reason == "MISSING_INDEXED_TARGET"
+    assert result.external_scope_records == ()
```

## FINAL_VERDICT

PASS — literal identity hardening, 48 targeted tests passed, both FileState-bound SCC replays preserved fail-closed status and 16 structural cycles.
