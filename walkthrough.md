# P5-M08-I10-D1 — external decorator knowledge boundary

## PREFLIGHT

DIRECT_EVIDENCE:

- HEAD before report replacement: 1b97e60545aa6f602a78e9b7623e265932d1535a.
- git status --short was empty before report replacement. No source or test edits were present.
- Contextor MCP get_module_context for contextor/core/cycle_semantics/package_model.py answered from canonical LIVE revision 1366. canonical_state=fresh, workspace_sync=verified, provenance=live. The cycle_semantics family was marked stale; module, graph, topology, artifact_consumption, cycles, collisions and lineage were marked fresh. No semantic refresh was requested or run.
- Earlier same-revision MCP reads for execution.calls and execution.imports also reported workspace_sync=verified.
- Active interpreter: C:\Temp\Contextor_Repo\.venv\Scripts\python.exe, CPython 3.15.2 (64-bit Windows).
- The current HEAD contains the I9-I2 and I9-T2 artifacts: class decorator staging includes test_same_name_decorator_stages_and_executes and test_class_decorator_identity_counterexamples.py is present. The relevant production branches are present in package_model.py.
- No backend restart, FULL, SCC02, update_file, semantic refresh, pytest, Git index operation or Git history operation was performed.

Actions/evidence:

- Contextor MCP documentation for get_module_context was read before the freshness query.
- Literal source and test reads followed the MCP check.
- All synthetic CPython module files were created in temporary directories outside the repository and run in fresh processes with -I -B.
- The first synthetic-process setup omitted the temporary root from the isolated child's sys.path and produced ModuleNotFoundError for pkg. That attempt is setup-only and contributes no semantic result. The probe was corrected by inserting the provided temporary root into sys.path; the five corrected cases all completed and their evidence is reported below.

## CURRENT_DECORATOR_ADMISSION_BOUNDARY

CODE_PATH_PROVED:

- Function admission is in contextor/core/cycle_semantics/package_model.py:144-242. The validator rejects invalid or dunder names by default, unsupported annotations/type parameters/type comments and nonliteral defaults. A decorator list is admitted only when allow_restricted_decorator=True and every decorator expression is exactly ast.Name with a non-dunder identifier; the separate builtin-property exception is a single exact property name for a FunctionDef.
- Class admission is in package_model.py:244-488. Ordinary class decorators are admitted only when allow_named_decorators=True and every decorator is exactly ast.Name with a non-dunder identifier. Attribute expressions and calls are rejected. Bases must be ast.Name expressions; only the one explicit keyword metaclass=<Name> form is admitted. Class bodies are restricted to pass, imports, safe annotation assignments, pure-literal assignments, an initial literal docstring, and admitted safe method definitions. Reserved class-creation method names are rejected. Unsupported class-body statements reject the definition.
- The ordinary named class decorator path in package_model.py:819-1033 additionally requires each decorator name to have an earlier DEFINE_FUNCTION step. It emits SNAPSHOT_CLASS_DECORATORS before PREPARE_PASSIVE_CLASS and the class-body steps, then emits DEFINE_DECORATED_PASSIVE_CLASS after the body. The conditional frozen dataclass path is selected separately and emits DEFINE_CONDITIONAL_FROZEN_DATACLASS; it does not use ordinary named decorator snapshots.
- FunctionDef compilation is in package_model.py:1035-1186. A restricted decorated function emits DEFINE_DECORATED_FUNCTION for one simple-name decorator or DEFINE_STACKED_FUNCTION for multiple names. A decorator factory expression such as lru_cache(maxsize=8) is an ast.Call, not ast.Name, so it fails this restricted compilation path before model execution.
- There is no lru_cache or functools-specific branch in package_model.py or contextor/core/cycle_semantics/execution. The literal production-source search returned no matches for either token. There is no decorator-name allowlist.
- Bare @lru_cache is syntactically a simple Name, but name syntax does not establish a trusted callable. In the normal package model, from functools import lru_cache reaches the unsupported external FROM boundary before the decorator can be applied. The optional passive-external-import assumption is an explicit conditional mode and is not runtime proof; with that assumption the decorated factory form still becomes UNKNOWN at the unmodeled FunctionDef.

