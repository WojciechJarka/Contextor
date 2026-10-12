from pathlib import Path

import pytest

from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.state_manager import (
    FileDelta,
    FileStateManager,
    RepositoryAnalysisState,
)
from contextor.core.domain.usage_facts import UsageDelta
from contextor.core.graph.graph import (
    build_graph,
    build_trie,
    detect_package_root,
)
from contextor.core.reference.shared import materialize_reexport_facts_by_module
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)
from contextor.core.reporting_layer.artifact_usage_report import (
    collect_module_artifacts,
    collect_qualified_artifact_identities,
)
from contextor.core.symbol_engine.indexer import index_repository


pytestmark = pytest.mark.live

GRAPH_RECOMPUTATIONS = (
    "macro_metrics",
    "reverse_blast_radius",
    "advanced_graph_metrics",
    "cycles",
)


def _initializer_delta(**kwargs):
    metadata_changes = kwargs.pop(
        "metadata_changes",
        {"reexport_facts_changed": True},
    )
    return FileDelta(
        module_path="pkg.__init__",
        metadata_changes=metadata_changes,
        **kwargs,
    )


def test_binding_only_package_initializer_change_plans_graph_refresh():
    plan = RefreshPlanner.plan_refresh(_initializer_delta())

    assert set(plan.patch_families) == {
        "reexport_facts",
        "dependency_graph",
        "artifact_consumption",
        "cached_analytics",
    }
    assert plan.patch_families.count("dependency_graph") == 1
    assert plan.graph_recomputations == GRAPH_RECOMPUTATIONS


def test_package_initializer_symbol_change_keeps_registry_work_and_refreshes_graph():
    plan = RefreshPlanner.plan_refresh(
        _initializer_delta(artifacts_changed=["child"])
    )

    assert "definitions" in plan.patch_families
    assert "identity_registry" in plan.patch_families
    assert "reexport_facts" in plan.patch_families
    assert "dependency_graph" in plan.patch_families
    assert plan.patch_families.count("dependency_graph") == 1
    assert plan.graph_recomputations == GRAPH_RECOMPUTATIONS


def test_initializer_alias_retarget_preserves_operations_and_refreshes_graph():
    usage_delta = UsageDelta(
        module_path="pkg.__init__",
        removed_aliases=(("child", "pkg.child"),),
        added_aliases=(("child", "pkg.child_alias"),),
    )
    plan = RefreshPlanner.plan_refresh(
        _initializer_delta(), usage_delta=usage_delta
    )

    assert {"definitions", "module_usages", "reexport_facts", "dependency_graph", "artifact_consumption", "cached_analytics"} <= set(plan.patch_families)
    assert plan.patch_families.count("dependency_graph") == 1
    assert plan.graph_recomputations == GRAPH_RECOMPUTATIONS


def test_ordinary_module_reexport_change_keeps_previous_graph_semantics():
    plan = RefreshPlanner.plan_refresh(
        FileDelta(
            module_path="pkg.child",
            metadata_changes={"reexport_facts_changed": True},
        )
    )

    assert "reexport_facts" in plan.patch_families
    assert "artifact_consumption" in plan.patch_families
    assert "cached_analytics" in plan.patch_families
    assert "dependency_graph" not in plan.patch_families
    assert plan.graph_recomputations == ()


def test_initializer_import_change_does_not_duplicate_graph_work():
    plan = RefreshPlanner.plan_refresh(
        _initializer_delta(imports_changed=["pkg.child"])
    )

    assert plan.patch_families.count("dependency_graph") == 1
    assert plan.graph_recomputations == GRAPH_RECOMPUTATIONS
    assert all(plan.graph_recomputations.count(item) == 1 for item in GRAPH_RECOMPUTATIONS)


def _fresh_graph(repo: Path):
    repo_index = index_repository(str(repo))
    modules = repo_index.modules
    facts = materialize_reexport_facts_by_module(
        modules,
        repo_index.reference_facts_by_module,
    )
    trie = build_trie(modules.keys())
    package_root = detect_package_root(modules, trie)
    graph = build_graph(
        modules,
        trie=trie,
        package_root=package_root,
        reexport_facts_by_module=facts,
    )
    return modules, facts, graph


