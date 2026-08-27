import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.analysis.state_manager import RepositoryAnalysisState
from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.mcp import query_helpers
from contextor.mcp import runtime as mcp_runtime
from contextor.mcp.tools.get_symbol_call_context import get_symbol_call_context


_MODULE = "pkg.graph"
_ROOT = f"{_MODULE}::root"


def _edge(caller, callee, line):
    return (f"{_MODULE}::{caller}", f"{_MODULE}::{callee}", line, "direct")


def _install(monkeypatch, edges, *, symbols=None, materialized=True, stale=False):
    names = set(symbols or ())
    for caller, callee, _line, _kind in edges:
        names.add(caller.split("::", 1)[1])
        names.add(callee.split("::", 1)[1])
    state = RepositoryAnalysisState(
        modules={_MODULE: object()},
        artifacts={_MODULE: {"own_symbols": sorted(names)}},
        module_usages={
            _MODULE: ModuleUsageFacts(
                symbol_calls=tuple(edges),
                symbol_calls_materialized=materialized,
            )
        },
    )
    if stale:
        state.module_parse_freshness[_MODULE] = {
            "state": "stale",
            "error": "invalid syntax",
            "line_number": 1,
        }
    monkeypatch.setattr(
        mcp_runtime, "get_or_init_engine", lambda _root: SimpleNamespace(state=state)
    )
    identities = {
        f"{_MODULE}::{name}": f"A{index}/1"
        for index, name in enumerate(sorted(names), 1)
    }
    monkeypatch.setattr(
        query_helpers,
        "read_registries",
        lambda _root: ({}, {}, identities, {value: key for key, value in identities.items()}),
    )
    return state


def _call(**kwargs):
    return json.loads(get_symbol_call_context("C:/repo", kwargs.pop("symbol", _ROOT), **kwargs))


def test_callers_callees_both_and_depth_one(monkeypatch):
    _install(
        monkeypatch,
        [_edge("left", "root", 2), _edge("root", "right", 3)],
    )
    callers = _call(direction="callers", representation="named")
    callees = _call(direction="callees", representation="named")
    both = _call(direction="both", representation="named")

    assert [item["caller"] for item in callers["callers"]["items"]] == [f"{_MODULE}::left"]
    assert [item["callee"] for item in callees["callees"]["items"]] == [f"{_MODULE}::right"]
    assert both["total_edges"] == both["returned_edges"] == 2
    assert all(item["depth"] == 1 for side in ("callers", "callees") for item in both[side]["items"])


def test_depth_two_three_are_deterministic_bfs_and_deduplicate(monkeypatch):
    edges = [
        _edge("root", "b", 5),
        _edge("root", "a", 4),
        _edge("a", "c", 8),
        _edge("c", "d", 9),
        _edge("root", "a", 4),
    ]
    _install(monkeypatch, edges)
    depth_two = _call(direction="callees", depth=2, max_items=None, representation="named")
    depth_three = _call(direction="callees", depth=3, max_items=None, representation="named")

    assert [(item["callee"], item["depth"]) for item in depth_two["callees"]["items"]] == [
        (f"{_MODULE}::a", 1),
        (f"{_MODULE}::b", 1),
        (f"{_MODULE}::c", 2),
    ]
    assert depth_three["callees"]["items"][-1]["callee"] == f"{_MODULE}::d"
    assert depth_three["callees"]["items"][-1]["depth"] == 3
    assert _call(direction="callees", depth=3, max_items=None, representation="named") == depth_three


@pytest.mark.parametrize("depth", [0, 4, True])
def test_invalid_depth(depth, monkeypatch):
    _install(monkeypatch, [], symbols={"root"})
    assert _call(depth=depth)["error"] == "invalid_depth"


@pytest.mark.parametrize("max_items", [0, -1, True])
def test_invalid_max_items(max_items, monkeypatch):
    _install(monkeypatch, [], symbols={"root"})
    assert _call(max_items=max_items)["error"] == "invalid_max_items"


def test_global_max_items_truthful_and_none_is_complete(monkeypatch):
    _install(monkeypatch, [_edge("root", "a", 2), _edge("root", "b", 3)])
    bounded = _call(direction="callees", max_items=1, representation="named")
    complete = _call(direction="callees", max_items=None, representation="named")

    assert bounded["total_edges"] == 2
    assert bounded["returned_edges"] == 1
    assert bounded["truncated"] is True
    assert bounded["callees"]["total"] == 2
    assert bounded["callees"]["truncated"] is True
    assert complete["returned_edges"] == 2
    assert complete["truncated"] is False


def test_exact_unknown_and_non_exact_symbol_handling(monkeypatch):
    _install(monkeypatch, [], symbols={"root"})
    assert _call(representation="named")["status"] == "ok"
    assert _call(symbol=f"{_MODULE}::missing")["error"] == "unknown_symbol"
    assert _call(symbol="root")["error"] == "exact_qualified_symbol_required"


def test_stale_unmaterialized_and_materialized_empty_fail_closed(monkeypatch):
    _install(monkeypatch, [], symbols={"root"}, stale=True)
    assert _call()["status"] == "stale"
    _install(monkeypatch, [], symbols={"root"}, materialized=False)
    assert _call()["error"] == "symbol_calls_unmaterialized"
    _install(monkeypatch, [], symbols={"root"}, materialized=True)
    empty = _call(representation="named")
    assert empty["status"] == "ok"
    assert empty["total_edges"] == empty["returned_edges"] == 0


def test_named_indexed_and_auto_use_existing_ids(monkeypatch):
    _install(monkeypatch, [_edge("root", "callee", 2)])
    named = _call(direction="callees", representation="named")
    indexed = _call(direction="callees", representation="indexed")
    auto = _call(direction="callees", representation="auto")

    assert named["callees"]["items"][0]["caller"] == _ROOT
    assert indexed["callees"]["items"][0]["caller"].startswith("A")
    assert indexed["resolver"]["resolve_via"] == "lookup_index_entries"
    assert auto["representation"] == "named"
    assert auto["representation_decision"]["bytes_saved"] < 512


def test_large_named_candidate_forces_indexed_preflight_and_exact_retry(monkeypatch):
    edges = []
    for index in range(220):
        long_name = f"callee_{index}_" + ("x" * 150)
        edges.append(_edge("root", long_name, index + 2))
    _install(monkeypatch, edges)

    bounded = _call(
        direction="callees",
        depth=1,
        max_items=None,
        representation="named",
    )
    assert bounded["status"] == "ok"
    assert bounded["representation"] == "indexed"
    assert bounded["representation_decision"]["reason"] == "named_candidate_exceeded_51200_bytes"
    assert "_output" in bounded
    assert bounded["_output"]["auto_bounded"] is True
    assert bounded["_output"]["warning_threshold_bytes"] == 15360
    assert bounded["_output"]["full_output_bytes"] > 15360

    approved_text = get_symbol_call_context(
        "C:/repo",
        _ROOT,
        direction="callees",
        depth=1,
        max_items=None,
        representation="named",
        allow_large_output=True,
    )
    approved = json.loads(approved_text)
    assert approved["representation"] == "indexed"
    assert len(approved_text.encode("utf-8")) == bounded["_output"]["full_output_bytes"]


def test_query_does_not_parse_or_read_source(monkeypatch):
    _install(monkeypatch, [_edge("root", "callee", 2)])
    monkeypatch.setattr(ast, "parse", lambda *_args, **_kwargs: pytest.fail("ast.parse called"))
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: pytest.fail("read_text called"))
    assert _call(direction="callees", representation="named")["status"] == "ok"
