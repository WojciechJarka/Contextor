"""D2B-2 indexer classification, cache and execution-mode regressions."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.graph.graph import build_graph
from contextor.core.graph.resolver import build_trie, detect_package_root
from contextor.core.reference.shared import materialize_reexport_facts_by_module
from contextor.core.symbol_engine import indexer
from tests.cycle_semantics_lab import write_synthetic_repository


D2B_NAME_SAFE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "value = 1\n"
    ),
    "pkg/b.py": "from pkg.a import value\n",
}

D2B2_NEGATIVE_CASES = [
    ("N01-no-marker", "if TYPE_CHECKING:\n    import pkg.b\n", {}, {"pkg.b"}),
    (
        "N02-assigned-before",
        "TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N03-assigned-after",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    import pkg.b\nTYPE_CHECKING = True\n",
        {}, {"pkg.b"},
    ),
    (
        "N04-aliased-marker",
        "from typing import TYPE_CHECKING as TC\nif TYPE_CHECKING:\n"
        "    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N05-aliased-typing",
        "import typing as t\nif typing.TYPE_CHECKING:\n"
        "    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N06-negated",
        "from typing import TYPE_CHECKING\nif not TYPE_CHECKING:\n"
        "    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N07-is-false",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING is False:\n"
        "    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N08-equals-false",
        "import typing\nif typing.TYPE_CHECKING == False:\n"
        "    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N09-nested-if-import",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    if True:\n        import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N10-function-import",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    def load():\n        import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N11-class-import",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    class Loader:\n        import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N12-try-import",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    try:\n        import pkg.b\n"
        "    except ImportError:\n        pass\n",
        {}, {"pkg.b"},
    ),
    (
        "N13-else-import",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    pass\nelse:\n    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N14-from-import",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    from pkg import b\n",
        {}, {"pkg.__init__"},
    ),
    (
        "N15-multiple-aliases",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    import pkg.b, pkg.c\n",
        {"pkg/c.py": "pass\n"}, {"pkg.b", "pkg.c"},
    ),
    (
        "N16-as-alias",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    import pkg.b as child\n",
        {}, {"pkg.b"},
    ),
    (
        "N17-local-typing-module",
        D2B_NAME_SAFE["pkg/a.py"],
        {"typing.py": "pass\n"}, {"pkg.b"},
    ),
    (
        "N18-local-typing-package",
        D2B_NAME_SAFE["pkg/a.py"],
        {"typing/__init__.py": "pass\n"}, {"pkg.b"},
    ),
    (
        "N19-marker-after-effect",
        "import pkg.b\nfrom typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    pass\n",
        {}, {"pkg.b"},
    ),
    (
        "N20-duplicate-marker",
        "from typing import TYPE_CHECKING\nfrom typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N21-conditional-marker",
        "if True:\n    from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N22-marker-shadow-import",
        "from typing import TYPE_CHECKING\nfrom other import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N23-nested-guard",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    if TYPE_CHECKING:\n        import pkg.b\n",
        {}, {"pkg.b"},
    ),
    (
        "N24-undotted-import",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
        "    import pkg\n",
        {}, {"pkg.__init__"},
    ),
]


@pytest.fixture(autouse=True)
def _inline_workers(monkeypatch):
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")


def _index_graph(root):
    index = indexer.index_repository(str(root))
    reexport_facts = materialize_reexport_facts_by_module(
        index.modules,
        index.reference_facts_by_module,
    )
    trie = build_trie(index.modules.keys())
    package_root = detect_package_root(index.modules, trie)
    graph = build_graph(
        index.modules,
        trie=trie,
        package_root=package_root,
        reexport_facts_by_module=reexport_facts,
    )
    return index, graph


def _import_signature(index):
    return tuple(
        (
            module_id,
            tuple(
                (
                    item.module,
                    item.level,
                    tuple(item.names),
                    item.is_from_import,
                    item.is_local,
                    item.type_only,
                )
                for item in module.imports
            ),
        )
        for module_id, module in sorted(index.modules.items())
    )


def _scc_signature(index, graph):
    trees = {
        module_id: ast.parse(
            Path(module.absolute_path).read_text(encoding="utf-8")
        )
        for module_id, module in index.modules.items()
    }
    report = analyze_cycle_scenarios(graph.hard_edges, trees)
    return tuple(tuple(component.members) for component in report.components)


def _graph_signature(index, graph):
    return (
        tuple(
            (module_id, tuple(sorted(targets)))
            for module_id, targets in sorted(graph.hard_edges.items())
        ),
        tuple(
            (module_id, tuple(sorted(targets)))
            for module_id, targets in sorted(graph.soft_edges.items())
        ),
        _scc_signature(index, graph),
    )


def _cache_data(root: Path, source: Path) -> dict:
    manager = CacheManager(str(root))
    return json.loads(
        manager._get_cache_file_path(source).read_text(encoding="utf-8")
    )["data"]


def test_cold_and_warm_worker_cache_match_type_only_graph(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    cold_index, cold_graph = _index_graph(root)
    cold_imports = _import_signature(cold_index)
    cold_graph_signature = _graph_signature(cold_index, cold_graph)
    source = root / "pkg" / "a.py"
    cached = _cache_data(root, source)
    assert cached["import_classification_semantics_version"] == 1
    assert next(
        item for item in cached["imports"] if item["module"] == "pkg.b"
    )["type_only"] is True

    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("current warm cache must not parse source")

    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
    warm_index, warm_graph = _index_graph(root)

    assert _import_signature(warm_index) == cold_imports
    assert _graph_signature(warm_index, warm_graph) == cold_graph_signature


@pytest.mark.parametrize("stored_version", [None, 0], ids=["absent", "old"])
def test_stale_import_classification_cache_reparses_same_snapshot(
    tmp_path, isolated_dirs, stored_version, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    indexer.index_repository(str(root))
    source = root / "pkg" / "a.py"
    cached = _cache_data(root, source)
    for item in cached["imports"]:
        if item["module"] == "pkg.b":
            item["type_only"] = False
    if stored_version is None:
        cached.pop("import_classification_semantics_version", None)
    else:
        cached["import_classification_semantics_version"] = stored_version
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    real_read = indexer.read_source_snapshot
    real_parse = indexer.parse_source_snapshot
    read_calls = []
    parse_calls = []

    def tracked_read(path):
        read_calls.append(Path(path).resolve())
        return real_read(path)

    def tracked_parse(snapshot, path):
        parse_calls.append(Path(path).resolve())
        return real_parse(snapshot, path)

    monkeypatch.setattr(indexer, "read_source_snapshot", tracked_read)
    monkeypatch.setattr(indexer, "parse_source_snapshot", tracked_parse)
    result = indexer.index_repository(str(root))

    assert len(read_calls) == 3
    assert len(set(read_calls)) == 3
    assert parse_calls == [(root / "pkg" / "a.py").resolve()]
    assert any(
        item.module == "pkg.b" and item.type_only
        for item in result.modules["pkg.a"].imports
    )
    rewritten = _cache_data(root, source)
    assert rewritten["import_classification_semantics_version"] == 1
    assert next(
        item for item in rewritten["imports"] if item["module"] == "pkg.b"
    )["type_only"] is True


def test_source_changes_and_typing_shadow_add_remove_reclassify(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    original_bytes = (root / "pkg" / "a.py").read_bytes()
    initial, initial_graph = _index_graph(root)
    source_fingerprint = initial.source_fingerprints_by_module["pkg.a"]
    initial_module = initial.modules["pkg.a"]
    initial_imports = tuple(initial_module.imports)
    assert next(
        item for item in initial.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is True
    assert initial_graph.soft_edges["pkg.a"] == {"pkg.b"}

    source = root / "pkg" / "a.py"
    source.write_text("value = 1\n", encoding="utf-8")
    changed, changed_graph = _index_graph(root)
    assert all(not item.type_only for item in changed.modules["pkg.a"].imports)
    assert changed_graph.soft_edges["pkg.a"] == set()
    assert "pkg.b" not in changed_graph.hard_edges["pkg.a"]

    source.write_bytes(original_bytes)
    restored, restored_graph = _index_graph(root)
    assert restored.source_fingerprints_by_module["pkg.a"] == source_fingerprint
    assert next(
        item for item in restored.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is True
    assert restored_graph.soft_edges["pkg.a"] == {"pkg.b"}

    simple_shadow = root / "typing.py"
    simple_shadow.write_text("pass\n", encoding="utf-8")
    shadowed, shadowed_graph = _index_graph(root)
    assert "typing" in shadowed.modules
    assert shadowed.source_fingerprints_by_module["pkg.a"] == source_fingerprint
    assert all(not item.type_only for item in shadowed.modules["pkg.a"].imports)
    shadowed_module = shadowed.modules["pkg.a"]
    assert (
        shadowed_module.module_id,
        shadowed_module.path,
        shadowed_module.absolute_path,
    ) == (
        initial_module.module_id,
        initial_module.path,
        initial_module.absolute_path,
    )
    assert [replace(item, type_only=False) for item in initial_imports] == (
        shadowed_module.imports
    )
    assert "pkg.b" in shadowed_graph.hard_edges["pkg.a"]
    assert next(
        item for item in _cache_data(root, source)["imports"]
        if item["module"] == "pkg.b"
    )["type_only"] is True

    simple_shadow.unlink()
    unshadowed, unshadowed_graph = _index_graph(root)
    assert "pkg.b" in unshadowed.modules
    assert next(
        item for item in unshadowed.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is True
    assert unshadowed_graph.soft_edges["pkg.a"] == {"pkg.b"}

    package_shadow = root / "typing" / "__init__.py"
    package_shadow.parent.mkdir(parents=True, exist_ok=True)
    package_shadow.write_text("pass\n", encoding="utf-8")
    package_shadowed, package_graph = _index_graph(root)
    assert "typing.__init__" in package_shadowed.modules
    assert all(
        not item.type_only
        for item in package_shadowed.modules["pkg.a"].imports
    )
    assert "pkg.b" in package_graph.hard_edges["pkg.a"]

    package_shadow.unlink()
    package_shadow.parent.rmdir()
    package_unshadowed, package_unshadowed_graph = _index_graph(root)
    assert next(
        item for item in package_unshadowed.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is True
    assert package_unshadowed_graph.soft_edges["pkg.a"] == {"pkg.b"}


def test_inline_and_process_pool_classification_parity(
    tmp_path, isolated_dirs, monkeypatch,
):
    inline_root = write_synthetic_repository(
        tmp_path / "inline", D2B_NAME_SAFE,
    )
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline_index, inline_graph = _index_graph(inline_root)

    pool_root = write_synthetic_repository(
        tmp_path / "pool", D2B_NAME_SAFE,
    )
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pool_index, pool_graph = _index_graph(pool_root)

    assert _import_signature(pool_index) == _import_signature(inline_index)
    assert _graph_signature(pool_index, pool_graph) == (
        _graph_signature(inline_index, inline_graph)
    )
    assert pool_index.original_worker_capture_status == "NOT_REQUESTED"


def test_inline_and_process_pool_typing_shadow_veto_parity(
    tmp_path, isolated_dirs, monkeypatch,
):
    fixture = {
        **D2B_NAME_SAFE,
        "typing.py": "pass\n",
    }
    inline_root = write_synthetic_repository(
        tmp_path / "inline", fixture,
    )
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline_index, inline_graph = _index_graph(inline_root)

    pool_root = write_synthetic_repository(
        tmp_path / "pool", fixture,
    )
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pool_index, pool_graph = _index_graph(pool_root)

    assert _import_signature(pool_index) == _import_signature(inline_index)
    assert _graph_signature(pool_index, pool_graph) == (
        _graph_signature(inline_index, inline_graph)
    )
    assert all(
        not item.type_only for item in pool_index.modules["pkg.a"].imports
    )
    assert "pkg.b" in pool_graph.hard_edges["pkg.a"]


@pytest.mark.parametrize(
    "case,source,extra,expected_hard_targets",
    D2B2_NEGATIVE_CASES,
    ids=[item[0] for item in D2B2_NEGATIVE_CASES],
)
def test_unsupported_imports_remain_non_type_only_and_hard(
    tmp_path, isolated_dirs, case, source, extra, expected_hard_targets,
):
    files = {
        "pkg/__init__.py": "pass\n",
        "pkg/a.py": source,
        "pkg/b.py": "from pkg.a import value\n",
        **extra,
    }
    root = write_synthetic_repository(tmp_path / case, files)
    index, graph = _index_graph(root)

    imports = index.modules["pkg.a"].imports
    assert imports
    assert all(item.type_only is False for item in imports)
    assert expected_hard_targets.issubset(graph.hard_edges["pkg.a"])
    if case == "N10-function-import":
        assert next(item for item in imports if item.module == "pkg.b").is_local
    if case == "N14-from-import":
        assert any(item.module == "pkg" and item.is_from_import for item in imports)
    if case == "N15-multiple-aliases":
        assert [item.module for item in imports if item.module in {"pkg.b", "pkg.c"}] == [
            "pkg.b", "pkg.c",
        ]

