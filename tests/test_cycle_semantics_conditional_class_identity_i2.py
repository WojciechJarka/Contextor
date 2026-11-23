"""Definition identity of conditional frozen dataclasses on CPython 3.15."""

import ast
import os
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.execution.annotation_effects import (
    _Class,
    _TypeUnion,
    _eval,
)
from contextor.core.cycle_semantics.package_model import (
    _compile,
    evaluate_package_import_order,
)


pytestmark = pytest.mark.skipif(
    sys.version_info[:2] != (3, 15),
    reason="CPython 3.15 deferred frozen dataclass contract",
)


DECORATOR = "from dataclasses import dataclass\n"
T = "@dataclass(frozen=True)\nclass T:\n    x: int\n"
C = "@dataclass(frozen=True)\nclass C:\n    x: Old | T\n"


def _compile_steps(source, logical="pkg"):
    tree = ast.parse(source)
    before = ast.dump(tree)
    steps = _compile(
        tree, logical, True,
        annotation_semantics="DEFERRED",
        assume_frozen_dataclass=True,
    )
    assert steps is not None
    assert ast.dump(tree) == before
    return steps


def _definitions(source, name="T", logical="pkg"):
    return [
        step for step in _compile_steps(source, logical)
        if step.op == "DEFINE_CONDITIONAL_FROZEN_DATACLASS"
        and step.binding == name
    ]


def _symbolic(expression, bindings):
    namespace = {
        name: "\x00PASSIVE_CLASS:" + identity
        for name, identity in bindings.items()
    }
    return _eval(
        ast.parse(expression, mode="eval").body,
        {}, namespace, {"pkg": namespace},
    )


def _model(sources):
    trees = {name: ast.parse(source) for name, source in sources.items()}
    before = {name: ast.dump(tree) for name, tree in trees.items()}
    options = dict(
        annotation_semantics="DEFERRED",
        _compile_on_first_import=True,
        _assume_passive_external_imports=True,
        _assume_frozen_dataclass_decoration=True,
        _assumed_external_callable_effects={
            ("dataclasses", "dataclass"):
                "FROZEN_DATACLASS_DECORATOR_FACTORY",
        },
    )
    first = evaluate_package_import_order(trees, "pkg", **options)
    second = evaluate_package_import_order(trees, "pkg", **options)
    assert first == second
    assert before == {name: ast.dump(tree) for name, tree in trees.items()}
    assert first.evidence_scope == (
        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
        + (
            "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
            if first.assumed_external_call_effects
            else ""
        )
    )
    return first


def _cpython(tmp_path, sources):
    package = tmp_path / "pkg"
    package.mkdir(parents=True)
    for logical, source in sources.items():
        name = "__init__.py" if logical == "pkg.__init__" else logical.removeprefix("pkg.") + ".py"
        (package / name).write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code = (
        "import pkg, typing\n"
        "print('SAME', pkg.Old is pkg.T)\n"
        "value = pkg.C.__dataclass_fields__['x'].type\n"
        "print('ARGS', len(typing.get_args(value)))\n"
        "print('MEMBERS', tuple(arg is pkg.Old for arg in typing.get_args(value)))\n"
        "print('FIELD', repr(value))\n"
    )
    process = subprocess.run(
        [sys.executable, "-u", "-c", code],
        cwd=tmp_path, env=env,
        capture_output=True, text=True,
        timeout=15, check=False,
    )
    assert process.returncode == 0, process.stderr
    return process.stdout.splitlines()


