"""
End-to-end checks over a small synthetic repository.
"""

import ast
import json
from pathlib import Path

import pytest

from contextor.core.api import facade
from contextor.core.api.facade import ContextorFacade
from contextor.core.graph.cycles import detect_cycles
from contextor.core.graph.graph import build_graph
from contextor.core import reporting_engine
from contextor.core.reporting_engine import artifact_pipeline, layer_pipeline
from contextor.core.reporting_engine import io_manager
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


def test_index_excludes_selected_python_subtree(sample_repo, isolated_dirs):
    modules = build_index(str(sample_repo), excludes=["core"])

    assert modules
    assert all(not module_name.startswith("core.") for module_name in modules)
    assert "ui.app" in modules


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


def test_per_analysis_excludes_merge_with_gui_state_without_persisting(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    saved = ["generated", "pkg/ignored.py"]
    monkeypatch.setattr(
        facade,
        "_load_excludes_for_repo",
        lambda _repo: (saved.copy(), {".git", ".venv"}),
    )

    excludes, ignored_dirs = facade._analysis_filters(
        str(repo), ["tests", "pkg\\ignored.py", str(repo / "legacy")]
    )

    assert excludes == ["generated", "pkg/ignored.py", "tests", "legacy"]
    assert ignored_dirs == {".git", ".venv"}
    assert saved == ["generated", "pkg/ignored.py"]


def test_per_analysis_excludes_reject_paths_outside_repository(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(
        facade, "_load_excludes_for_repo", lambda _repo: ([], set())
    )

    with pytest.raises(ValueError, match="outside the repository"):
        facade._analysis_filters(str(repo), [str(tmp_path / "other")])


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


def test_extracted_layer_pipeline_builds_analytics_and_status(monkeypatch):
    captured = {}

    def fake_graph_analytics(**kwargs):
        captured.update(kwargs)
        return {"scope": kwargs["scope"]}

    monkeypatch.setattr(
        layer_pipeline,
        "generate_graph_analytics_report",
        fake_graph_analytics,
    )
    reports = {
        "artifacts": {"artifacts": {}},
        "structure_raw": {
            "hard_edges": {"pkg.one": ["pkg.two"]},
            "soft_edges": {},
        },
        "summary": {
            "layer_modules": ["pkg.one", "pkg.two", 123],
            "layer_module_count": 2,
            "layer_cycles_count": 0,
            "hotspots": ["pkg.one"],
            "status": "WARNING",
            "computation_mode": "full",
        },
        "_index_dict": object(),
        "_global_artifact_data": {"artifacts": {"global": {}}},
    }

    status = layer_pipeline.execute_layer_pipeline("repo", "pkg", reports)

    assert reports["graph_analytics"] == {"scope": "layer"}
    assert captured["scope_modules"] == {"pkg.one", "pkg.two"}
    assert captured["hard_edges"] == {"pkg.one": ["pkg.two"]}
    assert captured["global_artifact_data"] is reports["_global_artifact_data"]
    assert status == {
        "layer": "pkg",
        "module_count": 2,
        "status": "WARNING",
        "cycles_count": 0,
        "hotspot_count": 1,
        "computation_mode": "full",
    }


def test_reporting_engine_keeps_layer_pipeline_as_public_package_api():
    assert reporting_engine.execute_layer_pipeline is (
        layer_pipeline.execute_layer_pipeline
    )


def test_artifact_pipeline_builds_all_views_from_one_full_report(monkeypatch):
    calls = {}
    full_report = {
        "artifacts": {"raw": {}},
        "_module_artifacts": {"pkg.one": {"run"}},
        "_usage_sidecar": {"run": ["pkg.two"]},
    }

    class Transaction:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeArtifactRegistry:
        def __init__(self, root_path):
            calls["registry_root"] = root_path

        def transaction(self):
            return Transaction()

        def sync_with_workspace(self, modules, artifacts):
            calls["sync"] = (modules, artifacts)

        def run_garbage_collector(self):
            calls["garbage_collected"] = True

    index = object()
    monkeypatch.setattr(
        artifact_pipeline,
        "generate_artifact_usage_report",
        lambda *args, **kwargs: full_report,
    )
    monkeypatch.setattr(
        artifact_pipeline,
        "collect_qualified_artifact_identities",
        lambda value: {"pkg.one::run"} if value else set(),
    )
    monkeypatch.setattr(
        artifact_pipeline,
        "PersistentIdentityRegistry",
        FakeArtifactRegistry,
    )
    monkeypatch.setattr(artifact_pipeline, "IndexDictionary", lambda _registry: index)
    monkeypatch.setattr(
        artifact_pipeline,
        "compact_artifact_report",
        lambda artifact_data, index_dict: {
            "same_source": artifact_data is full_report,
            "same_index": index_dict is index,
        },
    )
    monkeypatch.setattr(
        artifact_pipeline,
        "compact_structure_report",
        lambda structure, index_dict: {
            "structure": structure,
            "same_index": index_dict is index,
        },
    )

    def fake_analytics(**kwargs):
        calls["analytics"] = kwargs
        return {"scope": kwargs["scope"]}

    monkeypatch.setattr(
        artifact_pipeline, "generate_graph_analytics_report", fake_analytics
    )

    result = artifact_pipeline.build_artifact_pipeline(
        modules={"pkg.one": object()},
        root_path="repo-root",
        runtime={"mode": "test"},
        report_header={"branch": "main"},
        structure_data={"hard_edges": {}},
        hard_edges={"pkg.one": {"pkg.two"}},
        soft_edges={},
    )

    assert result.artifact_data is full_report
    assert result.usage_sidecar == {"run": ["pkg.two"]}
    assert result.compact_artifact_data == {
        "same_source": True,
        "same_index": True,
    }
    assert result.compact_structure_data["same_index"] is True
    assert result.graph_analytics_data == {"scope": "global"}
    assert full_report["report_header"]["data_source"] == "artifacts"
    assert calls["sync"] == ({"pkg.one"}, {"pkg.one::run"})
    assert calls["garbage_collected"] is True
    assert calls["analytics"]["artifact_data"] is full_report
    assert calls["analytics"]["index_dict"] is index


def test_consecutive_global_writes_diff_same_commit_worktree_states(
    tmp_path, monkeypatch
):
    output = tmp_path / "output"

    def report_path(value):
        relative = Path(value)
        return tmp_path / relative

    def save(payload, path, **_kwargs):
        target = report_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(io_manager, "resolve_report_path", report_path)
    monkeypatch.setattr(io_manager, "save_json", save)
    monkeypatch.setattr(io_manager, "_save_markdown", lambda *_args: None)
    first = {
        "summary": {
            "report_header": {"commit_sha": "same"},
            "metrics": {"nodes": 10, "edges_total": 12},
            "debt_summary": {"hotspot_count": 2, "total_score": 3.0},
        }
    }
    second = {
        "summary": {
            "report_header": {"commit_sha": "same"},
            "metrics": {"nodes": 11, "edges_total": 14},
            "debt_summary": {"hotspot_count": 1, "total_score": 2.0},
        }
    }

    io_manager.write_global_reports(first, "repo")
    io_manager.write_global_reports(second, "repo")

    diff = json.loads((output / "repo_report_diff.json").read_text())
    assert diff["classification"] == "IMPROVED"
    assert diff["comparison_basis"] == "consecutive_canonical_runs"
    assert diff["baseline"]["commit_sha"] == "same"
    assert diff["current"]["commit_sha"] == "same"
    assert diff["report_diff"]["metrics"]["nodes"]["delta"] == 1
    assert diff["report_diff"]["debt"]["hotspot_count"]["delta"] == -1
