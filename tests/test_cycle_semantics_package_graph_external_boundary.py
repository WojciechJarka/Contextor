"""External imports remain opaque to the closed package cycle model."""

import ast
from pathlib import Path

from contextor.core.cycle_semantics.model_source_closure import (
    compute_cycle_model_source_closures_with_optional_children,
)
from contextor.core.cycle_semantics.package_graph_consistency import (
    assess_package_graph_consistency,
)
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.symbol_engine.indexer import read_imports


def _check(source, *, edges=None):
    graph = {"pkg.__init__": set(), "pkg.a": set()}
    if edges is not None:
        graph["pkg.a"] = set(edges)
        graph["pkg.b"] = set()
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse(source),
    }
    if edges is not None:
        trees["pkg.b"] = ast.parse("pass\n")
    return assess_package_graph_consistency(
        graph, trees, tuple(sorted(trees))
    )


def test_stdlib_import_is_opaque():
    result = _check("import os\n")
    assert result.status == "INDETERMINATE"
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "os"),
    )


def test_stdlib_from_import_is_opaque():
    result = _check("from collections import Counter\n")
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "from", "collections"),
    )
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"


def test_third_party_and_nonexistent_imports_are_equally_opaque():
    result = _check(
        "import orjson\nimport definitely_nonexistent_package_xyz\n"
    )
    assert result.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "orjson"),
        ("pkg.a", 2, "import", "definitely_nonexistent_package_xyz"),
    )
    assert result.status == "INDETERMINATE"


def test_missing_internal_target_still_fails_closed():
    result = _check("import pkg.missing\n")
    assert result.reason == "MISSING_INDEXED_TARGET"
    assert result.unmodeled_external_imports == ()


def test_unresolved_relative_target_still_fails_closed():
    result = _check("from .missing import thing\n")
    assert result.reason == "MISSING_INDEXED_TARGET"
    assert result.unmodeled_external_imports == ()


def test_external_import_does_not_hide_internal_graph_mismatch():
    result = _check("import os\nimport pkg.b\n", edges=())
    assert result.reason == "GRAPH_SOURCE_IMPORT_MISMATCH"
    assert result.unmodeled_external_imports == ()


def test_external_records_are_sorted_without_mutating_inputs():
    graph = {"pkg.__init__": set(), "pkg.a": set()}
    trees = {
        "pkg.a": ast.parse("import zzz\nimport aaa\n"),
        "pkg.__init__": ast.parse("pass\n"),
    }
    before_graph = {name: set(targets) for name, targets in graph.items()}
    before_trees = dict(trees)
    first = assess_package_graph_consistency(
        graph, trees, ("pkg.a", "pkg.__init__")
    )
    second = assess_package_graph_consistency(
        graph, trees, ("pkg.__init__", "pkg.a")
    )
    assert first == second
    assert first.unmodeled_external_imports == (
        ("pkg.a", 1, "import", "zzz"),
        ("pkg.a", 2, "import", "aaa"),
    )
    assert graph == before_graph
    assert trees == before_trees


def test_optional_scc_with_external_import_never_model_passes():
    graph = {
        "pkg.__init__": set(),
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
    }
    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse("import pkg.b\nimport os\n"),
        "pkg.b": ast.parse("import pkg.a\n"),
    }
    imports = {}
    for module_id, tree in trees.items():
        extracted, error = read_imports(
            Path(*module_id.split(".")).with_suffix(".py"),
            tree=tree,
        )
        assert error is None
        imports[module_id] = extracted
    closures = compute_cycle_model_source_closures_with_optional_children(
        graph, imports
    )
    report = analyze_cycle_scenarios(
        graph,
        trees,
        source_selection="OPTIONAL_NAMED_CHILDREN",
        indexed_imports_by_module=imports,
        source_closures=closures,
    )
    component = report.components[0]
    assert component.classification == "INDETERMINATE"
    assert component.coverage == "NONE"
    assert component.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"


def test_g18_p2_p1_external_scope_evidence():
    source = (
        "import os\n"
        "class C:\n"
        "    import pathlib\n"
        "    def method(self):\n"
        "        import json\n"
        "def worker():\n"
        "    if True:\n"
        "        import collections\n"
        "async def async_worker():\n"
        "    import asyncio\n"
        "if True:\n"
        "    import sys\n"
        "try:\n"
        "    import uuid\n"
        "except ImportError:\n"
        "    import warnings\n"
    )

    result = _check(source)

    assert result.status == "INDETERMINATE"
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"

    by_target = {
        item.target: item
        for item in result.external_scope_records
    }

    assert len(by_target) == 8
    assert by_target["os"].primary_scope == "MODULE_BODY"
    assert by_target["pathlib"].primary_scope == "CLASS_BODY"
    assert by_target["json"].primary_scope == "METHOD_BODY"
    assert by_target["collections"].primary_scope == "FUNCTION_BODY"
    assert by_target["asyncio"].primary_scope == "ASYNC_FUNCTION_BODY"
    assert by_target["sys"].ancestry_flags == ("IF",)
    assert by_target["uuid"].ancestry_flags == ("TRY",)
    assert by_target["warnings"].ancestry_flags == (
        "TRY", "EXCEPT_HANDLER"
    )


