"""D2B-2 indexer classification, cache and execution-mode regressions."""

from __future__ import annotations

import ast
import json
import py_compile
import subprocess
import sys
from dataclasses import replace
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path

import pytest

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.graph.graph import build_graph
from contextor.core.graph.resolver import build_trie, detect_package_root
from contextor.core.reference.shared import materialize_reexport_facts_by_module
from contextor.core.symbol_engine import indexer
from tests.cycle_semantics_lab import run_synthetic_import, write_synthetic_repository


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

D2B4_INDEXED_LAUNCHER = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.c\n"
        "value = 1\n"
    ),
    "pkg/c.py": "from pkg.a import value\n",
    "pkg/launcher.py": (
        "import typing\n"
        "typing.TYPE_CHECKING = True\n"
        "import pkg.a\n"
    ),
}

D2B4_R1_BASE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.c\n"
        "value = 1\n"
    ),
    "pkg/c.py": "from pkg.a import value\n",
}

D2B4_R1_LAUNCHERS = [
    (
        "ior",
        "import typing\n"
        'typing.__dict__.__ior__({"TYPE_CHECKING": True})\n'
        "import pkg.a\n",
    ),
    (
        "alias-update",
        "import typing\n"
        "mutation = typing.__dict__.update\n"
        'mutation({"TYPE_CHECKING": True})\n'
        "import pkg.a\n",
    ),
]

D2B5_EXCLUDED_CHILD = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.c\n"
        "value = 1\n"
    ),
    "pkg/c.py": "from pkg.a import value\n",
    "pkg/hidden.py": "import typing\ntyping.TYPE_CHECKING = True\n",
    "pkg/launcher.py": "from pkg import hidden\nimport pkg.a\n",
}

D2B6_SOURCE_SHADOW = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.c\n"
        "value = 1\n"
    ),
    "pkg/c.py": "from pkg.a import value\n",
    "pkg/launcher.py": "pass\n",
}

D2B2_R1_GLOBALS_MUTATION = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        'globals()["TYPE_CHECKING"] = True\n'
        "if TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "value = 1\n"
    ),
    "pkg/b.py": "from pkg.a import value\n",
}

D2B2_R1_SETATTR_MUTATION = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "import typing\n"
        'setattr(typing, "TYPE_CHECKING", True)\n'
        "if typing.TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "value = 1\n"
    ),
    "pkg/b.py": "from pkg.a import value\n",
}

D2B2_R2_PARENT_MUTATION = {
    "pkg/__init__.py": (
        "import typing\n"
        "typing.TYPE_CHECKING = True\n"
    ),
    "pkg/a.py": D2B_NAME_SAFE["pkg/a.py"],
    "pkg/b.py": D2B_NAME_SAFE["pkg/b.py"],
}

D2B2_R2_PARENT_SETATTR = {
    **D2B2_R2_PARENT_MUTATION,
    "pkg/__init__.py": (
        "import typing\n"
        'setattr(typing, "TYPE_CHECKING", True)\n'
    ),
}

D2B2_R2_MULTILEVEL_COMMON = {
    "pkg/sub/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.sub.b\n"
        "value = 1\n"
    ),
    "pkg/sub/b.py": "from pkg.sub.a import value\n",
}

D2B2_R2_UNSAFE_INITIALIZER = (
    "import typing\n"
    "typing.TYPE_CHECKING = True\n"
)

D2B2_R2_MULTILEVEL_CASES = [
    ("M01-both-pass", "pass\n", "pass\n", True, True),
    ("M02-unsafe-outer", D2B2_R2_UNSAFE_INITIALIZER, "pass\n", False, True),
    ("M03-unsafe-inner", "pass\n", D2B2_R2_UNSAFE_INITIALIZER, False, True),
    ("M04-passive-literals", "constant = 1\n", '"docstring"\npass\n', True, True),
    ("M05-missing-inner", "pass\n", None, False, False),
    ("M06-missing-outer", None, "pass\n", False, False),
]

D2B2_R2_NEGATIVE_INITIALIZERS = [
    ("N01-import-typing", "import typing\n"),
    ("N02-from-typing", "from typing import TYPE_CHECKING\n"),
    ("N03-attribute-assignment", "typing.TYPE_CHECKING = True\n"),
    ("N04-setattr", 'setattr(typing, "TYPE_CHECKING", True)\n'),
    ("N05-globals", 'globals()["TYPE_CHECKING"] = True\n'),
    ("N06-exec", 'exec("x = 1")\n'),
    ("N07-function", "def f(): pass\n"),
    ("N08-class", "class C: pass\n"),
    ("N09-if", "if True: pass\n"),
    ("N10-try", "try:\n    pass\nexcept Exception:\n    pass\n"),
    ("N11-with", "with context:\n    pass\n"),
    ("N12-import-child", "import pkg.other\n"),
    ("N13-call", "arbitrary()\n"),
    ("N14-subscript-assignment", 'obj["x"] = 1\n'),
    ("N15-augmented-assignment", "x = 1\nx += 1\n"),
    ("N16-annotated-assignment", "x: int = 1\n"),
    ("N17-raise", "raise RuntimeError()\n"),
]

D2B2_R2_POSITIVE_INITIALIZERS = [
    ("P01-empty", ""),
    ("P02-pass", "pass\n"),
    ("P03-docstring", '"docstring"\n'),
    ("P04-literal", "constant = 1\n"),
    (
        "P05-mixed-passive",
        '"docstring"\nconstant = 1\nother = False\npass\n',
    ),
]

D2B2_R1_PREFIX_NEGATIVES = [
    (
        "globals-update",
        "from typing import TYPE_CHECKING\n"
        'globals().update({"TYPE_CHECKING": True})\n'
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "exec-rebinding",
        "from typing import TYPE_CHECKING\n"
        'exec("TYPE_CHECKING = True")\n'
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "typing-dict-rebinding",
        "import typing\n"
        'typing.__dict__["TYPE_CHECKING"] = True\n'
        "if typing.TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "vars-rebinding",
        "from typing import TYPE_CHECKING\n"
        'vars()["TYPE_CHECKING"] = True\n'
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "active-import-before-guard",
        "from typing import TYPE_CHECKING\n"
        "import pkg.b\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "conditional-before-guard",
        "from typing import TYPE_CHECKING\n"
        "if True:\n    pass\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "call-assignment-before-guard",
        "from typing import TYPE_CHECKING\n"
        "value = unknown()\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "function-before-guard",
        "from typing import TYPE_CHECKING\n"
        "def mutate():\n    pass\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "class-before-guard",
        "from typing import TYPE_CHECKING\n"
        "class Mutator:\n    pass\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "with-before-guard",
        "from typing import TYPE_CHECKING\n"
        "with context:\n    pass\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
    (
        "multiple-matching-guards",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    pass\n"
        "if TYPE_CHECKING:\n    import pkg.b\n",
    ),
]

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


def _index_graph(root, **kwargs):
    index = indexer.index_repository(str(root), **kwargs)
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


def _d2b6_spec_origin(root: Path, module: str) -> Path:
    program = (
        "import importlib.util,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "print(importlib.util.find_spec(sys.argv[2]).origin)"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", program, str(root.resolve()), module],
        capture_output=True, text=True, timeout=8, check=False,
    )
    assert result.returncode == 0, result.stderr
    return Path(result.stdout.strip()).resolve()


