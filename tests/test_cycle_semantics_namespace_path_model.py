"""Conditional namespace path-resolution model contracts."""

from __future__ import annotations

import ast

from dataclasses import asdict

from contextor.core.cycle_semantics.package_model import (
    evaluate_conditional_namespace_import_order,
    evaluate_package_import_order,
)
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


def _g18_p2_p5_sources(*, hazard=False):
    return {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.ns.a": ast.parse(
            (
                "import pkg.ns.b\n"
                "value = 1\n"
            )
            if hazard else (
                "value = 1\n"
                "import pkg.ns.b\n"
            )
        ),
        "pkg.ns.b": ast.parse(
            "from pkg.ns.a import value\n"
        ),
    }


def _g18_p2_p5_portions():
    return (
        SearchPortion(
            "root",
            frozenset({
                "pkg/__init__.py",
                "pkg/ns/a.py",
                "pkg/ns/b.py",
            }),
        ),
    )


def test_g18_p2_p5_default_namespace_remains_unknown():
    sources = _g18_p2_p5_sources()

    result = evaluate_package_import_order(
        sources,
        "pkg.ns.a",
    )

    assert result.outcome == "UNKNOWN"


def test_g18_p2_p5_conditional_safe_order():
    sources = _g18_p2_p5_sources()

    result = evaluate_conditional_namespace_import_order(
        sources,
        "pkg.ns.a",
        _g18_p2_p5_portions(),
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.reason is None
    assert result.model_assessment is not None
    assert result.model_assessment.outcome == "MODEL_PASS"
    assert result.namespace_parents == ("pkg.ns",)
    assert result.authority == (
        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
        "NOT_RUNTIME_OR_LIVE_PROOF"
    )


def test_g18_p2_p5_conditional_early_binding_hazard():
    sources = _g18_p2_p5_sources(hazard=True)

    result = evaluate_conditional_namespace_import_order(
        sources,
        "pkg.ns.a",
        _g18_p2_p5_portions(),
    )

    assert result.outcome == (
        "CONDITIONAL_EARLY_BINDING_HAZARD"
    )
    assert result.model_assessment is not None
    assert result.model_assessment.outcome == (
        "EARLY_BINDING_HAZARD"
    )
    assert result.model_assessment.target_module == (
        "pkg.ns.a"
    )
    assert result.model_assessment.symbol == "value"


def test_g18_p2_p5_other_entry_can_pass():
    sources = _g18_p2_p5_sources(hazard=True)

    result = evaluate_conditional_namespace_import_order(
        sources,
        "pkg.ns.b",
        _g18_p2_p5_portions(),
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"


def test_g18_p2_p5_two_namespace_portions():
    sources = {
        "ns.a": ast.parse(
            "value = 1\n"
            "import ns.b\n"
        ),
        "ns.b": ast.parse(
            "from ns.a import value\n"
        ),
    }

    portions = (
        SearchPortion(
            "first",
            frozenset({"ns/a.py"}),
        ),
        SearchPortion(
            "second",
            frozenset({"ns/b.py"}),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.namespace_parents == ("ns",)


def test_g18_p2_p5_unlisted_shadowing_source_unknown():
    sources = {
        "ns.a": ast.parse(
            "value = 1\n"
            "import ns.b\n"
        ),
        "ns.b": ast.parse(
            "from ns.a import value\n"
        ),
    }

    portions = (
        SearchPortion(
            "namespace",
            frozenset({
                "ns/a.py",
                "ns/b.py",
            }),
        ),
        SearchPortion(
            "shadow",
            frozenset({
                "ns/__init__.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == (
        "INVENTORY_SOURCE_DOMAIN_MISMATCH"
    )


def _p10_assess(sources, entry="ns.a"):
    paths = frozenset(
        module.replace(".", "/") + ".py"
        for module in sources
    )

    return evaluate_conditional_namespace_import_order(
        sources,
        entry,
        (SearchPortion("root", paths),),
        target_python_version=(3, 15),
    )


def test_p10_deferred_unreached_decorator_does_not_block():
    sources = {
        "ns.a": ast.parse(
            "def later():\n"
            "    import ns.unused\n"
            "value = 1\n"
        ),
        "ns.unused": ast.parse(
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }

    before = {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in sources.items()
    }

    first = _p10_assess(sources)
    second = _p10_assess(sources)

    assert first == second
    assert first.outcome == "CONDITIONAL_MODEL_PASS"
    assert first.model_assessment is not None

    assert not any(
        event.operation == "START_IMPORT"
        and event.target == "ns.unused"
        for event in first.model_assessment.events
    )

    assert before == {
        name: ast.dump(tree, include_attributes=True)
        for name, tree in sources.items()
    }


def test_p10_reached_decorated_class_still_unknown():
    sources = {
        "ns.a": ast.parse("import ns.bad"),
        "ns.bad": ast.parse(
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }

    result = _p10_assess(sources)

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "ns.bad"

    assert any(
        event.operation == "START_IMPORT"
        and event.target == "ns.bad"
        for event in result.model_assessment.events
    )


def test_p10_from_child_reached_decorator_still_unknown():
    sources = {
        "ns.a": ast.parse("from ns import bad"),
        "ns.bad": ast.parse(
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }

    result = _p10_assess(sources)

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "ns.bad"


def test_p10_regular_parent_initializer_not_skipped():
    sources = {
        "pkg.__init__": ast.parse(
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
        "pkg.ns.a": ast.parse("pass"),
    }

    result = _p10_assess(
        sources,
        entry="pkg.ns.a",
    )

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "pkg"


def test_p10_unselected_false_branch_remains_unvisited():
    sources = {
        "ns.a": ast.parse(
            "if False:\n"
            "    import ns.bad\n"
            "value = 1\n"
        ),
        "ns.bad": ast.parse(
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }

    result = _p10_assess(sources)

    assert result.outcome == "CONDITIONAL_MODEL_PASS"


def test_p10_compile_invalid_unreached_source_fails_closed():
    sources = {
        "ns.a": ast.parse(
            "def later():\n"
            "    import ns.bad\n"
        ),
        "ns.bad": ast.parse(
            "def broken():\n"
            "    break\n"
        ),
    }

    result = _p10_assess(sources)

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "ns.bad"
    assert result.model_assessment.events == ()


def test_p10_lazy_package_child_shadow_remains_unknown():
    sources = {
        "pkg.__init__": ast.parse(
            "def child():\n"
            "    pass\n"
        ),
        "pkg.ns.a": ast.parse(
            "def later():\n"
            "    import pkg.child\n"
        ),
        "pkg.child": ast.parse("pass"),
    }

    result = _p10_assess(
        sources,
        entry="pkg.ns.a",
    )

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "pkg"


def test_p10_early_binding_hazard_is_not_hidden():
    sources = {
        "ns.a": ast.parse(
            "from ns.b import ready\n"
            "ready = 1\n"
            "def later():\n"
            "    import ns.unused\n"
        ),
        "ns.b": ast.parse(
            "from ns.a import ready\n"
        ),
        "ns.unused": ast.parse(
            "@unknown_decorator\n"
            "class Bad:\n"
            "    pass\n"
        ),
    }

    result = _p10_assess(sources)

    assert result.outcome == (
        "CONDITIONAL_EARLY_BINDING_HAZARD"
    )
    assert result.model_assessment is not None
    assert result.model_assessment.outcome == (
        "EARLY_BINDING_HAZARD"
    )
    assert any(
        event.operation == "EARLY_BINDING_HAZARD"
        for event in result.model_assessment.events
    )


def test_p10_reached_external_import_still_unknown():
    sources = {
        "ns.a": ast.parse(
            "import missing_external_xyz\n"
        ),
    }

    result = _p10_assess(sources)

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == (
        "missing_external_xyz"
    )


def _p9_annotation_sources(code):
    return {"ns.a": ast.parse(code)}


def _p9_annotation_portions():
    return (
        SearchPortion(
            "root",
            frozenset({"ns/a.py"}),
        ),
    )


def test_p9_default_annotation_version_stays_unknown():
    sources = _p9_annotation_sources(
        "class Holder:\n"
        "    def method(self, value: Later) -> Later:\n"
        "        pass\n"
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        _p9_annotation_portions(),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
    assert result.target_python_version is None


def test_p9_cpython315_deferred_method_annotations():
    sources = _p9_annotation_sources(
        "class Holder:\n"
        "    def method(self, value: side_effect())"
        " -> Later:\n"
        "        pass\n"
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        _p9_annotation_portions(),
        target_python_version=(3, 15),
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.reason is None
    assert result.target_python_version == (3, 15)
    assert result.model_assessment is not None
    assert result.model_assessment.outcome == "MODEL_PASS"
    assert result.authority == (
        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
        "NOT_RUNTIME_OR_LIVE_PROOF"
    )


def test_p9_target_interpreter_mismatch_fails_closed():
    sources = _p9_annotation_sources("pass\n")

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        _p9_annotation_portions(),
        target_python_version=(3, 14),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "TARGET_INTERPRETER_UNVERIFIED"
    assert result.model_assessment is None


def test_p9_invalid_target_version_fails_closed():
    sources = _p9_annotation_sources("pass\n")

    for version in ((True, 15), "3.15", (3,), (3, 16)):
        result = evaluate_conditional_namespace_import_order(
            sources,
            "ns.a",
            _p9_annotation_portions(),
            target_python_version=version,
        )

        assert result.outcome == "UNKNOWN"
        assert result.model_assessment is None
        assert result.reason in {
            "INVALID_TARGET_PYTHON_VERSION",
            "UNSUPPORTED_TARGET_PYTHON_VERSION",
        }


def test_p9_dynamic_default_remains_unknown():
    sources = _p9_annotation_sources(
        "class Holder:\n"
        "    def method(self, value: Later"
        " = side_effect()):\n"
        "        pass\n"
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        _p9_annotation_portions(),
        target_python_version=(3, 15),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"


def test_p9_annotation_introspection_remains_unknown():
    sources = _p9_annotation_sources(
        "def method(value: side_effect()):\n"
        "    pass\n"
        "print(method.__annotations__)\n"
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        _p9_annotation_portions(),
        target_python_version=(3, 15),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"


def test_p9_external_import_still_unknown():
    sources = _p9_annotation_sources(
        "import missing_external_xyz\n"
        "class Holder:\n"
        "    def method(self, x: Later):\n"
        "        pass\n"
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        _p9_annotation_portions(),
        target_python_version=(3, 15),
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == (
        "missing_external_xyz"
    )


def test_g18_p2_p5_alternative_loader_unknown():
    sources = {
        "ns.a": ast.parse(
            "value = 1\n"
            "import ns.b\n"
        ),
        "ns.b": ast.parse(
            "from ns.a import value\n"
        ),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "ns/a.py",
                "ns/b.py",
                "ns/a.cp315-win_amd64.pyd",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == (
        "CONDITIONAL_PATH_UNRESOLVED:ns.a"
    )


def test_g18_p2_p5_missing_source_unknown():
    sources = _g18_p2_p5_sources()

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "pkg/__init__.py",
                "pkg/ns/a.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "pkg.ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == (
        "INVENTORY_SOURCE_DOMAIN_MISMATCH"
    )


def test_g18_p2_p5_no_namespace_parent_unknown():
    sources = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse("value = 1\n"),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "pkg/__init__.py",
                "pkg/a.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "pkg.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "NO_NAMESPACE_PARENT"


def test_g18_p2_p5_explicit_synthetic_initializer_rejected():
    sources = {
        "ns.a": ast.parse(
            "import ns.__init__\n"
        ),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({"ns/a.py"}),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == (
        "SYNTHETIC_INITIALIZER_REFERENCE"
    )


def test_g18_p2_p5_external_execution_still_unknown():
    sources = {
        "ns.a": ast.parse(
            "import os\n"
            "import ns.b\n"
        ),
        "ns.b": ast.parse(
            "import ns.a\n"
        ),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "ns/a.py",
                "ns/b.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"


def test_g18_p2_p5_deterministic_and_ast_immutable():
    sources = _g18_p2_p5_sources()

    before = {
        name: ast.dump(
            tree,
            include_attributes=True,
        )
        for name, tree in sources.items()
    }

    first = evaluate_conditional_namespace_import_order(
        sources,
        "pkg.ns.a",
        _g18_p2_p5_portions(),
    )

    second = evaluate_conditional_namespace_import_order(
        sources,
        "pkg.ns.a",
        _g18_p2_p5_portions(),
    )

    assert first == second
    assert first.outcome == "CONDITIONAL_MODEL_PASS"

    assert before == {
        name: ast.dump(
            tree,
            include_attributes=True,
        )
        for name, tree in sources.items()
    }


def test_g18_p2_p7_conditional_model_accepts_308_sources():
    sources = {
        f"ns.m{index:05d}": ast.parse("pass\n")
        for index in range(308)
    }

    portions = (
        SearchPortion(
            "root",
            frozenset(
                f"ns/m{index:05d}.py"
                for index in range(308)
            ),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.m00000",
        portions,
    )

    assert len(sources) == 308
    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.reason is None
    assert result.namespace_parents == ("ns",)
    assert result.model_assessment is not None
    assert result.model_assessment.outcome == "MODEL_PASS"
    assert result.authority == (
        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
        "NOT_RUNTIME_OR_LIVE_PROOF"
    )


def test_g18_p2_p8_unreachable_unsupported_module():
    sources = {
        "ns.a": ast.parse("pass\n"),
        "ns.unused": ast.parse(
            "raise RuntimeError('unused')\n"
        ),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "ns/a.py",
                "ns/unused.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"
    assert result.reason is None


def test_g18_p2_p8_direct_imported_unsupported_blocks():
    sources = {
        "ns.a": ast.parse("import ns.bad\n"),
        "ns.bad": ast.parse(
            "raise RuntimeError('bad')\n"
        ),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "ns/a.py",
                "ns/bad.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == "RESTRICTED_MODEL_UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "ns.bad"


def test_g18_p2_p8_from_child_not_omitted():
    sources = {
        "ns.a": ast.parse("from ns import bad\n"),
        "ns.bad": ast.parse(
            "raise RuntimeError('bad')\n"
        ),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "ns/a.py",
                "ns/bad.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "ns.bad"


def test_g18_p2_p8_relative_from_child_not_omitted():
    sources = {
        "ns.a": ast.parse("from . import bad\n"),
        "ns.bad": ast.parse(
            "raise RuntimeError('bad')\n"
        ),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "ns/a.py",
                "ns/bad.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "ns.bad"


def test_g18_p2_p8_parent_initializer_not_omitted():
    sources = {
        "pkg.__init__": ast.parse(
            "raise RuntimeError('initializer')\n"
        ),
        "pkg.ns.a": ast.parse("pass\n"),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({
                "pkg/__init__.py",
                "pkg/ns/a.py",
            }),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "pkg.ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.model_assessment is not None
    assert result.model_assessment.target_module == "pkg"


def test_g18_p2_p8_unrelated_two_portion_source():
    sources = {
        "ns.a": ast.parse("pass\n"),
        "ns.unused": ast.parse(
            "raise RuntimeError('unused')\n"
        ),
    }

    portions = (
        SearchPortion(
            "first",
            frozenset({"ns/a.py"}),
        ),
        SearchPortion(
            "second",
            frozenset({"ns/unused.py"}),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "CONDITIONAL_MODEL_PASS"


def test_g18_p2_p8_existing_hazard_still_detected():
    result = evaluate_conditional_namespace_import_order(
        _g18_p2_p5_sources(hazard=True),
        "pkg.ns.a",
        _g18_p2_p5_portions(),
    )

    assert result.outcome == (
        "CONDITIONAL_EARLY_BINDING_HAZARD"
    )
    assert result.model_assessment is not None
    assert result.model_assessment.symbol == "value"


def test_g18_p2_p8_no_full_inventory_shortcut():
    sources = {
        "ns.a": ast.parse("pass\n"),
        "ns.unused": ast.parse("pass\n"),
    }

    portions = (
        SearchPortion(
            "root",
            frozenset({"ns/a.py"}),
        ),
    )

    result = evaluate_conditional_namespace_import_order(
        sources,
        "ns.a",
        portions,
    )

    assert result.outcome == "UNKNOWN"
    assert result.reason == (
        "INVENTORY_SOURCE_DOMAIN_MISMATCH"
    )
