"""
tests/test_test_context_h1_equivalence.py

H1 Equivalence and Complexity Verification Tests for Test Context Engine.

Verifies:
1. Semantic equivalence between uncached and cached execution across multiple module classes.
2. O(T) parse complexity constraint (no repeated parsing of test files per target module).
"""

from pathlib import Path
from contextor.core.analysis import test_context as tc_mod
from contextor.core.analysis.test_context import (
    TestContextIndex,
    build_test_context,
    build_test_context_index,
    discover_test_dirs,
    find_test_files,
    extract_tested_symbols,
)


def _setup_fixture_repo(tmp_path: Path) -> Path:
    files = {
        # 1. Target with conventional test + extra import test
        "pkg/engine.py": "class Engine:\n    pass\nclass Worker:\n    pass\nclass UnusedEngine:\n    pass\n",
        "tests/test_engine.py": "from pkg.engine import Engine\n\ndef test_engine():\n    assert Engine()\n",
        "tests/test_integration.py": "from pkg.engine import Worker\n\ndef test_integration():\n    assert Worker()\n",

        # 2. Target with nonconventional test (import-only matching)
        "pkg/standalone.py": "class StandaloneService:\n    pass\n",
        "tests/test_custom_service.py": "import pkg.standalone\n\ndef test_custom():\n    assert pkg.standalone.StandaloneService()\n",

        # 3. Target with no tests whatsoever
        "pkg/untested.py": "class BlackBox:\n    pass\nclass Secret:\n    pass\n",

        # 4. Target with test file that lacks assertions
        "pkg/no_assert.py": "class NoAssertItem:\n    pass\n",
        "tests/test_no_assert.py": "from pkg.no_assert import NoAssertItem\n\ndef test_run():\n    NoAssertItem()\n",

        # 5. Test module as target
        "tests/test_dummy.py": "def test_something():\n    assert True\n",
    }

    for rel_path, content in files.items():
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return tmp_path


def test_uncached_vs_cached_equivalence(tmp_path):
    root = _setup_fixture_repo(tmp_path)
    root_str = str(root)

    test_dirs = discover_test_dirs(root_str)
    test_index = build_test_context_index(root_str, test_dirs=test_dirs)

    test_cases = [
        # Target 1: Conventional + integration test
        ("pkg.engine", ["Engine", "Worker", "UnusedEngine"]),
        # Target 2: Nonconventional import test
        ("pkg.standalone", ["StandaloneService"]),
        # Target 3: Completely untested
        ("pkg.untested", ["BlackBox", "Secret"]),
        # Target 4: Test without assertions
        ("pkg.no_assert", ["NoAssertItem"]),
        # Target 5: Test file itself
        ("tests.test_engine", ["test_engine"]),
        # Target 6: Non-existent / empty symbols
        ("pkg.unknown", []),
    ]

    for module_id, public_symbols in test_cases:
        # 1. Uncached invocation (standalone fallback)
        uncached_res = build_test_context(
            module_id,
            root_str,
            public_symbols,
            test_dirs=test_dirs,
            test_index=None,
        )

        # 2. Cached invocation via prebuilt TestContextIndex
        cached_res = build_test_context(
            module_id,
            root_str,
            public_symbols,
            test_dirs=test_dirs,
            test_index=test_index,
        )

        # 3. Direct TestContextIndex method
        direct_index_res = test_index.build_test_context(
            module_id,
            public_symbols,
        )

        # Exact equivalence assertions
        assert uncached_res == cached_res, f"Mismatch for module {module_id}: uncached != cached"
        assert cached_res == direct_index_res, f"Mismatch for module {module_id}: cached != direct_index"

    # Specific semantic checks on engine results
    engine_res = test_index.build_test_context("pkg.engine", ["Engine", "Worker", "UnusedEngine"])
    assert len(engine_res["test_files"]) == 2
    assert str(root / "tests" / "test_engine.py") in engine_res["test_files"]
    assert str(root / "tests" / "test_integration.py") in engine_res["test_files"]
    assert engine_res["tested_symbols"] == ["Engine", "Worker"]
    assert engine_res["untested_public_symbols"] == ["UnusedEngine"]

    # Specific semantic checks on untested
    untested_res = test_index.build_test_context("pkg.untested", ["BlackBox", "Secret"])
    assert untested_res["test_files"] == []
    assert untested_res["tested_symbols"] == []
    assert untested_res["untested_public_symbols"] == ["BlackBox", "Secret"]

    # Specific semantic checks on no assertions
    no_assert_res = test_index.build_test_context("pkg.no_assert", ["NoAssertItem"])
    assert len(no_assert_res["test_files"]) == 1
    assert no_assert_res["tested_symbols"] == []
    assert no_assert_res["untested_public_symbols"] == ["NoAssertItem"]


def test_complexity_o_t_ast_parses(tmp_path, monkeypatch):
    """
    Validates that N target modules analyzing T test files results in O(T) AST parses,
    NOT O(N * T) parses.
    """
    root = _setup_fixture_repo(tmp_path)
    root_str = str(root)

    # Count test files in repo fixture
    test_files = list((root / "tests").glob("*.py"))
    t_count = len(test_files)
    assert t_count == 5

    # Create 10 target modules to evaluate
    n_targets = [f"pkg.module_{i}" for i in range(10)]
    for i in range(10):
        mod_file = root / "pkg" / f"module_{i}.py"
        mod_file.write_text(f"class Model{i}:\n    pass\n", encoding="utf-8")

    parse_counts = {"count": 0, "parsed_files": []}
    orig_parse_source = tc_mod.parse_source

    def _tracking_parse_source(file_path):
        parse_counts["count"] += 1
        parse_counts["parsed_files"].append(str(file_path))
        return orig_parse_source(file_path)

    monkeypatch.setattr(tc_mod, "parse_source", _tracking_parse_source)

    # 1. Build index once
    test_dirs = discover_test_dirs(root_str)
    test_index = build_test_context_index(root_str, test_dirs=test_dirs)

    # At this point, each of the T test files should have been parsed at most once
    parses_after_index_build = parse_counts["count"]
    assert parses_after_index_build <= t_count, f"Index build did {parses_after_index_build} parses, expected <= {t_count}"

    # 2. Query test context for all N=10 target modules using the index
    for target in n_targets:
        res = build_test_context(
            target,
            root_str,
            ["Model0"],
            test_dirs=test_dirs,
            test_index=test_index,
        )
        assert isinstance(res, dict)

    # Assert: ZERO additional parses occurred during the N=10 target queries
    parses_after_all_queries = parse_counts["count"]
    assert parses_after_all_queries == parses_after_index_build, (
        f"Repeated AST parses detected! Total parses: {parses_after_all_queries}, "
        f"after build: {parses_after_index_build}. Expected 0 parses during N queries."
    )
