"""Restricted passive class import-order regressions."""

import ast
import json
import subprocess
import sys
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


def _model(sources, entry):
    return evaluate_package_import_order(
        {
            name: ast.parse(source)
            for name, source in sources.items()
        },
        entry,
    )


def _actual(tmp_path, sources, entry):
    for module, source in sources.items():
        parts = module.split(".")
        path = tmp_path.joinpath(
            *parts[:-1],
            "__init__.py"
            if parts[-1] == "__init__"
            else parts[-1] + ".py",
        )
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            source + "\n",
            encoding="utf-8",
        )

    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            (
                "import importlib,sys;"
                "sys.path.insert(0,sys.argv[1]);"
                "importlib.import_module(sys.argv[2])"
            ),
            str(tmp_path),
            entry,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_c24_plain_class_and_docstring(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            '    """Passive class."""\n'
            "    pass"
        ),
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "C"
        for event in result.events
    )

    assert _actual(
        tmp_path, sources, "pkg.a"
    ).returncode == 0


def test_c24_constructor_body_not_executed(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class RepoGenerator:\n"
            "    def __init__(self, parent=None):\n"
            '        raise RuntimeError("not called")\n'
            "    def run(self):\n"
            "        dangerous()"
        ),
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "MODEL_PASS"

    assert not any(
        event.operation == "CALL_FUNCTION"
        for event in result.events
    )

    assert _actual(
        tmp_path, sources, "pkg.a"
    ).returncode == 0


def test_c24_passive_class_reexport(tmp_path):
    sources = {
        "pkg.__init__": (
            "from pkg.a import RepoGenerator"
        ),
        "pkg.a": (
            "class RepoGenerator:\n"
            "    def __init__(self, parent=None):\n"
            "        dangerous()"
        ),
    }

    result = _model(sources, "pkg")

    assert result.outcome == "MODEL_PASS"

    assert any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        for event in result.events
    )

    assert _actual(
        tmp_path, sources, "pkg"
    ).returncode == 0


def test_c24_class_export_binding_order_hazard(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "from pkg.b import ready\n"
            "class C:\n"
            "    pass"
        ),
        "pkg.b": (
            "from pkg.a import C\n"
            "ready = 1"
        ),
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert (
        result.target_module,
        result.symbol,
    ) == ("pkg.a", "C")

    process = _actual(tmp_path, sources, "pkg.a")

    assert process.returncode != 0
    assert "ImportError" in process.stderr


@pytest.mark.parametrize(
    ("entry", "expected", "target", "symbol"),
    [
        (
            "repo",
            "EARLY_BINDING_HAZARD",
            "repo",
            "run_repo_generator",
        ),
        ("ui", "MODEL_PASS", None, None),
    ],
)
def test_c24_synthetic_two_entry_orders(
    tmp_path, entry, expected, target, symbol
):
    sources = {
        "repo.__init__": (
            "from repo.main import run_repo_generator"
        ),
        "repo.main": (
            "from repo.filters import FilterWindow\n"
            "class RepoGenerator:\n"
            "    def __init__(self, root):\n"
            "        dangerous()\n"
            "def run_repo_generator(parent=None):\n"
            "    dangerous()"
        ),
        "repo.filters": (
            "from ui import theme\n"
            "class FilterWindow:\n"
            "    def __init__(self, parent):\n"
            "        dangerous()"
        ),
        "ui.__init__": "from ui.gui import run",
        "ui.gui": (
            "from repo import run_repo_generator\n"
            "class ContextorGUI:\n"
            "    def __init__(self, root):\n"
            "        dangerous()\n"
            "def run(*, single_instance=None):\n"
            "    dangerous()"
        ),
        "ui.theme": "ready = 1",
    }

    result = _model(sources, entry)

    assert result.outcome == expected
    assert (
        result.target_module,
        result.symbol,
    ) == (target, symbol)

    process = _actual(tmp_path, sources, entry)

    if expected == "MODEL_PASS":
        assert process.returncode == 0
    else:
        assert process.returncode != 0
        assert "ImportError" in process.stderr


