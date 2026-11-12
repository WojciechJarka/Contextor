"""CPython and model baselines for cross-module decorator stacks."""

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
decorator_specs = json.loads(sys.argv[2])
tracked_imports = set(json.loads(sys.argv[3]))
tracked_effects = json.loads(sys.argv[4])
imports = []
decorator_calls = []
decorator_inputs = []
original_import = builtins.__import__

def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in tracked_imports:
        imports.append(name)
    return original_import(name, globals, locals, fromlist, level)

builtins.__import__ = traced_import

def trace_decorators(frame, event, arg):
    if event == "call":
        module_name = frame.f_globals.get("__name__")
        function_name = frame.f_code.co_name
        for expected_name, expected_module, parameter in decorator_specs:
            if function_name == expected_name and module_name == expected_module:
                value = frame.f_locals.get(parameter)
                decorator_calls.append(
                    [
                        function_name,
                        module_name,
                        type(value).__module__ + "." + type(value).__qualname__,
                    ]
                )
                decorator_inputs.append(value)
                break
    return trace_decorators

sys.settrace(trace_decorators)
error_type = None
try:
    app = importlib.import_module("pkg.app")
except BaseException as exc:
    app = sys.modules.get("pkg.app")
    error_type = type(exc).__name__
finally:
    sys.settrace(None)
    builtins.__import__ = original_import