def test_g18_p2_p1_scope_projection_is_lossless():
    source = (
        "import os, json\n"
        "import pathlib; import pathlib\n"
        "from collections import Counter\n"
    )

    result = _check(source)

    projected = tuple(
        sorted(
            (
                item.importer,
                item.line,
                item.form,
                item.target,
            )
            for item in result.external_scope_records
        )
    )

    assert projected == tuple(
        sorted(result.unmodeled_external_imports)
    )
    assert len(result.external_scope_records) == 5

    pathlib_records = [
        item for item in result.external_scope_records
        if item.target == "pathlib"
    ]

    assert len(pathlib_records) == 2
    assert pathlib_records[0].column != pathlib_records[1].column


def test_g18_p2_p1_deferred_import_remains_opaque():
    result = _check(
        "def worker():\n"
        "    import os\n"
    )

    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    assert result.status == "INDETERMINATE"
    assert result.external_scope_records[0].primary_scope == (
        "FUNCTION_BODY"
    )


def test_g18_p2_p1_internal_mismatch_stays_fail_closed():
    result = _check(
        "import os\n"
        "import pkg.missing\n"
    )

    assert result.status == "INDETERMINATE"
    assert result.reason == "MISSING_INDEXED_TARGET"
    assert result.external_scope_records == ()


def test_g18_p2_p1_deterministic_scope_records():
    source = "import os\nimport json\n"

    first = _check(source)
    second = _check(source)

    assert first == second
    assert first.external_scope_records == second.external_scope_records


def test_g18_p2_p2_repeated_target_alias_identity():
    result = _check(
        "import os as first, os as second\n"
    )

    assert result.status == "INDETERMINATE"
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"

    records = result.external_scope_records
    assert len(records) == 2
    assert {row.site_ordinal for row in records} == {0}
    assert [row.alias_ordinal for row in records] == [0, 1]
    assert [row.local_binding for row in records] == [
        "first", "second"
    ]
    assert [row.target for row in records] == ["os", "os"]


def test_g18_p2_p2_from_member_identity():
    result = _check(
        "from collections import Counter as C, deque\n"
    )

    records = result.external_scope_records
    assert len(records) == 1
    assert records[0].site_ordinal == 0
    assert records[0].alias_ordinal is None
    assert records[0].local_binding is None
    assert records[0].from_members == (
        ("Counter", "C"),
        ("deque", "deque"),
    )


def test_g18_p2_p2_lexical_not_ast_walk_order():
    result = _check(
        "def deferred():\n"
        "    import os\n"
        "import json\n"
    )

    ordered = sorted(
        result.external_scope_records,
        key=lambda row: row.site_ordinal,
    )

    assert [
        (row.target, row.site_ordinal)
        for row in ordered
    ] == [
        ("os", 0),
        ("json", 1),
    ]


def test_g18_p2_p2_same_line_separate_sites():
    result = _check(
        "import pathlib; import pathlib\n"
    )

    records = result.external_scope_records
    assert len(records) == 2
    assert {row.site_ordinal for row in records} == {0, 1}
    assert len({row.column for row in records}) == 2


def test_g18_p2_p2_legacy_projection_unchanged():
    result = _check(
        "import os as first, os as second\n"
        "from collections import Counter, deque\n"
    )

    projected = tuple(sorted(
        (row.importer, row.line, row.form, row.target)
        for row in result.external_scope_records
    ))

    assert projected == tuple(sorted(
        result.unmodeled_external_imports
    ))


def test_g18_p2_p2_unknown_stays_fail_closed():
    result = _check(
        "import os\n"
        "import pkg.missing\n"
    )

    assert result.reason == "MISSING_INDEXED_TARGET"
    assert result.external_scope_records == ()


