"""CPython references for imported class decorators and model boundaries."""

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
import importlib
import json
import sys

sys.path.insert(0, sys.argv[1])
specs = {
    (item["module"], item["name"]): item
    for item in json.loads(sys.argv[2])
}
calls = []
active_calls = {}
first_decorator_input = {"seen": False, "value": None}

def type_name(value):
    value_type = type(value)
    return value_type.__module__ + "." + value_type.__qualname__

def trace_calls(frame, event, arg):
    key = (frame.f_globals.get("__name__"), frame.f_code.co_name)
    spec = specs.get(key)
    if spec is None:
        return trace_calls

    if event == "call":
        value = frame.f_locals.get(spec["parameter"])
        record = {
            "name": spec["name"],
            "module": spec["module"],
            "role": spec["role"],
            "input_type": type_name(value),
            "return_type": None,
            "returned_input": None,
            "_input": value,
        }
        calls.append(record)
        active_calls[id(frame)] = record
        if spec["role"] == "decorator" and not first_decorator_input["seen"]:
            first_decorator_input["seen"] = True
            first_decorator_input["value"] = value
    elif event == "return":
        record = active_calls.pop(id(frame), None)
        if record is not None:
            record["return_type"] = type_name(arg)
            record["returned_input"] = arg is record["_input"]
            del record["_input"]
    return trace_calls

error_type = None
app = None
sys.settrace(trace_calls)
try:
    app = importlib.import_module("pkg.app")
except BaseException as exc:
    error_type = type(exc).__name__
    app = sys.modules.get("pkg.app")
finally:
    sys.settrace(None)

binding_present = app is not None and "C" in app.__dict__
value = app.__dict__.get("C") if binding_present else None
subclass = None
if app is not None and "Child" in app.__dict__:
    child = app.__dict__["Child"]
    if binding_present and isinstance(value, type) and isinstance(child, type):
        instance = child()
        subclass = {
            "present": True,
            "is_class": True,
            "issubclass": issubclass(child, value),
            "instantiable_as_base": isinstance(instance, value),
        }
    else:
        subclass = {
            "present": True,
            "is_class": isinstance(child, type),
            "issubclass": False,
            "instantiable_as_base": False,
        }

decorator_calls = [item for item in calls if item["role"] == "decorator"]
helper_calls = [item for item in calls if item["role"] == "helper"]
for item in calls:
    item.pop("role", None)