INFERENCE:

- Under the current narrow grammar, simple-name syntax is an admission shape only. It does not establish object provenance, purity, absence of side effects, or identity with the object originally imported under that name.

## EXTERNAL_IMPORT_PROVENANCE

CODE_PATH_PROVED:

- Import compilation resolves the target/member and stores the source alias as the step binding in package_model.py:501-625. At execution, _execute_from_binding in contextor/core/cycle_semantics/execution/imports.py:206-258 reads the actual indexed namespace value and assigns that same value to namespaces[module][step.binding]. Thus an indexed from-import alias preserves the modeled object reference; the FROM event records the imported member and target module.
- _classify_external_import in execution/imports.py:261-294 returns UNKNOWN_UNMODELED for an ordinary external import. It returns ASSUME only when passive external imports are explicitly enabled for compile-on-first-import, the target is not indexed, and the import is not class-local. The assumption is recorded as an assumed import and represented by a conditional sentinel, not by execution or inspection of an external callable.
- _RestrictedFunction is a frozen identity-based record containing defining_module, body and parameters (execution/calls.py:8-18). _execute_restricted_call (calls.py:59-83) and _execute_restricted_object_call (calls.py:86-101) require that the captured value be a _RestrictedFunction defined by the currently executing module. The object-call form also requires exactly one parameter. A valid indexed function imported from another module therefore retains its identity but does not satisfy the same-module execution predicate when used as a decorator in the importer.
- _snapshot_named_decorators (calls.py:21-44) copies ordered names and exact namespace values into frozen _DecoratorSnapshot (calls.py:8-18). Stacked function execution snapshots before application at package_model.py:2154-2163; class decorator names are snapshotted by the earlier SNAPSHOT_CLASS_DECORATORS operation at package_model.py:2400-2428. A single decorated function uses its target name in DEFINE_DECORATED_FUNCTION at package_model.py:2217-2274 and resolves that current namespace value at application. The snapshot mechanism is not a claim that every decorator route uses a snapshot.

DIRECT_EVIDENCE:

- Normal imports from functools are not treated as passive. The existing D02 test explicitly uses the opt-in conditional external-import assumption and still expects UNKNOWN for the lru_cache factory expression.
- No external installed package was executed by these probes. The external decorator cases below use only locally authored synthetic modules.

## EXISTING_D02_REGRESSIONS

The bounded inventory covered decorator-named tests and test_cycle_semantics_package_model.py. Relevant current test contracts:

