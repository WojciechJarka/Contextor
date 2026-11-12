"""CPython and current-model baseline for indexed cross-module decorators."""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.execution.calls import (
    _execute_restricted_object_call,
    _new_restricted_function,
)
from contextor.core.cycle_semantics.execution.imports import (
    _execute_from_binding,
)
from contextor.core.cycle_semantics.execution.steps import _Step
from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


_REFERENCE_RUNNER = r"""
import builtins
import importlib
import json
import sys

sys.path.insert(0, sys.argv[1])
export_name = sys.argv[2]
binding_name = sys.argv[3]
binding_kind = sys.argv[4]
decorator_binding_name = sys.argv[5]
imports = []
original_import = builtins.__import__
decorator_inputs = []

def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in {"pkg.decorators", "pkg.effect", "pkg.decorators.effect"}:
        imports.append(name)
    return original_import(name, globals, locals, fromlist, level)

builtins.__import__ = traced_import
def trace_decorator(frame, event, arg):
    if (
        event == "call"
        and frame.f_globals.get("__name__") == "pkg.decorators"
        and frame.f_code.co_name == export_name
    ):
        parameter = "cls" if binding_kind == "class" else "fn"
        decorator_inputs.append(frame.f_locals.get(parameter))
    return trace_decorator

sys.settrace(trace_decorator)
error = None
try:
    importlib.import_module("pkg.app")
except BaseException as exc:
    error = {"type": type(exc).__name__, "message": str(exc)}
finally:
    sys.settrace(None)

app = sys.modules.get("pkg.app")
decorators = sys.modules.get("pkg.decorators")
decorator = (
    getattr(decorators, export_name, None)
    if decorators is not None else None
)
binding_present = app is not None and binding_name in app.__dict__
value = app.__dict__.get(binding_name) if binding_present else None
seen = decorator_inputs[0] if decorator_inputs else None
decorator_calls_at_definition = len(decorator_inputs)
body_result = None
body_result_type = None
if error is None and callable(value):
    if binding_kind == "function":
        body_result = value()
    else:
        instance = value()
        body_result_type = (
            type(instance).__module__ + "." + type(instance).__qualname__
        )

print(json.dumps({
    "error": error,
    "imports": imports,
    "binding_present": binding_present,
    "binding_type": (
        type(value).__module__ + "." + type(value).__qualname__
        if binding_present else None
    ),
    "binding_repr": repr(value) if binding_present else None,
    "binding_callable": callable(value) if binding_present else False,
    "body_result": body_result,
    "body_result_type": body_result_type,
    "decorator_calls_at_definition": decorator_calls_at_definition,
    "decorator_seen_present": bool(decorator_inputs),
    "binding_is_decorator_input": (
        binding_present and value is seen and seen is not None
    ),
    "binding_is_imported_export": (
        app is not None
        and decorators is not None
        and app.__dict__.get(decorator_binding_name) is getattr(
            decorators, export_name, object()
        )
    ),
    "decorator_package": (
        getattr(decorator, "__globals__", {}).get("__package__")
        if decorator is not None else None
    ),
    "loaded_effect_modules": [
        name
        for name in ("pkg.decorators.effect", "pkg.effect")
        if name in sys.modules
    ],
}, sort_keys=True))
"""


