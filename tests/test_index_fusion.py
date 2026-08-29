import json

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.reporting_layer.artifact_usage_report import collect_module_artifacts
from contextor.core.symbol_engine import indexer


def _cache_payload(root, source):
    manager = CacheManager(str(root))
    return json.loads(manager._get_cache_file_path(source).read_text())


def test_index_cache_miss_stores_symbol_facts(tmp_path, isolated_dirs):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("def hello():\n    return 1\n", encoding="utf-8")

    result = indexer.index_repository(str(root))

    record = result.symbol_facts_by_module["module"]
    assert record["status"] == "available"
    assert record["facts"]["functions"] == ["hello"]
    assert _cache_payload(root, source)["data"]["symbol_facts"] == record


def test_new_format_cache_hit_does_not_parse(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("value = 1\n", encoding="utf-8")
    indexer.index_repository(str(root))
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    def forbidden_parse(path):
        raise AssertionError(f"unexpected parse: {path}")

    monkeypatch.setattr(indexer, "parse_source", forbidden_parse)

    result = indexer.index_repository(str(root))

    assert result.modules["module"].imports == []
    assert result.symbol_facts_by_module["module"]["status"] == "available"


def test_legacy_cache_is_migrated_once_then_warm_hit_is_parse_free(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("def hello():\n    return 1\n", encoding="utf-8")
    CacheManager(str(root)).set(source, {"imports": [], "error": None})
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    parse_calls = []
    original_parse = indexer.parse_source
    monkeypatch.setattr(
        indexer,
        "parse_source",
        lambda path: (parse_calls.append(path) or original_parse(path)),
    )

    migrated = indexer.index_repository(str(root))
    assert migrated.symbol_facts_by_module["module"]["status"] == "available"
    assert len(parse_calls) == 1

    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    parse_calls.clear()
    warm = indexer.index_repository(str(root))
    assert warm.symbol_facts_by_module["module"]["status"] == "available"
    assert parse_calls == []


def test_symbol_facts_schema_mismatch_recomputes(tmp_path, isolated_dirs, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("def hello():\n    return 1\n", encoding="utf-8")
    CacheManager(str(root)).set(
        source,
        {
            "imports": [],
            "error": None,
            "symbol_facts": {
                "schema_version": 0,
                "status": "available",
                "facts": {"functions": ["stale"]},
            },
        },
    )
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    original_parse = indexer.parse_source
    parse_calls = []
    monkeypatch.setattr(
        indexer,
        "parse_source",
        lambda path: (parse_calls.append(path) or original_parse(path)),
    )

    result = indexer.index_repository(str(root))

    assert len(parse_calls) == 1
    assert result.symbol_facts_by_module["module"]["facts"]["functions"] == ["hello"]


def test_symbol_failure_keeps_module_and_retries_without_negative_cache(
    tmp_path, isolated_dirs, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("import os\ndef hello():\n    return os.name\n", encoding="utf-8")
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")

    def fail_symbols(path, *, tree=None):
        raise RuntimeError("visitor failed")

    original_symbols = indexer.extract_file_symbols
    monkeypatch.setattr(indexer, "extract_file_symbols", fail_symbols)
    failed = indexer.index_repository(str(root))
    record = failed.symbol_facts_by_module["module"]
    assert "module" in failed.modules
    assert [item.module for item in failed.modules["module"].imports] == ["os"]
    assert record["status"] == "failure"
    artifacts, failures = collect_module_artifacts(
        failed.modules,
        str(root),
        symbol_facts_by_module=failed.symbol_facts_by_module,
    )
    assert "module" not in artifacts
    assert failures == {"module": "RuntimeError: visitor failed"}
    assert "symbol_facts" not in _cache_payload(root, source)["data"]

    monkeypatch.setattr(indexer, "extract_file_symbols", original_symbols)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    retried = indexer.index_repository(str(root))
    assert retried.symbol_facts_by_module["module"]["status"] == "available"