| File and test | Current expectation/evidence |
| --- | --- |
| tests/test_cycle_semantics_decorator_definition_effects.py::test_d02_lru_cache_is_not_passive_runtime_proof | Conditional model outcome UNKNOWN; final conditional event is UNMODELED_STATEMENT for FunctionDef at 2:1; explicitly rejects CONDITIONAL_MODEL_PASS. CPython import/call succeeds. |
| tests/test_cycle_semantics_decorator_definition_effects.py::test_d03_d05_decorator_import_entry_dependency | Local restricted function/class decorators that import pkg.b produce EARLY_BINDING_HAZARD when importing the partial export, and MODEL_PASS when importing pkg.b. Decorator-factory and class-body method-decorator cases expect UNKNOWN. |
| tests/test_cycle_semantics_decorator_definition_effects.py::test_decorator_expression_and_application_order | CPython confirms expression evaluation top-to-bottom and application bottom-to-top for factory expressions; model expectation is UNKNOWN. |
| tests/test_cycle_semantics_decorator_definition_effects.py::test_decorator_can_replace_definition_binding | CPython source returns 42; model expects UNKNOWN for both function and class replacement. |
| tests/test_cycle_semantics_decorator_definition_effects.py::test_nested_method_decorator_remains_unmodeled | UNKNOWN for a decorated method nested in a class. |
| tests/test_cycle_semantics_decorator_import_effect_baseline.py::test_minimal_decorator_import_effects | Parameterized local restricted cases cover deferred function bodies, imports during decorator application, stacked decorator import order, and a class-body import preceding decorator application. Expected outcomes are MODEL_PASS except class-body-before-decorator, which expects UNKNOWN. |
| tests/test_cycle_semantics_class_decorator_baseline.py::test_class_decorator_definition_time_baseline | Cases cover pass-through, decorator import, class-body-before-application ordering, stack ordering, same-name decorator, None return, and early class-name import hazard. Expected outcomes include MODEL_PASS for supported local decorators and EARLY_BINDING_HAZARD for the cyclic child case. |
| tests/test_cycle_semantics_class_decorator_staging.py::test_same_name_decorator_stages_and_executes | Historical I9-I1 expectation is corrected: compilation emits the named snapshot and model outcome is MODEL_PASS with CALL_FUNCTION C. The same file keeps attribute/call decorator forms UNKNOWN and checks conditional frozen dataclass staging separately. Its module docstring still says execution remains unknown; that wording is stale relative to the current test assertion and was not edited. |
| tests/test_cycle_semantics_class_decorator_identity_counterexamples.py::test_class_decorator_identity_counterexamples | Cases cover rebinding before snapshot (UNKNOWN; CPython TypeError), same-name and duplicate references (MODEL_PASS), class-local shadowing, post-decoration rebinding, and a noncallable stack member (UNKNOWN; CPython TypeError). |
| tests/test_cycle_semantics_stacked_decorator_identity.py::test_stacked_decorator_cpython_and_current_boundary | Includes a decorator binding replaced after decorator-expression evaluation; CPython imports pkg.bottom then pkg.top, while the model expects UNKNOWN. |
| tests/test_cycle_semantics_stacked_decorator_execution.py::test_stacked_decorator_execution | Cases include bottom-up order, intermediate None, global rebinding, and final None called; the last expects UNKNOWN after CPython TypeError. |
| tests/test_cycle_semantics_decorator_snapshots.py | Unit regressions assert source-order snapshots preserve object identity, repeated references, None values and values after namespace rebinding. |
| tests/test_cycle_semantics_package_model.py::test_external_assumption_normal_model_still_unknown | Normal external import remains UNKNOWN with no assumptions recorded. |
| tests/test_cycle_semantics_package_model.py::test_external_assumption_refused_without_lazy_compilation | Assumption alone, without compile-on-first-import, does not admit the external import. |
| tests/test_cycle_semantics_package_model.py::test_external_assumption_direct_conditional_scope | The explicit conditional import case can MODEL_PASS, with evidence_scope CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_ASSUMPTION_NOT_RUNTIME_PROOF and the import listed as assumed. |
| tests/test_cycle_semantics_package_model.py::test_external_assumption_does_not_skip_indexed_import | An indexed child remains modeled under the conditional setting and does not become an assumed external import. |
| tests/test_cycle_semantics_package_model.py::test_external_assumption_called_local_import_keeps_location | Explicit conditional import assumptions for a called restricted local function retain importer, operation, target and source location. |
| tests/test_cycle_semantics_package_model.py::test_external_assumption_uncalled_function_has_no_record | An uncalled function's external import has no reached-assumption record. |

No dedicated regression for applying a decorator imported as an alias from a different indexed module was found in this bounded inventory. The indexed cross-module observation below exercises that boundary without changing tests.

## CPYTHON_LRU_CACHE_MATRIX

Method: each A-G source was executed in a separate fresh process using the active CPython 3.15.2 interpreter with -I -B. A tracing import wrapper recorded the source-level import name/fromlist. A trace hook recorded executions of f's body without altering the source fixtures.

