# CONTEXTOR_B0G4B0_IMPORT_PROVENANCE_KERNEL

MODE=CONTROLLED IMPLEMENTATION
FINAL_VERDICT=B0G4B0_PASS

## HEAD_BEFORE
c7d68154b5a7b180a86b1591f590247504cec745

## HEAD_AFTER
c7d68154b5a7b180a86b1591f590247504cec745
No commit or Git mutation. Initial Git status had only the already-modified walkthrough.md; final task changes are the three new files below plus this report.

## LIVE_REVISION_BEFORE
397; activity_epoch=1beab26da2ff4932852caa7db6ff4242; canonical_state=fresh; resync_required=false; current LIVE cycle count=16/fresh; project-wide workspace_sync=unverified.

## LIVE_REVISION_AFTER
403; same activity_epoch; canonical_state=fresh; resync_required=false; current LIVE cycle count=16/fresh. get_live_events(after_revision=397): continuity=continuous, six desktop_watcher update_file events: revisions 398-400 UPDATED for the three new files, 401-403 UNCHANGED for the final newline normalization; no diagnostic_changes. No MCP update_file, FULL publish, analysis, restart or forced resync was invoked.

## FILES_CHANGED
- C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\__init__.py
- C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\provenance.py
- C:\Temp\Contextor_Repo\tests\test_cycle_semantics_provenance.py

## IMPLEMENTATION_CONTRACT
Auditor-provided content was copied literally into exactly the three new files. Normalized line-by-line comparison against the attachment returned EXACT_NORMALIZED=True for each file. A trailing blank line introduced by Set-Content was removed; no code contract changed. The package exports only the five specified names. The extractor accepts an already parsed ast.Module, records one immutable ImportOccurrence per explicit AST import statement with ordinal, coordinates, form, relative level, aliases, lexical scopes, raw control frames, source identity/fingerprint, and deterministic ordering. It does not evaluate controls, import analyzed source, execute analyzed code, resolve dependencies or classify safety. Code path reads only the supplied AST, arguments and stdlib ast/dataclasses; it contains no source-file read/write, filesystem API, subprocess or service call. Python 3.10.9 imported and ran the package in the targeted test. Existing frozen production modules were not edited.
Contextor discovery before edit found the target module absent; indexer and graph ownership/consumers remained in the established modules. After watcher indexing, get_file_edit_context found provenance.py as a new module with one direct production consumer (__init__.py), and get_module_blast_radius listed direct consumers __init__.py and the targeted test. No existing production consumer was connected.

## TEST_COMMAND
& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_provenance.py

## TEST_RESULTS
11 passed in 2.01s (Python 3.10.9). Assertions cover separate statements/aliases, relative imports, function/class/async scopes, IF/TRY/FOR/MATCH/main guards, dynamic-call exclusion, multiple origins, deterministic immutable-equivalent output, AST nonmutation, JSON serialization and invalid-tree rejection. No full suite or other pytest subset ran. git diff --no-index --check for each new file found no remaining whitespace/EOF warning after the trailing-blank correction; Git returns 1 for ordinary new-file differences.

## CANONICAL_GRAPH_UNCHANGED
Existing-source canonical hard edges are exactly unchanged: before=1746; after querying all 440 prior module identities=1746; set difference added=0, removed=0. Current total hard edges=1748 because the three newly indexed files introduce exactly two edges: package __init__ -> provenance and test -> package __init__. Soft edges remain 278. Structural cycle count stays 16/fresh. Therefore the graph *state* grew by the expected new-file edges, while every pre-existing graph edge and the graph contracts remained unchanged.

## EXISTING_CONTRACTS_UNCHANGED
No edit to ImportRef, AdvancedImportVisitor, read_imports, resolve_internal, resolve_module_edges, build_graph, detect_cycles, ArchitectureCycle, canonical snapshot schema, LIVE/MCP publication code or report schema. No semantic classifier or FULL/incremental hookup was added. Contextor after-change module context: provenance.py indexed, no syntax diagnostic, and only package/test direct consumers.

## NO_LIVE_PUBLICATION
No full-analysis publish was requested or performed. Desktop LIVE watcher independently indexed the three new files through six incremental update_file events; this is a canonical revision change caused by the active watcher, not a call from the extractor. Direct invocation of extract_import_provenance in tests has no canonical-state API and no observed publication. The current LIVE state is fresh at revision 403 with resync_required=false.

