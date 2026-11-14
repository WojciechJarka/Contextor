# P5-M08-I10-I4-R1/R2/R3 — indexed class decorator admission and test contracts

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was queried first. R3 preflight canonical LIVE revision was 1397, provenance live, canonical state fresh, workspace_sync unverified, syntax errors 0, structural DFS count 16, and cycle_semantics stale. This was the preflight snapshot, not a post-change audit.
- DIRECT_EVIDENCE: HEAD was 0d80d3e7078c7dc9fe9ce98101dce7d4e38ec3a9 on main. Before the R3 assertion correction, status showed the preserved R2 baseline edit, the report edit, and the untracked A-P regression file; package_model.py had no worktree diff. CPython was 3.15.2.
- DIRECT_EVIDENCE: HEAD is labeled “Auto-commit: Cleanup and update” and contains the I4-R1 production patch. The exact production delta from prior report baseline 396ebd24b7a68519113fd612bae3b8b3bbbd977c matches the reported I4-R1 patch below. It is committed in current HEAD, so it is not an uncommitted diff in this checkout. No Git operation changing the index/history was performed in this task.
- DIRECT_EVIDENCE: T4-C baseline, R2 model-only marker normalization, A-P admission regression file, and prior R2 report were present. Its twelve CASES retain the original source mappings and CPython references.
- DIRECT_EVIDENCE: the current baseline helper passed the exact case source strings directly to the evaluator before this task. R2 now makes a separate model_sources mapping; no case["sources"] object is modified.
- DIRECT_EVIDENCE: production source matches the I4-R1 requirements: the ClassDef gate accepts earlier DEFINE_FUNCTION/FROM at package_model.py:859-866; first decorated class object checks and uses _RestrictedFunction and defining_module at 2658-2672; its frame records binding_module at 2693-2702. The shared continuation remains unchanged.

## FILES_CHANGED

- tests/test_cycle_semantics_cross_module_class_decorator_baseline.py — preserved R2 model-only marker normalization and exact model event contracts; full diff below.
- tests/test_cycle_semantics_class_decorator_import_admission.py — untracked A-P admission and boundary regression file from R2, with the one authorized R3 assertion correction; complete current source below.
- contextor/core/cycle_semantics/package_model.py — unchanged in R2/R3. I4-R1 production delta is present in HEAD and reproduced separately below for the combined report.
- walkthrough.md — overwritten with this report; report-only.
- No other source or test file changed. No Git index/history operation was performed.

## CHANGE_LINEAGE

- I4-R1 production changes are already present in HEAD 0d80d3e; package_model.py has no current worktree diff.
- I4-R2 changes to the twelve-case baseline remain uncommitted in the modified baseline test file. The A-P admission regression file remains untracked.
- I4-R3 changes only one assertion in that untracked admission file; the file remains untracked and was not staged.

## DECORATED_FUNCTION_EVENT_ROOT_CAUSE

R2's added test correctly observed MODEL_PASS and CALL_FUNCTION(identity), but expected the compiler's internal Step name DEFINE_DECORATED_FUNCTION as a public event. The compiler uses that internal Step at package_model.py:1150-1172. The evaluator's branch at 2249-2300 emits the public DEFINE_FUNCTION(work) event followed by CALL_FUNCTION(identity). The R3 one-assertion correction now checks the public event contract.

## EXACT_R3_ASSERTION_CORRECTION

Only tests/test_cycle_semantics_class_decorator_import_admission.py changed in R3. In test_l_imported_decorated_function_contract_is_unchanged, the event operation expectation changed from DEFINE_DECORATED_FUNCTION to DEFINE_FUNCTION. The event symbol, MODEL_PASS assertion, CALL_FUNCTION(identity) assertion, fixture source, and all other assertions are preserved.

## INSTRUMENTATION_ROOT_CAUSE

- DIRECT_EVIDENCE: case C and case J use the exact CPython observation marker source __contextor_effect__ = True in indexed effect modules. Existing restricted assignment compilation rejects that dunder assignment, so the model previously returned UNKNOWN before executing the app.
- DIRECT_EVIDENCE: _model_record previously parsed case["sources"] directly. The marker was therefore part of the model input even though it only records whether CPython imported an effect module.
- CONTRACT_PROVED: this task explicitly identifies that marker as test instrumentation, requires preserving the CPython fixtures, and authorizes model-only normalization to pass for these exact effect-module names.