| Case | Definition/result | Final f and identity | Body execution | Source import observation |
| --- | --- | --- | --- | --- |
| A, from functools import lru_cache; @lru_cache | Successful | functools._lru_cache_wrapper, callable; __wrapped__ is the original builtins.function; f is not that original function; wrapper created | None at definition; no call was made | functools, fromlist [lru_cache] |
| B, @lru_cache(maxsize=8) | Successful | Same wrapper type and identity relationship as A | None at definition; no call was made | functools, fromlist [lru_cache] |
| C, import functools; @functools.lru_cache | Successful | Same wrapper type and identity relationship as A | None at definition; no call was made | functools, empty fromlist |
| D, from functools import lru_cache as cache; @cache | Successful | Same wrapper type and identity relationship as A | None at definition; no call was made | functools, fromlist [lru_cache] |
| E, rebind lru_cache to lambda fn: None; @lru_cache | Successful; no exception | f is None and noncallable; no wrapper | None at definition; no call was made | functools, fromlist [lru_cache] |
| F, rebind lru_cache to None; @lru_cache | TypeError: 'NoneType' object is not callable; f is not bound | No final f and no wrapper | None | functools, fromlist [lru_cache] |
| G, A followed by f(1) | Successful | Same wrapper type; __wrapped__ remains the original function and f is not it | No execution at definition; the body executed once on f(1), with the trace observing the return-x line | functools, fromlist [lru_cache] |

Each child returned process code 0 because the probe caught and reported the expected F exception. Every successful A-D/G wrapper had wrapped_present=true and wrapped_type=builtins.function. These observations are specific to CPython 3.15.2 and the exact listed sources; wrapper creation does not establish general decorator safety.

## WRAPPER_OBJECT_IDENTITY

DIRECT_EVIDENCE:

- A-D and G end with an object whose runtime type is functools._lru_cache_wrapper. Its __wrapped__ attribute refers to a builtins.function, and the wrapper is not that function by identity.
- E demonstrates that a binding with the imported spelling lru_cache can be replaced before decorator application; the replacement's returned None becomes f.
- F demonstrates the same rebinding to a noncallable value and the exact CPython TypeError.

CODE_PATH_PROVED:

- The current restricted decorator return vocabulary can produce the original restricted argument or None through RETURN_FUNCTION/natural frame completion. It does not construct a functools wrapper. Arbitrary return expressions and external callable execution are outside the restricted path and terminate conservatively as UNKNOWN.

INFERENCE:

- Import spelling/provenance by itself is insufficient to establish that a name still refers to the imported callable or that its application preserves the input identity.

## DECORATOR_FACTORY_BOUNDARY

CODE_PATH_PROVED:

- A decorator factory expression is an ast.Call and is rejected by the simple ast.Name decorator grammar. The compiler does not evaluate arbitrary decorator expressions.
- The single-name restricted function/class decorator paths accept only a same-module _RestrictedFunction with the required argument count. Stacked paths first snapshot exact name/value pairs, then apply in reverse source order.
- A supported local decorator body may import indexed package modules; those imports and the resulting package events are modeled. This does not admit executing an arbitrary imported callable.

DIRECT_EVIDENCE:

- Existing test_decorator_expression_and_application_order and the lru_cache factory probe both distinguish syntax that invokes a factory from a simple name decorator. The former's CPython source succeeds while the model intentionally returns UNKNOWN; the current lru_cache factory model observation below likewise returns UNKNOWN.

## SYNTHETIC_EXTERNAL_EFFECT_MATRIX

Method: each row used an isolated CPython process importing a temporary synthetic package. pkg.__init__ recorded package/import order, then imported pkg.decorators, defined class C with a class-body trace entry, and applied the external module's deco. All cases record whether C already existed in pkg during application. For D the external decorator assigned pkg.C = 'early-binding'. The process also retained the exact class object passed to the decorator for identity comparison.

