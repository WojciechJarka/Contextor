"""FULL FileState must describe exactly the currently indexed source domain."""

from __future__ import annotations

import builtins
import hashlib
import json
import os
from pathlib import Path

import pytest

from contextor.core.analysis.state_manager import (
    FileState,
    FileStateManager,
    RepositoryAnalysisState,
    load_engine_state,
)
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir


SOURCES = {
    "alpha/__init__.py": b"",
    "alpha/api.py": b"def api_function():\n    return 1\n",
    "beta/__init__.py": b"",
    "beta/consumer.py": (
        b"from alpha.api import api_function\n"
        b"CONSUMER_RESULT = api_function()\n"
    ),
    "loose.py": b"LOOSE_VALUE = 0\n",
}


def _write_repo(root: Path) -> None:
    root.mkdir()
    for relative, content in SOURCES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _source_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*.py")
    }


def _run_full(root: Path):
    errors, _ = ContextorFacade.analyze_project(str(root))
    assert not errors, f"FULL analysis failed for {root}: {errors!r}"

    cache = repo_cache_dir(root)
    metadata = read_metadata(cache)
    assert metadata is not None
    assert metadata.state_file and metadata.file_state_file

    state = load_engine_state(
        str(cache),
        metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root.resolve()),
    )
    assert isinstance(state, RepositoryAnalysisState)
    assert state.state_id == metadata.state_id
    assert state.revision == metadata.revision

    manager = FileStateManager(str(cache))
    assert manager.baseline_status == "trusted"
    assert manager.state_id == metadata.state_id
    assert manager.revision == metadata.revision
    return state, manager, metadata


def _assert_exact_file_state(root: Path, state, manager) -> None:
    expected = _source_hashes(root)
    canonical_paths = {
        module.absolute_path
        for module in state.modules.values()
        if module.absolute_path
    }
    assert canonical_paths == set(expected)
    assert manager.tracked_paths() == canonical_paths
    assert {
        path: file_state.sha256
        for path, file_state in manager._state.items()
    } == expected


def test_retain_tracked_paths_restricts_ram_domain_without_io(tmp_path, monkeypatch):
    manager = FileStateManager(str(tmp_path / "cache"))
    first, second, obsolete = (str(tmp_path / name) for name in ("a.py", "b.py", "old.py"))
    first_state = FileState(1, 2, "a" * 64)
    second_state = FileState(3, 4, "b" * 64)
    manager._state.update(
        {first: first_state, second: second_state, obsolete: FileState(5, 6, "c" * 64)}
    )
    mapping = manager._state

    def unexpected_io(*_args, **_kwargs):
        pytest.fail("retain_tracked_paths attempted filesystem I/O or persistence")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", unexpected_io)
        patch.setattr(os, "stat", unexpected_io)
        patch.setattr(manager, "save", unexpected_io)
        manager.retain_tracked_paths({first, second})

    assert manager._state is mapping
    assert manager.tracked_paths() == {first, second}
    assert manager._state[first] is first_state
    assert manager._state[second] is second_state
    assert list((tmp_path / "cache").iterdir()) == []


@pytest.mark.parametrize(
    "invalid_domain",
    [None, [], {""}, {42}, {Path("relative.py")}],
)
def test_retain_tracked_paths_rejects_invalid_domain_before_mutation(
    tmp_path, invalid_domain
):
    manager = FileStateManager(str(tmp_path / "cache"))
    manager._state.update(
        {"first.py": FileState(1, 2, "a" * 64), "second.py": FileState(3, 4, "b" * 64)}
    )
    mapping = manager._state
    original = manager._state.copy()

    with pytest.raises(ValueError, match="Current indexed file domain"):
        manager.retain_tracked_paths(invalid_domain)

    assert manager._state is mapping
    assert manager._state == original


def test_full_after_module_deletion_reconciles_domain_and_keeps_old_generation(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "repo"
    _write_repo(root)
    first_state, first_manager, first_metadata = _run_full(root)
    _assert_exact_file_state(root, first_state, first_manager)
    assert len(first_manager._state) == 5

    cache = repo_cache_dir(root)
    old_files = [cache / first_metadata.state_file, cache / first_metadata.file_state_file]
    if first_metadata.lineage_manifest_file:
        manifest = cache / first_metadata.lineage_manifest_file
        old_files.append(manifest)
        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        old_files.extend(
            cache / entry["file"] for entry in manifest_payload["sources"].values()
        )
    old_generation = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in set(old_files)
    }

    removed = (root / "beta" / "consumer.py").resolve()
    removed.unlink()
    second_state, second_manager, second_metadata = _run_full(root)

    assert second_metadata.revision > first_metadata.revision
    assert str(removed) not in {
        module.absolute_path for module in second_state.modules.values()
    }
    assert str(removed) not in second_manager.tracked_paths()
    assert len(second_manager._state) == 4
    _assert_exact_file_state(root, second_state, second_manager)

    persisted = json.loads(
        (cache / second_metadata.file_state_file).read_text(encoding="utf-8")
    )
    assert set(persisted["files"]) == second_manager.tracked_paths()
    assert {
        path: entry["sha256"] for path, entry in persisted["files"].items()
    } == _source_hashes(root)
    assert all(
        path.read_bytes() == content and path.stat().st_mtime_ns == mtime_ns
        for path, (content, mtime_ns) in old_generation.items()
    )


def test_unchanged_full_reanalysis_preserves_exact_domain_and_hashes(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "repo"
    _write_repo(root)
    first_state, first_manager, first_metadata = _run_full(root)
    _assert_exact_file_state(root, first_state, first_manager)
    first_hashes = {
        path: item.sha256 for path, item in first_manager._state.items()
    }

    second_state, second_manager, second_metadata = _run_full(root)
    assert second_metadata.revision > first_metadata.revision
    _assert_exact_file_state(root, second_state, second_manager)
    assert second_manager.tracked_paths() == first_manager.tracked_paths()
    assert {
        path: item.sha256 for path, item in second_manager._state.items()
    } == first_hashes


def test_full_discards_controlled_stale_tracked_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "repo"
    _write_repo(root)
    first_state, first_manager, first_metadata = _run_full(root)
    _assert_exact_file_state(root, first_state, first_manager)

    cache = repo_cache_dir(root)
    generation = cache / first_metadata.file_state_file
    payload = json.loads(generation.read_text(encoding="utf-8"))
    stale_path = str((root / "deleted.py").resolve())
    assert not (root / "deleted.py").exists()
    payload["files"][stale_path] = FileState(1, 1, "f" * 64).to_dict()
    generation.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    controlled_baseline = FileStateManager(str(cache))
    assert controlled_baseline.baseline_status == "trusted"
    assert controlled_baseline.tracked_paths() == first_manager.tracked_paths() | {stale_path}

    second_state, second_manager, second_metadata = _run_full(root)
    assert second_metadata.revision > first_metadata.revision
    assert stale_path not in second_manager.tracked_paths()
    _assert_exact_file_state(root, second_state, second_manager)
