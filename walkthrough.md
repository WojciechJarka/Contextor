# P5-M08-I10-T1 — indexed cross-module decorator baseline

## PREFLIGHT

DIRECT_EVIDENCE:

- HEAD at preflight: acf0e9b5ff112b849239cb51d08642d0924bf5b3. git status --short was empty before this task; tests/test_cycle_semantics_cross_module_decorator_baseline.py did not exist.
- Active interpreter: C:\Temp\Contextor_Repo\.venv\Scripts\python.exe, CPython 3.15.2 (64-bit Windows).
- Contextor MCP was queried first. package_model.py, execution/calls.py and execution/imports.py answered from canonical LIVE revision 1366 with canonical_state=fresh and workspace_sync=verified. cycle_semantics was stale; no semantic refresh was run.
- Source verification confirmed _RestrictedFunction retains defining_module; indexed FROM preserves the same modeled object reference; _execute_restricted_object_call requires same-module callable provenance; ordinary named class decorators require a preceding local DEFINE_FUNCTION compile step.
- The authorized target did not exist at preflight. No production source, existing test, backend, Git index or Git history changes were made.

## FILES_CHANGED

- tests/test_cycle_semantics_cross_module_decorator_baseline.py — new authorized test file.
- walkthrough.md — task report, report-only and excluded from source/test diff inventory.

## CROSS_MODULE_CALLABLE_PROVENANCE

CODE_PATH_PROVED:

- contextor/core/cycle_semantics/execution/calls.py:9-12 defines frozen identity-based _RestrictedFunction values containing defining_module, body and parameters.
- execution/imports.py:206-258 resolves an indexed FROM member from the target module namespace and assigns that same object reference to the importer's binding. The direct test observes namespaces[pkg.app][alias] is identity after _execute_from_binding.
- execution/calls.py:86-101 rejects _execute_restricted_object_call unless the value is a _RestrictedFunction whose defining_module equals the current module and whose parameter count is one. The imported identity remains available by object identity, but the same-module call guard refuses to execute it from pkg.app.
- package_model.py:847-865 requires each ordinary class decorator name to match an earlier DEFINE_FUNCTION step. An imported name emitted by FROM does not satisfy that compiler predicate.
- package_model.py:1035-1148 restricts decorated function bodies to pass, return-without-value, returning the sole parameter, and supported imports. The final decorated-function check returns None from compilation when another body statement occurs; this accounts for the empty event tuples for A-D's return 1 fixtures.
- The focused test also evaluates an import-only indexed package shape: the evaluator returns MODEL_PASS and emits FROM for pkg.decorators.identity. That proves modeled import availability for that shape; it does not permit using the imported callable as a cross-module decorator.

INFERENCE:

- A FROM event and retained callable identity are evidence of import/binding, not evidence that the restricted evaluator has permission or semantics to invoke the callable in another module.

## CPYTHON_REFERENCE_MATRIX

Each required case ran in a fresh isolated CPython 3.15.2 subprocess using -I -B and temporary package sources. The decorator fixtures remain literal to the specification. A trace hook observes the decorator call arguments without changing those sources. The runner records relevant imports, call count after importing pkg.app, final binding type/identity, and function behavior or class callability.

| Case | CPython result | Import order | Definition-time decoration | Final binding and identity |
| --- | --- | --- | --- | --- |
| A, imported identity function decorator | Import succeeds; f() returns 1 | pkg.decorators | identity called once before f() is invoked | f is builtins.function and is the exact object passed to identity |
| B, imported decorator imports pkg.effect | Import succeeds; f() returns 1 | pkg.decorators, pkg.effect | apply_decorator called once; pkg.effect is imported during its application | f is builtins.function and is the exact object passed to apply_decorator |
| C, imported identity alias | Import succeeds; f() returns 1 | pkg.decorators | identity called once before f() is invoked | app.alias is the exact imported decorators.identity callable; final f is the exact object passed to identity |
| D, imported decorator returns None | Import succeeds | pkg.decorators | replace called once | f is builtins.NoneType, noncallable, and not the object passed to replace |
| E, imported class decorator | Import succeeds; C() creates pkg.app.C | pkg.decorators | identity called once during class definition | C is builtins.type, callable, and the exact class object passed to identity |

