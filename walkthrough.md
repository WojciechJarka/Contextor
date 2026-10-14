# CONTEXTOR_B0G4B1_IMPORT_EXECUTION_CONTEXT

STATUS: Completed controlled implementation; stop at this stage and await `proceduj`.

## PRECHECK / DIRECT_EVIDENCE

HEAD_BEFORE: e15f597842e81ef978e316ffb908755029b4f31d
EXPECTED_PREVIOUS_HEAD: c7d68154b5a7b180a86b1591f590247504cec745
HEAD_RELATION: Expected commit is an ancestor of current HEAD (`git merge-base --is-ancestor` exit 0). Current HEAD includes the B0G4B0 provenance foundation. Git status before change was clean. Both B0G4B1 target files were absent.
HEAD_AFTER: e15f597842e81ef978e316ffb908755029b4f31d
LIVE_REVISION_BEFORE: 403; activity_epoch=1beab26da2ff4932852caa7db6ff4242; continuity=continuous; resync_required=false; canonical_state=fresh; workspace_sync=unverified in global LIVE overlay; cycles=16.
LIVE_REVISION_AFTER: 405; same activity_epoch; continuity=continuous; resync_required=false; canonical_state=fresh; all reported families fresh; no parse-stale modules; cycles=16. Target production file workspace_sync=verified by full get_file_edit_context at revision 405. Global overlay reports workspace_sync=unverified because it does not hash files.
WATCHER_EVENTS: revision 404 UPDATED execution_context.py and revision 405 UPDATED test_cycle_semantics_execution_context.py, both origin=desktop_watcher, blast_radius_state=fresh. No MCP update_file call.

## FILES_CHANGED

- contextor/core/cycle_semantics/execution_context.py (new)
- tests/test_cycle_semantics_execution_context.py (new)

No existing production module, existing test, or public MCP documentation was modified. `walkthrough.md` is this report and is excluded from source/test diff accounting.

## IMPLEMENTATION_CONTRACT

CONTRACT_PROVED: The new projection accepts only ImportProvenance, preserves source order, import occurrence ordinal and line, scope nesting through ordered activation_requirements, and ordered control kinds. It emits MODULE_OR_CLASS_CANDIDATE, CALL_DEPENDENT, or UNKNOWN. Any unsupported scope yields UNKNOWN. All controls are UNEVALUATED, and every result has initialization_reachability=UNKNOWN. Duplicate occurrence ordinals and wrong input type fail closed. Dataclasses are frozen and all result collections are tuples.
CODE_PATH_PROVED: The implementation iterates supplied immutable provenance facts and constructs new result objects. It does not read source files, parse or mutate AST, execute analyzed source, mutate graph edges or canonical state, or call LIVE/MCP publication. The tests exercise B0G4B0 extraction from `ast.parse` input and JSON-compatible deterministic output.
DIRECT_EVIDENCE: File contents matched the auditor-provided exact code sections after writing. Only the two named files are untracked in Git. Contextor before-change provenance module had direct consumers `__init__` and provenance tests. At revision 405, Contextor reports the new production module's only direct consumer and covering test as `tests.test_cycle_semantics_execution_context`; downstream consumers=0. Syntax diagnostics are fresh with no errors for both new files.

## TEST_COMMAND

`& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_execution_context.py tests/test_cycle_semantics_provenance.py`

## TEST_RESULTS

Python 3.10.9. Exit code 0: 23 passed in 1.21s. No other tests or full suite run.

## NO_WARNING_SUPPRESSION

CODE_PATH_PROVED: Neither new file contains ArchitectureCycle, warning suppression, or diagnostic publication logic. The existing warning producer and public projection are untouched. No `SAFE`, `RUNTIME_CONFIRMED`, or `NO_INITIALIZATION_HAZARD` state is produced. Contextor LIVE diagnostics retain 16 cycles before and after indexing.

## GRAPH_CONTRACT_UNCHANGED

CODE_PATH_PROVED: The pure projection accepts provenance data and returns frozen lexical facts; it has no graph input/output or graph mutation call. Existing graph implementation and schemas were untouched. The watcher indexed two new source/test modules and thus may add normal dependency edges for those modules; this report does not claim a byte-identical whole-repository graph. Contextor reports graph/topology families fresh and cycle count 16 at revision 405.

## NO_DIRECT_LIVE_PUBLICATION

CODE_PATH_PROVED: The new module is imported directly only by its targeted test. It is not exported in package `__init__.py` and is not wired into FULL, incremental, MCP, LIVE, snapshot schema, or warning publication. Desktop watcher indexing is an external observation, not direct publication by this component. No restart is required for this disconnected stage.

