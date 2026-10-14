# CONTEXTOR_B0G4B3_MODULE_BINDING_ORDER_EVIDENCE

## HEAD_BEFORE
5638c1b2c649889d15d66eec467053739730bdb4. Pre-edit Git status had pre-existing `M tests/test_cycle_semantics_guards.py` (B0G4B2F rename) and `M walkthrough.md`; both were preserved. B0G4B0 provenance, B0G4B1 execution_context, and B0G4B2 guards existed. Both B0G4B3 target files were absent.

## HEAD_AFTER
5638c1b2c649889d15d66eec467053739730bdb4. No commit. Git status adds only the two new task files; pre-existing test-helper edit remains untouched.

## LIVE_REVISION_BEFORE
408; activity_epoch=1beab26da2ff4932852caa7db6ff4242; continuity=continuous; resync_required=false; canonical_state=fresh; collision family fresh with count=0; cycles=16. Global workspace_sync=unverified. Contextor provenance module is the canonical source of ImportProvenance and extract_import_provenance; its blast radius was fresh. The B0G4B2F helper rename was verified in source and the previous collision was absent in fresh canonical diagnostics.

## LIVE_REVISION_AFTER
410; same activity_epoch; continuity=continuous; resync_required=false; canonical_state=fresh; graph, topology, collisions and cycles families fresh; no parse-stale modules. Desktop watcher revision 409 UPDATED binding_order.py and revision 410 UPDATED test_cycle_semantics_binding_order.py; both report blast_radius_state=fresh. The new production file workspace_sync=verified by full get_file_edit_context at revision 410; global overlay remains unverified.

## FILES_CHANGED
- contextor/core/cycle_semantics/binding_order.py (new)
- tests/test_cycle_semantics_binding_order.py (new)

The pre-existing edit to tests/test_cycle_semantics_guards.py was not changed in this task. No existing production/test file or __init__.py was edited. walkthrough.md is this report and is excluded from source/test diff accounting.

## IMPLEMENTATION_CONTRACT
CONTRACT_PROVED: The supplied literal design was implemented as a standalone projection of an existing ast.Module and matching ImportProvenance. It validates input types and replay equality, then matches each import occurrence by exact lexical key. It records top-level statement ordinal, source positions, kind, contained import ordinals and limited binding/deletion candidates. Duplicate/ambiguous or unmatched import positions fail closed. Results are frozen dataclasses with tuple collections and preserve module_id/source_fingerprint. Every statement execution_proven and timeline initialization_reachability is UNKNOWN.
CODE_PATH_PROVED: The new module traverses supplied AST/provenance and returns data. It has no analyzed-source execution, filesystem read, graph or canonical mutation, service/subprocess dependency, or warning publication call. Contextor reports the new module has only its targeted test as a direct consumer and zero downstream consumers; no other production consumer exists.

