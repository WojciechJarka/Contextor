"""
contextor/core/test_context.py

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

import ast
import os
from pathlib import Path

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


def discover_test_dirs(root_path: str) -> dict:
    """
    Locates every test directory in the repository and lists its files.

    Test layout is a property of the repository, not of an individual
    module, so callers analyzing many modules should call this once and
    pass the result into find_test_files(). Rediscovering per module
    meant a full recursive filesystem walk for each analyzed file.

    One walk collects both the directories and their file names, so
    find_test_files() answers from memory instead of issuing two
    exists() probes per directory per module.

    Returns {directory: frozenset(file names)}.
    """

    root = Path(root_path)

    listings: dict = {}

    for current, dir_names, file_names in os.walk(root):
        # Same exclusions the indexer applies, so a vendored 'tests'
        # directory inside .venv is not mistaken for the project's own.
        dir_names[:] = [name for name in dir_names if name not in DEFAULT_IGNORED_DIRS]

        directory = Path(current)

        if directory == root or directory.name in TEST_DIR_NAMES:
            listings[directory] = frozenset(file_names)

    listings.setdefault(root, frozenset())

    return listings


def find_test_files(module_id: str, root_path: str, test_dirs: dict | None = None) -> list:
    """
    Searches for test files associated with the module.

    Searches in:
    - tests/ and test/ directory in root
    - tests/ and test/ directories in subdirectories
    - directory where the module itself resides

    Returns a sorted list of paths as strings.
    """

    short_name = _module_short_name(module_id)

    candidates = (
        f"test_{short_name}.py",
        f"{short_name}_test.py",
    )

    if test_dirs is None:
        test_dirs = discover_test_dirs(root_path)

    found = [
        str(directory / candidate)
        for directory, file_names in test_dirs.items()
        for candidate in candidates
        if candidate in file_names
    ]

    # Deduplication
    return sorted(set(found))


# ==========================================================
# SYMBOL DETECTION IN TESTS
# ==========================================================


def _collect_names_from_file(file_path: str) -> tuple[set, bool]:
    """
    Collects all names used in the test file:
    - imports
    - function calls
    - attributes

    Heuristic - this is not flow analysis.
    """

    try:
        tree = parse_source(file_path)
    except Exception:
        return set(), False

    names = set()
    has_assertions = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
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

    return names, has_assertions


def extract_tested_symbols(
    test_files: list,
    public_symbols: list,
) -> list:
    """
    Checks which public_symbols are used in test files.

    Returns a list of symbols found in tests
    (heuristic detection - does not guarantee 100% accuracy).
    """

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

    # Compare by short name (without class)
    tested = []
    for symbol in public_symbols:
        short = symbol.split(".")[-1]
        if short in all_names or symbol in all_names:
            tested.append(symbol)

    return sorted(tested)


# ==========================================================
# PUBLIC API
# ==========================================================


def build_test_context(
    module_id: str,
    root_path: str,
    public_symbols: list,
    test_dirs: dict | None = None,
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

    test_files = find_test_files(module_id, root_path, test_dirs=test_dirs)
    tested = extract_tested_symbols(test_files, public_symbols or [])
    untested = sorted(s for s in (public_symbols or []) if s not in tested)

    return {
        "test_files": test_files,
        "tested_symbols": tested,
        "untested_public_symbols": untested,
    }