## CPYTHON_SOURCE_PRESERVATION

The twelve original case["sources"] mappings, reference runner, source writer, subprocess arguments, marker detection, and CPython reference assertions are unchanged. All twelve subprocess comparisons ran during the first gate and passed, including CPython 3.15.2 version assertions.

## MODEL_ONLY_EFFECT_SOURCE_NORMALIZATION

_model_record now builds a new model_sources mapping. It substitutes "pass\n" only when both conditions hold: the logical module is pkg.effect or pkg.decorators.effect, and the original source is exactly "__contextor_effect__ = True\n". All other module source strings are copied unchanged. Only model AST construction uses model_sources. CPython still receives case["sources"].

For case D, the separate C() negative probe appends to the copied model app source through the helper argument; the original case mapping and CPython fixture remain unchanged.

## COMPILER_FROM_BINDING_ADMISSION

The preserved I4-R1 gate matches the exact earlier binding for each decorator and admits only DEFINE_FUNCTION or FROM steps. The new A-G regressions pass in gate 1, covering earlier matching FROM, exact alias binding, late FROM, unrelated FROM, BIND, IMPORT, and incomplete stacked-name admission.

## RUNTIME_RESTRICTED_OBJECT_ADMISSION

The preserved I4-R1 runtime path admits only a captured one-parameter _RestrictedFunction whose defining module is indexed and compiled. It executes in that defining module, records the applying module as binding_module, and uses the existing continuation. The new positive and negative cases in A, B, H, I, J, and P passed in gate 1; H, I, and J include their model boundary assertions.

## CLASS_FACT_IDENTITY

Case I in the T4-C baseline and regression J both produce a class definition followed by the supported Child definition after an imported identity decorator. The new regression asserts the class-definition and call event sequence. The CPython reference separately verifies that the final class binding is the first decorator input and that Child is a subclass instantiable as the base. No additional runtime identity claim is inferred solely from MODEL_PASS.

## FIRST_DECORATOR_EXECUTION_MODULE

Cases C and J passed with the decorator call attributed to pkg.app and effect initialization executed in pkg.decorators. C emits FUNCTION_LOCAL_IMPORT for pkg.effect. J emits FUNCTION_LOCAL_FROM under pkg.decorators and starts pkg.decorators.effect; it does not start pkg.effect.

## SHARED_STACK_CONTINUATION

No production continuation was changed. Existing indexed class stacks G and H passed with bottom-to-top calls. The new function-stack regression M also passed, preserving the indexed function decorator contract.

## APPLYING_MODULE_RESULT_BINDING

The preserved R1 frame binds the final decorated class in the applying module. Cases A, B, C, D, G, H, I, and J completed their model contracts in the T4-C baseline gate. Case D's additional model-only C() probe returned UNKNOWN and emitted no CALL_FUNCTION(C).

## CPYTHON_PARITY_MATRIX

All twelve CPython references passed in the first gate:

| Case | CPython observation |
|---|---|
| A | Import succeeds; pkg.decorators.identity is called; C is a class and is the decorator input. |
| B | Import succeeds; exported identity is called through alias; C remains the decorator input class. |
| C | Import succeeds; decorate runs in pkg.decorators and imports pkg.effect. |
| D | Import succeeds; replace returns None and final C is None. |
| E | Import succeeds; decorate and nested factory are called in pkg.decorators. |
| F | TypeError; identity was rebound to None before decoration and no decorator call occurs. |
| G | Import succeeds; bottom runs before upper, in pkg.app then pkg.upper. |
| H | Import succeeds; lower runs before upper in distinct defining modules. |
| I | Import succeeds; identity returns C unchanged and Child subclasses C. |
| J | Import succeeds; relative effect is pkg.decorators.effect, not pkg.effect. |
| K | Import succeeds; same-module identity decorator returns C unchanged. |
| L | Import succeeds; external dataclasses.dataclass runs and binds a class. |

## ALIASES_AND_RELATIVE_IMPORTS

Case B passes with FROM exporting identity and CALL_FUNCTION(alias) under pkg.app. Case A passes with CALL_FUNCTION(identity). The alias is taken from the captured binding, not resolved by name after class creation. Case J passes with START_IMPORT(pkg.decorators.effect) and FUNCTION_LOCAL_FROM under pkg.decorators; pkg.effect is not imported.

## INTERMEDIATE_NONE

