# C16-B03-P1D3G18-P2-P1

## HEAD_BEFORE/AFTER

`1b52d9a9f50ce704f75191eb8ef139299935e324` before and after. Initial worktree contained only modified `walkthrough.md`. No Git mutation.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_graph_consistency.py`
- `tests/test_cycle_semantics_package_graph_external_boundary.py`

`walkthrough.md` was overwritten as the required report.

## CPYTHON_IDENTITY

`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`: Python 3.15.2. No interpreter switch.

## TARGETED_TEST_RESULTS

`python.exe -m pytest -q -rs` on the three specified modules: **42 passed in 46.19s**, exit code 0.

## LEXICAL_SCOPE_CONTRACT

DIRECT_EVIDENCE: Added frozen `ExternalImportScopeRecord` and appended `external_scope_records` to `PackageGraphConsistency`. The classifier derives primary scope and ancestry flags from AST parents. External `Import` and absolute `ImportFrom` candidates retain importer, line, column, form and target; multiple aliases and same-line statements remain distinct. Terminal INDETERMINATE results carry sorted records; CONSISTENT and early failure paths retain the empty default. No status, reason, graph, simulator, warning or MODEL_PASS policy was changed. These records prove lexical placement only, not execution timing, branch outcome or external import safety.

## SCC1_AND_SCC2_REPLAY

DIRECT_EVIDENCE: Read-only `load_snapshot` plus `compute_cycle_model_source_closures_with_optional_children` and updated `assess_package_graph_consistency` against revision 1086. SCC1: 44 members, 201 selected modules; 605 external candidates and 605 scope records; primary scopes MODULE_BODY 555, FUNCTION_BODY 24, METHOD_BODY 26; secondary flags IF 30, TRY 30, EXCEPT_HANDLER 4, LOOP 11. SCC2: 9 members, 221 selected modules; 723 candidates and 723 records; MODULE_BODY 647, FUNCTION_BODY 32, METHOD_BODY 44; IF 42, TRY 45, EXCEPT_HANDLER 5, LOOP 17. Both have zero missing or extra projected sites, 4 namespace records, and remain `INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED`. Counts match the historical reference. SCC cohorts overlap and were not summed.

## SOURCE_BINDING

DIRECT_EVIDENCE: Snapshot metadata and separate canonical FileState metadata both reported revision 1086 and state_id `20261106_195021`. Current SHA-256 matched FileState for 201/201 SCC1 and 221/221 SCC2 selected source files; zero missing or mismatched fingerprints. The first diagnostic attempt read the empty legacy `state.file_state` field; binding was confirmed only after reading the metadata-selected FileState JSON. No canonical FULL or source mutation was performed by replay.

## MCP_POST_CHANGE_AUDIT

DIRECT_EVIDENCE: Contextor MCP returned revision 1086, `canonical_state=fresh`, `workspace_sync=verified`, no advisory warning, syntax errors 0, structural DFS cycles 16, active warnings 16, model_pass_count 0, `cycle_semantics=stale` for the changed production and test modules. Runtime adoption of the modified classifier was not claimed; replay invoked current source in the local Python process.

## REMAINING_INDETERMINATE_GATES

Both SCCs retain namespace import resolution and opaque external import execution uncertainty. Existing scenario status remains INDETERMINATE. No /3 receipt or MODEL_PASS claim was made.

## FULL_DIFFS

Complete actual Git diff follows.

```diff
diff --git a/contextor/core/cycle_semantics/package_graph_consistency.py b/contextor/core/cycle_semantics/package_graph_consistency.py
index 4e1d4de..d0a2601 100644
--- a/contextor/core/cycle_semantics/package_graph_consistency.py
+++ b/contextor/core/cycle_semantics/package_graph_consistency.py
@@ -15,6 +15,17 @@ from .typing_guard import (
 )
 
 
+@dataclass(frozen=True)
+class ExternalImportScopeRecord:
+    importer: str
+    line: int
+    column: int
+    form: str
+    target: str
+    primary_scope: str
+    ancestry_flags: tuple[str, ...]
+
+
 @dataclass(frozen=True)
 class PackageGraphConsistency:
     status: str
@@ -23,6 +34,98 @@ class PackageGraphConsistency:
     unmodeled_namespace_parents: tuple[tuple[str, int, str, str], ...] = ()
     internal_graph_state: str = "NOT_PROVED"
     checked_source_modules: tuple[str, ...] = ()
