import ast
import json
import subprocess
import sys
from dataclasses import asdict

import pytest

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


def test_b0g4c5_deferred_function_import_not_executed(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    import pkg.child\n"
            "value=7"
        ),
        "pkg.child": "import pkg\nx=pkg.missing",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert not any(
        e.operation == "START_IMPORT"
        and e.target == "pkg.child"
        for e in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c5_call_activates_early_binding_hazard(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    import pkg.child\n"
            "load()\n"
            "value=7"
        ),
        "pkg.child": "import pkg\nx=pkg.value",
    }
    result = _model(source, "pkg")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "value"
    assert not _actual(tmp_path, source, "pkg")


def test_b0g4c5_binding_before_call_passes(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    import pkg.child\n"
            "value=7\n"
            "load()"
        ),
        "pkg.child": "import pkg\nx=pkg.value",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c5_function_local_import_not_exported(tmp_path):
    source = {
        "pkg.__init__": (
            "def activate():\n"
            "    import pkg.child as local_only\n"
            "activate()"
        ),
        "pkg.child": "from pkg import local_only",
    }
    result = _model(source, "pkg")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg"
    assert result.symbol == "local_only"
    assert not _actual(tmp_path, source, "pkg")


def test_b0g4c5_repeated_calls_import_child_once(tmp_path):
    source = {
        "pkg.__init__": (
            "def activate():\n"
            "    import pkg.child\n"
            "activate()\n"
            "activate()"
        ),
        "pkg.child": "value=7",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert sum(
        e.operation == "START_IMPORT"
        and e.target == "pkg.child"
        for e in result.events
    ) == 1
    assert sum(
        e.operation == "CALL_FUNCTION"
        for e in result.events
    ) == 2
    assert _actual(tmp_path, source, "pkg")


def test_b0g4c5_plain_flat_module_function_call(tmp_path):
    source = {
        "a": (
            "def load():\n"
            "    import b\n"
            "load()\n"
            "value=7"
        ),
        "b": "import a\nx=a.value",
    }
    result = _model(source, "a")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert not _actual(tmp_path, source, "a")


def test_b0g4c5_exported_definition_is_available(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    pass"
        ),
        "pkg.user": "from pkg import load",
    }
    result = _model(source, "pkg.user")
    assert result.outcome == "MODEL_PASS"
    assert _actual(tmp_path, source, "pkg.user")


def test_b0g4c5_foreign_function_call_unknown():
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    import pkg.child"
        ),
        "pkg.child": "pass",
        "pkg.user": (
            "from pkg import load\n"
            "load()"
        ),
    }
    assert _model(source, "pkg.user").outcome == "UNKNOWN"


def test_b0g4c5_call_without_local_definition_unknown():
    source = {
        "pkg.__init__": "missing()",
    }
    assert _model(source, "pkg").outcome == "UNKNOWN"


def test_b0g4c5_shadowed_function_call_unknown(tmp_path):
    source = {
        "pkg.__init__": (
            "def load():\n"
            "    pass\n"
            "load=3\n"
            "load()"
        ),
    }
    assert _model(source, "pkg").outcome == "UNKNOWN"
    assert not _actual(tmp_path, source, "pkg")


def test_b0g4c5_definition_effects_updated_contract():
    samples = (
        (
            "def f(x=1):\n    import pkg.child",
            "MODEL_PASS",
        ),
        (
            "def f(x):\n    import pkg.child",
            "MODEL_PASS",
        ),
        (
            "@decorator\ndef f():\n    import pkg.child",
            "UNKNOWN",
        ),
        (
            "def f() -> int:\n    import pkg.child",
            "UNKNOWN",
        ),
        (
            "def f():\n    helper()",
            "MODEL_PASS",
        ),
        (
            "async def f():\n    import pkg.child",
            "UNKNOWN",
        ),
        (
            "def f():\n    return 1",
            "MODEL_PASS",
        ),
    )

    for code, expected in samples:
        result = _model(
            {"pkg.__init__": code, "pkg.child": "pass"},
            "pkg",
        )

        assert result.outcome == expected


def test_b0g4c15_uncalled_function_local_from_supported(tmp_path):
    source = {
        "pkg.__init__": (
            "def f():\n"
            "    from pkg import child"
        ),
        "pkg.child": "pass",
    }

    result = _model(source, "pkg")

    assert result.outcome == "MODEL_PASS"

    assert any(
        event.operation == "DEFINE_FUNCTION"
        and event.symbol == "f"
        for event in result.events
    )

    assert not any(
        event.operation in {
            "FUNCTION_LOCAL_FROM",
            "FUNCTION_LOCAL_FROM_REENTRANT_CHILD",
        }
        for event in result.events
    )

    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "pkg.child"
        for event in result.events
    )

    assert _actual(tmp_path, source, "pkg")


def test_b0g4c5_deterministic_ast_unchanged():
    source = {
        "pkg.__init__": ast.parse(
            "def activate():\n"
            "    import pkg.child\n"
            "activate()"
        ),
        "pkg.child": ast.parse("pass"),
    }

    before = {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in source.items()
    }

    first = evaluate_package_import_order(source, "pkg")
    second = evaluate_package_import_order(source, "pkg")

    assert first == second
    assert first.outcome == "MODEL_PASS"

    assert {
        key: ast.dump(tree, include_attributes=True)
        for key, tree in source.items()
    } == before

    json.dumps(asdict(first))