Case D's class definition is MODEL_PASS and its CPython final binding is None. A separate model-only app source with C() returns UNKNOWN and has no CALL_FUNCTION(C). No callability is inferred from the successful class-definition result.

## SUBCLASS_IDENTITY

T4-C case I passed with DEFINE_PASSIVE_CLASS(C), CALL_FUNCTION(identity), then DEFINE_PASSIVE_CLASS(Child). Regression J passed with Product followed by Child. CPython independently confirms subclass identity and instantiation for case I.

## NEGATIVE_BOUNDARIES

- E and new case P remain UNKNOWN for the nested helper call. No CALL_FUNCTION(decorate) or CALL_FUNCTION(helper) is emitted.
- F remains UNKNOWN after the imported decorator binding is rebound to None; no decorator call is emitted.
- L and new case H remain UNKNOWN for the external dataclasses callable; no CALL_FUNCTION(dataclass) is emitted.
- New case O passes both unsupported base and unsupported metaclass variants as UNKNOWN with no decorator call.
- New cases C-G pass the compiler admission/rejection boundaries without admitting late, unrelated, BIND-only, IMPORT-only, or partially bound stacks.

## FIRST_GATE_RESULTS

Command: .\\.venv\\Scripts\\python.exe -m pytest -q tests/test_cycle_semantics_class_decorator_import_admission.py tests/test_cycle_semantics_cross_module_class_decorator_baseline.py -rs

Result after the exact R3 correction: 29 passed in 5.50s. This includes all twelve CPython 3.15.2 reference cases and all A-P admissions.

## FULL_TARGETED_RESULTS

Command: .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_class_decorator_import_admission.py tests/test_cycle_semantics_cross_module_class_decorator_baseline.py tests/test_cycle_semantics_class_decorator_baseline.py tests/test_cycle_semantics_class_decorator_execution.py tests/test_cycle_semantics_class_decorator_identity_counterexamples.py tests/test_cycle_semantics_class_decorator_staging.py tests/test_cycle_semantics_cross_module_stack_continuation.py tests/test_cycle_semantics_cross_module_stacked_baseline.py tests/test_cycle_semantics_cross_module_single_decorator.py tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_function_frame_result_owner.py tests/test_cycle_semantics_decorator_snapshots.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_cycle_semantics_package_model.py -rs

Result: 344 passed, 4 failed in 35.87s. No additional assertion or production changes were made after these failures.

The four failing tests all use this identical fixture: indexed pkg.decorators defines identity(cls) returning cls; pkg.app imports identity and applies it to a passive class C. The model result for each is MODEL_PASS, target_module=None, symbol=None, with evidence_scope RESTRICTED_REGULAR_PACKAGE_MODEL. Complete actual model events:

    0  module=\x00ENTRY operation=START_IMPORT target=pkg symbol=None
    1  module=pkg operation=READY target=None symbol=None
    2  module=\x00ENTRY operation=START_IMPORT target=pkg.app symbol=None
    3  module=pkg.app operation=START_IMPORT target=pkg.decorators symbol=None
    4  module=pkg.decorators operation=DEFINE_FUNCTION target=None symbol=identity
    5  module=pkg.decorators operation=READY target=None symbol=None
    6  module=pkg operation=BIND_CHILD target=pkg.decorators symbol=decorators
    7  module=pkg.app operation=FROM target=pkg.decorators symbol=identity
    8  module=pkg.app operation=DEFINE_PASSIVE_CLASS target=None symbol=C
    9  module=pkg.app operation=CALL_FUNCTION target=None symbol=identity
    10 module=pkg.app operation=READY target=None symbol=None
    11 module=pkg operation=BIND_CHILD target=pkg.app symbol=app

Failing historical contracts and exact assertions:

- tests/test_cycle_semantics_cross_module_stack_continuation.py::test_imported_class_decorator_remains_unknown at line 483 expected UNKNOWN; actual MODEL_PASS. Its next assertion at line 484 expects events == ().
- tests/test_cycle_semantics_cross_module_single_decorator.py::test_imported_class_decorator_remains_unknown at line 541 expected UNKNOWN; actual MODEL_PASS. Its next assertion at line 542 expects events == ().
- tests/test_cycle_semantics_cross_module_decorator_baseline.py::test_indexed_cross_module_decorator_reference_and_model_boundary[E-imported-class-decorator] at line 403 expected UNKNOWN; actual MODEL_PASS. Subsequent assertions at lines 404-405 expect restricted evidence and empty events. The CPython reference assertions before line 403 passed.
- tests/test_cycle_semantics_class_decorator_baseline.py::test_imported_class_decorator_does_not_satisfy_local_compile_gate at line 712 expected UNKNOWN; actual MODEL_PASS. Subsequent assertions at lines 713-714 expect restricted evidence and empty events.

