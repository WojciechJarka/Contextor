"""Restricted passive class import-order regressions."""

import ast
import json
import subprocess
import sys
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.package_model import (
    _ClassFact,
    _merge_class_mros,
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


def _actual(tmp_path, sources, entry, probe=""):
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
                "m=importlib.import_module(sys.argv[2]);"
                + probe
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


@pytest.mark.parametrize(
    ("name", "terminal_error"),
    [
        ("__slots__", "TypeError: 'function' object is not iterable"),
        (
            "__qualname__",
            "TypeError: type __qualname__ must be a str, not function",
        ),
        (
            "__classcell__",
            "TypeError: __classcell__ must be a nonlocal cell, "
            "not <class 'function'>",
        ),
    ],
)
def test_p3_d1f_type_new_reserved_method_names_are_unknown(
    tmp_path, name, terminal_error,
):
    class_name = {
        "__slots__": "A",
        "__qualname__": "B",
        "__classcell__": "C",
    }[name]
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            f"class {class_name}:\n"
            f"    def {name}(self):\n"
            "        pass"
        ),
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "UNKNOWN"
    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == class_name
        for event in result.events
    )

    process = _actual(tmp_path, sources, "pkg.a")

    assert process.returncode != 0
    assert terminal_error in process.stderr


def test_p3_d1f_reserved_method_name_cycle_does_not_export_class(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class A:\n"
            "    def __slots__(self):\n"
            "        pass\n"
            "from pkg.b import B"
        ),
        "pkg.b": "from pkg.a import A\nclass B: pass",
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "UNKNOWN"
    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "A"
        for event in result.events
    )
    assert not any(
        event.operation == "FROM"
        and event.module == "pkg.b"
        and event.symbol == "A"
        for event in result.events
    )

    process = _actual(tmp_path, sources, "pkg.a")

    assert process.returncode != 0
    assert "TypeError: 'function' object is not iterable" in process.stderr


@pytest.mark.parametrize(
    ("method", "body"),
    [("__init__", "pass"), ("__repr__", 'return "C"')],
)
def test_p3_d1f_regular_dunder_methods_remain_passive(
    tmp_path, method, body,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            f"    def {method}(self):\n"
            f"        {body}"
        ),
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "C"
        for event in result.events
    )
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


@pytest.mark.parametrize(
    ("entry", "source", "extra", "class_symbol"),
    [
        (
            "pkg.a",
            "class Left: pass\nclass Right: pass\n"
            "class Child(Left, Right): pass",
            {},
            "Child",
        ),
        (
            "pkg.a",
            "class Left: pass\nclass Right: pass\n"
            "class Child(Left, Right, metaclass=type): pass",
            {},
            "Child",
        ),
        (
            "pkg.a",
            "class First: pass\nclass Second: pass\n"
            "class Third: pass\n"
            "class Child(First, Second, Third): pass",
            {},
            "Child",
        ),
        (
            "pkg.a",
            "class Root: pass\nclass Left(Root): pass\n"
            "class Right(Root): pass\n"
            "class Diamond(Left, Right): pass",
            {},
            "Diamond",
        ),
        (
            "pkg.a",
            "class First: pass\nclass Second: pass\n"
            "AliasFirst = First\nAliasSecond = Second\n"
            "class Child(AliasFirst, AliasSecond): pass",
            {},
            "Child",
        ),
        (
            "pkg.use",
            "from pkg.base import First, Second\n"
            "class Child(First, Second): pass",
            {"pkg.base": "class First: pass\nclass Second: pass"},
            "Child",
        ),
        (
            "pkg.a",
            "class Base: pass\nclass Child(Base, object): pass",
            {},
            "Child",
        ),
        (
            "pkg.a",
            "class Base: pass\nOldBase = Base\n"
            "class Base: pass\nclass Child(OldBase, Base): pass",
            {},
            "Child",
        ),
        (
            "pkg.a",
            "class Left: pass\nfrom pkg.b import Right\n"
            "class Child(Left, Right): pass",
            {
                "pkg.b": (
                    "from pkg.a import Left\nclass Right: pass"
                ),
            },
            "Child",
        ),
    ],
)
def test_p3_d2_supported_multiple_inheritance_matches_cpython(
    tmp_path, entry, source, extra, class_symbol,
):
    sources = {"pkg.__init__": "pass", entry: source, **extra}

    result = _model(sources, entry)

    assert result.outcome == "MODEL_PASS"
    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == class_symbol
        for event in result.events
    )
    assert _actual(tmp_path, sources, entry).returncode == 0


