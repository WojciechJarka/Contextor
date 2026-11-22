"""CPython 3.15 annotation consumption versus the conditional package model."""

import ast
import os
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


pytestmark = pytest.mark.skipif(
    sys.version_info[:2] != (3, 15),
    reason="CPython 3.15 annotation consumption contract",
)


def _model(source, **other_sources):
    trees = {"pkg.__init__": ast.parse(source)}
    trees.update({name: ast.parse(body) for name, body in other_sources.items()})
    original = {name: ast.dump(tree) for name, tree in trees.items()}
    options = dict(
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
    )
    first = evaluate_package_import_order(trees, "pkg", **options)
    second = evaluate_package_import_order(trees, "pkg", **options)
    assert first == second
    assert original == {name: ast.dump(tree) for name, tree in trees.items()}
    assert first.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
    )
    return first


def _runtime(tmp_path, source, *, side=None, other=None, inspect=False):
    package = tmp_path / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(source, encoding="utf-8")
    if side is not None:
        (tmp_path / "side.py").write_text(side, encoding="utf-8")
    if other is not None:
        (package / "other.py").write_text(other, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code = (
        "try:\n"
        " import pkg\n"
        + (
            " print('FIELD_TYPE', repr(pkg.C.__dataclass_fields__['x'].type), flush=True)\n"
            " print('T_BOUND', 'T' in vars(pkg.C), flush=True)\n"
            if inspect else ""
        )
        +
        " print('RESULT', 'OK', flush=True)\n"
        "except BaseException as error:\n"
        " print('RESULT', type(error).__name__, str(error), flush=True)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-u", "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.splitlines()


@pytest.mark.parametrize("annotation", [
    "list[int]", "list[str] | None", "None | list[str]",
    "int | None", "str | None", "str | int", "str | None | None",
    "[T][0]", "Alias", "\"str\"",
    "1 if True else T[int]", "\"T[int]\"",
])
def test_passive_annotations_remain_conditional_pass(tmp_path, annotation):
    source = (
        "from dataclasses import dataclass\n"
        "class T:\n"
        "    def __class_getitem__(cls, item):\n"
        "        raise SystemExit('getitem-effect')\n"
        "Alias = T\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        f"    x: {annotation}\n"
    )
    result = _model(source)
    assert result.outcome == "MODEL_PASS", annotation
    assert len(result.assumed_dataclass_decorations) == 1
    assert _runtime(tmp_path, source)[-1] == "RESULT OK"


def test_indexed_module_attribute_with_known_binding(tmp_path):
    source = (
        "import pkg.other\n"
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: pkg.other.T\n"
    )
    other = "class T: pass\n"
    result = _model(source, **{"pkg.other": other})
    assert result.outcome == "MODEL_PASS"
    assert _runtime(tmp_path, source, other=other)[-1] == "RESULT OK"


@pytest.mark.parametrize("prelude,annotation,runtime_result", [
    (
        "class T:\n"
        "    def __class_getitem__(cls, item):\n"
        "        raise SystemExit('getitem-effect')\n",
        "T[int]", "RESULT SystemExit getitem-effect",
    ),
    (
        "class Meta(type):\n"
        "    def __or__(cls, other):\n"
        "        raise SystemExit('or-effect')\n"
        "class T(metaclass=Meta): pass\n",
        "T | str", "RESULT SystemExit or-effect",
    ),
    (
        "class Meta(type):\n"
        "    @property\n"
        "    def x(cls):\n"
        "        raise SystemExit('descriptor-effect')\n"
        "class Holder(metaclass=Meta): pass\n",
        "Holder.x", "RESULT SystemExit descriptor-effect",
    ),
    ("import ast\n", "ast.AST", "RESULT OK"),
    ("str = 42\n", "str", "RESULT OK"),
    ("", "Missing", "RESULT OK"),
])
def test_unproved_operations_stop_before_decoration(
    tmp_path, prelude, annotation, runtime_result,
):
    source = (
        prelude
        + "from dataclasses import dataclass\n"
        + "@dataclass(frozen=True)\n"
        + "class C:\n"
        + f"    x: {annotation}\n"
    )
    result = _model(source)
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert all(
        event.operation != "ASSUMED_FROZEN_DATACLASS_DECORATION"
        for event in result.events
    )
    assert _runtime(tmp_path, source)[-1] == runtime_result


def test_textual_attribute_can_invoke_external_getattr(tmp_path):
    source = (
        "import side\n"
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: \"side.missing\"\n"
    )
    side = (
        "def __getattr__(name):\n"
        "    print('SIDE_GETATTR', name, flush=True)\n"
        "    raise SystemExit('annotation-effect')\n"
    )
    result = _model(source)
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert _runtime(tmp_path, source, side=side) == [
        "SIDE_GETATTR missing", "RESULT SystemExit annotation-effect",
    ]


def test_class_local_precedes_module_and_missing_field_does_not_bind(tmp_path):
    source = (
        "T = 3\n"
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    T: int = 1\n"
        "    x: T = 2\n"
    )
    assert _model(source).outcome == "MODEL_PASS"
    runtime = _runtime(tmp_path, source, inspect=True)
    assert "FIELD_TYPE 1" in runtime
    assert "T_BOUND True" in runtime
    assert runtime[-1] == "RESULT OK"
    absent = (
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    T: int\n"
        "    x: T\n"
    )
    assert _model(absent).outcome == "UNKNOWN"
    absent_runtime = _runtime(tmp_path / "absent", absent, inspect=True)
    assert "T_BOUND False" in absent_runtime


def test_module_alias_rebinding_is_read_at_decoration(tmp_path):
    source = (
        "from dataclasses import dataclass\n"
        "class Old: pass\n"
        "class New: pass\n"
        "T = Old\n"
        "T = New\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    x: T\n"
        "T = Old\n"
    )
    assert _model(source).outcome == "MODEL_PASS"
    lines = _runtime(tmp_path, source, inspect=True)
    assert "FIELD_TYPE <class 'pkg.New'>" in lines
    assert lines[-1] == "RESULT OK"


def test_class_name_is_bound_only_after_decorator(tmp_path):
    source = (
        "from dataclasses import dataclass\n"
        "def decorate(cls):\n"
        "    print('BOUND_BEFORE', 'C' in globals(), flush=True)\n"
        "    return dataclass(frozen=True)(cls)\n"
        "@decorate\n"
        "class C:\n"
        "    x: int\n"
    )
    assert _runtime(tmp_path, source) == ["BOUND_BEFORE False", "RESULT OK"]


def test_unknown_class_local_and_prior_events_survive(tmp_path):
    source = (
        "from dataclasses import dataclass, field\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    T: int = field()\n"
        "    x: T\n"
    )
    result = _model(source)
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
    assert any(event.operation == "ASSUMED_EXTERNAL_IMPORT" for event in result.events)
    _runtime(tmp_path, source)


def test_annotation_phase_precedes_text_consumption(tmp_path):
    source = (
        "import side\n"
        "from dataclasses import dataclass\n"
        "class T:\n"
        "    def __class_getitem__(cls, item):\n"
        "        print('GETITEM', flush=True)\n"
        "        return int\n"
        "@dataclass(frozen=True)\n"
        "class C:\n"
        "    a: \"side.missing\"\n"
        "    b: T[int]\n"
    )
    side = (
        "def __getattr__(name):\n"
        "    print('SIDE_GETATTR', name, flush=True)\n"
        "    raise SystemExit('annotation-effect')\n"
    )
    lines = _runtime(tmp_path, source, side=side)
    assert "SIDE_GETATTR missing" in lines, lines
    assert lines.index("GETITEM") < lines.index("SIDE_GETATTR missing")
    result = _model(source)
    assert result.outcome == "UNKNOWN"
    assert result.assumed_dataclass_decorations == ()
