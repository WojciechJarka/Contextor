"""
Cycle detection: determinism, canonical form and deep-graph safety.
"""

import pytest

from contextor.core.errors import AnalysisCancelled
from contextor.core.graph.cycles import detect_cycles


def test_no_cycles_in_acyclic_graph(isolated_dirs):
    edges = {"a": {"b"}, "b": {"c"}, "c": set()}

    assert detect_cycles(edges) == []


def test_detects_simple_cycle(isolated_dirs):
    edges = {"a": {"b"}, "b": {"a"}}

    cycles = detect_cycles(edges)

    assert len(cycles) == 1
    # Closed path: first node repeated at the end.
    assert cycles[0][0] == cycles[0][-1]
    assert set(cycles[0]) == {"a", "b"}


def test_rotations_collapse_to_one_cycle(isolated_dirs):
    edges = {"a": {"b"}, "b": {"c"}, "c": {"a"}}

    assert len(detect_cycles(edges)) == 1


def test_result_is_deterministic(isolated_dirs):
    edges = {
        "a": {"b", "c"},
        "b": {"a"},
        "c": {"d"},
        "d": {"c"},
    }

    assert detect_cycles(edges) == detect_cycles(edges)


def test_self_loop_is_a_cycle(isolated_dirs):
    assert detect_cycles({"a": {"a"}}) == [["a", "a"]]


def test_deep_chain_does_not_exhaust_the_stack(isolated_dirs):
    """
    The previous recursive implementation raised RecursionError here,
    aborting analysis of any repository with a long dependency chain.
    """

    depth = 20000

    edges = {f"n{i}": {f"n{i + 1}"} for i in range(depth)}
    edges[f"n{depth}"] = {"n0"}

    cycles = detect_cycles(edges)

    assert len(cycles) == 1
    assert len(cycles[0]) == depth + 2


def test_cancellation_raises_instead_of_returning_empty(isolated_dirs):
    edges = {"a": {"b"}, "b": {"a"}}

    with pytest.raises(AnalysisCancelled):
        detect_cycles(edges, progress_callback=lambda *_: False)