def test_p1d3_d2b6_sourceless_package_preempts_python_module(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B6_SOURCE_SHADOW)
    source_local, error = indexer.read_imports(root / "pkg" / "a.py")
    assert error is None
    assert next(item for item in source_local if item.module == "pkg.c").type_only
    sources = {relative: (root / relative).read_bytes() for relative in D2B6_SOURCE_SHADOW}

    before, before_graph = _index_graph(root)
    assert set(before.modules) == {"pkg.__init__", "pkg.a", "pkg.c", "pkg.launcher"}
    assert "pkg.c" in before_graph.soft_edges["pkg.a"]
    assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
    assert not any(
        set(members) == {"pkg.a", "pkg.c"}
        for members in _scc_signature(before, before_graph)
    )
    cached = _cache_data(root, root / "pkg" / "a.py")
    assert cached["import_classification_semantics_version"] == 7

    compiled_source = tmp_path / "launcher_init_source.py"
    compiled_source.write_text(
        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
        encoding="utf-8",
    )
    package_directory = root / "pkg" / "launcher"
    package_directory.mkdir()
    bytecode = package_directory / "__init__.pyc"
    py_compile.compile(str(compiled_source), cfile=str(bytecode), doraise=True)
    compiled_source.unlink()
    assert (root / "pkg" / "launcher.py").is_file()
    assert bytecode.is_file()
    assert not (package_directory / "__init__.py").exists()

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("artifact transition must not reparse unchanged source")

    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
    during, during_graph = _index_graph(root)
    assert set(during.modules) == set(before.modules)
    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
    assert not during.skipped
    _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 7
    assert _d2b6_spec_origin(root, "pkg.launcher") == bytecode.resolve()
    assert run_synthetic_import(root, "pkg.a").returncode == 0
    assert run_synthetic_import(root, "pkg.c").returncode == 0
    failed = run_synthetic_import(root, "pkg.launcher")
    assert failed.returncode != 0
    assert "partially initialized module" in failed.stderr
    assert "pkg.a" in failed.stderr

    bytecode.unlink()
    package_directory.rmdir()
    after, after_graph = _index_graph(root)
    assert set(after.modules) == set(before.modules)
    assert after.source_fingerprints_by_module == before.source_fingerprints_by_module
    assert "pkg.c" in after_graph.soft_edges["pkg.a"]
    assert "pkg.c" not in after_graph.hard_edges["pkg.a"]
    assert not any(
        set(members) == {"pkg.a", "pkg.c"}
        for members in _scc_signature(after, after_graph)
    )
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 7
    assert {relative: (root / relative).read_bytes() for relative in sources} == sources


def test_p1d3_d2b6_native_extension_shadow_veto(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    original, original_graph = _index_graph(root)
    assert "pkg.b" in original_graph.soft_edges["pkg.a"]
    placeholder = root / "pkg" / ("a" + EXTENSION_SUFFIXES[0])
    placeholder.write_bytes(b"not-a-real-extension")
    index, graph = _index_graph(root)
    assert set(index.modules) == set(original.modules)
    assert not index.skipped
    _assert_d2b5_hard_scc(index, graph, "pkg.b")
    assert _d2b6_spec_origin(root, "pkg.a") == placeholder.resolve()


@pytest.mark.parametrize(
    "case,relative",
    [
        ("A01", "unrelated.pyc"),
        ("A02", "pkg/hidden.pyc"),
        ("A03", "pkg/launcher/__init__.pyc"),
        ("A04", "pkg/native" + EXTENSION_SUFFIXES[0]),
        ("A05", "pkg/other" + EXTENSION_SUFFIXES[-1]),
        ("A06", "build/hidden.pyc"),
        ("A07", ".venv/hidden.pyc"),
        ("A08", "build/unrelated" + EXTENSION_SUFFIXES[0]),
    ],
)
def test_p1d3_d2b6_alternative_artifact_matrix(
    tmp_path, isolated_dirs, case, relative,
):
    root = write_synthetic_repository(tmp_path / case, D2B_NAME_SAFE)
    before, before_graph = _index_graph(root)
    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
    before_facts = {
        source: _cache_data(root, root / source)["typing_guard_opaque_effects"]
        for source in D2B_NAME_SAFE
    }
    artifact = root / relative
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"not-an-executable-artifact")
    index, graph = _index_graph(root)
    assert set(index.modules) == set(before.modules)
    assert index.source_fingerprints_by_module == before.source_fingerprints_by_module
    assert {
        source: _cache_data(root, root / source)["typing_guard_opaque_effects"]
        for source in D2B_NAME_SAFE
    } == before_facts
    _assert_d2b5_hard_scc(index, graph, "pkg.b")


