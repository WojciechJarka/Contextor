"""
Test-file discovery.

Discovery walks the repository once and answers per-module queries from
that listing, instead of re-walking the tree and issuing exists() probes
for every analyzed module.
"""

from contextor.core.analysis.test_context import (
    build_test_context,
    discover_test_dirs,
    find_test_files,
)


def _repo(tmp_path, files):
    for relative, content in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return tmp_path


def test_finds_tests_at_any_depth(tmp_path):
    root = _repo(
        tmp_path,
        {
            "tests/test_alpha.py": "",
            "src/tests/test_beta.py": "",
            "src/deep/nested/test/gamma_test.py": "",
        },
    )

    test_dirs = discover_test_dirs(str(root))

    assert find_test_files("pkg.alpha", str(root), test_dirs)
    assert find_test_files("pkg.beta", str(root), test_dirs)
    assert find_test_files("pkg.gamma", str(root), test_dirs)


def test_finds_tests_beside_the_module_in_root(tmp_path):
    root = _repo(tmp_path, {"test_alpha.py": ""})

    assert find_test_files("alpha", str(root))


def test_unknown_module_has_no_tests(tmp_path):
    root = _repo(tmp_path, {"tests/test_alpha.py": ""})

    assert find_test_files("pkg.nothing", str(root)) == []


def test_ignores_vendored_test_directories(tmp_path):
    """
    A 'tests' directory inside .venv belongs to a dependency, not to the
    project under analysis.
    """

    root = _repo(tmp_path, {".venv/lib/pkg/tests/test_alpha.py": ""})

    assert find_test_files("pkg.alpha", str(root)) == []


def test_discovery_result_is_reusable_across_modules(tmp_path):
    root = _repo(tmp_path, {"tests/test_alpha.py": "", "tests/test_beta.py": ""})

    test_dirs = discover_test_dirs(str(root))

    first = find_test_files("pkg.alpha", str(root), test_dirs)
    second = find_test_files("pkg.beta", str(root), test_dirs)

    assert first != second
    assert find_test_files("pkg.alpha", str(root), test_dirs) == first


def test_context_marks_symbols_covered_by_assertions(tmp_path):
    root = _repo(
        tmp_path,
        {
            "tests/test_alpha.py": "from pkg.alpha import Engine\n\n\ndef test_it():\n    assert Engine()\n"
        },
    )

    context = build_test_context("pkg.alpha", str(root), ["Engine", "Unused"])

    assert context["tested_symbols"] == ["Engine"]
    assert context["untested_public_symbols"] == ["Unused"]


def test_context_without_assertions_counts_nothing_as_tested(tmp_path):
    root = _repo(tmp_path, {"tests/test_alpha.py": "from pkg.alpha import Engine\n\nEngine()\n"})

    context = build_test_context("pkg.alpha", str(root), ["Engine"])

    assert context["tested_symbols"] == []