Each failure traceback reports AssertionError: expected 'UNKNOWN', actual 'MODEL_PASS'. The historical empty-event expectations conflict with the admitted imported class decorator execution in I4-R1. The task prohibits further test edits, so these contracts remain unchanged.

No full pytest or SCC02 was run. git diff --check and untracked-file whitespace checking were not run after this failed regression gate.

## MCP_POST_CHANGE_AUDIT

NOT RUN because the full targeted regression gate had four failures. The current Contextor preflight snapshot is revision 1397 with workspace_sync unverified, zero syntax diagnostics, structural DFS count 16, and cycle_semantics stale. No post-edit workspace freshness is claimed. No FULL, update_file, backend restart, or semantic refresh was performed.

## FULL_DIFFS

### Preserved I4-R1 production delta now present in HEAD

This is the complete production delta from the previous report baseline 396ebd24b7a68519113fd612bae3b8b3bbbd977c. The production file is not changed by R2.

~~~diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index e6e477c..5275c9b 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -858,7 +858,7 @@ def _compile(
                 if any(
                     not any(
-                        earlier.op == "DEFINE_FUNCTION"
+                        earlier.op in {"DEFINE_FUNCTION", "FROM"}
                         and earlier.binding == decorator_name
                         for earlier in steps
                     )
@@ -2655,10 +2655,18 @@ def evaluate_package_import_order(
                 first_name, first_object = application_order[0]
                 local_bindings: dict[str, object | None] = {}
 
+                if (
+                    not isinstance(first_object, _RestrictedFunction)
+                    or len(first_object.parameters) != 1
+                    or first_object.defining_module not in logical_sources
+                    or first_object.defining_module not in programs
+                ):
+                    return result("UNKNOWN", module, first_name)
+
                 body = _execute_restricted_object_call(
                     first_object,
                     class_fact,
-                    module=module,
+                    module=first_object.defining_module,
                     local_bindings=local_bindings,
                 )
@@ -2684,12 +2692,13 @@ def evaluate_package_import_order(
                 frames[-1] = _advance_frame(frames[-1])
                 frames.append(
                     _FunctionFrame(
-                        module=module,
+                        module=first_object.defining_module,
                         index=0,
                         steps=body,
                         local_bindings=local_bindings,
                         decorator_final_binding=step.binding,
                         remaining_decorators=application_order[1:],
+                        binding_module=module,
                     )
                 )
                 continue
~~~

### R2 baseline test diff

~~~diff
diff --git a/tests/test_cycle_semantics_cross_module_class_decorator_baseline.py b/tests/test_cycle_semantics_cross_module_class_decorator_baseline.py
index 9463636..027df01 100644
--- a/tests/test_cycle_semantics_cross_module_class_decorator_baseline.py
+++ b/tests/test_cycle_semantics_cross_module_class_decorator_baseline.py
@@ -165,8 +164,0 @@ def _reference(
-_UNKNOWN_COMPILE_REJECTION = {
-    "outcome": "UNKNOWN",
-    "target_module": "pkg.app",
-    "symbol": None,
-    "evidence_scope": "RESTRICTED_REGULAR_PACKAGE_MODEL",
-    "events": (),
-}
-
@@ -184,0 +177,12 @@ _LOCAL_IDENTITY_EVENTS = (
+def _model_expectation(
+    events, *, outcome="MODEL_PASS", target_module=None, symbol=None,
+):
+    return {
+        "outcome": outcome,
+        "target_module": target_module,
+        "symbol": symbol,
+        "evidence_scope": "RESTRICTED_REGULAR_PACKAGE_MODEL",
+        "events": events,
+    }
+
+
@@ -200 +204,14 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "identity"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "identity"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "identity"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )),
@@ -216 +233,14 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "identity"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "identity"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "alias"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )),
@@ -238 +268,18 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "decorate"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "decorate"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "decorate"),
+            ("pkg.decorators", "START_IMPORT", "pkg.effect", None),
+            ("pkg.effect", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.effect", "effect"),
+            ("pkg.decorators", "FUNCTION_LOCAL_IMPORT", "pkg.effect", "pkg"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )),
@@ -264 +311,14 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "replace"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "replace"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "replace"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )),
@@ -289 +349,11 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "factory"),
+            ("pkg.decorators", "DEFINE_OPAQUE_FUNCTION", None, "decorate"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "decorate"),
+        ), outcome="UNKNOWN", target_module="pkg.app", symbol="decorate"),
@@ -311 +381,11 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "identity"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "identity"),
+            ("pkg.app", "BIND", None, "identity"),
+        ), outcome="UNKNOWN", target_module="pkg.app", symbol="identity"),
@@ -334 +414,16 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "DEFINE_FUNCTION", None, "bottom"),
+            ("pkg.app", "START_IMPORT", "pkg.upper", None),
+            ("pkg.upper", "DEFINE_FUNCTION", None, "upper"),
+            ("pkg.upper", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.upper", "upper"),
+            ("pkg.app", "FROM", "pkg.upper", "upper"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "bottom"),
+            ("pkg.app", "CALL_FUNCTION", None, "upper"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )),
@@ -358 +453,20 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.lower", None),
+            ("pkg.lower", "DEFINE_FUNCTION", None, "lower"),
+            ("pkg.lower", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.lower", "lower"),
+            ("pkg.app", "FROM", "pkg.lower", "lower"),
+            ("pkg.app", "START_IMPORT", "pkg.upper", None),
+            ("pkg.upper", "DEFINE_FUNCTION", None, "upper"),
+            ("pkg.upper", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.upper", "upper"),
+            ("pkg.app", "FROM", "pkg.upper", "upper"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "lower"),
+            ("pkg.app", "CALL_FUNCTION", None, "upper"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )),
@@ -381 +495,15 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "identity"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "identity"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "identity"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "Child"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )),
@@ -404 +532,18 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+            ("pkg.app", "START_IMPORT", "pkg.decorators", None),
+            ("pkg.decorators", "DEFINE_FUNCTION", None, "decorate"),
+            ("pkg.decorators", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.decorators", "decorators"),
+            ("pkg.app", "FROM", "pkg.decorators", "decorate"),
+            ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
+            ("pkg.app", "CALL_FUNCTION", None, "decorate"),
+            ("pkg.decorators", "START_IMPORT", "pkg.decorators.effect", None),
+            ("pkg.decorators.effect", "READY", None, None),
+            ("pkg.decorators", "BIND_CHILD", "pkg.decorators.effect", "effect"),
+            ("pkg.decorators", "FUNCTION_LOCAL_FROM", "pkg.decorators", "effect"),
+            ("pkg.app", "READY", None, None),
+            ("pkg", "BIND_CHILD", "pkg.app", "app"),
+        )),
@@ -440 +585,5 @@ CASES = [
-        "model": _UNKNOWN_COMPILE_REJECTION,
+        "model": _model_expectation((
+            ("\x00ENTRY", "START_IMPORT", "pkg", None),
+            ("pkg", "READY", None, None),
+            ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
+        ), outcome="UNKNOWN", target_module="dataclasses"),
@@ -475 +624,12 @@ def _cpython_reference(tmp_path: Path, case: dict) -> dict:
-def _model_record(case: dict) -> dict:
+def _model_record(case: dict, *, app_suffix: str = "") -> dict:
+    model_sources = {
+        module: (
+            "pass\n"
+            if module in {"pkg.effect", "pkg.decorators.effect"}
+            and source == "__contextor_effect__ = True\n"
+            else source
+        )
+        for module, source in case["sources"].items()
+    }
+    if app_suffix:
+        model_sources["pkg.app"] += app_suffix
@@ -479 +639 @@ def _model_record(case: dict) -> dict:
-            for module, source in case["sources"].items()
+            for module, source in model_sources.items()
@@ -533,0 +694,8 @@ def test_cross_module_class_decorator_baseline(tmp_path: Path, case: dict):
+
+    if case["id"] == "D-imported-decorator-returns-none":
+        called_result = _model_record(case, app_suffix="C()\n")
+        assert called_result["outcome"] == "UNKNOWN", called_result
+        assert not any(
+            event[1] == "CALL_FUNCTION" and event[3] == "C"
+            for event in called_result["events"]
+        ), called_result
~~~

### R2 newly added admission regression test

The following is the complete content of the new file; every listed line is part of the addition.

~~~python
"""Indexed class decorator admission and unchanged semantic boundaries."""

import ast

import pytest

from contextor.core.cycle_semantics.package_model import (
    _compile,
    evaluate_package_import_order,
)


def _compile_app(source):
    return _compile(ast.parse(source), "pkg.app", False)


def _model(sources, entry="pkg.app", **options):
    return evaluate_package_import_order(
        {name: ast.parse(source) for name, source in sources.items()},
        entry,
        **options,
    )


def _calls(result):
    return tuple(
        (event.module, event.symbol)
        for event in result.events
        if event.operation == "CALL_FUNCTION"
    )


def test_a_matching_earlier_indexed_from_is_admitted():
    app = (
        "from pkg.decorators import decorate\n"
        "@decorate\nclass Product:\n    pass\n"
    )
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def decorate(cls):\n    return cls\n",
        "pkg.app": app,
    })

    assert _compile_app(app) is not None
    assert result.outcome == "MODEL_PASS"
    assert tuple(
        (event.module, event.target, event.symbol)
        for event in result.events
        if event.operation == "FROM"
    ) == (("pkg.app", "pkg.decorators", "decorate"),)
    assert _calls(result) == (("pkg.app", "decorate"),)