@pytest.mark.parametrize(
    "case,relative",
    [
        ("C01", None),
        ("C02", "pkg/a.py"),
        ("C03", "pkg/b.py"),
        ("C04", "pkg/__init__.py"),
    ],
)
def test_p1d3_d2b6_standard_pycache_remains_soft(
    tmp_path, isolated_dirs, case, relative,
):
    root = write_synthetic_repository(tmp_path / case, D2B_NAME_SAFE)
    if relative is not None:
        py_compile.compile(str(root / relative), doraise=True)
    index, graph = _index_graph(root)
    assert next(
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is True
    assert "pkg.b" in graph.soft_edges["pkg.a"]
    assert "pkg.b" not in graph.hard_edges["pkg.a"]
    assert _scc_signature(index, graph) == ()
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 7


def test_p1d3_d2b6_symlinked_directory_veto(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    target = tmp_path / "symlink-target"
    target.mkdir()
    link = root / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")
    assert link.is_symlink() and link.is_dir()
    index, graph = _index_graph(root)
    assert set(index.modules) == {"pkg.__init__", "pkg.a", "pkg.b"}
    _assert_d2b5_hard_scc(index, graph, "pkg.b")


@pytest.mark.parametrize(
    "case",
    ["safe", "sourceless-shadow", "native-shadow", "pycache", "ignored-bytecode"],
)
def test_p1d3_d2b6_inline_process_pool_parity(
    tmp_path, isolated_dirs, monkeypatch, case,
):
    fixture = D2B6_SOURCE_SHADOW if case == "sourceless-shadow" else D2B_NAME_SAFE

    def prepare(root, label):
        if case == "sourceless-shadow":
            source = tmp_path / (label + "_init.py")
            source.write_text(
                "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
                encoding="utf-8",
            )
            package_directory = root / "pkg" / "launcher"
            package_directory.mkdir()
            py_compile.compile(
                str(source),
                cfile=str(package_directory / "__init__.pyc"),
                doraise=True,
            )
            source.unlink()
        elif case == "native-shadow":
            (root / "pkg" / ("a" + EXTENSION_SUFFIXES[0])).write_bytes(
                b"not-a-real-extension"
            )
        elif case == "pycache":
            py_compile.compile(str(root / "pkg" / "a.py"), doraise=True)
        elif case == "ignored-bytecode":
            artifact = root / "build" / "hidden.pyc"
            artifact.parent.mkdir()
            artifact.write_bytes(b"not-executable-bytecode")

    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
    prepare(inline_root, "inline")
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline_index, inline_graph = _index_graph(inline_root)

    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
    prepare(pool_root, "pool")
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pool_index, pool_graph = _index_graph(pool_root)

    assert set(pool_index.modules) == set(inline_index.modules)
    assert pool_index.source_fingerprints_by_module == (
        inline_index.source_fingerprints_by_module
    )
    assert _import_signature(pool_index) == _import_signature(inline_index)
    assert _graph_signature(pool_index, pool_graph) == (
        _graph_signature(inline_index, inline_graph)
    )


def _assert_d2b5_hard_scc(index, graph, target):
    guarded = next(
        item for item in index.modules["pkg.a"].imports
        if item.module == target and not item.is_from_import
    )
    assert guarded.type_only is False
    assert target in graph.hard_edges["pkg.a"]
    assert "pkg.a" in graph.hard_edges[target]
    assert target not in graph.soft_edges["pkg.a"]
    assert any(
        set(members) == {"pkg.a", target}
        for members in _scc_signature(index, graph)
    )


def test_p1d3_d2b5_excluded_child_keeps_hard_scc(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B5_EXCLUDED_CHILD)
    source_local, error = indexer.read_imports(root / "pkg" / "a.py")
    assert error is None
    assert next(item for item in source_local if item.module == "pkg.c").type_only
    index, graph = _index_graph(root, excludes=["pkg/hidden.py"])
    assert "pkg.hidden" not in index.modules
    assert {"pkg.a", "pkg.c", "pkg.launcher"} <= set(index.modules)
    assert not index.skipped
    _assert_d2b5_hard_scc(index, graph, "pkg.c")
    assert indexer._project_typing_imports_closed(index.modules) is False
    assert run_synthetic_import(root, "pkg.a").returncode == 0
    assert run_synthetic_import(root, "pkg.c").returncode == 0
    failed = run_synthetic_import(root, "pkg.launcher")
    assert failed.returncode != 0
    assert "partially initialized module" in failed.stderr
    assert "pkg.a" in failed.stderr


def test_p1d3_d2b5_excluded_local_typing_shadow(
    tmp_path, isolated_dirs,
):
    fixture = {**D2B_NAME_SAFE, "typing.py": "TYPE_CHECKING = True\n"}
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    source_local, error = indexer.read_imports(root / "pkg" / "a.py")
    assert error is None
    assert next(item for item in source_local if item.module == "pkg.b").type_only
    index, graph = _index_graph(root, excludes=["typing.py"])
    assert "typing" not in index.modules
    _assert_d2b5_hard_scc(index, graph, "pkg.b")
    program = (
        "import sys;"
        "assert 'typing' not in sys.modules;"
        "sys.path.insert(0, sys.argv[1]);"
        "import pkg.a"
    )
    failed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", program, str(root.resolve())],
        capture_output=True, text=True, timeout=8, check=False,
    )
    assert failed.returncode != 0
    assert "partially initialized module" in failed.stderr


@pytest.mark.parametrize(
    "case,extra,kwargs",
    [
        ("X01", {"typing.py": "TYPE_CHECKING = True\n"}, {"excludes": ["typing.py"]}),
        ("X02", {"pkg/hidden.py": "pass\n"}, {"excludes": ["pkg/hidden.py"]}),
        ("X03", {"hidden/unrelated.py": "pass\n"}, {"extra_ignored_dirs": {"hidden"}}),
        ("X04", {"build/unrelated.py": "pass\n"}, {}),
        ("X05", {}, {"excludes": ["nonexistent.py"]}),
    ],
)
def test_p1d3_d2b5_exclusion_matrix(
    tmp_path, isolated_dirs, case, extra, kwargs,
):
    root = write_synthetic_repository(tmp_path / case, {**D2B_NAME_SAFE, **extra})
    index, graph = _index_graph(root, **kwargs)
    guarded = next(
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b"
    )
    assert guarded.type_only is (case == "X05")
    assert ("pkg.b" in graph.hard_edges["pkg.a"]) is (case != "X05")
    assert ("pkg.b" in graph.soft_edges["pkg.a"]) is (case == "X05")


def test_p1d3_d2b5_package_prefix_exclude(
    tmp_path, isolated_dirs,
):
    fixture = {
        "app/__init__.py": "pass\n",
        "app/a.py": (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    import app.b\n"
            "value = 1\n"
        ),
        "app/b.py": "from app.a import value\n",
        "pkg/hidden.py": "pass\n",
    }
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, graph = _index_graph(root, excludes=["pkg"])
    assert "pkg.hidden" not in index.modules
    assert next(
        item for item in index.modules["app.a"].imports
        if item.module == "app.b"
    ).type_only is False
    assert "app.b" in graph.hard_edges["app.a"]


def test_p1d3_d2b5_source_visibility_toggle(
    tmp_path, isolated_dirs,
):
    fixture = {**D2B_NAME_SAFE, "unrelated.py": "pass\n"}
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    original_a = (root / "pkg" / "a.py").read_bytes()
    original_b = (root / "pkg" / "b.py").read_bytes()
    states = []
    for excludes in (None, ["unrelated.py"], None):
        index, graph = _index_graph(root, excludes=excludes)
        states.append((
            next(
                item for item in index.modules["pkg.a"].imports
                if item.module == "pkg.b"
            ).type_only,
            "pkg.b" in graph.hard_edges["pkg.a"],
            "pkg.b" in graph.soft_edges["pkg.a"],
        ))
        assert _cache_data(root, root / "pkg" / "a.py")[
            "import_classification_semantics_version"
        ] == 7
    assert states == [(True, False, True), (False, True, False), (True, False, True)]
    assert (root / "pkg" / "a.py").read_bytes() == original_a
    assert (root / "pkg" / "b.py").read_bytes() == original_b


D2B5_IMPORTFROM_NEGATIVES = [
    ("F01", "from pkg import absent\n", {}, None),
    ("F02", "from pkg import b, absent\n", {}, None),
    ("F03", "from pkg import __path__\n", {}, None),
    ("F04", "from pkg import child\n", {"pkg/child.py": "pass\n"}, ["pkg/child.py"]),
    ("F05", "from pkg.sub import child\n", {"pkg/sub/__init__.py": "pass\n"}, None),
    ("F06", "from typing import Any\n", {}, None),
]


@pytest.mark.parametrize("case,source,extra,excludes", D2B5_IMPORTFROM_NEGATIVES)
def test_p1d3_d2b5_importfrom_negative_matrix(
    tmp_path, isolated_dirs, case, source, extra, excludes,
):
    fixture = {**D2B_NAME_SAFE, "pkg/reader.py": source, **extra}
    root = write_synthetic_repository(tmp_path / case, fixture)
    index, graph = _index_graph(root, excludes=excludes)
    assert indexer._project_typing_imports_closed(index.modules) is False
    _assert_d2b5_hard_scc(index, graph, "pkg.b")
    cold_imports = _import_signature(index)
    cold_graph = _graph_signature(index, graph)
    warm_index, warm_graph = _index_graph(root, excludes=excludes)
    assert _import_signature(warm_index) == cold_imports
    assert _graph_signature(warm_index, warm_graph) == cold_graph


D2B5_IMPORTFROM_POSITIVES = [
    ("P01", "from pkg.a import value\n", {}),
    ("P02", "from pkg import b\n", {}),
    ("P03", "from pkg import b as alias\n", {}),
    ("P04", "from pkg import b, c\n", {"pkg/c.py": "pass\n"}),
    (
        "P05", "from pkg.sub import child\n",
        {"pkg/sub/__init__.py": "pass\n", "pkg/sub/child.py": "pass\n"},
    ),
    ("P06", "from typing import TYPE_CHECKING\n", {}),
]


@pytest.mark.parametrize("case,source,extra", D2B5_IMPORTFROM_POSITIVES)
def test_p1d3_d2b5_importfrom_positive_matrix(
    tmp_path, isolated_dirs, case, source, extra,
):
    fixture = {**D2B_NAME_SAFE, "pkg/reader.py": source, **extra}
    root = write_synthetic_repository(tmp_path / case, fixture)
    index, graph = _index_graph(root)
    assert indexer._project_typing_imports_closed(index.modules) is True
    guarded = next(
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b"
    )
    assert guarded.type_only is True
    assert "pkg.b" in graph.soft_edges["pkg.a"]
    assert "pkg.b" not in graph.hard_edges["pkg.a"]
    cold_imports = _import_signature(index)
    cold_graph = _graph_signature(index, graph)
    warm_index, warm_graph = _index_graph(root)
    assert _import_signature(warm_index) == cold_imports
    assert _graph_signature(warm_index, warm_graph) == cold_graph


@pytest.mark.parametrize(
    "case,fixture,kwargs",
    [
        ("safe", D2B_NAME_SAFE, {}),
        ("excluded-child", D2B5_EXCLUDED_CHILD, {"excludes": ["pkg/hidden.py"]}),
        (
            "excluded-typing",
            {**D2B_NAME_SAFE, "typing.py": "TYPE_CHECKING = True\n"},
            {"excludes": ["typing.py"]},
        ),
        (
            "ignored-unrelated",
            {**D2B_NAME_SAFE, "build/unrelated.py": "pass\n"},
            {},
        ),
        (
            "indexed-child",
            {**D2B_NAME_SAFE, "pkg/reader.py": "from pkg import b\n"},
            {},
        ),
        (
            "missing-child",
            {**D2B_NAME_SAFE, "pkg/reader.py": "from pkg import absent\n"},
            {},
        ),
    ],
)
def test_p1d3_d2b5_inline_process_pool_parity(
    tmp_path, isolated_dirs, monkeypatch, case, fixture, kwargs,
):
    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline_index, inline_graph = _index_graph(inline_root, **kwargs)

    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pool_index, pool_graph = _index_graph(pool_root, **kwargs)

    assert set(pool_index.modules) == set(inline_index.modules)
    assert pool_index.source_fingerprints_by_module == (
        inline_index.source_fingerprints_by_module
    )
    assert _import_signature(pool_index) == _import_signature(inline_index)
    assert _graph_signature(pool_index, pool_graph) == (
        _graph_signature(inline_index, inline_graph)
    )


@pytest.mark.parametrize(
    "fixture,excludes",
    [
        (D2B5_EXCLUDED_CHILD, ["pkg/hidden.py"]),
        ({**D2B_NAME_SAFE, "pkg/reader.py": "from pkg import absent\n"}, None),
    ],
    ids=["excluded-child", "incomplete-child"],
)
def test_p1d3_d2b5_original_worker_reindex_same_domain(
    tmp_path, isolated_dirs, fixture, excludes,
):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    original, graph = _index_graph(root, excludes=excludes)
    plan = plan_original_worker_reindex(original, graph.hard_edges)
    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
    assert plan.selected_module_ids
    captured, captured_graph = _index_graph(
        root,
        excludes=excludes,
        source_capture_module_ids=plan.selected_module_ids,
    )
    assert captured.original_worker_capture_status == (
        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    )
    assert captured_graph.hard_edges == graph.hard_edges
    assert captured_graph.soft_edges == graph.soft_edges
    assert captured.source_fingerprints_by_module == (
        original.source_fingerprints_by_module
    )
    assert plan.selected_module_ids.issubset(
        captured.original_worker_source_snapshots
    )
    for module_id in plan.selected_module_ids:
        assert captured.original_worker_source_snapshots[
            module_id
        ].source_fingerprint == captured.source_fingerprints_by_module[module_id]


D2B4_MUTATIONS = [
    ("M01", "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n"),
    ("M02", 'import typing\nsetattr(typing, "TYPE_CHECKING", True)\nimport pkg.a\n'),
    ("M03", 'import typing\ntyping.__dict__["TYPE_CHECKING"] = True\nimport pkg.a\n'),
    ("M04", 'exec("import typing; typing.TYPE_CHECKING = True")\nimport pkg.a\n'),
    ("M05", 'globals()["TYPE_CHECKING"] = True\nimport pkg.a\n'),
    ("M06", 'vars()["TYPE_CHECKING"] = True\nimport pkg.a\n'),
    ("M07", 'import typing\ntyping.__dict__.update({"TYPE_CHECKING": True})\nimport pkg.a\n'),
    ("M08", 'globals().update({"TYPE_CHECKING": True})\nimport pkg.a\n'),
    ("M09", 'def mutate():\n    import typing\n    typing.TYPE_CHECKING = True\nimport pkg.a\n'),
]


def _assert_d2b4_launcher_graph(index, graph):
    guarded = next(
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.c"
    )
    assert guarded.type_only is False
    assert "pkg.c" in graph.hard_edges["pkg.a"]
    assert "pkg.a" in graph.hard_edges["pkg.c"]
    assert "pkg.c" not in graph.soft_edges["pkg.a"]
    assert any(
        set(members) == {"pkg.a", "pkg.c"}
        for members in _scc_signature(index, graph)
    )


def test_p1d3_d2b4_indexed_launcher_mutation_retains_scc(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B4_INDEXED_LAUNCHER)
    index, graph = _index_graph(root)
    source_local, error = indexer.read_imports(
        root / "pkg" / "a.py",
        tree=ast.parse(D2B4_INDEXED_LAUNCHER["pkg/a.py"]),
    )
    assert error is None
    assert next(item for item in source_local if item.module == "pkg.c").type_only
    _assert_d2b4_launcher_graph(index, graph)
    assert _cache_data(root, root / "pkg" / "launcher.py")[
        "typing_guard_marker_mutation"
    ] is True
    for module in ("pkg.a", "pkg.c"):
        assert run_synthetic_import(root, module).returncode == 0
    failed = run_synthetic_import(root, "pkg.launcher")
    assert failed.returncode != 0
    assert "partially initialized module 'pkg.a'" in failed.stderr


@pytest.mark.parametrize("case,launcher", D2B4_MUTATIONS)
def test_p1d3_d2b4_mutation_matrix(
    tmp_path, isolated_dirs, case, launcher,
):
    fixture = {**D2B4_INDEXED_LAUNCHER, "pkg/launcher.py": launcher}
    root = write_synthetic_repository(tmp_path / case, fixture)
    worker = indexer._process_single_file(str(root / "pkg" / "launcher.py"), str(root))
    assert worker["typing_guard_marker_mutation"] is True
    index, graph = _index_graph(root)
    _assert_d2b4_launcher_graph(index, graph)


@pytest.mark.parametrize(
    "case,launcher",
    [item for item in D2B4_MUTATIONS if item[0] in {"M01", "M02", "M03", "M04", "M07"}],
)
def test_p1d3_d2b4_executed_mutation_differential(
    tmp_path, isolated_dirs, case, launcher,
):
    fixture = {**D2B4_INDEXED_LAUNCHER, "pkg/launcher.py": launcher}
    root = write_synthetic_repository(tmp_path / case, fixture)
    failed = run_synthetic_import(root, "pkg.launcher")
    assert failed.returncode != 0
    assert "partially initialized module 'pkg.a'" in failed.stderr


def test_p1d3_d2b4_unrelated_indexed_mutation_veto(
    tmp_path, isolated_dirs,
):
    fixture = {
        **D2B_NAME_SAFE,
        "unrelated.py": "import typing\ntyping.TYPE_CHECKING = True\n",
    }
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, graph = _index_graph(root)
    assert next(
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is False
    assert "pkg.b" in graph.hard_edges["pkg.a"]


@pytest.mark.parametrize("fixture", [D2B_NAME_SAFE, D2B4_INDEXED_LAUNCHER])
def test_p1d3_d2b4_cold_warm_parity(
    tmp_path, isolated_dirs, monkeypatch, fixture,
):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    cold_index, cold_graph = _index_graph(root)
    cold_imports = _import_signature(cold_index)
    cold_graph_signature = _graph_signature(cold_index, cold_graph)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("valid warm cache must not parse")

    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
    warm_index, warm_graph = _index_graph(root)
    assert _import_signature(warm_index) == cold_imports
    assert _graph_signature(warm_index, warm_graph) == cold_graph_signature


def test_p1d3_d2b4_forged_stale_launcher_cache(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B4_INDEXED_LAUNCHER)
    _index_graph(root)
    source = root / "pkg" / "launcher.py"
    cached = _cache_data(root, source)
    assert cached["import_classification_semantics_version"] == 7
    assert cached["typing_guard_marker_mutation"] is True
    cached["import_classification_semantics_version"] = 3
    cached["typing_guard_marker_mutation"] = False
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    index, graph = _index_graph(root)
    _assert_d2b4_launcher_graph(index, graph)
    rewritten = _cache_data(root, source)
    assert rewritten["import_classification_semantics_version"] == 7
    assert rewritten["typing_guard_marker_mutation"] is True


@pytest.mark.parametrize(
    "case,value",
    [("missing", None), ("none", None), ("string", "false"), ("integer", 0)],
)
def test_p1d3_d2b4_malformed_current_launcher_cache(
    tmp_path, isolated_dirs, monkeypatch, case, value,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B4_INDEXED_LAUNCHER)
    _index_graph(root)
    source = root / "pkg" / "launcher.py"
    cached = _cache_data(root, source)
    if case == "missing":
        cached.pop("typing_guard_marker_mutation")
    else:
        cached["typing_guard_marker_mutation"] = value
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    real_read = indexer.read_source_snapshot
    reads = []

    def tracked_read(path):
        reads.append(Path(path).resolve())
        return real_read(path)

    monkeypatch.setattr(indexer, "read_source_snapshot", tracked_read)
    index, graph = _index_graph(root)
    _assert_d2b4_launcher_graph(index, graph)
    assert reads.count(source.resolve()) == 1
    assert _cache_data(root, source)["typing_guard_marker_mutation"] is True


@pytest.mark.parametrize(
    "fixture",
    [
        D2B_NAME_SAFE,
        D2B4_INDEXED_LAUNCHER,
        {
            "pkg/__init__.py": "pass\n",
            "pkg/sub/__init__.py": "pass\n",
            "pkg/sub/a.py": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    import pkg.sub.c\n"
                "value = 1\n"
            ),
            "pkg/sub/c.py": "from pkg.sub.a import value\n",
        },
        {
            "pkg/__init__.py": "pass\n",
            "pkg/sub/__init__.py": "pass\n",
            "pkg/sub/a.py": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    import pkg.sub.c\n"
                "value = 1\n"
            ),
            "pkg/sub/c.py": "from pkg.sub.a import value\n",
            "pkg/sub/launcher.py": (
                "import typing\n"
                "typing.TYPE_CHECKING = True\n"
                "import pkg.sub.a\n"
            ),
        },
    ],
    ids=["safe", "unsafe", "nested-safe", "nested-unsafe"],
)
def test_p1d3_d2b4_inline_process_pool_parity(
    tmp_path, isolated_dirs, monkeypatch, fixture,
):
    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline_index, inline_graph = _index_graph(inline_root)
    inline_flags = {
        relative: _cache_data(inline_root, inline_root / relative)[
            "typing_guard_marker_mutation"
        ]
        for relative in fixture
    }
    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pool_index, pool_graph = _index_graph(pool_root)
    pool_flags = {
        relative: _cache_data(pool_root, pool_root / relative)[
            "typing_guard_marker_mutation"
        ]
        for relative in fixture
    }
    assert pool_flags == inline_flags
    assert _import_signature(pool_index) == _import_signature(inline_index)
    assert _graph_signature(pool_index, pool_graph) == _graph_signature(
        inline_index, inline_graph,
    )