## TEST_COMMAND
Pre-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`
Post-edit: `& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_binding_order.py tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`

## TEST_RESULTS
Repository Python 3.10.9. Pre-edit exit 0: 39 passed in 1.18s. Post-edit exit 0: 51 passed in 1.52s (12 new plus 39 existing). No other tests or full suite run. New production syntax diagnostics are fresh and empty at revision 410.

## BINDING_ORDER_EVIDENCE
CONTRACT_PROVED: Targeted tests cover assignment/import order, same-line imports, nested imports in function/class/if, alias candidates, deletion and augmented assignment, nonbinding annotation, star import, no imports, AST mismatch, wrong types, and deterministic JSON serialization. Binding completion points are lexical candidates only. A function definition containing an import is not treated as execution of its body; class name binding is recorded after definition; assignments may evaluate arbitrary expressions first. Source order is not represented as unconditional runtime execution.

## COLLISION_COUNT_BEFORE_AFTER
0 -> 0 from fresh Contextor get_name_collisions at revisions 408 and 410. The new test helper `_binding_order_for` does not duplicate the previous public helper name. The B0G4B2F rename was preserved.

## GRAPH_CONTRACT_UNCHANGED
CODE_PATH_PROVED: No graph implementation, hard_edges, soft_edges, graph schema, or warning policy was edited. The new files may add ordinary indexed import edges; the whole-repository graph is not claimed byte-identical. Contextor graph/topology families are fresh and structural cycles remain 16 after indexing.

## NO_SAFETY_CERTIFICATION
CODE_PATH_PROVED: Every statement has execution_proven=UNKNOWN and ModuleBindingOrder has initialization_reachability=UNKNOWN. No SAFE or runtime success state is emitted. Binding candidates do not prove availability or execution.

## NO_WARNING_SUPPRESSION
CODE_PATH_PROVED: ArchitectureCycle/warning publication code was not edited or called. Fresh canonical cycle count remains 16. No Contextor-specific exception was added.

## NO_DIRECT_LIVE_PUBLICATION
CODE_PATH_PROVED: The new module is imported only by its test, is not exported from __init__.py, and is not integrated with FULL/incremental, MCP, LIVE or snapshot publication. Desktop watcher indexing is external observation. No direct update_file, FULL analysis, restart or commit.

## UNRESOLVED_LIMITATIONS
UNKNOWN: Lexical ordering alone cannot establish whether a statement executes, whether a binding is available during import recursion, or whether a cycle succeeds/fails at runtime. Global project workspace_sync is unverified even though target production file synchronization was verified. No runtime execution of analyzed sources or full-suite certification was requested.

## FINAL_VERDICT
B0G4B3_PASS — exact isolated two-file implementation, 51 targeted tests passed, both watcher events observed, fresh canonical state, zero collisions, and no production consumers outside the new isolated test path. Await `proceduj`.

## FULL_DIFFS

### FULL_DIFF: contextor/core/cycle_semantics/binding_order.py

diff --git a/contextor/core/cycle_semantics/binding_order.py b/contextor/core/cycle_semantics/binding_order.py
new file mode 100644
index 0000000..1094789
--- /dev/null
+++ b/contextor/core/cycle_semantics/binding_order.py
@@ -0,0 +1,258 @@
+"""Lexical module-level binding order evidence, never runtime proof."""
+
+from __future__ import annotations
+
+import ast
+from dataclasses import dataclass
+
+from .provenance import (
+    ImportOccurrence,
+    ImportProvenance,
+    extract_import_provenance,
+)
+
+
+@dataclass(frozen=True)
+class CycleBindingCandidate:
+    name: str
+    operation: str
+    completion_point: str
+
+
+@dataclass(frozen=True)
+class ModuleStatementEvidence:
+    ordinal: int
+    line: int
+    column: int
+    end_line: int | None
+    end_column: int | None
+    kind: str
+    contained_import_ordinals: tuple[int, ...]
+    binding_candidates: tuple[CycleBindingCandidate, ...]
+    execution_proven: str = "UNKNOWN"
+
+
+@dataclass(frozen=True)
+class ModuleBindingOrder:
+    module_id: str
+    source_fingerprint: str
+    statements: tuple[ModuleStatementEvidence, ...]
+    initialization_reachability: str = "UNKNOWN"
+
+
+def _import_key(node: ast.Import | ast.ImportFrom) -> tuple:
+    return (
+        node.lineno,
+        node.col_offset,
+        getattr(node, "end_lineno", None),
+        getattr(node, "end_col_offset", None),
+        "IMPORT" if isinstance(node, ast.Import) else "IMPORT_FROM",
+        None if isinstance(node, ast.Import) else node.module,
+        0 if isinstance(node, ast.Import) else node.level,
+        tuple((alias.name, alias.asname) for alias in node.names),
+    )
+
+
+def _occurrence_key(occurrence: ImportOccurrence) -> tuple:
+    return (
+        occurrence.line,
+        occurrence.column,
+        occurrence.end_line,
+        occurrence.end_column,
+        occurrence.form,
+        occurrence.module,
+        occurrence.level,
+        occurrence.aliases,
+    )
+
+
+def _binding_candidates(
+    stmt: ast.stmt,
+) -> tuple[CycleBindingCandidate, ...]:
+    found: list[CycleBindingCandidate] = []
+
+    def record(
+        name: str,
+        operation: str,
+        completion: str,
+    ) -> None:
+        found.append(
+            CycleBindingCandidate(
+                name,
+                operation,
+                completion,
+            )
+        )
+
+    if isinstance(stmt, ast.Import):
+        for alias in stmt.names:
+            record(
+                alias.asname or alias.name.split(".")[0],
+                "BIND",
+                "AFTER_IMPORT",
+            )
+
+    elif isinstance(stmt, ast.ImportFrom):
+        for alias in stmt.names:
+            if alias.name != "*":
+                record(
+                    alias.asname or alias.name,
+                    "BIND",
+                    "AFTER_IMPORT",
+                )
+
+    elif isinstance(
+        stmt,
+        (ast.FunctionDef, ast.AsyncFunctionDef),
+    ):
+        record(
+            stmt.name,
+            "BIND",
+            "AFTER_FUNCTION_DEFINITION",
+        )
+
+    elif isinstance(stmt, ast.ClassDef):
+        record(
+            stmt.name,
+            "BIND",
+            "AFTER_CLASS_DEFINITION",
+        )
+
+    elif isinstance(stmt, ast.Assign):
+        if (
+            len(stmt.targets) == 1
+            and isinstance(stmt.targets[0], ast.Name)
+        ):
+            record(
+                stmt.targets[0].id,
+                "BIND",
+                "AFTER_ASSIGNMENT",
+            )
+
+    elif isinstance(stmt, ast.AnnAssign):
+        if (
+            stmt.value is not None
+            and isinstance(stmt.target, ast.Name)
+        ):
+            record(
+                stmt.target.id,
+                "BIND",
+                "AFTER_ANNOTATED_ASSIGNMENT",
+            )
+
+    elif isinstance(stmt, ast.AugAssign):
+        if isinstance(stmt.target, ast.Name):
+            record(
+                stmt.target.id,
+                "BIND",
+                "AFTER_AUGMENTED_ASSIGNMENT",
+            )
+
+    elif isinstance(stmt, ast.Delete):
+        for target in stmt.targets:
+            if isinstance(target, ast.Name):
+                record(
+                    target.id,
+                    "DELETE",
+                    "AFTER_DELETE",
+                )
+
+    return tuple(found)
+
+
+def extract_cycle_module_binding_order(
+    tree: ast.AST,
+    provenance: ImportProvenance,
+) -> ModuleBindingOrder:
+    """Record lexical top-level steps and candidate binding points.
+
+    A preceding candidate is not necessarily an available binding.
+    This function cannot certify runtime safety or import-order safety.
+    """
+    if not isinstance(tree, ast.Module):
+        raise TypeError("tree must be an ast.Module")
+
+    if not isinstance(provenance, ImportProvenance):
+        raise TypeError("provenance must be ImportProvenance")
+
+    replay = extract_import_provenance(
+        tree,
+        module_id=provenance.module_id,
+        source_key=provenance.source_key,
+        source_path=provenance.source_path,
+        source_fingerprint=provenance.source_fingerprint,
+    )
+
+    if replay != provenance:
+        raise ValueError(
+            "AST import occurrences differ from provenance"
+        )
+
+    lookup: dict[tuple, int] = {}
+
+    for occurrence in provenance.occurrences:
+        key = _occurrence_key(occurrence)
+
+        if key in lookup:
+            raise ValueError(
+                "ambiguous import occurrence position"
+            )
+
+        lookup[key] = occurrence.ordinal
+
+    seen: set[int] = set()
+    statements: list[ModuleStatementEvidence] = []
+
+    for index, statement in enumerate(tree.body):
+        contained: list[int] = []
+
+        for node in ast.walk(statement):
+            if not isinstance(
+                node,
+                (ast.Import, ast.ImportFrom),
+            ):
+                continue
+
+            key = _import_key(node)
+            ordinal = lookup.get(key)
+
+            if ordinal is None or ordinal in seen:
+                raise ValueError(
+                    "unmatched or duplicated AST import occurrence"
+                )
+
+            seen.add(ordinal)
+            contained.append(ordinal)
+
+        statements.append(
+            ModuleStatementEvidence(
+                ordinal=index,
+                line=statement.lineno,
+                column=statement.col_offset,
+                end_line=getattr(
+                    statement, "end_lineno", None
+                ),
+                end_column=getattr(
+                    statement, "end_col_offset", None
+                ),
+                kind=type(statement).__name__,
+                contained_import_ordinals=tuple(
+                    sorted(contained)
+                ),
+                binding_candidates=_binding_candidates(
+                    statement
+                ),
+            )
+        )
+
+    if seen != set(lookup.values()):
+        raise ValueError(
+            "not all import occurrences belong to "
+            "top-level statements"
+        )
+
+    return ModuleBindingOrder(
+        module_id=provenance.module_id,
+        source_fingerprint=provenance.source_fingerprint,
+        statements=tuple(statements),
+    )

### FULL_DIFF: tests/test_cycle_semantics_binding_order.py

diff --git a/tests/test_cycle_semantics_binding_order.py b/tests/test_cycle_semantics_binding_order.py
new file mode 100644
index 0000000..2e077b4
--- /dev/null
+++ b/tests/test_cycle_semantics_binding_order.py
@@ -0,0 +1,217 @@
+import ast
+import json
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics.provenance import (
+    extract_import_provenance,
+)
+from contextor.core.cycle_semantics.binding_order import (
+    extract_cycle_module_binding_order,
+)
+
+
+def _binding_order_for(code):
+    tree = ast.parse(code)
+    facts = extract_import_provenance(
+        tree,
+        module_id="pkg.a",
+        source_key="pkg/a.py",
+        source_path="C:/fixture/pkg/a.py",
+        source_fingerprint="fingerprint",
+    )
+    return extract_cycle_module_binding_order(tree, facts)
+
+
+def test_binding_order_switch_same_import_graph():
+    before = _binding_order_for(
+        "value = 1\nimport b\n"
+    )
+    after = _binding_order_for(
+        "import b\nvalue = 1\n"
+    )
+
+    assert (
+        before.statements[0].binding_candidates[0].name
+        == "value"
+    )
+    assert (
+        before.statements[1].contained_import_ordinals
+        == (0,)
+    )
+
+    assert (
+        after.statements[0].contained_import_ordinals
+        == (0,)
+    )
+    assert (
+        after.statements[1].binding_candidates[0].name
+        == "value"
+    )
+
+    assert before.initialization_reachability == "UNKNOWN"
+    assert after.initialization_reachability == "UNKNOWN"
+
+
+def test_same_line_separate_import_statements():
+    result = _binding_order_for(
+        "import a; import b\n"
+    )
+
+    assert [
+        item.contained_import_ordinals
+        for item in result.statements
+    ] == [(0,), (1,)]
+
+
+def test_function_and_class_imports_are_contained():
+    result = _binding_order_for(
+        "def f():\n"
+        "    import a\n"
+        "class K:\n"
+        "    import b\n"
+    )
+
+    assert [
+        item.contained_import_ordinals
+        for item in result.statements
+    ] == [(0,), (1,)]
+
+    assert [
+        item.binding_candidates[0].completion_point
+        for item in result.statements
+    ] == [
+        "AFTER_FUNCTION_DEFINITION",
+        "AFTER_CLASS_DEFINITION",
+    ]
+
+
+def test_conditional_imports_share_top_level_owner():
+    result = _binding_order_for(
+        "if flag:\n"
+        "    import a\n"
+        "else:\n"
+        "    import b\n"
+    )
+
+    assert (
+        result.statements[0].contained_import_ordinals
+        == (0, 1)
+    )
+    assert result.statements[0].binding_candidates == ()
+
+
+def test_import_alias_binding_candidates():
+    result = _binding_order_for(
+        "import os.path, sys as ss\n"
+        "from . import child as c\n"
+    )
+
+    assert [
+        candidate.name
+        for candidate in result.statements[0].binding_candidates
+    ] == ["os", "ss"]
+
+    assert (
+        result.statements[1].binding_candidates[0].name
+        == "c"
+    )
+
+
+def test_delete_and_augmented_assignment():
+    result = _binding_order_for(
+        "x = 1\n"
+        "x += 1\n"
+        "del x\n"
+    )
+
+    assert [
+        statement.binding_candidates[0].operation
+        for statement in result.statements
+    ] == ["BIND", "BIND", "DELETE"]
+
+
+def test_annotation_without_value_not_binding_candidate():
+    result = _binding_order_for(
+        "x: int\n"
+        "y: int = 1\n"
+        "a, b = (1, 2)\n"
+    )
+
+    assert result.statements[0].binding_candidates == ()
+    assert (
+        result.statements[1].binding_candidates[0].name
+        == "y"
+    )
+    assert result.statements[2].binding_candidates == ()
+
+
+def test_star_import_not_guessed():
+    result = _binding_order_for(
+        "from pkg import *\n"
+    )
+
+    assert result.statements[0].binding_candidates == ()
+    assert (
+        result.statements[0].contained_import_ordinals
+        == (0,)
+    )
+
+
+def test_no_imports_remains_valid():
+    result = _binding_order_for("x = 1\n")
+
+    assert result.statements[0].contained_import_ordinals == ()
+    assert result.initialization_reachability == "UNKNOWN"
+
+
+def test_ast_provenance_mismatch_rejected():
+    tree = ast.parse("import a\n")
+    facts = extract_import_provenance(
+        tree,
+        module_id="m",
+        source_key="m.py",
+        source_path="C:/m.py",
+        source_fingerprint="fingerprint",
+    )
+
+    with pytest.raises(ValueError, match="differ"):
+        extract_cycle_module_binding_order(
+            ast.parse("import b\n"),
+            facts,
+        )
+
+
+def test_wrong_input_types_rejected():
+    tree = ast.parse("import a\n")
+    facts = extract_import_provenance(
+        tree,
+        module_id="m",
+        source_key="m.py",
+        source_path="C:/m.py",
+        source_fingerprint="fingerprint",
+    )
+
+    with pytest.raises(TypeError):
+        extract_cycle_module_binding_order(None, facts)
+
+    with pytest.raises(TypeError):
+        extract_cycle_module_binding_order(tree, None)
+
+
+def test_deterministic_json_compatible():
+    first = _binding_order_for(
+        "if True:\n    import a\n"
+    )
+    second = _binding_order_for(
+        "if True:\n    import a\n"
+    )
+
+    assert first == second
+    json.dumps(asdict(first))
+
+    assert all(
+        statement.execution_proven == "UNKNOWN"
+        for statement in first.statements
+    )
