import json

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.api import facade
from contextor.core.reference.index import (
    RepositoryReferenceIndex,
    _assemble_reexport_map,
    assemble_reference_index_or_fallback,
)
from contextor.core.reference.shared import _build_reexport_map
from contextor.core.reporting_layer.artifact_usage_report import (
    generate_artifact_usage_report,
)
from contextor.core.symbol_engine import indexer


def _payload(root, source):
    manager = CacheManager(str(root))
    return json.loads(manager._get_cache_file_path(source).read_text())["data"]


def _reset_worker_cache(root):
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)


def test_cold_index_emits_json_safe_reference_facts_into_combined_cache(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("import os\ndef use(): return os.getcwd()\n", encoding="utf-8")

    result = indexer.index_repository(str(root))
    record = result.reference_facts_by_module["module"]

    assert record["schema_version"] == indexer.REFERENCE_FACTS_SCHEMA_VERSION
    assert record["status"] == "available"
    json.dumps(record)
    assert _payload(root, source)["reference_facts"] == record


def test_warm_reference_hit_performs_zero_parse_and_zero_extraction(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("def value(): return 1\n", encoding="utf-8")
    indexer.index_repository(str(root))
    _reset_worker_cache(root)

    monkeypatch.setattr(
        indexer, "parse_source", lambda path: (_ for _ in ()).throw(AssertionError(path))
    )
    monkeypatch.setattr(
        indexer,
        "extract_compact_reference_facts",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("visitor")),
    )

    result = indexer.index_repository(str(root))
    assert result.reference_facts_by_module["module"]["status"] == "available"


def test_reference_legacy_and_schema_migrations_parse_once_then_hit_warm(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("def current(): return 1\n", encoding="utf-8")
    CacheManager(str(root)).set(source, {"imports": [], "error": None})
    _reset_worker_cache(root)
    original_parse = indexer.parse_source
    calls = []
    monkeypatch.setattr(
        indexer, "parse_source", lambda path: (calls.append(path) or original_parse(path))
    )

    migrated = indexer.index_repository(str(root))
    assert len(calls) == 1
    assert migrated.reference_facts_by_module["module"]["status"] == "available"

    data = _payload(root, source)
    data["reference_facts"]["schema_version"] = 0
    CacheManager(str(root)).set(source, data)
    _reset_worker_cache(root)
    calls.clear()
    remigrated = indexer.index_repository(str(root))
    assert len(calls) == 1
    assert remigrated.reference_facts_by_module["module"]["schema_version"] == 1

    _reset_worker_cache(root)
    calls.clear()
    indexer.index_repository(str(root))
    assert calls == []


def test_source_change_invalidates_reference_facts_and_reassembles_reexports(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    provider = root / "provider.py"
    facade = root / "facade.py"
    consumer = root / "consumer.py"
    provider.write_text("def old(): pass\ndef new(): pass\n", encoding="utf-8")
    facade.write_text("from provider import old as public\n", encoding="utf-8")
    consumer.write_text("from facade import public\npublic()\n", encoding="utf-8")
    first = indexer.index_repository(str(root))
    first_ref = assemble_reference_index_or_fallback(
        first.modules, str(root), first.reference_facts_by_module
    )
    assert first_ref.reexports["facade.public"] == "provider.old"

    facade.write_text("from provider import new as public\n", encoding="utf-8")
    _reset_worker_cache(root)
    changed = indexer.index_repository(str(root))
    changed_ref = assemble_reference_index_or_fallback(
        changed.modules, str(root), changed.reference_facts_by_module
    )
    assert changed_ref.reexports["facade.public"] == "provider.new"
    assert changed_ref.build_symbol_references(["new"], "provider")["new"][
        "called_by"
    ] == ["consumer"]


def test_reference_failure_is_run_scoped_and_not_persisted(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "module.py"
    source.write_text("def value(): return 1\n", encoding="utf-8")
    monkeypatch.setattr(
        indexer,
        "extract_compact_reference_facts",
        lambda *args, **kwargs: {
            "status": "failure",
            "facts": None,
            "error_type": "RuntimeError",
            "message": "visitor failed",
        },
    )

    result = indexer.index_repository(str(root))
    assert result.reference_facts_by_module["module"]["status"] == "failure"
    assert "reference_facts" not in _payload(root, source)


def test_serial_and_process_pool_reference_side_tables_match(
    tmp_path, isolated_dirs, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text("def run(): pass\n", encoding="utf-8")
    (root / "b.py").write_text("from a import run\nrun()\n", encoding="utf-8")
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    serial = indexer.index_repository(str(root)).reference_facts_by_module
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL")
    _reset_worker_cache(root)
    pooled = indexer.index_repository(str(root)).reference_facts_by_module
    assert pooled == serial


def test_compact_reexport_oracle_and_artifact_output_parity(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    package = root / "pkg"
    package.mkdir()
    (package / "provider.py").write_text("def run(): pass\ndef hidden(): pass\n")
    (package / "__init__.py").write_text(
        "from .provider import run, hidden\n__all__ = ['run']\n"
    )
    (root / "facade.py").write_text("from pkg import *\n__all__ = ['run']\n")
    (root / "bridge.py").write_text(
        "from facade import run as execute\n__all__ = ['execute']\n"
    )
    (root / "consumer.py").write_text("from bridge import execute\nexecute()\n")
    (root / "cycle_a.py").write_text(
        "from cycle_b import value as other\nvalue = other\n__all__ = ['value']\n"
    )
    (root / "cycle_b.py").write_text(
        "from cycle_a import value as other\nvalue = other\n__all__ = ['value']\n"
    )
    (root / "shadow.py").write_text(
        "from pkg import run\ndef run(): pass\n__all__ = ['run']\n"
    )
    indexed = indexer.index_repository(str(root))

    assert _assemble_reexport_map(indexed.reference_facts_by_module) == (
        _build_reexport_map(indexed.modules)
    )
    passed = assemble_reference_index_or_fallback(
        indexed.modules, str(root), indexed.reference_facts_by_module
    )
    passed_report = generate_artifact_usage_report(
        indexed.modules,
        str(root),
        symbol_facts_by_module=indexed.symbol_facts_by_module,
        reference_index=passed,
    )
    fallback_report = generate_artifact_usage_report(
        indexed.modules,
        str(root),
        symbol_facts_by_module=indexed.symbol_facts_by_module,
    )
    for report in (passed_report, fallback_report):
        report.pop("runtime", None)
    assert passed_report == fallback_report


def test_missing_or_failed_compact_coverage_uses_ast_fallback(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "module.py").write_text("def run(): pass\n", encoding="utf-8")
    indexed = indexer.index_repository(str(root))
    calls = []
    original = RepositoryReferenceIndex.build

    def counted_build(modules, root_path):
        calls.append(root_path)
        return original(modules, root_path)

    monkeypatch.setattr(RepositoryReferenceIndex, "build", counted_build)
    assemble_reference_index_or_fallback(indexed.modules, str(root), {})
    failed = dict(indexed.reference_facts_by_module)
    failed["module"] = {"status": "failure", "facts": None}
    assemble_reference_index_or_fallback(indexed.modules, str(root), failed)
    assert calls == [str(root), str(root)]


def test_full_analysis_assembles_once_and_passes_same_index_to_artifacts(
    tmp_path, isolated_dirs, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "provider.py").write_text("def run(): pass\n", encoding="utf-8")
    (root / "consumer.py").write_text(
        "from provider import run\nrun()\n", encoding="utf-8"
    )
    assembled = []
    received = []
    original_assemble = facade.assemble_reference_index_or_fallback
    from contextor.core.reporting_layer import artifact_usage_report

    original_collect = artifact_usage_report.collect_module_artifacts

    def counted_assemble(modules, root_path, facts):
        value = original_assemble(modules, root_path, facts)
        assembled.append(value)
        return value

    def observed_collect(*args, **kwargs):
        received.append(kwargs.get("reference_index"))
        return original_collect(*args, **kwargs)

    monkeypatch.setattr(facade, "assemble_reference_index_or_fallback", counted_assemble)
    monkeypatch.setattr(artifact_usage_report, "collect_module_artifacts", observed_collect)

    facade.ContextorFacade.analyze_project(str(root))

    assert len(assembled) == 1
    assert received == [assembled[0]]
