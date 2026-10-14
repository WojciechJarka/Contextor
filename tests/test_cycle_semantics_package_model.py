import ast
import json
import subprocess
import sys
from dataclasses import asdict

from contextor.core.cycle_semantics.package_model import (
    evaluate_package_import_order,
)


def _model(source, entry):
    return evaluate_package_import_order(
        {
            key: ast.parse(code)
            for key, code in source.items()
        },
        entry,
    )


def _actual(tmp_path, source, entry):
    for module_id, code in source.items():
        parts = module_id.split(".")

        if parts[-1] == "__init__":
            path = tmp_path.joinpath(
                *parts[:-1],
                "__init__.py",
            )
        else:
            path = tmp_path.joinpath(
                *parts[:-1],
                parts[-1] + ".py",
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            code + "\n",
            encoding="utf-8",
        )

    process = subprocess.run(
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
        timeout=8,
        check=False,
    )

    return process.returncode == 0


def test_parent_initializer_precedes_submodule(tmp_path):
    source = {
        "pkg.__init__": "value=7",
        "pkg.sub": "from pkg import value",
    }

    result = _model(source, "pkg.sub")

    assert result.outcome == "MODEL_PASS"

    assert [
        (event.module, event.operation)
        for event in result.events
        if event.operation == "READY"
    ] == [
        ("pkg", "READY"),
        ("pkg.sub", "READY"),
    ]

    assert _actual(tmp_path, source, "pkg.sub")


def test_package_early_attribute_failure(tmp_path):
    source = {
        "pkg.__init__": "import pkg.sub\nvalue=2",
        "pkg.sub": "import pkg\nx=pkg.value",
    }

    result = _model(source, "pkg")

    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "pkg")


def test_same_imports_reordered_pass(tmp_path):
    source = {
        "pkg.__init__": "value=2\nimport pkg.sub",
        "pkg.sub": "import pkg\nx=pkg.value",
    }

    assert _model(source, "pkg").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_child_attribute_bound_after_ready(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub": "value=7",
        "entry": "import pkg.sub\nx=pkg.sub",
    }

    result = _model(source, "entry")

    assert result.outcome == "MODEL_PASS"

    operations = [
        (event.module, event.operation, event.target)
        for event in result.events
    ]

    assert operations.index(
        ("pkg.sub", "READY", None)
    ) < operations.index(
        ("pkg", "BIND_CHILD", "pkg.sub")
    )

    assert _actual(tmp_path, source, "entry")


def test_package_relative_reexport(tmp_path):
    source = {
        "pkg.__init__": "from .sub import value",
        "pkg.sub": "value=7",
    }

    assert _model(source, "pkg").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_package_explicit_reexport(tmp_path):
    source = {
        "pkg.__init__": "from pkg.sub import value",
        "pkg.sub": "value=7",
    }

    assert _model(source, "pkg").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_package_early_from_import_hazard(tmp_path):
    source = {
        "pkg.__init__": "from pkg.sub import value",
        "pkg.sub": "from pkg import value",
    }

    assert (
        _model(source, "pkg").outcome
        == "EARLY_BINDING_HAZARD"
    )

    assert not _actual(tmp_path, source, "pkg")


def test_dotted_alias_to_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub": "value=7",
        "entry": "import pkg.sub as s\nx=s.value",
    }

    assert _model(source, "entry").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_from_package_child_loads_indexed_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.child": "value=7",
        "entry": "from pkg import child\nx=child.value",
    }

    result = _model(source, "entry")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "entry")


def test_namespace_ambiguous_external_unknown():
    assert _model(
        {"pkg.sub": "value=7"},
        "pkg.sub",
    ).outcome == "UNKNOWN"

    assert _model(
        {
            "pkg": "pass",
            "pkg.__init__": "pass",
        },
        "pkg",
    ).outcome == "UNKNOWN"

    assert _model(
        {"pkg.__init__": "import os"},
        "pkg",
    ).outcome == "UNKNOWN"


def test_unsupported_hooks_mutations_unknown():
    assert _model(
        {"pkg.__init__": "__path__=[]"},
        "pkg",
    ).outcome == "UNKNOWN"

    assert _model(
        {
            "pkg.__init__":
                "def __getattr__(name):\n    pass"
        },
        "pkg",
    ).outcome == "UNKNOWN"

    assert _model(
        {
            "pkg.__init__": "sub=1\nimport pkg.sub",
            "pkg.sub": "pass",
        },
        "pkg",
    ).outcome == "UNKNOWN"

    assert _model(
        {
            "pkg.__init__": "pass",
            "pkg.sub": "pass",
            "entry": "from pkg import *",
        },
        "entry",
    ).outcome == "UNKNOWN"


