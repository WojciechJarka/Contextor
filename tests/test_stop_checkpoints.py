"""Long pure-Python stages must cooperatively honour the GUI STOP request."""

import pytest

from contextor.core.errors import AnalysisCancelled
from contextor.core.graph.graph import build_graph
from contextor.core.reporting_engine.dictionary import compact_recursively


class _UnusedIndex:
    def get_module_id(self, value):
        return value

    def get_artifact_id(self, value):
        return value


def test_dependency_graph_build_honours_stop_before_module_resolution():
    with pytest.raises(AnalysisCancelled):
        build_graph(
            {"pkg.module": object()},
            trie={},
            package_root="pkg",
            progress_callback=lambda *_args: False,
        )


def test_recursive_report_compaction_checks_stop_periodically():
    with pytest.raises(AnalysisCancelled):
        compact_recursively(
            list(range(600)),
            _UnusedIndex(),
            set(),
            progress_callback=lambda *_args: False,
        )
