import ast
import hashlib
import json
from dataclasses import FrozenInstanceError, asdict

import pytest

from contextor.core.source import ParsedSourceInput
from contextor.core.cycle_semantics.edge_sites import (
    analyze_cyclic_import_sites as analyze,
)


def _sources(**items):
    return {
        name: ParsedSourceInput(
            ast.parse(code),
            hashlib.sha256(code.encode()).hexdigest(),
        )
        for name, code in items.items()
    }


def test_plain_import_cycle():
    result = analyze(
        {"a": {"b"}, "b": {"a"}},
        _sources(a="import b", b="import a"),
    )
    component = result.components[0]
    assert component.matched_edge_count == 2
    assert all(
        edge.sites[0].match_kind == "DIRECT_MODULE"
        for edge in component.internal_edges
    )


def test_relative_package_cycle():
    graph = {
        "pkg.__init__": {"pkg.child"},
        "pkg.child": {"pkg.__init__"},
    }
    result = analyze(
        graph,
        _sources(**{
            "pkg.__init__": "from . import child",
            "pkg.child": "from pkg import value",
        }),
    )
    edges = {
        (edge.source, edge.target): edge
        for edge in result.components[0].internal_edges
    }
    assert edges[
        "pkg.__init__", "pkg.child"
    ].sites[0].match_kind == "OPTIONAL_FROM_CHILD"
    assert edges[
        "pkg.child", "pkg.__init__"
    ].sites[0].match_kind == "FROM_BASE"


def test_parent_initializer_candidate():
    graph = {
        "pkg.__init__": {"pkg.child"},
        "pkg.child": {"pkg.__init__"},
    }
    result = analyze(
        graph,
        _sources(**{
            "pkg.__init__": "import pkg.child",
            "pkg.child": "import pkg.child",
        }),
    )
    edge = next(
        edge
        for edge in result.components[0].internal_edges
        if edge.source == "pkg.child"
    )
    assert edge.sites[0].match_kind == "PARENT_INITIALIZER"


def test_function_scope_and_guard_sites_are_not_eager_proofs():
    result = analyze(
        {"a": {"b"}, "b": {"a"}},
        _sources(
            a=(
                "import b\n"
                "def f():\n"
                "    import b\n"
                "if False:\n"
                "    import b"
            ),
            b="import a",
        ),
    )
    edge = next(
        edge
        for edge in result.components[0].internal_edges
        if edge.source == "a"
    )
    assert [
        site.activation_scope
        for site in edge.sites
    ] == [
        "MODULE_TOP_LEVEL",
        "FUNCTION_SCOPED",
        "GUARDED_TOP_LEVEL",
    ]
    assert edge.sites[1].scopes
    assert edge.sites[2].controls


def test_only_function_local_candidate_is_preserved():
    result = analyze(
        {"a": {"b"}, "b": {"a"}},
        _sources(
            a="def f():\n    import b",
            b="import a",
        ),
    )
    edge = next(
        edge
        for edge in result.components[0].internal_edges
        if edge.source == "a"
    )
    assert edge.status == "LEXICAL_CANDIDATES"
    assert edge.sites[0].activation_scope == "FUNCTION_SCOPED"


def test_missing_and_unmatched_not_dropped():
    result = analyze(
        {"a": {"b"}, "b": {"a"}},
        _sources(a="pass"),
    )
    assert {
        edge.status
        for edge in result.components[0].internal_edges
    } == {
        "NO_MATCHING_LEXICAL_SITE",
        "SOURCE_MISSING_OR_INVALID",
    }
    assert result.components[0].unresolved_edge_count == 2


def test_unrelated_sources_do_not_change_results():
    graph = {
        "a": {"b"},
        "b": {"a"},
        "z": set(),
    }
    first = analyze(
        graph,
        _sources(
            a="import b",
            b="import a",
            z="pass",
        ),
    )
    second = analyze(
        graph,
        _sources(
            a="import b",
            b="import a",
            z="import a",
        ),
    )
    assert first == second


def test_from_possible_child_is_not_proof():
    graph = {
        "pkg.__init__": {"pkg.x"},
        "pkg.x": {"pkg.__init__"},
    }
    result = analyze(
        graph,
        _sources(**{
            "pkg.__init__": "from pkg import x",
            "pkg.x": "import pkg",
        }),
    )
    edge = next(
        edge
        for edge in result.components[0].internal_edges
        if edge.source == "pkg.__init__"
    )
    assert edge.sites[0].match_kind == "OPTIONAL_FROM_CHILD"
    assert result.evidence_scope.endswith(
        "NOT_RUNTIME_CERTIFICATION"
    )


def test_no_cycle():
    result = analyze(
        {"a": {"b"}, "b": set()},
        _sources(a="import b", b="pass"),
    )
    assert result.components == ()


def test_invalid_source_ast():
    result = analyze(
        {"a": {"b"}, "b": {"a"}},
        {
            "a": ParsedSourceInput(
                ast.parse("import b"),
                hashlib.sha256(b"import b").hexdigest(),
            ),
            "b": None,
        },
    )
    assert result.components[0].unresolved_edge_count == 1


def test_relative_second_level():
    graph = {
        "p.__init__": {"p.sub.mod"},
        "p.sub.__init__": {"p.__init__"},
        "p.sub.mod": {
            "p.__init__",
            "p.sub.__init__",
        },
    }
    sources = _sources(**{
        "p.__init__": "from p.sub import mod",
        "p.sub.__init__": "from .. import foo",
        "p.sub.mod": "from .. import foo",
    })
    result = analyze(graph, sources)
    edge = next(
        edge
        for edge in result.components[0].internal_edges
        if edge.source == "p.sub.mod"
        and edge.target == "p.__init__"
    )
    assert edge.sites[0].match_kind == "FROM_BASE"


def test_determinism_and_frozen():
    graph = {"a": {"b"}, "b": {"a"}}
    sources = _sources(a="import b", b="import a")
    result = analyze(graph, sources)
    assert result == analyze(graph, sources)
    json.dumps(asdict(result))

    with pytest.raises(FrozenInstanceError):
        result.components[0].matched_edge_count = 99

    assert graph == {
        "a": {"b"},
        "b": {"a"},
    }


def test_invalid_input_raises():
    with pytest.raises(TypeError):
        analyze({"a": {"a"}}, None)

    with pytest.raises(TypeError):
        analyze(None, {})


def test_invalid_fingerprint_is_not_treated_as_source():
    result = analyze(
        {"a": {"b"}, "b": {"a"}},
        {
            "a": ParsedSourceInput(
                ast.parse("import b"),
                "invalid",
            ),
            "b": _sources(b="import a")["b"],
        },
    )
    edge = next(
        edge
        for edge in result.components[0].internal_edges
        if edge.source == "a"
    )
    assert edge.status == "SOURCE_MISSING_OR_INVALID"
