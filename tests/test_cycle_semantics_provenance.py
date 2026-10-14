import ast
import json
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics import (
    extract_import_provenance,
)


def extract(code: str):
    return extract_import_provenance(
        ast.parse(code),
        module_id="p.a",
        source_key="p/a.py",
        source_path=r"C:\fixture\p\a.py",
        source_fingerprint="test-fingerprint",
    )


def test_individual_statements_and_aliases():
    result = extract(
        "import os as o, sys\n"
        "import os\n"
        "from . import child as c, other\n"
    )

    assert len(result.occurrences) == 3

    assert [
        item.ordinal
        for item in result.occurrences
    ] == [0, 1, 2]

    assert result.occurrences[0].aliases == (
        ("os", "o"),
        ("sys", None),
    )

    last = result.occurrences[-1]
    assert last.form == "IMPORT_FROM"
    assert last.module is None
    assert last.level == 1
    assert last.aliases == (
        ("child", "c"),
        ("other", None),
    )


def test_class_function_and_method_scopes():
    result = extract("""
import root

class C:
    import in_class

    def method(self):
        import in_method

def f():
    class D:
        import nested_class
""")

    scopes = [
        [frame.kind for frame in item.scopes]
        for item in result.occurrences
    ]

    assert scopes == [
        [],
        ["CLASS"],
        ["CLASS", "FUNCTION"],
        ["FUNCTION", "CLASS"],
    ]

    assert (
        result.occurrences[2].scopes[-1].name
        == "method"
    )


def test_async_function_scope():
    result = extract("""
async def load():
    import deferred_candidate
""")

    assert len(result.occurrences) == 1

    assert (
        result.occurrences[0].scopes[0].kind
        == "ASYNC_FUNCTION"
    )


def test_conditional_guards_preserved():
    result = extract("""
from typing import TYPE_CHECKING as TC

if TC:
    import typing_only_candidate
else:
    import runtime_candidate

if False:
    import unreachable_candidate
""")

    typing_site = result.occurrences[1]
    alternative = result.occurrences[2]
    false_site = result.occurrences[3]

    assert typing_site.controls[0].branch == "BODY"
    assert "TC" in typing_site.controls[0].expression
    assert alternative.controls[0].branch == "ELSE"
    assert "False" in false_site.controls[0].expression


def test_try_except_else_finally():
    result = extract("""
try:
    import a
except ImportError:
    import b
else:
    import c
finally:
    import d
""")

    assert [
        site.controls[0].kind
        for site in result.occurrences
    ] == [
        "TRY",
        "EXCEPT",
        "TRY_ELSE",
        "FINALLY",
    ]

    assert (
        "ImportError"
        in result.occurrences[1]
        .controls[0].expression
    )


def test_nested_conditions_and_match():
    result = extract("""
for i in range(2):
    if i:
        import x

match value:
    case 1 if enabled:
        import y
""")

    assert [
        frame.kind
        for frame in result.occurrences[0].controls
    ] == ["FOR", "IF"]

    assert (
        result.occurrences[1].controls[0].kind
        == "MATCH"
    )


def test_main_guard_preserved():
    result = extract("""
if __name__ == "__main__":
    import cli_runtime
""")

    assert len(result.occurrences) == 1

    guard = result.occurrences[0].controls[0]
    assert guard.kind == "IF"
    assert "__main__" in guard.expression


def test_dynamic_calls_not_fake_imports():
    assert extract(
        "__import__('target')\n"
    ).occurrences == ()

    assert extract(
        "importlib.import_module('target')\n"
    ).occurrences == ()


def test_multiple_origins_not_deduplicated():
    result = extract("""
import a

def later():
    import a

class C:
    import a
""")

    assert len(result.occurrences) == 3
    assert len({
        (site.line, site.column)
        for site in result.occurrences
    }) == 3


def test_deterministic_no_ast_mutation():
    tree = ast.parse("""
if True:
    import a
    import a
""")

    before = ast.dump(
        tree, include_attributes=True
    )

    kwargs = {
        "module_id": "p.a",
        "source_key": "p/a.py",
        "source_path": r"C:\fixture\p\a.py",
        "source_fingerprint": "fingerprint",
    }

    first = extract_import_provenance(
        tree, **kwargs
    )
    second = extract_import_provenance(
        tree, **kwargs
    )

    assert first == second
    assert len(first.occurrences) == 2

    assert ast.dump(
        tree, include_attributes=True
    ) == before

    json.dumps(asdict(first))


def test_invalid_tree_rejected():
    with pytest.raises(TypeError):
        extract_import_provenance(
            ast.parse("x").body[0],
            module_id="p.a",
            source_key="p/a.py",
            source_path=r"C:\fixture\p\a.py",
            source_fingerprint="fingerprint",
        )
