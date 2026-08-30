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
from contextor.core.reference.index import extract_compact_reference_facts
from contextor.core.source import SourceError, parse_source
from contextor.core.symbol_engine.extractor import extract_file_symbols
from contextor.core.validator.collisions import (
    COLLISION_FACT_KEYS,
    extract_module_collision_facts,
    extract_repository_collision_facts,
)


SYMBOL_FACTS_SCHEMA_VERSION = 1
REFERENCE_FACTS_SCHEMA_VERSION = 1
COLLISION_FACTS_SCHEMA_VERSION = 1
_SYMBOL_FACTS_AVAILABLE = "available"
_SYMBOL_FACTS_FAILURE = "failure"
_SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
_COLLISION_FACTS_AVAILABLE = "available"
_COLLISION_TYPES = frozenset({"class", "function", "variable"})
_COLLISION_FACT_FIELDS = frozenset(COLLISION_FACT_KEYS)
_SYMBOL_FACT_FIELDS = frozenset(
    {
        "classes",
        "functions",
        "methods",
        "globals",
        "calls",
        "assignments",
        "signatures",
        "body_fingerprints",
        "errors",
    }
)


def _valid_symbol_facts(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("schema_version") == SYMBOL_FACTS_SCHEMA_VERSION
        and value.get("status") == _SYMBOL_FACTS_AVAILABLE
        and isinstance(value.get("facts"), dict)
        and set(value["facts"]) == _SYMBOL_FACT_FIELDS
    )


def _valid_reference_facts(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("schema_version") == REFERENCE_FACTS_SCHEMA_VERSION
        and value.get("status") == "available"
        and isinstance(value.get("facts"), dict)
    )


def _valid_collision_fact_list(value: object, module_id: str) -> bool:
    if not isinstance(value, list):
        return False
    for fact in value:
        if not isinstance(fact, dict) or set(fact) != _COLLISION_FACT_FIELDS:
            return False
        if fact.get("name") is None or not isinstance(fact.get("name"), str):
            return False
        if fact.get("type") not in _COLLISION_TYPES:
            return False
        if fact.get("file") != module_id:
            return False
        if not isinstance(fact.get("file_path"), str) or not isinstance(fact.get("code"), str):
            return False
        if not all(
            isinstance(fact.get(field), int) or fact.get(field) is None
            for field in ("line_start", "line_end", "col_start", "col_end")
        ):
            return False
    return True


def _valid_collision_facts(value: object, module_id: str) -> bool:
    return (
        isinstance(value, dict)
        and value.get("schema_version") == COLLISION_FACTS_SCHEMA_VERSION
        and value.get("status") == _COLLISION_FACTS_AVAILABLE
        and _valid_collision_fact_list(value.get("facts"), module_id)
    )


def _extract_collision_facts(tree: ast.AST, module_id: str, path: Path) -> list[dict]:
    """Return cache/IPC-safe collision facts while the current AST is live."""
    return [
        fact.copy()
        for fact in extract_module_collision_facts(tree, module_id, str(path.resolve()))
    ]


def assemble_collision_facts_or_fallback(
    modules: dict[str, Module], collision_facts_by_module: dict[str, list[dict]] | None
) -> dict[str, list[dict]]:
    """Accept only complete indexed facts; otherwise preserve AST fallback semantics."""
    facts = collision_facts_by_module or {}
    if set(facts) == set(modules) and all(
        _valid_collision_fact_list(facts.get(module_id), module_id)
        for module_id in modules
    ):
        return facts
    return extract_repository_collision_facts(modules)


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


