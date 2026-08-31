"""Parity coverage for RepositoryIndex automatic test-directory reuse."""

from pathlib import Path

from contextor.core.analysis import test_context as test_context_module
from contextor.core.analysis.test_context import TestContextIndex, discover_test_dirs
from contextor.core.reporting_layer import artifact_usage_report
from contextor.core.symbol_engine import indexer


def _write_fixture(root: Path) -> None:
    files = {
        "pkg/module.py": "class Target: pass\n",
        "test_root.py": "from pkg.module import Target\nassert Target\n",
        "root_test.py": "assert True\n",
        "root_helper.py": "value = 1\n",
        "tests/test_module.py": "from pkg.module import Target\nassert Target\n",
        "tests/conftest.py": "fixture = 1\n",
        "test/test_other.py": "assert True\n",
        "tests/nested/test_nested.py": "assert True\n",
        "specs/test_spec.py": "assert True\n",
        "excluded/test_excluded.py": "assert True\n",
        ".venv/tests/test_vendor.py": "assert True\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _legacy_dirs(root: Path, indexed: indexer.RepositoryIndex):
    return discover_test_dirs(
        str(root), allowed_python_paths=[module.path for module in indexed.modules.values()]
    )


def test_repository_index_map_matches_automatic_allowed_path_discovery_contract(
    tmp_path, isolated_dirs, monkeypatch
):
    root = tmp_path / "repo"
    _write_fixture(root)
    outside = tmp_path / "outside.py"
    outside.write_text("assert True\n", encoding="utf-8")
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")

    indexed = indexer.index_repository(str(root), excludes=["excluded"])
    legacy = _legacy_dirs(root, indexed)
    relative_legacy = discover_test_dirs(
        str(root),
        allowed_python_paths=[module.path for module in indexed.modules.values()]
        + [str(outside)],
    )
    absolute_legacy = discover_test_dirs(
        str(root),
        allowed_python_paths=[module.absolute_path for module in indexed.modules.values()]
        + [str(outside)],
    )

    assert indexed.automatic_test_dirs == legacy
    assert relative_legacy == legacy
    assert absolute_legacy == legacy
    assert list(indexed.automatic_test_dirs) == sorted(indexed.automatic_test_dirs)
    assert indexed.automatic_test_dirs[root] == frozenset(
        {"test_root.py", "root_test.py", "root_helper.py"}
    )
    assert indexed.automatic_test_dirs[root / "tests"] == frozenset(
        {"test_module.py", "conftest.py"}
    )
    assert indexed.automatic_test_dirs[root / "test"] == frozenset({"test_other.py"})
    assert root / "tests" / "nested" not in indexed.automatic_test_dirs
    assert root / "specs" not in indexed.automatic_test_dirs
    assert root / "excluded" not in indexed.automatic_test_dirs
    assert root / ".venv" / "tests" not in indexed.automatic_test_dirs
    assert all(outside.name not in names for names in indexed.automatic_test_dirs.values())

    context = TestContextIndex.build(root, test_dirs=indexed.automatic_test_dirs)
    assert str(root / "root_helper.py") not in context.files_info
    assert str(root / "test_root.py") in context.files_info
    assert str(root / "root_test.py") in context.files_info
    assert str(root / "tests" / "conftest.py") in context.files_info
    assert str(root / "tests" / "nested" / "test_nested.py") not in context.files_info


def test_repository_index_map_preserves_empty_root_entry(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "empty"
    root.mkdir()
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")

    indexed = indexer.index_repository(str(root))

    assert indexed.modules == {}
    assert indexed.automatic_test_dirs == {root.resolve(): frozenset()}


def test_repository_index_map_is_identical_for_serial_and_process_pool(tmp_path, isolated_dirs, monkeypatch):
    root = tmp_path / "repo"
    _write_fixture(root)

    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    serial = indexer.index_repository(str(root), excludes=["excluded"])
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL")
    pooled = indexer.index_repository(str(root), excludes=["excluded"])

    assert pooled.automatic_test_dirs == serial.automatic_test_dirs
    assert list(pooled.automatic_test_dirs) == list(serial.automatic_test_dirs)
    assert set(pooled.test_facts_by_path) == {
        str((directory / name).resolve())
        for directory, names in pooled.automatic_test_dirs.items()
        for name in names
        if test_context_module.is_test_context_candidate(root, directory / name)
    }


def test_report_uses_supplied_automatic_map_and_missing_map_keeps_discovery_fallback(
    tmp_path, isolated_dirs, monkeypatch
):
    root = tmp_path / "repo"
    _write_fixture(root)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    indexed = indexer.index_repository(str(root), excludes=["excluded"])
    original_discover = artifact_usage_report.discover_test_dirs
    calls = []

    def tracked_discover(*args, **kwargs):
        calls.append((args, kwargs))
        return original_discover(*args, **kwargs)

    monkeypatch.setattr(artifact_usage_report, "discover_test_dirs", tracked_discover)
    reused = artifact_usage_report.generate_artifact_usage_report(
        indexed.modules,
        str(root),
        test_facts_by_path=indexed.test_facts_by_path,
        automatic_test_dirs=indexed.automatic_test_dirs,
    )
    assert calls == []

    fallback = artifact_usage_report.generate_artifact_usage_report(
        indexed.modules,
        str(root),
        test_facts_by_path=indexed.test_facts_by_path,
    )
    assert len(calls) == 1
    assert reused["test_traceability"] == fallback["test_traceability"]


def test_explicit_custom_test_dirs_remain_authoritative(tmp_path):
    root = tmp_path / "repo"
    custom = root / "specs"
    custom.mkdir(parents=True)
    source = custom / "custom_case.py"
    source.write_text("from pkg.module import Target\nassert Target\n", encoding="utf-8")

    context = TestContextIndex.build(root, test_dirs={custom: frozenset({source.name})})

    assert str(source) in context.files_info
    assert context.find_test_files("pkg.module") == [str(source)]