@pytest.mark.parametrize(
    ("source", "extra", "failed_class", "runtime_error"),
    [
        (
            "class Base: pass\nclass Child(Base): pass\n"
            "class Broken(object, Child): pass",
            {},
            "Broken",
            None,
        ),
        (
            "class Base: pass\nAlias = Base\n"
            "class Broken(Base, Alias): pass",
            {},
            "Broken",
            None,
        ),
        (
            "from pkg.base import Base as Left\n"
            "from pkg.base import Base as Right\n"
            "class Broken(Left, Right): pass",
            {"pkg.base": "class Base: pass"},
            "Broken",
            None,
        ),
        (
            "class Root: pass\nclass Left(Root): pass\n"
            "class Right(Root): pass\n"
            "class First(Left, Right): pass\n"
            "class Second(Right, Left): pass\n"
            "class Broken(First, Second): pass",
            {},
            "Broken",
            None,
        ),
        (
            "Base = 7\nclass Broken(Base, object): pass",
            {},
            "Broken",
            None,
        ),
        (
            "class Broken(SyntaxError, OSError): pass",
            {},
            "Broken",
            "multiple bases have instance lay-out conflict",
        ),
    ],
)
def test_p3_d2_unproven_or_invalid_multiple_inheritance_stays_unknown(
    tmp_path, source, extra, failed_class, runtime_error,
):
    sources = {"pkg.__init__": "pass", "pkg.a": source, **extra}

    result = _model(sources, "pkg.a")

    assert result.outcome == "UNKNOWN"
    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == failed_class
        for event in result.events
    )

    process = _actual(tmp_path, sources, "pkg.a")
    assert process.returncode != 0
    if runtime_error is not None:
        assert runtime_error in process.stderr


def test_p3_d2_multiple_exception_bases_remain_conservatively_unknown(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "class CustomError(ValueError, Exception): pass",
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "UNKNOWN"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS"
        and event.symbol == "CustomError"
        for event in result.events
    )
    assert _actual(tmp_path, sources, "pkg.a").returncode == 0


def test_p3_d2_c3_merge_preserves_order_and_common_ancestor():
    object_fact = _ClassFact(
        identity="builtins.object",
        origin="BUILTIN",
        direct_bases=(),
        linear_mro=("builtins.object",),
        metaclass_identity="builtins.type",
        defines_init_subclass=False,
        safe_to_subclass=True,
    )
    root = _ClassFact(
        identity="pkg.root:1:0",
        origin="INDEXED_SOURCE",
        direct_bases=("builtins.object",),
        linear_mro=("pkg.root:1:0", "builtins.object"),
        metaclass_identity="builtins.type",
        defines_init_subclass=False,
        safe_to_subclass=True,
    )
    left_identity = "pkg.left:1:0"
    left = _ClassFact(
        identity=left_identity,
        origin="INDEXED_SOURCE",
        direct_bases=(root.identity,),
        linear_mro=(left_identity, root.identity, "builtins.object"),
        metaclass_identity="builtins.type",
        defines_init_subclass=False,
        safe_to_subclass=True,
    )
    right = _ClassFact(
        identity="pkg.right:1:0",
        origin="INDEXED_SOURCE",
        direct_bases=(root.identity,),
        linear_mro=("pkg.right:1:0", root.identity, "builtins.object"),
        metaclass_identity="builtins.type",
        defines_init_subclass=False,
        safe_to_subclass=True,
    )

    assert _merge_class_mros((left, right)) == (
        left.identity,
        right.identity,
        root.identity,
        "builtins.object",
    )
    assert _merge_class_mros((root, object_fact)) == (
        root.identity,
        "builtins.object",
    )


