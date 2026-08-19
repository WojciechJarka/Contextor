import os
from pathlib import Path
import pytest
from unittest.mock import patch
from contextor.core.analysis.state_manager import RepositoryAnalysisState, FileStateManager, FileState
from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.core.symbol_engine.indexer import index_repository
from contextor.core.graph.graph import build_graph, build_trie, detect_package_root

pytestmark = pytest.mark.live

def bootstrap_state(root_path: Path, registry: PersistentIdentityRegistry) -> RepositoryAnalysisState:
    repo_index = index_repository(str(root_path))
    modules = repo_index.modules
    
    from contextor.core.reporting_layer.artifact_usage_report import collect_module_artifacts
    module_artifacts, _ = collect_module_artifacts(modules, str(root_path))
    
    trie = build_trie(modules.keys())
    package_root = detect_package_root(modules, trie)
    graph = build_graph(modules)
    
    from contextor.core.reporting_layer.artifact_usage_report import build_artifact_index
    artifact_index, usage_sidecar = build_artifact_index(module_artifacts)
    artifact_consumption = {
        "_report": artifact_index,
        "_usage_sidecar": usage_sidecar
    }
    
    state = RepositoryAnalysisState(
        modules=dict(modules),
        artifacts=module_artifacts,
        dependency_graph=graph,
        trie=trie,
        package_root=package_root,
        artifact_consumption=artifact_consumption,
    )
    return state

def init_engine(tmp_path, repo_dir, state, registry):
    from contextor.core.analysis.state_manager import FileStateManager
    state_mgr = FileStateManager(str(tmp_path))
    for f in repo_dir.rglob("*.py"):
        state_mgr.update_state(str(f))
    return IncrementalAnalysisEngine(state, registry, state_mgr, str(repo_dir))

def compare_states(incremental_state: RepositoryAnalysisState, full_state: RepositoryAnalysisState, compare_artifacts: bool = False):
    # 1. Modules & Imports
    assert incremental_state.modules.keys() == full_state.modules.keys()
    for mod_id in incremental_state.modules:
        assert [imp.module for imp in incremental_state.modules[mod_id].imports] == [imp.module for imp in full_state.modules[mod_id].imports]
        
    # 2. Graph
    assert incremental_state.dependency_graph.hard_edges == full_state.dependency_graph.hard_edges
    assert incremental_state.dependency_graph.soft_edges == full_state.dependency_graph.soft_edges
    
    # 3. Trie and Package Root
    assert incremental_state.package_root == full_state.package_root
    
    # 4. Artifacts and Consumption
    assert incremental_state.artifacts.keys() == full_state.artifacts.keys()
    for k in incremental_state.artifacts:
        assert incremental_state.artifacts[k]["own_symbols"] == full_state.artifacts[k]["own_symbols"]
        if compare_artifacts:
            for symbol, consumer_data in incremental_state.artifacts[k].get("consumers", {}).items():
                inc_consumers = consumer_data.get("consumers", []) if isinstance(consumer_data, dict) else consumer_data
                base_data = full_state.artifacts[k].get("consumers", {}).get(symbol, {})
                base_consumers = base_data.get("consumers", []) if isinstance(base_data, dict) else base_data
                assert set(inc_consumers) == set(base_consumers)
                
    if compare_artifacts:
        assert set(incremental_state.artifact_consumption.get("_report", {}).keys()) == set(full_state.artifact_consumption.get("_report", {}).keys())


