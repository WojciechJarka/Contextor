import os
import json
import shutil
import copy
import multiprocessing
import pytest
from pathlib import Path

from contextor.core.reporting_engine.persistent_registry import PersistentIdentityRegistry
from contextor.mcp import query_helpers

@pytest.fixture
def temp_repo(tmp_path):
    repo_dir = tmp_path / "TestRepo"
    repo_dir.mkdir()
    yield str(repo_dir)
    shutil.rmtree(repo_dir, ignore_errors=True)


def _hold_registry_lock_process(repo_path, acquired, release):
    registry = PersistentIdentityRegistry(repo_path)
    registry._lock()
    try:
        acquired.set()
        release.wait(timeout=10)
    finally:
        if registry._lock_file_obj is not None:
            registry._unlock()


def _observe_registry_constructor_process(
    repo_path, started, recovery_entered, completed, outcome
):
    original_recover = PersistentIdentityRegistry._recover_transaction

    def observe_recovery(self):
        recovery_entered.set()
        return original_recover(self)

    PersistentIdentityRegistry._recover_transaction = observe_recovery
    started.set()
    try:
        registry = PersistentIdentityRegistry(repo_path)
        module_ids = dict(
            registry._state.get("module_registry", {}).get("path_to_id", {})
        )
        outcome.put(("ok", module_ids))
    except BaseException as exc:
        outcome.put(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        completed.set()


def _pause_registry_constructor_process(
    repo_path,
    recovery_entered,
    release_recovery,
    load_entered,
    release_load,
    completed,
    outcome,
):
    original_recover = PersistentIdentityRegistry._recover_transaction
    original_load = PersistentIdentityRegistry._load_all

    def pause_recovery(self):
        recovery_entered.set()
        if not release_recovery.wait(timeout=10):
            raise TimeoutError("recovery phase was not released")
        return original_recover(self)

    def pause_load(self):
        load_entered.set()
        if not release_load.wait(timeout=10):
            raise TimeoutError("load phase was not released")
        return original_load(self)

    PersistentIdentityRegistry._recover_transaction = pause_recovery
    PersistentIdentityRegistry._load_all = pause_load
    try:
        PersistentIdentityRegistry(repo_path)
        outcome.put("constructed")
    except BaseException as exc:
        outcome.put(f"error:{type(exc).__name__}:{exc}")
    finally:
        completed.set()


def _probe_registry_lock_process(
    repo_path, ready, attempt, attempted, acquired
):
    registry = PersistentIdentityRegistry(repo_path)
    ready.set()
    if not attempt.wait(timeout=10):
        return
    attempted.set()
    registry._lock()
    try:
        acquired.set()
    finally:
        registry._unlock()


def _pause_registry_writer_replace_process(
    repo_path, staged, release, completed, outcome
):
    import contextor.core.reporting_engine.persistent_registry as registry_module

    original_replace = registry_module.os.replace
    paused = False

    def pause_first_registry_replace(source, destination):
        nonlocal paused
        if not paused and Path(source).name.endswith(".json.tmp"):
            paused = True
            staged.set()
            if not release.wait(timeout=10):
                raise TimeoutError("staged transaction was not released")
        return original_replace(source, destination)

    registry_module.os.replace = pause_first_registry_replace
    try:
        registry = PersistentIdentityRegistry(repo_path)
        with registry.transaction():
            registry.sync_with_workspace({"seed.py", "during_write.py"}, set())
        outcome.put(("committed", registry.get_module_id("during_write.py")))
    except BaseException as exc:
        outcome.put(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        registry_module.os.replace = original_replace
        completed.set()


def _fail_registry_constructor_process(
    repo_path, failure_stage, lock_acquired, failed, release, outcome
):
    original_lock = PersistentIdentityRegistry._lock

    def observe_lock(self):
        original_lock(self)
        lock_acquired.set()

    PersistentIdentityRegistry._lock = observe_lock
    if failure_stage == "recovery":
        def fail_recovery(self):
            raise RuntimeError("injected recovery failure")

        PersistentIdentityRegistry._recover_transaction = fail_recovery
    else:
        def fail_load(self):
            raise RuntimeError("injected load failure")

        PersistentIdentityRegistry._load_all = fail_load

    captured_exception = None
    try:
        PersistentIdentityRegistry(repo_path)
        outcome.put("unexpected_success")
    except BaseException as exc:
        captured_exception = exc
        outcome.put(("failed", failure_stage, str(exc)))
        failed.set()
        release.wait(timeout=10)
    finally:
        # Retain the traceback (and failed constructor instance) until the
        # parent has checked that another process can acquire the same lock.
        _ = captured_exception


def _probe_registry_constructor_process(repo_path, started, completed, outcome):
    started.set()
    try:
        registry = PersistentIdentityRegistry(repo_path)
        outcome.put(("ok", registry.lock_file.as_posix()))
    except BaseException as exc:
        outcome.put(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        completed.set()

def test_checkpoint_restore_persists_exact_registry_state(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry.sync_with_workspace({"seed"}, {"seed::SEED_VALUE"})
        registry.register_report_references(
            "baseline.json", [registry.get_module_id("seed")]
        )

    checkpoint = registry.create_checkpoint()
    seed_id = registry.get_module_id("seed")
    seed_artifact_id = registry.get_artifact_id("seed::SEED_VALUE")

    with registry.transaction():
        registry.sync_with_workspace(
            {"seed", "added"},
            {"seed::SEED_VALUE", "added::ADDED_VALUE"},
        )
        registry.register_report_references(
            "added.json", [registry.get_module_id("added")]
        )

    assert registry.get_module_id("added") is not None
    assert registry.get_artifact_id("added::ADDED_VALUE") is not None
    assert registry._state["module_slots"] != checkpoint["module_slots"]
    assert registry._state["artifact_slots"] != checkpoint["artifact_slots"]
    assert registry._state["output_references"] != checkpoint["output_references"]

    registry.restore_checkpoint(checkpoint)
    reloaded = PersistentIdentityRegistry(temp_repo)

    assert reloaded.get_module_id("seed") == seed_id
    assert reloaded.get_artifact_id("seed::SEED_VALUE") == seed_artifact_id
    assert reloaded.get_module_id("added") is None
    assert reloaded.get_artifact_id("added::ADDED_VALUE") is None
    assert reloaded._state["module_registry"] == checkpoint["module_registry"]
    assert reloaded._state["artifact_registry"] == checkpoint["artifact_registry"]
    assert reloaded._state["module_recovery"] == checkpoint["module_recovery"]
    assert reloaded._state["artifact_recovery"] == checkpoint["artifact_recovery"]
    assert reloaded._state["module_slots"] == checkpoint["module_slots"]
    assert reloaded._state["artifact_slots"] == checkpoint["artifact_slots"]
    assert reloaded._state["output_references"] == checkpoint["output_references"]


def test_read_registries_healthy_read_keeps_bytes_mtime_and_ids(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry.sync_with_workspace({"pkg.module"}, {"pkg.module::run"})
    expected = (
        copy.deepcopy(registry._state["module_registry"]["path_to_id"]),
        copy.deepcopy(registry._state["module_registry"]["id_to_path"]),
        copy.deepcopy(registry._state["artifact_registry"]["path_to_id"]),
        copy.deepcopy(registry._state["artifact_registry"]["id_to_path"]),
    )
    files = tuple(registry.files.values())
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
    marker = registry.transaction_file
    temporary = tuple(path.with_suffix(".json.tmp") for path in files)
    assert not marker.exists()
    assert not any(path.exists() for path in temporary)

    first = query_helpers.read_registries(Path(temp_repo))
    second = query_helpers.read_registries(Path(temp_repo))

    assert first == expected == second
    assert {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in files} == before
    assert not marker.exists()
    assert not any(path.exists() for path in temporary)
    reloaded = PersistentIdentityRegistry(temp_repo)
    assert reloaded.get_module_id("pkg.module") == expected[0]["pkg.module"]
    assert reloaded.get_artifact_id("pkg.module::run") == expected[2]["pkg.module::run"]


def test_read_registries_does_not_enter_write_transaction(temp_repo, monkeypatch):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry.sync_with_workspace({"pkg.module"}, {"pkg.module::run"})

    def forbidden(_self):
        pytest.fail("healthy read entered a write transaction")

    monkeypatch.setattr(PersistentIdentityRegistry, "transaction", forbidden)
    result = query_helpers.read_registries(Path(temp_repo))
    assert result[0]["pkg.module"] == registry.get_module_id("pkg.module")
    assert result[2]["pkg.module::run"] == registry.get_artifact_id("pkg.module::run")


def test_read_registries_recovers_interrupted_commit(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry.sync_with_workspace({"pkg.module"}, set())
    path = registry.files["module_registry"]
    next_state = json.loads(path.read_text(encoding="utf-8"))
    next_state["path_to_id"]["pkg.recovered"] = "9/1"
    next_state["id_to_path"]["9/1"] = "pkg.recovered"
    staged = path.with_suffix(".json.tmp")
    staged.write_text(json.dumps(next_state), encoding="utf-8")
    registry.transaction_file.write_text(
        json.dumps({"status": "committing", "files": ["module_registry"]}),
        encoding="utf-8",
    )

    result = query_helpers.read_registries(Path(temp_repo))

    assert result[0]["pkg.recovered"] == "9/1"
    assert result[1]["9/1"] == "pkg.recovered"
    assert not staged.exists()
    assert not registry.transaction_file.exists()

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


def test_read_transaction_returns_existing_ids_without_allocating_missing_ids(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        module_id = registry.get_module_id("existing.py")
        artifact_id = registry.get_artifact_id("existing::symbol")

    with registry.read_transaction():
        before = copy.deepcopy(registry._state)

        assert registry.get_module_id("existing.py") == module_id
        assert registry.get_artifact_id("existing::symbol") == artifact_id
        assert registry.get_module_id("missing.py") is None
        assert registry.get_artifact_id("missing::symbol") is None
        assert registry._state == before


def test_write_transaction_allocates_and_persists_missing_ids(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        module_id = registry.get_module_id("new.py")
        artifact_id = registry.get_artifact_id("new::symbol")

    reloaded = PersistentIdentityRegistry(temp_repo)
    assert reloaded.get_module_id("new.py") == module_id
    assert reloaded.get_artifact_id("new::symbol") == artifact_id


def test_write_transaction_nested_in_read_transaction_fails_without_mutation(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.read_transaction():
        before = copy.deepcopy(registry._state)

        with pytest.raises(
            RuntimeError,
            match="Cannot enter write transaction inside read transaction\\.",
        ):
            with registry.transaction():
                pass

        assert registry.get_module_id("missing.py") is None
        assert registry.get_artifact_id("missing::symbol") is None
        assert registry._state == before


def test_read_transaction_nested_in_write_transaction_views_current_generation(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        module_id = registry.get_module_id("current.py")
        artifact_id = registry.get_artifact_id("current::symbol")

        with registry.read_transaction():
            assert registry.get_module_id("current.py") == module_id
            assert registry.get_artifact_id("current::symbol") == artifact_id

    reloaded = PersistentIdentityRegistry(temp_repo)
    assert reloaded.get_module_id("current.py") == module_id
    assert reloaded.get_artifact_id("current::symbol") == artifact_id


def test_read_transaction_repairs_in_memory_without_persisting_projection(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    with registry.transaction():
        registry._state["module_registry"]["id_to_path"]["9/3"] = "orphan.py"

    registry_file = registry.files["module_registry"]
    before = registry_file.read_bytes()

    with registry.read_transaction():
        assert "9/3" not in registry._state["module_registry"]["id_to_path"]
        assert registry._state["module_recovery"]["9/3"]["path"] == "orphan.py"
        assert registry._state["module_slots"]["9"] == 3

    assert registry_file.read_bytes() == before


def test_constructor_waits_for_registry_lock_held_by_another_process(temp_repo):
    registry = PersistentIdentityRegistry(temp_repo)
    context = multiprocessing.get_context("spawn")
    holder_acquired = context.Event()
    release_holder = context.Event()
    constructor_started = context.Event()
    recovery_entered = context.Event()
    constructor_completed = context.Event()
    outcome = context.Queue()
    holder = context.Process(
        target=_hold_registry_lock_process,
        args=(temp_repo, holder_acquired, release_holder),
    )
    constructor = context.Process(
        target=_observe_registry_constructor_process,
        args=(
            temp_repo,
            constructor_started,
            recovery_entered,
            constructor_completed,
            outcome,
        ),
    )
    try:
        holder.start()
        assert holder_acquired.wait(timeout=5)
        constructor.start()
        assert constructor_started.wait(timeout=5)
        assert recovery_entered.wait(timeout=0.5) is False

        release_holder.set()
        assert recovery_entered.wait(timeout=5)
        assert constructor_completed.wait(timeout=5)
        assert outcome.get(timeout=2)[0] == "ok"
        constructor.join(timeout=5)
        holder.join(timeout=5)
        assert constructor.exitcode == 0
        assert holder.exitcode == 0
    finally:
        release_holder.set()
        for process in (constructor, holder):
            if process.pid is not None:
                process.join(timeout=3)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)


def test_constructor_holds_registry_os_lock_during_recovery_and_load(temp_repo):
    PersistentIdentityRegistry(temp_repo)
    context = multiprocessing.get_context("spawn")
    probe_ready = context.Event()
    attempt_probe = context.Event()
    probe_attempted = context.Event()
    probe_acquired = context.Event()
    probe = context.Process(
        target=_probe_registry_lock_process,
        args=(temp_repo, probe_ready, attempt_probe, probe_attempted, probe_acquired),
    )
    recovery_entered = context.Event()
    release_recovery = context.Event()
    load_entered = context.Event()
    release_load = context.Event()
    constructor_completed = context.Event()
    outcome = context.Queue()
    constructor = context.Process(
        target=_pause_registry_constructor_process,
        args=(
            temp_repo,
            recovery_entered,
            release_recovery,
            load_entered,
            release_load,
            constructor_completed,
            outcome,
        ),
    )
    try:
        probe.start()
        assert probe_ready.wait(timeout=5)
        constructor.start()
        assert recovery_entered.wait(timeout=5)

        attempt_probe.set()
        assert probe_attempted.wait(timeout=5)
        assert probe_acquired.wait(timeout=0.5) is False

        release_recovery.set()
        assert load_entered.wait(timeout=5)
        assert probe_acquired.wait(timeout=0.5) is False

        release_load.set()
        assert constructor_completed.wait(timeout=5)
        assert outcome.get(timeout=2) == "constructed"
        assert probe_acquired.wait(timeout=5)
        constructor.join(timeout=5)
        probe.join(timeout=5)
        assert constructor.exitcode == 0
        assert probe.exitcode == 0
    finally:
        release_recovery.set()
        release_load.set()
        attempt_probe.set()
        for process in (constructor, probe):
            if process.pid is not None:
                process.join(timeout=3)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)


def test_constructor_does_not_consume_active_writer_staging_and_loads_commit(temp_repo):
    initial = PersistentIdentityRegistry(temp_repo)
    with initial.transaction():
        initial.sync_with_workspace({"seed.py"}, set())
    assert initial.get_module_id("seed.py") == "1/1"

    context = multiprocessing.get_context("spawn")
    staged = context.Event()
    release_writer = context.Event()
    writer_completed = context.Event()
    writer_outcome = context.Queue()
    writer = context.Process(
        target=_pause_registry_writer_replace_process,
        args=(temp_repo, staged, release_writer, writer_completed, writer_outcome),
    )
    constructor_started = context.Event()
    recovery_entered = context.Event()
    constructor_completed = context.Event()
    constructor_outcome = context.Queue()
    constructor = context.Process(
        target=_observe_registry_constructor_process,
        args=(
            temp_repo,
            constructor_started,
            recovery_entered,
            constructor_completed,
            constructor_outcome,
        ),
    )
    try:
        writer.start()
        assert staged.wait(timeout=5)

        marker = initial.transaction_file
        temporary_files = {
            name: path.with_suffix(".json.tmp")
            for name, path in initial.files.items()
        }
        assert marker.exists()
        assert all(path.exists() for path in temporary_files.values())
        marker_before = marker.read_bytes()
        staged_before = {
            name: path.read_bytes() for name, path in temporary_files.items()
        }

        constructor.start()
        assert constructor_started.wait(timeout=5)
        assert recovery_entered.wait(timeout=0.5) is False
        assert marker.read_bytes() == marker_before
        assert {
            name: path.read_bytes() for name, path in temporary_files.items()
        } == staged_before

        release_writer.set()
        assert writer_completed.wait(timeout=5)
        writer_result = writer_outcome.get(timeout=2)
        assert writer_result == ("committed", "2/1")
        assert recovery_entered.wait(timeout=5)
        assert constructor_completed.wait(timeout=5)
        constructor_result = constructor_outcome.get(timeout=2)
        assert constructor_result == (
            "ok",
            {"seed.py": "1/1", "during_write.py": "2/1"},
        )
        assert not marker.exists()
        assert not any(path.exists() for path in temporary_files.values())
        writer.join(timeout=5)
        constructor.join(timeout=5)
        assert writer.exitcode == 0
        assert constructor.exitcode == 0
    finally:
        release_writer.set()
        for process in (constructor, writer):
            if process.pid is not None:
                process.join(timeout=3)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)


@pytest.mark.parametrize("failure_stage", ["recovery", "load"])
def test_constructor_releases_registry_lock_after_recovery_or_load_failure(
    temp_repo, failure_stage
):
    PersistentIdentityRegistry(temp_repo)
    context = multiprocessing.get_context("spawn")
    lock_acquired = context.Event()
    failed = context.Event()
    release_failure = context.Event()
    failure_outcome = context.Queue()
    failing_process = context.Process(
        target=_fail_registry_constructor_process,
        args=(
            temp_repo,
            failure_stage,
            lock_acquired,
            failed,
            release_failure,
            failure_outcome,
        ),
    )
    probe_started = context.Event()
    probe_completed = context.Event()
    probe_outcome = context.Queue()
    probe = context.Process(
        target=_probe_registry_constructor_process,
        args=(temp_repo, probe_started, probe_completed, probe_outcome),
    )
    try:
        failing_process.start()
        assert lock_acquired.wait(timeout=5)
        assert failed.wait(timeout=5)
        assert failure_outcome.get(timeout=2) == (
            "failed",
            failure_stage,
            f"injected {failure_stage} failure",
        )

        probe.start()
        assert probe_started.wait(timeout=5)
        assert probe_completed.wait(timeout=2)
        assert probe_outcome.get(timeout=2)[0] == "ok"
        probe.join(timeout=5)
        assert probe.exitcode == 0
    finally:
        release_failure.set()
        for process in (probe, failing_process):
            if process.pid is not None:
                process.join(timeout=3)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)


def test_independent_registry_instances_share_the_same_os_lock_path(temp_repo):
    first = PersistentIdentityRegistry(temp_repo)
    second = PersistentIdentityRegistry(temp_repo)

    assert first.registry_dir == second.registry_dir
    assert first.lock_file == second.lock_file
    assert first.lock_file.resolve() == second.lock_file.resolve()