+    external_scope_records: tuple[ExternalImportScopeRecord, ...] = ()
+
+
+def _external_import_scope_index(
+    tree: ast.Module,
+) -> dict[int, tuple[str, tuple[str, ...]]]:
+    """Classify lexical import locations, never execution safety."""
+    parents: dict[int, ast.AST | None] = {id(tree): None}
+
+    for parent in ast.walk(tree):
+        for child in ast.iter_child_nodes(parent):
+            parents[id(child)] = parent
+
+    function_types = (ast.FunctionDef, ast.AsyncFunctionDef)
+    try_types = (ast.Try, getattr(ast, "TryStar", ast.Try))
+    loop_types = (ast.For, ast.AsyncFor, ast.While)
+    with_types = (ast.With, ast.AsyncWith)
+
+    result: dict[int, tuple[str, tuple[str, ...]]] = {}
+
+    for node in ast.walk(tree):
+        if not isinstance(node, (ast.Import, ast.ImportFrom)):
+            continue
+
+        ancestors: list[ast.AST] = []
+        parent = parents.get(id(node))
+
+        while parent is not None:
+            ancestors.append(parent)
+            parent = parents.get(id(parent))
+
+        ancestors.reverse()
+
+        definitions = [
+            item for item in ancestors
+            if isinstance(item, (*function_types, ast.ClassDef))
+        ]
+
+        function_positions = [
+            index for index, item in enumerate(definitions)
+            if isinstance(item, function_types)
+        ]
+
+        if function_positions:
+            position = function_positions[-1]
+            function = definitions[position]
+
+            if (
+                position > 0
+                and isinstance(definitions[position - 1], ast.ClassDef)
+            ):
+                primary = "METHOD_BODY"
+            elif isinstance(function, ast.AsyncFunctionDef):
+                primary = "ASYNC_FUNCTION_BODY"
+            else:
+                primary = "FUNCTION_BODY"
+
+        elif any(
+            isinstance(item, ast.ClassDef)
+            for item in definitions
+        ):
+            primary = "CLASS_BODY"
+
+        else:
+            primary = "MODULE_BODY"
+
+        flags: list[str] = []
+
+        if any(isinstance(item, ast.If) for item in ancestors):
+            flags.append("IF")
+
+        if any(isinstance(item, try_types) for item in ancestors):
+            flags.append("TRY")
+
+        if any(
+            isinstance(item, ast.ExceptHandler)
+            for item in ancestors
+        ):
+            flags.append("EXCEPT_HANDLER")
+
+        if any(isinstance(item, loop_types) for item in ancestors):
+            flags.append("LOOP")
+
+        if any(isinstance(item, with_types) for item in ancestors):
+            flags.append("WITH")
+
+        if any(isinstance(item, ast.Match) for item in ancestors):
+            flags.append("MATCH")
+
+        result[id(node)] = (primary, tuple(flags))
+
+    return result
 
 
 def assess_package_graph_consistency(
@@ -40,6 +143,7 @@ def assess_package_graph_consistency(
     indexed_roots = frozenset(name.split(".", 1)[0] for name in indexed)
     unmodeled_external_imports: list[tuple[str, int, str, str]] = []
     unmodeled_namespace_parents: list[tuple[str, int, str, str]] = []
+    external_scopes: list[ExternalImportScopeRecord] = []
     if any(name not in indexed or not isinstance(sources.get(name), ast.Module)
            for name in evidence_source_modules):
         return unknown("MISSING_INDEXED_TARGET")
@@ -313,6 +417,10 @@ def assess_package_graph_consistency(
         if not parents_proved:
             type_only_ids = frozenset()
 
+        scope_index = _external_import_scope_index(
+            sources[module_id]
+        )
+
         for node in ast.walk(sources[module_id]):
             if (
                 typing_guard is not None
@@ -338,6 +446,18 @@ def assess_package_graph_consistency(
                         unmodeled_external_imports.append(
                             (module_id, node.lineno, "import", alias.name)
                         )
+                        primary, flags = scope_index[id(node)]
+                        external_scopes.append(
+                            ExternalImportScopeRecord(
+                                module_id,
+                                node.lineno,
+                                node.col_offset,
+                                "import",
+                                alias.name,
+                                primary,
+                                flags,
+                            )
+                        )
                         continue
                     if resolved != alias.name and resolved != alias.name + ".__init__":
                         return unknown("AMBIGUOUS_PACKAGE_TARGET")
@@ -391,6 +511,18 @@ def assess_package_graph_consistency(
                     unmodeled_external_imports.append(
                         (module_id, node.lineno, "from", base)
                     )
+                    primary, flags = scope_index[id(node)]
+                    external_scopes.append(
+                        ExternalImportScopeRecord(
+                            module_id,
+                            node.lineno,
+                            node.col_offset,
+                            "from",
+                            base,
+                            primary,
+                            flags,
+                        )
+                    )
                     continue
                 if resolved == base and any(
                     module.startswith(base + ".") for module in indexed
@@ -471,6 +603,21 @@ def assess_package_graph_consistency(
         if expected != set(hard_edges[module_id]):
             return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
 
+    ordered_external_scopes = tuple(
+        sorted(
+            external_scopes,
+            key=lambda row: (
+                row.importer,
+                row.line,
+                row.form,
+                row.target,
+                row.column,
+                row.primary_scope,
+                row.ancestry_flags,
+            ),
+        )
+    )
+
     checked_source_modules = tuple(sorted(evidence_source_modules))
     internal_graph_state = "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"
     if unmodeled_namespace_parents:
@@ -481,6 +628,7 @@ def assess_package_graph_consistency(
             tuple(sorted(unmodeled_namespace_parents)),
             internal_graph_state,
             checked_source_modules,
+            external_scope_records=ordered_external_scopes,
         )
     if unmodeled_external_imports:
         return PackageGraphConsistency(
@@ -489,6 +637,7 @@ def assess_package_graph_consistency(
             tuple(sorted(unmodeled_external_imports)),
             internal_graph_state=internal_graph_state,
             checked_source_modules=checked_source_modules,
+            external_scope_records=ordered_external_scopes,
         )
     return PackageGraphConsistency(
         "CONSISTENT",
diff --git a/tests/test_cycle_semantics_package_graph_external_boundary.py b/tests/test_cycle_semantics_package_graph_external_boundary.py
index 73272f6..3863fc7 100644
--- a/tests/test_cycle_semantics_package_graph_external_boundary.py
+++ b/tests/test_cycle_semantics_package_graph_external_boundary.py
@@ -131,3 +131,115 @@ def test_optional_scc_with_external_import_never_model_passes():
     assert component.classification == "INDETERMINATE"
     assert component.coverage == "NONE"
     assert component.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+
+
+def test_g18_p2_p1_external_scope_evidence():
+    source = (
+        "import os\n"
+        "class C:\n"
+        "    import pathlib\n"
+        "    def method(self):\n"
+        "        import json\n"
+        "def worker():\n"
+        "    if True:\n"
+        "        import collections\n"
+        "async def async_worker():\n"
+        "    import asyncio\n"
+        "if True:\n"
+        "    import sys\n"
+        "try:\n"
+        "    import uuid\n"
+        "except ImportError:\n"
+        "    import warnings\n"
+    )
+
+    result = _check(source)
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+
+    by_target = {
+        item.target: item
+        for item in result.external_scope_records
+    }
+
+    assert len(by_target) == 8
+    assert by_target["os"].primary_scope == "MODULE_BODY"
+    assert by_target["pathlib"].primary_scope == "CLASS_BODY"
+    assert by_target["json"].primary_scope == "METHOD_BODY"
+    assert by_target["collections"].primary_scope == "FUNCTION_BODY"
+    assert by_target["asyncio"].primary_scope == "ASYNC_FUNCTION_BODY"
+    assert by_target["sys"].ancestry_flags == ("IF",)
+    assert by_target["uuid"].ancestry_flags == ("TRY",)
+    assert by_target["warnings"].ancestry_flags == (
+        "TRY", "EXCEPT_HANDLER"
+    )
+
+
+def test_g18_p2_p1_scope_projection_is_lossless():
+    source = (
+        "import os, json\n"
+        "import pathlib; import pathlib\n"
+        "from collections import Counter\n"
+    )
+
+    result = _check(source)
+
+    projected = tuple(
+        sorted(
+            (
+                item.importer,
+                item.line,
+                item.form,
+                item.target,
+            )
+            for item in result.external_scope_records
+        )
+    )
+
+    assert projected == tuple(
+        sorted(result.unmodeled_external_imports)
+    )
+    assert len(result.external_scope_records) == 5
+
+    pathlib_records = [
+        item for item in result.external_scope_records
+        if item.target == "pathlib"
+    ]
+
+    assert len(pathlib_records) == 2
+    assert pathlib_records[0].column != pathlib_records[1].column
+
+
+def test_g18_p2_p1_deferred_import_remains_opaque():
+    result = _check(
+        "def worker():\n"
+        "    import os\n"
+    )
+
+    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
+    assert result.status == "INDETERMINATE"
+    assert result.external_scope_records[0].primary_scope == (
+        "FUNCTION_BODY"
+    )
+
+
+def test_g18_p2_p1_internal_mismatch_stays_fail_closed():
+    result = _check(
+        "import os\n"
+        "import pkg.missing\n"
+    )
+
+    assert result.status == "INDETERMINATE"
+    assert result.reason == "MISSING_INDEXED_TARGET"
+    assert result.external_scope_records == ()
+
+
+def test_g18_p2_p1_deterministic_scope_records():
+    source = "import os\nimport json\n"
+
+    first = _check(source)
+    second = _check(source)
+
+    assert first == second
+    assert first.external_scope_records == second.external_scope_records
```

## FINAL_VERDICT

PASS — literal implementation, 42 targeted tests passed, both FileState-bound SCC replays retained INDETERMINATE and 16 structural cycles.
