"""CPython identity and rebinding counterexamples for class decorators."""

import ast
import json
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)
from test_cycle_semantics_decorator_import_effect_baseline import RUNNER


CASES = [
    pytest.param(
        "def deco(cls):\n    import pkg.effect\n    return cls\n"
        "deco = None\n@deco\nclass C:\n    pass\n",
        "TypeError", (), "UNKNOWN", (), 0, (),
        id="A-rebind-before-snapshot",
    ),
    pytest.param(
        "def C(cls):\n    import pkg.effect\n    return cls\n"
        "@C\nclass C:\n    pass\n",
        None, ("pkg.effect",), "MODEL_PASS", ("C",), 1,
        ("pkg.effect",), id="B-same-name",
    ),
    pytest.param(
        "def deco(cls):\n    import pkg.effect\n    return cls\n"
        "@deco\n@deco\nclass C:\n    pass\n",
        None, ("pkg.effect", "pkg.effect"), "MODEL_PASS",
        ("deco", "deco"), 2, ("pkg.effect",),
        id="C-duplicate-references",
    ),
    pytest.param(
        "def deco(cls):\n    import pkg.effect\n    return cls\n"
        "@deco\nclass C:\n    from pkg.body import deco\n",
        None, ("pkg.body", "pkg.effect"), "MODEL_PASS",
        ("deco",), 1, ("pkg.body", "pkg.effect"),
        id="D-class-local-shadowing",
    ),
    pytest.param(
        "def deco(cls):\n    import pkg.effect\n    return cls\n"
        "@deco\nclass C:\n    pass\n"
        "deco = None\n",
        None, ("pkg.effect",), "MODEL_PASS", ("deco",), 1,
        ("pkg.effect",), id="E-rebind-after-decoration",
    ),
    pytest.param(
        "def top(cls):\n    import pkg.top_effect\n    return cls\n"
        "def bottom(cls):\n    import pkg.bottom_effect\n    return cls\n"
        "top = None\n@top\n@bottom\nclass C:\n    pass\n",
        "TypeError", ("pkg.bottom_effect",), "UNKNOWN",
        ("bottom",), 1, ("pkg.bottom_effect",),
        id="F-noncallable-stack-member",
    ),
]


@pytest.mark.parametrize(
    "source,error,imports,outcome,calls,local_import_count,starts",
    CASES,
)
def test_class_decorator_identity_counterexamples(
    tmp_path, source, error, imports, outcome, calls,
    local_import_count, starts,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")

    child_names = ("effect", "top_effect", "bottom_effect", "body")
    sources = {"pkg.__init__": ast.parse(source)}
    for child in child_names:
        child_source = (
            "deco = None\n" if child == "body" else "pass\n"
        )
        (package / f"{child}.py").write_text(
            child_source, encoding="utf-8",
        )
        sources[f"pkg.{child}"] = ast.parse(child_source)

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
    assert sum(
        event.operation == "FUNCTION_LOCAL_IMPORT"
        and event.target in {
            "pkg.effect", "pkg.top_effect", "pkg.bottom_effect",
        }
        for event in result.events
    ) == local_import_count
    actual_starts = tuple(
        event.target for event in result.events
        if event.operation == "START_IMPORT"
        and event.target is not None
        and event.target.startswith("pkg.")
    )
    assert actual_starts == starts
