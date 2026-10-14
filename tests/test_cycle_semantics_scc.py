import json
import random
from dataclasses import asdict

import pytest

from contextor.core.cycle_semantics.scc import (
    analyze_import_cycle_topology as analyze,
)


def test_b0g4b5_acyclic_target_only_and_empty():
    assert analyze({}).node_count == 0
    out = analyze({"a": {"b"}, "b": {"c"}})
    assert (
        out.node_count,
        out.hard_edge_count,
        out.total_scc_count,
        out.cyclic_components,
    ) == (3, 2, 3, ())


def test_b0g4b5_overlapping_cycles_one_scc():
    out = analyze({
        "a": {"b", "c", "x"},
        "b": {"c"},
        "c": {"a"},
        "x": set(),
    })
    assert out.total_scc_count == 2
    assert len(out.cyclic_components) == 1
    assert out.cyclic_components[0].members == ("a", "b", "c")
    assert out.cyclic_components[0].internal_edges == (
        ("a", "b"),
        ("a", "c"),
        ("b", "c"),
        ("c", "a"),
    )


def test_b0g4b5_independent_sccs_and_self_loop():
    out = analyze({
        "a": {"b"}, "b": {"a"},
        "c": {"c"},
        "d": {"e"}, "e": {"d"},
        "f": set(),
    })
    assert tuple(c.members for c in out.cyclic_components) == (
        ("a", "b"), ("c",), ("d", "e")
    )
    assert tuple(c.kind for c in out.cyclic_components) == (
        "MULTI_MODULE", "SELF_LOOP", "MULTI_MODULE"
    )
    assert out.total_scc_count == 4


def test_b0g4b5_order_independent_and_deduplicated():
    first = analyze({"b": ["a", "a"], "a": ("b", "c"), "c": ()})
    second = analyze({"c": set(), "a": {"c", "b"}, "b": {"a"}})
    assert first == second
    assert first.hard_edge_count == 3
    json.dumps(asdict(first))


def test_b0g4b5_deep_cycle_no_recursion():
    n = 4100
    graph = {f"m{i}": {f"m{i+1}"} for i in range(n)}
    graph[f"m{n}"] = {"m0"}
    out = analyze(graph)
    assert (
        out.node_count,
        out.hard_edge_count,
        out.total_scc_count,
    ) == (n + 1, n + 1, 1)
    assert len(out.cyclic_components[0].members) == n + 1


def test_b0g4b5_deep_acyclic_chain_no_recursion():
    n = 3000
    out = analyze({
        f"m{i}": {f"m{i+1}"} for i in range(n)
    })
    assert (
        out.node_count,
        out.total_scc_count,
        len(out.cyclic_components),
    ) == (n + 1, n + 1, 0)


@pytest.mark.parametrize("graph, error", [
    (None, TypeError),
    ([("a", {"b"})], TypeError),
    ({"a": "b"}, TypeError),
    ({"a": None}, TypeError),
    ({"": set()}, ValueError),
    ({1: {"a"}}, ValueError),
    ({"a": {None}}, ValueError),
])
def test_b0g4b5_rejects_invalid_graph(graph, error):
    with pytest.raises(error):
        analyze(graph)


def test_b0g4b5_no_graph_mutation():
    graph = {"a": {"b"}, "b": {"a"}}
    before = {k: set(v) for k, v in graph.items()}
    out = analyze(graph)
    assert graph == before
    with pytest.raises(Exception):
        out.cyclic_components[0].members = ("fake",)


def test_b0g4b5_random_graphs_against_reachability_definition():
    rng = random.Random(710)
    for n in range(2, 7):
        nodes = [f"x{i}" for i in range(n)]
        for _ in range(12):
            graph = {
                u: {v for v in nodes if rng.randrange(4) == 0}
                for u in nodes
            }
            out = analyze(graph)

            reach = {}
            for u in nodes:
                found = {u}
                stack = [u]
                while stack:
                    for v in graph[stack.pop()]:
                        if v not in found:
                            found.add(v)
                            stack.append(v)
                reach[u] = found

            unused = set(nodes)
            expected = []
            while unused:
                u = min(unused)
                group = {
                    v for v in nodes
                    if v in reach[u] and u in reach[v]
                }
                unused -= group
                if len(group) > 1 or u in graph[u]:
                    expected.append(tuple(sorted(group)))

            assert tuple(
                component.members
                for component in out.cyclic_components
            ) == tuple(sorted(expected))
