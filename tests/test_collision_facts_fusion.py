import json

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.domain.module import Module
from contextor.core.symbol_engine import indexer
from contextor.core.validator.collisions import (
    compute_collisions_from_facts,
    extract_repository_collision_facts,
)


def _cache_data(root, source):
    manager = CacheManager(str(root))
    return json.loads(manager._get_cache_file_path(source).read_text(encoding="utf-8"))["data"]


def _serial(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _repo(tmp_path, text):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text(text, encoding="utf-8")
    return root, source


def test_cold_index_facts_match_repository_extraction_and_materialize_all_fields(
    tmp_path, isolated_dirs, monkeypatch
):
    _serial(monkeypatch)
    root, _ = _repo(
        tmp_path,
        "class Public:\n    def method(self):\n        pass\n\n"
        "async def async_public():\n    return 1\n\n"
        "MAXIMUM = 2\n\n"
        "def main():\n    pass\n\n"
        "def _private():\n    pass\n",
    )

    result = indexer.index_repository(str(root))
    indexed = result.collision_facts_by_module
    legacy = extract_repository_collision_facts(result.modules)

    assert indexed == legacy
    assert [fact["name"] for fact in indexed["module"]] == ["Public", "async_public", "MAXIMUM"]
    for fact in indexed["module"]:
        assert list(fact) == [
            "name", "type", "file", "file_path", "code", "line_start", "line_end", "col_start", "col_end"
        ]
        assert fact["file"] == "module"
        assert fact["file_path"] == str((root / "module.py").resolve())
        assert isinstance(fact["code"], str)


def test_warm_current_schema_has_zero_parse_and_collision_extraction(
    tmp_path, isolated_dirs, monkeypatch
):
    _serial(monkeypatch)
    root, _ = _repo(tmp_path, "def public():\n    return 1\n")
    indexer.index_repository(str(root))
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected warm extraction")

    monkeypatch.setattr(indexer, "parse_source", forbidden)
    monkeypatch.setattr(indexer, "extract_module_collision_facts", forbidden)
    warm = indexer.index_repository(str(root))

    assert warm.collision_facts_by_module["module"][0]["name"] == "public"


def test_missing_collision_field_migrates_once_and_preserves_other_fact_families(
    tmp_path, isolated_dirs, monkeypatch
):
    _serial(monkeypatch)
    root, source = _repo(tmp_path, "def public():\n    return 1\n")
    seeded = indexer.index_repository(str(root))
    data = _cache_data(root, source)
    data.pop("collision_facts")
    CacheManager(str(root)).set(source, data)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    parse_calls = []
    collision_calls = []
    real_parse = indexer.parse_source
    real_extract = indexer.extract_module_collision_facts
    monkeypatch.setattr(indexer, "parse_source", lambda path: (parse_calls.append(path) or real_parse(path)))
    monkeypatch.setattr(
        indexer,
        "extract_module_collision_facts",
        lambda *args, **kwargs: (collision_calls.append(args[1]) or real_extract(*args, **kwargs)),
    )

    migrated = indexer.index_repository(str(root))

    assert len(parse_calls) == len(collision_calls) == 1
    assert migrated.symbol_facts_by_module == seeded.symbol_facts_by_module
    assert migrated.reference_facts_by_module == seeded.reference_facts_by_module
    assert _cache_data(root, source)["collision_facts"]["status"] == "available"


def test_failed_collision_migration_drops_invalid_envelope_and_retry_populates(
    tmp_path, isolated_dirs, monkeypatch
):
    _serial(monkeypatch)
    root, source = _repo(tmp_path, "def public():\n    return 1\n")
    seeded = indexer.index_repository(str(root))
    data = _cache_data(root, source)
    data["collision_facts"]["schema_version"] = 0
    CacheManager(str(root)).set(source, data)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    real_extract = indexer.extract_module_collision_facts
    monkeypatch.setattr(
        indexer,
        "extract_module_collision_facts",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("transient")),
    )
    failed = indexer.index_repository(str(root))

    persisted = _cache_data(root, source)
    assert set(failed.modules) != set(failed.collision_facts_by_module)
    assert failed.collision_facts_by_module == {}
    assert "collision_facts" not in persisted
    assert persisted["symbol_facts"] == seeded.symbol_facts_by_module["module"]
    assert persisted["reference_facts"] == seeded.reference_facts_by_module["module"]

    monkeypatch.setattr(
        indexer,
        "extract_module_collision_facts",
        real_extract,
    )
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    retried = indexer.index_repository(str(root))

    assert retried.collision_facts_by_module["module"][0]["name"] == "public"
    assert _cache_data(root, source)["collision_facts"]["status"] == "available"