def _case_sources(case):
    sources = {
        "pkg.__init__": "pass\n",
    }

    if case == "A":
        sources.update({
            "pkg.decorators": (
                "def identity(fn):\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\n"
                "def f():\n"
                "    return 1\n"
            ),
        })
    elif case == "B":
        sources.update({
            "pkg.decorators": (
                "def apply_decorator(fn):\n"
                "    import pkg.effect\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import apply_decorator\n"
                "@apply_decorator\n"
                "def f():\n"
                "    return 1\n"
            ),
            "pkg.effect": "pass\n",
        })
    elif case == "C":
        sources.update({
            "pkg.decorators": (
                "def identity(fn):\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import identity as alias\n"
                "@alias\n"
                "def f():\n"
                "    return 1\n"
            ),
        })
    elif case == "D":
        sources.update({
            "pkg.decorators": (
                "def replace(fn):\n"
                "    return None\n"
            ),
            "pkg.app": (
                "from pkg.decorators import replace\n"
                "@replace\n"
                "def f():\n"
                "    return 1\n"
            ),
        })
    elif case == "E":
        sources.update({
            "pkg.decorators": (
                "def identity(cls):\n"
                "    return cls\n"
            ),
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\n"
                "class C:\n"
                "    pass\n"
            ),
        })
    elif case == "A2":
        sources.update({
            "pkg.decorators": (
                "def identity(fn):\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\n"
                "def f():\n"
                "    pass\n"
            ),
        })
    elif case == "B2":
        sources.update({
            "pkg.decorators": (
                "def apply_decorator(fn):\n"
                "    import pkg.effect\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import apply_decorator\n"
                "@apply_decorator\n"
                "def f():\n"
                "    pass\n"
            ),
            "pkg.effect": "pass\n",
        })
    elif case == "C2":
        sources.update({
            "pkg.decorators": (
                "def identity(fn):\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import identity as alias\n"
                "@alias\n"
                "def f():\n"
                "    pass\n"
            ),
        })
    elif case == "D2":
        sources.update({
            "pkg.decorators": (
                "def replace(fn):\n"
                "    return None\n"
            ),
            "pkg.app": (
                "from pkg.decorators import replace\n"
                "@replace\n"
                "def f():\n"
                "    pass\n"
            ),
        })
    elif case == "E2":
        sources.update({
            "pkg.decorators.__init__": (
                "def relative_decorator(fn):\n"
                "    from . import effect\n"
                "    return effect.ORIGIN\n"
            ),
            "pkg.decorators.effect": (
                "ORIGIN = 'defining-package-effect'\n"
            ),
            "pkg.effect": "ORIGIN = 'caller-package-effect'\n",
            "pkg.app": (
                "from pkg.decorators import relative_decorator\n"
                "@relative_decorator\n"
                "def f():\n"
                "    pass\n"
            ),
        })
    elif case == "F2":
        sources.update({
            "pkg.decorators": (
                "marker = 'decorators-global'\n"
                "def read_marker(fn):\n"
                "    return marker\n"
            ),
            "pkg.app": (
                "marker = 'app-global'\n"
                "from pkg.decorators import read_marker\n"
                "@read_marker\n"
                "def f():\n"
                "    pass\n"
            ),
        })
    else:
        raise AssertionError(f"unknown case: {case}")

    return sources


def _write_sources(root: Path, sources):
    for module, source in sources.items():
        parts = module.split(".")
        if parts[-1] == "__init__":
            directory = root.joinpath(*parts[:-1])
            filename = "__init__.py"
        else:
            directory = root.joinpath(*parts[:-1])
            filename = parts[-1] + ".py"
        directory.mkdir(parents=True, exist_ok=True)
        directory.joinpath(filename).write_text(source, encoding="utf-8")


def _reference(
    tmp_path,
    sources,
    export_name,
    binding_name,
    binding_kind,
    decorator_binding_name,
):
    _write_sources(tmp_path, sources)
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            _REFERENCE_RUNNER,
            str(tmp_path),
            export_name,
            binding_name,
            binding_kind,
            decorator_binding_name,
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.parametrize(
    "case,export_name,decorator_binding_name,binding_name,binding_kind,expected_imports,expected_type,expected_callable,expected_result,expected_instance_type,expected_same_input",
    [
        pytest.param(
            "A", "identity", "identity", "f", "function",
            ("pkg.decorators",), "builtins.function", True, 1, None, True,
            id="A-imported-identity-function",
        ),
        pytest.param(
            "B", "apply_decorator", "apply_decorator", "f", "function",
            ("pkg.decorators", "pkg.effect"),
            "builtins.function", True, 1, None, True,
            id="B-imported-decorator-effect",
        ),
        pytest.param(
            "C", "identity", "alias", "f", "function",
            ("pkg.decorators",), "builtins.function", True, 1, None, True,
            id="C-imported-alias",
        ),
        pytest.param(
            "D", "replace", "replace", "f", "function",
            ("pkg.decorators",), "builtins.NoneType", False, None, None, False,
            id="D-imported-decorator-returns-none",
        ),
        pytest.param(
            "E", "identity", "identity", "C", "class",
            ("pkg.decorators",), "builtins.type", True, None,
            "pkg.app.C", True,
            id="E-imported-class-decorator",
        ),
    ],
)
def test_indexed_cross_module_decorator_reference_and_model_boundary(
    tmp_path,
    case,
    export_name,
    decorator_binding_name,
    binding_name,
    binding_kind,
    expected_imports,
    expected_type,
    expected_callable,
    expected_result,
    expected_instance_type,
    expected_same_input,
):
    sources = _case_sources(case)
    observed = _reference(
        tmp_path,
        sources,
        export_name,
        binding_name,
        binding_kind,
        decorator_binding_name,
    )

    assert observed["error"] is None
    assert tuple(observed["imports"]) == expected_imports
    assert observed["binding_present"] is True
    assert observed["binding_type"] == expected_type
    assert observed["binding_callable"] is expected_callable
    assert observed["body_result"] == expected_result
    assert observed["body_result_type"] == expected_instance_type
    assert observed["decorator_calls_at_definition"] == 1
    assert observed["decorator_seen_present"] is True
    assert observed["binding_is_decorator_input"] is expected_same_input
    assert observed["binding_is_imported_export"] is True

    modeled = evaluate_package_import_order(
        {name: ast.parse(source) for name, source in sources.items()},
        "pkg.app",
    )
    assert modeled.outcome == "UNKNOWN"
    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert modeled.events == ()