def test_b_imported_alias_uses_its_exact_binding_name():
    app = (
        "from pkg.decorators import decorate as alias\n"
        "@alias\nclass Product:\n    pass\n"
    )
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def decorate(cls):\n    return cls\n",
        "pkg.app": app,
    })

    assert _compile_app(app) is not None
    assert result.outcome == "MODEL_PASS"
    assert tuple(
        (event.target, event.symbol)
        for event in result.events
        if event.operation == "FROM"
    ) == (("pkg.decorators", "decorate"),)
    assert _calls(result) == (("pkg.app", "alias"),)


def test_c_from_after_class_does_not_admit_decorator():
    app = (
        "@decorate\nclass Product:\n    pass\n"
        "from pkg.decorators import decorate\n"
    )

    assert _compile_app(app) is None


def test_d_unrelated_earlier_from_does_not_admit_decorator():
    app = (
        "from pkg.other import token\n"
        "@decorate\nclass Product:\n    pass\n"
    )

    assert _compile_app(app) is None


def test_e_prior_binding_is_not_callable_proof():
    app = "decorate = None\n@decorate\nclass Product:\n    pass\n"

    assert _compile_app(app) is None


def test_f_prior_import_alone_does_not_admit_decorator():
    app = "import pkg.decorators\n@decorate\nclass Product:\n    pass\n"

    assert _compile_app(app) is None