Common import-trace prefix for all cases:

    import:pkg.decorators:from=deco
    import:_io:from=
    import:_io:from=
    import:builtins:from=
    import:sys:from=

| Case | Ordered execution/effects after import prefix | Final binding or exception |
| --- | --- | --- |
| A, return original | package-start; before-class; class-body; apply:start; binding-C-before=False; apply:return-original; after-class | Successful; pkg.C is class pkg.C and is the exact object passed to deco. |
| B, return None | package-start; before-class; class-body; apply:start; binding-C-before=False; apply:return-None; after-class | Successful; pkg.C is None. |
| C, import pkg.effect | package-start; before-class; class-body; apply:start; binding-C-before=False; import:pkg.effect:from=; import:_io:from= twice; import:builtins:from=; effect-module-body; apply:return-original; after-class | Successful; pkg.C is the exact object passed to deco. The package effect import occurs during application and before final class-name binding. |
| D, alter package global | package-start; before-class; class-body; apply:start; binding-C-before=False; binding-C-during='early-binding'; apply:return-original; after-class | Successful; final pkg.C is again the exact passed class object, after the decorator's early assignment was overwritten by the class statement's final binding. |
| E, raise | package-start; before-class; class-body; apply:start; binding-C-before=False; apply:raise | Import raises RuntimeError: synthetic decorator failure. pkg was removed from sys.modules after the failed import; no final C binding was produced. |

DIRECT_EVIDENCE:

- For all five probes, class-body execution precedes decorator application. The class name is not present in pkg during application. The statement's final name assignment happens only after successful decorator return.
- External module imports and global mutation can occur during application; an exception can escape from application. These are CPython results from synthetic fixtures, not model admissions.

## MODEL_OBSERVATIONS

All observations used evaluate_package_import_order on parsed indexed sources. No external callable was executed by Contextor. Complete relevant event sequences are listed in order; each event is module:operation(target, symbol), with omitted target/symbol shown as —. ENTRY is a readable report label for the evaluator's internal bootstrap module identifier.

