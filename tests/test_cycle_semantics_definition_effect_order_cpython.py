import json
import subprocess
import sys
from pathlib import Path

import pytest


CASES = [
    pytest.param(
        """
def deco(fn):
    trace.append("apply")
    return fn

@deco
def f():
    trace.append("body")

trace.append("after")
""",
        ["apply", "after"],
        None,
        False,
        id="function-decorator-application",
    ),
    pytest.param(
        """
def upper(fn):
    trace.append("apply-upper")
    return fn

def lower(fn):
    trace.append("apply-lower")
    return fn

@upper
@lower
def f():
    pass
""",
        ["apply-lower", "apply-upper"],
        None,
        False,
        id="stacked-application-bottom-up",
    ),
    pytest.param(
        """
def make(label):
    trace.append("evaluate-" + label)

    def deco(fn):
        trace.append("apply-" + label)
        return fn

    return deco

@make("upper")
@make("lower")
def f():
    pass
""",
        [
            "evaluate-upper",
            "evaluate-lower",
            "apply-lower",
            "apply-upper",
        ],
        None,
        False,
        id="factory-evaluation-and-application",
    ),
    pytest.param(
        """
def make():
    trace.append("decorator-expression")

    def deco(fn):
        trace.append("application")
        return fn

    return deco

def default():
    trace.append("default-expression")
    return 7

@make()
def f(x=default()):
    pass
""",
        [
            "decorator-expression",
            "default-expression",
            "application",
        ],
        None,
        False,
        id="decorator-expression-before-default",
    ),
    pytest.param(
        """
def deco(cls):
    trace.append("class-decoration")
    return cls

@deco
class C:
    trace.append("class-body")
""",
        ["class-body", "class-decoration"],
        None,
        False,
        id="class-body-before-decoration",
    ),
    pytest.param(
        """
def deco(fn):
    def replacement():
        trace.append("replacement-called")
    return replacement

@deco
def f():
    trace.append("original-called")

f()
""",
        ["replacement-called"],
        None,
        False,
        id="decorator-replaces-function-binding",
    ),
    pytest.param(
        """
def deco(fn):
    import pkg.child
    trace.append("decorator-import")
    return fn

@deco
def f():
    pass
""",
        ["decorator-import"],
        None,
        True,
        id="decorator-imports-during-definition",
    ),
    pytest.param(
        """
def deco(fn):
    trace.append("before-error")
    raise RuntimeError("decorator failed")

@deco
def f():
    pass

trace.append("unreachable")
""",
        ["before-error"],
        "RuntimeError",
        False,
        id="decorator-exception-stops-module",
    ),
]


RUNNER = """
import json
import sys

sys.path.insert(0, sys.argv[1])

trace = []
error = None

try:
    exec(
        compile(sys.argv[2], "<definition-effects>", "exec"),
        {"trace": trace},
    )
except Exception as exc:
    error = type(exc).__name__

print(json.dumps({
    "trace": trace,
    "error": error,
    "child_imported": "pkg.child" in sys.modules,
}))
"""


@pytest.mark.parametrize(
    "source,expected_trace,expected_error,child_imported",
    CASES,
)
def test_definition_effect_order_cpython(
    tmp_path: Path,
    source: str,
    expected_trace: list[str],
    expected_error: str | None,
    child_imported: bool,
):
    package = tmp_path / "pkg"
    package.mkdir()

    (package / "__init__.py").write_text(
        "pass\n", encoding="utf-8"
    )
    (package / "child.py").write_text(
        "pass\n", encoding="utf-8"
    )

    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            RUNNER,
            str(tmp_path),
            source,
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert process.returncode == 0, process.stderr

    observed = json.loads(process.stdout)

    assert observed == {
        "trace": expected_trace,
        "error": expected_error,
        "child_imported": child_imported,
    }