def test_incremental_add_imported_module(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_b = repo_dir / "b.py"
    file_b.write_text("from a import foo\n\ndef bar():\n    foo()\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    res = engine.update_file(str(file_a))
    assert res.graph_state == "fresh"
    
    registry_baseline = PersistentIdentityRegistry(str(repo_dir))
    state_baseline = bootstrap_state(repo_dir, registry_baseline)
    
    compare_states(engine.state, state_baseline, compare_artifacts=False)


def test_incremental_new_file_delta_imports_are_json_serializable(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "existing.py").write_text("VALUE = 1\n", encoding="utf-8")

    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)

    target = repo_dir / "new_module.py"
    target.write_text("import pathlib\n", encoding="utf-8")

    result = engine.update_file(str(target))

    assert result.delta.imports_added == ["pathlib"]
    __import__("json").dumps(result.delta.imports_added)


def test_incremental_update_synchronizes_qualified_artifact_registry(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    target = repo_dir / "a.py"
    target.write_text("def foo():\n    return 1\n", encoding="utf-8")

    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    with registry.transaction():
        registry.sync_with_workspace(
            {"a"},
            {"a::foo", "b::bar"},
        )
    foo_id = registry.get_artifact_id("a::foo")
    bar_id = registry.get_artifact_id("b::bar")
    engine = init_engine(tmp_path, repo_dir, state, registry)

    target.write_text("def bar_new():\n    return 2\n", encoding="utf-8")
    result = engine.update_file(str(target))

    assert result.artifact_consumption_state == "fresh"
    assert registry.get_artifact_id("a::bar_new") is not None
    assert registry.get_artifact_id("a::foo") is None
    assert registry.get_artifact_id("b::bar") is None
    assert registry.get_artifact_name(bar_id) == "b::bar"
    assert registry.get_artifact_id("foo") is None
    assert registry.get_artifact_id("bar") is None


def test_incremental_update_allocates_qualified_identity_for_new_symbol(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    target = repo_dir / "a.py"
    target.write_text("def existing():\n    return 1\n", encoding="utf-8")

    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    with registry.transaction():
        registry.sync_with_workspace({"a"}, {"a::existing"})
    existing_id = registry.get_artifact_id("a::existing")
    engine = init_engine(tmp_path, repo_dir, state, registry)

    target.write_text(
        "def existing():\n    return 2\n\ndef added():\n    return 3\n",
        encoding="utf-8",
    )
    engine.update_file(str(target))

    assert registry.get_artifact_id("a::existing") == existing_id
    assert registry.get_artifact_id("a::added") is not None
    assert registry.get_artifact_id("added") is None

def test_incremental_delete_imported_module(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    file_b = repo_dir / "b.py"
    file_b.write_text("from a import foo\n\ndef bar():\n    foo()\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    file_a.unlink()
    res = engine.update_file(str(file_a))
    assert res.graph_state == "fresh"
    
    registry_baseline = PersistentIdentityRegistry(str(repo_dir))
    state_baseline = bootstrap_state(repo_dir, registry_baseline)
    
    compare_states(engine.state, state_baseline, compare_artifacts=False)

def test_incremental_modify_consumers(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    file_b = repo_dir / "b.py"
    file_b.write_text("from a import foo\n\ndef bar():\n    foo()\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    file_b.write_text("def bar_modified():\n    pass\n")
    res = engine.update_file(str(file_b))
    
    assert res.artifact_consumption_state == "fresh"
    assert res.graph_state == "fresh"
    
    registry_baseline = PersistentIdentityRegistry(str(repo_dir))
    state_baseline = bootstrap_state(repo_dir, registry_baseline)
    
    compare_states(engine.state, state_baseline, compare_artifacts=False)
    
    # Check that incremental state dropped the consumer (b no longer listed)
    inc_foo_data = getattr(engine.state, "artifact_consumption", {}).get("a.foo", {})
    inc_consumers = inc_foo_data.get("consumers", []) if isinstance(inc_foo_data, dict) else inc_foo_data
    assert "b" not in inc_consumers
    
    # Check that full rebuild correctly dropped the consumer (b no longer listed)
    base_foo_data = getattr(state_baseline, "artifact_consumption", {}).get("a.foo", {})
    base_consumers = base_foo_data.get("consumers", []) if isinstance(base_foo_data, dict) else base_foo_data
    assert "b" not in base_consumers
    
def test_incremental_transaction_failure(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    old_modules_id = id(engine.state.modules)
    old_graph_id = id(engine.state.dependency_graph)
    
    file_a.write_text("def foo2():\n    pass\n")
    
    with patch("os.replace") as mock_replace:
        mock_replace.side_effect = OSError("Disk Full")
        with pytest.raises(OSError, match="Disk Full"):
            engine.update_file(str(file_a))
            
    assert id(engine.state.modules) == old_modules_id
    assert id(engine.state.dependency_graph) == old_graph_id
    assert len(engine.state.artifacts["a"]["own_symbols"]) == 1
    assert "foo" in engine.state.artifacts["a"]["own_symbols"]

def test_incremental_complex_sequence(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    file_b = repo_dir / "b.py"
    file_b.write_text("from a import foo\ndef bar():\n    foo()\n")
    engine.update_file(str(file_b))
    
    file_a.write_text("def foo2():\n    pass\n")
    engine.update_file(str(file_a))
    
    file_b.unlink()
    engine.update_file(str(file_b))
    
    registry_baseline = PersistentIdentityRegistry(str(repo_dir))
    state_baseline = bootstrap_state(repo_dir, registry_baseline)
    
    compare_states(engine.state, state_baseline, compare_artifacts=False)

def test_incremental_syntax_error(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    old_modules_id = id(engine.state.modules)
    
    # Introduce syntax error
    file_a.write_text("def foo(:\n    pass\n")
    res = engine.update_file(str(file_a))
    
    assert res.status == "SYNTAX_ERROR"
    assert res.line_number == 1
    assert res.column_number == 9
    assert res.graph_state == "stale"  # Because we default to stale on error, or it just wasn't reached.
    assert id(engine.state.modules) == old_modules_id
    assert "foo" in engine.state.artifacts["a"]["own_symbols"]

def test_incremental_graph_rebuild_failure(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    old_modules_id = id(engine.state.modules)
    
    file_b = repo_dir / "b.py"
    file_b.write_text("def bar():\n    pass\n")
    
    with patch("contextor.core.analysis.incremental.plan_executor.build_graph") as mock_build_graph:
        mock_build_graph.side_effect = RuntimeError("Graph Rebuild Crash")
        with pytest.raises(RuntimeError, match="Graph Rebuild Crash"):
            engine.update_file(str(file_b))
            
    # RAM state should remain completely unmodified
    assert id(engine.state.modules) == old_modules_id
    assert "b" not in engine.state.modules

def test_incremental_nested_mutation_isolation(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    # Capture original dict instance and its deep object (the module)
    orig_module_a = engine.state.modules["a"]
    orig_artifacts_a = engine.state.artifacts["a"]
    
    # Modify a.py
    file_a.write_text("def foo2():\n    pass\n")
    engine.update_file(str(file_a))
    
    # Assert that the old objects weren't mutated in-place
    assert len(orig_artifacts_a["own_symbols"]) == 1
    assert "foo" in orig_artifacts_a["own_symbols"]
    assert "foo2" not in orig_artifacts_a["own_symbols"]
    
    new_module_a = engine.state.modules["a"]
    new_artifacts_a = engine.state.artifacts["a"]
    assert id(orig_module_a) != id(new_module_a)
    assert id(orig_artifacts_a) != id(new_artifacts_a)

def test_incremental_successful_modify_after_failed_modify(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    file_a = repo_dir / "a.py"
    file_a.write_text("def foo():\n    pass\n")
    
    registry = PersistentIdentityRegistry(str(repo_dir))
    state = bootstrap_state(repo_dir, registry)
    engine = init_engine(tmp_path, repo_dir, state, registry)
    
    # 1. Failed Modify (Syntax Error)
    file_a.write_text("def foo(:\n")
    engine.update_file(str(file_a))
    assert "foo" in engine.state.artifacts["a"]["own_symbols"]
    
    # 2. Successful Modify
    file_a.write_text("def foo_new():\n    pass\n")
    res = engine.update_file(str(file_a))
    assert res.status == "UPDATED"
    assert "foo_new" in engine.state.artifacts["a"]["own_symbols"]
