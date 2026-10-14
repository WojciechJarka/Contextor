# CONTEXTOR_B0G4B2_GUARD_LEXICAL_EVIDENCE

STATUS: Controlled implementation completed. Stop at this stage and await `proceduj`.

## HEAD_BEFORE

27a8426f0e4a05ee4489df96f8d1e1767a45bcd9. Expected e15f597842e81ef978e316ffb908755029b4f31d is an ancestor (`git merge-base --is-ancestor` exit 0). Pre-edit Git status was clean. B0G4B0 provenance and B0G4B1 execution_context existed; both B0G4B2 target paths were absent.

## HEAD_AFTER

27a8426f0e4a05ee4489df96f8d1e1767a45bcd9. No commit made. Git status shows only the two new task files as untracked; this report file is ignored by Git.

## LIVE_REVISION_BEFORE

405, activity_epoch=1beab26da2ff4932852caa7db6ff4242, continuity=continuous, resync_required=false, canonical_state=fresh, global workspace_sync=unverified, cycles=16, name_collisions=0. Contextor pre-edit ownership: provenance is the canonical ImportProvenance/extract_import_provenance owner; execution_context is separate and has only its targeted test as direct consumer. Provenance blast radius was fresh.

## LIVE_REVISION_AFTER

407, same activity_epoch, continuity=continuous, resync_required=false, canonical_state=fresh, no parse-stale modules, all displayed canonical families fresh, cycles=16, name_collisions=1. Desktop watcher events: revision 406 UPDATED production guards.py; revision 407 UPDATED test guards.py; both blast_radius_state=fresh. Full get_file_edit_context verified guards.py workspace_sync=verified against disk at revision 407. Global overlay workspace_sync remains unverified because it does not hash repository files. No MCP update_file call.

## FILES_CHANGED

- contextor/core/cycle_semantics/guards.py (new)
- tests/test_cycle_semantics_guards.py (new)

No existing production or test file changed. `walkthrough.md` is the report, excluded from source/test diff accounting.

## IMPLEMENTATION_CONTRACT

CONTRACT_PROVED: Supplied implementation and tests were written verbatim, with a single final newline. Input requires ast.Module and matching ImportProvenance. The function replays provenance extraction and rejects AST/provenance mismatch. Results are frozen dataclasses with tuple collections, preserve ordinal, line and source order, and set initialization_reachability=UNKNOWN for every assessment. No existing API or package export changed.
CODE_PATH_PROVED: Projection traverses the supplied AST and provenance, classifies literal boolean predicates, syntactic typing.TYPE_CHECKING and __main__ candidates, unresolved IF, and non-IF controls. It does not read source files, run analyzed source, spawn services or subprocesses, mutate the supplied AST/provenance, graph, or canonical state, or publish warnings. Determinism, JSON compatibility and AST nonmutation are covered by focused tests. Provenance dataclasses are frozen. Contextor reports guards.py has only tests.test_cycle_semantics_guards as direct consumer, with zero downstream consumers.

## TEST_COMMAND

`& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_guards.py tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`

## TEST_RESULTS

Repository Python 3.10.9. Exit code 0: 39 passed in 14.94s. No other test files or full suite run. Contextor syntax diagnostics are fresh and error-free for both new files.

## GUARD_CLASSIFICATION_EVIDENCE

CONTRACT_PROVED: Literal True/False, unary not and simple all-literal And/Or produce TRUE/FALSE evidence and can block the opposite branch. Nested false branch evidence overrides an outer unknown guard in the overall gate. Alias detection is limited to unshadowed, preceding, top-level syntactic imports from typing. typing.TYPE_CHECKING and __main__ patterns remain UNKNOWN truth and produce only candidate kinds. Dynamic predicates, ambiguous IF matches, and non-IF controls remain unknown. Tests cover each of these cases, including ELSE and nested IF. Occurrence ordinals are passed through unchanged in source order.

## NO_SAFETY_CERTIFICATION

CODE_PATH_PROVED: Every ImportGuardAssessment has initialization_reachability=UNKNOWN. The component emits no SAFE, NO_INITIALIZATION_HAZARD, or RUNTIME_CONFIRMED state. BLOCKED_BY_LITERAL is lexical branch evidence, not a cycle-safety or runtime-outcome assertion.

## NO_WARNING_SUPPRESSION

