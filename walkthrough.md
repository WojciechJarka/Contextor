# P5-M08-I10-I4-R1 — indexed class decorator admission

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP was queried first. Pre-change canonical LIVE revision 1393, provenance live. `package_model.py`, `execution/calls.py`, `execution/state.py`, and the T4-C baseline test were `workspace_sync=verified`; syntax diagnostics were clear.
- DIRECT_EVIDENCE: HEAD `396ebd24b7a68519113fd612bae3b8b3bbbd977c`. Before the authorized patch, status contained only `M walkthrough.md` from the previous blocked I4-I1 report. Active interpreter is CPython 3.15.2.
- DIRECT_EVIDENCE: T4-C 12-case baseline exists. I10-I3 continuation is present. `package_model.py` imports `_RestrictedFunction`; `_FunctionFrame` has `binding_module`.
- DIRECT_EVIDENCE: the previous I4-I1 made no source/test changes. The only production source now changed is the authorized `package_model.py` patch shown in FULL_DIFFS.
- DIRECT_EVIDENCE: exact pre-change anchors matched: compiler gate `package_model.py:848-865`; indexed FROM step `630-643`; class snapshot `2469-2496`; class fact and first decorator `2624-2698`; RETURN_FUNCTION `2709-2790`; natural completion `1788-1866`; object-call helper `execution/calls.py:86-101`.
- DIRECT_EVIDENCE: current read-only Contextor snapshot after the authorized production edit reports canonical revision 1394, provenance `live`, `canonical_state=fresh`, `workspace_sync=unverified`, syntax errors 0, structural DFS back-edge paths 16, and cycle-semantics freshness `stale`. This is not the gated post-change audit; no source freshness is claimed for revision 1394.
- DIRECT_EVIDENCE: current Git status is `M contextor/core/cycle_semantics/package_model.py` and `M walkthrough.md`; HEAD remains `396ebd24b7a68519113fd612bae3b8b3bbbd977c`.

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py` — changed; complete diff is included below.
- `walkthrough.md` — overwritten with this task report; report-only and excluded from the source/test diff requirement.
- `tests/test_cycle_semantics_cross_module_class_decorator_baseline.py` — authorized but unchanged.
- `tests/test_cycle_semantics_class_decorator_import_admission.py` — authorized but not created.
- No test file was changed or added. No pytest, `git diff --check`, or Git index/history operation occurred.

## PREVIOUS_CONTRACT_CONFLICT_RESOLUTION

The R1 production patch addresses the previous G continuation finding as specified:
- compiler admission now allows the exact earlier `FROM` binding;
- the first captured indexed decorator is admitted only when it is a one-parameter `_RestrictedFunction` whose defining module is indexed and compiled;
- the call runs in the decorator's defining module, while events and final result ownership remain in the applying module;
- the shared continuation was not changed.

A read-only direct model probe over the unchanged T4-C fixtures then exposed a separate fixture/model compilation conflict in cases C and J. The required MODEL_PASS expectations cannot be met with their unchanged indexed sources under the current restricted compiler.

## COMPILER_FROM_BINDING_ADMISSION

The requested production edit was applied at `package_model.py:861`:

```python
earlier.op in {"DEFINE_FUNCTION", "FROM"}
and earlier.binding == decorator_name
```

It keeps the earlier-step and exact-binding checks. No `BIND`, `IMPORT`, `ALIAS`, `CALL_FUNCTION`, or opaque definition was admitted.

## RUNTIME_OBJECT_ADMISSION

The initial class decorator path now checks the captured object is a one-parameter `_RestrictedFunction` whose `defining_module` is in both `logical_sources` and `programs`. It calls that exact object in its defining module. Rejection returns UNKNOWN before emitting the rejected decorator's `CALL_FUNCTION`. For accepted objects, `DEFINE_PASSIVE_CLASS` and the first `CALL_FUNCTION` remain attributed to the applying module; the frame executes in the decorator module and records the applying module as `binding_module`. No final class-name binding occurs before continuation completion.

## CLASS_FACT_IDENTITY

DIRECT_EVIDENCE: `_ClassFact` creation and `class_facts_by_identity` insertion remain before decorator application at `package_model.py:2624-2642`. The first decorator receives that same `class_fact` object. No class-fact representation changed.

## FIRST_DECORATOR_EXECUTION_MODULE

DIRECT_EVIDENCE: the patched initial call passes `module=first_object.defining_module`; its frame uses that same module. The call event is still emitted with the applying module variable. This matches CPython's defining-module globals and leaves result ownership in the class-definition module.

## SHARED_STACK_CONTINUATION

UNCHANGED. `RETURN_FUNCTION`, natural frame completion, `_FunctionFrame`, `_advance_frame`, and `_execute_restricted_object_call` were not edited. Existing continuation uses each subsequent function's defining module, attributes `CALL_FUNCTION` to `binding_module`, transports the returned object, and binds the final value in the applying module.

## APPLYING_MODULE_RESULT_BINDING

DIRECT_EVIDENCE: the initial decorator frame now sets `binding_module=module`, where `module` is the module executing the class definition. The unchanged continuation uses this field for subsequent call events and final namespace write.

## CPYTHON_PARITY_MATRIX

The CPython fixture source and reference assertions in T4-C remain unchanged. The prior T4-C targeted run recorded 253 passing tests, including all twelve `-I -B` references. No CPython subprocess was rerun in this task before the fail-closed stop.

## ALIASED_DECORATORS

Direct model probe of the unchanged T4-C cases A and B:
- A: `MODEL_PASS`; FROM exports `identity`; `CALL_FUNCTION(identity)` is attributed to `pkg.app`.
- B: `MODEL_PASS`; FROM exports `identity`; `CALL_FUNCTION(alias)` is attributed to `pkg.app`.
The exact alias-binding operation is covered by the FROM compiler anchor and will be asserted in the authorized admission tests after the fixture conflict is resolved.

## RELATIVE_IMPORT_CONTEXT

T4-C case J uses `from . import effect` inside `pkg.decorators`, with indexed effect source `pkg.decorators.effect` and a contrasting `pkg.effect`. The direct model probe returned UNKNOWN before any events, target_module `pkg.decorators.effect`; see the specific source rejection below. CPython's preserved reference expects the defining-package effect `pkg.decorators.effect`.

## INTERMEDIATE_NONE

Direct model probe of T4-C case D: `MODEL_PASS`, with `FROM(replace)`, `DEFINE_PASSIVE_CLASS(C)`, then `CALL_FUNCTION(replace)`. The preserved CPython reference says final `C` is None. The separate model-only `C()` regression was not added because execution stopped at the C/J fixture conflict.

## SUBCLASS_IDENTITY

Direct model probe of T4-C case I: `MODEL_PASS`; events include `DEFINE_PASSIVE_CLASS(C)`, `CALL_FUNCTION(identity)`, then `DEFINE_PASSIVE_CLASS(Child)`. The same returned class fact is used as Child's base. No class-fact semantics changed.

## EXTERNAL_AND_OPAQUE_BOUNDARIES

- E remains UNKNOWN at `pkg.app`, symbol `decorate`; its full events include the indexed FROM and function definitions, with no `CALL_FUNCTION` for `decorate` or `factory`.
- F remains UNKNOWN at `pkg.app`, symbol `identity`; full events include indexed FROM and the subsequent BIND to None, with no decorator call.
- L remains UNKNOWN at `dataclasses`; full observed events stop at the app import start and contain no external `CALL_FUNCTION(dataclass)`.
- Direct probe outcomes for the other T4-C cases were A/B/D/G/H/I/K MODEL_PASS; E/F/L UNKNOWN. Cases C and J are the only mismatches to the requested new baseline expectations.

## BLOCKING_CONTRACT_MISMATCH_C_AND_J

DIRECT_EVIDENCE — unchanged T4-C fixtures and model input path:
- Case C indexes `pkg.effect` with source `__contextor_effect__ = True` (test line 227).
- Case J indexes both `pkg.decorators.effect` and the contrasting `pkg.effect` with the same dunder marker (test lines 392-393).
- `_model_record` at test lines 475-485 constructs the evaluator input by parsing each exact `case["sources"]` string and passes that mapping directly to `evaluate_package_import_order`; there is no separate model-only source mapping or marker normalization.

DIRECT_EVIDENCE — `package_model.py:713-742`:
- Assignment targets beginning with `__` are rejected unless they are the existing `__all__` or `__version__` cases.
- Direct `_compile(ast.parse("__contextor_effect__ = True"), "pkg.effect", False)` returned `None`.
- The evaluator returns `UNKNOWN` for a module whose compile result is None at `package_model.py:1615-1616`.

Observed complete model records from the direct probe after the authorized production patch:

```text
C: outcome=UNKNOWN
   target_module="pkg.effect"
   symbol=None
   evidence_scope="RESTRICTED_REGULAR_PACKAGE_MODEL"
   events=()

