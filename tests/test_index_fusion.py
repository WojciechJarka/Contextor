import hashlib
import json

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.analysis.process_pool_lifecycle import (
    terminate_active_process_pools,
)
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


def test_reused_indexer_pool_uses_current_parent_cache_root(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"

    first_cache = tmp_path / "cache-a"
    second_cache = tmp_path / "cache-b"

    monkeypatch.delenv(
        "CONTEXTOR_DISABLE_PROCESS_POOL",
        raising=False,
    )

    terminate_active_process_pools(
        timeout=1.0,
    )

    try:
        monkeypatch.setenv(
            "CONTEXTOR_CACHE_DIR",
            str(first_cache),
        )

        first_bytes = b"def first():\n    return 1\n"
        source.write_bytes(first_bytes)

        first = indexer.index_repository(
            str(root)
        )

        first_fingerprint = hashlib.sha256(first_bytes).hexdigest()
        assert first.source_fingerprints_by_module["module"] == first_fingerprint

        assert (
            first
            .symbol_facts_by_module["module"]
            ["facts"]["functions"]
            == ["first"]
        )

        first_payload = (
            CacheManager(str(root))
            ._get_cache_file_path(source)
        )

        assert first_payload.is_file()

        monkeypatch.setenv(
            "CONTEXTOR_CACHE_DIR",
            str(second_cache),
        )

        second_bytes = b"def second():\n    return 2\n"
        source.write_bytes(second_bytes)

        second = indexer.index_repository(
            str(root)
        )

        second_fingerprint = hashlib.sha256(second_bytes).hexdigest()
        assert second.source_fingerprints_by_module["module"] == second_fingerprint
        assert first_fingerprint != second_fingerprint

        assert (
            second
            .symbol_facts_by_module["module"]
            ["facts"]["functions"]
            == ["second"]
        )

        second_manager = CacheManager(
            str(root)
        )
        second_payload = (
            second_manager
            ._get_cache_file_path(source)
        )

        assert second_payload.is_file()

        cached = json.loads(
            second_payload.read_text()
        )

        assert (
            cached["data"]["symbol_facts"]
            == second.symbol_facts_by_module[
                "module"
            ]
        )

    finally:
        terminate_active_process_pools(
            timeout=1.0,
        )


def test_new_format_cache_hit_reuses_cached_facts_without_ast_parse(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("value = 1\n", encoding="utf-8")
    indexer.index_repository(str(root))
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    parse_calls = []
    original_parse = indexer.parse_source_snapshot
    monkeypatch.setattr(
        indexer,
        "parse_source_snapshot",
        lambda snapshot, path: (
            parse_calls.append(path) or original_parse(snapshot, path)
        ),
    )

    extraction_calls = []
    original_extract = indexer.extract_file_symbols
    monkeypatch.setattr(
        indexer,
        "extract_file_symbols",
        lambda path, *, tree=None: (
            extraction_calls.append(path) or original_extract(path, tree=tree)
        ),
    )

    result = indexer.index_repository(str(root))

    assert parse_calls == []
    assert extraction_calls == []
    assert result.modules["module"].imports == []
    assert result.symbol_facts_by_module["module"]["status"] == "available"
    assert result.lineage_facts_by_source["module.py"].source_key == "module.py"


def test_source_change_invalidates_symbol_facts_then_complete_warm_hit_skips_ast_parse(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("def old():\n    return 1\n", encoding="utf-8")
    indexer.index_repository(str(root))

    source.write_text("def new():\n    return 2\n", encoding="utf-8")
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    parse_calls = []
    original_parse = indexer.parse_source_snapshot
    monkeypatch.setattr(
        indexer,
        "parse_source_snapshot",
        lambda snapshot, path: (
            parse_calls.append(path) or original_parse(snapshot, path)
        ),
    )

    changed = indexer.index_repository(str(root))

    assert len(parse_calls) == 1
    assert changed.symbol_facts_by_module["module"]["facts"]["functions"] == ["new"]

    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    parse_calls.clear()
    warm = indexer.index_repository(str(root))
    assert parse_calls == []
    assert warm.lineage_facts_by_source["module.py"].source_key == "module.py"
    assert warm.symbol_facts_by_module["module"]["facts"]["functions"] == ["new"]


def test_legacy_cache_is_migrated_once_then_complete_warm_hit_skips_ast_parse(
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
    original_parse = indexer.parse_source_snapshot
    monkeypatch.setattr(
        indexer,
        "parse_source_snapshot",
        lambda snapshot, path: (
            parse_calls.append(path) or original_parse(snapshot, path)
        ),
    )

    migrated = indexer.index_repository(str(root))
    assert migrated.symbol_facts_by_module["module"]["status"] == "available"
    assert len(parse_calls) == 1

    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    parse_calls.clear()
    warm = indexer.index_repository(str(root))
    assert warm.symbol_facts_by_module["module"]["status"] == "available"
    assert parse_calls == []
    assert warm.lineage_facts_by_source["module.py"].source_key == "module.py"


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
    original_parse = indexer.parse_source_snapshot
    parse_calls = []
    monkeypatch.setattr(
        indexer,
        "parse_source_snapshot",
        lambda snapshot, path: (
            parse_calls.append(path) or original_parse(snapshot, path)
        ),
    )

    result = indexer.index_repository(str(root))

    assert len(parse_calls) == 1
    assert result.symbol_facts_by_module["module"]["facts"]["functions"] == ["hello"]


def test_symbol_facts_semantic_version_invalidates_stale_class_field_globals(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text(
        "MODULE_REAL = 1\n"
        "\n"
        "class Holder:\n"
        "    CLASS_FIELD = 1\n",
        encoding="utf-8",
    )

    indexer.index_repository(str(root))
    cached = _cache_payload(root, source)["data"]
    old_version = indexer.SYMBOL_FACTS_SCHEMA_VERSION - 1
    cached["symbol_facts"]["schema_version"] = old_version
    cached["symbol_facts"]["facts"]["globals"] = [
        "CLASS_FIELD",
        "MODULE_REAL",
    ]
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    extraction_calls = []
    original_extract = indexer.extract_file_symbols
    monkeypatch.setattr(
        indexer,
        "extract_file_symbols",
        lambda path, *, tree=None: (
            extraction_calls.append(path)
            or original_extract(path, tree=tree)
        ),
    )

    recomputed = indexer.index_repository(str(root))
    facts = recomputed.symbol_facts_by_module["module"]

    assert len(extraction_calls) == 1
    assert facts["schema_version"] == indexer.SYMBOL_FACTS_SCHEMA_VERSION
    assert facts["facts"]["globals"] == ["MODULE_REAL"]
    assert "CLASS_FIELD" not in facts["facts"]["globals"]
    assert _cache_payload(root, source)["data"]["symbol_facts"]["schema_version"] == 2

    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    extraction_calls.clear()
    warm = indexer.index_repository(str(root))

    assert extraction_calls == []
    assert warm.symbol_facts_by_module["module"]["facts"]["globals"] == [
        "MODULE_REAL"
    ]


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


def test_index_source_fingerprint_cold_warm_raw_bytes(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    first = root / "alpha.py"
    second = root / "beta.py"
    first_bytes = b"import beta\r\ndef alpha():\r\n    return beta.value\r\n"
    second_bytes = b"value = 7\n"
    first.write_bytes(first_bytes)
    second.write_bytes(second_bytes)

    cold = indexer.index_repository(str(root))
    expected = {
        "alpha": hashlib.sha256(first_bytes).hexdigest(),
        "beta": hashlib.sha256(second_bytes).hexdigest(),
    }
    assert set(cold.modules) == set(expected)
    assert cold.source_fingerprints_by_module == expected
    assert list(cold.source_fingerprints_by_module) == sorted(expected)

    def forbidden_parse(*_args, **_kwargs):
        raise AssertionError("warm index reparsed a source")

    with monkeypatch.context() as scoped:
        scoped.setattr(indexer, "parse_source_snapshot", forbidden_parse)
        warm = indexer.index_repository(str(root))

    assert warm.source_fingerprints_by_module == expected
    assert [item.module for item in warm.modules["alpha"].imports] == ["beta"]
    assert warm.symbol_facts_by_module["alpha"]["status"] == "available"
    assert warm.reference_facts_by_module["alpha"]["status"] == "available"


def test_index_source_fingerprint_body_only_change(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "alpha.py"
    other = root / "beta.py"
    original_bytes = b"import beta\ndef answer():\n    return 1\n"
    changed_bytes = b"import beta\ndef answer():\n    return 2\n"
    other_bytes = b"value = 7\n"
    source.write_bytes(original_bytes)
    other.write_bytes(other_bytes)

    initial = indexer.index_repository(str(root))
    source.write_bytes(changed_bytes)
    changed = indexer.index_repository(str(root))

    assert changed.source_fingerprints_by_module["alpha"] == hashlib.sha256(changed_bytes).hexdigest()
    assert changed.source_fingerprints_by_module["alpha"] != initial.source_fingerprints_by_module["alpha"]
    assert changed.source_fingerprints_by_module["beta"] == initial.source_fingerprints_by_module["beta"]
    assert changed.source_fingerprints_by_module["beta"] == hashlib.sha256(other_bytes).hexdigest()
    assert changed.modules["alpha"].imports == initial.modules["alpha"].imports

    warm = indexer.index_repository(str(root))
    assert warm.source_fingerprints_by_module == changed.source_fingerprints_by_module


def test_index_source_fingerprint_skipped_and_excluded(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    valid_bytes = b"value = 1\n"
    (root / "valid.py").write_bytes(valid_bytes)
    (root / "invalid.py").write_bytes(b"def broken(:\n")
    (root / "excluded.py").write_bytes(b"value = 2\n")

    result = indexer.index_repository(str(root), excludes=["excluded.py"])

    assert set(result.modules) == {"valid"}
    assert {item.path for item in result.skipped} == {"invalid.py"}
    assert list(result.source_fingerprints_by_module) == ["valid"]
    assert result.source_fingerprints_by_module["valid"] == hashlib.sha256(valid_bytes).hexdigest()
    assert set(result.source_fingerprints_by_module) == set(result.modules)


def test_index_source_fingerprint_survives_optional_fact_failure(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source_bytes = b"import os\ndef hello():\n    return os.name\n"
    source.write_bytes(source_bytes)

    def fail_symbols(path, *, tree=None):
        raise RuntimeError("visitor failed")

    monkeypatch.setattr(indexer, "extract_file_symbols", fail_symbols)
    result = indexer.index_repository(str(root))

    assert "module" in result.modules
    assert [item.module for item in result.modules["module"].imports] == ["os"]
    assert result.symbol_facts_by_module["module"]["status"] == "failure"
    assert "symbol_facts" not in _cache_payload(root, source)["data"]
    assert result.source_fingerprints_by_module == {
        "module": hashlib.sha256(source_bytes).hexdigest()
    }


def test_repository_index_legacy_construction():
    modules = {}
    skipped = []
    symbol_facts = {"symbol": {"status": "available"}}
    reference_facts = {"reference": {"status": "available"}}
    lineage_facts = {}
    collision_facts = {}
    test_facts = {}
    test_dirs = {}
    result = indexer.RepositoryIndex(
        modules,
        skipped,
        symbol_facts,
        reference_facts,
        lineage_facts,
        collision_facts,
        test_facts,
        test_dirs,
    )

    assert result.modules is modules
    assert result.skipped is skipped
    assert result.symbol_facts_by_module is symbol_facts
    assert result.reference_facts_by_module is reference_facts
    assert result.lineage_facts_by_source is lineage_facts
    assert result.collision_facts_by_module is collision_facts
    assert result.test_facts_by_path is test_facts
    assert result.automatic_test_dirs is test_dirs
    assert result.source_fingerprints_by_module == {}
