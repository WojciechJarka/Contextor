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


def test_b0g4c3_reentrant_child_uses_same_thread_fallback(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "from pkg import child",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM_REENTRANT_CHILD"
        and event.target == "pkg.child"
        and event.module == "pkg.child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c2_missing_member_no_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "entry": "from pkg import missing",
    }
    result = _model(source, "entry")
    assert result.outcome == "MISSING_EXPORT"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c4_multiple_fromlist_members_supported(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a, b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


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


def test_b0g4c3_early_read_from_reentrant_child(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": (
            "from pkg import child\n"
            "x=child.value\n"
            "value=7"
        ),
    }
    result = _model(source, "pkg")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg.child"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "pkg")


def test_b0g4c3_bound_attribute_before_reentrant_read(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": (
            "value=7\n"
            "from pkg import child\n"
            "x=child.value"
        ),
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c3_relative_reentrant_child(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "from . import child",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM_REENTRANT_CHILD"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c3_explicit_from_alias(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": (
            "value=7\n"
            "from pkg import child as c\n"
            "x=c.value"
        ),
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM_REENTRANT_CHILD"
        and event.symbol == "child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c3_nested_regular_package_fallback(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub.__init__": "from . import child",
        "pkg.sub.child": "from pkg.sub import child",
    }
    result = _model(source, "pkg.sub")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "FROM_REENTRANT_CHILD"
        and event.target == "pkg.sub.child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg.sub")


def test_b0g4c4_multi_member_missing_export(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.child": "pass",
        "entry": "from pkg import child, missing",
    }
    result = _model(source, "entry")
    assert result.outcome == "MISSING_EXPORT"
    assert result.target_module == "pkg"
    assert result.symbol == "missing"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c4_preparation_before_local_binding_hazard(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "value=1",
        "pkg.b": "import entry\nx=entry.a",
        "entry": "from pkg import a,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "entry"
    assert result.symbol == "a"
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c4_all_prepares_before_from_bindings(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    operations = [
        e.operation
        for e in result.events
        if e.module == "entry"
        and e.operation in {"PREPARE_FROM_MEMBER", "FROM"}
    ]
    assert operations == [
        "PREPARE_FROM_MEMBER",
        "PREPARE_FROM_MEMBER",
        "FROM",
        "FROM",
    ]
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_aliases_after_preparation(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "value=1",
        "pkg.b": "value=2",
        "entry": "from pkg import a as aa,b as bb\nx=aa.value",
    }
    assert _model(source, "entry").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_multi_from_plain_module(tmp_path):
    source = {
        "provider": "x=1\ny=2",
        "entry": "from provider import x,y",
    }
    assert _model(source, "entry").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_relative_multi_in_initializer(tmp_path):
    source = {
        "pkg.__init__": "from . import a,b",
        "pkg.a": "value=1",
        "pkg.b": "from pkg import a\nx=a.value",
    }
    assert _model(source, "pkg").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c4_relative_multi_in_module(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "value=1",
        "pkg.b": "value=2",
        "pkg.user": "from . import a,b",
    }
    assert _model(source, "pkg.user").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.user")


def test_b0g4c4_nested_relative_multi(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.sub.__init__": "from . import a,b",
        "pkg.sub.a": "pass",
        "pkg.sub.b": "pass",
    }
    assert _model(source, "pkg.sub").outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.sub")


def test_b0g4c4_attribute_precedence_during_preparation(tmp_path):
    source = {
        "pkg.__init__": "a=7",
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert not any(
        e.operation == "START_IMPORT" and e.target == "pkg.a"
        for e in result.events
    )
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_reentrant_child_chain(tmp_path):
    source = {
        "pkg.__init__": "from . import a,b",
        "pkg.a": "from pkg import b",
        "pkg.b": "from pkg import a",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        e.operation == "FROM_REENTRANT_CHILD"
        for e in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c4_later_child_loads_before_missing_export(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import missing,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MISSING_EXPORT"
    assert ("pkg.b", "READY") in [
        (e.module, e.operation)
        for e in result.events
    ]
    assert not _actual(tmp_path, source, "entry")


def test_b0g4c4_sibling_uses_prepared_child(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "value=1",
        "pkg.b": "from pkg import a\nx=a.value",
        "entry": "from pkg import a,b",
    }
    result = _model(source, "entry")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "entry")


def test_b0g4c4_namespace_layout_remains_unknown():
    source = {
        "pkg.a": "pass",
        "pkg.b": "pass",
        "entry": "from pkg import a,b",
    }
    assert _model(source, "entry").outcome == "UNKNOWN"
