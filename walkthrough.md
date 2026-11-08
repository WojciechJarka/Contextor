# C16-B03-P1D3G18-P2-P11 — restricted module prefix with fail-closed execution boundary

## HEAD_BEFORE_AFTER

- Before and after: `b25c875b156cdb167fd3f46c9a929851d768f375`. Before P11, only `walkthrough.md` was modified. No commit, push or reset.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_package_model.py`
- `tests/test_cycle_semantics_namespace_path_model.py`
- `walkthrough.md` (report; excluded from its own diff)

## D11_ROOT_CAUSE

- CONTRACT_PROVED: P10 compiled an entered module's entire restricted AST before executing any of that module's steps. A later unsupported decorated class in `contextor.core.domain.graph` therefore caused UNKNOWN before its earlier `from dataclasses import dataclass` step was modeled. P11 preserves the accepted prefix and places an unconditional UNKNOWN marker at the first refused statement.

## P11_PREFIX_COMPILATION_CONTRACT

- The new private `_compile_reachable_prefix` first calls the unchanged whole-module `_compile`. On refusal, it uses the specified monotonic binary search over top-level AST prefixes with the same typing guard and annotation mode, then returns accepted steps followed by `_Step("UNMODELED_STATEMENT")`. It is called only when a pending module is entered in the P10 opt-in path.
- The eager/default path still uses unchanged whole-module `_compile`. No decorator, dataclass, class-base, external-import or call special case was added.

## FIRST_UNMODELED_STATEMENT_BOUNDARY

- The interpreter returns UNKNOWN with the current module on `UNMODELED_STATEMENT`; it does not emit a marker event or advance the frame. Earlier accepted modeled steps may emit their own evidence before the boundary. The marker cannot be skipped or promoted to MODEL_PASS.
- The first test run exposed a placement error in the new package-model test: it interrupted an existing test and left three old assertions in the new function, producing `NameError: result is not defined` (1 failed, 321 passed). I moved the new test to the end of that module using direct file edits; the existing assertions and their original test were restored without alteration. The repeated exact six-module suite passed.

## FULL_CPYTHON_VALIDATION_PRESERVED

- CODE_PATH_PROVED: package layout, complete CPython AST validity check, source mapping and `valid_chain` still precede opt-in module entry and prefix compilation. Existing negative tests for CPython-invalid unreachable source remain passing. All real-replay source bytes were checked against one metadata-selected FileState before evaluation.

## STRICT_MODE_PARITY

- The new test confirms default strict mode returns whole-module UNKNOWN at `pkg.a` with zero events for a valid binding followed by decorated class. Opt-in mode records the earlier binding and then returns UNKNOWN at `pkg.a`. All prior strict-mode assertions in the targeted modules passed.

## PACKAGE_SHADOWING_PARITY

- The P10 checks for a pending entered package still operate on the resulting program, whose accepted prefix ends in an unconditional UNKNOWN marker when necessary. Full indexed `programs` keys, from-child candidates, cyclic reentrance, class-local import order and function-body step insertion remain in place. P11 package-parent and reentrant negative tests passed.

## TARGETED_TEST_RESULTS

- Initial exact six-module run: **1 failed, 321 passed** due only to the test-placement `NameError` described above. After restoring placement, repeated exact six-module run using repository CPython 3.15.2: **322 passed in 28.78s**, zero failures. No full pytest.
- `git diff --check` on the three changed source/test files exited 0; only Windows line-ending notices were emitted.

## NEGATIVE_SAFETY_TESTS

- Passing P11 cases cover external import before decorated class, binding before UNKNOWN marker, reentrant import before marker, earlier early-binding hazard, parent stop before child, class-local import ordering, called function steps, deterministic AST immutability and strict-mode parity. Existing P10 source binding, package shadowing, external UNKNOWN and invalid-unreached-source assertions also passed unchanged.

## FACADE_AND_GUI_REPLAY

- DIRECT_EVIDENCE: fresh-process source-bound replay used one FileState generation, revision **1116**, state_id `20261106_195021`, repo_id `ctx_8efc50d8`, root `C:\Temp\Contextor_Repo`. All **308** physical production files matched FileState SHA-256; mismatch count 0.
- Facade entry `contextor.core.api.facade`: selected cohort **202**; digest `0fe88b04d5f4f48d35593c4b5a4dc1a97dbcb3de56ec3c8e2d90573bbdf51615`; UNKNOWN / RESTRICTED_MODEL_UNKNOWN, first UNKNOWN target **`dataclasses`**, 9 events. First START_IMPORT `contextor`, last `contextor.core.domain.graph`. The `domain.graph` module was entered; its prefix attempted the `dataclasses` from-import, which remains outside the closed source domain. There was no modeled `DEFINE_PASSIVE_CLASS` event for its decorated class and no analyzed source execution.
- Ordered facade events: (0) bootstrap START_IMPORT contextor; (1) contextor READY; (2) bootstrap START_IMPORT contextor.core; (3) contextor.core START_IMPORT contextor.core.graph; (4) contextor.core.graph READY; (5) contextor.core BIND_CHILD contextor.core.graph/graph; (6) contextor.core START_IMPORT contextor.core.graph.graph; (7) contextor.core.graph.graph START_IMPORT contextor.core.domain; (8) contextor.core.domain START_IMPORT contextor.core.domain.graph. The UNKNOWN `dataclasses` lookup does not append a success event.
- GUI entry `contextor.ui.gui`: selected cohort **222**; digest `b2a169e33d34c73dd0a4335331aa8d1f8fe963c784d6893742d9de950b1d8968`; UNKNOWN / RESTRICTED_MODEL_UNKNOWN, first UNKNOWN target **`os`**, 4 events. First START_IMPORT `contextor`, last `contextor.ui.gui`. `domain.graph` was not entered, `dataclasses` was not attempted, and no decorated-class event occurred.
- Ordered GUI events: (0) bootstrap START_IMPORT contextor; (1) contextor READY; (2) bootstrap START_IMPORT contextor.ui; (3) contextor.ui START_IMPORT contextor.ui.gui. Both calls preserve outer authority `SOURCE_BOUND_CALLER_SUPPLIED_INVENTORY_NOT_RUNTIME_OR_LIVE_PROOF`, inner `CONDITIONAL_ORDERED_INVENTORY_AND_AST_NOT_RUNTIME_OR_LIVE_PROOF`, and nested model scope `RESTRICTED_REGULAR_PACKAGE_MODEL`. Neither conditional result is runtime safety proof.

## SCC1_SCC2_GATES

- DIRECT_EVIDENCE: current canonical snapshot at revision 1116, matching state_id. SCC1: **44** members / **202** optional sources; SCC2: **9** members / **222** optional sources. All selected closure source hashes matched FileState. Both graph-consistency outcomes remain INDETERMINATE / NAMESPACE_IMPORT_RESOLUTION_UNMODELED with **4** namespace candidates; external gate OPAQUE_EXECUTION_POSSIBLE. Opaque external candidates: SCC1 **608**, SCC2 **726**.
- MCP reports structural DFS cycles **16**, active warnings **16**, model_pass_count **0**, cycle_semantics **stale**. No early-binding hazard was proven by either real-repo conditional replay before its external UNKNOWN. No warning suppression, MODEL_PASS promotion or /3 receipt was performed.

## MCP_POST_CHANGE_AUDIT

- Contextor MCP contexts for the changed production module and both test modules: canonical revision **1116**, canonical_state=fresh, workspace_sync=verified, advisory_warning=null, LIVE provenance; graph/cycles fresh, cycle_semantics stale; syntax_errors=0, structural DFS cycles=16, active warnings=16, model_pass_count=0. Metadata confirms state_id `20261106_195021`, repo_id `ctx_8efc50d8`.
- Changed-file disk SHA-256 equals FileState: `package_model.py` `11fc5e227574042dc6783b44b71e7097bce2f057e32d7df6a6e1a0a365cb2166`; `test_cycle_semantics_package_model.py` `e6dac61e6fdde2bb7799ee967a8048bf3fc489f82bf2dc5a9aa3cf6a1680a5f2`; `test_cycle_semantics_namespace_path_model.py` `99094e8244fb7918146c821ecf20b89977009657a9af844f7d00c9b5df630560`.

## RESTART_DECISION

- No Desktop/backend restart. Fresh-process replay loaded P11 directly. Adoption by the active Desktop/backend process remains **UNVERIFIED** until a later controlled restart and identity audit of interpreter, process, GUI ownership and LIVE authority.

## REMAINING_UNKNOWN

- Actual application import finder, `sys.path`, `sys.meta_path`, `sys.modules`, external import effects and live-process loaded-code identity remain unknown. Cycle-semantics canonical family is stale. UNKNOWN is not proof of safety.

## FULL_DIFFS

Complete actual diffs for all three changed production/test files follow. `walkthrough.md` is excluded from its own diff.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 363dca0..4ccaa26 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -911,6 +911,83 @@ def _compile(
     return tuple(steps)
 
 
+def _compile_reachable_prefix(
+    tree: ast.Module,
+    logical: str,
+    package: bool,
+    *,
+    typing_guard: RecognizedTypingGuard | None,
+    annotation_semantics: str | None,
+) -> tuple[_Step, ...] | None:
+    """Preserve modeled effects before the first unsupported statement.
+
+    This helper is used only for a module actually entered by
+    the opt-in import-order simulator.
+
+    The caller must already have validated the complete
+    original AST with CPython compile(), without execution.
+
+    An unsupported statement is an unavoidable UNKNOWN
+    boundary, never an instruction that may be skipped.
+    """
+
+    complete = _compile(
+        tree,
+        logical,
+        package,
+        typing_guard=typing_guard,
+        annotation_semantics=annotation_semantics,
+    )
+
+    if complete is not None:
+        return complete
+
+    if not tree.body:
+        return None
+
+    def compile_prefix(
+        count: int,
+    ) -> tuple[_Step, ...] | None:
+        return _compile(
+            ast.Module(
+                body=tree.body[:count],
+                type_ignores=[],
+            ),
+            logical,
+            package,
+            typing_guard=typing_guard,
+            annotation_semantics=annotation_semantics,
+        )
+
+    # The existing restricted compiler processes top-level
+    # statements in order and aborts on its first refusal.
+    # Prefix support is monotonic for the same full-tree
+    # typing guard and annotation semantics.
+
+    low = 0
+    high = len(tree.body)
+
+    while low + 1 < high:
+        middle = (low + high) // 2
+
+        if compile_prefix(middle) is None:
+            high = middle
+        else:
+            low = middle
+
+    accepted = compile_prefix(low)
+
+    if (
+        accepted is None
+        or compile_prefix(high) is not None
+    ):
+        return None
+
+    return accepted + (
+        _Step("UNMODELED_STATEMENT"),
+    )
+
+
 def evaluate_package_import_order(
     indexed_sources: Mapping[str, ast.AST],
     entry_module: str,
@@ -1247,7 +1324,7 @@ def evaluate_package_import_order(
                 frozenset(indexed_sources),
             )
 
-            program = _compile(
+            program = _compile_reachable_prefix(
                 tree,
                 module,
                 module in packages,
@@ -1726,6 +1803,9 @@ def evaluate_package_import_order(
                 )
             )
 
+        elif step.op == "UNMODELED_STATEMENT":
+            return result("UNKNOWN", module)
+
         else:
             return result("UNKNOWN")
 
diff --git a/tests/test_cycle_semantics_namespace_path_model.py b/tests/test_cycle_semantics_namespace_path_model.py
index 0403be6..442e1fa 100644
--- a/tests/test_cycle_semantics_namespace_path_model.py
+++ b/tests/test_cycle_semantics_namespace_path_model.py
@@ -420,6 +420,251 @@ def test_g18_p2_p5_unlisted_shadowing_source_unknown():
     )
 
 
+def test_p11_external_import_precedes_decorator_boundary():
+    sources = {
+        "ns.a": ast.parse(
+            "from dataclasses import dataclass\n"
+            "@dataclass(frozen=True)\n"
+            "class Model:\n"
+            "    value: int\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == (
+        "dataclasses"
+    )
+
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        for event in result.model_assessment.events
+    )
+
+
+def test_p11_binding_before_unknown_boundary():
+    sources = {
+        "ns.a": ast.parse(
+            "value = 1\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.a"
+
+    assert any(
+        event.operation == "BIND"
+        and event.module == "ns.a"
+        and event.symbol == "value"
+        for event in result.model_assessment.events
+    )
+
+
+def test_p11_reentrant_import_before_unknown_boundary():
+    sources = {
+        "ns.a": ast.parse(
+            "value = 1\n"
+            "import ns.b\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+        "ns.b": ast.parse(
+            "from ns.a import value\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.a"
+
+    events = result.model_assessment.events
+
+    assert any(
+        event.operation == "START_IMPORT"
+        and event.target == "ns.b"
+        for event in events
+    )
+
+    assert any(
+        event.operation == "FROM"
+        and event.module == "ns.b"
+        and event.target == "ns.a"
+        and event.symbol == "value"
+        for event in events
+    )
+
+    assert not any(
+        event.operation == "EARLY_BINDING_HAZARD"
+        for event in events
+    )
+
+
+def test_p11_early_binding_hazard_precedes_later_unknown():
+    sources = {
+        "ns.a": ast.parse(
+            "import ns.b\n"
+            "value = 1\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+        "ns.b": ast.parse(
+            "from ns.a import value\n"
+        ),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == (
+        "CONDITIONAL_EARLY_BINDING_HAZARD"
+    )
+    assert result.model_assessment is not None
+    assert result.model_assessment.outcome == (
+        "EARLY_BINDING_HAZARD"
+    )
+
+    assert any(
+        event.operation == "EARLY_BINDING_HAZARD"
+        for event in result.model_assessment.events
+    )
+
+
+def test_p11_unknown_parent_stops_before_child_entry():
+    sources = {
+        "pkg.__init__": ast.parse(
+            "value = 1\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+        "pkg.ns.a": ast.parse("pass\n"),
+    }
+
+    result = _p10_assess(
+        sources,
+        entry="pkg.ns.a",
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "pkg"
+
+    events = result.model_assessment.events
+
+    assert any(
+        event.operation == "BIND"
+        and event.module == "pkg"
+        and event.symbol == "value"
+        for event in events
+    )
+
+    assert not any(
+        event.operation == "START_IMPORT"
+        and event.target == "pkg.ns.a"
+        for event in events
+    )
+
+
+def test_p11_class_local_import_before_unknown_boundary():
+    sources = {
+        "ns.a": ast.parse(
+            "class Holder:\n"
+            "    import ns.b\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+        "ns.b": ast.parse("pass\n"),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.a"
+
+    assert any(
+        event.operation == "CLASS_LOCAL_IMPORT"
+        and event.module == "ns.a"
+        and event.target == "ns.b"
+        for event in result.model_assessment.events
+    )
+
+
+def test_p11_called_function_steps_precede_unknown_boundary():
+    sources = {
+        "ns.a": ast.parse(
+            "def run():\n"
+            "    import ns.b\n"
+            "run()\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+        "ns.b": ast.parse("pass\n"),
+    }
+
+    result = _p10_assess(sources)
+
+    assert result.outcome == "UNKNOWN"
+    assert result.model_assessment is not None
+    assert result.model_assessment.target_module == "ns.a"
+
+    events = result.model_assessment.events
+
+    assert any(
+        event.operation == "CALL_FUNCTION"
+        and event.module == "ns.a"
+        and event.symbol == "run"
+        for event in events
+    )
+
+    assert any(
+        event.operation == "START_IMPORT"
+        and event.target == "ns.b"
+        for event in events
+    )
+
+
+def test_p11_deterministic_without_ast_mutation():
+    sources = {
+        "ns.a": ast.parse(
+            "value = 1\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    before = {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in sources.items()
+    }
+
+    first = _p10_assess(sources)
+    second = _p10_assess(sources)
+
+    assert first == second
+    assert first.outcome == "UNKNOWN"
+
+    assert before == {
+        name: ast.dump(tree, include_attributes=True)
+        for name, tree in sources.items()
+    }
+
+
 def _p10_assess(sources, entry="ns.a"):
     paths = frozenset(
         module.replace(".", "/") + ".py"
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index a91541e..5556799 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -1504,3 +1504,41 @@ def test_p10_private_mode_rejects_session_combination():
     )
 
     assert result.outcome == "UNKNOWN"
+
+
+def test_p11_strict_mode_remains_whole_module_unknown():
+    sources = {
+        "pkg.__init__": ast.parse("pass"),
+        "pkg.a": ast.parse(
+            "value = 1\n"
+            "@unknown_decorator\n"
+            "class Bad:\n"
+            "    pass\n"
+        ),
+    }
+
+    strict = evaluate_package_import_order(
+        sources,
+        "pkg.a",
+        annotation_semantics="DEFERRED",
+    )
+
+    opt_in = evaluate_package_import_order(
+        sources,
+        "pkg.a",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+    )
+
+    assert strict.outcome == "UNKNOWN"
+    assert strict.target_module == "pkg.a"
+    assert strict.events == ()
+
+    assert opt_in.outcome == "UNKNOWN"
+    assert opt_in.target_module == "pkg.a"
+    assert any(
+        event.operation == "BIND"
+        and event.module == "pkg.a"
+        and event.symbol == "value"
+        for event in opt_in.events
+    )
```

## FINAL_VERDICT

PASS. Exact P11 implementation and test scope completed; 322 targeted tests passed; both real source-bound replays remain UNKNOWN at external imports; 16 structural cycles and 16 active warnings remain; active-process code adoption is unverified.
