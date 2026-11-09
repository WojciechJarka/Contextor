"""Potential union-graph cycles remain separate from hard-cycle evidence."""

from types import SimpleNamespace
import subprocess
import sys

import pytest

from contextor.core.cycle_semantics.scc import (
    analyze_import_cycle_topology,
    analyze_soft_dependent_potential_cycles,
)
from contextor.core.diagnostics_projection import diagnostics_summary_for_state
from contextor.core.symbol_engine.indexer import index_repository
from contextor.core.graph.graph import build_graph


def test_soft_edge_closes_cycle_without_changing_hard_graph():
    hard = {"a": {"b"}, "b": set()}
    soft = {"b": {"a"}}
    before = ({key: set(value) for key, value in hard.items()},
              {key: set(value) for key, value in soft.items()})
    result = analyze_soft_dependent_potential_cycles(hard, soft)

    assert analyze_import_cycle_topology(hard).cyclic_components == ()
    assert result.component_count == 1
    assert result.components[0].members == ("a", "b")
    assert result.components[0].soft_only_internal_edges == (("b", "a"),)
    assert (hard, soft) == before


def test_soft_internal_evidence_is_complete_and_deduplicated():
    hard = {"a": {"b"}, "b": {"a"}}
    soft = {"a": ["b", "b"], "b": ["b", "b"]}
    result = analyze_soft_dependent_potential_cycles(hard, soft)
    assert len(analyze_import_cycle_topology(hard).cyclic_components) == 1
    assert result.component_count == 1
    assert result.components[0].soft_only_internal_edges == (("b", "b"),)


def test_acyclic_soft_edge_and_duplicate_hard_edge_do_not_create_potential():
    assert analyze_soft_dependent_potential_cycles(
        {"a": {"b"}}, {"b": {"c"}}
    ).component_count == 0
    assert analyze_soft_dependent_potential_cycles(
        {"a": {"b"}, "b": {"a"}}, {"a": {"b"}}
    ).component_count == 0


def test_freshness_gate_never_asserts_zero_for_missing_or_stale_graph():
    state = SimpleNamespace(
        cycles_state="fresh", cycles=[],
        collisions_state="fresh", collisions=[],
        syntax_diagnostics_state="fresh", syntax_diagnostics_by_path={},
        dependency_graph=SimpleNamespace(
            hard_edges={"a": {"b"}}, soft_edges={"b": {"a"}},
        ),
    )
    fresh = diagnostics_summary_for_state(state)
    assert fresh["soft_dependent_potential_cycles"]["count"] == 1
    assert fresh["soft_dependent_potential_cycles"]["availability"] == "fresh"
    assert fresh["soft_dependent_potential_cycles"]["runtime_execution_proven"] is False
    state.cycles_state = "stale"
    stale = diagnostics_summary_for_state(state)["soft_dependent_potential_cycles"]
    assert stale["count"] is None and stale["availability"] == "stale"
    state.cycles_state = "fresh"
    state.dependency_graph = None
    missing = diagnostics_summary_for_state(state)["soft_dependent_potential_cycles"]
    assert missing["count"] is None and missing["availability"] == "unavailable"


@pytest.mark.skipif(sys.version_info[:3] != (3, 15, 2), reason="CPython 3.15.2 oracle")
def test_same_repository_has_potential_graph_cycle_in_both_import_environments(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    repo = tmp_path / "repo"
    package = repo / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_bytes(b"pass\n")
    (package / "a.py").write_bytes(
        b"from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        b"    import pkg.b\nvalue = 1\n"
    )
    (package / "b.py").write_bytes(b"from pkg.a import value\n")
    external = tmp_path / "external"
    external.mkdir()
    (external / "typing.py").write_bytes(b"TYPE_CHECKING = True\n")

    indexed = index_repository(str(repo))
    graph = build_graph(indexed.modules)
    result = analyze_soft_dependent_potential_cycles(
        graph.hard_edges, graph.soft_edges,
    )
    assert result.component_count == 1
    assert result.components[0].members == ("pkg.a", "pkg.b")
    assert result.components[0].soft_only_internal_edges == (("pkg.a", "pkg.b"),)

    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "sys.path.insert(0, sys.argv[2]) if len(sys.argv) > 2 else None; "
        "import typing; print(typing.__file__, flush=True); import pkg.a"
    )
    normal = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code, str(repo)],
        capture_output=True, text=True, check=False,
    )
    overridden = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code, str(repo), str(external)],
        capture_output=True, text=True, check=False,
    )
    assert normal.returncode == 0
    assert "typing.py" in normal.stdout
    assert str(external) not in normal.stdout
    assert overridden.returncode != 0
    assert str(external / "typing.py") in overridden.stdout
    assert "partially initialized module 'pkg.a'" in overridden.stderr
