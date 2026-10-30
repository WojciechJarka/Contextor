"""Conditional namespace path-resolution model contracts."""

from __future__ import annotations

from dataclasses import asdict

from contextor.core.cycle_semantics.namespace_path_model import (
    SearchPortion,
    resolve_namespace_path,
)


def _p(name, *files):
    return SearchPortion(name, frozenset(files))


def _resolve(roots, name, *, standard_finder_assumed=True):
    return resolve_namespace_path(
        tuple(roots),
        name,
        standard_finder_assumed=standard_finder_assumed,
    )


def test_t01_namespace_nested_under_regular_package():
    result = _resolve(
        [_p(
            "root",
            "regular/__init__.py",
            "regular/ns/child.py",
        )],
        "regular.ns.child",
    )

    assert result.status == "CONDITIONAL"
    assert tuple(item.kind for item in result.steps) == (
        "REGULAR_PACKAGE",
        "NAMESPACE_PACKAGE",
        "MODULE_FILE",
    )
    assert result.source == "root:regular/ns/child.py"


def test_t02_top_level_namespace():
    result = _resolve(
        [_p("root", "nsp/child.py")],
        "nsp.child",
    )

    assert tuple(item.kind for item in result.steps) == (
        "NAMESPACE_PACKAGE",
        "MODULE_FILE",
    )


def test_t03_two_namespace_portions():
    roots = [
        _p("first", "nsp/left.py"),
        _p("second", "nsp/right.py"),
    ]

    result = _resolve(roots, "nsp")

    assert result.kind == "NAMESPACE_PACKAGE"
    assert result.portions == (
        "first:nsp",
        "second:nsp",
    )
    assert _resolve(
        roots, "nsp.left"
    ).source == "first:nsp/left.py"
    assert _resolve(
        roots, "nsp.right"
    ).source == "second:nsp/right.py"


def test_t04_regular_package_shadows_earlier_namespace():
    roots = [
        _p("namespace", "nsp/child.py"),
        _p("regular", "nsp/__init__.py"),
    ]

    result = _resolve(roots, "nsp")

    assert result.kind == "REGULAR_PACKAGE"
    assert result.source == "regular:nsp/__init__.py"

    missing = _resolve(roots, "nsp.child")
    assert missing.status == "INDETERMINATE"
    assert missing.reason == (
        "TARGET_NOT_IN_SUPPLIED_INVENTORY"
    )


def test_t05_changed_path_inventory_changes_resolution():
    first = _p("first", "nsp/left.py")
    second = _p("second", "nsp/right.py")

    assert _resolve(
        [first], "nsp.right"
    ).status == "INDETERMINATE"

    assert _resolve(
        [second, first], "nsp.right"
    ).status == "CONDITIONAL"


def test_t06_finder_environment_not_proved():
    result = _resolve(
        [_p("root", "nsp/child.py")],
        "nsp.child",
        standard_finder_assumed=False,
    )

    assert result.status == "INDETERMINATE"
    assert result.reason == (
        "IMPORT_FINDER_ENVIRONMENT_NOT_PROVED"
    )
    assert result.steps == ()


def test_t07_plain_module_cannot_be_package_parent():
    result = _resolve(
        [_p("root", "nsp.py", "nsp/child.py")],
        "nsp.child",
    )

    assert result.status == "INDETERMINATE"
    assert result.reason == "MODULE_IS_NOT_A_PACKAGE"


def test_t08_alternative_loader_fails_closed():
    result = _resolve(
        [_p(
            "root",
            "nsp/__init__.py",
            "nsp/child.pyd",
        )],
        "nsp.child",
    )

    assert result.status == "INDETERMINATE"
    assert result.reason == (
        "ALTERNATIVE_LOADER_CANDIDATE"
    )


def test_t08b_tagged_alternative_loaders_fail_closed():
    variants = (
        "pkg/child.cp310-win_amd64.pyd",
        "pkg/child.cpython-310-x86_64-linux-gnu.so",
        "pkg/child.pyc",
        "pkg/__init__.cp310-win_amd64.pyd",
        "pkg/__init__.cpython-310-x86_64-linux-gnu.so",
    )

    for filename in variants:
        result = _resolve(
            [_p(
                "root",
                "pkg/__init__.py",
                "pkg/child.py",
                filename,
            )],
            "pkg.child",
        )

        assert result.status == "INDETERMINATE"
        assert result.reason == "ALTERNATIVE_LOADER_CANDIDATE"


def test_t08c_alternative_in_earlier_namespace_portion():
    roots = (
        _p(
            "first",
            "nsp/left.py",
            "nsp/child.cp310-win_amd64.pyd",
        ),
        _p("second", "nsp/child.py"),
    )

    result = _resolve(roots, "nsp.child")

    assert result.status == "INDETERMINATE"
    assert result.reason == "ALTERNATIVE_LOADER_CANDIDATE"


def test_t08d_unrelated_file_does_not_block_source():
    result = _resolve(
        [_p(
            "root",
            "pkg/__init__.py",
            "pkg/child.py",
            "pkg/child.notes.txt",
        )],
        "pkg.child",
    )

    assert result.status == "CONDITIONAL"
    assert result.source == "root:pkg/child.py"


def test_t09_invalid_inventory_fails_closed():
    assert _resolve(
        [_p("root", "../evil.py")],
        "pkg",
    ).status == "INDETERMINATE"

    assert _resolve(
        [_p("root", "ok.py"), _p("root", "other.py")],
        "ok",
    ).status == "INDETERMINATE"

    assert _resolve(
        [_p("root", "x.py")],
        "missing..pkg",
    ).status == "INDETERMINATE"


def test_t10_regular_initializer_precedes_module_file():
    result = _resolve(
        [_p(
            "root",
            "pkg.py",
            "pkg/__init__.py",
            "pkg/child.py",
        )],
        "pkg.child",
    )

    assert result.status == "CONDITIONAL"
    assert result.steps[0].kind == "REGULAR_PACKAGE"


def test_t11_deterministic_and_not_runtime_certified():
    roots = (_p("root", "nsp/child.py"),)

    first = _resolve(roots, "nsp.child")
    second = _resolve(roots, "nsp.child")

    assert first == second
    assert asdict(first) == asdict(second)
    assert first.authority == (
        "CONDITIONAL_ORDERED_PATH_INVENTORY_NOT_RUNTIME_PROOF"
    )
    assert first.status == "CONDITIONAL"
