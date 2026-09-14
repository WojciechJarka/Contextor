from pathlib import Path

import contextor.core.symbol_engine.indexer as indexer


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
