import os
import json
import shutil
import pytest
from pathlib import Path

from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry

@pytest.fixture
def temp_repo(tmp_path):
    repo_dir = tmp_path / "TestRepo"
    repo_dir.mkdir()
    yield str(repo_dir)
    shutil.rmtree(repo_dir, ignore_errors=True)

def test_identity_preservation(temp_repo):
    # nowy plik dostaje ID
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry.sync_with_workspace({"parser.py"}, set())
    
    parser_id = registry.get_module_id("parser.py")
    assert parser_id == "1/1" # Assuming starting from 1
    
    # drugi scan zachowuje ID
    with registry.transaction():
        registry.sync_with_workspace({"parser.py", "graph.py"}, set())
    
    assert registry.get_module_id("parser.py") == "1/1"
    assert registry.get_module_id("graph.py") == "2/1"
    
    # usunięcie przenosi do recovery
    with registry.transaction():
        registry.sync_with_workspace({"graph.py"}, set()) # parser.py is missing
        
    assert registry.get_module_id("parser.py") is None
    assert registry.get_module_path("1/1") == "parser.py" # Should still be resolvable via recovery
    
    # powrót przywraca ID (but wait, user said "nowy plik po usunięciu dostaje nową generację" 
    # but "powrót przywraca ID"? Actually, we just need to ensure that the recovery works)
    # Actually, the user clarified: 
    # "Nowy skan: plik wraca: system sprawdza: module_registry (brak), module_recovery (znajduje) -> przywraca 17/4. Nie tworzy 17/5. Generacja jest tylko dla nowej tożsamości."
    # Let's test that!
    
    with registry.transaction():
        registry.sync_with_workspace({"parser.py", "graph.py"}, set())
        
    assert registry.get_module_id("parser.py") == "1/1" # Restored from recovery
    
    # Nowy plik po usunięciu (different path) dostaje nową generację w tym samym slocie
    # Remove parser.py again
    with registry.transaction():
        registry.sync_with_workspace({"graph.py"}, set())
        
    # Now add a completely new file
    with registry.transaction():
        registry.sync_with_workspace({"graph.py", "new_file.py"}, set())
        
    assert registry.get_module_id("new_file.py") == "1/2" # Reused slot 1, bumped generation