def test_schema_mismatch_and_source_change_reextract_once(tmp_path, isolated_dirs, monkeypatch):
    _serial(monkeypatch)
    root, source = _repo(tmp_path, "def old_name():\n    return 1\n")
    indexer.index_repository(str(root))
    data = _cache_data(root, source)
    data["collision_facts"]["schema_version"] = 0
    CacheManager(str(root)).set(source, data)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    parse_calls = []
    real_parse = indexer.parse_source
    monkeypatch.setattr(indexer, "parse_source", lambda path: (parse_calls.append(path) or real_parse(path)))
    mismatched = indexer.index_repository(str(root))
    assert len(parse_calls) == 1
    assert mismatched.collision_facts_by_module["module"][0]["name"] == "old_name"

    source.write_text("def new_name():\n    return 2\n", encoding="utf-8")
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    parse_calls.clear()
    changed = indexer.index_repository(str(root))
    assert len(parse_calls) == 1
    assert changed.collision_facts_by_module["module"][0]["name"] == "new_name"


def test_valid_empty_collision_facts_persist_and_cover_module(tmp_path, isolated_dirs, monkeypatch):
    _serial(monkeypatch)
    root, source = _repo(tmp_path, "def _private():\n    pass\n")
    result = indexer.index_repository(str(root))

    assert result.collision_facts_by_module == {"module": []}
    envelope = _cache_data(root, source)["collision_facts"]
    assert envelope == {
        "schema_version": indexer.COLLISION_FACTS_SCHEMA_VERSION,
        "status": "available",
        "facts": [],
    }


def test_collision_failure_is_not_cached_and_uses_full_domain_fallback(
    tmp_path, isolated_dirs, monkeypatch
):
    _serial(monkeypatch)
    root, source = _repo(tmp_path, "def public():\n    return 1\n")

    real_extract = indexer.extract_module_collision_facts
    monkeypatch.setattr(
        indexer,
        "extract_module_collision_facts",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("transient")),
    )
    failed = indexer.index_repository(str(root))

    assert failed.collision_facts_by_module == {}
    assert "collision_facts" not in _cache_data(root, source)

    fallback_calls = []
    monkeypatch.setattr(indexer, "extract_repository_collision_facts", lambda modules: (fallback_calls.append(modules) or {"module": []}))
    assert indexer.assemble_collision_facts_or_fallback(failed.modules, failed.collision_facts_by_module) == {"module": []}
    assert fallback_calls == [failed.modules]

    monkeypatch.setattr(indexer, "extract_module_collision_facts", real_extract)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    retried = indexer.index_repository(str(root))
    assert retried.collision_facts_by_module["module"][0]["name"] == "public"


def test_incomplete_or_invalid_side_table_never_merges_with_fallback(tmp_path, isolated_dirs, monkeypatch):
    root, a = _repo(tmp_path, "def one():\n    return 1\n")
    b = root / "other.py"
    b.write_text("def two():\n    return 2\n", encoding="utf-8")
    modules = {
        "module": Module("module", "module.py", str(a), []),
        "other": Module("other", "other.py", str(b), []),
    }
    fallback = {"module": [], "other": []}
    monkeypatch.setattr(indexer, "extract_repository_collision_facts", lambda got: fallback)

    assert indexer.assemble_collision_facts_or_fallback(modules, {"module": []}) is fallback
    assert indexer.assemble_collision_facts_or_fallback(modules, {"module": [{"bad": "fact"}], "other": []}) is fallback


def test_serial_and_process_pool_side_tables_match(tmp_path, isolated_dirs, monkeypatch):
    root, _ = _repo(tmp_path, "def first():\n    return 1\n")
    (root / "other.py").write_text("VALUE = 3\n", encoding="utf-8")
    _serial(monkeypatch)
    serial = indexer.index_repository(str(root))
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL")
    pooled = indexer.index_repository(str(root))

    assert pooled.collision_facts_by_module == serial.collision_facts_by_module
    assert compute_collisions_from_facts(pooled.collision_facts_by_module) == []


def test_full_facade_uses_complete_indexed_facts_without_repository_fallback(
    tmp_path, isolated_dirs, monkeypatch
):
    from contextor.core.api.facade import ContextorFacade
    import contextor.core.api.facade as facade_module

    _serial(monkeypatch)
    root, _ = _repo(tmp_path, "def public():\n    return 1\n")
    observed = []
    real_assemble = facade_module.assemble_collision_facts_or_fallback

    def track_assemble(modules, facts):
        observed.append((set(modules), set(facts)))
        return real_assemble(modules, facts)

    monkeypatch.setattr(facade_module, "assemble_collision_facts_or_fallback", track_assemble)
    monkeypatch.setattr(
        indexer,
        "extract_repository_collision_facts",
        lambda modules: (_ for _ in ()).throw(AssertionError("unexpected fallback")),
    )

    errors, analysis_result = ContextorFacade.analyze_project(str(root))

    assert errors == []
    assert analysis_result.collision_facts == {"module": analysis_result.collision_facts["module"]}
    assert observed == [({"module"}, {"module"})]
