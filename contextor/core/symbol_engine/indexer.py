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
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from contextor.core.analysis.cache_manager import CacheManager
from contextor.core.analysis.process_pool_lifecycle import (
    managed_process_pool,
    terminate_process_pool,
)
from contextor.core.analysis.lineage_extraction import (
    deserialize_extracted_lineage_source_facts,
    extract_lineage_source_facts,
    serialize_extracted_lineage_source_facts,
)
from contextor.core.analysis.test_context import (
    _extract_test_file_facts,
    is_test_context_candidate,
)
from contextor.core.domain.imports import (
    ImportRef,
)
from contextor.core.domain.lineage_facts import ExtractedLineageSourceFacts
from contextor.core.domain.module import (
    Module,
)
from contextor.core.errors import AnalysisCancelled, checkpoint
from contextor.core.paths import DEFAULT_IGNORED_DIRS
from contextor.core.reference.index import extract_compact_reference_facts
from contextor.core.runtime_trace import trace_event
from contextor.core.source import (
    SourceError,
    parse_source,
    parse_source_snapshot,
    read_source_snapshot,
)
from contextor.core.symbol_engine.extractor import extract_file_symbols
from contextor.core.validator.collisions import (
    COLLISION_FACT_KEYS,
    extract_module_collision_facts,
    extract_repository_collision_facts,
)


# Semantic contract version for SymbolFacts, not only serialized JSON shape.
# Bump this whenever extractor classification semantics change, even when the
# persisted fact keys and value types remain unchanged.
SYMBOL_FACTS_SCHEMA_VERSION = 2
REFERENCE_FACTS_SCHEMA_VERSION = 1
COLLISION_FACTS_SCHEMA_VERSION = 1
TEST_FACTS_SCHEMA_VERSION = 1
_SYMBOL_FACTS_AVAILABLE = "available"
_SYMBOL_FACTS_FAILURE = "failure"
_SYMBOL_FACTS_NOT_COMPUTED = "not_computed"
_COLLISION_FACTS_AVAILABLE = "available"
_TEST_FACTS_AVAILABLE = "available"
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


def _valid_test_facts(value: object) -> bool:
    if not (
        isinstance(value, dict)
        and value.get("schema_version") == TEST_FACTS_SCHEMA_VERSION
        and value.get("status") == _TEST_FACTS_AVAILABLE
        and isinstance(value.get("facts"), dict)
    ):
        return False
    facts = value["facts"]
    return (
        set(facts) == {"imported_modules", "names", "has_assertions"}
        and isinstance(facts["imported_modules"], list)
        and all(isinstance(item, str) for item in facts["imported_modules"])
        and isinstance(facts["names"], list)
        and all(isinstance(item, str) for item in facts["names"])
        and isinstance(facts["has_assertions"], bool)
    )