def test_c24_constructor_call_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            "    pass\n"
            "C()"
        ),
    }

    assert _model(
        sources, "pkg.a"
    ).outcome == "UNKNOWN"


@pytest.mark.parametrize(
    "definition",
    [
        "class C(Base):\n    pass",
        "@decorator\nclass C:\n    pass",
        (
            "class C:\n"
            "    def method(self, x=compute()):\n"
            "        pass"
        ),
        (
            "class C:\n"
            "    def method(self, x: Unknown):\n"
            "        pass"
        ),
    ],
)
def test_c24_unsupported_class_definitions_unknown(
    definition,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": definition,
    }

    assert _model(
        sources, "pkg.a"
    ).outcome == "UNKNOWN"


def test_c24_class_body_import_executes_before_class_binding(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            "    import pkg.child"
        ),
        "pkg.child": "pass",
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "CLASS_LOCAL_IMPORT"
        and event.target == "pkg.child"
        for event in result.events
    )
    assert any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "C"
        for event in result.events
    )
    assert _actual(
        tmp_path, sources, "pkg.a"
    ).returncode == 0


def test_c24_main_guard_selected_class(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            'if __name__ != "__main__":\n'
            "    class C:\n"
            "        def __init__(self):\n"
            "            dangerous()"
        ),
    }

    assert _model(
        sources, "pkg.a"
    ).outcome == "MODEL_PASS"

    assert _actual(
        tmp_path, sources, "pkg.a"
    ).returncode == 0


def test_c24_invalid_method_body_compile_unknown(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            "    def method(self):\n"
            "        break"
        ),
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "UNKNOWN"

    process = _actual(tmp_path, sources, "pkg.a")

    assert process.returncode != 0
    assert "SyntaxError" in process.stderr


def test_c24_determinism_and_ast_immutability():
    trees = {
        "pkg.__init__": ast.parse(
            "from pkg.a import C"
        ),
        "pkg.a": ast.parse(
            "class C:\n"
            "    def __init__(self, value=None):\n"
            "        dangerous()"
        ),
    }

    before = {
        name: ast.dump(
            tree,
            include_attributes=True,
        )
        for name, tree in trees.items()
    }

    first = evaluate_package_import_order(
        trees, "pkg"
    )

    second = evaluate_package_import_order(
        trees, "pkg"
    )

    assert first == second
    assert first.outcome == "MODEL_PASS"

    assert before == {
        name: ast.dump(
            tree,
            include_attributes=True,
        )
        for name, tree in trees.items()
    }

    json.dumps(asdict(first))


@pytest.mark.parametrize(
    ("source", "extra"),
    [
        ("class Child(object): pass", {}),
        ("class Child(Exception): pass", {}),
        ("class Child(BaseException): pass", {}),
        ("class Child(ValueError): pass", {}),
        ("class Base: pass\nclass Child(Base): pass", {}),
        (
            "class Base: pass\nBaseAlias = Base\n"
            "class Child(BaseAlias): pass",
            {},
        ),
        (
            "from pkg.base import Base\nclass Child(Base): pass",
            {"pkg.base": "class Base: pass"},
        ),
        ("class Child(metaclass=type): pass", {}),
        (
            "class Base: pass\nOldBase = Base\nclass Base: pass\n"
            "class Child(OldBase): pass",
            {},
        ),
    ],
)
def test_p3_d1_proven_class_bases_match_cpython(
    tmp_path, source, extra,
):
    sources = {"pkg.__init__": "pass", "pkg.a": source, **extra}

    result = _model(sources, "pkg.a")

    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