J: outcome=UNKNOWN
   target_module="pkg.decorators.effect"
   symbol=None
   evidence_scope="RESTRICTED_REGULAR_PACKAGE_MODEL"
   events=()
```

These outcomes occur before the app's FROM or class decorator steps execute. They conflict with the required C/J MODEL_PASS contracts and required effect-import events. Changing the indexed effect-module inputs would alter the preserved fixtures; admitting the marker assignment would expand compiler grammar, which this task prohibits. No test expectation was changed to conceal the mismatch.

## FIRST_GATE_RESULTS

NOT RUN. Cases C and J already violate their required model contracts under a direct read-only evaluator probe; creating the expected-pass tests and running the gate would knowingly produce a contract failure.

## TARGETED_REGRESSION_RESULTS

NOT RUN. Stopped before test changes under fail-closed semantic integrity. No pytest command, `git diff --check`, or MCP post-change audit was run.

## MCP_POST_CHANGE_AUDIT

The required post-change audit was not run because the test gates did not pass. The separate read-only preflight snapshot now available reports LIVE revision 1394, `workspace_sync=unverified`, syntax diagnostics fresh with zero errors, structural DFS count 16, and cycle-semantics freshness stale. Pre-change LIVE revision was 1393 and the authorized source anchors were verified before editing. No semantic refresh, FULL, `update_file`, or backend restart was performed.

## FULL_DIFFS

Complete current production diff:

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

No test diff exists. `walkthrough.md` is the report-only file.

## FINAL_VERDICT

BLOCKED_SEMANTIC_INTEGRITY — cases C and J require MODEL_PASS with effect imports, but their preserved model input includes a dunder marker assignment rejected by the existing compiler. The task simultaneously prohibits fixture changes and grammar expansion. Corrected instructions are needed to specify how the model input should represent these CPython-only observation markers while preserving the CPython fixtures.