@pytest.mark.parametrize(
    "condition,expected,active",
    [
        ("False", "MODEL_PASS", False),
        ("True", "EARLY_BINDING_HAZARD", True),
    ],
)
def test_p1d3_d1_literal_branch_activation(tmp_path, condition, expected, active):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": f"if {condition}:\n    import pkg.b\nvalue = 1",
        "pkg.b": "from pkg.a import value",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == expected
    assert any(
        event.operation == "START_IMPORT" and event.target == "pkg.b"
        for event in result.events
    ) is active
    assert _actual(tmp_path, source, "pkg.a") is (not active)


def test_p1d3_d1_false_else_and_name_guard(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": (
            "if False:\n    pass\nelse:\n    import pkg.b\n"
            "if __name__ == '__main__':\n    import pkg.missing\n"
            "value = 1"
        ),
        "pkg.b": "pass",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == "MODEL_PASS"
    assert any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
    assert _actual(tmp_path, source, "pkg.a")


@pytest.mark.parametrize(
    "body,expected,operation",
    [
        ("class Loader:\n    import pkg.b\nvalue = 1", "EARLY_BINDING_HAZARD", "CLASS_LOCAL_IMPORT"),
        ("value = 1\nclass Loader:\n    import pkg.b", "MODEL_PASS", "CLASS_LOCAL_IMPORT"),
        ("class Loader:\n    from pkg.b import value", "MODEL_PASS", "CLASS_LOCAL_FROM"),
        ("class Loader:\n    import pkg.b as local_child", "MODEL_PASS", "CLASS_LOCAL_IMPORT"),
    ],
)
def test_p1d3_d1_class_import_timing(tmp_path, body, expected, operation):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": body,
        "pkg.b": "from pkg.a import value" if "value = 1" in body else "value = 2",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == expected
    if expected == "MODEL_PASS":
        assert any(e.operation == operation for e in result.events)
    else:
        assert any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
    assert _actual(tmp_path, source, "pkg.a") is (expected == "MODEL_PASS")


def test_p1d3_d1_class_local_binding_does_not_escape(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "class Loader:\n    import pkg.b as local_child",
        "pkg.b": "from pkg.a import local_child",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == "EARLY_BINDING_HAZARD"
    assert result.target_module == "pkg.a"
    assert result.symbol == "local_child"
    assert not any(e.operation == "DEFINE_PASSIVE_CLASS" for e in result.events)
    assert not _actual(tmp_path, source, "pkg.a")


def test_p1d3_d1_class_local_reentrant_child_from(tmp_path):
    source = {
        "pkg.__init__": "from . import child",
        "pkg.child": "class Loader:\n    from pkg import child",
    }
    result = _model(source, "pkg")
    assert result.outcome == "MODEL_PASS"
    assert any(
        event.operation == "CLASS_LOCAL_FROM_REENTRANT_CHILD"
        and event.target == "pkg.child"
        for event in result.events
    )
    assert _actual(tmp_path, source, "pkg")


def test_p1d3_d1_uncalled_method_import_is_deferred(tmp_path):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "class Loader:\n    def load(self):\n        import pkg.b\nvalue = 1",
        "pkg.b": "from pkg.a import value",
    }
    result = _model(source, "pkg.a")
    assert result.outcome == "MODEL_PASS"
    assert not any(e.operation == "START_IMPORT" and e.target == "pkg.b" for e in result.events)
    assert _actual(tmp_path, source, "pkg.a")


@pytest.mark.parametrize("condition", ["unknown_condition", "1"])
def test_p1d3_d1_unsupported_condition(condition):
    source = {
        "pkg.__init__": "pass",
        "pkg.a": f"if {condition}:\n    import pkg.b",
        "pkg.b": "pass",
    }
    assert _model(source, "pkg.a").outcome == "UNKNOWN"


@pytest.mark.parametrize("body", [
    "class Loader(Base):\n    import pkg.b",
    "class Loader(metaclass=Meta):\n    import pkg.b",
    "@decorator\nclass Loader:\n    import pkg.b",
    "class Loader:\n    helper()",
    "class Loader:\n    x = helper()",
    "class Loader:\n    class Nested:\n        pass",
    "class Loader:\n    if True:\n        import pkg.b",
    "class Loader:\n    from pkg.b import *",
])
def test_p1d3_d1_unsupported_class_effects(body):
    source = {"pkg.__init__": "pass", "pkg.a": body, "pkg.b": "pass"}
    assert _model(source, "pkg.a").outcome == "UNKNOWN"


def test_p1d3_d1_invalid_unselected_branch_fails_compile():
    source = {
        "pkg.__init__": "pass",
        "pkg.a": "if False:\n    return 1\nelse:\n    pass",
    }
    assert _model(source, "pkg.a").outcome == "UNKNOWN"


def test_p1d3_d1_deterministic_events_and_ast_unchanged():
    sources = {
        "pkg.__init__": ast.parse("pass"),
        "pkg.a": ast.parse("if True:\n    class Loader:\n        import pkg.b"),
        "pkg.b": ast.parse("from pkg.a import Loader"),
    }
    before = {key: ast.dump(tree, include_attributes=True) for key, tree in sources.items()}
    first = evaluate_package_import_order(sources, "pkg.a")
    second = evaluate_package_import_order(sources, "pkg.a")
    assert first == second
    assert first.events == second.events
    assert first.outcome == "EARLY_BINDING_HAZARD"
    assert {key: ast.dump(tree, include_attributes=True) for key, tree in sources.items()} == before
