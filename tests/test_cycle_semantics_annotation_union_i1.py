"""CPython 3.15 union operator and restricted annotation model parity."""

import ast
import os
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.execution.annotation_effects import (
    _Alias,
    _BuiltinUnionOr,
    _Class,
    _Module,
    _Scalar,
    _Seq,
    _Type,
    _TypeUnion,
    _construct_union,
    _eval,
    _proven_key,
)
from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


pytestmark = pytest.mark.skipif(
    sys.version_info[:2] != (3, 15),
    reason="CPython 3.15 annotation consumption contract",
)


def _source(annotation, prelude=""):
    return (
        prelude
        + "from dataclasses import dataclass\n"
        + "@dataclass(frozen=True)\n"
        + "class C:\n"
        + f"    x: {annotation}\n"
    )


def _model(source):
    tree = ast.parse(source)
    before = ast.dump(tree)
    options = dict(
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )
    first = evaluate_package_import_order(
        {"pkg.__init__": tree}, "pkg", **options,
    )
    second = evaluate_package_import_order(
        {"pkg.__init__": tree}, "pkg", **options,
    )
    assert first == second
    assert ast.dump(tree) == before
    assert first.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )
    return first


def _runtime(tmp_path, source):
    package = tmp_path / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code = (
        "try:\n"
        " import pkg\n"
        " print('FIELD', repr(pkg.C.__dataclass_fields__['x'].type))\n"
        " print('RESULT OK')\n"
        "except BaseException as error:\n"
        " print('RESULT', type(error).__name__, str(error))\n"
    )
    process = subprocess.run(
        [sys.executable, "-u", "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    return process.stdout.splitlines()


@pytest.mark.parametrize("annotation", [
    "None | None",
    "(None | None) | int",
    "None | (None | None)",
])
def test_none_without_union_slot_stays_unknown(
    tmp_path, annotation,
):
    assert _eval(ast.parse(annotation, mode="eval").body, {}, {}, {}) is None
    result = _model(_source(annotation))
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert all(
        event.operation != "ASSUMED_FROZEN_DATACLASS_DECORATION"
        for event in result.events
    )
    assert _runtime(tmp_path, _source(annotation))[-1].startswith(
        "RESULT TypeError unsupported operand type(s) for |:"
    )


@pytest.mark.parametrize("annotation,expected,field_type", [
    ("int | int", _Type("builtins.int", False), "<class 'int'>"),
    ("list[int] | list[int]", _Alias(_Type("builtins.list", True), (_Type("builtins.int", False),)), "list[int]"),
    ("int | None", _TypeUnion((_Type("builtins.int", False), _Type("builtins.NoneType", False))), "int | None"),
    ("None | int", _TypeUnion((_Type("builtins.NoneType", False), _Type("builtins.int", False))), "None | int"),
    ("int | None | None", _TypeUnion((_Type("builtins.int", False), _Type("builtins.NoneType", False))), "int | None"),
    ("int | str | int", _TypeUnion((_Type("builtins.int", False), _Type("builtins.str", False))), "int | str"),
    ("(int | str) | (str | None)", _TypeUnion((_Type("builtins.int", False), _Type("builtins.str", False), _Type("builtins.NoneType", False))), "int | str | None"),
    ("list[int] | list[str]", _TypeUnion((_Alias(_Type("builtins.list", True), (_Type("builtins.int", False),)), _Alias(_Type("builtins.list", True), (_Type("builtins.str", False),)))), "list[int] | list[str]"),
    ("list[[]] | int", _TypeUnion((_Alias(_Type("builtins.list", True), (_Seq("list", ()),)), _Type("builtins.int", False))), "list[[]] | int"),
    ("list[[]] | list[[]]", _Alias(_Type("builtins.list", True), (_Seq("list", ()),)), "list[[]]"),
    ("list[int | str] | list[str | int]", _Alias(_Type("builtins.list", True), (_TypeUnion((_Type("builtins.int", False), _Type("builtins.str", False))),)), "list[int | str]"),
])
def test_union_normalization_matches_cpython(
    tmp_path, annotation, expected, field_type,
):
    expression = ast.parse(annotation, mode="eval").body
    before = ast.dump(expression)
    assert _eval(expression, {}, {}, {}) == expected
    assert _eval(expression, {}, {}, {}) == expected
    assert ast.dump(expression) == before
    result = _model(_source(annotation))
    assert result.outcome == "MODEL_PASS"
    assert len(result.assumed_dataclass_decorations) == 1
    runtime = _runtime(tmp_path, _source(annotation))
    assert runtime[-1] == "RESULT OK"
    assert runtime[0] == f"FIELD {field_type}"


def test_union_keys_and_dispatch_boundary():
    integer = _Type("builtins.int", False)
    string = _Type("builtins.str", False)
    left = _construct_union(integer, string)
    right = _construct_union(string, integer)
    assert isinstance(left, _TypeUnion)
    assert isinstance(right, _TypeUnion)
    assert left.args == (integer, string)
    assert right.args == (string, integer)
    assert _proven_key(left) == _proven_key(right)
    assert _construct_union(left, integer) == left
    assert _construct_union(_Scalar(None), _Scalar(None)) is None
    assert _proven_key(_Module("external")) is None
    assert not isinstance(_Scalar(None), _BuiltinUnionOr)
    assert not isinstance(_Seq("list", ()), _BuiltinUnionOr)
    assert not isinstance(_Module("pkg"), _BuiltinUnionOr)
    assert isinstance(_Class("pkg.T"), _BuiltinUnionOr)


@pytest.mark.parametrize("prelude,annotation,effect", [
    (
        "class T:\n"
        "    def __class_getitem__(cls, item):\n"
        "        print('USER_GETITEM', flush=True)\n"
        "        raise SystemExit('getitem-effect')\n",
        "T[int]", "USER_GETITEM",
    ),
    (
        "class Meta(type):\n"
        "    def __or__(cls, other):\n"
        "        print('USER_OR', flush=True)\n"
        "        raise SystemExit('or-effect')\n"
        "class T(metaclass=Meta): pass\n",
        "T | int", "USER_OR",
    ),
    ("list = 1\n", "list[int]", None),
    ("from builtins import list as Alias\n", "Alias[int]", None),
])
def test_dynamic_boundaries_do_not_gain_pass(
    tmp_path, prelude, annotation, effect,
):
    source = _source(annotation, prelude)
    result = _model(source)
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    runtime = _runtime(tmp_path, source)
    if effect:
        assert effect in runtime


def test_operand_evaluation_order_remains_left_to_right(tmp_path):
    prelude = (
        "class L:\n"
        "    def __class_getitem__(cls, item):\n"
        "        print('LEFT', flush=True)\n"
        "        return int\n"
        "class R:\n"
        "    def __class_getitem__(cls, item):\n"
        "        print('RIGHT', flush=True)\n"
        "        return str\n"
    )
    source = _source("L[int] | R[int]", prelude)
    result = _model(source)
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert _runtime(tmp_path, source) == [
        "LEFT", "RIGHT", "FIELD int | str", "RESULT OK",
    ]