@pytest.mark.parametrize(
    ("source", "runtime_succeeds"),
    [
        ("object = 1\nclass Child(object): pass", False),
        ("Exception = 1\nclass Child(Exception): pass", False),
        ("ValueError = 1\nclass Child(ValueError): pass", False),
        ("type = 1\nclass Child(metaclass=type): pass", False),
        ("class Child(MissingBase): pass", False),
        ("Base = 1\nclass Child(Base): pass", False),
        (
            "class Base:\n"
            "    def __init_subclass__(cls):\n"
            "        raise RuntimeError('hook')\n"
            "class Child(Base): pass",
            False,
        ),
        (
            "class Meta(type): pass\n"
            "class Child(metaclass=Meta): pass",
            True,
        ),
        (
            "class Left: pass\nclass Right: pass\n"
            "class Child(Left, Right): pass",
            True,
        ),
        (
            "class A: pass\nclass B: pass\nclass C(A, B): pass\n"
            "class D(B, A): pass\nclass E(C, D): pass",
            False,
        ),
        (
            "class MetaA(type): pass\nclass MetaB(type): pass\n"
            "class A(metaclass=MetaA): pass\n"
            "class B(metaclass=MetaB): pass\n"
            "class C(A, B): pass",
            False,
        ),
        (
            "class Proxy:\n"
            "    def __mro_entries__(self, bases):\n"
            "        return (object,)\n"
            "proxy = Proxy()\nclass Child(proxy): pass",
            True,
        ),
    ],
)
def test_p3_d1_unproven_class_mechanisms_stay_unknown(
    tmp_path, source, runtime_succeeds,
):
    sources = {"pkg.__init__": "pass", "pkg.a": source}

    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
    process = _actual(tmp_path, sources, "pkg.a")
    assert (process.returncode == 0) is runtime_succeeds


def test_p3_d1_old_alias_keeps_redefined_class_identity(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class Base:\n"
            "    def __init_subclass__(cls):\n"
            "        raise RuntimeError('old hook')\n"
            "OldBase = Base\n"
            "class Base: pass\n"
            "class Child(OldBase): pass"
        ),
    }

    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
    process = _actual(tmp_path, sources, "pkg.a")
    assert process.returncode != 0
    assert "old hook" in process.stderr


def test_p3_d1_reentrant_import_sees_class_unbound(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class Base: pass\n"
            "class Child(Base):\n"
            "    import pkg.b"
        ),
        "pkg.b": "from pkg.a import Child",
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.symbol == "Child"
    process = _actual(tmp_path, sources, "pkg.a")
    assert process.returncode != 0
    assert "ImportError" in process.stderr


@pytest.mark.parametrize("name", ["object", "Exception", "ValueError"])
def test_p3_d1_shadowed_builtin_base_is_unknown(tmp_path, name):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": f"{name} = 1\nclass Child({name}): pass",
    }

    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
    assert _actual(tmp_path, sources, "pkg.a").returncode != 0


def test_p3_d1_class_body_import_remains_supported(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "class Child(object):\n    import pkg.b",
        "pkg.b": "value = 1",
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


def test_p3_d1_conditional_dataclass_is_not_a_proven_base(tmp_path):
    source = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class Base: pass\n"
        "class Child(Base): pass"
    )
    sources = {"pkg.__init__": "pass", "pkg.a": source}
    result = evaluate_package_import_order(
        {name: ast.parse(value) for name, value in sources.items()},
        "pkg.a",
        annotation_semantics="DEFERRED",
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )

    assert result.outcome == "UNKNOWN"
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


def test_p3_d1_unknown_set_name_descriptor_stays_unknown(tmp_path):
    source = (
        "class Descriptor:\n"
        "    def __set_name__(self, owner, name):\n"
        "        raise RuntimeError('descriptor hook')\n"
        "class Subject:\n"
        "    value = Descriptor()"
    )
    sources = {"pkg.__init__": "pass", "pkg.a": source}

    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
    process = _actual(tmp_path, sources, "pkg.a")
    assert process.returncode != 0
    assert "descriptor hook" in process.stderr