binding_present = app is not None and "f" in app.__dict__
value = app.__dict__.get("f") if binding_present else None
print(json.dumps({
    "python": list(sys.version_info[:3]),
    "error_type": error_type,
    "decorator_calls": decorator_calls,
    "imports": imports,
    "loaded_effect_modules": [
        name for name in tracked_effects if name in sys.modules
    ],
    "binding_present": binding_present,
    "binding_type": (
        type(value).__module__ + "." + type(value).__qualname__
        if binding_present else None
    ),
    "binding_callable": callable(value) if binding_present else False,
    "binding_is_first_decorator_input": (
        binding_present
        and bool(decorator_inputs)
        and value is decorator_inputs[0]
    ),
}, sort_keys=True))
"""


_TRACKED_IMPORTS = (
    "pkg.decorators",
    "pkg.lower",
    "pkg.upper",
    "pkg.bottom_effect",
    "pkg.upper_effect",
    "pkg.lower_effect",
)
_TRACKED_EFFECTS = (
    "pkg.bottom_effect",
    "pkg.upper_effect",
    "pkg.lower_effect",
)

_DECORATOR_SPECS = {
    "A": (
        ("bottom", "pkg.decorators", "fn"),
        ("upper", "pkg.app", "fn"),
    ),
    "B": (
        ("bottom", "pkg.app", "fn"),
        ("upper", "pkg.decorators", "fn"),
    ),
    "C": (
        ("lower", "pkg.lower", "fn"),
        ("upper", "pkg.upper", "fn"),
    ),
    "D": (
        ("lower", "pkg.lower", "fn"),
        ("upper", "pkg.upper", "fn"),
    ),
    "E": (
        ("bottom", "pkg.decorators", "fn"),
        ("upper", "pkg.app", "value"),
    ),
    "F": (
        ("bottom", "pkg.app", "fn"),
        ("upper", "pkg.decorators", "fn"),
    ),
}

_EXPECTED = {
    "A": {
        "error_type": None,
        "calls": (
            ("bottom", "pkg.decorators", "builtins.function"),
            ("upper", "pkg.app", "builtins.function"),
        ),
        "imports": (
            "pkg.decorators",
            "pkg.bottom_effect",
            "pkg.upper_effect",
        ),
        "loaded_effects": ("pkg.bottom_effect", "pkg.upper_effect"),
        "binding_present": True,
        "binding_type": "builtins.function",
        "binding_callable": True,
        "binding_is_first_input": True,
        "model_outcome": "MODEL_PASS",
        "model_calls": ("bottom", "upper"),
        "from_symbols": ("bottom",),
        "model_starts": (
            "pkg.decorators",
            "pkg.bottom_effect",
            "pkg.upper_effect",
        ),
        "local_imports": (
            ("pkg.bottom_effect", "pkg.decorators"),
            ("pkg.upper_effect", "pkg.app"),
        ),
    },
    "B": {
        "error_type": None,
        "calls": (
            ("bottom", "pkg.app", "builtins.function"),
            ("upper", "pkg.decorators", "builtins.function"),
        ),
        "imports": (
            "pkg.decorators",
            "pkg.bottom_effect",
            "pkg.upper_effect",
        ),
        "loaded_effects": ("pkg.bottom_effect", "pkg.upper_effect"),
        "binding_present": True,
        "binding_type": "builtins.function",
        "binding_callable": True,
        "binding_is_first_input": True,
        "model_outcome": "MODEL_PASS",
        "model_calls": ("bottom", "upper"),
        "from_symbols": ("upper",),
        "model_starts": (
            "pkg.decorators",
            "pkg.bottom_effect",
            "pkg.upper_effect",
        ),
        "local_imports": (
            ("pkg.bottom_effect", "pkg.app"),
            ("pkg.upper_effect", "pkg.decorators"),
        ),
    },
    "C": {
        "error_type": None,
        "calls": (
            ("lower", "pkg.lower", "builtins.function"),
            ("upper", "pkg.upper", "builtins.function"),
        ),
        "imports": (
            "pkg.lower",
            "pkg.upper",
            "pkg.lower_effect",
            "pkg.upper_effect",
        ),
        "loaded_effects": ("pkg.lower_effect", "pkg.upper_effect"),
        "binding_present": True,
        "binding_type": "builtins.function",
        "binding_callable": True,
        "binding_is_first_input": True,
        "model_outcome": "MODEL_PASS",
        "model_calls": ("lower", "upper"),
        "from_symbols": ("lower", "upper"),
        "model_starts": (
            "pkg.lower",
            "pkg.upper",
            "pkg.lower_effect",
            "pkg.upper_effect",
        ),
        "local_imports": (
            ("pkg.lower_effect", "pkg.lower"),
            ("pkg.upper_effect", "pkg.upper"),
        ),
    },
    "D": {
        "error_type": None,
        "calls": (
            ("lower", "pkg.lower", "builtins.function"),
            ("upper", "pkg.upper", "builtins.function"),
        ),
        "imports": (
            "pkg.lower",
            "pkg.upper",
            "pkg.lower_effect",
            "pkg.upper_effect",
        ),
        "loaded_effects": ("pkg.lower_effect", "pkg.upper_effect"),
        "binding_present": True,
        "binding_type": "builtins.function",
        "binding_callable": True,
        "binding_is_first_input": True,
        "model_outcome": "MODEL_PASS",
        "model_calls": ("bottom_alias", "top_alias"),
        "from_symbols": ("lower", "upper"),
        "model_starts": (
            "pkg.lower",
            "pkg.upper",
            "pkg.lower_effect",
            "pkg.upper_effect",
        ),
        "local_imports": (
            ("pkg.lower_effect", "pkg.lower"),
            ("pkg.upper_effect", "pkg.upper"),
        ),
    },
    "E": {
        "error_type": None,
        "calls": (
            ("bottom", "pkg.decorators", "builtins.function"),
            ("upper", "pkg.app", "builtins.NoneType"),
        ),
        "imports": ("pkg.decorators",),
        "loaded_effects": (),
        "binding_present": True,
        "binding_type": "builtins.NoneType",
        "binding_callable": False,
        "binding_is_first_input": False,
        "model_outcome": "MODEL_PASS",
        "model_calls": ("bottom", "upper"),
        "from_symbols": ("bottom",),
        "model_starts": ("pkg.decorators",),
        "local_imports": (),
    },
    "F": {
        "error_type": "TypeError",
        "calls": (("bottom", "pkg.app", "builtins.function"),),
        "imports": ("pkg.decorators", "pkg.bottom_effect"),
        "loaded_effects": ("pkg.bottom_effect",),
        "binding_present": False,
        "binding_type": None,
        "binding_callable": False,
        "binding_is_first_input": False,
        "model_outcome": "UNKNOWN",
        "model_calls": ("bottom",),
        "from_symbols": ("upper",),
        "model_starts": ("pkg.decorators", "pkg.bottom_effect"),
        "local_imports": ("pkg.bottom_effect",),
    },
}


def _sources(case):
    sources = {"pkg.__init__": "pass\n"}
    if case == "A":
        sources.update(
            {
                "pkg.decorators": (
                    "def bottom(fn):\n"
                    "    import pkg.bottom_effect\n"
                    "    return fn\n"
                ),
                "pkg.bottom_effect": "pass\n",
                "pkg.upper_effect": "pass\n",
                "pkg.app": (
                    "from pkg.decorators import bottom\n"
                    "def upper(fn):\n"
                    "    import pkg.upper_effect\n"
                    "    return fn\n"
                    "@upper\n"
                    "@bottom\n"
                    "def f():\n"
                    "    pass\n"
                ),
            }
        )
    elif case == "B":
        sources.update(
            {
                "pkg.decorators": (
                    "def upper(fn):\n"
                    "    import pkg.upper_effect\n"
                    "    return fn\n"
                ),
                "pkg.upper_effect": "pass\n",
                "pkg.bottom_effect": "pass\n",
                "pkg.app": (
                    "from pkg.decorators import upper\n"
                    "def bottom(fn):\n"
                    "    import pkg.bottom_effect\n"
                    "    return fn\n"
                    "@upper\n"
                    "@bottom\n"
                    "def f():\n"
                    "    pass\n"
                ),
            }
        )
    elif case in {"C", "D"}:
        sources.update(
            {
                "pkg.lower": (
                    "def lower(fn):\n"
                    "    import pkg.lower_effect\n"
                    "    return fn\n"
                ),
                "pkg.upper": (
                    "def upper(fn):\n"
                    "    import pkg.upper_effect\n"
                    "    return fn\n"
                ),
                "pkg.lower_effect": "pass\n",
                "pkg.upper_effect": "pass\n",
                "pkg.app": (
                    (
                        "from pkg.lower import lower as bottom_alias\n"
                        "from pkg.upper import upper as top_alias\n"
                        "@top_alias\n"
                        "@bottom_alias\n"
                    )
                    if case == "D"
                    else (
                        "from pkg.lower import lower\n"
                        "from pkg.upper import upper\n"
                        "@upper\n"
                        "@lower\n"
                    )
                )
                + "def f():\n    pass\n",
            }
        )
    elif case == "E":
        sources.update(
            {
                "pkg.decorators": "def bottom(fn):\n    return\n",
                "pkg.app": (
                    "from pkg.decorators import bottom\n"
                    "def upper(value):\n"
                    "    return value\n"
                    "@upper\n"
                    "@bottom\n"
                    "def f():\n"
                    "    pass\n"
                ),
            }
        )
    elif case == "F":
        sources.update(
            {
                "pkg.decorators": (
                    "def upper(fn):\n"
                    "    import pkg.upper_effect\n"
                    "    return fn\n"
                ),
                "pkg.upper_effect": "pass\n",
                "pkg.bottom_effect": "pass\n",
                "pkg.app": (
                    "from pkg.decorators import upper\n"
                    "upper = None\n"
                    "def bottom(fn):\n"
                    "    import pkg.bottom_effect\n"
                    "    return fn\n"
                    "@upper\n"
                    "@bottom\n"
                    "def f():\n"
                    "    pass\n"
                ),
            }
        )
    else:
        raise AssertionError(f"unknown case: {case}")
    return sources


def _write_sources(root: Path, sources):
    for module, source in sources.items():
        parts = module.split(".")
        directory = root.joinpath(*parts[:-1])
        filename = "__init__.py" if parts[-1] == "__init__" else parts[-1] + ".py"
        directory.mkdir(parents=True, exist_ok=True)
        directory.joinpath(filename).write_text(source, encoding="utf-8")


def _cpython_reference(tmp_path, case, sources):
    _write_sources(tmp_path, sources)
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            _REFERENCE_RUNNER,
            str(tmp_path),
            json.dumps(_DECORATOR_SPECS[case]),
            json.dumps(_TRACKED_IMPORTS),
            json.dumps(_TRACKED_EFFECTS),
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


@pytest.mark.parametrize("case", ("A", "B", "C", "D", "E", "F"))
def test_cross_module_decorator_stack_cpython_and_model_baseline(tmp_path, case):
    expected = _EXPECTED[case]
    sources = _sources(case)
    observed = _cpython_reference(tmp_path, case, sources)

    assert observed["python"] == [3, 15, 2]
    assert observed["error_type"] == expected["error_type"]
    assert tuple(tuple(call) for call in observed["decorator_calls"]) == expected["calls"]
    assert tuple(observed["imports"]) == expected["imports"]
    assert set(observed["loaded_effect_modules"]) == set(expected["loaded_effects"])
    assert observed["binding_present"] is expected["binding_present"]
    assert observed["binding_type"] == expected["binding_type"]
    assert observed["binding_callable"] is expected["binding_callable"]
    assert (
        observed["binding_is_first_decorator_input"]
        is expected["binding_is_first_input"]
    )

    modeled = _model(sources)
    assert modeled.outcome == expected["model_outcome"]
    assert modeled.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    calls = _events(modeled, "CALL_FUNCTION")
    assert tuple(event.symbol for event in calls) == expected["model_calls"]
    assert tuple(event.module for event in calls) == ("pkg.app",) * len(calls)
    assert tuple(event.symbol for event in _events(modeled, "FROM")) == expected[
        "from_symbols"
    ]
    model_starts = tuple(
        event.target
        for event in _events(modeled, "START_IMPORT")
        if event.target in _TRACKED_IMPORTS
    )
    assert model_starts == expected["model_starts"]
    assert len(model_starts) == len(set(model_starts))
    local_imports = tuple(
        event
        for event in modeled.events
        if event.operation == "FUNCTION_LOCAL_IMPORT"
        and event.target in _TRACKED_EFFECTS
    )
    assert tuple(
        (event.target, event.module)
        for event in local_imports
    ) == expected["local_imports"]
    assert not any(
        event.operation == "BIND" and event.symbol == "f"
        for event in modeled.events
    )

    if case in {"A", "B", "C", "D"}:
        model_only_sources = dict(sources)
        model_only_sources["pkg.app"] += "f()\n"
        called = _model(model_only_sources)
        assert called.outcome == "MODEL_PASS"
        called_events = _events(called, "CALL_FUNCTION")
        assert tuple(event.symbol for event in called_events) == (
            *expected["model_calls"],
            "f",
        )
        assert tuple(event.module for event in called_events) == (
            "pkg.app",
        ) * len(called_events)

    elif case == "E":
        model_only_sources = dict(sources)
        model_only_sources["pkg.app"] += "f()\n"
        called = _model(model_only_sources)
        assert called.outcome == "UNKNOWN"
        assert tuple(
            event.symbol for event in _events(called, "CALL_FUNCTION")
        ) == expected["model_calls"]
        assert not any(
            event.operation == "CALL_FUNCTION" and event.symbol == "f"
            for event in called.events
        )