def _g18_p2_p3_scenario(a_source, b_source="import pkg.a\n"):
    graph = {
        "pkg.__init__": set(),
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
    }

    trees = {
        "pkg.__init__": ast.parse("pass\n"),
        "pkg.a": ast.parse(a_source),
        "pkg.b": ast.parse(b_source),
    }

    imports = {}

    for module_id, tree in trees.items():
        extracted, error = read_imports(
            Path(*module_id.split(".")).with_suffix(".py"),
            tree=tree,
        )
        assert error is None
        imports[module_id] = extracted

    closures = compute_cycle_model_source_closures_with_optional_children(
        graph, imports
    )

    report = analyze_cycle_scenarios(
        graph,
        trees,
        source_selection="OPTIONAL_NAMED_CHILDREN",
        indexed_imports_by_module=imports,
        source_closures=closures,
    )

    assert len(report.components) == 1
    return report.components[0]


def test_g18_p2_p3_deferred_gate_preserves_indeterminate():
    result = _check(
        "def unused():\n"
        "    import os\n"
    )

    assert result.status == "INDETERMINATE"
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    assert result.external_execution_gate == (
        "LEXICALLY_DEFERRED_ONLY"
    )
    assert len(result.unmodeled_external_imports) == 1


def test_g18_p2_p3_eager_gate_stays_blocking():
    result = _check(
        "import os\n"
        "def unused():\n"
        "    import json\n"
    )

    assert result.external_execution_gate == (
        "OPAQUE_EXECUTION_POSSIBLE"
    )
    assert result.reason == "EXTERNAL_IMPORT_EXECUTION_UNMODELED"


def test_g18_p2_p3_uncalled_external_function_model_pass():
    component = _g18_p2_p3_scenario(
        "import pkg.b\n"
        "def unused():\n"
        "    import os\n"
    )

    assert component.classification == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    )
    assert component.coverage == "COMPLETE_FRESH_MEMBER_ENTRIES"
    assert all(
        assessment.outcome == "MODEL_PASS"
        for assessment in component.entry_assessments
    )


def test_g18_p2_p3_called_external_function_unknown():
    component = _g18_p2_p3_scenario(
        "def load():\n"
        "    import os\n"
        "load()\n"
        "import pkg.b\n"
    )

    assert component.classification == "INDETERMINATE"
    assert component.coverage != "NONE"
    assert any(
        assessment.outcome == "UNKNOWN"
        for assessment in component.entry_assessments
    )


def test_g18_p2_p3_async_body_deferred():
    component = _g18_p2_p3_scenario(
        "import pkg.b\n"
        "async def worker():\n"
        "    import os\n"
    )

    assert component.classification == (
        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
    )


def test_g18_p2_p3_async_invocation_not_assumed_safe():
    component = _g18_p2_p3_scenario(
        "import pkg.b\n"
        "async def worker():\n"
        "    import os\n"
        "worker()\n"
    )

    assert component.classification == "INDETERMINATE"
    assert any(
        assessment.outcome == "UNKNOWN"
        for assessment in component.entry_assessments
    )


def test_g18_p2_p3_decorated_function_unknown():
    component = _g18_p2_p3_scenario(
        "import pkg.b\n"
        "@decorator\n"
        "def unused():\n"
        "    import os\n"
    )

    assert component.classification == "INDETERMINATE"
    assert any(
        assessment.outcome == "UNKNOWN"
        for assessment in component.entry_assessments
    )


def test_g18_p2_p3_dynamic_default_unknown():
    component = _g18_p2_p3_scenario(
        "import pkg.b\n"
        "def unused(x=side_effect()):\n"
        "    import os\n"
    )

    assert component.classification == "INDETERMINATE"
    assert any(
        assessment.outcome == "UNKNOWN"
        for assessment in component.entry_assessments
    )


def test_g18_p2_p3_eager_external_scenario_still_blocked():
    component = _g18_p2_p3_scenario(
        "import os\n"
        "import pkg.b\n"
    )

    assert component.classification == "INDETERMINATE"
    assert component.coverage == "NONE"
    assert component.reason == (
        "EXTERNAL_IMPORT_EXECUTION_UNMODELED"
    )
    assert component.entry_assessments == ()


def test_g18_p2_p3_internal_graph_mismatch_stays_blocked():
    result = _check(
        "def unused():\n"
        "    import os\n"
        "import pkg.missing\n"
    )

    assert result.reason == "MISSING_INDEXED_TARGET"
    assert result.external_execution_gate == "NOT_ESTABLISHED"
    assert result.external_scope_records == ()


def test_g18_p2_p3_source_evidence_deterministic():
    source = (
        "def worker():\n"
        "    import os\n"
        "    from collections import deque\n"
    )

    first = _check(source)
    second = _check(source)

    assert first == second
    assert first.external_execution_gate == (
        "LEXICALLY_DEFERRED_ONLY"
    )
