from contextor.core.analysis.cache_manager import CacheManager


def test_cache_manager_rechecks_file_content_in_same_instance(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "mod.py"
    source.write_text("value = 1\n", encoding="utf-8")

    manager = CacheManager(
        str(repo),
        cache_dir=tmp_path / "cache",
    )

    manager.set(source, {"value": 1})

    assert manager.get(source) == {"value": 1}

    source.write_text("value = 2\n", encoding="utf-8")

    assert manager.get(source) is None


def test_cache_manager_can_validate_exact_supplied_source_snapshot(
    tmp_path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "mod.py"
    source.write_text("value = 1\n", encoding="utf-8")
    manager = CacheManager(str(repo), cache_dir=tmp_path / "cache")
    raw = source.read_bytes()
    expected_hash = manager._compute_hash_bytes(raw)
    manager.set(source, {"value": 1}, source_bytes=raw)
    import orjson
    wrapper = orjson.loads(manager._get_cache_file_path(source).read_bytes())
    assert wrapper["_file_hash"] == expected_hash

    def fail_disk_hash(file_path):
        raise AssertionError("supplied source snapshot must avoid disk hash")

    monkeypatch.setattr(manager, "_compute_hash", fail_disk_hash)
    assert manager.get(source, source_bytes=raw) == {"value": 1}