def test_g_every_name_in_decorator_stack_needs_earlier_binding():
    app = (
        "from pkg.decorators import lower\n"
        "@upper\n@lower\nclass Product:\n    pass\n"
    )

    assert _compile_app(app) is None


def test_h_external_callable_is_not_executed():
    app = (
        "from dataclasses import dataclass\n"
        "@dataclass\nclass Product:\n    pass\n"
    )
    result = _model({"pkg.__init__": "pass\n", "pkg.app": app})

    assert _compile_app(app) is not None
    assert result.outcome == "UNKNOWN"
    assert result.target_module == "dataclasses"
    assert not _calls(result)


def test_i_none_class_decorator_result_does_not_admit_class_call():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def replace(cls):\n    return\n",
        "pkg.app": (
            "from pkg.decorators import replace\n"
            "@replace\nclass Product:\n    pass\n"
            "Product()\n"
        ),
    })

    assert result.outcome == "UNKNOWN"
    assert _calls(result) == (("pkg.app", "replace"),)
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "Product"
        for event in result.events
    )


def test_j_indexed_identity_class_fact_remains_a_supported_subclass_base():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def identity(cls):\n    return cls\n",
        "pkg.app": (
            "from pkg.decorators import identity\n"
            "@identity\nclass Product:\n    pass\n"
            "class Child(Product):\n    pass\n"
        ),
    })

    assert result.outcome == "MODEL_PASS"
    assert _calls(result) == (("pkg.app", "identity"),)
    assert tuple(
        event.symbol for event in result.events
        if event.operation == "DEFINE_PASSIVE_CLASS"
    ) == ("Product", "Child")


