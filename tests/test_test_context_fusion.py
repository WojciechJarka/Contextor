import json
from pathlib import Path

import pytest

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.analysis import test_context as test_context_module
from contextor.core.analysis.test_context import TestContextIndex, discover_test_dirs
from contextor.core.symbol_engine import indexer


def _cache_data(root: Path, source: Path) -> dict:
    manager = CacheManager(str(root))
    return json.loads(manager._get_cache_file_path(source).read_text(encoding="utf-8"))["data"]


def _write_repo(root: Path, test_source: str = "from pkg.mod import Target\nassert Target\n") -> Path:
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pkg" / "mod.py").write_text("class Target: pass\n", encoding="utf-8")
    source = root / "tests" / "test_mod.py"
    source.write_text(test_source, encoding="utf-8")
    (root / "tests" / "conftest.py").write_text("fixture = 1\n", encoding="utf-8")
    return source


def test_candidate_domain_is_shared_and_excludes_nested_test_directories(tmp_path):
    root = tmp_path / "repo"
    source = _write_repo(root)
    nested = root / "tests" / "nested"
    nested.mkdir()
    (nested / "test_nested.py").write_text("assert True\n", encoding="utf-8")
    (root / "main.py").write_text("value = 1\n", encoding="utf-8")

    dirs = discover_test_dirs(str(root), allowed_python_paths=[
        str(path) for path in root.rglob("*.py")
    ])
    assert set(dirs) == {root, root / "tests"}
    assert test_context_module.is_test_context_candidate(root, source)
    assert test_context_module.is_test_context_candidate(root, root / "tests" / "conftest.py")
    assert not test_context_module.is_test_context_candidate(root, root / "main.py")
    assert not test_context_module.is_test_context_candidate(root, nested / "test_nested.py")


def test_explicit_custom_test_dirs_preserve_supplied_directory_membership(tmp_path):
    root = tmp_path / "repo"
    custom = root / "specs"
    custom.mkdir(parents=True)
    source = custom / "case.py"
    source.write_text("from pkg.mod import Target\nassert Target\n", encoding="utf-8")
    (custom / "notes.txt").write_text("not Python\n", encoding="utf-8")

    index = TestContextIndex.build(
        str(root),
        test_dirs={custom: frozenset({"case.py", "notes.txt"})},
    )

    assert str(source) in index.files_info
    assert str(custom / "notes.txt") not in index.files_info
    assert index.find_test_files("pkg.mod") == [str(source)]