## UNRESOLVED_LIMITATIONS
The kernel records lexical AST evidence only. TYPE_CHECKING, false guards and function-local imports are not certified safe; dynamic import calls are not represented as explicit imports. Runtime reachability, binding hazards and package initialization timing remain outside this task. Project-wide workspace_sync remained unverified by the global overlay; target file was accepted by watcher as UPDATED. No runtime restart was requested or needed for this disconnected package; no loaded-service behavior is claimed from the passing pytest result.

## FULL_DIFFS
Complete raw new-file diffs follow. walkthrough.md is excluded from its own diff.


### FULL_DIFF: contextor/core/cycle_semantics/__init__.py
diff --git a/contextor/core/cycle_semantics/__init__.py b/contextor/core/cycle_semantics/__init__.py
new file mode 100644
index 0000000..a3d653c
--- /dev/null
+++ b/contextor/core/cycle_semantics/__init__.py
@@ -0,0 +1,17 @@
+"""Independent Python cycle-semantics analysis."""
+
+from .provenance import (
+    ControlFrame,
+    ImportOccurrence,
+    ImportProvenance,
+    ScopeFrame,
+    extract_import_provenance,
+)
+
+__all__ = [
+    "ControlFrame",
+    "ImportOccurrence",
+    "ImportProvenance",
+    "ScopeFrame",
+    "extract_import_provenance",
+]

