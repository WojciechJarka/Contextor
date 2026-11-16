"""D2B-2 indexer classification, cache and execution-mode regressions."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pickle
import py_compile
import subprocess
import sys
from dataclasses import replace
from importlib.machinery import EXTENSION_SUFFIXES, SOURCE_SUFFIXES
from pathlib import Path
from types import SimpleNamespace

import pytest

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.analysis.incremental import preparation
from contextor.core.analysis.refresh_planner import RefreshPlanner
from contextor.core.analysis.state_manager import RepositoryAnalysisState, load_engine_state
from contextor.core.api.facade import ContextorFacade
from contextor.core.live_state.hydration import hydrate_repository_engine
from contextor.core.live_state.store import read_metadata
from contextor.core.paths import repo_cache_dir
from contextor.core.cycle_semantics.original_worker_reindex_planning import plan_original_worker_reindex
from contextor.core.cycle_semantics.package_model import evaluate_package_import_order
from contextor.core.cycle_semantics.scenarios import analyze_cycle_scenarios
from contextor.core.domain.imports import ImportRef
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

D2B6_R1_PYCACHE_PACKAGE = {
    "__pycache__.py": "pass\n",
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.c\n"
        "value = 1\n"
    ),
    "pkg/c.py": "from pkg.a import value\n",
    "pkg/launcher.py": "import __pycache__\nimport pkg.a\n",
}

D2B6_R1_FORGED_TAGGED_CACHE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.c\n"
        "value = 1\n"
    ),
    "pkg/c.py": "from pkg.a import value\n",
    "pkg/launcher.py": "import pkg.a\n",
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


def test_p1d3_d2b7_real_windows_alternative_source_loader(
    tmp_path, isolated_dirs, monkeypatch,
):
    if ".pyw" not in SOURCE_SUFFIXES:
        pytest.skip(f"real .pyw loader unavailable: SOURCE_SUFFIXES={SOURCE_SUFFIXES!r}")

    root = write_synthetic_repository(tmp_path / "repo", D2B6_SOURCE_SHADOW)
    source_bytes = {
        relative: (root / relative).read_bytes()
        for relative in D2B6_SOURCE_SHADOW
    }
    before, before_graph = _index_graph(root)
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10
    assert _d2b6_spec_origin(root, "pkg.launcher") == (
        root / "pkg" / "launcher.py"
    ).resolve()
    assert run_synthetic_import(root, "pkg.launcher").returncode == 0
    assert "pkg.c" in before_graph.soft_edges["pkg.a"]
    assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
    assert not any(
        set(members) == {"pkg.a", "pkg.c"}
        for members in _scc_signature(before, before_graph)
    )

    package_directory = root / "pkg" / "launcher"
    package_directory.mkdir()
    alternative_source = package_directory / "__init__.pyw"
    alternative_source.write_text(
        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
        encoding="utf-8",
    )
    assert not (package_directory / "__init__.py").exists()

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("alternative source presence must not reparse indexed source")

    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
    during, during_graph = _index_graph(root)
    assert set(during.modules) == set(before.modules)
    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
    _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10
    assert _d2b6_spec_origin(root, "pkg.launcher") == alternative_source.resolve()
    assert run_synthetic_import(root, "pkg.a").returncode == 0
    assert run_synthetic_import(root, "pkg.c").returncode == 0
    failed = run_synthetic_import(root, "pkg.launcher")
    assert failed.returncode != 0
    assert "partially initialized module" in failed.stderr
    assert "pkg.a" in failed.stderr

    alternative_source.unlink()
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
    assert {
        relative: (root / relative).read_bytes() for relative in source_bytes
    } == source_bytes
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10


@pytest.mark.parametrize(
    "relative",
    ["unrelated.pyw", "build/unrelated.pyw", ".venv/unrelated.pyw"],
)
def test_p1d3_d2b7_synthetic_scanner_detection(
    tmp_path, isolated_dirs, monkeypatch, relative,
):
    monkeypatch.setattr(indexer, "_ALTERNATIVE_SOURCE_SUFFIXES", (".pyw",))
    root = write_synthetic_repository(tmp_path / "repo", D2B_NAME_SAFE)
    source_bytes = {
        source: (root / source).read_bytes()
        for source in D2B_NAME_SAFE
    }
    before, before_graph = _index_graph(root)
    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
    assert "pkg.b" not in before_graph.hard_edges["pkg.a"]
    assert _scc_signature(before, before_graph) == ()
    artifact = root / relative
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("pass\n", encoding="utf-8")
    during, during_graph = _index_graph(root)
    assert set(during.modules) == set(before.modules)
    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
    _assert_d2b5_hard_scc(during, during_graph, "pkg.b")
    artifact.unlink()
    after, after_graph = _index_graph(root)
    assert set(after.modules) == set(before.modules)
    assert after.source_fingerprints_by_module == before.source_fingerprints_by_module
    assert "pkg.b" in after_graph.soft_edges["pkg.a"]
    assert "pkg.b" not in after_graph.hard_edges["pkg.a"]
    assert _scc_signature(after, after_graph) == ()
    assert {
        source: (root / source).read_bytes() for source in source_bytes
    } == source_bytes


def test_p1d3_d2b6_r1_pycache_package_precedence(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B6_R1_PYCACHE_PACKAGE)
    original_bytes = {
        relative: (root / relative).read_bytes()
        for relative in D2B6_R1_PYCACHE_PACKAGE
    }
    before, before_graph = _index_graph(root)
    assert "pkg.c" in before_graph.soft_edges["pkg.a"]
    assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10
    assert run_synthetic_import(root, "pkg.launcher").returncode == 0

    temporary_source = tmp_path / "dangerous_pycache_initializer.py"
    temporary_source.write_text(
        "import typing\ntyping.TYPE_CHECKING = True\n", encoding="utf-8",
    )
    package_directory = root / "__pycache__"
    package_directory.mkdir()
    bytecode = package_directory / "__init__.pyc"
    py_compile.compile(str(temporary_source), cfile=str(bytecode), doraise=True)
    temporary_source.unlink()
    assert not (package_directory / "__init__.py").exists()

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("binary presence must not reparse unchanged source")

    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
    during, during_graph = _index_graph(root)
    assert set(during.modules) == set(before.modules)
    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
    _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10
    assert _d2b6_spec_origin(root, "__pycache__") == bytecode.resolve()
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
    assert {
        relative: (root / relative).read_bytes() for relative in original_bytes
    } == original_bytes
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10


def test_p1d3_d2b6_r1_forged_tagged_unchecked_hash_cache(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", D2B6_R1_FORGED_TAGGED_CACHE)
    original_bytes = {
        relative: (root / relative).read_bytes()
        for relative in D2B6_R1_FORGED_TAGGED_CACHE
    }
    before, before_graph = _index_graph(root)
    assert "pkg.c" in before_graph.soft_edges["pkg.a"]
    assert "pkg.c" not in before_graph.hard_edges["pkg.a"]
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10
    assert run_synthetic_import(root, "pkg.launcher").returncode == 0

    temporary_source = tmp_path / "forged_launcher_source.py"
    temporary_source.write_text(
        "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
        encoding="utf-8",
    )
    target_cache_path = Path(
        importlib.util.cache_from_source(str(root / "pkg" / "launcher.py"))
    )
    target_cache_path.parent.mkdir()
    py_compile.compile(
        str(temporary_source),
        cfile=str(target_cache_path),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    temporary_source.unlink()
    assert target_cache_path.parent == root / "pkg" / "__pycache__"

    def unexpected_parse(*args, **kwargs):
        raise AssertionError("binary presence must not reparse unchanged source")

    monkeypatch.setattr(indexer, "parse_source_snapshot", unexpected_parse)
    during, during_graph = _index_graph(root)
    assert set(during.modules) == set(before.modules)
    assert during.source_fingerprints_by_module == before.source_fingerprints_by_module
    _assert_d2b5_hard_scc(during, during_graph, "pkg.c")
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10
    assert _d2b6_spec_origin(root, "pkg.launcher") == (
        root / "pkg" / "launcher.py"
    ).resolve()
    failed = run_synthetic_import(root, "pkg.launcher")
    assert failed.returncode != 0
    assert "partially initialized module" in failed.stderr
    assert "pkg.a" in failed.stderr

    target_cache_path.unlink()
    target_cache_path.parent.rmdir()
    after, after_graph = _index_graph(root)
    assert set(after.modules) == set(before.modules)
    assert after.source_fingerprints_by_module == before.source_fingerprints_by_module
    assert "pkg.c" in after_graph.soft_edges["pkg.a"]
    assert "pkg.c" not in after_graph.hard_edges["pkg.a"]
    assert not any(
        set(members) == {"pkg.a", "pkg.c"}
        for members in _scc_signature(after, after_graph)
    )
    assert {
        relative: (root / relative).read_bytes() for relative in original_bytes
    } == original_bytes
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10


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
    assert cached["import_classification_semantics_version"] == 10

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
    ] == 10
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
    ] == 10
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
def test_p1d3_d2b6_r1_standard_pycache_conservative_veto(
    tmp_path, isolated_dirs, case, relative,
):
    root = write_synthetic_repository(tmp_path / case, D2B_NAME_SAFE)
    if relative is not None:
        py_compile.compile(str(root / relative), doraise=True)
    index, graph = _index_graph(root)
    guarded = next(
        item for item in index.modules["pkg.a"].imports
        if item.module == "pkg.b"
    )
    if case == "C01":
        assert guarded.type_only is True
        assert "pkg.b" in graph.soft_edges["pkg.a"]
        assert "pkg.b" not in graph.hard_edges["pkg.a"]
        assert _scc_signature(index, graph) == ()
    else:
        assert guarded.type_only is False
        _assert_d2b5_hard_scc(index, graph, "pkg.b")
    assert _cache_data(root, root / "pkg" / "a.py")[
        "import_classification_semantics_version"
    ] == 10


@pytest.mark.parametrize("case", ["N01", "N02", "N03", "N04", "N05", "N06", "N07"])
def test_p1d3_d2b6_r1_nested_pycache_negatives(
    tmp_path, isolated_dirs, case,
):
    root = write_synthetic_repository(tmp_path / case, D2B_NAME_SAFE)
    before, before_graph = _index_graph(root)
    assert "pkg.b" in before_graph.soft_edges["pkg.a"]
    before_facts = {
        relative: _cache_data(root, root / relative)["typing_guard_opaque_effects"]
        for relative in D2B_NAME_SAFE
    }
    paths = {
        "N01": root / "__pycache__" / "__init__.pyc",
        "N02": root / "pkg" / "__pycache__" / "__init__.pyc",
        "N03": root / "pkg" / "__pycache__" / "unrelated.pyc",
        "N04": root / "build" / "__pycache__" / "hidden.pyc",
        "N05": root / ".venv" / "__pycache__" / "hidden.pyc",
        "N06": Path(importlib.util.cache_from_source(str(root / "pkg" / "a.py"))),
        "N07": Path(importlib.util.cache_from_source(
            str(root / "pkg" / "a.py"), optimization="1",
        )),
    }
    artifact = paths[case]
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"not-executable-bytecode")
    index, graph = _index_graph(root)
    assert set(index.modules) == set(before.modules)
    assert index.source_fingerprints_by_module == before.source_fingerprints_by_module
    assert {
        relative: _cache_data(root, root / relative)["typing_guard_opaque_effects"]
        for relative in D2B_NAME_SAFE
    } == before_facts
    _assert_d2b5_hard_scc(index, graph, "pkg.b")


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
    [
        "safe", "sourceless-shadow", "native-shadow", "pycache",
        "ignored-bytecode", "pycache-package", "forged-tagged", "pycache-init",
        "alternative-source",
    ],
)
def test_p1d3_d2b6_inline_process_pool_parity(
    tmp_path, isolated_dirs, monkeypatch, case,
):
    fixture = (
        D2B6_SOURCE_SHADOW if case in {"sourceless-shadow", "alternative-source"}
        else D2B6_R1_PYCACHE_PACKAGE if case == "pycache-package"
        else D2B6_R1_FORGED_TAGGED_CACHE if case == "forged-tagged"
        else D2B_NAME_SAFE
    )

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
        elif case == "alternative-source":
            package_directory = root / "pkg" / "launcher"
            package_directory.mkdir()
            (package_directory / "__init__.pyw").write_text(
                "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
                encoding="utf-8",
            )
        elif case == "native-shadow":
            (root / "pkg" / ("a" + EXTENSION_SUFFIXES[0])).write_bytes(
                b"not-a-real-extension"
            )
        elif case == "pycache":
            py_compile.compile(str(root / "pkg" / "a.py"), doraise=True)
        elif case == "pycache-init":
            py_compile.compile(str(root / "pkg" / "__init__.py"), doraise=True)
        elif case == "pycache-package":
            source = tmp_path / (label + "_pycache_package.py")
            source.write_text(
                "import typing\ntyping.TYPE_CHECKING = True\n", encoding="utf-8",
            )
            package_directory = root / "__pycache__"
            package_directory.mkdir()
            py_compile.compile(
                str(source), cfile=str(package_directory / "__init__.pyc"),
                doraise=True,
            )
            source.unlink()
        elif case == "forged-tagged":
            source = tmp_path / (label + "_forged_tagged.py")
            source.write_text(
                "import typing\ntyping.TYPE_CHECKING = True\nimport pkg.a\n",
                encoding="utf-8",
            )
            target = Path(importlib.util.cache_from_source(
                str(root / "pkg" / "launcher.py")
            ))
            target.parent.mkdir()
            py_compile.compile(
                str(source), cfile=str(target), doraise=True,
                invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
            )
            source.unlink()
        elif case == "ignored-bytecode":
            artifact = root / "build" / "hidden.pyc"
            artifact.parent.mkdir()
            artifact.write_bytes(b"not-executable-bytecode")

    if case == "alternative-source" and ".pyw" not in SOURCE_SUFFIXES:
        monkeypatch.setattr(indexer, "_ALTERNATIVE_SOURCE_SUFFIXES", (".pyw",))

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
        ] == 10
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
    assert cached["import_classification_semantics_version"] == 10
    assert cached["typing_guard_marker_mutation"] is True
    cached["import_classification_semantics_version"] = 3
    cached["typing_guard_marker_mutation"] = False
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    index, graph = _index_graph(root)
    _assert_d2b4_launcher_graph(index, graph)
    rewritten = _cache_data(root, source)
    assert rewritten["import_classification_semantics_version"] == 10
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
    assert cached["import_classification_semantics_version"] == 10
    assert cached["typing_guard_marker_mutation"] is False
    assert cached["typing_guard_opaque_effects"] is True
    cached["import_classification_semantics_version"] = 4
    cached["typing_guard_opaque_effects"] = False
    CacheManager(str(root)).set(source, cached)
    indexer._CACHE_MANAGERS.pop(str(root.resolve()), None)
    index, graph = _index_graph(root)
    _assert_d2b4_launcher_graph(index, graph)
    rewritten = _cache_data(root, source)
    assert rewritten["import_classification_semantics_version"] == 10
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
    assert cached["import_classification_semantics_version"] == 10
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
    "stored_version", [None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    ids=["absent", "version-0", "version-1", "version-2", "version-3", "version-4", "version-5", "version-6", "version-7", "version-8", "version-9"],
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
    assert rewritten["import_classification_semantics_version"] == 10
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
    assert cached["import_classification_semantics_version"] == 10
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
    assert rewritten["import_classification_semantics_version"] == 10
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
    assert cached["import_classification_semantics_version"] == 10
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
    assert cached["import_classification_semantics_version"] == 10
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
    assert rewritten["import_classification_semantics_version"] == 10
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
    assert cached["import_classification_semantics_version"] == 10
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
    assert rewritten["import_classification_semantics_version"] == 10
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


_I1_SAFE = {
    "pkg/__init__.py": "pass\n",
    "pkg/a.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "value = 1\n"
    ),
    "pkg/b.py": "pass\n",
    "pkg/c.py": "pass\n",
}


def _i1_full_engine(root):
    errors, _ = ContextorFacade.analyze_project(str(root))
    assert not errors
    metadata = read_metadata(repo_cache_dir(root))
    assert metadata is not None
    persisted = load_engine_state(
        str(repo_cache_dir(root)), metadata.state_id,
        expected_repo_id=metadata.repo_id,
        expected_root_path=str(root.resolve()),
    )
    hydrated = hydrate_repository_engine(root)
    assert hydrated is not None
    return persisted, hydrated.engine


def _i1_guarded_import(state):
    return next(
        item for item in state.modules["pkg.a"].imports
        if item.module == "pkg.b"
    )


def test_sp_t4_i1_t01_safe_full_evidence(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    index, graph = _index_graph(root)
    evidence = index.typing_guard_evidence
    assert evidence["schema_version"] == 2
    assert evidence["global_policy_satisfied"] is True
    assert evidence["skipped_source_paths"] == ()
    assert evidence["unindexed_python_sources_present"] is False
    assert evidence["unindexed_import_artifacts_present"] is False
    fingerprints = evidence["source_fingerprints_by_module"]
    assert fingerprints == index.source_fingerprints_by_module
    assert set(fingerprints) == set(index.modules)
    for key in ("marker_mutation_by_module", "opaque_effects_by_module"):
        facts = evidence[key]
        assert set(facts) == set(index.modules)
        assert all(value == (False, fingerprints[name]) for name, value in facts.items())
    assert set(evidence["initializer_passivity_by_module"]) == {"pkg.__init__"}
    assert evidence["initializer_passivity_by_module"]["pkg.__init__"] == (
        True, fingerprints["pkg.__init__"]
    )
    assert _i1_guarded_import(index).type_only is True
    assert graph.soft_edges["pkg.a"] == {"pkg.b"}


def test_sp_t4_i1_t02_shadow_policy_false(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"})
    index, graph = _index_graph(root)
    assert index.typing_guard_evidence["global_policy_satisfied"] is False
    assert "typing" in index.modules
    assert _i1_guarded_import(index).type_only is False
    assert "pkg.b" in graph.hard_edges["pkg.a"]


def test_sp_t4_i1_t03_skipped_policy_false(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", {**_I1_SAFE, "broken.py": "def invalid(:\n"})
    index, graph = _index_graph(root)
    assert index.typing_guard_evidence["global_policy_satisfied"] is False
    assert index.typing_guard_evidence["skipped_source_paths"] == ("broken.py",)
    assert _i1_guarded_import(index).type_only is False
    assert "pkg.b" in graph.hard_edges["pkg.a"]


def test_sp_t4_i1_t04_inline_pool_evidence_parity(tmp_path, isolated_dirs, monkeypatch):
    inline_root = write_synthetic_repository(tmp_path / "inline", _I1_SAFE)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline, _ = _index_graph(inline_root)
    pool_root = write_synthetic_repository(tmp_path / "pool", _I1_SAFE)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pooled, _ = _index_graph(pool_root)
    assert pooled.typing_guard_evidence == inline.typing_guard_evidence


def test_sp_t4_i1_t05_snapshot_roundtrip(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    index, _ = _index_graph(root)
    persisted, engine = _i1_full_engine(root)
    assert persisted.typing_guard_evidence == index.typing_guard_evidence
    assert engine.state.typing_guard_evidence == index.typing_guard_evidence


def test_sp_t4_i1_t06_updated_invalidates_evidence(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    persisted, engine = _i1_full_engine(root)
    assert persisted.typing_guard_evidence["global_policy_satisfied"] is True
    before_import = _i1_guarded_import(engine.state)
    before_hard = dict(engine.state.dependency_graph.hard_edges)
    before_soft = dict(engine.state.dependency_graph.soft_edges)
    target = root / "pkg/c.py"
    target.write_text("pass\nVALUE = 2\n", encoding="utf-8")
    result = engine.update_file(str(target.resolve()))
    assert result.status == "UPDATED"
    assert engine.state.typing_guard_evidence == {}
    assert _i1_guarded_import(engine.state).type_only == before_import.type_only
    assert engine.state.dependency_graph.hard_edges == before_hard
    assert engine.state.dependency_graph.soft_edges == before_soft


def test_sp_t4_i1_t07_syntax_error_invalidates_evidence(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    persisted, engine = _i1_full_engine(root)
    assert persisted.typing_guard_evidence["global_policy_satisfied"] is True
    before_graph = engine.state.dependency_graph
    target = root / "broken.py"
    target.write_text("def invalid(:\n", encoding="utf-8")
    result = engine.update_file(str(target.resolve()))
    assert result.status == "SYNTAX_ERROR"
    assert engine.state.typing_guard_evidence == {}
    assert engine.state.dependency_graph is before_graph
    assert engine.state.module_parse_freshness["broken"]["state"] == "stale"


def test_sp_t4_i1_t08_rejected_transaction_preserves_evidence(
    tmp_path, isolated_dirs, monkeypatch,
):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    _, engine = _i1_full_engine(root)
    evidence_before = dict(engine.state.typing_guard_evidence)
    graph_before = engine.state.dependency_graph
    target = root / "new_module.py"
    target.write_text("pass\n", encoding="utf-8")

    def reject(*args, **kwargs):
        raise RuntimeError("I1 transaction rejection witness")

    monkeypatch.setattr(engine.registry, "sync_with_workspace", reject)
    with pytest.raises(RuntimeError, match="I1 transaction rejection witness"):
        engine.update_file(str(target.resolve()))
    assert engine.state.typing_guard_evidence == evidence_before
    assert engine.state.dependency_graph is graph_before
    assert "new_module" not in engine.state.modules


def test_sp_t4_i1c_t09_positional_constructor():
    modules = {"sample": object()}
    artifacts = {"sample": {}}
    state = RepositoryAnalysisState(modules, artifacts)
    assert state.modules is modules
    assert state.artifacts is artifacts
    assert state.typing_guard_evidence == {}


def test_sp_t4_i1c_t10_legacy_missing_field_roundtrip():
    state = RepositoryAnalysisState()
    del state.typing_guard_evidence
    restored = pickle.loads(pickle.dumps(state))
    assert "typing_guard_evidence" not in restored.__dict__
    candidate = restored.clone_for_update()
    assert candidate.typing_guard_evidence == {}


def test_sp_t4_i1c_t11_malformed_evidence():
    state = RepositoryAnalysisState(typing_guard_evidence="invalid")
    candidate = state.clone_for_update()
    assert candidate.typing_guard_evidence == {}


def test_sp_t4_i1c_t12_valid_evidence_copy():
    evidence = {"schema_version": 1, "global_policy_satisfied": True}
    state = RepositoryAnalysisState(typing_guard_evidence=evidence)
    candidate = state.clone_for_update()
    assert candidate.typing_guard_evidence == evidence
    assert candidate.typing_guard_evidence is not state.typing_guard_evidence
    candidate.typing_guard_evidence["global_policy_satisfied"] = False
    assert state.typing_guard_evidence["global_policy_satisfied"] is True


def _i2a_prepare(path: Path, module_path: str):
    return preparation.prepare_source_update(
        file_path=path,
        module_path=module_path,
        is_new=True,
        old_module=None,
        old_artifacts=None,
        old_usage=None,
    )


def test_sp_t4_i2a_t13_safe_source_evidence(tmp_path, monkeypatch):
    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "value = 1\n"
    )
    path = tmp_path / "a.py"
    path.write_text(source, encoding="utf-8")
    parse_calls = []
    import_trees = []
    original_parse = preparation.parse_source_with_fingerprint
    original_read_imports = indexer.read_imports

    def recorded_parse(file_path):
        parsed = original_parse(file_path)
        parse_calls.append(parsed)
        return parsed

    def recorded_read_imports(file_path, *, tree=None):
        import_trees.append(tree)
        return original_read_imports(file_path, tree=tree)

    monkeypatch.setattr(preparation, "parse_source_with_fingerprint", recorded_parse)
    monkeypatch.setattr(indexer, "read_imports", recorded_read_imports)
    prepared = _i2a_prepare(path, "pkg.a")
    assert not prepared.has_error
    assert len(parse_calls) == 1
    assert import_trees == [parse_calls[0].tree]
    evidence = prepared.typing_guard_source_evidence
    assert evidence["schema_version"] == 1
    assert evidence["source_fingerprint"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert evidence["initializer_passive"] is False
    assert evidence["marker_mutation"] is False
    assert evidence["opaque_effects"] is False


def test_sp_t4_i2a_t14_marker_mutation_matches_full_predicate(tmp_path):
    path = tmp_path / "other.py"
    path.write_text("import typing\ntyping.TYPE_CHECKING = True\n", encoding="utf-8")
    prepared = _i2a_prepare(path, "pkg.other")
    assert not prepared.has_error
    evidence = prepared.typing_guard_source_evidence
    assert evidence["marker_mutation"] is True
    full_index, _ = _index_graph(tmp_path)
    assert full_index.typing_guard_evidence["marker_mutation_by_module"]["other"][0] is True


def test_sp_t4_i2a_t15_initializer_passivity(tmp_path):
    path = tmp_path / "__init__.py"
    path.write_text("pass\n", encoding="utf-8")
    passive = _i2a_prepare(path, "pkg.__init__")
    assert not passive.has_error
    assert passive.typing_guard_source_evidence["initializer_passive"] is True
    path.write_text("import typing\ntyping.TYPE_CHECKING = True\n", encoding="utf-8")
    active = _i2a_prepare(path, "pkg.__init__")
    assert not active.has_error
    assert active.typing_guard_source_evidence["initializer_passive"] is False
    assert active.typing_guard_source_evidence["source_fingerprint"] != (
        passive.typing_guard_source_evidence["source_fingerprint"]
    )


def test_sp_t4_i2a_t16_guard_change_same_import_names(tmp_path):
    path = tmp_path / "a.py"
    guarded = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    import pkg.b\n"
        "value = 1\n"
    )
    path.write_text(guarded, encoding="utf-8")
    before = _i2a_prepare(path, "pkg.a")
    path.write_text(guarded.replace("if TYPE_CHECKING:", "if True:"), encoding="utf-8")
    after = _i2a_prepare(path, "pkg.a")
    assert not before.has_error and not after.has_error
    before_import = next(item for item in before.new_imports if item.module == "pkg.b")
    after_import = next(item for item in after.new_imports if item.module == "pkg.b")
    assert before_import.type_only is True
    assert after_import.type_only is False
    assert before.delta.imports_added == after.delta.imports_added
    assert before.typing_guard_source_evidence["source_fingerprint"] != (
        after.typing_guard_source_evidence["source_fingerprint"]
    )
    assert after.typing_guard_source_evidence["marker_mutation"] is False
    assert after.typing_guard_source_evidence["opaque_effects"] is False


def _i2b1_source(*, guarded: bool) -> str:
    condition = "TYPE_CHECKING" if guarded else "True"
    return (
        "from typing import TYPE_CHECKING\n"
        f"if {condition}:\n"
        "    import pkg.b\n"
        "value = 1\n"
    )


def test_sp_t4_i2b1_t17_same_names_semantic_delta_plans_graph(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    _, engine = _i1_full_engine(root)
    target = root / "pkg/a.py"
    target.write_text(_i2b1_source(guarded=False), encoding="utf-8")
    prepared = preparation.prepare_source_update(
        file_path=target,
        module_path="pkg.a",
        is_new=False,
        old_module=engine.state.modules["pkg.a"],
        old_artifacts=engine.state.artifacts.get("pkg.a"),
        old_usage=engine.state.module_usages.get("pkg.a"),
        persistent_id=engine.registry.get_module_id("pkg.a"),
        old_collision_facts=engine.state.collision_facts.get("pkg.a"),
        old_reexport_facts=engine.state.reexport_facts_by_module.get("pkg.a"),
    )
    assert not prepared.has_error
    assert prepared.delta.imports_added == []
    assert prepared.delta.imports_removed == []
    assert prepared.delta.metadata_changes["import_ref_payload_changed"] is True
    plan = RefreshPlanner.plan_refresh(
        prepared.delta,
        usage_delta=prepared.usage_delta,
        module_usages=engine.state.module_usages,
        collision_facts_changed=prepared.collision_facts_changed,
    )
    assert "modules" in plan.patch_families
    assert "dependency_graph" in plan.patch_families
    assert "cycles" in plan.graph_recomputations


@pytest.mark.parametrize("initial_guarded", [True, False], ids=["t18-soft-to-hard", "t19-hard-to-soft"])
def test_sp_t4_i2b1_t18_t19_direct_incremental_full_parity(
    tmp_path, isolated_dirs, initial_guarded,
):
    initial_fixture = {
        **_I1_SAFE,
        "pkg/a.py": _i2b1_source(guarded=initial_guarded),
    }
    root = write_synthetic_repository(tmp_path / "repo", initial_fixture)
    _, engine = _i1_full_engine(root)
    before = _i1_guarded_import(engine.state)
    assert before.type_only is initial_guarded
    assert ("pkg.b" in engine.state.dependency_graph.soft_edges.get("pkg.a", set())) is initial_guarded
    target = root / "pkg/a.py"
    final_source = _i2b1_source(guarded=not initial_guarded)
    target.write_text(final_source, encoding="utf-8")
    result = engine.update_file(str(target.resolve()))
    assert result.status == "UPDATED"
    assert result.delta.imports_added == []
    assert result.delta.imports_removed == []
    assert result.delta.metadata_changes["import_ref_payload_changed"] is True
    assert "modules" in result.shadow_plan.patch_families
    assert "dependency_graph" in result.shadow_plan.patch_families
    incremental = engine.state
    assert _i1_guarded_import(incremental).type_only is not initial_guarded
    assert ("pkg.b" in incremental.dependency_graph.hard_edges.get("pkg.a", set())) is initial_guarded
    assert ("pkg.b" in incremental.dependency_graph.soft_edges.get("pkg.a", set())) is not initial_guarded

    fresh_root = write_synthetic_repository(
        tmp_path / "fresh", {**initial_fixture, "pkg/a.py": final_source},
    )
    fresh, _ = _i1_full_engine(fresh_root)
    assert _i1_guarded_import(incremental).type_only == _i1_guarded_import(fresh).type_only
    assert incremental.dependency_graph.hard_edges == fresh.dependency_graph.hard_edges
    assert incremental.dependency_graph.soft_edges == fresh.dependency_graph.soft_edges


@pytest.mark.parametrize(
    "changes",
    [
        {"level": 1},
        {"names": ["Other"]},
        {"is_from_import": True},
        {"is_local": True},
        {"is_lazy": True},
    ],
    ids=["level", "names", "from", "local", "lazy"],
)
def test_sp_t4_i2b1_t20_other_import_ref_field_changes(changes):
    original = ImportRef(
        module="pkg.b", level=0, names=[], is_from_import=False,
    )
    changed = replace(original, **changes)
    assert original != changed
    delta = preparation.calculate_file_delta(
        module_path="pkg.a", persistent_id="M1", is_new=False,
        old_module=SimpleNamespace(imports=[original]),
        old_artifacts={}, new_imports=[changed], new_artifacts_dict={},
    )
    assert delta.imports_added == []
    assert delta.imports_removed == []
    assert delta.metadata_changes["import_ref_payload_changed"] is True
    plan = RefreshPlanner.plan_refresh(delta)
    assert "modules" in plan.patch_families
    assert "dependency_graph" in plan.patch_families


def test_sp_t4_i2b1_t21_identical_import_ref_no_graph_plan():
    original = ImportRef(
        module="pkg.b", level=0, names=[], is_from_import=False,
    )
    delta = preparation.calculate_file_delta(
        module_path="pkg.a", persistent_id="M1", is_new=False,
        old_module=SimpleNamespace(imports=[original]),
        old_artifacts={}, new_imports=[replace(original)], new_artifacts_dict={},
    )
    assert delta.imports_added == []
    assert delta.imports_removed == []
    assert "import_ref_payload_changed" not in delta.metadata_changes
    plan = RefreshPlanner.plan_refresh(delta)
    assert "dependency_graph" not in plan.patch_families
    assert plan.graph_recomputations == ()


def _i2b2_candidates(index, module_id="pkg.a"):
    evidence = index.typing_guard_evidence
    assert evidence["schema_version"] == 2
    return evidence["candidate_imports_by_module"][module_id]


def test_sp_t4_i2b2c_t22_safe_full_candidate_matches_final_imports(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    index, graph = _index_graph(root)
    candidate = _i2b2_candidates(index)
    final_imports = index.modules["pkg.a"].imports
    assert _i1_guarded_import(index).type_only is True
    assert graph.soft_edges["pkg.a"] == {"pkg.b"}
    assert candidate == tuple(final_imports)
    for before, after in zip(candidate, final_imports):
        assert before == after
        assert before.names is not after.names


def test_sp_t4_i2b2c_t23_shadow_keeps_pre_finalization_candidate(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"},
    )
    index, graph = _index_graph(root)
    candidate = _i2b2_candidates(index)
    final_import = _i1_guarded_import(index)
    saved_import = next(ref for ref in candidate if ref.module == "pkg.b")
    assert final_import.type_only is False
    assert saved_import.type_only is True
    assert "pkg.b" in graph.hard_edges["pkg.a"]


def test_sp_t4_i2b2c_t24_skipped_keeps_pre_finalization_candidate(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", {**_I1_SAFE, "broken.py": "def invalid(:\n"},
    )
    index, graph = _index_graph(root)
    candidate = _i2b2_candidates(index)
    final_import = _i1_guarded_import(index)
    saved_import = next(ref for ref in candidate if ref.module == "pkg.b")
    assert final_import.type_only is False
    assert saved_import.type_only is True
    assert index.typing_guard_evidence["skipped_source_paths"] == ("broken.py",)
    assert "pkg.b" in graph.hard_edges["pkg.a"]


@pytest.mark.parametrize(
    "ordinary_import",
    [
        "import pkg.c as helper\n",
        "from pkg.d import Symbol as Alias\n",
    ],
    ids=["import-alias-not-in-importref", "from-alias-not-in-importref"],
)
def test_sp_t4_i2b2c_t25_all_existing_importrefs_in_order(
    tmp_path, isolated_dirs, ordinary_import,
):
    fixture = {
        "pkg/__init__.py": "pass\n",
        "pkg/a.py": (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    import pkg.b\n"
            + ordinary_import
        ),
        "pkg/b.py": "pass\n",
        "pkg/c.py": "pass\n",
        "pkg/d.py": "pass\n",
    }
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, _ = _index_graph(root)
    candidate = _i2b2_candidates(index)
    extracted, error = indexer.read_imports(root / "pkg/a.py")
    assert error is None
    assert len(candidate) == len(extracted) == 3
    assert candidate == tuple(extracted)
    assert [ref.module for ref in candidate] == [
        ref.module for ref in extracted
    ]
    for captured, parsed in zip(candidate, extracted):
        assert captured == parsed
        assert captured.names == parsed.names
        assert captured.names is not parsed.names
    final_imports = index.modules["pkg.a"].imports
    assert len(final_imports) == 3
    assert [ref.module for ref in candidate] == [
        "typing", "pkg.b",
        "pkg.c" if ordinary_import.startswith("import") else "pkg.d",
    ]
    assert all(
        captured.names is not final.names
        for captured, final in zip(candidate, final_imports)
    )


def test_sp_t4_i2b2c_t26_snapshot_roundtrip_keeps_rejected_candidates(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"},
    )
    index, _ = _index_graph(root)
    persisted, engine = _i1_full_engine(root)
    candidate = _i2b2_candidates(index)
    assert _i1_guarded_import(index).type_only is False
    assert next(ref for ref in candidate if ref.module == "pkg.b").type_only is True
    assert persisted.typing_guard_evidence == index.typing_guard_evidence
    assert engine.state.typing_guard_evidence == index.typing_guard_evidence


def test_sp_t4_i2b2c_t27_inline_process_pool_evidence_parity(
    tmp_path, isolated_dirs, monkeypatch,
):
    inline_root = write_synthetic_repository(tmp_path / "inline", _I1_SAFE)
    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
    inline, _ = _index_graph(inline_root)
    pool_root = write_synthetic_repository(tmp_path / "pool", _I1_SAFE)
    monkeypatch.delenv("CONTEXTOR_DISABLE_PROCESS_POOL", raising=False)
    pooled, _ = _index_graph(pool_root)
    assert inline.typing_guard_evidence["schema_version"] == 2
    assert pooled.typing_guard_evidence == inline.typing_guard_evidence


def _i2b3_classify(index, evidence=None):
    evidence = evidence or index.typing_guard_evidence
    modules = dict(index.modules)
    for module_id, candidate_imports in evidence[
        "candidate_imports_by_module"
    ].items():
        modules[module_id] = replace(
            modules[module_id],
            imports=list(candidate_imports),
        )
    classified, policy = indexer._classify_type_only_modules(
        modules,
        source_fingerprints_by_module=evidence[
            "source_fingerprints_by_module"
        ],
        initializer_passivity_by_module=evidence[
            "initializer_passivity_by_module"
        ],
        marker_mutation_by_module=evidence[
            "marker_mutation_by_module"
        ],
        opaque_effects_by_module=evidence[
            "opaque_effects_by_module"
        ],
        skipped_source_paths=evidence["skipped_source_paths"],
        unindexed_python_sources_present=evidence[
            "unindexed_python_sources_present"
        ],
        unindexed_import_artifacts_present=evidence[
            "unindexed_import_artifacts_present"
        ],
    )
    return modules, classified, policy


def _i2b3_graph_edges(modules):
    graph = build_graph(modules)
    return (
        set(graph.hard_edges.get("pkg.a", set())),
        set(graph.soft_edges.get("pkg.a", set())),
    )


def _i2b3_guarded_import(modules):
    return next(
        item for item in modules["pkg.a"].imports
        if item.module == "pkg.b"
    )


def test_sp_t4_i2b3_t28_safe_classifier_matches_full(tmp_path, isolated_dirs):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    index, _ = _index_graph(root)
    _, classified, policy = _i2b3_classify(index)
    assert policy is True
    assert classified["pkg.a"].imports == index.modules["pkg.a"].imports
    assert _i2b3_graph_edges(classified) == _i2b3_graph_edges(index.modules)


def test_sp_t4_i2b3_t29_typing_shadow_veto_matches_full(tmp_path, isolated_dirs):
    root = write_synthetic_repository(
        tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"},
    )
    index, _ = _index_graph(root)
    _, classified, policy = _i2b3_classify(index)
    assert policy is False
    assert _i2b3_guarded_import(classified).type_only is False
    full_hard, full_soft = _i2b3_graph_edges(index.modules)
    pure_hard, pure_soft = _i2b3_graph_edges(classified)
    assert "pkg.b" in full_hard and "pkg.b" not in full_soft
    assert (pure_hard, pure_soft) == (full_hard, full_soft)


def test_sp_t4_i2b3_t30_skipped_veto_matches_full(tmp_path, isolated_dirs):
    root = write_synthetic_repository(
        tmp_path / "repo", {**_I1_SAFE, "broken.py": "def invalid(:\n"},
    )
    index, _ = _index_graph(root)
    _, classified, policy = _i2b3_classify(index)
    assert policy is False
    assert _i2b3_guarded_import(classified).type_only is False
    full_hard, full_soft = _i2b3_graph_edges(index.modules)
    pure_hard, pure_soft = _i2b3_graph_edges(classified)
    assert "pkg.b" in full_hard and "pkg.b" not in full_soft
    assert (pure_hard, pure_soft) == (full_hard, full_soft)


def test_sp_t4_i2b3_t31_parent_passivity_veto_is_preserved(
    tmp_path, isolated_dirs,
):
    fixture = {**_I1_SAFE, "pkg/__init__.py": "import typing\n"}
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, _ = _index_graph(root)
    evidence = index.typing_guard_evidence
    assert evidence["global_policy_satisfied"] is True
    assert evidence["initializer_passivity_by_module"]["pkg.__init__"][0] is False
    _, classified, policy = _i2b3_classify(index)
    assert policy is True
    assert _i2b3_guarded_import(classified).type_only is False
    assert _i1_guarded_import(index).type_only is False


@pytest.mark.parametrize(
    "extra_source,evidence_key",
    [
        ("import typing\ntyping.TYPE_CHECKING = True\n", "marker_mutation_by_module"),
        ("eval('0')\n", "opaque_effects_by_module"),
    ],
    ids=["marker-mutation", "opaque-effects"],
)
def test_sp_t4_i2b3_t32_project_veto_is_preserved(
    tmp_path, isolated_dirs, extra_source, evidence_key,
):
    fixture = {**_I1_SAFE, "pkg/c.py": extra_source}
    root = write_synthetic_repository(tmp_path / "repo", fixture)
    index, _ = _index_graph(root)
    evidence = index.typing_guard_evidence
    assert evidence["global_policy_satisfied"] is False
    assert evidence[evidence_key]["pkg.c"][0] is True
    _, classified, policy = _i2b3_classify(index)
    assert policy is False
    assert _i2b3_guarded_import(classified).type_only is False
    assert _i1_guarded_import(index).type_only is False


def test_sp_t4_i2b3_t33_fingerprint_mismatch_fails_closed(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(tmp_path / "repo", _I1_SAFE)
    index, _ = _index_graph(root)
    evidence = dict(index.typing_guard_evidence)
    marker_facts = dict(evidence["marker_mutation_by_module"])
    marker_facts["pkg.a"] = (False, "stale-fingerprint")
    evidence["marker_mutation_by_module"] = marker_facts
    _, classified, policy = _i2b3_classify(index, evidence)
    assert policy is False
    assert _i2b3_guarded_import(classified).type_only is False


def test_sp_t4_i2b3_t34_classifier_is_copy_on_write(
    tmp_path, isolated_dirs,
):
    root = write_synthetic_repository(
        tmp_path / "repo", {**_I1_SAFE, "typing.py": "pass\n"},
    )
    index, _ = _index_graph(root)
    modules, classified, policy = _i2b3_classify(index)
    assert policy is False
    assert classified is not modules
    assert set(classified) == set(modules)
    assert classified["pkg.a"] is not modules["pkg.a"]
    assert _i2b3_guarded_import(modules).type_only is True
    assert _i2b3_guarded_import(classified).type_only is False
    for module_id in modules:
        if module_id != "pkg.a":
            assert classified[module_id] is modules[module_id]
    assert _i2b3_guarded_import(modules).type_only is True


def _i2b4_verify_case(
    tmp_path, initial, final, changed_path, *, deleted=False
):
    from contextor.core.analysis.incremental.type_only_policy import (
        reclassify_incremental_type_only,
    )
    from contextor.core.domain.module import Module

    old_root = write_synthetic_repository(
        tmp_path / "initial", initial
    )
    old_index, _ = _index_graph(old_root)

    new_root = write_synthetic_repository(
        tmp_path / "final", final
    )
    new_index, new_graph = _index_graph(new_root)

    module_id = ".".join(
        Path(changed_path).with_suffix("").parts
    )

    candidate_modules = dict(old_index.modules)
    changed_imports = []
    source_evidence = None

    if deleted:
        candidate_modules.pop(module_id, None)
    else:
        prepared = _i2a_prepare(
            new_root / changed_path, module_id
        )
        assert not prepared.has_error

        changed_imports = prepared.new_imports
        source_evidence = (
            prepared.typing_guard_source_evidence
        )

        prior = candidate_modules.get(module_id)

        if prior is None:
            candidate_modules[module_id] = Module(
                module_id=module_id,
                path=changed_path,
                absolute_path=str(
                    (new_root / changed_path).resolve()
                ),
                imports=changed_imports,
            )
        else:
            candidate_modules[module_id] = replace(
                prior,
                imports=list(changed_imports),
            )

    previous_imports = {
        key: tuple(
            (ref, tuple(ref.names))
            for ref in module.imports
        )
        for key, module in old_index.modules.items()
    }

    previous_evidence = old_index.typing_guard_evidence

    before_candidate_names = {
        key: tuple(
            tuple(ref.names)
            for ref in refs
        )
        for key, refs in previous_evidence[
            "candidate_imports_by_module"
        ].items()
    }

    classified, evidence = (
        reclassify_incremental_type_only(
            candidate_modules,
            previous_modules=old_index.modules,
            previous_evidence=previous_evidence,
            changed_module_id=module_id,
            changed_source_path=changed_path,
            changed_imports=changed_imports,
            changed_source_evidence=source_evidence,
            deleted=deleted,
        )
    )

    assert evidence["schema_version"] == 2
    assert set(classified) == set(new_index.modules)

    assert all(
        classified[key].imports
        == new_index.modules[key].imports
        for key in new_index.modules
    )

    trie = build_trie(classified.keys())
    package_root = detect_package_root(classified, trie)

    candidate_graph = build_graph(
        classified,
        trie=trie,
        package_root=package_root,
        reexport_facts_by_module=(
            materialize_reexport_facts_by_module(
                classified,
                new_index.reference_facts_by_module,
            )
        ),
    )

    assert (
        candidate_graph.hard_edges
        == new_graph.hard_edges
    )
    assert (
        candidate_graph.soft_edges
        == new_graph.soft_edges
    )

    assert evidence[
        "global_policy_satisfied"
    ] == new_index.typing_guard_evidence[
        "global_policy_satisfied"
    ]

    assert (
        old_index.typing_guard_evidence
        == previous_evidence
    )

    assert all(
        tuple(
            (ref, tuple(ref.names))
            for ref in old_index.modules[key].imports
        ) == old_imports
        for key, old_imports in previous_imports.items()
    )

    assert {
        key: tuple(
            tuple(ref.names)
            for ref in refs
        )
        for key, refs in previous_evidence[
            "candidate_imports_by_module"
        ].items()
    } == before_candidate_names

    return classified, evidence, old_index, new_index


def test_sp_t4_i2b4_t35_safe_module_change(
    tmp_path, isolated_dirs
):
    final = {
        **_I1_SAFE,
        "pkg/c.py": "pass\nVALUE = 2\n",
    }
    _i2b4_verify_case(
        tmp_path, _I1_SAFE, final, "pkg/c.py"
    )


def test_sp_t4_i2b4_t36_new_typing_shadow(
    tmp_path, isolated_dirs
):
    final = {
        **_I1_SAFE,
        "typing.py": "pass\n",
    }
    classified, _, _, _ = _i2b4_verify_case(
        tmp_path, _I1_SAFE, final, "typing.py"
    )
    assert not _i2b3_guarded_import(
        classified
    ).type_only


def test_sp_t4_i2b4_t37_deleted_shadow_restores_soft(
    tmp_path, isolated_dirs
):
    initial = {
        **_I1_SAFE,
        "typing.py": "pass\n",
    }
    classified, _, _, _ = _i2b4_verify_case(
        tmp_path,
        initial,
        _I1_SAFE,
        "typing.py",
        deleted=True,
    )
    assert _i2b3_guarded_import(
        classified
    ).type_only


def test_sp_t4_i2b4_t38_parent_becomes_active(
    tmp_path, isolated_dirs
):
    final = {
        **_I1_SAFE,
        "pkg/__init__.py": "import typing\n",
    }
    classified, _, _, _ = _i2b4_verify_case(
        tmp_path,
        _I1_SAFE,
        final,
        "pkg/__init__.py",
    )
    assert not _i2b3_guarded_import(
        classified
    ).type_only


def test_sp_t4_i2b4_t39_parent_restored(
    tmp_path, isolated_dirs
):
    initial = {
        **_I1_SAFE,
        "pkg/__init__.py": "import typing\n",
    }
    classified, _, _, _ = _i2b4_verify_case(
        tmp_path,
        initial,
        _I1_SAFE,
        "pkg/__init__.py",
    )
    assert _i2b3_guarded_import(
        classified
    ).type_only


def test_sp_t4_i2b4_t40_marker_mutation_other_module(
    tmp_path, isolated_dirs
):
    final = {
        **_I1_SAFE,
        "pkg/c.py": (
            "import typing\n"
            "typing.TYPE_CHECKING = True\n"
        ),
    }
    classified, evidence, _, _ = _i2b4_verify_case(
        tmp_path, _I1_SAFE, final, "pkg/c.py"
    )
    assert not evidence["global_policy_satisfied"]
    assert not _i2b3_guarded_import(
        classified
    ).type_only


def test_sp_t4_i2b4_t41_opaque_effect_other_module(
    tmp_path, isolated_dirs
):
    final = {
        **_I1_SAFE,
        "pkg/c.py": "eval('0')\n",
    }
    classified, evidence, _, _ = _i2b4_verify_case(
        tmp_path, _I1_SAFE, final, "pkg/c.py"
    )
    assert not evidence["global_policy_satisfied"]
    assert not _i2b3_guarded_import(
        classified
    ).type_only


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "legacy",
        "wrong-fingerprint",
        "wrong-candidate",
    ],
    ids=[
        "missing",
        "legacy",
        "fingerprint",
        "candidate",
    ],
)
def test_sp_t4_i2b4_t42_invalid_evidence_fails_closed(
    tmp_path, isolated_dirs, damage
):
    from contextor.core.analysis.incremental.type_only_policy import (
        reclassify_incremental_type_only,
    )

    root = write_synthetic_repository(
        tmp_path / "repo", _I1_SAFE
    )
    baseline, _ = _index_graph(root)
    evidence = dict(baseline.typing_guard_evidence)

    if damage == "missing":
        evidence = None
    elif damage == "legacy":
        evidence["schema_version"] = 1
    elif damage == "wrong-fingerprint":
        marker = dict(
            evidence["marker_mutation_by_module"]
        )
        marker["pkg.a"] = (False, "invalid")
        evidence["marker_mutation_by_module"] = marker
    else:
        raw = dict(
            evidence["candidate_imports_by_module"]
        )
        raw["pkg.a"] = (
            ImportRef(
                "pkg.z",
                0,
                [],
                False,
                type_only=True,
            ),
        )
        evidence["candidate_imports_by_module"] = raw

    changed = root / "pkg/c.py"
    changed.write_text(
        "pass\nVALUE = 2\n", encoding="utf-8"
    )

    prepared = _i2a_prepare(changed, "pkg.c")
    assert not prepared.has_error

    candidate = dict(baseline.modules)
    candidate["pkg.c"] = replace(
        candidate["pkg.c"],
        imports=list(prepared.new_imports),
    )

    classified, new_evidence = (
        reclassify_incremental_type_only(
            candidate,
            previous_modules=baseline.modules,
            previous_evidence=evidence,
            changed_module_id="pkg.c",
            changed_source_path="pkg/c.py",
            changed_imports=prepared.new_imports,
            changed_source_evidence=(
                prepared.typing_guard_source_evidence
            ),
        )
    )

    assert new_evidence == {}
    assert not any(
        ref.type_only
        for module in classified.values()
        for ref in module.imports
    )
    assert _i2b3_guarded_import(
        baseline.modules
    ).type_only


def test_sp_t4_i2b4_t43_skipped_recovers(
    tmp_path, isolated_dirs
):
    initial = {
        **_I1_SAFE,
        "broken.py": "def invalid(:\n",
    }
    final = {
        **_I1_SAFE,
        "broken.py": "pass\n",
    }

    classified, evidence, _, _ = _i2b4_verify_case(
        tmp_path,
        initial,
        final,
        "broken.py",
    )

    assert evidence["skipped_source_paths"] == ()
    assert _i2b3_guarded_import(
        classified
    ).type_only


def test_sp_t4_i2b4_t44_no_input_mutation_on_benign_change(
    tmp_path, isolated_dirs
):
    final = {
        **_I1_SAFE,
        "pkg/c.py": "pass\nVALUE = 2\n",
    }

    classified, evidence, old, _ = (
        _i2b4_verify_case(
            tmp_path,
            _I1_SAFE,
            final,
            "pkg/c.py",
        )
    )

    assert evidence is not old.typing_guard_evidence

    assert (
        evidence["candidate_imports_by_module"]
        is not old.typing_guard_evidence[
            "candidate_imports_by_module"
        ]
    )

    assert _i2b3_guarded_import(
        classified
    ).type_only


@pytest.mark.parametrize(
    "invalid_value", [1, "true", 0],
)
def test_sp_t4_i2b4c_t45_malformed_saved_candidate(
    tmp_path, isolated_dirs, invalid_value,
):
    from contextor.core.analysis.incremental.type_only_policy import (
        reclassify_incremental_type_only,
    )

    initial = {
        **_I1_SAFE,
        "typing.py": "pass\n",
    }
    root = write_synthetic_repository(
        tmp_path / "repo", initial
    )
    baseline, _ = _index_graph(root)

    evidence = dict(baseline.typing_guard_evidence)
    candidates = dict(
        evidence["candidate_imports_by_module"]
    )
    candidates["pkg.a"] = tuple(
        replace(ref, type_only=invalid_value)
        if ref.type_only else ref
        for ref in candidates["pkg.a"]
    )
    evidence["candidate_imports_by_module"] = candidates

    modules = dict(baseline.modules)
    modules.pop("typing")

    classified, updated = reclassify_incremental_type_only(
        modules,
        previous_modules=baseline.modules,
        previous_evidence=evidence,
        changed_module_id="typing",
        changed_source_path="typing.py",
        changed_imports=[],
        changed_source_evidence=None,
        deleted=True,
    )

    assert updated == {}
    assert all(
        ref.type_only is False
        for module in classified.values()
        for ref in module.imports
    )


def test_sp_t4_i2b4c_t46_malformed_changed_import(
    tmp_path, isolated_dirs,
):
    from contextor.core.analysis.incremental.type_only_policy import (
        reclassify_incremental_type_only,
    )

    root = write_synthetic_repository(
        tmp_path / "repo", _I1_SAFE
    )
    baseline, _ = _index_graph(root)
    prepared = _i2a_prepare(root / "pkg/a.py", "pkg.a")

    malformed = [
        replace(ref, type_only=1)
        if ref.type_only else ref
        for ref in prepared.new_imports
    ]
    assert any(
        type(ref.type_only) is int
        for ref in malformed
    )

    modules = dict(baseline.modules)
    modules["pkg.a"] = replace(
        modules["pkg.a"],
        imports=list(malformed),
    )

    classified, updated = reclassify_incremental_type_only(
        modules,
        previous_modules=baseline.modules,
        previous_evidence=baseline.typing_guard_evidence,
        changed_module_id="pkg.a",
        changed_source_path="pkg/a.py",
        changed_imports=malformed,
        changed_source_evidence=(
            prepared.typing_guard_source_evidence
        ),
    )

    assert updated == {}
    assert all(
        ref.type_only is False
        for module in classified.values()
        for ref in module.imports
    )


def test_sp_t4_i2b4c_t47_malformed_previous_final(
    tmp_path, isolated_dirs,
):
    from contextor.core.analysis.incremental.type_only_policy import (
        reclassify_incremental_type_only,
    )

    root = write_synthetic_repository(
        tmp_path / "repo", _I1_SAFE
    )
    baseline, _ = _index_graph(root)

    previous = dict(baseline.modules)
    previous["pkg.a"] = replace(
        previous["pkg.a"],
        imports=[
            replace(ref, type_only=1)
            if ref.type_only else ref
            for ref in previous["pkg.a"].imports
        ],
    )

    prepared = _i2a_prepare(root / "pkg/c.py", "pkg.c")
    classified, updated = reclassify_incremental_type_only(
        dict(previous),
        previous_modules=previous,
        previous_evidence=baseline.typing_guard_evidence,
        changed_module_id="pkg.c",
        changed_source_path="pkg/c.py",
        changed_imports=prepared.new_imports,
        changed_source_evidence=(
            prepared.typing_guard_source_evidence
        ),
    )

    assert updated == {}
    assert all(
        ref.type_only is False
        for module in classified.values()
        for ref in module.imports
    )


def test_sp_t4_i2b4c_t48_unrelated_module_tampering(
    tmp_path, isolated_dirs,
):
    from contextor.core.analysis.incremental.type_only_policy import (
        reclassify_incremental_type_only,
    )

    root = write_synthetic_repository(
        tmp_path / "repo", _I1_SAFE
    )
    baseline, _ = _index_graph(root)

    modules = dict(baseline.modules)
    modules["pkg.a"] = replace(
        modules["pkg.a"],
        imports=[
            replace(ref, type_only=False)
            if ref.type_only else ref
            for ref in modules["pkg.a"].imports
        ],
    )

    prepared = _i2a_prepare(root / "pkg/c.py", "pkg.c")
    classified, updated = reclassify_incremental_type_only(
        modules,
        previous_modules=baseline.modules,
        previous_evidence=baseline.typing_guard_evidence,
        changed_module_id="pkg.c",
        changed_source_path="pkg/c.py",
        changed_imports=prepared.new_imports,
        changed_source_evidence=(
            prepared.typing_guard_source_evidence
        ),
    )

    assert updated == {}
    assert all(
        ref.type_only is False
        for module in classified.values()
        for ref in module.imports
    )

