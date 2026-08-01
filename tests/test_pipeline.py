"""
End-to-end checks over a small synthetic repository.
"""

from contextor.core.graph.cycles import detect_cycles
from contextor.core.graph.graph import build_graph
from contextor.core.symbol_engine.indexer import build_index
from contextor.core.validator.collisions import validate_name_collisions


def test_index_finds_every_source_file(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    assert set(modules) == {
        "core.__init__",
        "core.alpha",
        "core.beta",
        "core.gamma",
        "ui.__init__",
        "ui.app",
    }


def test_index_never_writes_into_the_analyzed_repository(sample_repo, isolated_dirs):
    """
    Contextor advertises read-only analysis; the per-file cache used to
    create '.contextor_cache' inside the inspected project.
    """

    before = {p.relative_to(sample_repo) for p in sample_repo.rglob("*")}

    build_index(str(sample_repo))

    after = {p.relative_to(sample_repo) for p in sample_repo.rglob("*")}

    assert after == before


def test_graph_records_hard_dependencies(sample_repo, isolated_dirs):
    graph = build_graph(build_index(str(sample_repo)))

    assert "core.beta" in graph.hard_edges["core.alpha"]
    assert "core.alpha" in graph.hard_edges["ui.app"]


def test_graph_is_deterministic(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    assert build_graph(modules).hard_edges == build_graph(modules).hard_edges


def test_import_cycle_is_detected(sample_repo, isolated_dirs):
    graph = build_graph(build_index(str(sample_repo)))

    cycles = detect_cycles(graph.hard_edges)

    assert any({"core.alpha", "core.beta"} <= set(c) for c in cycles)


def test_conflicting_definitions_are_reported_as_collisions(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo))

    collisions = validate_name_collisions(modules)

    helper = [c for c in collisions if "'helper'" in c.message]

    assert helper, "differing helper() implementations must collide"
    assert helper[0].is_identical is False
    assert set(helper[0].nodes) == {"core.beta", "core.gamma"}


def test_constant_collision_is_detected(sample_repo, isolated_dirs):
    collisions = validate_name_collisions(build_index(str(sample_repo)))

    assert any("'MAX_ITEMS'" in c.message for c in collisions)