def read_imports(
    file_path: Path,
    *,
    tree: ast.AST | None = None,
) -> tuple[list[ImportRef] | None, str | None]:
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
        if tree is None:
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

    rel = path.relative_to(Path(root_str))
    module_id = ".".join(rel.with_suffix("").parts)

    # Próba odczytu z cache
    cache = _cache_manager(root_str)
    cached_data = cache.get(path)

    symbol_facts = None
    reference_facts = None
    collision_facts = None
    collision_facts_status = None
    if cached_data is not None:
        error = cached_data.get("error")
        imports = None if error else [ImportRef(**imp) for imp in cached_data.get("imports", [])]

        cached_facts = cached_data.get("symbol_facts") if not error else None
        cached_reference_facts = cached_data.get("reference_facts") if not error else None
        cached_collision_facts = cached_data.get("collision_facts") if not error else None
        if _valid_symbol_facts(cached_facts):
            symbol_facts = cached_facts
        if _valid_reference_facts(cached_reference_facts):
            reference_facts = cached_reference_facts
        if _valid_collision_facts(cached_collision_facts, module_id):
            collision_facts = cached_collision_facts
            collision_facts_status = _COLLISION_FACTS_AVAILABLE

        if not error and (
            symbol_facts is None
            or reference_facts is None
            or collision_facts is None
        ):
            try:
                tree = parse_source(path)
            except SourceError as exc:
                if symbol_facts is None:
                    symbol_facts = {
                        "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
                        "status": _SYMBOL_FACTS_FAILURE,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    }
                if reference_facts is None:
                    reference_facts = {
                        "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                        "status": "failure",
                        "facts": None,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                if collision_facts is None:
                    collision_facts_status = "failure"
            else:
                if symbol_facts is None:
                    try:
                        migrated_facts = extract_file_symbols(path, tree=tree)
                    except Exception as exc:
                        symbol_facts = {
                            "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
                            "status": _SYMBOL_FACTS_FAILURE,
                            "exception_type": type(exc).__name__,
                            "message": str(exc),
                        }
                    else:
                        symbol_facts = {
                            "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
                            "status": _SYMBOL_FACTS_AVAILABLE,
                            "facts": migrated_facts,
                        }
                if reference_facts is None:
                    extracted_reference = extract_compact_reference_facts(
                        module_id, tree=tree, imports=imports
                    )
                    reference_facts = {
                        "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                        **extracted_reference,
                        }
                if collision_facts is None:
                    try:
                        extracted_collision_facts = _extract_collision_facts(
                            tree, module_id, path
                        )
                    except Exception:
                        collision_facts_status = "failure"
                    else:
                        collision_facts = {
                            "schema_version": COLLISION_FACTS_SCHEMA_VERSION,
                            "status": _COLLISION_FACTS_AVAILABLE,
                            "facts": extracted_collision_facts,
                        }
                        collision_facts_status = _COLLISION_FACTS_AVAILABLE
                rewritten = dict(cached_data)
                if collision_facts is None:
                    rewritten.pop("collision_facts", None)
                if _valid_symbol_facts(symbol_facts):
                    rewritten["symbol_facts"] = symbol_facts
                if _valid_reference_facts(reference_facts):
                    rewritten["reference_facts"] = reference_facts
                if _valid_collision_facts(collision_facts, module_id):
                    rewritten["collision_facts"] = collision_facts
                cache.set(path, rewritten)
    else:
        try:
            tree = parse_source(path)
        except SourceError as exc:
            imports, error = None, str(exc)
        else:
            imports, error = read_imports(path, tree=tree)
            if error is None:
                try:
                    extracted_facts = extract_file_symbols(path, tree=tree)
                    symbol_facts = {
                        "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
                        "status": _SYMBOL_FACTS_AVAILABLE,
                        "facts": extracted_facts,
                    }
                except Exception as exc:
                    symbol_facts = {
                        "schema_version": SYMBOL_FACTS_SCHEMA_VERSION,
                        "status": _SYMBOL_FACTS_FAILURE,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    }
                extracted_reference = extract_compact_reference_facts(
                    module_id, tree=tree, imports=imports
                )
                reference_facts = {
                    "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                    **extracted_reference,
                }
                try:
                    extracted_collision_facts = _extract_collision_facts(
                        tree, module_id, path
                    )
                except Exception:
                    collision_facts_status = "failure"
                else:
                    collision_facts = {
                        "schema_version": COLLISION_FACTS_SCHEMA_VERSION,
                        "status": _COLLISION_FACTS_AVAILABLE,
                        "facts": extracted_collision_facts,
                    }
                    collision_facts_status = _COLLISION_FACTS_AVAILABLE
        cache_data = {
            "imports": [dataclasses.asdict(imp) for imp in imports or []],
            "error": error,
        }
        if symbol_facts and symbol_facts.get("status") == _SYMBOL_FACTS_AVAILABLE:
            cache_data["symbol_facts"] = symbol_facts
        if _valid_reference_facts(reference_facts):
            cache_data["reference_facts"] = reference_facts
        if _valid_collision_facts(collision_facts, module_id):
            cache_data["collision_facts"] = collision_facts
        cache.set(path, cache_data)

    return {
        "module_id": module_id,
        "path": str(rel),
        "absolute_path": str(path.resolve()),
        "imports": imports,
        "error": error,
        "filename": path.name,
        "symbol_facts": symbol_facts,
        "reference_facts": reference_facts,
        "collision_facts": collision_facts,
        "collision_facts_status": collision_facts_status,
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

    symbol_facts_by_module: dict[str, dict] = dataclasses.field(default_factory=dict)

    reference_facts_by_module: dict[str, dict] = dataclasses.field(default_factory=dict)

    collision_facts_by_module: dict[str, list[dict]] = dataclasses.field(default_factory=dict)


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
    symbol_facts_by_module: dict[str, dict] = {}
    reference_facts_by_module: dict[str, dict] = {}
    collision_facts_by_module: dict[str, list[dict]] = {}

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
                if res.get("symbol_facts") is not None:
                    symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
                if res.get("reference_facts") is not None:
                    reference_facts_by_module[res["module_id"]] = res["reference_facts"]
                cached_collision_facts = res.get("collision_facts")
                if _valid_collision_facts(cached_collision_facts, res["module_id"]):
                    collision_facts_by_module[res["module_id"]] = cached_collision_facts["facts"]
            completed += 1
            checkpoint(progress_callback, res["filename"], completed, total_files)
        return RepositoryIndex(
            modules=modules,
            skipped=sorted(skipped, key=lambda item: item.path),
            symbol_facts_by_module=symbol_facts_by_module,
            reference_facts_by_module=reference_facts_by_module,
            collision_facts_by_module=collision_facts_by_module,
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
                if res.get("symbol_facts") is not None:
                    symbol_facts_by_module[res["module_id"]] = res["symbol_facts"]
                if res.get("reference_facts") is not None:
                    reference_facts_by_module[res["module_id"]] = res["reference_facts"]
                cached_collision_facts = res.get("collision_facts")
                if _valid_collision_facts(cached_collision_facts, res["module_id"]):
                    collision_facts_by_module[res["module_id"]] = cached_collision_facts["facts"]

            completed += 1
            try:
                checkpoint(progress_callback, res["filename"], completed, total_files)
            except AnalysisCancelled:
                executor.shutdown(wait=False, cancel_futures=True)
                raise

    return RepositoryIndex(
        modules=modules,
        skipped=sorted(skipped, key=lambda item: item.path),
        symbol_facts_by_module=symbol_facts_by_module,
        reference_facts_by_module=reference_facts_by_module,
        collision_facts_by_module=collision_facts_by_module,
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