CODE_PATH_PROVED: No ArchitectureCycle warning or publication code was changed. guards.py has no warning-suppression path. LIVE cycle count remains 16 before and after. A new Contextor name collision was added by the exact auditor-provided test helper `project`, shared with tests.test_cycle_semantics_execution_context. The revision 407 watcher event identifies a NAME_COLLISION between those two test modules; this is not a cycle diagnostic and was not suppressed.

## GRAPH_CONTRACT_UNCHANGED

CODE_PATH_PROVED: guards.py receives AST/provenance and returns lexical evidence, with no graph-edge mutation API. Existing graph modules and schemas were untouched. Watcher indexing of two new modules may add ordinary dependency edges; the whole-repository graph is therefore not claimed byte-identical. Contextor graph/topology families are fresh at revision 407 and cycles remain 16.

## NO_DIRECT_LIVE_PUBLICATION

CODE_PATH_PROVED: guards.py is imported only by its targeted test and is not exported by cycle_semantics.__init__. No FULL/incremental, LIVE, MCP, snapshot, or warning-publication integration was added. Watcher indexing is external observation of file changes. No Desktop/MCP restart or FULL analysis was performed or needed for this disconnected stage.

## UNRESOLVED_LIMITATIONS

UNKNOWN: Syntactic TYPE_CHECKING candidate does not establish runtime binding; syntactic __main__ candidate does not establish that __name__ was not reassigned. Lexical evidence does not establish runtime reachability, cycle safety, or cycle failure. Global workspace synchronization remains unverified in the project overlay, while target guards.py was verified. DIRECT_EVIDENCE: revision 407 added one test-only helper-name collision. It remains because the auditor supplied an exact test file and prohibited redesign; resolving it requires a later authorized design decision. No runtime execution of analyzed sources or full-suite certification was requested.

## FINAL_VERDICT

B0G4B2_PASS — exact two-file implementation and 39 targeted tests pass, both files are indexed in fresh LIVE state, and architectural scope is contained. The new test-helper name collision is recorded as an unresolved diagnostic, not hidden. Await `proceduj`.

## FULL_DIFFS

### FULL_DIFF: contextor/core/cycle_semantics/guards.py

