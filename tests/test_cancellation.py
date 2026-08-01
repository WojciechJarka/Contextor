"""
Cancellation must never look like a completed run.

Every checkpoint used to be written by hand, and several were spelled
`return errors` / `return []`, so aborting an analysis produced a
truncated but perfectly well-formed result. The GUI then reported a
cancelled validation as "no issues found".
"""

import pytest

from contextor.core.errors import AnalysisCancelled, checkpoint
from contextor.core.graph.cycles import detect_cycles
from contextor.core.graph.graph import build_graph
from contextor.core.symbol_engine.indexer import build_index
from contextor.core.validator import validate


def _cancel_after(n):
    """
    Progress callback that allows n calls, then requests cancellation.
    """

    state = {"calls": 0}

    def callback(*_args):
        state["calls"] += 1
        return state["calls"] <= n

    return callback


def test_checkpoint_raises_when_cancelled():
    with pytest.raises(AnalysisCancelled):
        checkpoint(lambda *_: False, "working")


def test_checkpoint_is_a_noop_without_a_callback():
    checkpoint(None, "working")


def test_checkpoint_passes_progress_through():
    seen = []

    checkpoint(lambda *args: seen.append(args) or True, "working", 3, 7)

    assert seen == [(3, 7, "working")]


@pytest.mark.parametrize("allowed", [0, 1, 2, 3])
def test_validate_raises_instead_of_returning_partial_errors(sample_repo, isolated_dirs, allowed):
    modules = build_index(str(sample_repo))
    graph = build_graph(modules)

    with pytest.raises(AnalysisCancelled):
        validate(modules, graph, progress_callback=_cancel_after(allowed))


def test_validate_reports_collisions_when_not_cancelled(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))
    graph = build_graph(modules)

    errors = validate(modules, graph, progress_callback=lambda *_: True)

    assert errors, "the sample repository contains real collisions"


def test_cycle_detection_raises_instead_of_returning_no_cycles(sample_repo, isolated_dirs):
    graph = build_graph(build_index(str(sample_repo)))

    with pytest.raises(AnalysisCancelled):
        detect_cycles(graph.hard_edges, progress_callback=lambda *_: False)