For every case CPython error=null, decorator_calls_at_definition=1, and binding_is_imported_export=true. Case B's pkg.effect import is observed after pkg.decorators loads and during decorator application.

## INDEXED_FROM_IMPORT_IDENTITY

DIRECT_EVIDENCE:

- The helper test creates an identity-based _RestrictedFunction owned by pkg.decorators, passes it through _execute_from_binding under alias, and asserts the importer binding is the same object by is.
- The test then calls _execute_restricted_object_call with current module pkg.app and asserts the result is None. The callable's defining_module remains pkg.decorators.
- An evaluator import-only control returns MODEL_PASS with evidence_scope RESTRICTED_REGULAR_PACKAGE_MODEL and a FROM event for pkg.app importing identity from pkg.decorators.

Complete import-only evaluator events, in order (ENTRY is a readable label for the internal bootstrap module identifier):

    ENTRY:START_IMPORT(target=pkg)
    pkg:READY
    ENTRY:START_IMPORT(target=pkg.app)
    pkg.app:START_IMPORT(target=pkg.decorators)
    pkg.decorators:DEFINE_FUNCTION(symbol=identity)
    pkg.decorators:READY
    pkg:BIND_CHILD(target=pkg.decorators, symbol=decorators)
    pkg.app:FROM(target=pkg.decorators, symbol=identity)
    pkg.app:READY
    pkg:BIND_CHILD(target=pkg.app, symbol=app)

## DECORATOR_APPLICATION_EFFECTS

DIRECT_EVIDENCE:

- CPython case B imports pkg.decorators then pkg.effect. The synthetic decorator imports pkg.effect inside apply_decorator, after module definition and while the decorator is running.
- For the exact required case B source, the current model outcome is UNKNOWN with evidence_scope RESTRICTED_REGULAR_PACKAGE_MODEL and no events. The decorated f body contains return 1, outside the restricted decorated-function body vocabulary; compilation returns no program before package imports are simulated. This is not evidence of a cross-module call attempt.
- A separate model-supported-body control uses the same imported apply_decorator with def f(): pass. It imports pkg.decorators, records the FROM binding, then returns UNKNOWN before CALL_FUNCTION. Complete events:

    ENTRY:START_IMPORT(target=pkg)
    pkg:READY
    ENTRY:START_IMPORT(target=pkg.app)
    pkg.app:START_IMPORT(target=pkg.decorators)
    pkg.decorators:DEFINE_FUNCTION(symbol=apply_decorator)
    pkg.decorators:READY
    pkg:BIND_CHILD(target=pkg.decorators, symbol=decorators)
    pkg.app:FROM(target=pkg.decorators, symbol=apply_decorator)

- That control emits no CALL_FUNCTION for apply_decorator, START_IMPORT(pkg.effect), or FUNCTION_LOCAL_IMPORT(pkg.effect). The decorator body is not executed by the model, so its import is not represented as a modeled effect.

## IMPORTED_ALIAS_BEHAVIOR

DIRECT_EVIDENCE:

- In case C, pkg.app binds identity as alias. The CPython runner checks app.alias is decorators.identity and gets true. It separately checks final f is the object seen by identity and gets true.
- The Contextor outcome for the exact case C fixture is UNKNOWN, with no events. As in cases A, B and D, return 1 in the decorated function body is rejected by restricted compilation before import simulation.
- The separate helper/import-only checks establish the indexed FROM identity rule without attributing cross-module call permission to the alias.

## RETURN_NONE_BEHAVIOR

DIRECT_EVIDENCE:

- CPython case D imports successfully, executes replace once during definition, and binds f to None.
- The Contextor outcome is UNKNOWN with no events for the exact case D fixture because its decorated function body returns the unsupported constant 1 before import simulation.
- No final None binding was inferred or admitted by the model in this indexed cross-module fixture.

## CLASS_DECORATOR_COMPILER_BOUNDARY

CODE_PATH_PROVED:

- For exact case E, the class decorator is imported by FROM, not defined by an earlier local DEFINE_FUNCTION operation in pkg.app. The ordinary named-class-decorator compiler gate rejects that shape. The model outcome is UNKNOWN, target_module=pkg.app, symbol=None, events=().
- CPython succeeds: the imported identity decorator receives the newly created class and returns the same callable class object.
- The existing compiler gate was not changed or weakened.

## EXTERNAL_FUNCTOOLS_BOUNDARY

DIRECT_EVIDENCE:

- A focused negative test uses from functools import lru_cache with @lru_cache and no assumptions. It gets UNKNOWN, evidence_scope RESTRICTED_REGULAR_PACKAGE_MODEL, target_module=functools, and reached_unmodeled_import=(operation=FROM, target=functools, symbol=lru_cache, line=1, column=0). No CALL_FUNCTION for lru_cache is emitted.
- execution/imports.py:261-294 keeps an ordinary external import at UNKNOWN_UNMODELED; only the explicit conditional passive-import mode can assume it.
- No lru_cache allowlist or production treatment was added. External-import policy was not changed.

## MODEL_OBSERVATIONS

For each exact required A-E source set, evaluate_package_import_order returns UNKNOWN with evidence_scope RESTRICTED_REGULAR_PACKAGE_MODEL, target_module=pkg.app, symbol=None, and events=(). A-D are blocked during full restricted compilation because the decorated function body returns constant 1. E is blocked by the preceding-local-DEFINE_FUNCTION class decorator gate.

The separate supported-body cross-module effect control returns UNKNOWN for target_module=pkg.app and symbol=apply_decorator. Its full event tuple is the eight events listed under DECORATOR_APPLICATION_EFFECTS. It contains FROM but no CALL_FUNCTION and no effect-module START_IMPORT.

The separate ordinary external functools control returns UNKNOWN with target_module=functools; events are ENTRY:START_IMPORT(pkg), pkg:READY, ENTRY:START_IMPORT(pkg.app). The reached unmodeled import is FROM functools lru_cache at 1:0.

No UNKNOWN result is classified as a CPython mismatch.

## TARGETED_TEST_RESULTS

The first full targeted invocation exposed test-runner wiring error in case C: the runner was given alias as the final decorated binding name and attempted alias(), causing TypeError because identity requires fn. This was not a CPython/model semantic discrepancy. The runner was corrected to track decorator_binding_name separately from final binding_name; the exact fixture sources and expected outcomes were preserved. A trace hook now observes identity and definition-time calls without adding statements to pkg.decorators.

Final required command:

    .venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_cross_module_decorator_baseline.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_cycle_semantics_class_decorator_baseline.py tests/test_cycle_semantics_class_decorator_identity_counterexamples.py tests/test_cycle_semantics_stacked_decorator_execution.py tests/test_cycle_semantics_package_model.py -rs

Result: 252 passed in 19.68s. The new file contributes 9 passing tests.

No full pytest, SCC02, FULL, backend restart or update_file was run. No Git add, commit, push or history/index operation was performed.

## MCP_POST_TASK_AUDIT

DIRECT_EVIDENCE:

- Contextor get_module_context for tests/test_cycle_semantics_cross_module_decorator_baseline.py resolved tests.test_cycle_semantics_cross_module_decorator_baseline at canonical LIVE revision 1370.
- canonical_state=fresh; workspace_sync=verified; provenance=live. cycle_semantics remained stale; no semantic refresh was run.
- Syntax errors: 0, availability=fresh.
- Structural DFS cycles: 16, availability=fresh. Count semantics are DFS back-edge paths with rotation deduplication, not all simple cycles.

