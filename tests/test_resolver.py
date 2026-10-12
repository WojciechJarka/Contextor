"""
Import resolution: exact matches, fallbacks and package-root detection.
"""

from pathlib import Path

from contextor.core.domain.imports import ImportRef
from contextor.core.domain.module import Module
from contextor.core.graph.graph import build_graph, resolve_module_edges
from contextor.core.graph.resolver import (
    build_trie,
    detect_package_root,
    resolve_internal,
)
from contextor.core.reference.shared import materialize_reexport_facts_by_module
from contextor.core.symbol_engine.indexer import read_imports

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


def _package_modules(tmp_path: Path, importer_source: str):
    package = tmp_path / "pkg"
    json_package = package / "json"
    json_package.mkdir(parents=True)
    importer = package / "__init__.py"
    importer.write_text(importer_source, encoding="utf-8")
    (json_package / "__init__.py").write_text("def jsonify(): pass\n", encoding="utf-8")
    (package / "app.py").write_text("class Flask: pass\n", encoding="utf-8")
    imports, error = read_imports(importer)
    assert error is None
    assert imports is not None
    modules = {
        "pkg.__init__": Module("pkg.__init__", "pkg/__init__.py", str(importer), imports),
        "pkg.json.__init__": Module(
            "pkg.json.__init__", "pkg/json/__init__.py", str(json_package / "__init__.py"), []
        ),
        "pkg.app": Module("pkg.app", "pkg/app.py", str(package / "app.py"), []),
    }
    return modules, imports


def test_relative_package_init_import_produces_hard_edge(tmp_path):
    modules, imports = _package_modules(
        tmp_path,
        "from .json import jsonify as jsonify\nfrom .app import Flask as Flask\n",
    )
    trie = build_trie(modules)
    json_result = resolve_internal(imports[0], trie, "pkg.__init__", None)
    app_result = resolve_internal(imports[1], trie, "pkg.__init__", None)
    assert (json_result.kind, json_result.target_module) == ("MODULE", "pkg.json.__init__")
    assert (app_result.kind, app_result.target_module) == ("MODULE", "pkg.app")
    hard, soft = resolve_module_edges("pkg.__init__", modules["pkg.__init__"], trie, None)
    assert hard == {"pkg.json.__init__", "pkg.app"}
    assert soft == set()
    graph = build_graph(modules)
    assert graph.hard_edges["pkg.__init__"] == hard
    assert graph.soft_edges["pkg.__init__"] == soft
    assert "pkg.json" not in modules
    assert resolve_internal(ImportRef("missing", 1, [], True), trie, "pkg.__init__", None).kind == "UNKNOWN"


def test_relative_from_import_multiple_package_targets(tmp_path):
    modules, imports = _package_modules(tmp_path, "from . import json, app, nonexistent\n")
    trie = build_trie(modules)
    assert len(imports) == 1
    assert imports[0].module is None
    hard, soft = resolve_module_edges("pkg.__init__", modules["pkg.__init__"], trie, None)
    assert hard == {"pkg.json.__init__", "pkg.app"}
    assert soft == set()
    assert "pkg.__init__" not in hard
    assert "pkg.nonexistent" not in hard
    graph = build_graph(modules)
    assert graph.hard_edges["pkg.__init__"] == hard
    assert graph.soft_edges["pkg.__init__"] == soft


def test_initializer_self_import_binding_keeps_child_package_hard_edge(tmp_path):
    modules, _ = _package_modules(tmp_path, "from . import json as json\n")
    facts = materialize_reexport_facts_by_module(modules)
    assert facts["pkg.__init__"]["bindings"]["json"] == "pkg.json"

    trie = build_trie(modules)
    hard, soft = resolve_module_edges(
        "pkg.__init__", modules["pkg.__init__"], trie, None, facts
    )
    graph = build_graph(modules, reexport_facts_by_module=facts)
    assert hard == {"pkg.json.__init__"}
    assert soft == set()
    assert graph.hard_edges["pkg.__init__"] == hard
    assert graph.soft_edges["pkg.__init__"] == soft
    assert "pkg.json" not in modules


def test_initializer_real_assignment_shadows_same_named_child(tmp_path):
    modules, _ = _named_package_modules(
        tmp_path, "from pkg import runtime\n", "runtime = object()\n"
    )
    facts = materialize_reexport_facts_by_module(modules)
    assert facts["pkg.__init__"]["bindings"]["runtime"] == "pkg.runtime"

    hard, soft = resolve_module_edges(
        "consumer", modules["consumer"], build_trie(modules), None, facts
    )
    assert hard == {"pkg.__init__"}
    assert soft == set()


def test_initializer_real_multi_name_bindings_keep_indexed_child_edges(tmp_path):
    modules, _ = _package_modules(tmp_path, "from . import json, app, nonexistent\n")
    facts = materialize_reexport_facts_by_module(modules)
    assert facts["pkg.__init__"]["bindings"] == {
        "json": "pkg.json",
        "app": "pkg.app",
        "nonexistent": "pkg.nonexistent",
    }

    hard, soft = resolve_module_edges(
        "pkg.__init__", modules["pkg.__init__"], build_trie(modules), None, facts
    )
    graph = build_graph(modules, reexport_facts_by_module=facts)
    assert hard == {"pkg.json.__init__", "pkg.app"}
    assert soft == set()
    assert "pkg.__init__" not in hard
    assert "pkg.nonexistent" not in hard | soft
    assert graph.hard_edges["pkg.__init__"] == hard
    assert graph.soft_edges["pkg.__init__"] == soft


