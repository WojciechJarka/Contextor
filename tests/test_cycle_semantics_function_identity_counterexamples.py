import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)

from test_cycle_semantics_function_identity_cpython import (
    RUNNER,
    OLD,
    NEW,
)


CASES = [
    pytest.param(
        OLD + "\ng = f\nh = g\nf = None\nh()\n",
        "MODEL_PASS",
        True,
        False,
        ["h"],
        None,
        id="alias-chain-survives-rebinding",
    ),
    pytest.param(
        OLD + "\ng = f\n" + NEW + "\ng = f\ng()\n",
        "MODEL_PASS",
        False,
        True,
        ["g"],
        None,
        id="alias-rebound-to-new-definition",
    ),
    pytest.param(
        OLD + "\ng = f\n" + NEW + "\ng()\nf()\n",
        "MODEL_PASS",
        True,
        True,
        ["g", "f"],
        None,
        id="old-and-new-bodies-both-executed",
    ),
    pytest.param(
        OLD + "\ng = f\n" + NEW + "\nf = g\nf()\n",
        "MODEL_PASS",
        True,
        False,
        ["f"],
        None,
        id="old-object-restored-under-original-name",
    ),
    pytest.param(
        OLD + "\ng = f\ng = None\ng()\n",
        "UNKNOWN",
        False,
        False,
        [],
        "TypeError",
        id="alias-overwritten-with-noncallable",
    ),
]


@pytest.mark.parametrize(
    "source,outcome,old,new,call_names,error",
    CASES,
)
def test_function_identity_counterexample_parity(
    tmp_path: Path,
    source: str,
    outcome: str,
    old: bool,
    new: bool,
    call_names: list[str],
    error: str | None,
):
    package = tmp_path / "pkg"
    package.mkdir()

    (package / "__init__.py").write_text(
        source,
        encoding="utf-8",
    )
    (package / "old.py").write_text(
        "pass\n",
        encoding="utf-8",
    )
    (package / "new.py").write_text(
        "pass\n",
        encoding="utf-8",
    )

    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            RUNNER,
            str(tmp_path),
            "pkg",
        ],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert process.returncode == 0, process.stderr

    actual = json.loads(process.stdout)

    assert actual["ok"] == (error is None)
    assert actual["error"] == error
    assert actual["old"] is old
    assert actual["new"] is new

    result = evaluate_package_import_order(
        {
            "pkg.__init__": ast.parse(source),
            "pkg.old": ast.parse("pass\n"),
            "pkg.new": ast.parse("pass\n"),
        },
        "pkg",
    )

    assert result.outcome == outcome

    imported = {
        event.target
        for event in result.events
        if event.operation == "START_IMPORT"
        and event.target in {"pkg.old", "pkg.new"}
    }

    assert ("pkg.old" in imported) is old
    assert ("pkg.new" in imported) is new

    model_calls = [
        event.symbol
        for event in result.events
        if event.operation == "CALL_FUNCTION"
        and event.module == "pkg"
    ]

    assert model_calls == call_names
