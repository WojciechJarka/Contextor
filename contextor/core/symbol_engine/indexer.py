"""
core/indexer.py

AST → RAW IMPORTS with depth-scope support.

Differentiates between:
- global imports
- local imports (inside functions/closures)

Builds stable module_id against project root.
"""

import ast
import dataclasses
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.domain.imports import (
    ImportRef,
)
from contextor.core.domain.module import (
    Module,
)
from contextor.core.errors import AnalysisCancelled, checkpoint
from contextor.core.paths import DEFAULT_IGNORED_DIRS
from contextor.core.source import SourceError, parse_source


# ==========================================================
# IMPORT EXTRACTION
# ==========================================================


class AdvancedImportVisitor(ast.NodeVisitor):
    """
    Przechodzi AST zachowując informację
    o głębokości funkcji.

    Pozwala rozróżnić:

    import x

    oraz:

    def f():
        import x
    """

    def __init__(self):

        self.found_imports: list[ImportRef] = []

        self._in_function_depth = 0

    def visit_FunctionDef(self, node):

        self._in_function_depth += 1

        self.generic_visit(node)

        self._in_function_depth -= 1

    def visit_AsyncFunctionDef(self, node):

        self.visit_FunctionDef(node)

    def visit_Import(self, node):

        is_local = self._in_function_depth > 0

        for item in node.names:
            self.found_imports.append(
                ImportRef(
                    module=item.name,
                    level=0,
                    names=[],
                    is_from_import=False,
                    is_local=is_local,
                )
            )

    def visit_ImportFrom(self, node):

        is_local = self._in_function_depth > 0

        names = [item.name for item in node.names]

        self.found_imports.append(
            ImportRef(
                module=node.module,
                level=node.level or 0,
                names=names,
                is_from_import=True,
                is_local=is_local,
            )
        )


def read_imports(file_path: Path) -> tuple[list[ImportRef] | None, str | None]:
    """
    Ekstrakcja surowych importów AST.

    Returns (imports, error). `imports is None` means the file is not
    readable Python and must not become a module: a file with no imports
    and a file that could not be parsed are entirely different facts, and
    collapsing both into an empty list let binaries, JSON and text files
    that merely end in '.py' enter the dependency graph as real modules
    with no dependencies.
    """

    try:
        tree = parse_source(file_path)

    except SourceError as exc:
        return None, str(exc)

    visitor = AdvancedImportVisitor()

    visitor.visit(tree)

    return visitor.found_imports, None


def extract_imports(file_path: Path) -> list[ImportRef]:
    """
    Backwards-compatible wrapper returning imports only.
    """

    imports, _ = read_imports(file_path)

    return imports or []


# One CacheManager per worker process. Building it per file meant a
# directory check for every source file in the repository.
_CACHE_MANAGERS: dict[str, CacheManager] = {}


def _cache_manager(root_str: str) -> CacheManager:
    manager = _CACHE_MANAGERS.get(root_str)

    if manager is None:
        manager = CacheManager(root_str)
        _CACHE_MANAGERS[root_str] = manager

    return manager


def _process_single_file(path_str: str, root_str: str) -> dict:
    """Funkcja pomocnicza dla wieloprocesowości."""
    path = Path(path_str)

    # Próba odczytu z cache
    cache = _cache_manager(root_str)
    cached_data = cache.get(path)

    if cached_data:
        error = cached_data.get("error")
        imports = None if error else [ImportRef(**imp) for imp in cached_data.get("imports", [])]
    else:
        imports, error = read_imports(path)
        cache.set(
            path,
            {
                "imports": [dataclasses.asdict(imp) for imp in imports or []],
                "error": error,
            },
        )

    rel = path.relative_to(Path(root_str))
    module_id = ".".join(rel.with_suffix("").parts)

    return {
        "module_id": module_id,
        "path": str(rel),
        "absolute_path": str(path.resolve()),
        "imports": imports,
        "error": error,
        "filename": path.name,
    }


# ==========================================================
# INDEX BUILDER
# ==========================================================


@dataclasses.dataclass(frozen=True)
class SkippedFile:
    """
    A '.py' path that is not analyzable Python, and why.
    """

    path: str

    reason: str

    line_number: int | None = None

    column_number: int | None = None