effect_modules = [
    name
    for name, module in sys.modules.items()
    if name.startswith("pkg.")
    and getattr(module, "__contextor_effect__", False)
]
print(json.dumps({
    "python": list(sys.version_info[:3]),
    "import_succeeded": error_type is None,
    "error_type": error_type,
    "decorator_calls": decorator_calls,
    "helper_calls": helper_calls,
    "effect_modules": effect_modules,
    "binding_present": binding_present,
    "binding_type": type_name(value) if binding_present else None,
    "is_class": binding_present and isinstance(value, type),
    "final_same_as_first_decorator_input": (
        value is first_decorator_input["value"]
        if binding_present and first_decorator_input["seen"]
        else None
    ),
    "subclass": subclass,
}))
"""


def _spec(name, module, role="decorator"):
    return {
        "name": name,
        "module": module,
        "parameter": "cls",
        "role": role,
    }


def _call(name, module, *, input_type="builtins.type", return_type="builtins.type", returned_input=True):
    return (name, module, input_type, return_type, returned_input)


def _reference(
    *,
    error_type=None,
    decorator_calls=(),
    helper_calls=(),
    effect_modules=(),
    binding_present=True,
    binding_type="builtins.type",
    is_class=True,
    same_as_input=True,
    subclass=None,
):
    return {
        "import_succeeded": error_type is None,
        "error_type": error_type,
        "decorator_calls": decorator_calls,
        "helper_calls": helper_calls,
        "effect_modules": effect_modules,
        "binding_present": binding_present,
        "binding_type": binding_type,
        "is_class": is_class,
        "same_as_input": same_as_input,
        "subclass": subclass,
    }


_UNKNOWN_COMPILE_REJECTION = {
    "outcome": "UNKNOWN",
    "target_module": "pkg.app",
    "symbol": None,
    "evidence_scope": "RESTRICTED_REGULAR_PACKAGE_MODEL",
    "events": (),
}

_LOCAL_IDENTITY_EVENTS = (
    ("\x00ENTRY", "START_IMPORT", "pkg", None),
    ("pkg", "READY", None, None),
    ("\x00ENTRY", "START_IMPORT", "pkg.app", None),
    ("pkg.app", "DEFINE_FUNCTION", None, "identity"),
    ("pkg.app", "DEFINE_PASSIVE_CLASS", None, "C"),
    ("pkg.app", "CALL_FUNCTION", None, "identity"),
    ("pkg.app", "READY", None, None),
    ("pkg", "BIND_CHILD", "pkg.app", "app"),
)


CASES = [
    {
        "id": "A-imported-identity",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.decorators": "def identity(cls):\n    return cls\n",
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\nclass C:\n    pass\n"
            ),
        },
        "specs": [_spec("identity", "pkg.decorators")],
        "reference": _reference(
            decorator_calls=(_call("identity", "pkg.decorators"),),
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "B-imported-identity-alias",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.decorators": "def identity(cls):\n    return cls\n",
            "pkg.app": (
                "from pkg.decorators import identity as alias\n"
                "@alias\nclass C:\n    pass\n"
            ),
        },
        "specs": [_spec("identity", "pkg.decorators")],
        "reference": _reference(
            decorator_calls=(_call("identity", "pkg.decorators"),),
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "C-imported-decorator-effect",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.decorators": (
                "def decorate(cls):\n"
                "    import pkg.effect\n"
                "    return cls\n"
            ),
            "pkg.effect": "__contextor_effect__ = True\n",
            "pkg.app": (
                "from pkg.decorators import decorate\n"
                "@decorate\nclass C:\n    pass\n"
            ),
        },
        "specs": [_spec("decorate", "pkg.decorators")],
        "reference": _reference(
            decorator_calls=(_call("decorate", "pkg.decorators"),),
            effect_modules=("pkg.effect",),
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "D-imported-decorator-returns-none",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.decorators": "def replace(cls):\n    return\n",
            "pkg.app": (
                "from pkg.decorators import replace\n"
                "@replace\nclass C:\n    pass\n"
            ),
        },
        "specs": [_spec("replace", "pkg.decorators")],
        "reference": _reference(
            decorator_calls=(
                _call(
                    "replace",
                    "pkg.decorators",
                    return_type="builtins.NoneType",
                    returned_input=False,
                ),
            ),
            binding_type="builtins.NoneType",
            is_class=False,
            same_as_input=False,
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "E-imported-decorator-nested-call",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.decorators": (
                "def factory(cls):\n"
                "    return cls\n"
                "def decorate(cls):\n"
                "    return factory(cls)\n"
            ),
            "pkg.app": (
                "from pkg.decorators import decorate\n"
                "@decorate\nclass C:\n    pass\n"
            ),
        },
        "specs": [
            _spec("decorate", "pkg.decorators"),
            _spec("factory", "pkg.decorators", role="helper"),
        ],
        "reference": _reference(
            decorator_calls=(_call("decorate", "pkg.decorators"),),
            helper_calls=(_call("factory", "pkg.decorators"),),
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "F-imported-decorator-rebound-to-none",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.decorators": "def identity(cls):\n    return cls\n",
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "identity = None\n"
                "@identity\nclass C:\n    pass\n"
            ),
        },
        "specs": [_spec("identity", "pkg.decorators")],
        "reference": _reference(
            error_type="TypeError",
            decorator_calls=(),
            binding_present=False,
            binding_type=None,
            is_class=False,
            same_as_input=None,
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "G-local-bottom-imported-upper",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.upper": "def upper(cls):\n    return cls\n",
            "pkg.app": (
                "def bottom(cls):\n    return cls\n"
                "from pkg.upper import upper\n"
                "@upper\n@bottom\nclass C:\n    pass\n"
            ),
        },
        "specs": [
            _spec("bottom", "pkg.app"),
            _spec("upper", "pkg.upper"),
        ],
        "reference": _reference(
            decorator_calls=(
                _call("bottom", "pkg.app"),
                _call("upper", "pkg.upper"),
            ),
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "H-imported-decorators-distinct-modules",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.lower": "def lower(cls):\n    return cls\n",
            "pkg.upper": "def upper(cls):\n    return cls\n",
            "pkg.app": (
                "from pkg.lower import lower\n"
                "from pkg.upper import upper\n"
                "@upper\n@lower\nclass C:\n    pass\n"
            ),
        },
        "specs": [
            _spec("lower", "pkg.lower"),
            _spec("upper", "pkg.upper"),
        ],
        "reference": _reference(
            decorator_calls=(
                _call("lower", "pkg.lower"),
                _call("upper", "pkg.upper"),
            ),
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "I-imported-identity-then-subclass",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.decorators": "def identity(cls):\n    return cls\n",
            "pkg.app": (
                "from pkg.decorators import identity\n"
                "@identity\nclass C:\n    pass\n"
                "class Child(C):\n    pass\n"
            ),
        },
        "specs": [_spec("identity", "pkg.decorators")],
        "reference": _reference(
            decorator_calls=(_call("identity", "pkg.decorators"),),
            subclass={
                "present": True,
                "is_class": True,
                "issubclass": True,
                "instantiable_as_base": True,
            },
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "J-relative-import-in-defining-package",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.decorators.__init__": (
                "def decorate(cls):\n"
                "    from . import effect\n"
                "    return cls\n"
            ),
            "pkg.decorators.effect": "__contextor_effect__ = True\n",
            "pkg.effect": "__contextor_effect__ = True\n",
            "pkg.app": (
                "from pkg.decorators import decorate\n"
                "@decorate\nclass C:\n    pass\n"
            ),
        },
        "specs": [_spec("decorate", "pkg.decorators")],
        "reference": _reference(
            decorator_calls=(_call("decorate", "pkg.decorators"),),
            effect_modules=("pkg.decorators.effect",),
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
    {
        "id": "K-local-identity",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.app": (
                "def identity(cls):\n    return cls\n"
                "@identity\nclass C:\n    pass\n"
            ),
        },
        "specs": [_spec("identity", "pkg.app")],
        "reference": _reference(
            decorator_calls=(_call("identity", "pkg.app"),),
        ),
        "model": {
            "outcome": "MODEL_PASS",
            "target_module": None,
            "symbol": None,
            "evidence_scope": "RESTRICTED_REGULAR_PACKAGE_MODEL",
            "events": _LOCAL_IDENTITY_EVENTS,
        },
    },
    {
        "id": "L-external-dataclass-decorator",
        "sources": {
            "pkg.__init__": "pass\n",
            "pkg.app": (
                "from dataclasses import dataclass\n"
                "@dataclass\nclass C:\n    pass\n"
            ),
        },
        "specs": [_spec("dataclass", "dataclasses")],
        "reference": _reference(
            decorator_calls=(_call("dataclass", "dataclasses"),),
        ),
        "model": _UNKNOWN_COMPILE_REJECTION,
    },
]


def _write_sources(root: Path, sources: dict[str, str]) -> None:
    for module, source in sources.items():
        parts = module.split(".")
        directory = root.joinpath(*parts[:-1])
        filename = "__init__.py" if parts[-1] == "__init__" else parts[-1] + ".py"
        directory.mkdir(parents=True, exist_ok=True)
        directory.joinpath(filename).write_text(source, encoding="utf-8")


def _cpython_reference(tmp_path: Path, case: dict) -> dict:
    _write_sources(tmp_path, case["sources"])
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            _REFERENCE_RUNNER,
            str(tmp_path),
            json.dumps(case["specs"]),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _model_record(case: dict) -> dict:
    modeled = evaluate_package_import_order(
        {
            module: ast.parse(source)
            for module, source in case["sources"].items()
        },
        "pkg.app",
    )
    return {
        "outcome": modeled.outcome,
        "target_module": modeled.target_module,
        "symbol": modeled.symbol,
        "evidence_scope": modeled.evidence_scope,
        "events": tuple(
            (event.module, event.operation, event.target, event.symbol)
            for event in modeled.events
        ),
    }


def _call_shape(call: dict) -> tuple:
    return (
        call["name"],
        call["module"],
        call["input_type"],
        call["return_type"],
        call["returned_input"],
    )


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_cross_module_class_decorator_baseline(tmp_path: Path, case: dict):
    observed = _cpython_reference(tmp_path, case)
    assert tuple(observed["python"]) == tuple(sys.version_info[:3])
    assert tuple(observed["python"]) == (3, 15, 2)

    actual_reference = {
        "import_succeeded": observed["import_succeeded"],
        "error_type": observed["error_type"],
        "decorator_calls": tuple(
            _call_shape(call) for call in observed["decorator_calls"]
        ),
        "helper_calls": tuple(
            _call_shape(call) for call in observed["helper_calls"]
        ),
        "effect_modules": tuple(observed["effect_modules"]),
        "binding_present": observed["binding_present"],
        "binding_type": observed["binding_type"],
        "is_class": observed["is_class"],
        "same_as_input": observed["final_same_as_first_decorator_input"],
        "subclass": observed["subclass"],
    }
    assert actual_reference == case["reference"], (
        case["id"],
        actual_reference,
    )

    actual_model = _model_record(case)
    assert actual_model == case["model"], (case["id"], actual_model)
