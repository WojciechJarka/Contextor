"""CPython-backed definition-time decorator effect regressions."""

import ast
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.namespace_path_model import (
    SearchPortion,
)
from contextor.core.cycle_semantics.package_model import (
    evaluate_conditional_namespace_import_order,
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
        filename = (
            "__init__.py"
            if parts[-1] == "__init__"
            else parts[-1] + ".py"
        )
        path = tmp_path.joinpath(*parts[:-1], filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source + "\n", encoding="utf-8")

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


def test_d02_lru_cache_is_not_passive_runtime_proof(tmp_path):
    source = (
        "from functools import lru_cache\n"
        "@lru_cache(maxsize=1024)\n"
        "def cached(value):\n"
        "    return value\n"
    )

    conditional = evaluate_conditional_namespace_import_order(
        {"ns.a": ast.parse(source)},
        "ns.a",
        (SearchPortion("repo", frozenset({"ns/a.py"})),),
        target_python_version=sys.version_info[:2],
        assume_passive_external_imports=True,
    )

    assert conditional.outcome == "UNKNOWN"
    assert conditional.model_assessment is not None

    last = conditional.model_assessment.events[-1]
    assert last.operation == "UNMODELED_STATEMENT"
    assert last.target == "FunctionDef"
    assert last.symbol == "2:1"

    assert conditional.outcome != "CONDITIONAL_MODEL_PASS"

    actual = _actual(
        tmp_path,
        {
            "pkg.__init__": "pass",
            "pkg.a": source + "assert cached(3) == 3\n",
        },
        "pkg.a",
    )
    assert actual.returncode == 0, actual.stderr


@pytest.mark.parametrize(
    "definition,export",
    [
        (
            "def deco(obj):\n"
            "    import pkg.b\n"
            "    return obj\n"
            "@deco\n"
            "def export():\n"
            "    pass\n",
            "export",
        ),
        (
            "def make():\n"
            "    import pkg.b\n"
            "    return lambda obj: obj\n"
            "@make()\n"
            "def export():\n"
            "    pass\n",
            "export",
        ),
        (
            "def deco(obj):\n"
            "    import pkg.b\n"
            "    return obj\n"
            "@deco\n"
            "class C:\n"
            "    pass\n",
            "C",
        ),
        (
            "def deco(obj):\n"
            "    import pkg.b\n"
            "    return obj\n"
            "class C:\n"
            "    @deco\n"
            "    def method(self):\n"
            "        pass\n",
            "C",
        ),
    ],
    ids=[
        "function_decorator",
        "decorator_factory",
        "class_decorator",
        "class_body_method_decorator",
    ],
)
@pytest.mark.parametrize(
    "entry,should_succeed",
    [
        ("pkg.a", False),
        ("pkg.b", True),
    ],
)
def test_d03_d05_decorator_import_entry_dependency(
    tmp_path, definition, export, entry, should_succeed
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": definition,
        "pkg.b": f"from pkg.a import {export}",
    }

    modeled = _model(sources, entry)
    actual = _actual(tmp_path, sources, entry)

    assert modeled.outcome == "UNKNOWN"
    assert modeled.outcome != "MODEL_PASS"

    if should_succeed:
        assert actual.returncode == 0, actual.stderr
    else:
        assert actual.returncode != 0
        assert "ImportError" in actual.stderr


@pytest.mark.parametrize(
    "definition,expected_trace",
    [
        (
            "@make('top')\n"
            "@make('bottom')\n"
            "def f():\n"
            "    trace.append('function_body')\n",
            [
                "eval:top",
                "eval:bottom",
                "apply:bottom",
                "apply:top",
            ],
        ),
        (
            "@make('top')\n"
            "@make('bottom')\n"
            "class C:\n"
            "    trace.append('class_body')\n",
            [
                "eval:top",
                "eval:bottom",
                "class_body",
                "apply:bottom",
                "apply:top",
            ],
        ),
    ],
    ids=["function_stack", "class_stack"],
)
def test_decorator_expression_and_application_order(
    tmp_path, definition, expected_trace
):
    source = (
        "trace = []\n"
        "def make(tag):\n"
        "    trace.append('eval:' + tag)\n"
        "    def apply(obj):\n"
        "        trace.append('apply:' + tag)\n"
        "        return obj\n"
        "    return apply\n"
        + definition
        + f"\nassert trace == {expected_trace!r}\n"
    )

    modeled = _model(
        {"pkg.__init__": "pass", "pkg.a": source},
        "pkg.a",
    )
    actual = _actual(
        tmp_path,
        {"pkg.__init__": "pass", "pkg.a": source},
        "pkg.a",
    )

    assert modeled.outcome == "UNKNOWN"
    assert actual.returncode == 0, actual.stderr


@pytest.mark.parametrize(
    "definition,export",
    [
        (
            "@replace\n"
            "def exported():\n"
            "    pass\n",
            "exported",
        ),
        (
            "@replace\n"
            "class Exported:\n"
            "    pass\n",
            "Exported",
        ),
    ],
    ids=["function_replacement", "class_replacement"],
)
def test_decorator_can_replace_definition_binding(
    tmp_path, definition, export
):
    source = (
        "def replace(obj):\n"
        "    return 42\n"
        + definition
        + f"assert {export} == 42\n"
    )

    sources = {
        "pkg.__init__": "pass",
        "pkg.a": source,
    }

    modeled = _model(sources, "pkg.a")
    actual = _actual(tmp_path, sources, "pkg.a")

    assert modeled.outcome == "UNKNOWN"
    assert actual.returncode == 0, actual.stderr


def test_nested_method_decorator_remains_unmodeled():
    source = (
        "class C:\n"
        "    @deco\n"
        "    def method(self):\n"
        "        pass\n"
    )

    result = evaluate_conditional_namespace_import_order(
        {"ns.a": ast.parse(source)},
        "ns.a",
        (SearchPortion("repo", frozenset({"ns/a.py"})),),
        target_python_version=sys.version_info[:2],
    )

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.events[-1].operation == (
        "UNMODELED_STATEMENT"
    )
    assert result.model_assessment.events[-1].target == (
        "ClassDef"
    )
