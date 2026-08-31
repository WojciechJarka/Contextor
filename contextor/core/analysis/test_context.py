"""
contextor/core/analysis/test_context.py

TEST DISCOVERY ENGINE

Layer: FACT EXTRACTION

Heuristically searches for test files associated with the module
and checks which public symbols are used in them.

Does not guarantee full coverage - this is convention detection,
not code coverage analysis.

Conventions detected:
    tests/test_<name>.py
    tests/<name>_test.py
    test_<name>.py      (in module directory)
    <name>_test.py      (in module directory)
    tests/test_<name>/  (test packages)
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contextor.core.paths import DEFAULT_IGNORED_DIRS
from contextor.core.source import parse_source


# ==========================================================
# TEST FILE DISCOVERY
# ==========================================================


def _module_short_name(module_id: str) -> str:
    """
    Extracts short module name from module_id.
    Example: 'core.function_analysis' -> 'function_analysis'
    """
    return module_id.split(".")[-1]


TEST_DIR_NAMES = ("tests", "test")


def _is_test_context_directory(root: Path, directory: Path) -> bool:
    return directory == root or directory.name in TEST_DIR_NAMES


def is_test_context_candidate(root_path: str | Path, file_path: str | Path) -> bool:
    """Return whether a path is a current TestContextIndex candidate."""
    root = Path(root_path).resolve()
    path = Path(file_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return False
    if path.suffix != ".py" or not _is_test_context_directory(root, path.parent):
        return False
    if path.parent == root:
        return path.name.startswith("test_") or path.name.endswith("_test.py")
    return True


def discover_test_dirs(
    root_path: str,
    allowed_python_paths: list[str] | None = None,
) -> dict[Path, frozenset[str]]:
    """
    Locates every test directory in the repository and lists its files.

    Test layout is a property of the repository, not of an individual
    module, so callers analyzing many modules should call this once and
    pass the result into find_test_files(). Rediscovering per module
    meant a full recursive filesystem walk for each analyzed file.

    One walk collects both the directories and their file names, so
    find_test_files() answers from memory instead of issuing two
    exists() probes per directory per module.

    When ``allowed_python_paths`` is provided, discovery is derived only from
    that already-filtered AST index. This keeps test coverage aligned with
    per-analysis excludes and avoids a second repository walk.

    Returns {directory: frozenset(file names)}.
    """
    root = Path(root_path).resolve()

    if allowed_python_paths is not None:
        listings: dict[Path, set[str]] = {root: set()}
        for item in allowed_python_paths:
            path = Path(item)
            if not path.is_absolute():
                path = root / path
            path = path.resolve()
            try:
                path.relative_to(root)
            except ValueError:
                continue
            if path.suffix != ".py":
                continue
            directory = path.parent
            if _is_test_context_directory(root, directory):
                listings.setdefault(directory, set()).add(path.name)
        return {
            directory: frozenset(file_names)
            for directory, file_names in listings.items()
        }

    listings: dict[Path, frozenset[str]] = {}

    for current, dir_names, file_names in os.walk(root):
        # Same exclusions the indexer applies, so a vendored 'tests'
        # directory inside .venv is not mistaken for the project's own.
        dir_names[:] = [name for name in dir_names if name not in DEFAULT_IGNORED_DIRS]

        directory = Path(current)

        if _is_test_context_directory(root, directory):
            listings[directory] = frozenset(file_names)

    listings.setdefault(root, frozenset())

    return listings


# ==========================================================
# SINGLE-PASS AST FACT EXTRACTION
# ==========================================================


def _extract_test_file_facts(tree: ast.AST | None) -> tuple[set[str], set[str], bool]:
    """
    Extracts in a single AST walk:
    - imported_modules: for import-based test file discovery (Import and ImportFrom level=0)
    - names: for tested symbol matching (imports, calls, attributes, names)
    - has_assertions: whether the test contains assert statements or assert* calls
    """
    if tree is None:
        return set(), set(), False

    imported_modules: set[str] = set()
    names: set[str] = set()
    has_assertions = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
                names.add(alias.name)
                if alias.asname:
                    names.add(alias.asname)

        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                imported_modules.add(node.module)
            for alias in node.names:
                names.add(alias.name)
                if alias.asname:
                    names.add(alias.asname)

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
                if node.func.attr.startswith("assert"):
                    has_assertions = True

        elif isinstance(node, ast.Assert):
            has_assertions = True

        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

        elif isinstance(node, ast.Name):
            names.add(node.id)

    return imported_modules, names, has_assertions


def _collect_names_from_file(file_path: str) -> tuple[set[str], bool]:
    """
    Collects all names used in the test file:
    - imports
    - function calls
    - attributes

    Heuristic - this is not flow analysis.
    Maintained for direct backward compatibility.
    """
    try:
        tree = parse_source(file_path)
    except Exception:
        return set(), False

    _, names, has_assertions = _extract_test_file_facts(tree)
    return names, has_assertions


# ==========================================================
# RUN-SCOPED TEST CONTEXT INDEX
# ==========================================================


@dataclass(frozen=True)
class TestFileInfo:
    """Pre-extracted facts for a single test file."""

    path: str
    filename: str
    directory: Path
    imported_modules: set[str]
    names: set[str]
    has_assertions: bool


class TestContextIndex:
    """
    Run-scoped precomputed index of test files and their AST facts.

    Eliminates N x T repeated filesystem reads and AST parsing during
    repository analysis runs.
    """

    __test__ = False

    def __init__(
        self,
        root_path: str | Path,
        test_dirs: dict[Path, frozenset[str]],
        files_info: dict[str, TestFileInfo],
    ):
        self.root_path = Path(root_path).resolve()
        self.test_dirs = test_dirs
        self.files_info = files_info
        self._paths_by_filename: dict[str, set[str]] = {}
        for directory, file_names in test_dirs.items():
            for file_name in file_names:
                self._paths_by_filename.setdefault(file_name, set()).add(
                    str(directory / file_name)
                )

        self._paths_by_import_prefix: dict[str, set[str]] = {}
        for info in files_info.values():
            for imported_module in info.imported_modules:
                lookup_keys = {imported_module}
                lookup_keys.update(
                    imported_module[:position]
                    for position, character in enumerate(imported_module)
                    if character == "."
                )
                for lookup_key in lookup_keys:
                    self._paths_by_import_prefix.setdefault(lookup_key, set()).add(
                        info.path
                    )

    @classmethod
    def build(
        cls,
        root_path: str | Path,
        test_dirs: dict[Path, frozenset[str]] | None = None,
        modules: dict[str, Any] | None = None,
        allowed_python_paths: list[str] | None = None,
        test_facts_by_path: dict[str, dict] | None = None,
    ) -> TestContextIndex:
        """
        Builds the test context index by discovering test files and extracting
        AST facts at most once per test file.
        """
        root = Path(root_path).resolve()
        discovered_test_dirs = test_dirs is None
        if test_dirs is None:
            test_dirs = discover_test_dirs(
                str(root), allowed_python_paths=allowed_python_paths
            )

        # Index known module objects by resolved path for zero-parse AST reuse
        module_by_path: dict[str, Any] = {}
        if modules:
            for mod in modules.values():
                abs_path = getattr(mod, "absolute_path", None) or getattr(
                    mod, "path", None
                )
                if abs_path:
                    module_by_path[str(Path(abs_path).resolve())] = mod

        files_info: dict[str, TestFileInfo] = {}

        for directory, file_names in test_dirs.items():
            if discovered_test_dirs:
                candidate_names = [
                    name
                    for name in file_names
                    if is_test_context_candidate(root, directory / name)
                ]
            elif directory == root:
                candidate_names = [
                    name
                    for name in file_names
                    if name.startswith("test_") or name.endswith("_test.py")
                ]
            else:
                candidate_names = [name for name in file_names if name.endswith(".py")]

            for name in candidate_names:
                test_path = str(directory / name)
                if test_path in files_info:
                    continue

                normalized_path = str(Path(test_path).resolve())
                supplied_facts = (test_facts_by_path or {}).get(normalized_path)
                if (
                    isinstance(supplied_facts, dict)
                    and set(supplied_facts) == {
                        "imported_modules",
                        "names",
                        "has_assertions",
                    }
                    and isinstance(supplied_facts["imported_modules"], list)
                    and all(isinstance(item, str) for item in supplied_facts["imported_modules"])
                    and isinstance(supplied_facts["names"], list)
                    and all(isinstance(item, str) for item in supplied_facts["names"])
                    and isinstance(supplied_facts["has_assertions"], bool)
                ):
                    imported_modules = set(supplied_facts["imported_modules"])
                    names = set(supplied_facts["names"])
                    has_assertions = supplied_facts["has_assertions"]
                else:
                    tree = None
                    mod = module_by_path.get(normalized_path)
                    if mod is not None:
                        tree = getattr(mod, "ast_tree", None)

                    if tree is None:
                        try:
                            tree = parse_source(test_path)
                        except Exception:
                            tree = None

                    imported_modules, names, has_assertions = _extract_test_file_facts(tree)
                files_info[test_path] = TestFileInfo(
                    path=test_path,
                    filename=name,
                    directory=directory,
                    imported_modules=imported_modules,
                    names=names,
                    has_assertions=has_assertions,
                )

        return cls(root_path=root, test_dirs=test_dirs, files_info=files_info)

    def find_test_files(self, module_id: str) -> list[str]:
        """
        Searches for test files associated with module_id using the precomputed index.
        """
        short_name = _module_short_name(module_id)
        candidates = (
            f"test_{short_name}.py",
            f"{short_name}_test.py",
        )

        found: set[str] = set()
        for candidate in candidates:
            found.update(self._paths_by_filename.get(candidate, ()))
        found.update(self._paths_by_import_prefix.get(module_id, ()))

        return sorted(found)

    def extract_tested_symbols(
        self,
        test_files: list[str],
        public_symbols: list[str],
    ) -> list[str]:
        """
        Checks which public_symbols are used in test files using pre-extracted facts.
        """
        if not test_files or not public_symbols:
            return []

        all_names: set[str] = set()
        has_valid_assertions = False

        for tf in test_files:
            info = self.files_info.get(tf)
            if info is not None:
                all_names.update(info.names)
                if info.has_assertions:
                    has_valid_assertions = True
            else:
                names, assertions = _collect_names_from_file(tf)
                all_names.update(names)
                if assertions:
                    has_valid_assertions = True

        if not has_valid_assertions:
            return []

        tested = []
        for symbol in public_symbols:
            short = symbol.split(".")[-1]
            if short in all_names or symbol in all_names:
                tested.append(symbol)

        return sorted(tested)

    def build_test_context(
        self,
        module_id: str,
        public_symbols: list[str] | None,
    ) -> dict[str, Any]:
        """
        Builds the test context payload for a single module.
        """
        test_files = self.find_test_files(module_id)
        tested = self.extract_tested_symbols(test_files, public_symbols or [])
        untested = sorted(s for s in (public_symbols or []) if s not in tested)

        return {
            "test_files": test_files,
            "tested_symbols": tested,
            "untested_public_symbols": untested,
        }


def build_test_context_index(
    root_path: str | Path,
    test_dirs: dict[Path, frozenset[str]] | None = None,
    modules: dict[str, Any] | None = None,
    allowed_python_paths: list[str] | None = None,
    test_facts_by_path: dict[str, dict] | None = None,
) -> TestContextIndex:
    """
    Public factory function for constructing a TestContextIndex.
    """
    return TestContextIndex.build(
        root_path=root_path,
        test_dirs=test_dirs,
        modules=modules,
        allowed_python_paths=allowed_python_paths,
        test_facts_by_path=test_facts_by_path,
    )


# ==========================================================
# PUBLIC API (BACKWARD COMPATIBLE WRAPPERS)
# ==========================================================


def find_test_files(
    module_id: str,
    root_path: str,
    test_dirs: dict | None = None,
    test_index: TestContextIndex | None = None,
) -> list[str]:
    """
    Searches for test files associated with the module.

    Searches in:
    - tests/ and test/ directory in root
    - tests/ and test/ directories in subdirectories
    - directory where the module itself resides

    Returns a sorted list of paths as strings.
    """
    if test_index is not None:
        return test_index.find_test_files(module_id)

    index = TestContextIndex.build(root_path, test_dirs=test_dirs)
    return index.find_test_files(module_id)


def extract_tested_symbols(
    test_files: list,
    public_symbols: list,
    test_index: TestContextIndex | None = None,
) -> list[str]:
    """
    Checks which public_symbols are used in test files.

    Returns a list of symbols found in tests
    (heuristic detection - does not guarantee 100% accuracy).
    """
    if test_index is not None:
        return test_index.extract_tested_symbols(test_files, public_symbols or [])

    if not test_files or not public_symbols:
        return []

    all_names = set()
    has_valid_assertions = False
    for tf in test_files:
        names, has_assertions = _collect_names_from_file(tf)
        all_names.update(names)
        if has_assertions:
            has_valid_assertions = True

    if not has_valid_assertions:
        return []

    tested = []
    for symbol in public_symbols:
        short = symbol.split(".")[-1]
        if short in all_names or symbol in all_names:
            tested.append(symbol)

    return sorted(tested)


def build_test_context(
    module_id: str,
    root_path: str,
    public_symbols: list,
    test_dirs: dict | None = None,
    allowed_python_paths: list[str] | None = None,
    test_index: TestContextIndex | None = None,
) -> dict:
    """
    Link: discovery + symbol matching.

    Returns:
    {
        "test_files": [...],
        "tested_symbols": [...],
        "untested_public_symbols": [...]
    }
    """
    if not root_path:
        return {
            "test_files": [],
            "tested_symbols": [],
            "untested_public_symbols": list(public_symbols or []),
        }

    if test_index is not None:
        return test_index.build_test_context(module_id, public_symbols or [])

    if test_dirs is None and allowed_python_paths is not None:
        test_dirs = discover_test_dirs(
            root_path, allowed_python_paths=allowed_python_paths
        )

    index = TestContextIndex.build(
        root_path, test_dirs=test_dirs, allowed_python_paths=allowed_python_paths
    )
    return index.build_test_context(module_id, public_symbols or [])
