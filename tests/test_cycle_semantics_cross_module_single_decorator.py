"""CPython-backed contract for one indexed cross-module decorator."""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


_REFERENCE_RUNNER = r"""
import builtins
import importlib
import json
import sys

sys.path.insert(0, sys.argv[1])
decorator_name = sys.argv[2]
invoke_after_import = sys.argv[3] == "true"
imports = []
decorator_inputs = []
original_import = builtins.__import__

def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in {"pkg.decorators", "pkg.effect"}:
        imports.append(name)
    elif (
        level == 1
        and globals is not None
        and globals.get("__package__") == "pkg.decorators"
        and (name == "effect" or "effect" in fromlist)
    ):
        imports.append("pkg.decorators.effect")
    return original_import(name, globals, locals, fromlist, level)

builtins.__import__ = traced_import

def trace_decorator(frame, event, arg):
    if (
        event == "call"
        and frame.f_globals.get("__name__") == "pkg.decorators"
        and frame.f_code.co_name == decorator_name
    ):
        decorator_inputs.append(frame.f_locals.get("fn"))
    return trace_decorator

sys.settrace(trace_decorator)
error = None
try:
    app = importlib.import_module("pkg.app")
except BaseException as exc:
    app = sys.modules.get("pkg.app")
    error = {"type": type(exc).__name__, "message": str(exc)}
finally:
    sys.settrace(None)

binding_present = app is not None and "f" in app.__dict__
value = app.__dict__.get("f") if binding_present else None
call_error = None
if error is None and invoke_after_import:
    try:
        value()
    except BaseException as exc:
        call_error = {"type": type(exc).__name__, "message": str(exc)}

seen = decorator_inputs[0] if decorator_inputs else None
print(json.dumps({
    "python": list(sys.version_info[:3]),
    "error": error,
    "call_error": call_error,
    "imports": imports,
    "binding_present": binding_present,
    "binding_type": (
        type(value).__module__ + "." + type(value).__qualname__
        if binding_present else None
    ),
    "binding_callable": callable(value) if binding_present else False,
    "binding_is_decorator_input": binding_present and value is seen,
    "decorator_calls": len(decorator_inputs),
    "loaded_effect_modules": [
        name
        for name in ("pkg.effect", "pkg.decorators.effect")
        if name in sys.modules
    ],
}, sort_keys=True))
"""


def _write_sources(root: Path, sources):
    for module, source in sources.items():
        parts = module.split(".")
        directory = root.joinpath(*parts[:-1])
        filename = "__init__.py" if parts[-1] == "__init__" else parts[-1] + ".py"
        directory.mkdir(parents=True, exist_ok=True)
        directory.joinpath(filename).write_text(source, encoding="utf-8")


def _cpython_reference(tmp_path, sources, decorator_name, *, invoke=False):
    _write_sources(tmp_path, sources)
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            _REFERENCE_RUNNER,
            str(tmp_path),
            decorator_name,
            "true" if invoke else "false",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _model(sources):
    return evaluate_package_import_order(
        {name: ast.parse(source) for name, source in sources.items()},
        "pkg.app",
    )


def _events(model, operation):
    return tuple(
        event
        for event in model.events
        if event.operation == operation
    )


def _single_imported_decorator_contract(model, imported_symbol, decorator_name):
    assert model.outcome == "MODEL_PASS"
    assert model.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == imported_symbol
        for event in model.events
    )
    decorator_calls = tuple(
        event
        for event in _events(model, "CALL_FUNCTION")
        if event.symbol == decorator_name
    )
    assert len(decorator_calls) == 1
    assert decorator_calls[0].module == "pkg.app"
    function_calls = tuple(
        event
        for event in _events(model, "CALL_FUNCTION")
        if event.symbol == "f"
    )
    assert len(function_calls) == 1
    assert function_calls[0].module == "pkg.app"
    return decorator_calls[0]


def _relevant_start_imports(model):
    relevant = {"pkg.decorators", "pkg.effect", "pkg.decorators.effect"}
    return tuple(
        event.target
        for event in _events(model, "START_IMPORT")
        if event.target in relevant
    )


