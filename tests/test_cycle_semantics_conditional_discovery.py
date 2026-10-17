"""Focused synthetic contracts for conditional reexport discovery."""

import ast
from dataclasses import asdict
from hashlib import sha256
import json

import pytest

from contextor.core.cycle_semantics.conditional_discovery import (
    discover_conditional_reexports,
)
from contextor.core.cycle_semantics.edge_sites import analyze_cyclic_import_sites
from contextor.core.source import ParsedSourceInput


GRAPH = {
    "repo.__init__": ("repo.main",),
    "repo.main": ("repo.filters", "ui.__init__"),
    "repo.filters": ("ui.__init__",),
    "ui.__init__": ("ui.gui",),
    "ui.gui": ("repo.__init__",),
}

C28_FIXTURE_SOURCES = {
    "repo.__init__": "from repo.main import run_repo_generator\n",
    "repo.main": (
        "from repo.filters import FilterWindow\n"
        "from ui import theme\n"
        "\n"
        "def run_repo_generator(parent=None):\n"
        "    pass\n"
    ),
    "repo.filters": "from ui import theme\n",
    "ui.__init__": "from .gui import run\n",
    "ui.gui": (
        "from repo import run_repo_generator\n"
        "\n"
        "def run(*, single_instance=None):\n"
        "    pass\n"
    ),
}


def _inputs(*, sources=None, graph=None, indexed=None):
    source_text = C28_FIXTURE_SOURCES if sources is None else sources
    edges = GRAPH if graph is None else graph
    parsed = {
        module: ParsedSourceInput(
            tree=ast.parse(text),
            source_fingerprint=sha256(text.encode("utf-8")).hexdigest(),
        )
        for module, text in source_text.items()
    }
    sites = analyze_cyclic_import_sites(edges, parsed)
    module_ids = tuple(GRAPH) if indexed is None else indexed
    return sites, parsed, module_ids


def _discover(*, sources=None, graph=None, indexed=None, max_searches=256):
    sites, parsed, module_ids = _inputs(
        sources=sources, graph=graph, indexed=indexed
    )
    return discover_conditional_reexports(
        sites, parsed, module_ids, max_searches=max_searches
    )


def _chains(report):
    return {candidate.assessment.chain for candidate in report.candidates}


VIA_FILTERS = (
    "repo.__init__", "repo.main", "repo.filters",
    "ui.__init__", "ui.gui", "repo.__init__",
)
DIRECT = (
    "repo.__init__", "repo.main", "ui.__init__",
    "ui.gui", "repo.__init__",
)


def test_c28_discovers_two_distinct_outgoing_paths():
    report = _discover()
    assert len(report.candidates) == 2
    assert _chains(report) == {VIA_FILTERS, DIRECT}
    assert {item.export_name for item in report.candidates} == {
        "run_repo_generator"
    }
    assert {item.assessment.status for item in report.candidates} == {
        "CONDITIONAL_DELAYED_REEXPORT"
    }
    assert report.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
    assert report.source_snapshot_binding == "NOT_ATOMICALLY_VERIFIED_BY_DISCOVERY"
    assert report.coverage_status == "BOUNDED_SELECTION_COMPLETE"


def test_c28_determinism_independent_graph_order():
    graph = dict(reversed(list(GRAPH.items())))
    sources = dict(reversed(list(C28_FIXTURE_SOURCES.items())))
    assert _discover() == _discover(graph=graph, sources=sources)


def test_c28_function_scoped_return_is_not_eager():
    sources = dict(C28_FIXTURE_SOURCES)
    sources["repo.filters"] = "def later():\n    from ui import theme\n"
    report = _discover(sources=sources)
    assert _chains(report) == {DIRECT}


def test_c28_mismatched_closing_export():
    sources = dict(C28_FIXTURE_SOURCES)
    sources["ui.gui"] = "from repo import other_name\n"
    report = _discover(sources=sources)
    assert report.candidates == ()
    assert report.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"


def test_c28_duplicate_exact_source_hop_rejected():
    sources = dict(C28_FIXTURE_SOURCES)
    sources["repo.filters"] = "from ui import theme\nfrom ui import theme\n"
    report = _discover(sources=sources)
    assert _chains(report) == {DIRECT}


def test_c28_ambiguous_layout_rejected():
    report = _discover(indexed=tuple(GRAPH) + ("repo",))
    assert report.candidates == ()


def test_c28_missing_source_partial():
    sources = dict(C28_FIXTURE_SOURCES)
    del sources["repo.filters"]
    report = _discover(sources=sources)
    assert "repo.filters" in report.unavailable_source_modules
    assert report.coverage_status == "PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE"
    assert _chains(report) == {DIRECT}
    assert report.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"


def test_c28_invalid_fingerprint_is_not_trusted():
    sites, parsed, indexed = _inputs()
    parsed["ui.gui"] = ParsedSourceInput(parsed["ui.gui"].tree, "invalid")
    report = discover_conditional_reexports(
        analyze_cyclic_import_sites(GRAPH, parsed), parsed, indexed
    )
    assert report.candidates == ()
    assert "ui.gui" in report.unavailable_source_modules
    assert report.coverage_status == "PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE"


def test_c28_bounded_search_limit():
    report = _discover(max_searches=1)
    assert report.examined_outgoing_count == 1
    assert report.coverage_status == "PARTIAL_SEARCH_LIMIT"
    assert len(report.candidates) < 2


def test_c28_source_ast_immutability_and_json():
    sites, parsed, indexed = _inputs()
    before = {
        module: ast.dump(source.tree, include_attributes=True)
        for module, source in parsed.items()
    }
    first = discover_conditional_reexports(sites, parsed, indexed)
    second = discover_conditional_reexports(sites, parsed, indexed)
    after = {
        module: ast.dump(source.tree, include_attributes=True)
        for module, source in parsed.items()
    }
    assert first == second
    assert before == after
    json.dumps(asdict(first))


def test_c28_unresolved_lexical_edges_preserved():
    graph = dict(GRAPH)
    graph["repo.filters"] = ("ui.__init__", "repo.__init__")
    report = _discover(graph=graph)
    assert report.unresolved_lexical_edge_count >= 1
    assert report.coverage_status == "PARTIAL_SOURCE_OR_LEXICAL_EVIDENCE"
    assert _chains(report) == {VIA_FILTERS, DIRECT}


def test_c28_rejects_invalid_search_limits():
    sites, parsed, indexed = _inputs()
    for limit in (0, -1, 4097, True):
        with pytest.raises(ValueError):
            discover_conditional_reexports(
                sites, parsed, indexed, max_searches=limit
            )


def test_c28_invalid_cpython_module_fails_closed():
    sources = dict(C28_FIXTURE_SOURCES)
    sources["ui.gui"] = (
        "from repo import run_repo_generator\n"
        "def invalid():\n"
        "    from repo import *\n"
    )
    assert isinstance(ast.parse(sources["ui.gui"]), ast.Module)
    report = _discover(sources=sources)
    assert report.candidates == ()
    assert "ui.gui" in report.unavailable_source_modules
    assert report.runtime_execution_status == "UNKNOWN_NOT_EVALUATED"