def test_collision_prevention(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry.sync_with_workspace({"parser.py"}, set())
        
    old_id = registry.get_module_id("parser.py") # 1/1
    
    with registry.transaction():
        registry.sync_with_workspace(set(), set()) # Delete it
        
    with registry.transaction():
        registry.sync_with_workspace({"new_parser.py"}, set()) # New file takes slot 1
        
    new_id = registry.get_module_id("new_parser.py") # 1/2
    
    assert old_id != new_id
    
    # Rewriter nadal rozpoznaje 17/4 (or 1/1 here)
    assert registry.get_module_path("1/1") == "parser.py"
    assert registry.get_module_path("1/2") == "new_parser.py"

def test_multi_repo_isolation(tmp_path):
    repo_a = str(tmp_path / "RepoA")
    repo_b = str(tmp_path / "RepoB")
    
    os.makedirs(repo_a)
    os.makedirs(repo_b)
    
    reg_a = PersistentIdentityRegistry(repo_a)
    with reg_a.transaction():
        reg_a.sync_with_workspace({"main.py"}, set())
        
    reg_b = PersistentIdentityRegistry(repo_b)
    with reg_b.transaction():
        reg_b.sync_with_workspace({"main.py"}, set())
        
    assert reg_a.get_module_id("main.py") == "1/1"
    assert reg_b.get_module_id("main.py") == "1/1"
    
    # Ensure they have separate metadata
    assert reg_a.repo_id != reg_b.repo_id


def test_each_repository_has_separate_directory_and_repo_meta_json(tmp_path):
    repo_a = tmp_path / "RepoA"
    repo_b = tmp_path / "RepoB"
    repo_a.mkdir()
    repo_b.mkdir()

    reg_a = PersistentIdentityRegistry(str(repo_a))
    reg_b = PersistentIdentityRegistry(str(repo_b))
    with reg_a.transaction():
        reg_a.sync_with_workspace({"pkg.alpha"}, {"pkg.alpha::run"})
    with reg_b.transaction():
        reg_b.sync_with_workspace({"pkg.beta"}, {"pkg.beta::run"})

    assert reg_a.registry_dir != reg_b.registry_dir
    assert reg_a.registry_dir.is_dir()
    assert reg_b.registry_dir.is_dir()

    meta_a = json.loads((reg_a.registry_dir / "repo.meta.json").read_text(encoding="utf-8"))
    meta_b = json.loads((reg_b.registry_dir / "repo.meta.json").read_text(encoding="utf-8"))
    assert meta_a["repo_id"] != meta_b["repo_id"]
    assert reg_a.registry_dir.name == f"RepoA__{reg_a.repo_id}"
    assert reg_b.registry_dir.name == f"RepoB__{reg_b.repo_id}"
    assert not (repo_a / ".contextor").exists()
    assert not (repo_b / ".contextor").exists()

    modules_a = json.loads((reg_a.registry_dir / "module_registry.json").read_text(encoding="utf-8"))
    modules_b = json.loads((reg_b.registry_dir / "module_registry.json").read_text(encoding="utf-8"))
    slots_a = json.loads((reg_a.registry_dir / "module_slots.json").read_text(encoding="utf-8"))
    slots_b = json.loads((reg_b.registry_dir / "module_slots.json").read_text(encoding="utf-8"))
    assert set(modules_a["path_to_id"]) == {"pkg.alpha"}
    assert set(modules_b["path_to_id"]) == {"pkg.beta"}
    assert slots_a["1"] == 1
    assert slots_b["1"] == 1

def test_garbage_collection_with_output_references(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry.sync_with_workspace({"old_file.py", "another.py"}, set())
        
    old_id = registry.get_module_id("old_file.py")
    
    # Save a report that references old_id
    with registry.transaction():
        registry.register_report_references("report1.json", [old_id])
        
    # Delete old_file.py
    with registry.transaction():
        registry.sync_with_workspace({"another.py"}, set())
        
    # It should be in recovery
    assert registry.get_module_path(old_id) == "old_file.py"
    
    # Run GC with a very low limit to force deletion of oldest (if unreferenced)
    with registry.transaction():
        registry.run_garbage_collector(max_module_recovery_bytes=0) # 0 bytes forces it
        
    # It should STILL be in recovery because it is referenced in output_references!
    assert registry.get_module_path(old_id) == "old_file.py"
    
    # Unregister the report
    with registry.transaction():
        registry.unregister_report_references("report1.json")
        
    # Run GC again
    with registry.transaction():
        registry.run_garbage_collector(max_module_recovery_bytes=0)
        
    # Now it should be purged
    assert registry.get_module_path(old_id) is None


def test_registry_never_allocates_slots_for_empty_identities(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)

    with registry.transaction():
        assert registry.get_module_id(None) is None
        assert registry.get_module_id("") is None
        assert registry.get_artifact_id(None) is None
        assert registry.get_artifact_id("  ") is None

    assert set(registry._state["module_slots"]) == {"schema_version"}
    assert set(registry._state["artifact_slots"]) == {"schema_version"}


def test_registry_repairs_reverse_only_entries_into_recovery(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry._state["module_registry"]["id_to_path"]["9/3"] = "orphan.py"
        registry._state["module_registry"]["id_to_path"]["10/2"] = None

    with registry.transaction():
        assert "9/3" not in registry._state["module_registry"]["id_to_path"]
        assert "10/2" not in registry._state["module_registry"]["id_to_path"]
        assert registry._state["module_recovery"]["9/3"]["path"] == "orphan.py"
        assert "10/2" not in registry._state["module_recovery"]
        assert registry._state["module_slots"]["9"] == 3
        assert registry._state["module_slots"]["10"] == 2