## FULL_DIFFS

Complete new-file diff follows. It is the final source version tested by the targeted command above.

    diff --git a/tests/test_cycle_semantics_cross_module_decorator_baseline.py b/tests/test_cycle_semantics_cross_module_decorator_baseline.py
    new file mode 100644
    index 0000000..68b95ea
    --- /dev/null
    +++ b/tests/test_cycle_semantics_cross_module_decorator_baseline.py
    @@ -0,0 +1,451 @@
    +"""CPython and current-model baseline for indexed cross-module decorators."""
    +
    +import ast
    +import json
    +import subprocess
    +import sys
    +from pathlib import Path
    +
    +import pytest
    +
    +from contextor.core.cycle_semantics.execution.calls import (
    +    _execute_restricted_object_call,
    +    _new_restricted_function,
    +)
    +from contextor.core.cycle_semantics.execution.imports import (
    +    _execute_from_binding,
    +)
    +from contextor.core.cycle_semantics.execution.steps import _Step
    +from contextor.core.cycle_semantics.package_model import (
    +    evaluate_package_import_order,
    +)
    +
    +
    +_REFERENCE_RUNNER = r"""
    +import builtins
    +import importlib
    +import json
    +import sys
    +
    +sys.path.insert(0, sys.argv[1])
    +export_name = sys.argv[2]
    +binding_name = sys.argv[3]
    +binding_kind = sys.argv[4]
    +decorator_binding_name = sys.argv[5]
    +imports = []
    +original_import = builtins.__import__
    +decorator_inputs = []
    +
    +def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
    +    if name in {"pkg.decorators", "pkg.effect"}:
    +        imports.append(name)
    +    return original_import(name, globals, locals, fromlist, level)
    +
    +builtins.__import__ = traced_import
    +def trace_decorator(frame, event, arg):
    +    if (
    +        event == "call"
    +        and frame.f_globals.get("__name__") == "pkg.decorators"
    +        and frame.f_code.co_name == export_name
    +    ):
    +        parameter = "cls" if binding_kind == "class" else "fn"
    +        decorator_inputs.append(frame.f_locals.get(parameter))
    +    return trace_decorator
    +
    +sys.settrace(trace_decorator)
    +error = None
    +try:
    +    importlib.import_module("pkg.app")
    +except BaseException as exc:
    +    error = {"type": type(exc).__name__, "message": str(exc)}
    +finally:
    +    sys.settrace(None)
    +
    +app = sys.modules.get("pkg.app")
    +decorators = sys.modules.get("pkg.decorators")
    +binding_present = app is not None and binding_name in app.__dict__
    +value = app.__dict__.get(binding_name) if binding_present else None
    +seen = decorator_inputs[0] if decorator_inputs else None
    +decorator_calls_at_definition = len(decorator_inputs)
    +body_result = None
    +body_result_type = None
    +if error is None and callable(value):
    +    if binding_kind == "function":
    +        body_result = value()
    +    else:
    +        instance = value()
    +        body_result_type = (
    +            type(instance).__module__ + "." + type(instance).__qualname__
    +        )
    +
    +print(json.dumps({
    +    "error": error,
    +    "imports": imports,
    +    "binding_present": binding_present,
    +    "binding_type": (
    +        type(value).__module__ + "." + type(value).__qualname__
    +        if binding_present else None
    +    ),
    +    "binding_callable": callable(value) if binding_present else False,
    +    "body_result": body_result,
    +    "body_result_type": body_result_type,
    +    "decorator_calls_at_definition": decorator_calls_at_definition,
    +    "decorator_seen_present": bool(decorator_inputs),
    +    "binding_is_decorator_input": (
    +        binding_present and value is seen and seen is not None
    +    ),
    +    "binding_is_imported_export": (
    +        app is not None
    +        and decorators is not None
    +        and app.__dict__.get(decorator_binding_name) is getattr(
    +            decorators, export_name, object()
    +        )
    +    ),
    +}, sort_keys=True))
    +"""
    +
    +
    +def _case_sources(case):
    +    sources = {
    +        "pkg.__init__": "pass\n",
    +    }
    +
    +    if case == "A":
    +        sources.update({
    +            "pkg.decorators": (
    +                "def identity(fn):\n"
    +                "    return fn\n"
    +            ),
    +            "pkg.app": (
    +                "from pkg.decorators import identity\n"
    +                "@identity\n"
    +                "def f():\n"
    +                "    return 1\n"
    +            ),
    +        })
    +    elif case == "B":
    +        sources.update({
    +            "pkg.decorators": (
    +                "def apply_decorator(fn):\n"
    +                "    import pkg.effect\n"
    +                "    return fn\n"
    +            ),
    +            "pkg.app": (
    +                "from pkg.decorators import apply_decorator\n"
    +                "@apply_decorator\n"
    +                "def f():\n"
    +                "    return 1\n"
    +            ),
    +            "pkg.effect": "pass\n",
    +        })
    +    elif case == "C":
    +        sources.update({
    +            "pkg.decorators": (
    +                "def identity(fn):\n"
    +                "    return fn\n"
    +            ),
    +            "pkg.app": (
    +                "from pkg.decorators import identity as alias\n"
    +                "@alias\n"
    +                "def f():\n"
    +                "    return 1\n"
    +            ),
    +        })
    +    elif case == "D":
    +        sources.update({
    +            "pkg.decorators": (
    +                "def replace(fn):\n"
    +                "    return None\n"
    +            ),
    +            "pkg.app": (
    +                "from pkg.decorators import replace\n"
    +                "@replace\n"
    +                "def f():\n"
    +                "    return 1\n"
    +            ),
    +        })
    +    elif case == "E":
    +        sources.update({
    +            "pkg.decorators": (
    +                "def identity(cls):\n"
    +                "    return cls\n"
    +            ),
    +            "pkg.app": (
    +                "from pkg.decorators import identity\n"
    +                "@identity\n"
    +                "class C:\n"
    +                "    pass\n"
    +            ),
    +        })
    +    else:
    +        raise AssertionError(f"unknown case: {case}")
    +
    +    return sources
    +
    +
    +def _write_sources(root: Path, sources):
    +    for module, source in sources.items():
    +        parts = module.split(".")
    +        if parts[-1] == "__init__":
    +            directory = root.joinpath(*parts[:-1])
    +            filename = "__init__.py"
    +        else:
    +            directory = root.joinpath(*parts[:-1])
    +            filename = parts[-1] + ".py"
    +        directory.mkdir(parents=True, exist_ok=True)
    +        directory.joinpath(filename).write_text(source, encoding="utf-8")
    +
    +
    +def _reference(
    +    tmp_path,
    +    sources,
    +    export_name,
    +    binding_name,
    +    binding_kind,
    +    decorator_binding_name,
    +):
    +    _write_sources(tmp_path, sources)
    +    completed = subprocess.run(
    +        [
    +            sys.executable,
    +            "-I",
    +            "-B",
    +            "-c",
    +            _REFERENCE_RUNNER,
    +            str(tmp_path),
    +            export_name,
    +            binding_name,
    +            binding_kind,
    +            decorator_binding_name,
    +        ],
    +        capture_output=True,
    +        text=True,
    +        timeout=20,
    +        check=False,
    +    )
    +    assert completed.returncode == 0, completed.stderr
    +    return json.loads(completed.stdout)
    +
    +
    +@pytest.mark.parametrize(
    +    "case,export_name,decorator_binding_name,binding_name,binding_kind,expected_imports,expected_type,expected_callable,expected_result,expected_instance_type,expected_same_input",
    +    [
    +        pytest.param(
    +            "A", "identity", "identity", "f", "function",
    +            ("pkg.decorators",), "builtins.function", True, 1, None, True,
    +            id="A-imported-identity-function",
    +        ),
    +        pytest.param(
    +            "B", "apply_decorator", "apply_decorator", "f", "function",
    +            ("pkg.decorators", "pkg.effect"),
    +            "builtins.function", True, 1, None, True,
    +            id="B-imported-decorator-effect",
    +        ),
    +        pytest.param(
    +            "C", "identity", "alias", "f", "function",
    +            ("pkg.decorators",), "builtins.function", True, 1, None, True,
    +            id="C-imported-alias",
    +        ),
    +        pytest.param(
    +            "D", "replace", "replace", "f", "function",
    +            ("pkg.decorators",), "builtins.NoneType", False, None, None, False,
    +            id="D-imported-decorator-returns-none",
    +        ),
    +        pytest.param(
    +            "E", "identity", "identity", "C", "class",
    +            ("pkg.decorators",), "builtins.type", True, None,
    +            "pkg.app.C", True,
    +            id="E-imported-class-decorator",
    +        ),
    +    ],
    +)
    +def test_indexed_cross_module_decorator_reference_and_model_boundary(
    +    tmp_path,
    +    case,
    +    export_name,
    +    decorator_binding_name,
    +    binding_name,
    +    binding_kind,
    +    expected_imports,
    +    expected_type,
    +    expected_callable,
    +    expected_result,
    +    expected_instance_type,
    +    expected_same_input,
    +):
    +    sources = _case_sources(case)
    +    observed = _reference(
    +        tmp_path,
    +        sources,
    +        export_name,
    +        binding_name,
    +        binding_kind,
    +        decorator_binding_name,
    +    )
    +
    +    assert observed["error"] is None
    +    assert tuple(observed["imports"]) == expected_imports
    +    assert observed["binding_present"] is True
    +    assert observed["binding_type"] == expected_type
    +    assert observed["binding_callable"] is expected_callable
    +    assert observed["body_result"] == expected_result
    +    assert observed["body_result_type"] == expected_instance_type
    +    assert observed["decorator_calls_at_definition"] == 1
    +    assert observed["decorator_seen_present"] is True
    +    assert observed["binding_is_decorator_input"] is expected_same_input
    +    assert observed["binding_is_imported_export"] is True
    +
    +    modeled = evaluate_package_import_order(
    +        {name: ast.parse(source) for name, source in sources.items()},
    +        "pkg.app",
    +    )
    +    assert modeled.outcome == "UNKNOWN"
    +    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    +    assert modeled.events == ()
    +
    +
    +def test_indexed_from_import_availability_does_not_admit_cross_module_call():
    +    identity = _new_restricted_function(
    +        "pkg.decorators",
    +        (),
    +        ("fn",),
    +    )
    +    namespaces = {
    +        "pkg.decorators": {"identity": identity},
    +        "pkg.app": {},
    +    }
    +    control = _execute_from_binding(
    +        _Step(
    +            "FROM",
    +            target="pkg.decorators",
    +            symbol="identity",
    +            binding="alias",
    +        ),
    +        module="pkg.app",
    +        states={"pkg.decorators": "READY"},
    +        namespaces=namespaces,
    +        class_namespace_admissible=lambda value: True,
    +    )
    +
    +    assert control.action == "ADVANCE"
    +    assert namespaces["pkg.app"]["alias"] is identity
    +    assert identity.defining_module == "pkg.decorators"
    +    assert _execute_restricted_object_call(
    +        identity,
    +        object(),
    +        module="pkg.app",
    +        local_bindings={},
    +    ) is None
    +
    +    indexed_sources = {
    +        "pkg.__init__": ast.parse("pass\n"),
    +        "pkg.decorators": ast.parse(
    +            "def identity(fn):\n    return fn\n"
    +        ),
    +        "pkg.app": ast.parse(
    +            "from pkg.decorators import identity\n"
    +        ),
    +    }
    +    imported = evaluate_package_import_order(indexed_sources, "pkg.app")
    +    assert imported.outcome == "MODEL_PASS"
    +    assert imported.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    +    assert any(
    +        event.operation == "FROM"
    +        and event.module == "pkg.app"
    +        and event.target == "pkg.decorators"
    +        and event.symbol == "identity"
    +        for event in imported.events
    +    )
    +
    +
    +def test_imported_decorator_body_effect_is_not_reported_as_model_execution():
    +    sources = {
    +        "pkg.__init__": ast.parse("pass\n"),
    +        "pkg.decorators": ast.parse(
    +            "def apply_decorator(fn):\n"
    +            "    import pkg.effect\n"
    +            "    return fn\n"
    +        ),
    +        "pkg.app": ast.parse(
    +            "from pkg.decorators import apply_decorator\n"
    +            "@apply_decorator\n"
    +            "def f():\n"
    +            "    pass\n"
    +        ),
    +        "pkg.effect": ast.parse("pass\n"),
    +    }
    +    modeled = evaluate_package_import_order(sources, "pkg.app")
    +
    +    assert modeled.outcome == "UNKNOWN"
    +    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    +    assert any(
    +        event.operation == "FROM"
    +        and event.module == "pkg.app"
    +        and event.target == "pkg.decorators"
    +        and event.symbol == "apply_decorator"
    +        for event in modeled.events
    +    )
    +    assert not any(
    +        event.operation == "CALL_FUNCTION"
    +        and event.symbol == "apply_decorator"
    +        for event in modeled.events
    +    )
    +    assert not any(
    +        event.operation == "START_IMPORT"
    +        and event.target == "pkg.effect"
    +        for event in modeled.events
    +    )
    +    assert not any(
    +        event.operation == "FUNCTION_LOCAL_IMPORT"
    +        and event.target == "pkg.effect"
    +        for event in modeled.events
    +    )
    +
    +
    +def test_external_functools_decorator_remains_unmodeled_without_assumptions():
    +    sources = {
    +        "pkg.__init__": ast.parse("pass\n"),
    +        "pkg.decorators": ast.parse("pass\n"),
    +        "pkg.app": ast.parse(
    +            "from functools import lru_cache\n"
    +            "@lru_cache\n"
    +            "def f():\n"
    +            "    pass\n"
    +        ),
    +    }
    +    modeled = evaluate_package_import_order(sources, "pkg.app")
    +
    +    assert modeled.outcome == "UNKNOWN"
    +    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    +    assert modeled.target_module == "functools"
    +    assert modeled.reached_unmodeled_import is not None
    +    assert (
    +        modeled.reached_unmodeled_import.operation,
    +        modeled.reached_unmodeled_import.target,
    +        modeled.reached_unmodeled_import.symbol,
    +    ) == ("FROM", "functools", "lru_cache")
    +    assert not any(
    +        event.operation == "CALL_FUNCTION"
    +        and event.symbol == "lru_cache"
    +        for event in modeled.events
    +    )
    +
    +
    +def test_imported_class_decorator_does_not_satisfy_local_compile_gate():
    +    sources = {
    +        "pkg.__init__": ast.parse("pass\n"),
    +        "pkg.decorators": ast.parse(
    +            "def identity(cls):\n    return cls\n"
    +        ),
    +        "pkg.app": ast.parse(
    +            "from pkg.decorators import identity\n"
    +            "@identity\n"
    +            "class C:\n"
    +            "    pass\n"
    +        ),
    +    }
    +    modeled = evaluate_package_import_order(sources, "pkg.app")
    +
    +    assert modeled.outcome == "UNKNOWN"
    +    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    +    assert modeled.events == ()
