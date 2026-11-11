import ast
import json
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)
from test_cycle_semantics_decorator_import_effect_baseline import RUNNER
from test_cycle_semantics_stacked_decorator_identity import CASES


THREE_PASS = (
    "def top_decorator(fn):\n"
    "    import pkg.a\n"
    "    return fn\n"
    "def middle_decorator(fn):\n"
    "    import pkg.b\n"
    "    return fn\n"
    "def bottom_decorator(fn):\n"
    "    import pkg.c\n"
    "    return fn\n"
    "@top_decorator\n"
    "@middle_decorator\n"
    "@bottom_decorator\n"
    "def f():\n"
    "    pass\n"
)

MIDDLE_NONE = (
    "def top_decorator(fn):\n"
    "    import pkg.a\n"
    "    return fn\n"
    "def middle_decorator(fn):\n"
    "    return\n"
    "def bottom_decorator(fn):\n"
    "    import pkg.c\n"
    "    return fn\n"
    "@top_decorator\n"
    "@middle_decorator\n"
    "@bottom_decorator\n"
    "def f():\n"
    "    pass\n"
)


@pytest.mark.parametrize(
    "source,error,imports,outcome,calls,starts",
    [
        pytest.param(CASES[0].values[0], None, ("pkg.bottom", "pkg.top"), "MODEL_PASS", ("lower", "upper"), ("pkg.bottom", "pkg.top"), id="A-bottom-up"),
        pytest.param(CASES[1].values[0], None, ("pkg.child", "pkg.child"), "MODEL_PASS", ("deco", "deco"), ("pkg.child",), id="B-repeated"),
        pytest.param(CASES[3].values[0], None, ("pkg.top",), "MODEL_PASS", ("lower", "upper"), ("pkg.top",), id="C-intermediate-none"),
        pytest.param(CASES[4].values[0], "TypeError", ("pkg.bottom",), "UNKNOWN", ("lower",), ("pkg.bottom",), id="D-wrong-arity"),
        pytest.param(CASES[5].values[0], None, ("pkg.bottom", "pkg.top", "pkg.child"), "MODEL_PASS", ("lower", "upper", "f"), ("pkg.bottom", "pkg.top", "pkg.child"), id="E-deferred-body"),
        pytest.param(CASES[2].values[0], None, ("pkg.bottom", "pkg.top"), "UNKNOWN", (), (), id="F-global-rebinding"),
        pytest.param(THREE_PASS, None, ("pkg.c", "pkg.b", "pkg.a"), "MODEL_PASS", ("bottom_decorator", "middle_decorator", "top_decorator"), ("pkg.c", "pkg.b", "pkg.a"), id="G-three-pass-through"),
        pytest.param(MIDDLE_NONE, None, ("pkg.c", "pkg.a"), "MODEL_PASS", ("bottom_decorator", "middle_decorator", "top_decorator"), ("pkg.c", "pkg.a"), id="H-middle-none"),
        pytest.param(MIDDLE_NONE + "f()\n", "TypeError", ("pkg.c", "pkg.a"), "UNKNOWN", ("bottom_decorator", "middle_decorator", "top_decorator"), ("pkg.c", "pkg.a"), id="I-final-none-called"),
    ],
)
def test_stacked_decorator_execution(
    tmp_path, source, error, imports, outcome, calls, starts,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")

    child_names = ("top", "bottom", "child", "a", "b", "c")
    sources = {"pkg.__init__": ast.parse(source)}
    for name in child_names:
        (package / f"{name}.py").write_text("pass\n", encoding="utf-8")
        sources[f"pkg.{name}"] = ast.parse("pass\n")

    process = subprocess.run(
        [sys.executable, "-I", "-B", "-c", RUNNER, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    observed = json.loads(process.stdout)
    assert observed == {"error": error, "imports": list(imports)}

    result = evaluate_package_import_order(sources, "pkg")
    assert result.outcome == outcome
    actual_calls = tuple(
        event.symbol for event in result.events
        if event.operation == "CALL_FUNCTION"
    )
    assert actual_calls == calls
    actual_starts = tuple(
        event.target for event in result.events
        if event.operation == "START_IMPORT"
        and event.target is not None
        and event.target.startswith("pkg.")
    )
    assert actual_starts == starts

    if source == CASES[1].values[0]:
        assert sum(
            event.operation == "FUNCTION_LOCAL_IMPORT"
            and event.target == "pkg.child"
            for event in result.events
        ) == 2