def test_worker_facts_match_authoritative_extractor_field_for_field(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "repo"
    source = _write_repo(
        root,
        """import pkg.mod as alias
from pkg.mod import Target as Renamed
from .relative import local as local_name
value = alias.Target
def test_case():
    assert Renamed
    obj.assert_called_once()
    call(Target, local_name)
""",
    )
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    original_parse = test_context_module.parse_source
    tree = original_parse(source)
    expected = test_context_module._extract_test_file_facts(tree)

    result = indexer.index_repository(str(root))
    facts = result.test_facts_by_path[str(source.resolve())]
    assert set(facts["imported_modules"]) == expected[0]
    assert set(facts["names"]) == expected[1]
    assert facts["has_assertions"] is expected[2]


def test_cold_then_current_schema_warm_has_zero_test_fact_parse_and_visitor(
    tmp_path, isolated_dirs, monkeypatch
):
    root = tmp_path / "repo"
    source = _write_repo(root)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    indexer.index_repository(str(root))
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    parse_calls = []
    visitor_calls = []
    original_parse = indexer.parse_source
    original_extract = indexer._extract_test_file_facts
    monkeypatch.setattr(indexer, "parse_source", lambda path: (parse_calls.append(path) or original_parse(path)))
    monkeypatch.setattr(indexer, "_extract_test_file_facts", lambda tree: (visitor_calls.append(tree) or original_extract(tree)))

    warm = indexer.index_repository(str(root))
    assert parse_calls == []
    assert visitor_calls == []
    assert str(source.resolve()) in warm.test_facts_by_path

    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    monkeypatch.undo()
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def test_non_candidate_cache_record_is_not_migrated(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "repo"
    source = root / "module.py"
    root.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    CacheManager(str(root)).set(source, {"imports": [], "error": None})
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    calls = []
    original = indexer.parse_source
    monkeypatch.setattr(indexer, "parse_source", lambda path: (calls.append(path) or original(path)))

    result = indexer.index_repository(str(root))
    assert str(source.resolve()) not in result.test_facts_by_path
    assert "test_facts" not in _cache_data(root, source)
    assert len(calls) == 1


def test_missing_schema_and_source_change_invalidate_test_facts(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "repo"
    source = _write_repo(root)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    first = indexer.index_repository(str(root))
    data = _cache_data(root, source)
    data["test_facts"]["schema_version"] = 0
    CacheManager(str(root)).set(source, data)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    migrated = indexer.index_repository(str(root))
    assert migrated.test_facts_by_path[str(source.resolve())]["has_assertions"] is True
    assert _cache_data(root, source)["test_facts"]["schema_version"] == indexer.TEST_FACTS_SCHEMA_VERSION

    source.write_text("from pkg.mod import Target\nassert Target\nvalue = 2\n", encoding="utf-8")
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    changed = indexer.index_repository(str(root))
    assert changed.test_facts_by_path[str(source.resolve())]["names"]
    assert first.test_facts_by_path[str(source.resolve())] != changed.test_facts_by_path[str(source.resolve())]


def test_valid_empty_facts_are_available(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "repo"
    source = _write_repo(root, "")
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    result = indexer.index_repository(str(root))
    facts = result.test_facts_by_path[str(source.resolve())]
    assert facts == {"imported_modules": [], "names": [], "has_assertions": False}
    assert _cache_data(root, source)["test_facts"]["status"] == "available"


def test_failed_test_fact_migration_preserves_other_facts_and_removes_stale_envelope(
    tmp_path, isolated_dirs, monkeypatch
):
    root = tmp_path / "repo"
    source = _write_repo(root)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    seeded = indexer.index_repository(str(root))
    data = _cache_data(root, source)
    data["test_facts"] = {
        "schema_version": 0,
        "status": "available",
        "facts": {"names": ["stale"]},
    }
    CacheManager(str(root)).set(source, data)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    original = indexer._extract_test_file_facts
    monkeypatch.setattr(indexer, "_extract_test_file_facts", lambda tree: (_ for _ in ()).throw(RuntimeError("test visitor failed")))

    failed = indexer.index_repository(str(root))
    persisted = _cache_data(root, source)
    assert str(source.resolve()) not in failed.test_facts_by_path
    assert "test_facts" not in persisted
    assert failed.symbol_facts_by_module == seeded.symbol_facts_by_module
    assert failed.reference_facts_by_module == seeded.reference_facts_by_module

    monkeypatch.setattr(indexer, "_extract_test_file_facts", original)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    recovered = indexer.index_repository(str(root))
    assert str(source.resolve()) in recovered.test_facts_by_path
    assert _cache_data(root, source)["test_facts"]["status"] == "available"


def test_supplied_facts_avoid_ast_parse_and_authoritative_visitor(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    source = _write_repo(root)
    test_dirs = discover_test_dirs(str(root), allowed_python_paths=[str(path) for path in root.rglob("*.py")])
    facts = {
        str(source.resolve()): {
            "imported_modules": ["pkg.mod"],
            "names": ["Target", "assert"],
            "has_assertions": True,
        },
        str((root / "tests" / "conftest.py").resolve()): {
            "imported_modules": [], "names": [], "has_assertions": False
        },
    }
    modules = {"pkg.mod": type("Module", (), {"absolute_path": str(root / "pkg" / "mod.py"), "path": "pkg/mod.py"})()}
    monkeypatch.setattr(test_context_module, "parse_source", lambda path: (_ for _ in ()).throw(AssertionError("supplied parse")))
    monkeypatch.setattr(test_context_module, "_extract_test_file_facts", lambda tree: (_ for _ in ()).throw(AssertionError("supplied visitor")))

    index = TestContextIndex.build(
        str(root), test_dirs=test_dirs, modules=modules, test_facts_by_path=facts
    )
    info = index.files_info[str(source)]
    assert info.imported_modules == {"pkg.mod"}
    assert info.names == {"Target", "assert"}
    assert info.has_assertions is True


def test_serial_and_process_pool_test_fact_side_tables_match(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "repo"
    _write_repo(root)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    serial = indexer.index_repository(str(root)).test_facts_by_path
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pooled = indexer.index_repository(str(root)).test_facts_by_path
    assert pooled == serial