@pytest.mark.parametrize("case,launcher", D2B4_R1_LAUNCHERS)
def test_p1d3_d2b4_r1_opaque_launcher_counterexamples(
    tmp_path, isolated_dirs, case, launcher,
):
    fixture = {**D2B4_R1_BASE, "pkg/launcher.py": launcher}
    root = write_synthetic_repository(tmp_path / case, fixture)
    tree = ast.parse(launcher)
    assert indexer._possible_project_typing_marker_mutation(tree) is False
    assert indexer._project_typing_opaque_effects(tree) is True
    worker = indexer._process_single_file(str(root / "pkg" / "launcher.py"), str(root))
    assert worker["typing_guard_marker_mutation"] is False
    assert worker["typing_guard_opaque_effects"] is True
    index, graph = _index_graph(root)
    _assert_d2b4_launcher_graph(index, graph)
    for module in ("pkg.a", "pkg.c"):
        assert run_synthetic_import(root, module).returncode == 0
    failed = run_synthetic_import(root, "pkg.launcher")
    assert failed.returncode != 0
    assert "partially initialized module 'pkg.a'" in failed.stderr


D2B4_R1_UNKNOWN_EFFECTS = [
    ("E01", "arbitrary()\n", True),
    ("E02", "callback = arbitrary.callback\n", True),
    ("E03", "def f(): pass\n", True),
    ("E04", "class C: pass\n", True),
    ("E05", 'import typing\ntarget = typing.__dict__\ntarget["TYPE_CHECKING"] = True\n', True),
    ("E06", 'import typing\ngetattr(typing, "__dict__").update({"TYPE_CHECKING": True})\n', True),
    ("E07", "if condition:\n    pass\n", True),
    ("E08", "try:\n    pass\nexcept Exception:\n    pass\n", True),
    ("E09", "x: int = 1\n", True),
    ("E10", "x = 1\nx += 1\n", True),
    ("E11", "with manager:\n    pass\n", True),
    ("E12", 'import importlib\nimportlib.import_module("typing")\n', True),
]