def _syntax_error_location(reason: str | None) -> tuple[int | None, int | None]:
    """Extract parser coordinates while preserving the readable reason."""
    match = re.search(r"\(line (\d+)(?:, column (\d+))?:", reason or "")
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2)) if match.group(2) else None


@dataclasses.dataclass(frozen=True)
class RepositoryIndex:
    """
    Result of indexing: the modules, plus what was left out.

    Skipped files are carried alongside rather than discarded, so a
    report can state what it does not cover instead of quietly
    presenting a partial picture as complete.
    """

    modules: dict[str, Module]

    skipped: list[SkippedFile]


def index_repository(
    root: str, excludes: list[str] = None, extra_ignored_dirs: set = None, progress_callback=None
) -> RepositoryIndex:
    """
    Buduje indeks modułów projektu wraz z listą pominiętych plików.
    """

    root_path = Path(root).resolve()

    if not root_path.exists():
        raise ValueError(f"Repository root does not exist: {root_path}")

    if not root_path.is_dir():
        raise ValueError(f"Repository root is not directory: {root_path}")

    modules: dict[str, Module] = {}
    skipped: list[SkippedFile] = []

    ignored_dirs = set(DEFAULT_IGNORED_DIRS)

    if extra_ignored_dirs:
        ignored_dirs.update(extra_ignored_dirs)

    files_to_process = []
    for path in root_path.rglob("*.py"):
        # rglob matches directories too, and a directory named 'foo.py'
        # was becoming a module in its own right.
        if not path.is_file():
            continue
        rel = path.relative_to(root_path)
        if any(part in ignored_dirs for part in rel.parts):
            continue
        if excludes:
            rel_str = rel.as_posix()
            is_excluded = False
            for ex in excludes:
                ex_norm = ex.replace("\\", "/")
                if rel_str == ex_norm or rel_str.startswith(ex_norm + "/"):
                    is_excluded = True
                    break
            if is_excluded:
                continue
        files_to_process.append(path)

    total_files = len(files_to_process)
    if progress_callback:
        progress_callback(0, total_files, "Start...")

    completed = 0
    if os.environ.get("CONTEXTOR_DISABLE_PROCESS_POOL") == "1":
        for path in files_to_process:
            res = _process_single_file(str(path), str(root_path))
            if res["error"]:
                line_number, column_number = _syntax_error_location(res["error"])
                skipped.append(
                    SkippedFile(
                        path=res["path"],
                        reason=res["error"],
                        line_number=line_number,
                        column_number=column_number,
                    )
                )
            else:
                modules[res["module_id"]] = Module(
                    module_id=res["module_id"],
                    path=res["path"],
                    absolute_path=res.get("absolute_path", res["path"]),
                    imports=res["imports"],
                )
            completed += 1
            checkpoint(progress_callback, res["filename"], completed, total_files)
        return RepositoryIndex(
            modules=modules,
            skipped=sorted(skipped, key=lambda item: item.path),
        )

    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(_process_single_file, str(p), str(root_path)): p
            for p in files_to_process
        }

        for future in as_completed(futures):
            res = future.result()

            if res["error"]:
                line_number, column_number = _syntax_error_location(res["error"])
                skipped.append(
                    SkippedFile(
                        path=res["path"],
                        reason=res["error"],
                        line_number=line_number,
                        column_number=column_number,
                    )
                )
            else:
                modules[res["module_id"]] = Module(
                    module_id=res["module_id"],
                    path=res["path"],
                    absolute_path=res.get("absolute_path", res["path"]),
                    imports=res["imports"],
                )

            completed += 1
            try:
                checkpoint(progress_callback, res["filename"], completed, total_files)
            except AnalysisCancelled:
                executor.shutdown(wait=False, cancel_futures=True)
                raise

    return RepositoryIndex(
        modules=modules,
        skipped=sorted(skipped, key=lambda item: item.path),
    )


def build_index(
    root: str, excludes: list[str] = None, extra_ignored_dirs: set = None, progress_callback=None
) -> dict[str, Module]:
    """
    Buduje indeks modułów projektu.

    Klucz:
        module_id

    Wartość:
        Module

    Use index_repository() when the list of skipped files matters.
    """

    return index_repository(
        root,
        excludes=excludes,
        extra_ignored_dirs=extra_ignored_dirs,
        progress_callback=progress_callback,
    ).modules
