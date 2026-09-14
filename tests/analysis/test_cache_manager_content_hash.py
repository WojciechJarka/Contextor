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