@pytest.mark.parametrize("case,source,opaque", D2B4_R1_UNKNOWN_EFFECTS)
def test_p1d3_d2b4_r1_unknown_effects_veto(
    tmp_path, isolated_dirs, case, source, opaque,
):
    fixture = {**D2B_NAME_SAFE, "unrelated.py": source}
    root = write_synthetic_repository(tmp_path / case, fixture)
    worker = indexer._process_single_file(str(root / "unrelated.py"), str(root))
    assert worker["typing_guard_opaque_effects"] is opaque
    index, graph = _index_graph(root)
    if case == "E12":
        assert indexer._project_typing_imports_closed(index.modules) is False
    assert next(
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is False
    assert "pkg.b" in graph.hard_edges["pkg.a"]
    assert "pkg.a" in graph.hard_edges["pkg.b"]
    assert "pkg.b" not in graph.soft_edges["pkg.a"]


D2B4_R1_EXTERNAL_IMPORTS = [
    ("I01", "import sys\n"),
    ("I02", "import os\n"),
    ("I03", "import unknown_external\n"),
    ("I04", "from typing import Any\n"),
    ("I05", "from external_module import value\n"),
    ("I06", "from . import sibling\n"),
]


@pytest.mark.parametrize("case,source", D2B4_R1_EXTERNAL_IMPORTS)
def test_p1d3_d2b4_r1_external_import_veto(
    tmp_path, isolated_dirs, case, source,
):
    fixture = {**D2B_NAME_SAFE, "pkg/unrelated.py": source}
    root = write_synthetic_repository(tmp_path / case, fixture)
    index, graph = _index_graph(root)
    assert indexer._project_typing_imports_closed(index.modules) is False
    assert next(
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is False
    assert "pkg.b" in graph.hard_edges["pkg.a"]


def test_p1d3_d2b4_r1_forged_stale_opaque_cache(
    tmp_path, isolated_dirs,
):
    fixture = {**D2B4_R1_BASE, "pkg/launcher.py": D2B4_R1_LAUNCHERS[0][1]}
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    _index_graph(root)
    source = root / "pkg" / "launcher.py"
    cached = _cache_data(root, source)
    assert cached["import_classification_semantics_version"] == 7
    assert cached["typing_guard_marker_mutation"] is False
    assert cached["typing_guard_opaque_effects"] is True
    cached["import_classification_semantics_version"] = 4
    cached["typing_guard_opaque_effects"] = False
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    index, graph = _index_graph(root)
    _assert_d2b4_launcher_graph(index, graph)
    rewritten = _cache_data(root, source)
    assert rewritten["import_classification_semantics_version"] == 7
    assert rewritten["typing_guard_opaque_effects"] is True


@pytest.mark.parametrize(
    "case,value",
    [("missing", None), ("none", None), ("string", "false"), ("integer", 0)],
)
def test_p1d3_d2b4_r1_malformed_current_opaque_cache(
    tmp_path, isolated_dirs, monkeypatch, case, value,
):
    fixture = {**D2B4_R1_BASE, "pkg/launcher.py": D2B4_R1_LAUNCHERS[0][1]}
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    original, _ = _index_graph(root)
    source = root / "pkg" / "launcher.py"
    cached = _cache_data(root, source)
    if case == "missing":
        cached.pop("typing_guard_opaque_effects")
    else:
        cached["typing_guard_opaque_effects"] = value
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    real_read = indexer.read_source_snapshot
    reads = []

    def tracked_read(path):
        reads.append(Path(path).resolve())
        return real_read(path)

    monkeypatch.setattr(indexer, "read_source_snapshot", tracked_read)
    replayed, graph = _index_graph(root)
    _assert_d2b4_launcher_graph(replayed, graph)
    assert replayed.source_fingerprints_by_module["pkg.launcher"] == (
        original.source_fingerprints_by_module["pkg.launcher"]
    )
    assert reads.count(source.resolve()) == 1
    assert _cache_data(root, source)["typing_guard_opaque_effects"] is True


@pytest.mark.parametrize(
    "fixture",
    [
        D2B_NAME_SAFE,
        {**D2B4_R1_BASE, "pkg/launcher.py": D2B4_R1_LAUNCHERS[0][1]},
        {**D2B4_R1_BASE, "pkg/launcher.py": D2B4_R1_LAUNCHERS[1][1]},
    ],
    ids=["safe-name", "ior", "alias-update"],
)
def test_p1d3_d2b4_r1_cold_warm_parity(
    tmp_path, isolated_dirs, monkeypatch, fixture,
):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    cold_index, cold_graph = _index_graph(root)
    cold_imports = _import_signature(cold_index)
    cold_graph_signature = _graph_signature(cold_index, cold_graph)
    cold_flags = {
        relative: _cache_data(root, root / relative)["typing_guard_opaque_effects"]
        for relative in fixture
    }
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("valid warm cache must not parse")

    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
    warm_index, warm_graph = _index_graph(root)
    assert _import_signature(warm_index) == cold_imports
    assert _graph_signature(warm_index, warm_graph) == cold_graph_signature
    assert {
        relative: _cache_data(root, root / relative)["typing_guard_opaque_effects"]
        for relative in fixture
    } == cold_flags


def test_cold_and_warm_worker_cache_match_type_only_graph(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    cold_index, cold_graph = _index_graph(root)
    cold_imports = _import_signature(cold_index)
    cold_graph_signature = _graph_signature(cold_index, cold_graph)
    source = root / "pkg" / "a.py"
    cached = _cache_data(root, source)
    assert cached["import_classification_semantics_version"] == 7
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


@pytest.mark.parametrize(
    "stored_version", [None, 0, 1, 2, 3, 4, 5, 6],
    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5", "version-6"],
)
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
    assert rewritten["import_classification_semantics_version"] == 7
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


@pytest.mark.parametrize(
    "shadow_path", ["typing.py", "typing/__init__.py"],
    ids=["module", "package"],
)
def test_inline_and_process_pool_typing_shadow_veto_parity(
    tmp_path, isolated_dirs, monkeypatch, shadow_path,
):
    fixture = {
        **D2B_NAME_SAFE,
        shadow_path: "pass\n",
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


def _assert_dynamic_mutation_retains_hard_scc(root):
    indexed, graph = _index_graph(root)
    guarded_imports = [
        item for item in indexed.modules["pkg.a"].imports
        if item.module == "pkg.b" and not item.is_from_import
    ]
    assert len(guarded_imports) == 1
    assert guarded_imports[0].type_only is False
    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
    assert "pkg.b" not in graph.soft_edges["pkg.a"]
    assert any(
        set(members) == {"pkg.a", "pkg.b"}
        for members in _scc_signature(indexed, graph)
    )

    trees = {
        module_id: ast.parse(Path(module.absolute_path).read_text(encoding="utf-8"))
        for module_id, module in indexed.modules.items()
    }
    modeled = evaluate_package_import_order(trees, "pkg.a")
    assert modeled.outcome != "MODEL_PASS"
    scenarios = analyze_cycle_scenarios(graph.hard_edges, trees)
    assert all(
        component.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        for component in scenarios.components
        if {"pkg.a", "pkg.b"}.issubset(set(component.members))
    )

    actual = run_synthetic_import(root, "pkg.a")
    assert actual.returncode != 0
    assert "partially initialized module" in actual.stderr
    return indexed, graph


def test_d2b2_r1_globals_rebinding_keeps_hard_scc(tmp_path, isolated_dirs):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_R1_GLOBALS_MUTATION,
    )
    _assert_dynamic_mutation_retains_hard_scc(root)


def test_d2b2_r1_setattr_mutation_keeps_hard_scc(tmp_path, isolated_dirs):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_R1_SETATTR_MUTATION,
    )
    _assert_dynamic_mutation_retains_hard_scc(root)


@pytest.mark.parametrize(
    "case,source", D2B2_R1_PREFIX_NEGATIVES,
    ids=[item[0] for item in D2B2_R1_PREFIX_NEGATIVES],
)
def test_d2b2_r1_effectful_prefixes_keep_hard_edge(
    tmp_path, isolated_dirs, case, source,
):
    fixture = {
        "pkg/__init__.py": "pass\n",
        "pkg/a.py": source,
        "pkg/b.py": "from pkg.a import value\n",
    }
    root = write_synthetic_repository(tmp_path / case, fixture)
    indexed, graph = _index_graph(root)
    guarded_imports = [
        item for item in indexed.modules["pkg.a"].imports
        if item.module == "pkg.b" and not item.is_from_import
    ]
    assert guarded_imports
    assert all(item.type_only is False for item in guarded_imports)
    assert "pkg.b" in graph.hard_edges["pkg.a"]
    assert "pkg.b" not in graph.soft_edges["pkg.a"]


def test_d2b2_r1_safe_prefix_remains_type_only(tmp_path, isolated_dirs):
    fixture = {
        "pkg/__init__.py": "pass\n",
        "pkg/a.py": (
            "from typing import TYPE_CHECKING\n"
            "constant = 1\n"
            "pass\n"
            "if TYPE_CHECKING:\n"
            "    import pkg.b\n"
            "value = 1\n"
        ),
        "pkg/b.py": "from pkg.a import value\n",
    }
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    indexed, graph = _index_graph(root)
    assert indexer._project_typing_imports_closed(indexed.modules) is True
    assert all(
        indexer._process_single_file(
            str(module.absolute_path), str(root),
        )["typing_guard_opaque_effects"] is False
        for module in indexed.modules.values()
    )
    guarded_imports = [
        item for item in indexed.modules["pkg.a"].imports
        if item.module == "pkg.b" and not item.is_from_import
    ]
    assert len(guarded_imports) == 1
    assert guarded_imports[0].type_only is True
    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
    assert "pkg.b" not in graph.hard_edges["pkg.a"]
    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
    assert not any(
        {"pkg.a", "pkg.b"}.issubset(set(members))
        for members in _scc_signature(indexed, graph)
    )
    assert run_synthetic_import(root, "pkg.a").returncode == 0


def test_d2b2_r1_forged_version_one_cache_is_reparsed(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_R1_GLOBALS_MUTATION,
    )
    first, first_graph = _index_graph(root)
    assert "pkg.b" in first_graph.hard_edges["pkg.a"]
    assert any(
        item.module == "pkg.b" and not item.type_only
        for item in first.modules["pkg.a"].imports
    )

    source = root / "pkg" / "a.py"
    cached = _cache_data(root, source)
    assert cached["import_classification_semantics_version"] == 7
    forged_imports = [
        item for item in cached["imports"] if item["module"] == "pkg.b"
    ]
    assert len(forged_imports) == 1
    forged_imports[0]["type_only"] = True
    cached["import_classification_semantics_version"] = 1
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    replayed, graph = _index_graph(root)
    assert any(
        item.module == "pkg.b" and not item.type_only
        for item in replayed.modules["pkg.a"].imports
    )
    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
    assert any(
        set(members) == {"pkg.a", "pkg.b"}
        for members in _scc_signature(replayed, graph)
    )
    rewritten = _cache_data(root, source)
    assert rewritten["import_classification_semantics_version"] == 7
    assert next(
        item for item in rewritten["imports"] if item["module"] == "pkg.b"
    )["type_only"] is False


@pytest.mark.parametrize(
    "fixture", [D2B2_R1_GLOBALS_MUTATION, D2B2_R1_SETATTR_MUTATION],
    ids=["globals", "setattr"],
)
def test_d2b2_r1_dynamic_mutation_inline_process_pool_parity(
    tmp_path, isolated_dirs, monkeypatch, fixture,
):
    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline_index, inline_graph = _index_graph(inline_root)

    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pool_index, pool_graph = _index_graph(pool_root)

    assert _import_signature(pool_index) == _import_signature(inline_index)
    assert _graph_signature(pool_index, pool_graph) == (
        _graph_signature(inline_index, inline_graph)
    )
    assert pool_graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert pool_graph.hard_edges["pkg.b"] == {"pkg.a"}
    assert "pkg.b" not in pool_graph.soft_edges["pkg.a"]


def _assert_r2_unsafe_parent(root):
    indexed, graph = _index_graph(root)
    guarded = [
        item for item in indexed.modules["pkg.a"].imports
        if item.module == "pkg.b" and not item.is_from_import
    ]
    assert len(guarded) == 1
    assert guarded[0].type_only is False
    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
    assert "pkg.b" not in graph.soft_edges["pkg.a"]
    assert any(
        set(members) == {"pkg.a", "pkg.b"}
        for members in _scc_signature(indexed, graph)
    )

    trees = {
        module_id: ast.parse(Path(module.absolute_path).read_text(encoding="utf-8"))
        for module_id, module in indexed.modules.items()
    }
    scenarios = analyze_cycle_scenarios(graph.hard_edges, trees)
    assert all(
        component.classification != "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
        for component in scenarios.components
        if {"pkg.a", "pkg.b"}.issubset(set(component.members))
    )

    actual = run_synthetic_import(root, "pkg.a")
    assert actual.returncode != 0
    assert "partially initialized module" in actual.stderr
    return indexed, graph


def test_d2b2_r2_parent_initializer_mutation_retains_hard_scc(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_R2_PARENT_MUTATION,
    )
    _assert_r2_unsafe_parent(root)


def test_d2b2_r2_parent_setattr_retains_hard_scc(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_R2_PARENT_SETATTR,
    )
    _assert_r2_unsafe_parent(root)


@pytest.mark.parametrize(
    "case,outer,inner,expected_type_only,run_cpython",
    D2B2_R2_MULTILEVEL_CASES,
    ids=[item[0] for item in D2B2_R2_MULTILEVEL_CASES],
)
def test_d2b2_r2_multilevel_parent_chain(
    tmp_path, isolated_dirs, case, outer, inner,
    expected_type_only, run_cpython,
):
    fixture = dict(D2B2_R2_MULTILEVEL_COMMON)
    if outer is not None:
        fixture["pkg/__init__.py"] = outer
    if inner is not None:
        fixture["pkg/sub/__init__.py"] = inner
    root = write_synthetic_repository(tmp_path / case, fixture)
    indexed, graph = _index_graph(root)
    expected_ids = {"pkg.sub.a", "pkg.sub.b"}
    if outer is not None:
        expected_ids.add("pkg.__init__")
    if inner is not None:
        expected_ids.add("pkg.sub.__init__")
    assert set(indexed.modules) == expected_ids
    assert indexer._typing_guard_parent_initializers("pkg.sub.a") == (
        "pkg.__init__", "pkg.sub.__init__",
    )
    guarded = [
        item for item in indexed.modules["pkg.sub.a"].imports
        if item.module == "pkg.sub.b" and not item.is_from_import
    ]
    assert len(guarded) == 1
    assert guarded[0].type_only is expected_type_only
    assert graph.hard_edges["pkg.sub.b"] == {"pkg.sub.a"}
    if expected_type_only:
        assert graph.soft_edges["pkg.sub.a"] == {"pkg.sub.b"}
        assert "pkg.sub.b" not in graph.hard_edges["pkg.sub.a"]
        assert not any(
            {"pkg.sub.a", "pkg.sub.b"}.issubset(set(members))
            for members in _scc_signature(indexed, graph)
        )
    else:
        assert "pkg.sub.b" in graph.hard_edges["pkg.sub.a"]
        assert "pkg.sub.b" not in graph.soft_edges["pkg.sub.a"]
        assert any(
            set(members) == {"pkg.sub.a", "pkg.sub.b"}
            for members in _scc_signature(indexed, graph)
        )
    if run_cpython:
        actual = run_synthetic_import(root, "pkg.sub.a")
        assert (actual.returncode == 0) is expected_type_only
        if not expected_type_only:
            assert "partially initialized module" in actual.stderr


@pytest.mark.parametrize(
    "case,source", D2B2_R2_NEGATIVE_INITIALIZERS,
    ids=[item[0] for item in D2B2_R2_NEGATIVE_INITIALIZERS],
)
def test_d2b2_r2_negative_parent_initializer_matrix(
    tmp_path, isolated_dirs, case, source,
):
    assert indexer._typing_guard_passive_initializer(ast.parse(source)) is False
    fixture = {**D2B_NAME_SAFE, "pkg/__init__.py": source}
    root = write_synthetic_repository(tmp_path / case, fixture)
    indexed, graph = _index_graph(root)
    guarded = [
        item for item in indexed.modules["pkg.a"].imports
        if item.module == "pkg.b" and not item.is_from_import
    ]
    assert len(guarded) == 1
    assert guarded[0].type_only is False
    assert "pkg.b" in graph.hard_edges["pkg.a"]
    assert "pkg.b" not in graph.soft_edges["pkg.a"]


@pytest.mark.parametrize(
    "case,source", D2B2_R2_POSITIVE_INITIALIZERS,
    ids=[item[0] for item in D2B2_R2_POSITIVE_INITIALIZERS],
)
def test_d2b2_r2_positive_parent_initializer_matrix(
    tmp_path, isolated_dirs, case, source,
):
    assert indexer._typing_guard_passive_initializer(ast.parse(source)) is True
    fixture = {**D2B_NAME_SAFE, "pkg/__init__.py": source}
    root = write_synthetic_repository(tmp_path / case, fixture)
    indexed, graph = _index_graph(root)
    assert indexer._project_typing_imports_closed(indexed.modules) is True
    assert all(
        indexer._process_single_file(
            str(module.absolute_path), str(root),
        )["typing_guard_opaque_effects"] is False
        for module in indexed.modules.values()
    )
    guarded = [
        item for item in indexed.modules["pkg.a"].imports
        if item.module == "pkg.b" and not item.is_from_import
    ]
    assert len(guarded) == 1
    assert guarded[0].type_only is True
    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
    assert "pkg.b" not in graph.hard_edges["pkg.a"]
    assert _scc_signature(indexed, graph) == ()


@pytest.mark.parametrize(
    "fixture,expected_passive",
    [(D2B_NAME_SAFE, True), (D2B2_R2_PARENT_MUTATION, False)],
    ids=["safe-parent", "unsafe-parent"],
)
def test_d2b2_r2_worker_success_returns_and_warm_cache(
    tmp_path, isolated_dirs, fixture, expected_passive,
):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    parent = root / "pkg" / "__init__.py"
    cold = indexer._process_single_file(str(parent), str(root))
    assert cold["error"] is None
    assert cold["source_parse_called"] is True
    assert type(cold["typing_guard_initializer_passive"]) is bool
    assert cold["typing_guard_initializer_passive"] is expected_passive
    assert type(cold["typing_guard_marker_mutation"]) is bool
    assert cold["source_fingerprint"]
    warm = indexer._process_single_file(str(parent), str(root))
    assert warm["error"] is None
    assert warm["source_parse_called"] is False
    assert warm["cache_hit"] is True
    assert type(warm["typing_guard_initializer_passive"]) is bool
    assert warm["typing_guard_initializer_passive"] is expected_passive
    assert warm["typing_guard_marker_mutation"] is cold[
        "typing_guard_marker_mutation"
    ]
    assert warm["source_fingerprint"] == cold["source_fingerprint"]
    cached = _cache_data(root, parent)
    assert cached["import_classification_semantics_version"] == 7
    assert type(cached["typing_guard_initializer_passive"]) is bool
    assert cached["typing_guard_initializer_passive"] is expected_passive
    assert cached["typing_guard_marker_mutation"] is cold[
        "typing_guard_marker_mutation"
    ]


def test_d2b2_r2_forged_stale_parent_cache_rejected(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_R2_PARENT_MUTATION,
    )
    original, original_graph = _index_graph(root)
    assert "pkg.b" in original_graph.hard_edges["pkg.a"]
    parent = root / "pkg" / "__init__.py"
    original_fingerprint = original.source_fingerprints_by_module["pkg.__init__"]
    cached = _cache_data(root, parent)
    assert cached["import_classification_semantics_version"] == 7
    assert cached["typing_guard_initializer_passive"] is False
    cached["typing_guard_initializer_passive"] = True
    cached["import_classification_semantics_version"] = 2
    CacheManager(str(root)).set(parent, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    replayed, graph = _index_graph(root)
    assert replayed.source_fingerprints_by_module["pkg.__init__"] == (
        original_fingerprint
    )
    assert next(
        item for item in replayed.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is False
    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
    rewritten = _cache_data(root, parent)
    assert rewritten["import_classification_semantics_version"] == 7
    assert type(rewritten["typing_guard_initializer_passive"]) is bool
    assert rewritten["typing_guard_initializer_passive"] is False


@pytest.mark.parametrize(
    "case,malformed",
    [("missing", None), ("none", None), ("string", "true"), ("integer", 1)],
)
def test_d2b2_r2_malformed_current_parent_cache_rejected(
    tmp_path, isolated_dirs, monkeypatch, case, malformed,
):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_R2_PARENT_MUTATION,
    )
    _index_graph(root)
    parent = root / "pkg" / "__init__.py"
    cached = _cache_data(root, parent)
    assert cached["import_classification_semantics_version"] == 7
    if case == "missing":
        cached.pop("typing_guard_initializer_passive")
    else:
        cached["typing_guard_initializer_passive"] = malformed
    CacheManager(str(root)).set(parent, cached)
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
    replayed, graph = _index_graph(root)
    assert len(read_calls) == 3
    assert len(set(read_calls)) == 3
    assert parse_calls == [parent.resolve()]
    assert next(
        item for item in replayed.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is False
    assert graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert graph.hard_edges["pkg.b"] == {"pkg.a"}
    assert any(
        set(members) == {"pkg.a", "pkg.b"}
        for members in _scc_signature(replayed, graph)
    )
    rewritten = _cache_data(root, parent)
    assert rewritten["import_classification_semantics_version"] == 7
    assert type(rewritten["typing_guard_initializer_passive"]) is bool
    assert rewritten["typing_guard_initializer_passive"] is False


@pytest.mark.parametrize(
    "fixture",
    [D2B_NAME_SAFE, D2B2_R2_PARENT_MUTATION],
    ids=["passive-parent", "unsafe-parent"],
)
def test_d2b2_r2_cold_warm_graph_parity(
    tmp_path, isolated_dirs, monkeypatch, fixture,
):
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    cold_index, cold_graph = _index_graph(root)
    cold_imports = _import_signature(cold_index)
    cold_graph_signature = _graph_signature(cold_index, cold_graph)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("complete current warm cache must not parse source")

    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
    warm_index, warm_graph = _index_graph(root)
    assert _import_signature(warm_index) == cold_imports
    assert _graph_signature(warm_index, warm_graph) == cold_graph_signature


def test_d2b2_r2_parent_source_fingerprint_change_reclassifies_child(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    safe_index, safe_graph = _index_graph(root)
    assert "pkg.b" in safe_graph.soft_edges["pkg.a"]
    parent_fingerprint = safe_index.source_fingerprints_by_module["pkg.__init__"]
    child_fingerprint = safe_index.source_fingerprints_by_module["pkg.a"]

    (root / "pkg" / "__init__.py").write_text(
        D2B2_R2_UNSAFE_INITIALIZER, encoding="utf-8",
    )
    unsafe_index, unsafe_graph = _index_graph(root)
    assert unsafe_index.source_fingerprints_by_module["pkg.__init__"] != (
        parent_fingerprint
    )
    assert unsafe_index.source_fingerprints_by_module["pkg.a"] == (
        child_fingerprint
    )
    assert next(
        item for item in unsafe_index.modules["pkg.a"].imports
        if item.module == "pkg.b"
    ).type_only is False
    assert unsafe_graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert unsafe_graph.hard_edges["pkg.b"] == {"pkg.a"}


@pytest.mark.parametrize(
    "case,fixture",
    [
        ("safe-single", D2B_NAME_SAFE),
        ("unsafe-single", D2B2_R2_PARENT_MUTATION),
        (
            "safe-multilevel",
            {
                **D2B2_R2_MULTILEVEL_COMMON,
                "pkg/__init__.py": "pass\n",
                "pkg/sub/__init__.py": "pass\n",
            },
        ),
        (
            "unsafe-outer",
            {
                **D2B2_R2_MULTILEVEL_COMMON,
                "pkg/__init__.py": D2B2_R2_UNSAFE_INITIALIZER,
                "pkg/sub/__init__.py": "pass\n",
            },
        ),
        (
            "unsafe-inner",
            {
                **D2B2_R2_MULTILEVEL_COMMON,
                "pkg/__init__.py": "pass\n",
                "pkg/sub/__init__.py": D2B2_R2_UNSAFE_INITIALIZER,
            },
        ),
    ],
)
def test_d2b2_r2_inline_process_pool_parent_parity(
    tmp_path, isolated_dirs, monkeypatch, case, fixture,
):
    inline_root = write_synthetic_repository(tmp_path / "inline", fixture)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline_index, inline_graph = _index_graph(inline_root)

    pool_root = write_synthetic_repository(tmp_path / "pool", fixture)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pool_index, pool_graph = _index_graph(pool_root)

    assert _import_signature(pool_index) == _import_signature(inline_index)
    assert _graph_signature(pool_index, pool_graph) == (
        _graph_signature(inline_index, inline_graph)
    )


def test_d2b2_r2_original_worker_reindex_retains_hard_graph(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", D2B2_R2_PARENT_MUTATION,
    )
    original, graph = _index_graph(root)
    plan = plan_original_worker_reindex(original, graph.hard_edges)
    assert plan.status == "READY_FOR_REINDEX_NON_ATOMIC"
    assert plan.selected_module_ids

    captured = indexer.index_repository(
        str(root), source_capture_module_ids=plan.selected_module_ids,
    )
    assert captured.original_worker_capture_status == (
        "ALL_SELECTED_CAPTURED_NON_ATOMIC"
    )
    assert plan.selected_module_ids.issubset(
        captured.original_worker_source_snapshots
    )
    for module_id in plan.selected_module_ids:
        assert captured.original_worker_source_snapshots[
            module_id
        ].source_fingerprint == captured.source_fingerprints_by_module[module_id]
    assert captured.source_fingerprints_by_module == (
        original.source_fingerprints_by_module
    )

    reexport_facts = materialize_reexport_facts_by_module(
        captured.modules,
        captured.reference_facts_by_module,
    )
    trie = build_trie(captured.modules.keys())
    package_root = detect_package_root(captured.modules, trie)
    captured_graph = build_graph(
        captured.modules,
        trie=trie,
        package_root=package_root,
        reexport_facts_by_module=reexport_facts,
    )
    assert captured_graph.hard_edges == graph.hard_edges
    assert captured_graph.soft_edges == graph.soft_edges
    assert captured_graph.hard_edges["pkg.a"] == {"pkg.b"}
    assert captured_graph.hard_edges["pkg.b"] == {"pkg.a"}

