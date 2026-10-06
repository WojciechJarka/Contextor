"""Focused cross-module provenance tests for explicit Python re-exports."""

from contextor.core.reference.engine import _build_reexport_map, build_symbol_references
from contextor.core.reporting_layer.artifact_usage_report import (
    build_artifact_index,
    collect_module_artifacts,
)
from contextor.core.symbol_engine.indexer import index_repository
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.reference.shared import (
    _canonicalize_package_reference_target,
)


def _full_canonical_state(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    errors, _ = ContextorFacade().analyze_project(str(tmp_path))
    assert not errors, errors

    hydrated = hydrate_repository_engine(tmp_path)
    assert hydrated is not None
    return hydrated.engine.state


def _write_star_visibility_fixture(tmp_path, explicit_all):
    (tmp_path / "a.py").write_text(
        "def imported():\n"
        "    pass\n",
        encoding="utf-8",
    )
    source = (
        "from a import imported\n"
        "PUBLIC = 1\n"
        "_PRIVATE = 2\n"
    )
    if explicit_all is not None:
        source += f"__all__ = {explicit_all!r}\n"
    (tmp_path / "b.py").write_text(source, encoding="utf-8")
    (tmp_path / "c.py").write_text(
        "from b import *\n",
        encoding="utf-8",
    )


def _star_channels(state, target, consumer="c"):
    return state.artifact_consumption.get(target, {}).get(
        "channels",
        {},
    ).get(consumer, [])


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



def test_repeated_all_uses_last_assignment_consistently(
    tmp_path,
):
    (tmp_path / "provider.py").write_text(
        "def first():\n"
        "    return 1\n"
        "\n"
        "def second():\n"
        "    return 2\n",
        encoding="utf-8",
    )

    (tmp_path / "facade.py").write_text(
        "from provider import first, second\n"
        "__all__ = ['first']\n"
        "__all__ = ['second']\n",
        encoding="utf-8",
    )

    modules = index_repository(
        str(tmp_path)
    ).modules

    legacy_mapping = _build_reexport_map(
        modules
    )

    assert (
        "facade.first"
        not in legacy_mapping
    )
    assert (
        legacy_mapping["facade.second"]
        == "provider.second"
    )


def test_repeated_all_dynamic_then_literal_uses_last_assignment(
    tmp_path,
):
    (tmp_path / "provider.py").write_text(
        "def run():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    (tmp_path / "facade.py").write_text(
        "from provider import run\n"
        "__all__ = make_exports()\n"
        "__all__ = ['run']\n",
        encoding="utf-8",
    )

    modules = index_repository(
        str(tmp_path)
    ).modules

    mapping = _build_reexport_map(
        modules
    )

    assert mapping["facade.run"] == (
        "provider.run"
    )


def test_full_star_import_uses_explicit_all_and_tracks_metadata(tmp_path, monkeypatch):
    _write_star_visibility_fixture(
        tmp_path,
        ["imported", "PUBLIC"],
    )

    state = _full_canonical_state(tmp_path, monkeypatch)

    assert _star_channels(state, "a::imported") == ["api_imports"]
    assert _star_channels(state, "b::PUBLIC") == ["api_imports"]
    assert _star_channels(state, "b::_PRIVATE") == []
    assert _star_channels(state, "b::__all__") == ["api_imports"]


def test_full_star_import_empty_all_exports_only_metadata(tmp_path, monkeypatch):
    _write_star_visibility_fixture(tmp_path, [])

    state = _full_canonical_state(tmp_path, monkeypatch)

    assert _star_channels(state, "a::imported") == []
    assert _star_channels(state, "b::PUBLIC") == []
    assert _star_channels(state, "b::_PRIVATE") == []
    assert _star_channels(state, "a::imported", consumer="b") == [
        "api_imports"
    ]
    assert _star_channels(state, "b::__all__") == ["api_imports"]


def test_full_star_import_without_all_exports_public_bindings_only(
    tmp_path,
    monkeypatch,
):
    _write_star_visibility_fixture(tmp_path, None)

    state = _full_canonical_state(tmp_path, monkeypatch)

    assert _star_channels(state, "a::imported") == ["api_imports"]
    assert _star_channels(state, "b::PUBLIC") == ["api_imports"]
    assert _star_channels(state, "b::_PRIVATE") == []
    assert "b::__all__" not in state.artifact_consumption


def test_full_multiple_star_imports_project_each_source_module(
    tmp_path,
    monkeypatch,
):
    (tmp_path / "a.py").write_text(
        "def alpha():\n"
        "    pass\n"
        "_A_PRIVATE = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "b.py").write_text(
        "def beta():\n"
        "    pass\n"
        "_B_PRIVATE = 2\n",
        encoding="utf-8",
    )
    (tmp_path / "c.py").write_text(
        "from a import *\n"
        "from b import *\n",
        encoding="utf-8",
    )

    state = _full_canonical_state(tmp_path, monkeypatch)

    assert _star_channels(state, "a::alpha") == ["api_imports"]
    assert _star_channels(state, "b::beta") == ["api_imports"]
    assert _star_channels(state, "a::_A_PRIVATE") == []
    assert _star_channels(state, "b::_B_PRIVATE") == []


def test_package_reference_canonicalizer_prefers_longest_module_prefix():
    modules = {
        "pkg.__init__",
        "pkg.provider",
        "pkg.sub.__init__",
    }

    assert (
        _canonicalize_package_reference_target(
            "pkg.PUBLIC",
            modules,
        )
        == "pkg.__init__.PUBLIC"
    )
    assert (
        _canonicalize_package_reference_target(
            "pkg.__all__",
            modules,
        )
        == "pkg.__init__.__all__"
    )
    assert (
        _canonicalize_package_reference_target(
            "pkg.provider.run",
            modules,
        )
        == "pkg.provider.run"
    )
    assert (
        _canonicalize_package_reference_target(
            "pkg.sub.VALUE",
            modules,
        )
        == "pkg.sub.__init__.VALUE"
    )
    assert (
        _canonicalize_package_reference_target(
            "pkg.sub.__all__",
            modules,
        )
        == "pkg.sub.__init__.__all__"
    )


def test_named_package_local_import_uses_init_canonical_identity(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "def public():\n"
        "    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.py").write_text(
        "from pkg import public\n"
        "\n"
        "def use():\n"
        "    public()\n",
        encoding="utf-8",
    )

    state = _full_canonical_state(tmp_path, monkeypatch)

    entry = state.artifact_consumption["pkg.__init__::public"]
    assert entry["consumers"] == ["consumer"]
    assert set(entry["channels"]["consumer"]) == {
        "api_imports",
        "direct_calls",
    }


def test_package_star_explicit_all_uses_init_canonical_identity(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "PUBLIC = 1\n"
        "_PRIVATE = 2\n"
        "__all__ = ['PUBLIC']\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.py").write_text(
        "from pkg import *\n",
        encoding="utf-8",
    )

    state = _full_canonical_state(tmp_path, monkeypatch)

    assert _star_channels(
        state,
        "pkg.__init__::PUBLIC",
        consumer="consumer",
    ) == ["api_imports"]
    assert _star_channels(
        state,
        "pkg.__init__::_PRIVATE",
        consumer="consumer",
    ) == []
    assert _star_channels(
        state,
        "pkg.__init__::__all__",
        consumer="consumer",
    ) == ["api_imports"]


def test_package_star_empty_all_keeps_only_metadata_dependency(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "PUBLIC = 1\n"
        "_PRIVATE = 2\n"
        "__all__ = []\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.py").write_text(
        "from pkg import *\n",
        encoding="utf-8",
    )

    state = _full_canonical_state(tmp_path, monkeypatch)

    assert _star_channels(
        state,
        "pkg.__init__::PUBLIC",
        consumer="consumer",
    ) == []
    assert _star_channels(
        state,
        "pkg.__init__::_PRIVATE",
        consumer="consumer",
    ) == []
    assert _star_channels(
        state,
        "pkg.__init__::__all__",
        consumer="consumer",
    ) == ["api_imports"]


def test_package_star_without_all_exports_public_only(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "PUBLIC = 1\n"
        "_PRIVATE = 2\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.py").write_text(
        "from pkg import *\n",
        encoding="utf-8",
    )

    state = _full_canonical_state(tmp_path, monkeypatch)

    assert _star_channels(
        state,
        "pkg.__init__::PUBLIC",
        consumer="consumer",
    ) == ["api_imports"]
    assert _star_channels(
        state,
        "pkg.__init__::_PRIVATE",
        consumer="consumer",
    ) == []
    assert "pkg.__init__::__all__" not in state.artifact_consumption


def test_package_star_reexport_keeps_provider_api_origin(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "provider.py").write_text(
        "def run():\n"
        "    pass\n",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text(
        "from .provider import run\n"
        "__all__ = ['run']\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.py").write_text(
        "from pkg import *\n",
        encoding="utf-8",
    )

    state = _full_canonical_state(tmp_path, monkeypatch)

    entry = state.artifact_consumption["pkg.provider::run"]
    assert "consumer" in entry["consumers"]
    assert "api_imports" in entry["channels"]["consumer"]
    assert "pkg.__init__::run" not in state.artifact_consumption