### FULL_DIFF: contextor/core/cycle_semantics/provenance.py
diff --git a/contextor/core/cycle_semantics/provenance.py b/contextor/core/cycle_semantics/provenance.py
new file mode 100644
index 0000000..9307b6d
--- /dev/null
+++ b/contextor/core/cycle_semantics/provenance.py
@@ -0,0 +1,421 @@
+"""Lossless lexical provenance of explicit Python imports.
+
+No import resolution, graph mutation, reachability proof
+or runtime execution.
+"""
+
+from __future__ import annotations
+
+import ast
+from dataclasses import dataclass
+
+
+@dataclass(frozen=True)
+class ScopeFrame:
+    kind: str
+    name: str
+    line: int
+
+
+@dataclass(frozen=True)
+class ControlFrame:
+    kind: str
+    branch: str
+    line: int
+    expression: str | None = None
+
+
+@dataclass(frozen=True)
+class ImportOccurrence:
+    ordinal: int
+    line: int
+    column: int
+    end_line: int | None
+    end_column: int | None
+    form: str
+    module: str | None
+    level: int
+    aliases: tuple[tuple[str, str | None], ...]
+    scopes: tuple[ScopeFrame, ...]
+    controls: tuple[ControlFrame, ...]
+
+
+@dataclass(frozen=True)
+class ImportProvenance:
+    module_id: str
+    source_key: str
+    source_path: str
+    source_fingerprint: str
+    occurrences: tuple[ImportOccurrence, ...]
+
+
+class _ImportOccurrenceVisitor(ast.NodeVisitor):
+
+    def __init__(self) -> None:
+        self.scopes: list[ScopeFrame] = []
+        self.controls: list[ControlFrame] = []
+        self.raw: list[
+            tuple[
+                ast.Import | ast.ImportFrom,
+                tuple[ScopeFrame, ...],
+                tuple[ControlFrame, ...],
+            ]
+        ] = []
+
+    def _record(
+        self,
+        node: ast.Import | ast.ImportFrom,
+    ) -> None:
+        self.raw.append(
+            (
+                node,
+                tuple(self.scopes),
+                tuple(self.controls),
+            )
+        )
+
+    def visit_Import(self, node: ast.Import) -> None:
+        self._record(node)
+
+    def visit_ImportFrom(
+        self,
+        node: ast.ImportFrom,
+    ) -> None:
+        self._record(node)
+
+    def _visit_body_with_scope(
+        self,
+        node: ast.AST,
+        kind: str,
+        name: str,
+    ) -> None:
+        self.scopes.append(
+            ScopeFrame(kind, name, node.lineno)
+        )
+        try:
+            for statement in node.body:
+                self.visit(statement)
+        finally:
+            self.scopes.pop()
+
+    def visit_FunctionDef(
+        self,
+        node: ast.FunctionDef,
+    ) -> None:
+        # Definition-time expressions have no import
+        # statements. Their calls require later analysis.
+        self._visit_body_with_scope(
+            node, "FUNCTION", node.name
+        )
+
+    def visit_AsyncFunctionDef(
+        self,
+        node: ast.AsyncFunctionDef,
+    ) -> None:
+        self._visit_body_with_scope(
+            node, "ASYNC_FUNCTION", node.name
+        )
+
+    def visit_ClassDef(
+        self,
+        node: ast.ClassDef,
+    ) -> None:
+        self._visit_body_with_scope(
+            node, "CLASS", node.name
+        )
+
+    def _visit_control_body(
+        self,
+        statements: list[ast.stmt],
+        *,
+        kind: str,
+        branch: str,
+        line: int,
+        expression: str | None = None,
+    ) -> None:
+        self.controls.append(
+            ControlFrame(
+                kind,
+                branch,
+                line,
+                expression,
+            )
+        )
+        try:
+            for statement in statements:
+                self.visit(statement)
+        finally:
+            self.controls.pop()
+
+    @staticmethod
+    def _expression(
+        node: ast.AST | None,
+    ) -> str | None:
+        if node is None:
+            return None
+        return ast.dump(
+            node,
+            include_attributes=False,
+        )
+
+    def visit_If(self, node: ast.If) -> None:
+        expression = self._expression(node.test)
+
+        self._visit_control_body(
+            node.body,
+            kind="IF",
+            branch="BODY",
+            line=node.lineno,
+            expression=expression,
+        )
+
+        self._visit_control_body(
+            node.orelse,
+            kind="IF",
+            branch="ELSE",
+            line=node.lineno,
+            expression=expression,
+        )
+
+    def visit_Try(self, node: ast.Try) -> None:
+        self._visit_control_body(
+            node.body,
+            kind="TRY",
+            branch="BODY",
+            line=node.lineno,
+        )
+
+        for index, handler in enumerate(
+            node.handlers
+        ):
+            self._visit_control_body(
+                handler.body,
+                kind="EXCEPT",
+                branch=str(index),
+                line=handler.lineno,
+                expression=self._expression(
+                    handler.type
+                ),
+            )
+
+        self._visit_control_body(
+            node.orelse,
+            kind="TRY_ELSE",
+            branch="ELSE",
+            line=node.lineno,
+        )
+
+        self._visit_control_body(
+            node.finalbody,
+            kind="FINALLY",
+            branch="FINAL",
+            line=node.lineno,
+        )
+
+    def visit_For(self, node: ast.For) -> None:
+        self._visit_control_body(
+            node.body,
+            kind="FOR",
+            branch="BODY",
+            line=node.lineno,
+            expression=self._expression(
+                node.iter
+            ),
+        )
+
+        self._visit_control_body(
+            node.orelse,
+            kind="FOR",
+            branch="ELSE",
+            line=node.lineno,
+        )
+
+    def visit_AsyncFor(
+        self,
+        node: ast.AsyncFor,
+    ) -> None:
+        self._visit_control_body(
+            node.body,
+            kind="ASYNC_FOR",
+            branch="BODY",
+            line=node.lineno,
+            expression=self._expression(
+                node.iter
+            ),
+        )
+
+        self._visit_control_body(
+            node.orelse,
+            kind="ASYNC_FOR",
+            branch="ELSE",
+            line=node.lineno,
+        )
+
+    def visit_While(
+        self,
+        node: ast.While,
+    ) -> None:
+        expression = self._expression(node.test)
+
+        self._visit_control_body(
+            node.body,
+            kind="WHILE",
+            branch="BODY",
+            line=node.lineno,
+            expression=expression,
+        )
+
+        self._visit_control_body(
+            node.orelse,
+            kind="WHILE",
+            branch="ELSE",
+            line=node.lineno,
+            expression=expression,
+        )
+
+    def visit_With(
+        self,
+        node: ast.With,
+    ) -> None:
+        self._visit_control_body(
+            node.body,
+            kind="WITH",
+            branch="BODY",
+            line=node.lineno,
+        )
+
+    def visit_AsyncWith(
+        self,
+        node: ast.AsyncWith,
+    ) -> None:
+        self._visit_control_body(
+            node.body,
+            kind="ASYNC_WITH",
+            branch="BODY",
+            line=node.lineno,
+        )
+
+    def visit_Match(
+        self,
+        node: ast.Match,
+    ) -> None:
+        for index, case in enumerate(node.cases):
+            condition = self._expression(
+                case.pattern
+            )
+
+            if case.guard is not None:
+                condition += (
+                    " GUARD "
+                    + self._expression(case.guard)
+                )
+
+            self._visit_control_body(
+                case.body,
+                kind="MATCH",
+                branch=str(index),
+                line=node.lineno,
+                expression=condition,
+            )
+
+
+def extract_import_provenance(
+    tree: ast.AST,
+    *,
+    module_id: str,
+    source_key: str,
+    source_path: str,
+    source_fingerprint: str,
+) -> ImportProvenance:
+    """Extract individual explicit imports from an AST.
+
+    These are lexical source facts, not runtime proofs.
+
+    A function-local occurrence is not necessarily
+    deferred during module initialization.
+
+    Conditional guards are recorded, not evaluated.
+    """
+
+    if not isinstance(tree, ast.Module):
+        raise TypeError(
+            "tree must be an ast.Module"
+        )
+
+    values = (
+        module_id,
+        source_key,
+        source_path,
+        source_fingerprint,
+    )
+
+    if not all(
+        isinstance(value, str) and value
+        for value in values
+    ):
+        raise ValueError(
+            "module identity, path and fingerprint "
+            "must be nonempty strings"
+        )
+
+    visitor = _ImportOccurrenceVisitor()
+    visitor.visit(tree)
+
+    ordered = sorted(
+        enumerate(visitor.raw),
+        key=lambda pair: (
+            pair[1][0].lineno,
+            pair[1][0].col_offset,
+            pair[0],
+        ),
+    )
+
+    occurrences: list[ImportOccurrence] = []
+
+    for ordinal, (_, record) in enumerate(
+        ordered
+    ):
+        node, scopes, controls = record
+
+        occurrences.append(
+            ImportOccurrence(
+                ordinal=ordinal,
+                line=node.lineno,
+                column=node.col_offset,
+                end_line=getattr(
+                    node, "end_lineno", None
+                ),
+                end_column=getattr(
+                    node, "end_col_offset", None
+                ),
+                form=(
+                    "IMPORT"
+                    if isinstance(node, ast.Import)
+                    else "IMPORT_FROM"
+                ),
+                module=(
+                    node.module
+                    if isinstance(node, ast.ImportFrom)
+                    else None
+                ),
+                level=(
+                    node.level
+                    if isinstance(node, ast.ImportFrom)
+                    else 0
+                ),
+                aliases=tuple(
+                    (alias.name, alias.asname)
+                    for alias in node.names
+                ),
+                scopes=scopes,
+                controls=controls,
+            )
+        )
+
+    return ImportProvenance(
+        module_id=module_id,
+        source_key=source_key,
+        source_path=source_path,
+        source_fingerprint=source_fingerprint,
+        occurrences=tuple(occurrences),
+    )