| Indexed input | Outcome and evidence_scope | Relevant complete events / assumptions |
| --- | --- | --- |
| Local same-module identity decorator on function | MODEL_PASS; RESTRICTED_REGULAR_PACKAGE_MODEL | ENTRY:START_IMPORT(pkg, —); pkg:READY(—, —); ENTRY:START_IMPORT(pkg.app, —); pkg.app:DEFINE_FUNCTION(—, deco); pkg.app:DEFINE_FUNCTION(—, f); pkg.app:CALL_FUNCTION(—, deco); pkg.app:READY(—, —); pkg:BIND_CHILD(pkg.app, app). |
| Bare from functools import lru_cache; @lru_cache def f | UNKNOWN; RESTRICTED_REGULAR_PACKAGE_MODEL | ENTRY:START_IMPORT(pkg, —); pkg:READY(—, —); ENTRY:START_IMPORT(pkg.app, —). reached_unmodeled_import: importer pkg.app, FROM functools member lru_cache at 1:0. No decorator call occurs. |
| lru_cache factory expression | UNKNOWN; RESTRICTED_REGULAR_PACKAGE_MODEL | No events; the whole module's restricted compilation fails before execution. |
| Indexed pkg.decorators function imported into pkg.app and used as @deco | UNKNOWN; RESTRICTED_REGULAR_PACKAGE_MODEL | ENTRY:START_IMPORT(pkg, —); pkg:READY(—, —); ENTRY:START_IMPORT(pkg.app, —); pkg.app:START_IMPORT(pkg.decorators, —); pkg.decorators:DEFINE_FUNCTION(—, deco); pkg.decorators:READY(—, —); pkg:BIND_CHILD(pkg.decorators, decorators); pkg.app:FROM(pkg.decorators, deco). The imported value is a foreign-module _RestrictedFunction; same-module object-call validation fails before CALL_FUNCTION. |
| Same indexed cross-module decorator whose body would import pkg.effect | UNKNOWN; RESTRICTED_REGULAR_PACKAGE_MODEL | Same complete events as the preceding row, ending at pkg.app:FROM(pkg.decorators, deco). The decorator body and its pkg.effect import are not executed or reported. |
| lru_cache factory form with _compile_on_first_import=True and _assume_passive_external_imports=True | UNKNOWN; CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_ASSUMPTION_NOT_RUNTIME_PROOF | ENTRY:START_IMPORT(pkg, —); pkg:READY(—, —); ENTRY:START_IMPORT(pkg.app, —); pkg.app:ASSUMED_EXTERNAL_IMPORT(functools, lru_cache); pkg.app:UNMODELED_STATEMENT(FunctionDef, 2:1). assumed_external_imports contains the FROM functools lru_cache row at 1:0. |
| Local class decorator imports indexed pkg.effect and returns its input | MODEL_PASS; RESTRICTED_REGULAR_PACKAGE_MODEL | ENTRY:START_IMPORT(pkg, —); pkg:READY(—, —); ENTRY:START_IMPORT(pkg.app, —); pkg.app:DEFINE_FUNCTION(—, deco); pkg.app:DEFINE_PASSIVE_CLASS(—, C); pkg.app:CALL_FUNCTION(—, deco); pkg.app:START_IMPORT(pkg.effect, —); pkg.effect:READY(—, —); pkg:BIND_CHILD(pkg.effect, effect); pkg.app:FUNCTION_LOCAL_IMPORT(pkg.effect, pkg); pkg.app:READY(—, —); pkg:BIND_CHILD(pkg.app, app). |
| Local class decorator returns None, then C() is evaluated | UNKNOWN; RESTRICTED_REGULAR_PACKAGE_MODEL | Through application: ENTRY:START_IMPORT(pkg, —); pkg:READY(—, —); ENTRY:START_IMPORT(pkg.app, —); pkg.app:DEFINE_FUNCTION(—, deco); pkg.app:DEFINE_PASSIVE_CLASS(—, C); pkg.app:CALL_FUNCTION(—, deco). The subsequent call is UNKNOWN for symbol C, consistent with the modeled final namespace value None. |

No row treats UNKNOWN as a runtime mismatch. No model observation changes or expands the current admission boundary.

## MODEL_PASS_SAFETY_PRECONDITIONS

CODE_PATH_PROVED:

- Current ordinary MODEL_PASS for decorator examples is limited to the restricted grammar, modeled same-module callable identity, supported one-argument call shape, restricted body operations/return values, and indexed imports whose initialization can be modeled.
- The conditional external import mode has a distinct evidence_scope explicitly labeled NOT_RUNTIME_PROOF. A conditional assumption can record an external import, but it neither executes nor validates an external decorator.
- Class creation facts use frozen _ClassFact values keyed by definition_id in class_facts_by_identity before decorator application. The decorated class name is bound in the module namespace only after the final decorator frame completes. A None return may replace that namespace binding without deleting the separately keyed class fact.

CONTRACT_PROVED:

- The D1 request is read-only discovery, not implementation. Its required distinction is supported by the source contracts and CPython reference probes above: restricted local decoration can be modeled; external callable behavior is not thereby known.

INFERENCE:

- A general safety claim for an external decorator would need evidence about the exact callable object selected at application time, its implementation or independently documented semantics, its effects/imports, possible exceptions, and the value/identity it returns. Decorator-factory expression evaluation and alias/rebinding would also need evidence. The current external-import assumption supplies none of those callable semantics. This is a statement of missing knowledge, not an implementation design.

## UNRESOLVED_SEMANTIC_REQUIREMENTS

UNKNOWN:

