"""CPython parity for restricted import-time __main__ guards."""

import ast
import json
import subprocess
import sys
from dataclasses import asdict

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


def test_b0g4c22_main_guard_skips_unknown_import_and_call(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.entry": (
            'if __name__ == "__main__":\n'
            "    import pkg.missing\n"
            "    dangerous()\n"
            "ready = 1"
        ),
    }

    result = _model(sources, "pkg.entry")

    assert result.outcome == "MODEL_PASS"
    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.missing"
        for event in result.events
    )

    assert _actual(
        tmp_path, sources, "pkg.entry"
    ).returncode == 0


def test_b0g4c22_main_guard_else_imports_child(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.entry": (
            'if __name__ == "__main__":\n'
            "    dangerous()\n"
            "else:\n"
            "    from pkg import child"
        ),
        "pkg.child": "pass",
    }

    result = _model(sources, "pkg.entry")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.child"
        for event in result.events
    )

    assert _actual(
        tmp_path, sources, "pkg.entry"
    ).returncode == 0


def test_b0g4c22_not_main_imports_relative_child(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.entry": (
            'if __name__ != "__main__":\n'
            "    from . import child"
        ),
        "pkg.child": "pass",
    }

    result = _model(sources, "pkg.entry")

    assert result.outcome == "MODEL_PASS"

    assert _actual(
        tmp_path, sources, "pkg.entry"
    ).returncode == 0


def test_b0g4c22_not_main_else_is_skipped(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.entry": (
            'if __name__ != "__main__":\n'
            "    ready = 1\n"
            "else:\n"
            "    import pkg.missing\n"
            "    dangerous()"
        ),
    }

    result = _model(sources, "pkg.entry")

    assert result.outcome == "MODEL_PASS"

    assert _actual(
        tmp_path, sources, "pkg.entry"
    ).returncode == 0


def test_b0g4c22_package_initializer_guard(
    tmp_path,
):
    sources = {
        "pkg.__init__": (
            'if __name__ == "__main__":\n'
            "    dangerous()\n"
            "else:\n"
            "    from pkg import child"
        ),
        "pkg.child": "pass",
    }

    result = _model(sources, "pkg")

    assert result.outcome == "MODEL_PASS"

    assert _actual(
        tmp_path, sources, "pkg"
    ).returncode == 0


def test_b0g4c22_selected_branch_preserves_binding_hazard(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "from pkg.b import ready\n"
            'if __name__ != "__main__":\n'
            "    ready = 1"
        ),
        "pkg.b": "from pkg.a import ready",
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert (
        result.target_module,
        result.symbol,
    ) == ("pkg.a", "ready")

    process = _actual(tmp_path, sources, "pkg.a")

    assert process.returncode != 0
    assert "ImportError" in process.stderr


def test_b0g4c22_selected_branch_definition_and_call(
    tmp_path,
):
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            'if __name__ != "__main__":\n'
            "    def f():\n"
            "        from pkg import child\n"
            "    f()"
        ),
        "pkg.child": "pass",
    }

    result = _model(sources, "pkg.a")

    assert result.outcome == "MODEL_PASS"

    assert any(
        event.operation == "CALL_FUNCTION"
        and event.symbol == "f"
        for event in result.events
    )

    assert _actual(
        tmp_path, sources, "pkg.a"
    ).returncode == 0


def test_b0g4c22_reversed_comparison_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            'if "__main__" == __name__:\n'
            "    pass"
        ),
    }

    assert _model(
        sources, "pkg.a"
    ).outcome == "UNKNOWN"


def test_b0g4c22_dynamic_predicate_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "if is_main():\n"
            "    pass"
        ),
    }

    assert _model(
        sources, "pkg.a"
    ).outcome == "UNKNOWN"


def test_b0g4c22_name_reassignment_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            '__name__ = "__main__"\n'
            'if __name__ == "__main__":\n'
            "    ready = 1"
        ),
    }

    assert _model(
        sources, "pkg.a"
    ).outcome == "UNKNOWN"


def test_b0g4c22_selected_unsupported_branch_unknown():
    sources = {
        "pkg.__init__": "pass",
        "pkg.a": (
            'if __name__ != "__main__":\n'
            "    dangerous()"
        ),
    }

    assert _model(
        sources, "pkg.a"
    ).outcome == "UNKNOWN"


def test_b0g4c22_determinism_and_ast_immutability():
    sources = {
        "pkg.__init__": (
            'if __name__ == "__main__":\n'
            "    dangerous()\n"
            "else:\n"
            "    ready = 1"
        ),
    }

    trees = {
        name: ast.parse(source)
        for name, source in sources.items()
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
