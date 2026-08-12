"""
End-to-end checks over a small synthetic repository.
"""

import ast
from pathlib import Path

from contextor.core.graph.cycles import detect_cycles
from contextor.core.graph.graph import build_graph
from contextor.core.api.facade import ContextorFacade
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


def test_global_pipeline_forwards_datestamp_to_report_writer():
    pipeline_path = (
        Path(__file__).parents[1]
        / "contextor"
        / "core"
        / "reporting_engine"
        / "pipeline.py"
    )
    tree = ast.parse(pipeline_path.read_text(encoding="utf-8"))
    pipeline = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "execute_global_pipeline"
    )
    write_call = next(
        node
        for node in ast.walk(pipeline)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "write_global_reports"
    )

    forwarded = {keyword.arg: keyword.value for keyword in write_call.keywords}
    assert isinstance(forwarded["datestamp"], ast.Name)
    assert forwarded["datestamp"].id == "datestamp"


def test_first_global_run_writes_canonical_and_timestamped_snapshot(
    sample_repo, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")

    ContextorFacade.analyze_project(str(sample_repo))

    output = isolated_dirs / "output"
    repo_name = sample_repo.name
    assert (output / f"{repo_name}_summary.json").is_file()
    snapshots = [
        path
        for path in output.glob(f"{repo_name}_*")
        if path.is_dir()
    ]
    assert len(snapshots) == 1
    assert (snapshots[0] / f"{repo_name}_summary.json").is_file()
    assert (snapshots[0] / f"{repo_name}_summary.md").is_file()


def test_layer_report_writers_receive_datestamp():
    root = Path(__file__).parents[1]
    targets = {
        root / "contextor" / "core" / "api" / "facade.py": "analyze_layer",
        root / "contextor" / "core" / "reporting_engine" / "pipeline.py": (
            "execute_global_pipeline"
        ),
    }

    for path, function_name in targets.items():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        )
        calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "write_layer_reports"
        ]
        assert calls
        for call in calls:
            forwarded = {keyword.arg: keyword.value for keyword in call.keywords}
            assert isinstance(forwarded["datestamp"], ast.Name)
            assert forwarded["datestamp"].id == "datestamp"