@pytest.mark.parametrize(
    "case,decorator_name,imported_symbol,expected_imports,expected_loaded_effects",
    [
        ("A", "identity", "identity", ("pkg.decorators",), ()),
        (
            "B",
            "apply_decorator",
            "apply_decorator",
            ("pkg.decorators", "pkg.effect"),
            ("pkg.effect",),
        ),
        ("C", "identity", "identity", ("pkg.decorators",), ()),
        (
            "G",
            "relative_decorator",
            "relative_decorator",
            ("pkg.decorators", "pkg.decorators.effect"),
            ("pkg.decorators.effect",),
        ),
    ],
    ids=["A-imported-identity", "B-indexed-effect", "C-imported-alias", "G-relative-import"],
)
def test_indexed_single_decorator_matches_cpython_and_binds_result(
    tmp_path,
    case,
    decorator_name,
    imported_symbol,
    expected_imports,
    expected_loaded_effects,
):
    sources = _positive_sources(case)
    observed = _cpython_reference(tmp_path, sources, decorator_name)

    assert observed["python"] == [3, 15, 2]
    assert observed["error"] is None
    assert tuple(observed["imports"]) == expected_imports
    assert observed["binding_present"] is True
    assert observed["binding_type"] == "builtins.function"
    assert observed["binding_callable"] is True
    assert observed["binding_is_decorator_input"] is True
    assert observed["decorator_calls"] == 1
    assert tuple(observed["loaded_effect_modules"]) == expected_loaded_effects

    modeled = _model(sources)
    decorator_call = _single_imported_decorator_contract(
        modeled,
        imported_symbol,
        decorator_name,
    )
    assert _relevant_start_imports(modeled) == expected_imports

    local_imports = _events(modeled, "FUNCTION_LOCAL_IMPORT")
    if case == "B":
        effect_import = tuple(
            event
            for event in local_imports
            if event.target == "pkg.effect"
        )
        assert len(effect_import) == 1
        assert effect_import[0].module == "pkg.decorators"
        starts = _events(modeled, "START_IMPORT")
        effect_start = next(
            index
            for index, event in enumerate(starts)
            if event.target == "pkg.effect"
        )
        assert starts[effect_start].module == "pkg.decorators"
        assert modeled.events.index(decorator_call) < modeled.events.index(
            effect_import[0]
        )
        assert modeled.events.index(decorator_call) < modeled.events.index(
            starts[effect_start]
        )
    elif case == "G":
        relative_import = tuple(
            event
            for event in local_imports
            if event.target == "pkg.decorators.effect"
        )
        assert len(relative_import) == 1
        assert relative_import[0].module == "pkg.decorators"
        assert not any(
            event.target == "pkg.effect"
            for event in modeled.events
            if event.operation in {"START_IMPORT", "FUNCTION_LOCAL_IMPORT"}
        )
        assert modeled.events.index(decorator_call) < modeled.events.index(
            relative_import[0]
        )
        relative_start = next(
            event
            for event in _events(modeled, "START_IMPORT")
            if event.target == "pkg.decorators.effect"
        )
        assert modeled.events.index(decorator_call) < modeled.events.index(
            relative_start
        )
    else:
        assert local_imports == ()

    starts = tuple(event.target for event in _events(modeled, "START_IMPORT"))
    assert len(starts) == len(set(starts))
    assert set(starts).issubset(
        {"pkg", "pkg.app", "pkg.decorators", *expected_loaded_effects}
    )


def _positive_sources(case):
    sources = {"pkg.__init__": "pass\n"}
    if case == "A":
        sources.update(
            {
                "pkg.decorators": "def identity(fn):\n    return fn\n",
                "pkg.app": (
                    "from pkg.decorators import identity\n"
                    "@identity\n"
                    "def f():\n"
                    "    pass\n"
                    "f()\n"
                ),
            }
        )
    elif case == "B":
        sources.update(
            {
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
                    "f()\n"
                ),
                "pkg.effect": "pass\n",
            }
        )
    elif case == "C":
        sources.update(
            {
                "pkg.decorators": "def identity(fn):\n    return fn\n",
                "pkg.app": (
                    "from pkg.decorators import identity as alias\n"
                    "@alias\n"
                    "def f():\n"
                    "    pass\n"
                    "f()\n"
                ),
            }
        )
    elif case == "G":
        sources.update(
            {
                "pkg.decorators.__init__": (
                    "def relative_decorator(fn):\n"
                    "    from .effect import ORIGIN\n"
                    "    return fn\n"
                ),
                "pkg.decorators.effect": "ORIGIN = 'defining-package'\n",
                "pkg.effect": "ORIGIN = 'caller-package'\n",
                "pkg.app": (
                    "from pkg.decorators import relative_decorator\n"
                    "@relative_decorator\n"
                    "def f():\n"
                    "    pass\n"
                    "f()\n"
                ),
            }
        )
    else:
        raise AssertionError(f"unknown positive case: {case}")
    return sources