def test_p3_d2_c3_merge_rejects_conflicting_parent_order():
    first = _ClassFact(
        identity="pkg.first:1:0",
        origin="INDEXED_SOURCE",
        direct_bases=("builtins.object",),
        linear_mro=("pkg.first:1:0", "builtins.object"),
        metaclass_identity="builtins.type",
        defines_init_subclass=False,
        safe_to_subclass=True,
    )
    second = _ClassFact(
        identity="pkg.second:1:0",
        origin="INDEXED_SOURCE",
        direct_bases=("builtins.object",),
        linear_mro=("pkg.second:1:0", "builtins.object"),
        metaclass_identity="builtins.type",
        defines_init_subclass=False,
        safe_to_subclass=True,
    )
    left_order = _ClassFact(
        identity="pkg.left_order:1:0",
        origin="INDEXED_SOURCE",
        direct_bases=(first.identity, second.identity),
        linear_mro=(
            "pkg.left_order:1:0",
            first.identity,
            second.identity,
            "builtins.object",
        ),
        metaclass_identity="builtins.type",
        defines_init_subclass=False,
        safe_to_subclass=True,
    )
    right_order = _ClassFact(
        identity="pkg.right_order:1:0",
        origin="INDEXED_SOURCE",
        direct_bases=(second.identity, first.identity),
        linear_mro=(
            "pkg.right_order:1:0",
            second.identity,
            first.identity,
            "builtins.object",
        ),
        metaclass_identity="builtins.type",
        defines_init_subclass=False,
        safe_to_subclass=True,
    )

    assert _merge_class_mros((left_order, right_order)) is None


@pytest.mark.parametrize(
    ("source", "extra", "probe"),
    [
        ("class Meta(type): pass", {}, "assert type(m.Meta) is type;assert m.Meta.__mro__==(m.Meta,type,object)"),
        ("class Meta(type): pass\nclass C(metaclass=Meta): pass", {}, "assert type(m.C) is m.Meta;assert m.C.__mro__==(m.C,object)"),
        ("class Meta(type): pass\nclass C(metaclass=Meta): pass\nclass D(C): pass", {}, "assert type(m.D) is m.Meta;assert m.D.__mro__==(m.D,m.C,object)"),
        ("class Meta(type): pass\nclass N(Meta): pass", {}, "assert m.N.__mro__==(m.N,m.Meta,type,object)"),
        ("class Meta(type): pass\nclass N(Meta): pass\nclass C(metaclass=N): pass", {}, "assert type(m.C) is m.N"),
        ("class Meta(type): pass\nAlias=Meta\nclass C(metaclass=Alias): pass", {}, "assert type(m.C) is m.Meta"),
        ("from pkg.meta import Meta\nclass C(metaclass=Meta): pass", {"pkg.meta": "class Meta(type): pass"}, "assert type(m.C) is __import__('pkg.meta',fromlist=['Meta']).Meta"),
        ("class Meta(type): pass\nOld=Meta\nclass Meta(type): pass\nclass C(metaclass=Old): pass", {}, "assert type(m.C) is m.Old and m.Old is not m.Meta"),
        ("class Meta(type): pass\nclass A(metaclass=Meta): pass\nclass C(A,metaclass=type): pass", {}, "assert type(m.C) is m.Meta"),
        ("class Meta(type): pass\nclass A(metaclass=Meta): pass\nclass B(metaclass=Meta): pass\nclass C(A,B): pass", {}, "assert type(m.C) is m.Meta;assert m.C.__mro__==(m.C,m.A,m.B,object)"),
        ("class Meta(type): pass\nclass N(Meta): pass\nclass A(metaclass=Meta): pass\nclass B(metaclass=N): pass\nclass C(A,B): pass", {}, "assert type(m.C) is m.N"),
        ("class Meta(type): pass\nclass A(metaclass=Meta): pass\nclass C(A,metaclass=Meta): pass", {}, "assert type(m.C) is m.Meta"),
    ],
)
def test_p3_d3_semantic_metaclass_selection(tmp_path, source, extra, probe):
    sources = {"pkg.__init__": "pass", "pkg.a": source, **extra}
    result = _model(sources, "pkg.a")
    assert result.outcome == "MODEL_PASS", result
    actual = _actual(tmp_path, sources, "pkg.a", probe)
    assert actual.returncode == 0, actual.stderr