diff --git a/contextor/core/cycle_semantics/guards.py b/contextor/core/cycle_semantics/guards.py
new file mode 100644
index 0000000..10fef1e
--- /dev/null
+++ b/contextor/core/cycle_semantics/guards.py
@@ -0,0 +1,244 @@
+"""Conservative AST guard evidence for explicit import occurrences.
+
+Only literal boolean conditions can block a branch here. Named guards are
+recognition candidates, never verified runtime values or safety proofs.
+"""
+
+from __future__ import annotations
+
+import ast
+from dataclasses import dataclass
+
+from .provenance import ImportProvenance, extract_import_provenance
+
+
+@dataclass(frozen=True)
+class GuardFrameEvidence:
+    kind: str
+    branch: str
+    line: int
+    predicate_kind: str
+    predicate_truth: str
+    branch_gate: str
+
+
+@dataclass(frozen=True)
+class ImportGuardAssessment:
+    ordinal: int
+    line: int
+    gate: str
+    frames: tuple[GuardFrameEvidence, ...]
+    initialization_reachability: str = "UNKNOWN"
+
+
+@dataclass(frozen=True)
+class GuardProjection:
+    module_id: str
+    source_fingerprint: str
+    assessments: tuple[ImportGuardAssessment, ...]
+
+
+def _literal_truth(node: ast.AST) -> bool | None:
+    if isinstance(node, ast.Constant) and type(node.value) is bool:
+        return node.value
+    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
+        inner = _literal_truth(node.operand)
+        return None if inner is None else not inner
+    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
+        values = [_literal_truth(child) for child in node.values]
+        if any(value is None for value in values):
+            return None
+        return all(values) if isinstance(node.op, ast.And) else any(values)
+    return None
+
+
+def _binding_occurrences(tree: ast.Module) -> dict[str, list[ast.AST]]:
+    """Gather potential lexical writes, conservatively across all scopes."""
+    owners: dict[str, list[ast.AST]] = {}
+
+    def add(name: str, node: ast.AST) -> None:
+        owners.setdefault(name, []).append(node)
+
+    class Visitor(ast.NodeVisitor):
+        def visit_Import(self, node: ast.Import) -> None:
+            for item in node.names:
+                add(item.asname or item.name.split(".")[0], node)
+
+        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
+            for item in node.names:
+                if item.name != "*":
+                    add(item.asname or item.name, node)
+
+        def visit_Name(self, node: ast.Name) -> None:
+            if isinstance(node.ctx, (ast.Store, ast.Del)):
+                add(node.id, node)
+
+        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
+            add(node.name, node)
+            self.generic_visit(node)
+
+        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
+            add(node.name, node)
+            self.generic_visit(node)
+
+        def visit_ClassDef(self, node: ast.ClassDef) -> None:
+            add(node.name, node)
+            self.generic_visit(node)
+
+        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
+            if node.name:
+                add(node.name, node)
+            self.generic_visit(node)
+
+        def visit_arg(self, node: ast.arg) -> None:
+            add(node.arg, node)
+            self.generic_visit(node)
+
+    Visitor().visit(tree)
+    return owners
+
+
+def _known_typing_aliases(
+    tree: ast.Module,
+    before_line: int,
+    bindings: dict[str, list[ast.AST]],
+) -> tuple[set[str], set[str]]:
+    """Identify unshadowed top-level syntactic origins only, not runtime truth."""
+    module_names: set[str] = set()
+    constant_names: set[str] = set()
+    for statement in tree.body:
+        if getattr(statement, "lineno", 0) >= before_line:
+            continue
+        if isinstance(statement, ast.Import):
+            for alias in statement.names:
+                bound = alias.asname or alias.name.split(".")[0]
+                if alias.name == "typing" and bindings.get(bound) == [statement]:
+                    module_names.add(bound)
+        elif isinstance(statement, ast.ImportFrom):
+            if statement.level != 0 or statement.module != "typing":
+                continue
+            for alias in statement.names:
+                bound = alias.asname or alias.name
+                if alias.name == "TYPE_CHECKING" and bindings.get(bound) == [statement]:
+                    constant_names.add(bound)
+    return module_names, constant_names
+
+
+def _is_main_pattern(node: ast.AST) -> bool:
+    if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
+        return False
+    if not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
+        return False
+    left, right = node.left, node.comparators[0]
+    return (
+        isinstance(left, ast.Name) and left.id == "__name__"
+        and isinstance(right, ast.Constant) and right.value == "__main__"
+    ) or (
+        isinstance(right, ast.Name) and right.id == "__name__"
+        and isinstance(left, ast.Constant) and left.value == "__main__"
+    )
+
+
+def _predicate_evidence(
+    node: ast.AST,
+    tree: ast.Module,
+    bindings: dict[str, list[ast.AST]],
+    before_line: int,
+) -> tuple[str, str]:
+    truth = _literal_truth(node)
+    if truth is not None:
+        return "LITERAL_BOOLEAN", "TRUE" if truth else "FALSE"
+    if _is_main_pattern(node):
+        return "MAIN_GUARD_CANDIDATE", "UNKNOWN"
+    modules, names = _known_typing_aliases(tree, before_line, bindings)
+    if isinstance(node, ast.Name) and node.id in names:
+        return "TYPE_CHECKING_CANDIDATE", "UNKNOWN"
+    if (
+        isinstance(node, ast.Attribute)
+        and node.attr == "TYPE_CHECKING"
+        and isinstance(node.value, ast.Name)
+        and node.value.id in modules
+    ):
+        return "TYPE_CHECKING_CANDIDATE", "UNKNOWN"
+    return "UNKNOWN_EXPRESSION", "UNKNOWN"
+
+
+def project_import_guards(
+    tree: ast.AST,
+    provenance: ImportProvenance,
+) -> GuardProjection:
+    """Map each lexical import to guard evidence; never certify cycle safety."""
+    if not isinstance(tree, ast.Module):
+        raise TypeError("tree must be an ast.Module")
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
+    if replay != provenance:
+        raise ValueError("AST import occurrences differ from provenance")
+
+    # Multiple matching If statements are treated as ambiguous, not guessed.
+    lookup: dict[tuple[int, str], list[ast.AST]] = {}
+    for node in ast.walk(tree):
+        if isinstance(node, ast.If):
+            lookup.setdefault(
+                (node.lineno, ast.dump(node.test, include_attributes=False)), []
+            ).append(node.test)
+
+    bindings = _binding_occurrences(tree)
+    assessments: list[ImportGuardAssessment] = []
+    for occurrence in provenance.occurrences:
+        frame_evidence: list[GuardFrameEvidence] = []
+        for frame in occurrence.controls:
+            if frame.kind != "IF":
+                predicate_kind, truth = "NON_IF_CONTROL", "UNKNOWN"
+            else:
+                matches = lookup.get((frame.line, frame.expression or ""), [])
+                if len(matches) != 1:
+                    predicate_kind, truth = "UNRESOLVED_IF", "UNKNOWN"
+                else:
+                    predicate_kind, truth = _predicate_evidence(
+                        matches[0], tree, bindings, frame.line
+                    )
+            if truth == "UNKNOWN":
+                gate = "UNKNOWN"
+            else:
+                taken = (truth == "TRUE") == (frame.branch == "BODY")
+                gate = "POSSIBLE" if taken else "BLOCKED"
+            frame_evidence.append(
+                GuardFrameEvidence(
+                    kind=frame.kind,
+                    branch=frame.branch,
+                    line=frame.line,
+                    predicate_kind=predicate_kind,
+                    predicate_truth=truth,
+                    branch_gate=gate,
+                )
+            )
+
+        if any(frame.branch_gate == "BLOCKED" for frame in frame_evidence):
+            overall = "BLOCKED_BY_LITERAL"
+        elif any(frame.branch_gate == "UNKNOWN" for frame in frame_evidence):
+            overall = "GUARDED_UNKNOWN"
+        else:
+            overall = "NO_KNOWN_GUARD_BLOCKER"
+        assessments.append(
+            ImportGuardAssessment(
+                ordinal=occurrence.ordinal,
+                line=occurrence.line,
+                gate=overall,
+                frames=tuple(frame_evidence),
+            )
+        )
+
+    return GuardProjection(
+        module_id=provenance.module_id,
+        source_fingerprint=provenance.source_fingerprint,
+        assessments=tuple(assessments),
+    )