def test_imported_decorator_return_none_binds_none_then_call_is_unknown(tmp_path):
    sources = {
        "pkg.__init__": "pass\n",
        "pkg.decorators": "def replace(fn):\n    return\n",
        "pkg.app": (
            "from pkg.decorators import replace\n"
            "@replace\n"
            "def f():\n"
            "    pass\n"
        ),
    }
    observed = _cpython_reference(tmp_path, sources, "replace", invoke=True)

    assert observed["python"] == [3, 15, 2]
    assert observed["error"] is None
    assert observed["call_error"]["type"] == "TypeError"
    assert tuple(observed["imports"]) == ("pkg.decorators",)
    assert observed["binding_present"] is True
    assert observed["binding_type"] == "builtins.NoneType"
    assert observed["binding_callable"] is False
    assert observed["decorator_calls"] == 1
    assert tuple(observed["loaded_effect_modules"]) == ()

    definition = _model(sources)
    assert definition.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == "replace"
        for event in definition.events
    )
    decorator_calls = _events(definition, "CALL_FUNCTION")
    assert tuple(
        event.symbol
        for event in decorator_calls
    ) == ("replace",)
    assert decorator_calls[0].module == "pkg.app"
    assert _relevant_start_imports(definition) == ("pkg.decorators",)

    called = _model(
        {
            **sources,
            "pkg.app": sources["pkg.app"] + "f()\n",
        }
    )
    assert called.outcome == "UNKNOWN"
    assert tuple(
        event.symbol
        for event in _events(called, "CALL_FUNCTION")
    ) == ("replace",)


def test_rebound_imported_decorator_is_not_called_or_replaced():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": (
                "def apply_decorator(fn):\n"
                "    import pkg.effect\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import apply_decorator\n"
                "apply_decorator = None\n"
                "@apply_decorator\n"
                "def f():\n"
                "    pass\n"
            ),
            "pkg.effect": "pass\n",
        }
    )

    assert modeled.outcome == "UNKNOWN"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == "apply_decorator"
        for event in modeled.events
    )
    assert not _events(modeled, "CALL_FUNCTION")
    assert not any(event.target == "pkg.effect" for event in modeled.events)


def test_imported_decorator_global_expression_remains_unknown():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": (
                "marker = 'decorators-global'\n"
                "def read_marker(fn):\n"
                "    return marker\n"
            ),
            "pkg.app": (
                "from pkg.decorators import read_marker\n"
                "@read_marker\n"
                "def f():\n"
                "    pass\n"
            ),
        }
    )

    assert modeled.outcome == "UNKNOWN"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == "read_marker"
        for event in modeled.events
    )
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "read_marker"
        for event in modeled.events
    )


def test_nested_unsupported_decorator_call_remains_unknown():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": (
                "def nested(fn):\n"
                "    return helper(fn)\n"
                "def helper(fn):\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import nested\n"
                "@nested\n"
                "def f():\n"
                "    pass\n"
            ),
        }
    )

    assert modeled.outcome == "UNKNOWN"
    assert any(
        event.operation == "FROM"
        and event.module == "pkg.app"
        and event.target == "pkg.decorators"
        and event.symbol == "nested"
        for event in modeled.events
    )
    assert not any(
        event.operation == "CALL_FUNCTION"
        and event.symbol in {"nested", "helper"}
        for event in modeled.events
    )


def test_same_module_single_decorator_keeps_call_order():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.app": (
                "def identity(fn):\n"
                "    return fn\n"
                "@identity\n"
                "def f():\n"
                "    pass\n"
                "f()\n"
            ),
        }
    )

    assert modeled.outcome == "MODEL_PASS"
    assert tuple(
        event.symbol
        for event in _events(modeled, "CALL_FUNCTION")
    ) == ("identity", "f")
    assert not any(event.operation == "FROM" for event in modeled.events)


def test_imported_class_decorator_remains_unknown():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": "def identity(cls):\n    return cls\n",
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\n"
                "class C:\n"
                "    pass\n"
            ),
        }
    )

    assert modeled.outcome == "UNKNOWN"
    assert any(event.operation == "FROM" for event in modeled.events)
    assert not _events(modeled, "CALL_FUNCTION")


def test_imported_stacked_decorators_remain_unknown():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.decorators": (
                "def lower(fn):\n"
                "    return fn\n"
                "def upper(fn):\n"
                "    return fn\n"
            ),
            "pkg.app": (
                "from pkg.decorators import lower, upper\n"
                "@upper\n"
                "@lower\n"
                "def f():\n"
                "    pass\n"
            ),
        }
    )

    assert modeled.outcome == "UNKNOWN"
    assert not any(
        event.operation == "CALL_FUNCTION"
        and event.symbol in {"lower", "upper"}
        for event in modeled.events
    )


def test_external_lru_cache_remains_unknown():
    modeled = _model(
        {
            "pkg.__init__": "pass\n",
            "pkg.app": (
                "from functools import lru_cache\n"
                "@lru_cache\n"
                "def f():\n"
                "    pass\n"
            ),
        }
    )

    assert modeled.outcome == "UNKNOWN"
    assert modeled.target_module == "functools"
    assert modeled.reached_unmodeled_import is not None
    assert (
        modeled.reached_unmodeled_import.operation,
        modeled.reached_unmodeled_import.target,
        modeled.reached_unmodeled_import.symbol,
    ) == ("FROM", "functools", "lru_cache")
    assert not any(
        event.operation == "CALL_FUNCTION" and event.symbol == "lru_cache"
        for event in modeled.events
    )
