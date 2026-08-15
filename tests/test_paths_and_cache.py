"""
Path resolution and the per-file cache.
"""

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.paths import (
    legacy_repo_cache_dir,
    output_dir,
    prune_orphaned_repository_caches,
    repo_cache_dir,
    repo_key,
)
from contextor.core.reporting_engine.persistent_registry import (
    PersistentIdentityRegistry,
)

import pytest

pytestmark = pytest.mark.live


def test_repo_key_distinguishes_same_named_repositories(tmp_path):
    first = tmp_path / "work" / "api"
    second = tmp_path / "private" / "api"

    first.mkdir(parents=True)
    second.mkdir(parents=True)

    assert repo_key(first) != repo_key(second)


def test_repo_cache_lives_outside_the_analyzed_repository(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))

    repo = tmp_path / "repo"
    repo.mkdir()

    cache_dir = repo_cache_dir(repo)

    assert repo.resolve() not in cache_dir.resolve().parents


def test_registered_repo_cache_is_keyed_by_durable_repo_id(tmp_path, monkeypatch):
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    repo = tmp_path / "repo"
    repo.mkdir()

    legacy = legacy_repo_cache_dir(repo)
    registry = PersistentIdentityRegistry(str(repo))

    assert repo_cache_dir(repo) == cache_root / "repositories" / registry.repo_id
    assert repo_cache_dir(repo) != legacy


def test_orphaned_repo_id_cache_is_removed_but_registered_and_unrelated_remain(
    tmp_path, monkeypatch
):
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(cache_root))
    repo = tmp_path / "repo"
    repo.mkdir()
    registry = PersistentIdentityRegistry(str(repo))
    repositories = cache_root / "repositories"
    valid = repositories / registry.repo_id
    orphan = repositories / "ctx_orphaned"
    unrelated = repositories / "legacy-path-cache"
    for directory in (valid, orphan, unrelated):
        directory.mkdir(parents=True)
        (directory / "marker.txt").write_text("keep?", encoding="utf-8")

    result = prune_orphaned_repository_caches()

    assert result == {"removed": ["ctx_orphaned"], "errors": []}
    assert valid.is_dir()
    assert unrelated.is_dir()
    assert not orphan.exists()


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))

    repo = tmp_path / "repo"
    repo.mkdir()

    source = repo / "module.py"
    source.write_text("x = 1\n", encoding="utf-8")

    manager = CacheManager(str(repo))

    assert manager.get(source) is None

    manager.set(source, {"imports": ["os"]})

    assert CacheManager(str(repo)).get(source) == {"imports": ["os"]}


def test_cache_is_invalidated_when_content_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))

    repo = tmp_path / "repo"
    repo.mkdir()

    source = repo / "module.py"
    source.write_text("x = 1\n", encoding="utf-8")

    CacheManager(str(repo)).set(source, {"imports": ["os"]})

    source.write_text("x = 2\n", encoding="utf-8")

    assert CacheManager(str(repo)).get(source) is None


def test_paths_that_flatten_to_the_same_name_do_not_collide(tmp_path, monkeypatch):
    """
    'core/graph.py' and 'core_graph.py' both flattened to
    'core_graph.py.json' under the old separator-substitution scheme.
    """

    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))

    repo = tmp_path / "repo"
    (repo / "core").mkdir(parents=True)

    nested = repo / "core" / "graph.py"
    flat = repo / "core_graph.py"

    nested.write_text("a = 1\n", encoding="utf-8")
    flat.write_text("a = 1\n", encoding="utf-8")

    manager = CacheManager(str(repo))

    manager.set(nested, {"id": "nested"})
    manager.set(flat, {"id": "flat"})

    assert manager.get(nested) == {"id": "nested"}
    assert manager.get(flat) == {"id": "flat"}


def test_output_dir_ignores_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_OUTPUT_DIR", str(tmp_path / "reports"))
    monkeypatch.chdir(tmp_path)

    assert output_dir() == (tmp_path / "reports").resolve()


def test_save_json_writes_into_the_output_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_OUTPUT_DIR", str(tmp_path / "reports"))
    monkeypatch.chdir(tmp_path)

    from contextor.core.reporting_engine.formatting import save_json

    save_json({"ok": True}, "output/demo.json")

    written = tmp_path / "reports" / "demo.json"

    assert written.exists()
    assert not (tmp_path / "output").exists()
