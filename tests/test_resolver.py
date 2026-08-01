"""
Import resolution: exact matches, fallbacks and package-root detection.
"""

from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module
from contextor.core.graph.resolver import (
    build_trie,
    detect_package_root,
    resolve_internal,
)

MODULES = ["core.alpha", "core.beta", "ui.app"]


def _trie():
    return build_trie(MODULES)


def _module(module_id, imports):
    return Module(module_id, f"{module_id}.py", f"/abs/{module_id}.py", imports)


def test_exact_module_resolves_as_module():
    result = resolve_internal(
        ImportRef("core.alpha", 0, [], True),
        _trie(),
        current_module_id="ui.app",
        package_root=None,
    )

    assert result.kind == "MODULE"
    assert result.target_module == "core.alpha"


def test_symbol_import_falls_back_to_defining_module():
    result = resolve_internal(
        ImportRef("core", 0, ["alpha"], True),
        _trie(),
        current_module_id="ui.app",
        package_root=None,
    )

    assert result.kind == "FALLBACK"
    assert result.target_module == "core.alpha"


def test_unrelated_import_is_unknown():
    result = resolve_internal(
        ImportRef("numpy", 0, ["array"], True),
        _trie(),
        current_module_id="ui.app",
        package_root=None,
    )

    assert result.kind == "UNKNOWN"
    assert result.target_module is None


def test_relative_import_resolves_against_current_module():
    result = resolve_internal(
        ImportRef("beta", 1, [], True),
        _trie(),
        current_module_id="core.alpha",
        package_root=None,
    )

    assert result.target_module == "core.beta"


def test_package_root_prefix_is_stripped_when_supplied():
    result = resolve_internal(
        ImportRef("myapp.core.alpha", 0, [], True),
        _trie(),
        current_module_id="ui.app",
        package_root="myapp",
    )

    assert result.kind == "MODULE"
    assert result.target_module == "core.alpha"


def test_package_root_is_detected_from_imports_not_hardcoded():
    """
    The prefix appears only in import statements, never in module ids.
    """

    modules = {
        "ui.app": _module("ui.app", [ImportRef("myapp.core.alpha", 0, [], True)]),
        "core.beta": _module("core.beta", [ImportRef("myapp.core.alpha", 0, [], True)]),
    }

    assert detect_package_root(modules, _trie()) == "myapp"


def test_package_root_detection_yields_none_without_evidence():
    modules = {
        "ui.app": _module("ui.app", [ImportRef("core.alpha", 0, [], True)]),
    }

    assert detect_package_root(modules, _trie()) is None