### FULL_DIFF: tests/test_cycle_semantics_guards.py

diff --git a/tests/test_cycle_semantics_guards.py b/tests/test_cycle_semantics_guards.py
new file mode 100644
index 0000000..178378e
--- /dev/null
+++ b/tests/test_cycle_semantics_guards.py
@@ -0,0 +1,160 @@
+import ast
+import json
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics.provenance import extract_import_provenance
+from contextor.core.cycle_semantics.guards import project_import_guards
+
+
+def project(code):
+    tree = ast.parse(code)
+    p = extract_import_provenance(
+        tree, module_id="p.a", source_key="p/a.py",
+        source_path="C:/fixture/p/a.py", source_fingerprint="fingerprint",
+    )
+    return project_import_guards(tree, p)
+
+
+def test_literal_false_body_and_else():
+    result = project("if False:\n    import a\nelse:\n    import b\n")
+    assert [a.gate for a in result.assessments] == [
+        "BLOCKED_BY_LITERAL", "NO_KNOWN_GUARD_BLOCKER"]
+    assert [f.branch_gate for a in result.assessments for f in a.frames] == [
+        "BLOCKED", "POSSIBLE"
+    ]
+
+
+def test_literal_true_else_blocked():
+    result = project("if True:\n    import a\nelse:\n    import b\n")
+    assert [a.gate for a in result.assessments] == [
+        "NO_KNOWN_GUARD_BLOCKER", "BLOCKED_BY_LITERAL"]
+
+
+def test_nested_condition_false_overrides_dynamic_unknown():
+    result = project("if condition:\n    if False:\n        import a\n")
+    assert result.assessments[0].gate == "BLOCKED_BY_LITERAL"
+    assert [f.branch_gate for f in result.assessments[0].frames] == [
+        "UNKNOWN", "BLOCKED"
+    ]
+
+
+def test_boolean_literals_not_and():
+    result = project(
+        "if not False and True:\n    import a\n"
+        "if True and False:\n    import b\n"
+    )
+    assert [a.gate for a in result.assessments] == [
+        "NO_KNOWN_GUARD_BLOCKER", "BLOCKED_BY_LITERAL"]
+
+
+def test_dynamic_predicate_stays_unknown():
+    result = project("if arbitrary_function():\n    import a\n")
+    assert result.assessments[0].gate == "GUARDED_UNKNOWN"
+    assert result.assessments[0].frames[0].predicate_kind == "UNKNOWN_EXPRESSION"
+
+
+def test_type_checking_direct_alias_candidate_not_proof():
+    result = project(
+        "from typing import TYPE_CHECKING as TC\n"
+        "if TC:\n    import a\n"
+    )
+    assert result.assessments[1].frames[0].predicate_kind == (
+        "TYPE_CHECKING_CANDIDATE"
+    )
+    assert result.assessments[1].gate == "GUARDED_UNKNOWN"
+
+
+def test_typing_module_alias_candidate():
+    result = project("import typing as t\nif t.TYPE_CHECKING:\n    import a\n")
+    assert result.assessments[1].frames[0].predicate_kind == (
+        "TYPE_CHECKING_CANDIDATE"
+    )
+    assert result.assessments[1].gate == "GUARDED_UNKNOWN"
+
+
+def test_unbound_and_shadowed_typechecking_unresolved():
+    p = project("if TC:\n    import a\n")
+    assert p.assessments[0].frames[0].predicate_kind == "UNKNOWN_EXPRESSION"
+    p = project(
+        "from typing import TYPE_CHECKING as TC\n"
+        "TC = True\nif TC:\n    import a\n"
+    )
+    assert p.assessments[1].frames[0].predicate_kind == "UNKNOWN_EXPRESSION"
+
+
+def test_future_alias_import_does_not_count():
+    p = project(
+        "if TC:\n    import a\n"
+        "from typing import TYPE_CHECKING as TC\n"
+    )
+    assert p.assessments[0].frames[0].predicate_kind == "UNKNOWN_EXPRESSION"
+
+
+def test_main_guard_candidate_is_not_runtime_proof():
+    p = project('if __name__ == "__main__":\n    import a\n')
+    assert p.assessments[0].frames[0].predicate_kind == "MAIN_GUARD_CANDIDATE"
+    assert p.assessments[0].gate == "GUARDED_UNKNOWN"
+
+
+def test_try_and_for_controls_unknown():
+    p = project(
+        "try:\n    import a\n"
+        "except ImportError:\n    import b\n"
+        "for x in seq:\n    import c\n"
+    )
+    assert [a.gate for a in p.assessments] == ["GUARDED_UNKNOWN"] * 3
+    assert all(
+        a.frames[0].predicate_kind == "NON_IF_CONTROL"
+        for a in p.assessments
+    )
+
+
+def test_absence_of_guard_is_not_reachability_proof():
+    p = project("def later():\n    import a\n")
+    a = p.assessments[0]
+    assert a.gate == "NO_KNOWN_GUARD_BLOCKER"
+    assert a.initialization_reachability == "UNKNOWN"
+
+
+def test_nested_if_in_function_preserves_lexical_blocker():
+    p = project("def later():\n    if False:\n        import a\n")
+    assert p.assessments[0].gate == "BLOCKED_BY_LITERAL"
+    assert p.assessments[0].initialization_reachability == "UNKNOWN"
+
+
+def test_ast_mismatch_rejected():
+    tree = ast.parse("import a")
+    p = extract_import_provenance(
+        tree, module_id="m", source_key="m.py", source_path="C:/m.py",
+        source_fingerprint="fingerprint"
+    )
+    with pytest.raises(ValueError, match="differ"):
+        project_import_guards(ast.parse("import b"), p)
+
+
+def test_invalid_inputs_rejected():
+    tree = ast.parse("import a")
+    p = extract_import_provenance(
+        tree, module_id="m", source_key="m.py", source_path="C:/m.py",
+        source_fingerprint="fingerprint"
+    )
+    with pytest.raises(TypeError):
+        project_import_guards(None, p)
+    with pytest.raises(TypeError):
+        project_import_guards(tree, None)
+
+
+def test_deterministic_json_compatible_and_nonmutating():
+    code = "if False:\n    import a\n"
+    tree = ast.parse(code)
+    p = extract_import_provenance(
+        tree, module_id="m", source_key="m.py", source_path="C:/m.py",
+        source_fingerprint="fingerprint"
+    )
+    before = ast.dump(tree, include_attributes=True)
+    first = project_import_guards(tree, p)
+    assert first == project_import_guards(tree, p)
+    json.dumps(asdict(first))
+    assert ast.dump(tree, include_attributes=True) == before