def _extract_test_facts(tree: ast.AST | None) -> dict:
    imported_modules, names, has_assertions = _extract_test_file_facts(tree)
    return {
        "schema_version": TEST_FACTS_SCHEMA_VERSION,
        "status": _TEST_FACTS_AVAILABLE,
        "facts": {
            "imported_modules": sorted(imported_modules),
            "names": sorted(names),
            "has_assertions": has_assertions,
        },
    }


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
    source_key = rel.as_posix()
    module_id = ".".join(rel.with_suffix("").parts)

    task_started = time.monotonic()

    source_read_called = False
    source_read_ms = 0.0

    import_extract_called = False
    import_extract_ms = 0.0

    symbol_extract_called = False
    symbol_extract_ms = 0.0

    reference_extract_called = False
    reference_extract_ms = 0.0

    collision_extract_called = False
    collision_extract_ms = 0.0

    test_extract_called = False
    test_extract_ms = 0.0

    cache_set_called = False
    cache_set_ms = 0.0

    def timing_evidence() -> dict[str, object]:
        return {
            "task_total_ms": (
                time.monotonic()
                - task_started
            )
            * 1000.0,
            "source_read_called": source_read_called,
            "source_read_ms": source_read_ms,
            "import_extract_called": import_extract_called,
            "import_extract_ms": import_extract_ms,
            "symbol_extract_called": symbol_extract_called,
            "symbol_extract_ms": symbol_extract_ms,
            "reference_extract_called": reference_extract_called,
            "reference_extract_ms": reference_extract_ms,
            "collision_extract_called": collision_extract_called,
            "collision_extract_ms": collision_extract_ms,
            "test_extract_called": test_extract_called,
            "test_extract_ms": test_extract_ms,
            "cache_set_called": cache_set_called,
            "cache_set_ms": cache_set_ms,
        }

    test_candidate = is_test_context_candidate(root_str, path)

    source_read_called = True
    source_read_started = time.monotonic()

    try:
        source_snapshot = read_source_snapshot(path)
    except SourceError as exc:
        source_read_ms = (
            time.monotonic()
            - source_read_started
        ) * 1000.0
        return {
            "module_id": module_id,
            "path": str(rel),
            "absolute_path": str(path.resolve()),
            "imports": None,
            "error": str(exc),
            "filename": path.name,
            "symbol_facts": None,
            "reference_facts": None,
            "collision_facts": None,
            "collision_facts_status": None,
            "test_facts": None,
            "test_facts_status": None,
            "lineage_facts": None,
            "lineage_extract_ms": 0.0,
            "source_parse_called": False,
            "source_parse_ms": 0.0,
            "source_parse_failed": False,
            "cache_get_called": False,
            "cache_get_ms": 0.0,
            "cache_hit": False,
            "lineage_cache_hit": False,
            "lineage_extract_called": False,
            "automatic_test_context_directory": (
                str(path.parent)
                if test_candidate
                or path.parent == Path(root_str)
                else None
            ),
            **timing_evidence(),
        }

    source_read_ms = (
        time.monotonic()
        - source_read_started
    ) * 1000.0

    cache = _cache_manager(root_str)
    cache_get_started = time.monotonic()
    cached_data = cache.get(path, source_bytes=source_snapshot.raw)
    cache_get_ms = (time.monotonic() - cache_get_started) * 1000.0

    lineage_facts = None
    lineage_cache_hit = False
    cached_lineage_valid = False
    if cached_data is not None:
        lineage_facts = deserialize_extracted_lineage_source_facts(
            cached_data.get("lineage_facts"),
            source_key=source_key,
            source_fingerprint=source_snapshot.source_fingerprint,
        )
        lineage_cache_hit = lineage_facts is not None
        cached_lineage_valid = lineage_facts is not None

    symbol_facts = None
    reference_facts = None
    collision_facts = None
    collision_facts_status = None
    test_facts = None
    test_facts_status = None
    if cached_data is not None:
        error = cached_data.get("error")
        imports = None if error else [ImportRef(**imp) for imp in cached_data.get("imports", [])]

        cached_facts = cached_data.get("symbol_facts") if not error else None
        cached_reference_facts = cached_data.get("reference_facts") if not error else None
        cached_collision_facts = cached_data.get("collision_facts") if not error else None
        cached_test_facts = cached_data.get("test_facts") if not error and test_candidate else None
        if _valid_symbol_facts(cached_facts):
            symbol_facts = cached_facts
        if _valid_reference_facts(cached_reference_facts):
            reference_facts = cached_reference_facts
        if _valid_collision_facts(cached_collision_facts, module_id):
            collision_facts = cached_collision_facts
            collision_facts_status = _COLLISION_FACTS_AVAILABLE
        if _valid_test_facts(cached_test_facts):
            test_facts = cached_test_facts
            test_facts_status = _TEST_FACTS_AVAILABLE

        if (
            not error
            and lineage_facts is not None
            and symbol_facts is not None
            and reference_facts is not None
            and collision_facts is not None
            and (not test_candidate or test_facts is not None)
        ):
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
                "test_facts": test_facts,
                "test_facts_status": test_facts_status,
                "lineage_facts": lineage_facts,
                "lineage_extract_ms": 0.0,
                "source_parse_called": False,
                "source_parse_ms": 0.0,
                "source_parse_failed": False,
                "cache_get_called": True,
                "cache_get_ms": cache_get_ms,
                "cache_hit": True,
                "lineage_cache_hit": True,
                "lineage_extract_called": False,
                "automatic_test_context_directory": (
                    str(path.parent)
                    if test_candidate or path.parent == Path(root_str)
                    else None
                ),
                **timing_evidence(),
            }

    source_parse_started = time.monotonic()
    try:
        parsed_input = parse_source_snapshot(source_snapshot, path)
    except SourceError as exc:
        source_parse_ms = (time.monotonic() - source_parse_started) * 1000.0
        return {
            "module_id": module_id, "path": str(rel),
            "absolute_path": str(path.resolve()), "imports": None,
            "error": str(exc), "filename": path.name,
            "symbol_facts": None, "reference_facts": None,
            "collision_facts": None, "collision_facts_status": None,
            "test_facts": None, "test_facts_status": None,
            "lineage_facts": None, "lineage_extract_ms": 0.0,
            "source_parse_called": True, "source_parse_ms": source_parse_ms,
            "source_parse_failed": True, "cache_get_called": True,
            "cache_get_ms": cache_get_ms, "cache_hit": cached_data is not None,
            "lineage_cache_hit": False, "lineage_extract_called": False,
            "automatic_test_context_directory": (
                str(path.parent) if test_candidate or path.parent == Path(root_str)
                else None
            ),
            **timing_evidence(),
        }

    source_parse_ms = (time.monotonic() - source_parse_started) * 1000.0
    assert parsed_input.source_fingerprint == source_snapshot.source_fingerprint
    tree = parsed_input.tree
    lineage_extract_ms = 0.0
    lineage_extract_called = False
    if lineage_facts is None:
        lineage_extract_called = True
        lineage_extract_started = time.monotonic()
        lineage_facts = extract_lineage_source_facts(
            tree,
            source_key=source_key,
            source_fingerprint=source_snapshot.source_fingerprint,
        )
        lineage_extract_ms = (time.monotonic() - lineage_extract_started) * 1000.0

    if cached_data is not None:
        if not error and (
            not cached_lineage_valid
            or symbol_facts is None
            or reference_facts is None
            or collision_facts is None
            or (test_candidate and test_facts is None)
        ):
            try:
                tree = parsed_input.tree
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
                    symbol_extract_called = True
                    symbol_extract_started = time.monotonic()
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
                    finally:
                        symbol_extract_ms += (
                            time.monotonic()
                            - symbol_extract_started
                        ) * 1000.0
                if reference_facts is None:
                    reference_extract_called = True
                    reference_extract_started = time.monotonic()
                    try:
                        extracted_reference = extract_compact_reference_facts(
                            module_id,
                            tree=tree,
                            imports=imports,
                        )
                    finally:
                        reference_extract_ms += (
                            time.monotonic()
                            - reference_extract_started
                        ) * 1000.0
                    reference_facts = {
                        "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                        **extracted_reference,
                    }
                if collision_facts is None:
                    collision_extract_called = True
                    collision_extract_started = time.monotonic()
                    try:
                        extracted_collision_facts = _extract_collision_facts(
                            tree,
                            module_id,
                            path,
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
                    finally:
                        collision_extract_ms += (
                            time.monotonic()
                            - collision_extract_started
                        ) * 1000.0
                if test_candidate and test_facts is None:
                    test_extract_called = True
                    test_extract_started = time.monotonic()
                    try:
                        test_facts = _extract_test_facts(tree)
                    except Exception:
                        test_facts_status = "failure"
                    else:
                        test_facts_status = _TEST_FACTS_AVAILABLE
                    finally:
                        test_extract_ms += (
                            time.monotonic()
                            - test_extract_started
                        ) * 1000.0
                rewritten = dict(cached_data)
                rewritten["lineage_facts"] = serialize_extracted_lineage_source_facts(
                    lineage_facts
                )
                if collision_facts is None:
                    rewritten.pop("collision_facts", None)
                if _valid_symbol_facts(symbol_facts):
                    rewritten["symbol_facts"] = symbol_facts
                if _valid_reference_facts(reference_facts):
                    rewritten["reference_facts"] = reference_facts
                if _valid_collision_facts(collision_facts, module_id):
                    rewritten["collision_facts"] = collision_facts
                if test_candidate:
                    if _valid_test_facts(test_facts):
                        rewritten["test_facts"] = test_facts
                    else:
                        rewritten.pop("test_facts", None)
                cache_set_called = True
                cache_set_started = time.monotonic()
                try:
                    cache.set(
                        path,
                        rewritten,
                        source_bytes=source_snapshot.raw,
                    )
                finally:
                    cache_set_ms += (
                        time.monotonic()
                        - cache_set_started
                    ) * 1000.0
    else:
        try:
            tree = parsed_input.tree
        except SourceError as exc:
            imports, error = None, str(exc)
        else:
            import_extract_called = True
            import_extract_started = time.monotonic()
            try:
                imports, error = read_imports(
                    path,
                    tree=tree,
                )
            finally:
                import_extract_ms += (
                    time.monotonic()
                    - import_extract_started
                ) * 1000.0

            if error is None:
                symbol_extract_called = True
                symbol_extract_started = time.monotonic()
                try:
                    extracted_facts = extract_file_symbols(
                        path,
                        tree=tree,
                    )
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
                finally:
                    symbol_extract_ms += (
                        time.monotonic()
                        - symbol_extract_started
                    ) * 1000.0
                reference_extract_called = True
                reference_extract_started = time.monotonic()
                try:
                    extracted_reference = extract_compact_reference_facts(
                        module_id,
                        tree=tree,
                        imports=imports,
                    )
                finally:
                    reference_extract_ms += (
                        time.monotonic()
                        - reference_extract_started
                    ) * 1000.0
                reference_facts = {
                    "schema_version": REFERENCE_FACTS_SCHEMA_VERSION,
                    **extracted_reference,
                }
                collision_extract_called = True
                collision_extract_started = time.monotonic()
                try:
                    extracted_collision_facts = _extract_collision_facts(
                        tree,
                        module_id,
                        path,
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
                finally:
                    collision_extract_ms += (
                        time.monotonic()
                        - collision_extract_started
                    ) * 1000.0
                if test_candidate:
                    test_extract_called = True
                    test_extract_started = time.monotonic()
                    try:
                        test_facts = _extract_test_facts(tree)
                    except Exception:
                        test_facts_status = "failure"
                    else:
                        test_facts_status = _TEST_FACTS_AVAILABLE
                    finally:
                        test_extract_ms += (
                            time.monotonic()
                            - test_extract_started
                        ) * 1000.0
        cache_data = {
            "imports": [dataclasses.asdict(imp) for imp in imports or []],
            "error": error,
            "lineage_facts": serialize_extracted_lineage_source_facts(lineage_facts),
        }
        if symbol_facts and symbol_facts.get("status") == _SYMBOL_FACTS_AVAILABLE:
            cache_data["symbol_facts"] = symbol_facts
        if _valid_reference_facts(reference_facts):
            cache_data["reference_facts"] = reference_facts
        if _valid_collision_facts(collision_facts, module_id):
            cache_data["collision_facts"] = collision_facts
        if _valid_test_facts(test_facts):
            cache_data["test_facts"] = test_facts
        cache_set_called = True
        cache_set_started = time.monotonic()
        try:
            cache.set(
                path,
                cache_data,
                source_bytes=source_snapshot.raw,
            )
        finally:
            cache_set_ms += (
                time.monotonic()
                - cache_set_started
            ) * 1000.0

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
        "test_facts": test_facts,
        "test_facts_status": test_facts_status,
        "lineage_facts": lineage_facts,
        "lineage_extract_ms": lineage_extract_ms,
        "source_parse_called": True,
        "source_parse_ms": source_parse_ms,
        "source_parse_failed": False,
        "cache_get_called": True,
        "cache_get_ms": cache_get_ms,
        "cache_hit": cached_data is not None,
        "lineage_cache_hit": lineage_cache_hit,
        "lineage_extract_called": lineage_extract_called,
        "automatic_test_context_directory": (
            str(path.parent)
            if test_candidate or path.parent == Path(root_str)
            else None
        ),
        **timing_evidence(),
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

    lineage_facts_by_source: dict[str, ExtractedLineageSourceFacts] = dataclasses.field(default_factory=dict)

    collision_facts_by_module: dict[str, list[dict]] = dataclasses.field(default_factory=dict)

    test_facts_by_path: dict[str, dict] = dataclasses.field(default_factory=dict)

    automatic_test_dirs: dict[Path, frozenset[str]] = dataclasses.field(default_factory=dict)


def index_repository(
    root: str, excludes: list[str] = None, extra_ignored_dirs: set = None, progress_callback=None
) -> RepositoryIndex:
    """
    Buduje indeks modułów projektu wraz z listą pominiętych plików.
    """

    index_started = time.monotonic()
    root_path = Path(root).resolve()

    if not root_path.exists():
        raise ValueError(f"Repository root does not exist: {root_path}")

    if not root_path.is_dir():
        raise ValueError(f"Repository root is not directory: {root_path}")

    modules: dict[str, Module] = {}
    skipped: list[SkippedFile] = []
    symbol_facts_by_module: dict[str, dict] = {}
    reference_facts_by_module: dict[str, dict] = {}
    lineage_facts_by_source: dict[str, ExtractedLineageSourceFacts] = {}
    file_tasks = 0
    source_parse_calls = 0
    source_parse_failures = 0
    cache_get_calls = 0
    cache_hits = 0
    lineage_cache_hits = 0
    lineage_extract_calls = 0
    source_parse_sum_ms = 0.0
    cache_get_sum_ms = 0.0
    lineage_extract_sum_ms = 0.0
    lineage_extract_slowest: list[tuple[float, str]] = []

    worker_task_sum_ms = 0.0
    worker_task_slowest: list[tuple[float, str]] = []
    cache_miss_slowest: list[tuple[float, str]] = []

    source_read_calls = 0
    source_read_sum_ms = 0.0

    import_extract_calls = 0
    import_extract_sum_ms = 0.0

    symbol_extract_calls = 0
    symbol_extract_sum_ms = 0.0

    reference_extract_calls = 0
    reference_extract_sum_ms = 0.0

    collision_extract_calls = 0
    collision_extract_sum_ms = 0.0

    test_extract_calls = 0
    test_extract_sum_ms = 0.0

    cache_set_calls = 0
    cache_set_sum_ms = 0.0

    file_discovery_ms = 0.0

    pool_scope_ms = 0.0
    pool_enter_ms = 0.0
    pool_submit_ms = 0.0
    parent_future_wait_ms = 0.0
    parent_future_result_ms = 0.0
    parent_merge_ms = 0.0
    parent_progress_ms = 0.0
    pool_shutdown_ms = 0.0

    collision_facts_by_module: dict[str, list[dict]] = {}
    test_facts_by_path: dict[str, dict] = {}
    automatic_test_dir_entries: dict[Path, set[str]] = {root_path: set()}

    def record_automatic_test_context_path(result: dict) -> None:
        directory = result.get("automatic_test_context_directory")
        if directory is not None:
            automatic_test_dir_entries.setdefault(Path(directory), set()).add(
                result["filename"]
            )

    def automatic_test_dirs() -> dict[Path, frozenset[str]]:
        return {
            directory: frozenset(automatic_test_dir_entries[directory])
            for directory in sorted(automatic_test_dir_entries)
        }

    def record_file_task_evidence(result: dict) -> None:
        nonlocal file_tasks
        nonlocal source_parse_calls
        nonlocal source_parse_failures
        nonlocal cache_get_calls
        nonlocal cache_hits
        nonlocal lineage_cache_hits
        nonlocal lineage_extract_calls
        nonlocal source_parse_sum_ms
        nonlocal cache_get_sum_ms
        nonlocal lineage_extract_sum_ms

        nonlocal worker_task_sum_ms
        nonlocal source_read_calls
        nonlocal source_read_sum_ms
        nonlocal import_extract_calls
        nonlocal import_extract_sum_ms
        nonlocal symbol_extract_calls
        nonlocal symbol_extract_sum_ms
        nonlocal reference_extract_calls
        nonlocal reference_extract_sum_ms
        nonlocal collision_extract_calls
        nonlocal collision_extract_sum_ms
        nonlocal test_extract_calls
        nonlocal test_extract_sum_ms
        nonlocal cache_set_calls
        nonlocal cache_set_sum_ms

        file_tasks += 1

        task_total_ms = float(
            result.get(
                "task_total_ms",
                0.0,
            )
        )
        worker_task_sum_ms += task_total_ms
        worker_task_slowest.append(
            (
                task_total_ms,
                result["path"],
            )
        )

        elapsed_ms = float(
            result.get(
                "lineage_extract_ms",
                0.0,
            )
        )
        lineage_extract_sum_ms += elapsed_ms
        lineage_extract_slowest.append(
            (
                elapsed_ms,
                result["path"],
            )
        )

        if result.get("source_parse_called") is True:
            source_parse_calls += 1

        if result.get("source_parse_failed") is True:
            source_parse_failures += 1

        if result.get("cache_get_called") is True:
            cache_get_calls += 1

        if result.get("cache_hit") is True:
            cache_hits += 1

        if result.get("lineage_cache_hit") is True:
            lineage_cache_hits += 1

        if result.get("lineage_extract_called") is True:
            lineage_extract_calls += 1

        source_parse_sum_ms += float(
            result.get(
                "source_parse_ms",
                0.0,
            )
        )

        cache_get_sum_ms += float(
            result.get(
                "cache_get_ms",
                0.0,
            )
        )

        if result.get("source_read_called") is True:
            source_read_calls += 1

        source_read_sum_ms += float(
            result.get(
                "source_read_ms",
                0.0,
            )
        )

        if result.get("import_extract_called") is True:
            import_extract_calls += 1

        import_extract_sum_ms += float(
            result.get(
                "import_extract_ms",
                0.0,
            )
        )

        if result.get("symbol_extract_called") is True:
            symbol_extract_calls += 1

        symbol_extract_sum_ms += float(
            result.get(
                "symbol_extract_ms",
                0.0,
            )
        )

        if result.get("reference_extract_called") is True:
            reference_extract_calls += 1

        reference_extract_sum_ms += float(
            result.get(
                "reference_extract_ms",
                0.0,
            )
        )

        if result.get("collision_extract_called") is True:
            collision_extract_calls += 1

        collision_extract_sum_ms += float(
            result.get(
                "collision_extract_ms",
                0.0,
            )
        )

        if result.get("test_extract_called") is True:
            test_extract_calls += 1

        test_extract_sum_ms += float(
            result.get(
                "test_extract_ms",
                0.0,
            )
        )

        if result.get("cache_set_called") is True:
            cache_set_calls += 1

        cache_set_sum_ms += float(
            result.get(
                "cache_set_ms",
                0.0,
            )
        )

        if (
            result.get("cache_get_called") is True
            and result.get("cache_hit") is not True
        ):
            detail = (
                f"{result['path']}"
                f"|task={task_total_ms:.3f}"
                f"|source_read={float(result.get('source_read_ms', 0.0)):.3f}"
                f"|cache_get={float(result.get('cache_get_ms', 0.0)):.3f}"
                f"|source_parse={float(result.get('source_parse_ms', 0.0)):.3f}"
                f"|lineage={float(result.get('lineage_extract_ms', 0.0)):.3f}"
                f"|imports={float(result.get('import_extract_ms', 0.0)):.3f}"
                f"|symbols={float(result.get('symbol_extract_ms', 0.0)):.3f}"
                f"|references={float(result.get('reference_extract_ms', 0.0)):.3f}"
                f"|collisions={float(result.get('collision_extract_ms', 0.0)):.3f}"
                f"|tests={float(result.get('test_extract_ms', 0.0)):.3f}"
                f"|cache_set={float(result.get('cache_set_ms', 0.0)):.3f}"
            )
            cache_miss_slowest.append(
                (
                    task_total_ms,
                    detail,
                )
            )

            trace_event(
                "ANALYSIS",
                "FULL_ANALYSIS_INDEX_CACHE_MISS_TIMING",
                operation="indexing_cache_miss_timing",
                timing_semantics=(
                    "single_file_task_wall_and_nested_subphases"
                ),
                path=result["path"],
                task_total_ms=task_total_ms,
                source_read_ms=float(
                    result.get(
                        "source_read_ms",
                        0.0,
                    )
                ),
                cache_get_ms=float(
                    result.get(
                        "cache_get_ms",
                        0.0,
                    )
                ),
                source_parse_ms=float(
                    result.get(
                        "source_parse_ms",
                        0.0,
                    )
                ),
                lineage_extract_ms=float(
                    result.get(
                        "lineage_extract_ms",
                        0.0,
                    )
                ),
                import_extract_ms=float(
                    result.get(
                        "import_extract_ms",
                        0.0,
                    )
                ),
                symbol_extract_ms=float(
                    result.get(
                        "symbol_extract_ms",
                        0.0,
                    )
                ),
                reference_extract_ms=float(
                    result.get(
                        "reference_extract_ms",
                        0.0,
                    )
                ),
                collision_extract_ms=float(
                    result.get(
                        "collision_extract_ms",
                        0.0,
                    )
                ),
                test_extract_ms=float(
                    result.get(
                        "test_extract_ms",
                        0.0,
                    )
                ),
                cache_set_ms=float(
                    result.get(
                        "cache_set_ms",
                        0.0,
                    )
                ),
            )

    def emit_index_profile_evidence(execution_mode: str) -> None:
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_INDEX_EVIDENCE",
            operation="indexing_file_tasks",
            execution_mode=execution_mode,
            timing_semantics="aggregate_file_task_not_critical_path",
            file_tasks=file_tasks,
            source_parse_calls=source_parse_calls,
            source_parse_failures=source_parse_failures,
            cache_get_calls=cache_get_calls,
            cache_hits=cache_hits,
            cache_misses=cache_get_calls - cache_hits,
            lineage_cache_hits=lineage_cache_hits,
            lineage_extract_calls=lineage_extract_calls,
            source_parse_sum_ms=source_parse_sum_ms,
            cache_get_sum_ms=cache_get_sum_ms,
            lineage_extract_sum_ms=lineage_extract_sum_ms,
        )

    def emit_lineage_extract_timing() -> None:
        slowest = sorted(lineage_extract_slowest, reverse=True)[:10]
        max_ms = slowest[0][0] if slowest else 0.0
        top10 = ",".join(f"{path}:{elapsed_ms:.3f}" for elapsed_ms, path in slowest)
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_LINEAGE_EXTRACTION",
            elapsed_ms=lineage_extract_sum_ms,
            operation="lineage_extraction",
            timing_semantics="aggregate_file_task_not_critical_path",
            lineage_extract_calls=lineage_extract_calls,
            lineage_cache_hits=lineage_cache_hits,
            result=(
                f"sum_ms={lineage_extract_sum_ms:.3f};max_ms={max_ms:.3f};"
                f"files={len(lineage_extract_slowest)};top10={top10}"
            ),
        )

    def emit_worker_timing_evidence(
        execution_mode: str,
    ) -> None:
        slowest_tasks = sorted(
            worker_task_slowest,
            reverse=True,
        )[:10]

        worker_task_max_ms = (
            slowest_tasks[0][0]
            if slowest_tasks
            else 0.0
        )

        worker_task_top10 = ",".join(
            f"{path}:{elapsed_ms:.3f}"
            for elapsed_ms, path in slowest_tasks
        )

        slowest_misses = sorted(
            cache_miss_slowest,
            reverse=True,
        )[:10]

        cache_miss_top10 = ";".join(
            detail
            for _elapsed_ms, detail in slowest_misses
        )

        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_INDEX_WORKER_TIMING",
            operation="indexing_worker_timing",
            execution_mode=execution_mode,
            timing_semantics=(
                "aggregate_file_task_not_critical_path"
            ),
            file_tasks=file_tasks,
            worker_task_sum_ms=worker_task_sum_ms,
            worker_task_max_ms=worker_task_max_ms,
            worker_task_top10=worker_task_top10,
            source_read_calls=source_read_calls,
            source_read_sum_ms=source_read_sum_ms,
            import_extract_calls=import_extract_calls,
            import_extract_sum_ms=import_extract_sum_ms,
            symbol_extract_calls=symbol_extract_calls,
            symbol_extract_sum_ms=symbol_extract_sum_ms,
            reference_extract_calls=reference_extract_calls,
            reference_extract_sum_ms=reference_extract_sum_ms,
            collision_extract_calls=collision_extract_calls,
            collision_extract_sum_ms=collision_extract_sum_ms,
            test_extract_calls=test_extract_calls,
            test_extract_sum_ms=test_extract_sum_ms,
            cache_set_calls=cache_set_calls,
            cache_set_sum_ms=cache_set_sum_ms,
            cache_miss_task_count=len(
                cache_miss_slowest
            ),
            cache_miss_top10=cache_miss_top10,
        )

    def emit_parent_timing_evidence(
        execution_mode: str,
    ) -> None:
        trace_event(
            "ANALYSIS",
            "FULL_ANALYSIS_INDEX_PARENT_TIMING",
            operation="indexing_parent_timing",
            execution_mode=execution_mode,
            timing_semantics=(
                "critical_path_parent_subphases_partial"
            ),
            index_internal_ms=(
                time.monotonic()
                - index_started
            )
            * 1000.0,
            file_discovery_ms=file_discovery_ms,
            pool_scope_ms=pool_scope_ms,
            pool_enter_ms=pool_enter_ms,
            pool_submit_ms=pool_submit_ms,
            parent_future_wait_ms=(
                parent_future_wait_ms
            ),
            parent_future_result_ms=(
                parent_future_result_ms
            ),
            parent_merge_ms=parent_merge_ms,
            parent_progress_ms=parent_progress_ms,
            pool_shutdown_ms=pool_shutdown_ms,
        )

    ignored_dirs = set(DEFAULT_IGNORED_DIRS)

    if extra_ignored_dirs:
        ignored_dirs.update(extra_ignored_dirs)

    file_discovery_started = time.monotonic()

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

    file_discovery_ms = (
        time.monotonic()
        - file_discovery_started
    ) * 1000.0

    total_files = len(files_to_process)
    if progress_callback:
        progress_callback(0, total_files, "Start...")

    completed = 0
    if os.environ.get("CONTEXTOR_DISABLE_PROCESS_POOL") == "1":
        for path in files_to_process:
            res = _process_single_file(str(path), str(root_path))
            record_file_task_evidence(res)
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
                extracted_lineage = res.get("lineage_facts")
                if extracted_lineage is not None:
                    lineage_facts_by_source[extracted_lineage.source_key] = extracted_lineage
                cached_collision_facts = res.get("collision_facts")
                if _valid_collision_facts(cached_collision_facts, res["module_id"]):
                    collision_facts_by_module[res["module_id"]] = cached_collision_facts["facts"]
                if _valid_test_facts(res.get("test_facts")):
                    test_facts_by_path[str(Path(res["absolute_path"]).resolve())] = res["test_facts"]["facts"]
                record_automatic_test_context_path(res)
            completed += 1
            checkpoint(progress_callback, res["filename"], completed, total_files)
        emit_index_profile_evidence("inline")
        emit_worker_timing_evidence("inline")
        emit_parent_timing_evidence("inline")
        emit_lineage_extract_timing()
        return RepositoryIndex(
            modules=modules,
            skipped=sorted(skipped, key=lambda item: item.path),
            symbol_facts_by_module=symbol_facts_by_module,
            reference_facts_by_module=reference_facts_by_module,
            lineage_facts_by_source=lineage_facts_by_source,
            collision_facts_by_module=collision_facts_by_module,
            test_facts_by_path=test_facts_by_path,
            automatic_test_dirs=automatic_test_dirs(),
        )

    pool_scope_started = time.monotonic()
    pool_enter_started = pool_scope_started

    with managed_process_pool(
        ProcessPoolExecutor,
    ) as executor:
        pool_enter_ms = (
            time.monotonic()
            - pool_enter_started
        ) * 1000.0

        pool_submit_started = time.monotonic()

        futures = {
            executor.submit(
                _process_single_file,
                str(p),
                str(root_path),
            ): p
            for p in files_to_process
        }

        pool_submit_ms = (
            time.monotonic()
            - pool_submit_started
        ) * 1000.0

        wait_started = time.monotonic()

        for future in as_completed(futures):
            parent_future_wait_ms += (
                time.monotonic()
                - wait_started
            ) * 1000.0

            future_result_started = time.monotonic()
            res = future.result()
            parent_future_result_ms += (
                time.monotonic()
                - future_result_started
            ) * 1000.0

            parent_merge_started = time.monotonic()

            record_file_task_evidence(res)

            if res["error"]:
                line_number, column_number = (
                    _syntax_error_location(
                        res["error"]
                    )
                )
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
                    absolute_path=res.get(
                        "absolute_path",
                        res["path"],
                    ),
                    imports=res["imports"],
                )

                if res.get("symbol_facts") is not None:
                    symbol_facts_by_module[
                        res["module_id"]
                    ] = res["symbol_facts"]

                if res.get("reference_facts") is not None:
                    reference_facts_by_module[
                        res["module_id"]
                    ] = res["reference_facts"]

                extracted_lineage = res.get(
                    "lineage_facts"
                )

                if extracted_lineage is not None:
                    lineage_facts_by_source[
                        extracted_lineage.source_key
                    ] = extracted_lineage

                cached_collision_facts = res.get(
                    "collision_facts"
                )

                if _valid_collision_facts(
                    cached_collision_facts,
                    res["module_id"],
                ):
                    collision_facts_by_module[
                        res["module_id"]
                    ] = cached_collision_facts[
                        "facts"
                    ]

                if _valid_test_facts(
                    res.get(
                        "test_facts"
                    )
                ):
                    test_facts_by_path[
                        str(
                            Path(
                                res["absolute_path"]
                            ).resolve()
                        )
                    ] = res["test_facts"][
                        "facts"
                    ]

                record_automatic_test_context_path(
                    res
                )

            parent_merge_ms += (
                time.monotonic()
                - parent_merge_started
            ) * 1000.0

            completed += 1

            progress_started = time.monotonic()

            try:
                checkpoint(
                    progress_callback,
                    res["filename"],
                    completed,
                    total_files,
                )
            except AnalysisCancelled:
                terminate_process_pool(executor)
                raise
            finally:
                parent_progress_ms += (
                    time.monotonic()
                    - progress_started
                ) * 1000.0

            wait_started = time.monotonic()

        pool_body_end = time.monotonic()

    pool_scope_end = time.monotonic()

    pool_scope_ms = (
        pool_scope_end
        - pool_scope_started
    ) * 1000.0

    pool_shutdown_ms = (
        pool_scope_end
        - pool_body_end
    ) * 1000.0

    emit_index_profile_evidence("process_pool")
    emit_worker_timing_evidence("process_pool")
    emit_parent_timing_evidence("process_pool")
    emit_lineage_extract_timing()

    return RepositoryIndex(
        modules=modules,
        skipped=sorted(skipped, key=lambda item: item.path),
        symbol_facts_by_module=symbol_facts_by_module,
        reference_facts_by_module=reference_facts_by_module,
        lineage_facts_by_source=lineage_facts_by_source,
        collision_facts_by_module=collision_facts_by_module,
        test_facts_by_path=test_facts_by_path,
        automatic_test_dirs=automatic_test_dirs(),
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
