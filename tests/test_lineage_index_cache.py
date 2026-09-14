from pathlib import Path

import contextor.core.symbol_engine.indexer as indexer
from contextor.core.analysis.lineage_extraction import (
    LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION,
)


def test_warm_index_reuses_cached_lineage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "mod.py"
    source.write_text(
        "def f(value):\n"
        "    return value + 1\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    indexer._CACHE_MANAGERS.clear()

    first = indexer.index_repository(str(repo))
    first_lineage = first.lineage_facts_by_source["mod.py"]

    def fail_extract(*args, **kwargs):
        raise AssertionError("warm lineage cache hit must skip extraction")

    monkeypatch.setattr(indexer, "extract_lineage_source_facts", fail_extract)

    second = indexer.index_repository(str(repo))

    assert second.lineage_facts_by_source["mod.py"] == first_lineage


def test_legacy_cache_without_lineage_is_migrated_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "mod.py"
    source.write_text(
        "def f(value):\n"
        "    return value + 1\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    indexer._CACHE_MANAGERS.clear()

    indexer.index_repository(str(repo))

    root_str = str(repo.resolve())
    cache = indexer._CACHE_MANAGERS[root_str]
    cached_data = cache.get(source)
    assert cached_data is not None
    assert "lineage_facts" in cached_data

    legacy_data = dict(cached_data)
    legacy_data.pop("lineage_facts")
    cache.set(source, legacy_data)

    original_extract = indexer.extract_lineage_source_facts
    calls = 0

    def counted_extract(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_extract(*args, **kwargs)

    monkeypatch.setattr(
        indexer,
        "extract_lineage_source_facts",
        counted_extract,
    )

    indexer.index_repository(str(repo))

    assert calls == 1

    migrated_data = cache.get(source)
    assert migrated_data is not None
    assert "lineage_facts" in migrated_data

    def fail_extract(*args, **kwargs):
        raise AssertionError("migrated lineage cache must skip extraction")

    monkeypatch.setattr(
        indexer,
        "extract_lineage_source_facts",
        fail_extract,
    )

    indexer.index_repository(str(repo))


def test_stale_lineage_schema_is_migrated_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "mod.py"
    source.write_text(
        "def f(value):\n"
        "    return value + 1\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("CONTEXTOR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    indexer._CACHE_MANAGERS.clear()

    indexer.index_repository(str(repo))

    root_str = str(repo.resolve())
    cache = indexer._CACHE_MANAGERS[root_str]
    cached_data = cache.get(source)
    assert cached_data is not None

    stale_data = dict(cached_data)
    stale_lineage = dict(stale_data["lineage_facts"])
    stale_lineage["schema_version"] = (
        LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION + 1
    )
    stale_data["lineage_facts"] = stale_lineage
    cache.set(source, stale_data)

    original_extract = indexer.extract_lineage_source_facts
    calls = 0

    def counted_extract(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_extract(*args, **kwargs)

    monkeypatch.setattr(
        indexer,
        "extract_lineage_source_facts",
        counted_extract,
    )

    indexer.index_repository(str(repo))

    assert calls == 1

    migrated_data = cache.get(source)
    assert migrated_data is not None
    assert (
        migrated_data["lineage_facts"]["schema_version"]
        == LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION
    )

    def fail_extract(*args, **kwargs):
        raise AssertionError("current-schema lineage cache must skip extraction")

    monkeypatch.setattr(
        indexer,
        "extract_lineage_source_facts",
        fail_extract,
    )

    indexer.index_repository(str(repo))