def _make_real_engine(repo: Path, cache_dir: Path):
    repo_index = index_repository(str(repo))
    modules = repo_index.modules
    artifacts, failures = collect_module_artifacts(modules, str(repo))
    assert not failures
    facts = materialize_reexport_facts_by_module(
        modules,
        repo_index.reference_facts_by_module,
    )
    trie = build_trie(modules.keys())
    package_root = detect_package_root(modules, trie)
    graph = build_graph(
        modules,
        trie=trie,
        package_root=package_root,
        reexport_facts_by_module=facts,
    )
    state = RepositoryAnalysisState(
        modules=dict(modules),
        reexport_facts_by_module=facts,
        artifacts=artifacts,
        dependency_graph=graph,
        trie=trie,
        package_root=package_root,
        artifact_consumption={},
    )

    registry = PersistentIdentityRegistry(str(repo))
    with registry.transaction():
        registry.sync_with_workspace(
            set(modules),
            collect_qualified_artifact_identities(artifacts),
        )

    state_manager = FileStateManager(str(cache_dir))
    for path in repo.rglob("*.py"):
        state_manager.update_state(str(path))
    return IncrementalAnalysisEngine(
        state,
        registry,
        state_manager,
        str(repo),
    )


def _assert_graph_matches_fresh(engine, repo):
    fresh_modules, fresh_facts, fresh_graph = _fresh_graph(repo)
    assert engine.state.dependency_graph.hard_edges == fresh_graph.hard_edges
    assert engine.state.dependency_graph.soft_edges == fresh_graph.soft_edges
    assert engine.state.reexport_facts_by_module == fresh_facts
    assert set(engine.state.modules) == set(fresh_modules)
    return fresh_graph


def test_initializer_binding_updates_incremental_graph_and_recovers_child_edge(tmp_path):
    repo = tmp_path / "repo"
    package = repo / "pkg"
    package.mkdir(parents=True)
    initializer = package / "__init__.py"
    initializer.write_text("", encoding="utf-8")
    (package / "child.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "consumer.py").write_text(
        "from pkg import child\nchild.VALUE\n",
        encoding="utf-8",
    )
    (repo / "unrelated.py").write_text("VALUE = 2\n", encoding="utf-8")

    engine = _make_real_engine(repo, tmp_path / "cache")
    initial_graph = engine.state.dependency_graph
    assert initial_graph.hard_edges["consumer"] == {"pkg.__init__"}
    assert initial_graph.soft_edges["consumer"] == {"pkg.child"}

    initializer.write_text("child = 123\n", encoding="utf-8")
    result = engine.update_file(str(initializer))

    assert result.status == "UPDATED"
    assert result.graph_state == "fresh"
    assert result.dependencies_state == "fresh"
    assert result.blast_radius_state == "fresh"
    assert "dependency_graph" in result.shadow_plan.patch_families
    assert "consumer" in result.affected_modules
    assert "unrelated" not in result.affected_modules
    assert engine.state.dependency_graph.hard_edges["consumer"] == {"pkg.__init__"}
    assert engine.state.dependency_graph.soft_edges["consumer"] == set()
    assert engine.state.dependency_graph.hard_edges["unrelated"] == initial_graph.hard_edges["unrelated"]
    assert engine.state.dependency_graph.soft_edges["unrelated"] == initial_graph.soft_edges["unrelated"]
    _assert_graph_matches_fresh(engine, repo)

    initializer.write_text("", encoding="utf-8")
    result = engine.update_file(str(initializer))

    assert result.status == "UPDATED"
    assert result.graph_state == "fresh"
    assert result.dependencies_state == "fresh"
    assert result.blast_radius_state == "fresh"
    assert "consumer" in result.affected_modules
    assert "unrelated" not in result.affected_modules
    assert engine.state.dependency_graph.hard_edges["consumer"] == {"pkg.__init__"}
    assert engine.state.dependency_graph.soft_edges["consumer"] == {"pkg.child"}
    _assert_graph_matches_fresh(engine, repo)