def test_k_same_module_class_decorator_event_contract_is_unchanged():
    result = _model({
        "pkg.__init__": (
            "def identity(cls):\n    return cls\n"
            "@identity\nclass Product:\n    pass\n"
        ),
    }, entry="pkg")

    assert result.outcome == "MODEL_PASS"
    assert tuple(
        (event.module, event.operation, event.target, event.symbol)
        for event in result.events
    ) == (
        ("\x00ENTRY", "START_IMPORT", "pkg", None),
        ("pkg", "DEFINE_FUNCTION", None, "identity"),
        ("pkg", "DEFINE_PASSIVE_CLASS", None, "Product"),
        ("pkg", "CALL_FUNCTION", None, "identity"),
        ("pkg", "READY", None, None),
    )


def test_l_imported_decorated_function_contract_is_unchanged():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def identity(fn):\n    return fn\n",
        "pkg.app": (
            "from pkg.decorators import identity\n"
            "@identity\ndef work():\n    pass\n"
        ),
    })

    assert result.outcome == "MODEL_PASS"
    assert _calls(result) == (("pkg.app", "identity"),)
    assert any(
        event.operation == "DEFINE_FUNCTION"
        and event.symbol == "work"
        for event in result.events
    )


def test_m_indexed_function_decorator_stack_contract_is_unchanged():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.lower": "def lower(fn):\n    return fn\n",
        "pkg.upper": "def upper(fn):\n    return fn\n",
        "pkg.app": (
            "from pkg.lower import lower\n"
            "from pkg.upper import upper\n"
            "@upper\n@lower\ndef work():\n    pass\n"
        ),
    })

    assert result.outcome == "MODEL_PASS"
    assert _calls(result) == (
        ("pkg.app", "lower"),
        ("pkg.app", "upper"),
    )


def test_n_conditional_frozen_dataclass_path_is_unchanged():
    result = _model(
        {
            "pkg.__init__": (
                "from dataclasses import dataclass\n"
                "@dataclass(frozen=True)\n"
                "class Record:\n    value: int\n"
            ),
        },
        entry="pkg",
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )

    assert result.outcome == "MODEL_PASS"
    assert result.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )
    assert len(result.assumed_dataclass_decorations) == 1
    assert result.assumed_dataclass_decorations[0].class_name == "Record"
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "dataclass"
        for event in result.events
    )


@pytest.mark.parametrize(
    "class_statement",
    (
        "@identity\nclass Product(MissingBase):\n    pass\n",
        "@identity\nclass Product(metaclass=MissingMeta):\n    pass\n",
    ),
    ids=("unsupported-base", "unsupported-metaclass"),
)
def test_o_unsupported_base_or_metaclass_stays_unknown(class_statement):
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def identity(cls):\n    return cls\n",
        "pkg.app": "from pkg.decorators import identity\n" + class_statement,
    })

    assert result.outcome == "UNKNOWN"
    assert not _calls(result)


def test_p_unsupported_imported_decorator_body_has_no_fabricated_calls():
    result = _model({
        "pkg.__init__": "pass\n",
        "pkg.decorators": (
            "def helper(cls):\n    return cls\n"
            "def decorate(cls):\n    return helper(cls)\n"
        ),
        "pkg.app": (
            "from pkg.decorators import decorate\n"
            "@decorate\nclass Product:\n    pass\n"
        ),
    })

    assert result.outcome == "UNKNOWN"
    assert result.target_module == "pkg.app"
    assert result.symbol == "decorate"
    assert not _calls(result)
    assert not any(
        event.operation in {"FUNCTION_LOCAL_IMPORT", "FUNCTION_LOCAL_FROM"}
        for event in result.events
    )
~~~

### R3 exact assertion correction

~~~diff
diff --git a/tests/test_cycle_semantics_class_decorator_import_admission.py b/tests/test_cycle_semantics_class_decorator_import_admission.py
--- a/tests/test_cycle_semantics_class_decorator_import_admission.py
+++ b/tests/test_cycle_semantics_class_decorator_import_admission.py
@@
-        event.operation == "DEFINE_DECORATED_FUNCTION"
+        event.operation == "DEFINE_FUNCTION"
~~~

## FINAL_VERDICT

STOP_AFTER_TARGETED_REGRESSION_FAILURE — R3's first gate passed (29 passed). The full targeted subset produced 344 passed and four historical failures, each expecting UNKNOWN and empty events for an imported identity class decorator whose actual result is MODEL_PASS with CALL_FUNCTION(identity). No additional tests or production behavior were changed; the post-change MCP audit, git diff --check, and untracked-file whitespace check were not run because the full targeted gate did not pass.