@pytest.mark.parametrize(
    "body",
    [
        "def __prepare__(cls,*args): return {}",
        "def __new__(cls,*args): return super().__new__(cls,*args)",
        "def __init__(cls,*args): pass",
        "def __call__(cls,*args): return super().__call__(*args)",
        "def __getattribute__(cls,name): return super().__getattribute__(name)",
        "def method(cls): pass",
        "flag = 1",
    ],
)
def test_p3_d3_unproved_metaclass_effects_are_unknown(body):
    source = "class Meta(type):\n    " + body.replace("\n", "\n    ") + "\nclass C(metaclass=Meta): pass"
    result = _model({"pkg.__init__": "pass", "pkg.a": source}, "pkg.a")
    assert result.outcome == "UNKNOWN"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS" and event.symbol == "C"
        for event in result.events
    )


def test_p3_d3_reentrant_before_class_binding(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class Meta(type): pass\n"
            "class C(metaclass=Meta):\n"
            "    from pkg.b import Seen"
        ),
        "pkg.b": "from pkg.a import C as Seen",
    }
    modeled = _model(sources, "pkg.a")
    assert modeled.outcome == "EARLY_BINDING_HAZARD"
    assert not any(
        event.operation == "DEFINE_PASSIVE_CLASS" and event.symbol == "C"
        for event in modeled.events
    )
    actual = _actual(tmp_path, sources, "pkg.a")
    assert actual.returncode != 0
    assert "cannot import name 'C'" in actual.stderr


def test_p3_d3_import_after_class_binding(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class Meta(type): pass\n"
            "class C(metaclass=Meta): pass\n"
            "from pkg.b import Seen"
        ),
        "pkg.b": "from pkg.a import C as Seen",
    }
    modeled = _model(sources, "pkg.a")
    assert modeled.outcome == "MODEL_PASS"
    assert [
        event.operation for event in modeled.events
        if event.operation == "DEFINE_PASSIVE_CLASS"
    ] == ["DEFINE_PASSIVE_CLASS", "DEFINE_PASSIVE_CLASS"]
    actual = _actual(
        tmp_path, sources, "pkg.a",
        "assert m.Seen is m.C;assert type(m.C) is m.Meta",
    )
    assert actual.returncode == 0, actual.stderr


@pytest.mark.parametrize(
    "entry,expected",
    [
        ("pkg.a", "EARLY_BINDING_HAZARD"),
        ("pkg.b", "MODEL_PASS"),
    ],
)
def test_k09_a_class_name_bound_after_body(tmp_path, entry, expected):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "class C:\n    import pkg.b",
        "pkg.b": "from pkg.a import C",
    }

    result = _model(sources, entry)
    actual = _actual(tmp_path, sources, entry)

    assert result.outcome == expected

    if expected == "EARLY_BINDING_HAZARD":
        assert (result.target_module, result.symbol) == ("pkg.a", "C")
        assert actual.returncode != 0
        assert "ImportError" in actual.stderr
        assert not any(
            e.operation == "DEFINE_PASSIVE_CLASS"
            and e.module == "pkg.a"
            and e.symbol == "C"
            for e in result.events
        )
    else:
        assert actual.returncode == 0, actual.stderr
        operations = [
            e.operation for e in result.events
            if e.module == "pkg.a"
        ]
        assert operations.index("CLASS_LOCAL_IMPORT") < (
            operations.index("DEFINE_PASSIVE_CLASS")
        )


@pytest.mark.parametrize(
    "entry,expected",
    [
        ("pkg.a", "EARLY_BINDING_HAZARD"),
        ("pkg.b", "MODEL_PASS"),
    ],
)
def test_k09_b_module_binding_after_class(tmp_path, entry, expected):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            "    import pkg.b\n"
            "value = 1"
        ),
        "pkg.b": "from pkg.a import value",
    }

    result = _model(sources, entry)
    actual = _actual(tmp_path, sources, entry)

    assert result.outcome == expected

    if expected == "EARLY_BINDING_HAZARD":
        assert (result.target_module, result.symbol) == (
            "pkg.a", "value"
        )
        assert actual.returncode != 0
        assert "ImportError" in actual.stderr
    else:
        assert actual.returncode == 0, actual.stderr
        assert any(
            e.operation == "CLASS_LOCAL_IMPORT"
            and e.target == "pkg.b"
            for e in result.events
        )