### FULL_DIFF: tests/test_cycle_semantics_provenance.py
diff --git a/tests/test_cycle_semantics_provenance.py b/tests/test_cycle_semantics_provenance.py
new file mode 100644
index 0000000..a0d967d
--- /dev/null
+++ b/tests/test_cycle_semantics_provenance.py
@@ -0,0 +1,256 @@
+import ast
+import json
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics import (
+    extract_import_provenance,
+)
+
+
+def extract(code: str):
+    return extract_import_provenance(
+        ast.parse(code),
+        module_id="p.a",
+        source_key="p/a.py",
+        source_path=r"C:\fixture\p\a.py",
+        source_fingerprint="test-fingerprint",
+    )
+
+
+def test_individual_statements_and_aliases():
+    result = extract(
+        "import os as o, sys\n"
+        "import os\n"
+        "from . import child as c, other\n"
+    )
+
+    assert len(result.occurrences) == 3
+
+    assert [
+        item.ordinal
+        for item in result.occurrences
+    ] == [0, 1, 2]
+
+    assert result.occurrences[0].aliases == (
+        ("os", "o"),
+        ("sys", None),
+    )
+
+    last = result.occurrences[-1]
+    assert last.form == "IMPORT_FROM"
+    assert last.module is None
+    assert last.level == 1
+    assert last.aliases == (
+        ("child", "c"),
+        ("other", None),
+    )
+
+
+def test_class_function_and_method_scopes():
+    result = extract("""
+import root
+
+class C:
+    import in_class
+
+    def method(self):
+        import in_method
+
+def f():
+    class D:
+        import nested_class
+""")
+
+    scopes = [
+        [frame.kind for frame in item.scopes]
+        for item in result.occurrences
+    ]
+
+    assert scopes == [
+        [],
+        ["CLASS"],
+        ["CLASS", "FUNCTION"],
+        ["FUNCTION", "CLASS"],
+    ]
+
+    assert (
+        result.occurrences[2].scopes[-1].name
+        == "method"
+    )
+
+
+def test_async_function_scope():
+    result = extract("""
+async def load():
+    import deferred_candidate
+""")
+
+    assert len(result.occurrences) == 1
+
+    assert (
+        result.occurrences[0].scopes[0].kind
+        == "ASYNC_FUNCTION"
+    )
+
+
+def test_conditional_guards_preserved():
+    result = extract("""
+from typing import TYPE_CHECKING as TC
+
+if TC:
+    import typing_only_candidate
+else:
+    import runtime_candidate
+
+if False:
+    import unreachable_candidate
+""")
+
+    typing_site = result.occurrences[1]
+    alternative = result.occurrences[2]
+    false_site = result.occurrences[3]
+
+    assert typing_site.controls[0].branch == "BODY"
+    assert "TC" in typing_site.controls[0].expression
+    assert alternative.controls[0].branch == "ELSE"
+    assert "False" in false_site.controls[0].expression
+
+
+def test_try_except_else_finally():
+    result = extract("""
+try:
+    import a
+except ImportError:
+    import b
+else:
+    import c
+finally:
+    import d
+""")
+
+    assert [
+        site.controls[0].kind
+        for site in result.occurrences
+    ] == [
+        "TRY",
+        "EXCEPT",
+        "TRY_ELSE",
+        "FINALLY",
+    ]
+
+    assert (
+        "ImportError"
+        in result.occurrences[1]
+        .controls[0].expression
+    )
+
+
+def test_nested_conditions_and_match():
+    result = extract("""
+for i in range(2):
+    if i:
+        import x
+
+match value:
+    case 1 if enabled:
+        import y
+""")
+
+    assert [
+        frame.kind
+        for frame in result.occurrences[0].controls
+    ] == ["FOR", "IF"]
+
+    assert (
+        result.occurrences[1].controls[0].kind
+        == "MATCH"
+    )
+
+
+def test_main_guard_preserved():
+    result = extract("""
+if __name__ == "__main__":
+    import cli_runtime
+""")
+
+    assert len(result.occurrences) == 1
+
+    guard = result.occurrences[0].controls[0]
+    assert guard.kind == "IF"
+    assert "__main__" in guard.expression
+
+
+def test_dynamic_calls_not_fake_imports():
+    assert extract(
+        "__import__('target')\n"
+    ).occurrences == ()
+
+    assert extract(
+        "importlib.import_module('target')\n"
+    ).occurrences == ()
+
+
+def test_multiple_origins_not_deduplicated():
+    result = extract("""
+import a
+
+def later():
+    import a
+
+class C:
+    import a
+""")
+
+    assert len(result.occurrences) == 3
+    assert len({
+        (site.line, site.column)
+        for site in result.occurrences
+    }) == 3
+
+
+def test_deterministic_no_ast_mutation():
+    tree = ast.parse("""
+if True:
+    import a
+    import a
+""")
+
+    before = ast.dump(
+        tree, include_attributes=True
+    )
+
+    kwargs = {
+        "module_id": "p.a",
+        "source_key": "p/a.py",
+        "source_path": r"C:\fixture\p\a.py",
+        "source_fingerprint": "fingerprint",
+    }
+
+    first = extract_import_provenance(
+        tree, **kwargs
+    )
+    second = extract_import_provenance(
+        tree, **kwargs
+    )
+
+    assert first == second
+    assert len(first.occurrences) == 2
+
+    assert ast.dump(
+        tree, include_attributes=True
+    ) == before
+
+    json.dumps(asdict(first))
+
+
+def test_invalid_tree_rejected():
+    with pytest.raises(TypeError):
+        extract_import_provenance(
+            ast.parse("x").body[0],
+            module_id="p.a",
+            source_key="p/a.py",
+            source_path=r"C:\fixture\p\a.py",
+            source_fingerprint="fingerprint",
+        )
