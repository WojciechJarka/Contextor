"""Focused cross-module provenance tests for explicit Python re-exports."""

from contextor.core.reference.engine import _build_reexport_map, build_symbol_references
from contextor.core.reporting_layer.artifact_usage_report import (
    build_artifact_index,
    collect_module_artifacts,
)
from contextor.core.symbol_engine.indexer import index_repository


def test_transitive_aliased_reexport_resolves_to_original_artifact(tmp_path):
    (tmp_path / "provider.py").write_text(
        "def run():\n    return 1\n", encoding="utf-8"
    )
    (tmp_path / "facade.py").write_text(
        "from provider import run as execute\n__all__ = ['execute']\n",
        encoding="utf-8",
    )
    (tmp_path / "bridge.py").write_text(
        "from facade import execute as public_run\n__all__ = ['public_run']\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.py").write_text(
        "from bridge import public_run\nvalue = public_run()\n",
        encoding="utf-8",
    )
    modules = index_repository(str(tmp_path)).modules

    references = build_symbol_references(
        modules,
        ["run"],
        str(tmp_path),
        definer_module="provider",
    )

    assert references["run"]["called_by"] == ["consumer"]
    assert references["run"]["imported_from"] == [
        "bridge",
        "consumer",
        "facade",
    ]


def test_relative_package_init_reexport_resolves_to_provider(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "provider.py").write_text("def run():\n    pass\n", encoding="utf-8")
    (package / "__init__.py").write_text(
        "from .provider import run\n__all__ = ['run']\n", encoding="utf-8"
    )
    (tmp_path / "consumer.py").write_text(
        "from pkg import run\nrun()\n", encoding="utf-8"
    )
    modules = index_repository(str(tmp_path)).modules

    references = build_symbol_references(
        modules, ["run"], str(tmp_path), definer_module="pkg.provider"
    )

    assert references["run"]["called_by"] == ["consumer"]
    assert references["run"]["imported_from"] == ["consumer", "pkg.__init__"]


def test_star_reexport_uses_explicit_all_and_remains_transitive(tmp_path):
    (tmp_path / "provider.py").write_text(
        "def run(): pass\ndef hidden(): pass\n", encoding="utf-8"
    )
    (tmp_path / "facade.py").write_text(
        "from provider import run, hidden\n__all__ = ['run']\n", encoding="utf-8"
    )
    (tmp_path / "bridge.py").write_text(
        "from facade import *\n__all__ = ['run']\n", encoding="utf-8"
    )
    (tmp_path / "consumer.py").write_text(
        "from bridge import run\nrun()\n", encoding="utf-8"
    )
    modules = index_repository(str(tmp_path)).modules

    mapping = _build_reexport_map(modules)
    references = build_symbol_references(
        modules, ["run"], str(tmp_path), definer_module="provider"
    )

    assert mapping["bridge.run"] == "provider.run"
    assert "bridge.hidden" not in mapping
    assert references["run"]["called_by"] == ["consumer"]
    assert references["run"]["imported_from"] == [
        "bridge",
        "consumer",
        "facade",
    ]


def test_direct_star_reexport_includes_public_source_definition(tmp_path):
    (tmp_path / "provider.py").write_text(
        "def run(): pass\ndef hidden(): pass\n", encoding="utf-8"
    )
    (tmp_path / "facade.py").write_text(
        "from provider import *\n__all__ = ['run']\n", encoding="utf-8"
    )
    (tmp_path / "consumer.py").write_text(
        "from facade import run\nrun()\n", encoding="utf-8"
    )
    modules = index_repository(str(tmp_path)).modules

    mapping = _build_reexport_map(modules)
    references = build_symbol_references(
        modules, ["run"], str(tmp_path), definer_module="provider"
    )

    assert mapping["facade.run"] == "provider.run"
    assert "facade.hidden" not in mapping
    assert references["run"]["called_by"] == ["consumer"]


def test_cyclic_reexports_are_not_resolved_arbitrarily(tmp_path):
    (tmp_path / "a.py").write_text(
        "from b import value\n__all__ = ['value']\n", encoding="utf-8"
    )
    (tmp_path / "b.py").write_text(
        "from a import value\n__all__ = ['value']\n", encoding="utf-8"
    )
    modules = index_repository(str(tmp_path)).modules

    mapping = _build_reexport_map(modules)

    assert "a.value" not in mapping
    assert "b.value" not in mapping


def test_local_definition_shadows_earlier_imported_binding(tmp_path):
    (tmp_path / "provider.py").write_text("def run(): pass\n", encoding="utf-8")
    (tmp_path / "facade.py").write_text(
        "from provider import run\n"
        "def run():\n"
        "    return 'local'\n"
        "__all__ = ['run']\n",
        encoding="utf-8",
    )
    modules = index_repository(str(tmp_path)).modules

    mapping = _build_reexport_map(modules)

    assert "facade.run" not in mapping


def test_compact_artifact_pipeline_attributes_reexport_consumers_to_origin(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    (tmp_path / "provider.py").write_text("def run(): pass\n", encoding="utf-8")
    (tmp_path / "facade.py").write_text(
        "from provider import run\n__all__ = ['run']\n", encoding="utf-8"
    )
    (tmp_path / "consumer.py").write_text(
        "from facade import run\nrun()\n", encoding="utf-8"
    )
    modules = index_repository(str(tmp_path)).modules

    module_artifacts, failures = collect_module_artifacts(modules, str(tmp_path))
    artifacts, _usage = build_artifact_index(module_artifacts)

    assert not failures
    assert artifacts["provider::run"]["consumers"] == ["consumer", "facade"]
    assert artifacts["provider::run"]["consumer_count"] == 2
