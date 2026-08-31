"""Parity coverage for the run-scoped TestContextIndex reverse lookups."""

from pathlib import Path

from contextor.core.analysis.test_context import (
    TestContextIndex,
    TestFileInfo as _TestFileInfo,
    find_test_files,
)


def _legacy_find_test_files(index: TestContextIndex, module_id: str) -> list[str]:
    """Reference implementation of the pre-0J6 query semantics."""
    short_name = module_id.split(".")[-1]
    candidates = (f"test_{short_name}.py", f"{short_name}_test.py")
    found = [
        str(directory / candidate)
        for directory, file_names in index.test_dirs.items()
        for candidate in candidates
        if candidate in file_names
    ]
    for info in index.files_info.values():
        if any(
            imported == module_id or imported.startswith(f"{module_id}.")
            for imported in info.imported_modules
        ):
            found.append(info.path)
    return sorted(set(found))


def _fixture_index(tmp_path: Path) -> TestContextIndex:
    root = tmp_path / "repo"
    directories = {
        root: frozenset({"test_root.py", "root_test.py"}),
        root / "tests": frozenset(
            {
                "test_alpha.py",
                "alpha_test.py",
                "test_alphabeta.py",
                "import_only.py",
                "test_both.py",
            }
        ),
        root / "test": frozenset({"test_alpha.py", "child_test.py"}),
        root / "specs": frozenset({"test_alpha.py", "custom.py"}),
    }
    infos = {
        str(root / "tests" / "test_alpha.py"): _TestFileInfo(
            path=str(root / "tests" / "test_alpha.py"),
            filename="test_alpha.py",
            directory=root / "tests",
            imported_modules={"pkg.alpha"},
            names=set(),
            has_assertions=True,
        ),
        str(root / "tests" / "alpha_test.py"): _TestFileInfo(
            path=str(root / "tests" / "alpha_test.py"),
            filename="alpha_test.py",
            directory=root / "tests",
            imported_modules={"pkg.alpha.child.deep"},
            names=set(),
            has_assertions=True,
        ),
        str(root / "test" / "child_test.py"): _TestFileInfo(
            path=str(root / "test" / "child_test.py"),
            filename="child_test.py",
            directory=root / "test",
            imported_modules={"pkg.alpha.child"},
            names=set(),
            has_assertions=True,
        ),
        str(root / "tests" / "test_alphabeta.py"): _TestFileInfo(
            path=str(root / "tests" / "test_alphabeta.py"),
            filename="test_alphabeta.py",
            directory=root / "tests",
            imported_modules={"pkg.alphabeta"},
            names=set(),
            has_assertions=True,
        ),
        str(root / "tests" / "import_only.py"): _TestFileInfo(
            path=str(root / "tests" / "import_only.py"),
            filename="import_only.py",
            directory=root / "tests",
            imported_modules={"other.pkg"},
            names=set(),
            has_assertions=True,
        ),
        str(root / "tests" / "test_both.py"): _TestFileInfo(
            path=str(root / "tests" / "test_both.py"),
            filename="test_both.py",
            directory=root / "tests",
            imported_modules={"pkg.both"},
            names=set(),
            has_assertions=True,
        ),
    }
    return TestContextIndex(root, directories, infos)


def test_reverse_lookup_preserves_filename_import_prefix_and_dedupe_semantics(tmp_path):
    index = _fixture_index(tmp_path)
    queries = [
        "pkg.alpha",
        "pkg.alpha.child",
        "pkg.alpha.child.deep",
        "pkg.alphabeta",
        "pkg.alph",
        "other.pkg",
        "pkg.both",
        "missing.module",
    ]

    for module_id in queries:
        assert index.find_test_files(module_id) == _legacy_find_test_files(index, module_id)

    assert str(index.root_path / "tests" / "test_alpha.py") in index.find_test_files("pkg.alpha")
    assert str(index.root_path / "test" / "child_test.py") in index.find_test_files("pkg.alpha")
    assert str(index.root_path / "tests" / "alpha_test.py") in index.find_test_files("pkg.alpha")
    assert str(index.root_path / "tests" / "test_alphabeta.py") not in index.find_test_files("pkg.alpha")
    assert index.find_test_files("pkg.both").count(str(index.root_path / "tests" / "test_both.py")) == 1


def test_reverse_lookup_supports_root_standard_and_explicit_custom_directories(tmp_path):
    index = _fixture_index(tmp_path)

    assert index.find_test_files("root") == sorted(
        {
            str(index.root_path / "test_root.py"),
            str(index.root_path / "root_test.py"),
        }
    )
    assert index.find_test_files("root") == _legacy_find_test_files(index, "root")
    assert index.find_test_files("alpha") == _legacy_find_test_files(index, "alpha")
    assert str(index.root_path / "specs" / "test_alpha.py") in index.find_test_files("alpha")


def test_reverse_lookup_uses_one_run_scoped_snapshot_without_files_info_scan(tmp_path):
    index = _fixture_index(tmp_path)

    class ValuesMustNotBeRead(dict):
        def values(self):
            raise AssertionError("find_test_files must use the reverse lookup")

    index.files_info = ValuesMustNotBeRead(index.files_info)
    assert index.find_test_files("pkg.alpha") == sorted(
        {
            str(index.root_path / "tests" / "test_alpha.py"),
            str(index.root_path / "test" / "test_alpha.py"),
            str(index.root_path / "specs" / "test_alpha.py"),
            str(index.root_path / "tests" / "alpha_test.py"),
            str(index.root_path / "test" / "child_test.py"),
        }
    )


def test_explicit_custom_directory_build_and_compatibility_wrappers_match(tmp_path):
    root = tmp_path / "repo"
    custom = root / "specs"
    custom.mkdir(parents=True)
    source = custom / "custom.py"
    source.write_text(
        "from pkg.custom import Target\n\nassert Target\n",
        encoding="utf-8",
    )
    test_dirs = {custom: frozenset({"custom.py"})}

    index = TestContextIndex.build(root, test_dirs=test_dirs)
    expected = [str(source)]
    assert index.find_test_files("pkg.custom") == expected
    assert find_test_files("pkg.custom", str(root), test_dirs=test_dirs) == expected
    assert find_test_files(
        "pkg.custom", str(root), test_dirs=test_dirs, test_index=index
    ) == expected