@pytest.mark.parametrize(
    "case,export_name,decorator_binding_name,imported_symbol,expected_imports,expected_type,expected_callable,expected_result,expected_same_input",
    [
        pytest.param(
            "A2", "identity", "identity", "identity",
            ("pkg.decorators",), "builtins.function", True, None, True,
            id="A2-supported-imported-identity",
        ),
        pytest.param(
            "B2", "apply_decorator", "apply_decorator", "apply_decorator",
            ("pkg.decorators", "pkg.effect"),
            "builtins.function", True, None, True,
            id="B2-supported-imported-effectful-decorator",
        ),
        pytest.param(
            "C2", "identity", "alias", "identity",
            ("pkg.decorators",), "builtins.function", True, None, True,
            id="C2-supported-imported-alias",
        ),
        pytest.param(
            "D2", "replace", "replace", "replace",
            ("pkg.decorators",), "builtins.NoneType", False, None, False,
            id="D2-supported-imported-returns-none",
        ),
    ],
)
def test_supported_body_imported_decorators_execute_when_supported(
    tmp_path,
    case,
    export_name,
    decorator_binding_name,
    imported_symbol,
    expected_imports,
    expected_type,
    expected_callable,
    expected_result,
    expected_same_input,
):
    sources = _case_sources(case)
    observed = _reference(
        tmp_path,
        sources,
        export_name,
        "f",
        "function",
        decorator_binding_name,
    )

    assert observed["error"] is None
    assert tuple(observed["imports"]) == expected_imports
    assert observed["binding_present"] is True
    assert observed["binding_type"] == expected_type
    assert observed["binding_callable"] is expected_callable
    assert observed["body_result"] == expected_result
    assert observed["decorator_calls_at_definition"] == 1
    assert observed["decorator_seen_present"] is True
    assert observed["binding_is_decorator_input"] is expected_same_input
    assert observed["binding_is_imported_export"] is True

    modeled = evaluate_package_import_order(
        {name: ast.parse(source) for name, source in sources.items()},
        "pkg.app",
    )
    assert modeled.outcome == ("UNKNOWN" if case == "D2" else "MODEL_PASS")
    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == imported_symbol
        for event in modeled.events
    )
    decorator_calls = tuple(
        event
        for event in modeled.events
        if event.operation == "CALL_FUNCTION"
        and event.symbol == decorator_binding_name
    )
    if case == "D2":
        assert decorator_calls == ()
        assert not any(
            event.target == "pkg.effect"
            for event in modeled.events
        )
    else:
        assert len(decorator_calls) == 1
        assert decorator_calls[0].module == "pkg.app"

        if case == "B2":
            effect_imports = tuple(
                event
                for event in modeled.events
                if event.operation == "FUNCTION_LOCAL_IMPORT"
                and event.target == "pkg.effect"
            )
            assert len(effect_imports) == 1
            assert effect_imports[0].module == "pkg.decorators"
            assert sum(
                event.operation == "START_IMPORT"
                and event.target == "pkg.effect"
                for event in modeled.events
            ) == 1
        else:
            assert not any(
                event.target == "pkg.effect"
                for event in modeled.events
            )


def test_cpython_relative_decorator_import_uses_defining_package_context(
    tmp_path,
):
    sources = _case_sources("E2")
    observed = _reference(
        tmp_path,
        sources,
        "relative_decorator",
        "f",
        "function",
        "relative_decorator",
    )

    assert observed["error"] is None
    assert observed["binding_present"] is True
    assert observed["binding_type"] == "builtins.str"
    assert observed["binding_repr"] == repr("defining-package-effect")
    assert observed["decorator_package"] == "pkg.decorators"
    assert observed["loaded_effect_modules"] == ["pkg.decorators.effect"]
    assert observed["decorator_calls_at_definition"] == 1
    assert observed["binding_is_imported_export"] is True