def test_relative_package_import_preserves_nonpackage_behavior(tmp_path):
    modules, imports = _package_modules(tmp_path, "from .app import Flask\n")
    trie = build_trie(modules)
    app_result = resolve_internal(imports[0], trie, "pkg.__init__", None)
    assert (app_result.kind, app_result.target_module) == ("MODULE", "pkg.app")
    assert resolve_internal(ImportRef("missing", 1, [], True), trie, "pkg.__init__", None).kind == "UNKNOWN"
    fallback = resolve_internal(
        ImportRef("other", 0, ["app"], True),
        build_trie(["other.app"]),
        "pkg.__init__",
        None,
    )
    assert (fallback.kind, fallback.target_module) == ("FALLBACK", "other.app")
    soft_module = Module(
        "pkg.__init__",
        "pkg/__init__.py",
        modules["pkg.__init__"].absolute_path,
        [ImportRef("json", 1, ["jsonify"], True, type_only=True)],
    )
    hard, soft = resolve_module_edges("pkg.__init__", soft_module, trie, None)
    assert hard == set()
    assert soft == {"pkg.json.__init__"}


def _named_package_modules(
    tmp_path: Path,
    importer_source: str,
    init_source: str = "",
    child_name: str = "runtime",
):
    package = tmp_path / "pkg"
    package.mkdir()
    initializer = package / "__init__.py"
    initializer.write_text(init_source, encoding="utf-8")
    child = package / f"{child_name}.py"
    child.write_text("VALUE = 1\n", encoding="utf-8")
    importer = tmp_path / "consumer.py"
    importer.write_text(importer_source, encoding="utf-8")
    imports, error = read_imports(importer)
    assert error is None
    assert imports is not None
    modules = {
        "pkg.__init__": Module("pkg.__init__", "pkg/__init__.py", str(initializer), []),
        f"pkg.{child_name}": Module(
            f"pkg.{child_name}", f"pkg/{child_name}.py", str(child), []
        ),
        "consumer": Module("consumer", "consumer.py", str(importer), imports),
    }
    return modules, imports


def test_named_child_keeps_initializer_and_soft_child_edges(tmp_path):
    modules, imports = _named_package_modules(
        tmp_path, "from pkg import runtime as mcp_runtime\n"
    )
    assert imports[0].names == ["runtime"]
    trie = build_trie(modules)
    hard, soft = resolve_module_edges("consumer", modules["consumer"], trie, None)
    assert hard == {"pkg.__init__"}
    assert soft == {"pkg.runtime"}
    assert hard | soft <= modules.keys()


def test_initializer_binding_shadows_same_named_child(tmp_path):
    modules, _ = _named_package_modules(
        tmp_path, "from pkg import runtime\n", "runtime = object()\n"
    )
    facts = {"pkg.__init__": {"bindings": {"runtime": "pkg.__init__.runtime"}}}
    hard, soft = resolve_module_edges(
        "consumer", modules["consumer"], build_trie(modules), None, facts
    )
    assert hard == {"pkg.__init__"}
    assert soft == set()


def test_mixed_named_import_preserves_only_unbound_indexed_child(tmp_path):
    modules, _ = _named_package_modules(
        tmp_path,
        "from pkg import exported_symbol, child, nonexistent\n",
        "exported_symbol = 1\n",
        child_name="child",
    )
    facts = {"pkg.__init__": {"bindings": {"exported_symbol": "pkg.__init__.exported_symbol"}}}
    hard, soft = resolve_module_edges(
        "consumer", modules["consumer"], build_trie(modules), None, facts
    )
    assert hard == {"pkg.__init__"}
    assert soft == {"pkg.child"}


def test_relative_named_import_shadows_indexed_child_when_bound(tmp_path):
    modules, imports = _named_package_modules(tmp_path, "from . import runtime\n")
    modules["pkg.consumer"] = Module(
        "pkg.consumer", "pkg/consumer.py", modules["consumer"].absolute_path, imports
    )
    del modules["consumer"]
    facts = {"pkg.__init__": {"bindings": {"runtime": "pkg.__init__.runtime"}}}
    hard, soft = resolve_module_edges(
        "pkg.consumer", modules["pkg.consumer"], build_trie(modules), None, facts
    )
    assert hard == {"pkg.__init__"}
    assert soft == set()


def test_type_only_named_package_dependencies_are_soft(tmp_path):
    modules, imports = _named_package_modules(tmp_path, "from pkg import runtime\n")
    original = imports[0]
    modules["consumer"] = Module(
        "consumer",
        "consumer.py",
        modules["consumer"].absolute_path,
        [ImportRef(original.module, original.level, original.names, True, type_only=True)],
    )
    hard, soft = resolve_module_edges(
        "consumer", modules["consumer"], build_trie(modules), None
    )
    assert hard == set()
    assert soft == {"pkg.__init__", "pkg.runtime"}


def test_full_graph_matches_direct_resolver_for_named_package(tmp_path):
    modules, _ = _named_package_modules(tmp_path, "from pkg import runtime\n")
    facts = {"pkg.__init__": {"bindings": {}}}
    direct_hard, direct_soft = resolve_module_edges(
        "consumer", modules["consumer"], build_trie(modules), None, facts
    )
    graph = build_graph(modules, reexport_facts_by_module=facts)
    assert graph.hard_edges["consumer"] == direct_hard
    assert graph.soft_edges["consumer"] == direct_soft