- The behavior of arbitrary installed external decorators, including their body effects, import behavior, exception behavior, wrapper identity, and return object, is not inferred from their import spelling.
- No installed third-party decorator was run or examined.
- The probes establish the listed CPython 3.15.2 behavior only. They do not establish a general guarantee for standard-library or external decorators.
- Contextor's canonical cycle_semantics family was stale at revision 1366. This task performed no semantic refresh; the source/model observations here are tied to the checked-out source and recorded MCP freshness, not a claim that LIVE semantic facts were recomputed.

## RELEVANT_SOURCE_ANCHORS

- contextor/core/cycle_semantics/package_model.py:144-242 — restricted function admission and decorator expression grammar.
- contextor/core/cycle_semantics/package_model.py:244-488 — passive class body, bases/metaclass and ordinary-vs-conditional decorator admission.
- contextor/core/cycle_semantics/package_model.py:501-625 — import and from-import target/binding compilation.
- contextor/core/cycle_semantics/package_model.py:819-1033 — class validation, prior local decorator definition check, snapshot, class preparation, class body imports and final definition operation.
- contextor/core/cycle_semantics/package_model.py:1035-1186 — function definition restrictions, supported return steps and decorated function operations.
- contextor/core/cycle_semantics/package_model.py:1350-1425 — evaluator contract, evidence_scope and opt-in conditional assumptions.
- contextor/core/cycle_semantics/package_model.py:1792-1844 — natural function-frame completion; None transport and deferred final decorated-name binding.
- contextor/core/cycle_semantics/package_model.py:2146-2274 — stacked and single decorated function execution.
- contextor/core/cycle_semantics/package_model.py:2400-2428 — class decorator snapshot.
- contextor/core/cycle_semantics/package_model.py:2440-2510 — prepared bases and metaclass candidate validation.
- contextor/core/cycle_semantics/package_model.py:2513-2635 — class fact construction/identity map, decorator application and final namespace path.
- contextor/core/cycle_semantics/package_model.py:2640-2704 — explicit function return transport through remaining decorators.
- contextor/core/cycle_semantics/execution/calls.py:8-101 — identity-based restricted function/snapshot records and same-module call checks.
- contextor/core/cycle_semantics/execution/imports.py:206-294 — imported object binding and conditional external-import classification.
- contextor/core/cycle_semantics/execution/state.py:32-90, 96-114 — function continuation fields, frame advancement, 10000-step budget and definition-time identity maps.
- contextor/core/cycle_semantics/execution/class_facts.py:7-18 — frozen _ClassFact identity and class provenance fields.
- tests/test_cycle_semantics_decorator_definition_effects.py:61-84, 157-217, 219-287 — D02, decorator import entry, factory ordering and replacement regressions.
- tests/test_cycle_semantics_class_decorator_staging.py:75-90, 92-106, 108-143 — same-name execution, unsupported expression forms and separate conditional dataclass coverage.
- tests/test_cycle_semantics_class_decorator_identity_counterexamples.py:15-60 — pre-snapshot rebinding, identity, repeated reference, class-local shadowing, post-decoration rebinding and noncallable stack cases.
- tests/test_cycle_semantics_package_model.py:1201-1288 — normal and conditional external-import assumption regressions.

## FILES_CHANGED

- No production source, test or documentation file was changed.
- walkthrough.md was replaced with this task report as required by the repository workflow. Report-only walkthrough changes are excluded from the source/test changed-file inventory.

## ACTUAL_DIFF

Source/test/docs diff: NONE.

git diff --check: PASS after report write.

## FINAL_VERDICT

READ-ONLY DISCOVERY COMPLETE. CPython 3.15.2 probes A-G and synthetic external-effect probes A-E completed after correcting the isolated subprocess path setup. Current model observations and bounded regression inventory are recorded above. No pytest was necessary or run. No implementation or test admission was made. STOP AFTER DISCOVERY.