def test_redefinition_alias_and_union_have_two_identities(tmp_path):
    source = DECORATOR + T + "Old = T\n" + T + C
    definitions = _definitions(source)
    assert len(definitions) == 2
    first, second = (step.definition_id for step in definitions)
    assert (first, second) == ("pkg:3:0", "pkg:7:0")
    assert all(step.source_line == int(step.definition_id.split(":")[1]) - 1 for step in definitions)
    value = _symbolic("Old | T", {"Old": first, "T": second})
    assert isinstance(value, _TypeUnion)
    assert value.args == (
        _Class("\x00PASSIVE_CLASS:" + first),
        _Class("\x00PASSIVE_CLASS:" + second),
    )
    result = _model({"pkg.__init__": source})
    assert result.outcome == "MODEL_PASS"
    assert len(result.assumed_dataclass_decorations) == 3
    assert _cpython(tmp_path, {"pkg.__init__": source})[:3] == [
        "SAME False", "ARGS 2", "MEMBERS (True, False)",
    ]


def test_same_alias_deduplicates_and_rebinding_preserves_old(tmp_path):
    source = DECORATOR + T + "Old = T\n" + T + "T = 1\n" + C.replace("Old | T", "Old | Old")
    first, second = (step.definition_id for step in _definitions(source))
    assert first != second
    assert _symbolic("Old | Old", {"Old": first}) == _Class(
        "\x00PASSIVE_CLASS:" + first
    )
    assert _model({"pkg.__init__": source}).outcome == "MODEL_PASS"
    runtime = _cpython(tmp_path, {"pkg.__init__": source})
    assert runtime[:3] == ["SAME False", "ARGS 0", "MEMBERS ()"]


def test_two_names_and_two_modules_keep_distinct_identity(tmp_path):
    local = DECORATOR + T + "Old = T\n" + T.replace("class T:", "class U:") + C.replace("Old | T", "Old | U")
    t_id = _definitions(local)[0].definition_id
    u_id = _definitions(local, "U")[0].definition_id
    assert t_id != u_id
    value = _symbolic("Old | U", {"Old": t_id, "U": u_id})
    assert isinstance(value, _TypeUnion) and len(value.args) == 2
    assert _model({"pkg.__init__": local}).outcome == "MODEL_PASS"
    assert _cpython(tmp_path / "local", {"pkg.__init__": local})[:3] == [
        "SAME True", "ARGS 2", "MEMBERS (True, False)",
    ]

    sources = {
        "pkg.__init__": DECORATOR + "from .a import T as Old\nfrom .b import T\n" + C,
        "pkg.a": DECORATOR + T,
        "pkg.b": DECORATOR + T,
    }
    a_id = _definitions(sources["pkg.a"], logical="pkg.a")[0].definition_id
    b_id = _definitions(sources["pkg.b"], logical="pkg.b")[0].definition_id
    assert a_id != b_id
    assert isinstance(_symbolic("Old | T", {"Old": a_id, "T": b_id}), _TypeUnion)
    assert _model(sources).outcome == "MODEL_PASS"
    assert _cpython(tmp_path, sources)[:3] == [
        "SAME False", "ARGS 2", "MEMBERS (True, False)",
    ]


def test_shifted_definition_changes_id_not_runtime_semantics(tmp_path):
    source = DECORATOR + T + "Old = T\n" + T + C
    shifted = DECORATOR + "\n" + T + "Old = T\n" + T + C
    original = [step.definition_id for step in _definitions(source)]
    moved = [step.definition_id for step in _definitions(shifted)]
    assert original != moved
    assert [int(value.split(":")[1]) for value in moved] == [
        int(value.split(":")[1]) + 1 for value in original
    ]
    assert _model({"pkg.__init__": shifted}).outcome == "MODEL_PASS"
    assert _cpython(tmp_path, {"pkg.__init__": shifted})[:3] == [
        "SAME False", "ARGS 2", "MEMBERS (True, False)",
    ]


def test_ordinary_class_definition_id_unchanged():
    source = "class T: pass\nclass T: pass\n"
    steps = _compile_steps(source)
    defined = [step for step in steps if step.op == "DEFINE_PASSIVE_CLASS"]
    assert [step.definition_id for step in defined] == [
        "pkg:1:0", "pkg:2:0",
    ]