def test_determinism_invalid_no_ast_mutation():
    sources = {
        "pkg.__init__": ast.parse("import pkg.sub"),
        "pkg.sub": ast.parse("import pkg"),
    }

    before = {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in sources.items()
    }

    first = evaluate_package_import_order(
        sources,
        "pkg",
    )

    second = evaluate_package_import_order(
        sources,
        "pkg",
    )

    assert first == second
    assert first.outcome == "MODEL_PASS"

    assert {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in sources.items()
    } == before

    json.dumps(asdict(first))

    assert (
        evaluate_package_import_order(None, "pkg").outcome
        == "UNKNOWN"
    )

    assert (
        evaluate_package_import_order(
            {"pkg.__init__": None},
            "pkg",
        ).outcome
        == "UNKNOWN"
    )


def test_explicit_alias_equal_root_binds_submodule(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub": "value=2",
        "entry": "import pkg.sub as pkg\nx=pkg.value",
    }

    result = _model(source, "entry")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "ATTR"
        and event.target == "pkg.sub"
        and event.symbol == "value"
        for event in result.events
    )
    assert _actual(tmp_path, source, "entry")


def test_explicit_alias_equal_root_prevents_false_model_pass(tmp_path):
    source = {
        "pkg.__init__": "value=2",
        "pkg.sub": "pass",
        "entry": "import pkg.sub as pkg\nx=pkg.value",
    }

    result = _model(source, "entry")

    assert result.outcome == "MISSING_ATTRIBUTE"
    assert result.target_module == "pkg.sub"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "entry")


def test_explicit_alias_equal_root_inside_package_initializer(tmp_path):
    source = {
        "pkg.__init__": "import pkg.sub as pkg\nx=pkg.value",
        "pkg.sub": "value=2",
    }

    result = _model(source, "pkg")

    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "ATTR"
        and event.target == "pkg.sub"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_plain_dotted_import_still_binds_root_package(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub": "value=2",
        "entry": "import pkg.sub\nx=pkg.value",
    }

    result = _model(source, "entry")

    assert result.outcome == "MISSING_ATTRIBUTE"
    assert result.target_module == "pkg"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c2_relative_initializer_imports_child(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "value=7",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        e.operation == "BIND_CHILD"
        and e.target == "pkg.child"
        for e in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c2_relative_import_from_submodule(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.child": "value=7",
        "pkg.user": "from . import child\nx=child.value",
    }
    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.user")


def test_b0g4c2_existing_attribute_precedes_child(tmp_path):
    source = {
        "pkg.__init__": "child=3",
        "pkg.child": "value=7",
        "entry": "from pkg import child",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert not any(
        e.operation == "START_IMPORT"
        and e.target == "pkg.child"
        for e in result.events
    )
    assert _actual(tmp_path, source, "entry")


def test_b0g4c2_constant_attribute_is_not_module(tmp_path):
    source = {
        "pkg.__init__": "child=3",
        "pkg.child": "value=7",
        "entry": "from pkg import child\nx=child.value",
    }
    assert _model(source, "entry").outcome == "UNKNOWN"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c2_child_already_initialized(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.child": "value=7",
        "entry": (
            "import pkg.child\n"
            "from pkg import child\n"
            "x=child.value"
        ),
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert sum(
        e.operation == "START_IMPORT"
        and e.target == "pkg.child"
        for e in result.events
    ) == 1
    assert _actual(tmp_path, source, "entry")


def test_b0g4c2_regular_attribute_reexport(tmp_path):
    source = {
        "pkg.__init__": "from .util import exposed",
        "pkg.util": "exposed=7",
        "pkg.user": "from pkg import exposed",
    }
    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.user")


def test_b0g4c2_reentrant_child_fails_closed(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "from pkg import child",
    }
    result = _model(source, "pkg")
    assert result.outcome == "UNKNOWN"
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c2_missing_member_no_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "entry": "from pkg import missing",
    }
    result = _model(source, "entry")
    assert result.outcome == "MISSING_EXPORT"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c2_multiple_fromlist_members_unknown():
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a, b",
    }
    assert _model(source, "entry").outcome == "UNKNOWN"


def test_b0g4c2_shadowing_sequence_stays_unknown():
    source = {
        "pkg.__init__": "child=1\nimport pkg.child",
        "pkg.child": "pass",
    }
    assert _model(source, "pkg").outcome == "UNKNOWN"


def test_b0g4c2_operation_budget_unknown():
    source = {
        "pkg.__init__": "pass",
        "entry": "import pkg\n" * 10020,
    }
    assert _model(source, "entry").outcome == "UNKNOWN"