## UNRESOLVED_LIMITATIONS

UNKNOWN: Lexical scope and guard facts do not prove runtime reachability, import safety, or cycle-failure outcome. No runtime execution of analyzed sources, broad suite, or full analysis was requested or performed. Global LIVE overlay workspace sync remains unverified at repository scope; the changed production file was verified against disk at revision 405.

## FINAL_VERDICT

B0G4B1_PASS — the exact two-file auditor implementation is present, targeted tests pass, LIVE watcher indexed both files with fresh canonical state, and no integration or warning suppression was added. Await `proceduj`.

## FULL_DIFFS

### FULL_DIFF: contextor/core/cycle_semantics/execution_context.py

diff --git a/contextor/core/cycle_semantics/execution_context.py b/contextor/core/cycle_semantics/execution_context.py
new file mode 100644
index 0000000..240e226
--- /dev/null
+++ b/contextor/core/cycle_semantics/execution_context.py
@@ -0,0 +1,88 @@
+"""Conservative lexical activation requirements for explicit imports.
+
+This is not a reachability, safety, or runtime-failure classifier.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+from .provenance import ImportProvenance
+
+
+_SCOPE_REQUIREMENT = {
+    "CLASS": "EXECUTE_CLASS_DEFINITION",
+    "FUNCTION": "CALL_FUNCTION_BODY",
+    "ASYNC_FUNCTION": "RESUME_COROUTINE_BODY",
+}
+
+
+@dataclass(frozen=True)
+class ImportExecutionContext:
+    ordinal: int
+    line: int
+    phase: str
+    activation_requirements: tuple[str, ...]
+    control_kinds: tuple[str, ...]
+    guard_evaluation: str
+    initialization_reachability: str
+
+
+@dataclass(frozen=True)
+class ExecutionContextProjection:
+    module_id: str
+    source_fingerprint: str
+    contexts: tuple[ImportExecutionContext, ...]
+
+
+def project_execution_context(
+    provenance: ImportProvenance,
+) -> ExecutionContextProjection:
+    """Project lexical facts without inferring a safe import cycle.
+
+    MODULE_OR_CLASS_CANDIDATE does not imply unconditional execution.
+    CALL_DEPENDENT does not imply safety during module initialization.
+    """
+    if not isinstance(provenance, ImportProvenance):
+        raise TypeError("provenance must be ImportProvenance")
+
+    output: list[ImportExecutionContext] = []
+    seen_ordinals: set[int] = set()
+
+    for occurrence in provenance.occurrences:
+        if occurrence.ordinal in seen_ordinals:
+            raise ValueError("duplicate import occurrence ordinal")
+        seen_ordinals.add(occurrence.ordinal)
+
+        requirements = tuple(
+            _SCOPE_REQUIREMENT.get(scope.kind, "UNKNOWN_SCOPE_ACTIVATION")
+            for scope in occurrence.scopes
+        )
+        scope_types = {scope.kind for scope in occurrence.scopes}
+
+        if "UNKNOWN_SCOPE_ACTIVATION" in requirements:
+            phase = "UNKNOWN"
+        elif scope_types & {"FUNCTION", "ASYNC_FUNCTION"}:
+            phase = "CALL_DEPENDENT"
+        else:
+            phase = "MODULE_OR_CLASS_CANDIDATE"
+
+        output.append(
+            ImportExecutionContext(
+                ordinal=occurrence.ordinal,
+                line=occurrence.line,
+                phase=phase,
+                activation_requirements=requirements,
+                control_kinds=tuple(frame.kind for frame in occurrence.controls),
+                guard_evaluation=(
+                    "UNEVALUATED" if occurrence.controls else "NO_LEXICAL_CONTROL"
+                ),
+                initialization_reachability="UNKNOWN",
+            )
+        )
+
+    return ExecutionContextProjection(
+        module_id=provenance.module_id,
+        source_fingerprint=provenance.source_fingerprint,
+        contexts=tuple(output),
+    )

### FULL_DIFF: tests/test_cycle_semantics_execution_context.py

diff --git a/tests/test_cycle_semantics_execution_context.py b/tests/test_cycle_semantics_execution_context.py
new file mode 100644
index 0000000..197ca73
--- /dev/null
+++ b/tests/test_cycle_semantics_execution_context.py
@@ -0,0 +1,124 @@
+import ast
+from dataclasses import asdict
+
+import pytest
+
+from contextor.core.cycle_semantics import extract_import_provenance
+from contextor.core.cycle_semantics.execution_context import (
+    project_execution_context,
+)
+from contextor.core.cycle_semantics.provenance import (
+    ImportProvenance,
+    ImportOccurrence,
+    ScopeFrame,
+)
+
+
+def project(code):
+    facts = extract_import_provenance(
+        ast.parse(code),
+        module_id="pkg.a",
+        source_key="pkg/a.py",
+        source_path="C:/fixture/pkg/a.py",
+        source_fingerprint="fingerprint",
+    )
+    return project_execution_context(facts)
+
+
+def test_module_and_class_import_candidates_not_certified_safe():
+    p = project("import a\nclass K:\n    import b\n")
+    assert [c.phase for c in p.contexts] == [
+        "MODULE_OR_CLASS_CANDIDATE", "MODULE_OR_CLASS_CANDIDATE"
+    ]
+    assert p.contexts[1].activation_requirements == ("EXECUTE_CLASS_DEFINITION",)
+    assert all(c.initialization_reachability == "UNKNOWN" for c in p.contexts)
+
+
+def test_function_and_method_are_call_dependent_not_safe():
+    p = project("def f():\n    import a\nclass K:\n    def g(self):\n        import b\n")
+    assert [c.phase for c in p.contexts] == ["CALL_DEPENDENT"] * 2
+    assert p.contexts[1].activation_requirements == (
+        "EXECUTE_CLASS_DEFINITION", "CALL_FUNCTION_BODY"
+    )
+
+
+def test_nested_class_inside_function_requires_parent_call():
+    p = project("def f():\n    class K:\n        import x\n")
+    assert p.contexts[0].phase == "CALL_DEPENDENT"
+    assert p.contexts[0].activation_requirements == (
+        "CALL_FUNCTION_BODY", "EXECUTE_CLASS_DEFINITION"
+    )
+
+
+def test_async_body_requires_resume():
+    p = project("async def f():\n    import a\n")
+    assert p.contexts[0].activation_requirements == ("RESUME_COROUTINE_BODY",)
+    assert p.contexts[0].phase == "CALL_DEPENDENT"
+
+
+def test_controls_not_evaluated():
+    p = project(
+        "if False:\n    import a\n"
+        "try:\n    import b\n"
+        "except ImportError:\n    import c\n"
+    )
+    assert [c.control_kinds for c in p.contexts] == [
+        ("IF",), ("TRY",), ("EXCEPT",)
+    ]
+    assert all(c.guard_evaluation == "UNEVALUATED" for c in p.contexts)
+    assert all(c.initialization_reachability == "UNKNOWN" for c in p.contexts)
+
+
+def test_control_in_function_preserves_both_dimensions():
+    p = project("def f():\n    if ready:\n        import a\n")
+    c = p.contexts[0]
+    assert c.phase == "CALL_DEPENDENT"
+    assert c.control_kinds == ("IF",)
+    assert c.initialization_reachability == "UNKNOWN"
+
+
+def test_no_imports_stable():
+    p = project("x = 1\n")
+    assert p.contexts == ()
+    assert p.source_fingerprint == "fingerprint"
+
+
+def test_repeated_occurrences_preserved_in_source_order():
+    p = project("import a\nimport a\n")
+    assert tuple(c.ordinal for c in p.contexts) == (0, 1)
+    assert p.contexts[0].line != p.contexts[1].line
+
+
+def test_projection_is_deterministic_and_json_compatible():
+    p = project("class A:\n    import x\n")
+    assert p == project("class A:\n    import x\n")
+    import json
+    json.dumps(asdict(p))
+
+
+def test_unknown_scope_fail_closed():
+    occurrence = ImportOccurrence(
+        ordinal=0, line=1, column=0, end_line=1, end_column=8,
+        form="IMPORT", module=None, level=0, aliases=(("a", None),),
+        scopes=(ScopeFrame("FUTURE_SCOPE", "f", 1),), controls=()
+    )
+    facts = ImportProvenance("p", "p.py", "C:/p.py", "sha", (occurrence,))
+    c = project_execution_context(facts).contexts[0]
+    assert c.phase == "UNKNOWN"
+    assert c.activation_requirements == ("UNKNOWN_SCOPE_ACTIVATION",)
+
+
+def test_duplicate_ordinal_fails_closed():
+    occurrence = ImportOccurrence(
+        ordinal=0, line=1, column=0, end_line=1, end_column=8,
+        form="IMPORT", module=None, level=0, aliases=(("a", None),),
+        scopes=(), controls=()
+    )
+    facts = ImportProvenance("p", "p.py", "C:/p.py", "sha", (occurrence, occurrence))
+    with pytest.raises(ValueError, match="duplicate"):
+        project_execution_context(facts)
+
+
+def test_wrong_input_type_rejected():
+    with pytest.raises(TypeError):
+        project_execution_context(None)