def test_cpython_imported_decorator_reads_its_defining_module_global(
    tmp_path,
):
    sources = _case_sources("F2")
    observed = _reference(
        tmp_path,
        sources,
        "read_marker",
        "f",
        "function",
        "read_marker",
    )

    assert observed["error"] is None
    assert observed["binding_present"] is True
    assert observed["binding_type"] == "builtins.str"
    assert observed["binding_repr"] == repr("decorators-global")
    assert observed["decorator_calls_at_definition"] == 1
    assert observed["binding_is_imported_export"] is True


def test_indexed_from_import_availability_does_not_admit_cross_module_call():
    identity = _new_restricted_function(
        "pkg.decorators",
        (),
        ("fn",),
    )
    namespaces = {
        "pkg.decorators": {"identity": identity},
        "pkg.app": {},
    }
    control = _execute_from_binding(
        _Step(
            "FROM",
            target="pkg.decorators",
            symbol="identity",
            binding="alias",
        ),
        module="pkg.app",
        states={"pkg.decorators": "READY"},
        namespaces=namespaces,
        class_namespace_admissible=lambda value: True,
    )

    assert control.action == "ADVANCE"
    assert namespaces["pkg.app"]["alias"] is identity
    assert identity.defining_module == "pkg.decorators"
    assert _execute_restricted_object_call(
        identity,
        object(),
        module="pkg.app",
        local_bindings={},
    ) is None

    indexed_sources = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.decorators": ast.parse(
            "def identity(fn):\n    return fn\n"
        ),
        "pkg.app": ast.parse(
            "from pkg.decorators import identity\n"
        ),
    }
    imported = evaluate_package_import_order(indexed_sources, "pkg.app")
    assert imported.outcome == "MODEL_PASS"
    assert imported.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == "identity"
        for event in imported.events
    )


def test_imported_decorator_body_effect_is_not_reported_as_model_execution():
    sources = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.decorators": ast.parse(
            "def apply_decorator(fn):\n"
            "    import pkg.effect\n"
            "    return fn\n"
        ),
        "pkg.app": ast.parse(
            "from pkg.decorators import apply_decorator\n"
            "@apply_decorator\n"
            "def f():\n"
            "    pass\n"
        ),
        "pkg.effect": ast.parse("pass\n"),
    }
    modeled = evaluate_package_import_order(sources, "pkg.app")

    assert modeled.outcome == "MODEL_PASS"
    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == "apply_decorator"
        for event in modeled.events
    )
    calls = tuple(
        event
        for event in modeled.events
        if event.operation == "CALL_FUNCTION"
        and event.symbol == "apply_decorator"
    )
    assert len(calls) == 1
    assert calls[0].module == "pkg.app"
    starts = tuple(
        event
        for event in modeled.events
        if event.operation == "START_IMPORT"
        and event.target == "pkg.effect"
    )
    assert len(starts) == 1
    local_imports = tuple(
        event
        for event in modeled.events
        if event.operation == "FUNCTION_LOCAL_IMPORT"
        and event.target == "pkg.effect"
    )
    assert len(local_imports) == 1
    assert local_imports[0].module == "pkg.decorators"
    assert modeled.events.index(calls[0]) < modeled.events.index(local_imports[0])


def test_external_functools_decorator_remains_unmodeled_without_assumptions():
    sources = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.decorators": ast.parse("pass\n"),
        "pkg.app": ast.parse(
            "from functools import lru_cache\n"
            "@lru_cache\n"
            "def f():\n"
            "    pass\n"
        ),
    }
    modeled = evaluate_package_import_order(sources, "pkg.app")

    assert modeled.outcome == "UNKNOWN"
    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert modeled.target_module == "functools"
    assert modeled.reached_unmodeled_import is not None
    assert (
        modeled.reached_unmodeled_import.operation,
        modeled.reached_unmodeled_import.target,
        modeled.reached_unmodeled_import.symbol,
    ) == ("FROM", "functools", "lru_cache")
    assert not any(
        event.operation == "CALL_FUNCTION"
        and event.symbol == "lru_cache"
        for event in modeled.events
    )


def test_imported_class_decorator_does_not_satisfy_local_compile_gate():
    sources = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.decorators": ast.parse(
            "def identity(cls):\n    return cls\n"
        ),
        "pkg.app": ast.parse(
            "from pkg.decorators import identity\n"
            "@identity\n"
            "class C:\n"
            "    pass\n"
        ),
    }
    modeled = evaluate_package_import_order(sources, "pkg.app")

    assert modeled.outcome == "UNKNOWN"
    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert modeled.events == ()