@pytest.mark.parametrize(
    "entry,expected",
    [
        ("pkg.a", "EARLY_BINDING_HAZARD"),
        ("pkg.b", "MISSING_EXPORT"),
    ],
)
def test_k09_c_class_local_alias_does_not_escape(
    tmp_path, entry, expected
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            "    import pkg.c as inside\n"
            "    import pkg.b"
        ),
        "pkg.b": "from pkg.a import inside",
        "pkg.c": "pass",
    }

    result = _model(sources, entry)
    actual = _actual(tmp_path, sources, entry)

    assert result.outcome == expected
    assert (result.target_module, result.symbol) == (
        "pkg.a", "inside"
    )
    assert actual.returncode != 0
    assert "ImportError" in actual.stderr

    assert not any(
        e.module == "pkg.a"
        and e.operation in {"BIND", "ALIAS"}
        and e.symbol == "inside"
        for e in result.events
    )


@pytest.mark.parametrize(
    "entry,expected",
    [
        ("pkg.a", "EARLY_BINDING_HAZARD"),
        ("pkg.b", "MISSING_EXPORT"),
    ],
)
def test_k09_d_class_local_assignment_does_not_escape(
    tmp_path, entry, expected
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            "    local = 1\n"
            "    import pkg.b"
        ),
        "pkg.b": "from pkg.a import local",
    }

    result = _model(sources, entry)
    actual = _actual(tmp_path, sources, entry)

    assert result.outcome == expected
    assert (result.target_module, result.symbol) == (
        "pkg.a", "local"
    )
    assert actual.returncode != 0
    assert "ImportError" in actual.stderr

    assert any(
        e.module == "pkg.a"
        and e.operation == "CLASS_LOCAL_BIND"
        and e.symbol == "local"
        for e in result.events
    )
    assert not any(
        e.module == "pkg.a"
        and e.operation == "BIND"
        and e.symbol == "local"
        for e in result.events
    )


def test_k09_e_class_local_from_is_not_module_export(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": "class C:\n    from pkg.b import token",
        "pkg.b": "token = 1",
        "pkg.c": "from pkg.a import token",
    }

    result = _model(sources, "pkg.c")
    actual = _actual(tmp_path, sources, "pkg.c")

    assert result.outcome == "MISSING_EXPORT"
    assert (result.target_module, result.symbol) == (
        "pkg.a", "token"
    )
    assert actual.returncode != 0
    assert "ImportError" in actual.stderr

    events = result.events
    class_from = next(
        i for i, e in enumerate(events)
        if e.module == "pkg.a"
        and e.operation == "CLASS_LOCAL_FROM"
        and e.target == "pkg.b"
        and e.symbol == "token"
    )
    missing = next(
        i for i, e in enumerate(events)
        if e.operation == "MISSING_EXPORT"
        and e.target == "pkg.a"
        and e.symbol == "token"
    )
    assert class_from < missing


def test_k09_f_method_body_import_is_deferred(tmp_path):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "class C:\n"
            "    def later(self):\n"
            "        import pkg.b\n"
            "value = 1"
        ),
        "pkg.b": "from pkg.a import value",
    }

    result = _model(sources, "pkg.a")
    actual = _actual(tmp_path, sources, "pkg.a")

    assert result.outcome == "MODEL_PASS"
    assert actual.returncode == 0, actual.stderr

    assert not any(
        e.operation == "START_IMPORT"
        and e.target == "pkg.b"
        for e in result.events
    )


@pytest.mark.parametrize(
    "body",
    [
        'class C:\n    exec("import pkg.b")',
        "class C(factory()):\n    import pkg.b",
        "@decorator\nclass C:\n    import pkg.b",
    ],
)
def test_k09_g_unmodeled_class_effects_fail_closed(body):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": body,
        "pkg.b": "pass",
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "UNKNOWN"
    assert result.outcome != "MODEL_PASS"


def test_k09_h_deterministic_without_ast_mutation():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse(
            "class C:\n"
            "    import pkg.b"
        ),
        "pkg.b": ast.parse("from pkg.a import C"),
    }

    before = {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in sources.items()
    }

    first = evaluate_package_import_order(sources, "pkg.a")
    second = evaluate_package_import_order(sources, "pkg.a")

    assert first == second
    assert first.events == second.events
    assert first.outcome == "EARLY_BINDING_HAZARD"

    after = {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in sources.items()
    }
    assert after == before
