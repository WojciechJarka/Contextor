
"""
contextor/core/reference/engine.py

Główny silnik zbierający referencje (Symbol Reference Engine).

NOTE:
Usage detail arrays (`*_detail`) are intentionally capped at
MAX_USAGE_DETAILS to prevent massive I/O bloat in the artifact
usage report.
"""

import re
from pathlib import Path

from contextor.core.source import SourceError, read_source

from .visitor import SymbolReferenceVisitor


# ==========================================================
# PROCESS-LOCAL IDENTIFIER CACHE
# ==========================================================

_IDENTIFIER_CACHE: dict[str, frozenset[str]] = {}

# One stat() per file per analysis instead of one per defining
# module. The repository is treated as a fixed snapshot for
# the duration of an analysis.
_FINGERPRINT_CACHE: dict[str, str | None] = {}

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def reset_caches() -> None:
    """
    Drops cached file state.

    Call at the start of an analysis run.
    """
    _IDENTIFIER_CACHE.clear()
    _FINGERPRINT_CACHE.clear()


def _cache_key(path: Path) -> str | None:
    """
    Identity of a file version: path + mtime + size.
    """
    key = str(path)

    if key in _FINGERPRINT_CACHE:
        return _FINGERPRINT_CACHE[key]

    try:
        stat = path.stat()
        fingerprint = (
            f"{key}|{stat.st_mtime_ns}|{stat.st_size}"
        )
    except OSError:
        fingerprint = None

    _FINGERPRINT_CACHE[key] = fingerprint

    return fingerprint


def _identifiers_for(
    path: Path,
    key: str,
) -> frozenset[str]:
    """
    Returns every identifier-like token appearing in the file.

    String literals are intentionally included because dynamic
    getattr("name") lookups can reference symbols.
    """
    cached = _IDENTIFIER_CACHE.get(key)

    if cached is not None:
        return cached

    try:
        names = frozenset(
            _IDENTIFIER_RE.findall(read_source(path))
        )
    except SourceError:
        names = frozenset()

    _IDENTIFIER_CACHE[key] = names

    return names


def _search_needles(
    bare_symbols: set[str],
    definer_module: str | None,
) -> set[str]:
    """
    Returns identifier tokens that must occur in a source file
    before reference analysis is worth attempting.

    Reference matching operates on either:

        - complete dotted names
        - final symbol components

    Therefore symbol components are sufficient for the textual
    prefilter.

    The defining module is intentionally not added here.
    Import relationships are handled independently below.
    """
    needles: set[str] = set()

    for symbol in bare_symbols:
        needles.update(symbol.split("."))

    return needles


def _empty_reference():
    """
    Creates an empty reference record.

    Each usage category is represented explicitly so downstream
    consumers do not need to infer semantics from missing keys.
    """
    return {
        "called_by": [],
        "called_by_detail": [],
        "callback_called": [],
        "callback_called_detail": [],
        "called_by_ambiguous": [],
        "called_by_ambiguous_detail": [],
        "event_bound_by": [],
        "event_bound_by_detail": [],
        "imported_from": [],
        "inherited_by": [],
        "inherited_by_detail": [],
    }


def _module_path(
    root_path,
    module,
) -> Path:
    """
    Returns the absolute source path of a module.

    The indexer normally stores an already-absolute path.
    Path(root_path) / absolute_path therefore remains absolute.
    """
    raw = (
        getattr(module, "absolute_path", None)
        or module.path
    )

    return Path(root_path) / raw


def _import_matches_symbol(
    imported,
    symbol,
):
    if not imported:
        return False

    if imported == symbol:
        return True

    if imported.endswith("." + symbol):
        return True

    if symbol.endswith("." + imported):
        return True

    return False


# ==========================================================
# NORMALIZATION
# ==========================================================

MAX_USAGE_DETAILS = 15


def _normalize_references(references):
    """
    Deduplicates scalar consumer lists and caps detail lists.

    Detail records remain dictionaries and therefore are not
    converted through set().
    """
    for data in references.values():
        for key, values in data.items():
            if not isinstance(values, list):
                continue

            if key.endswith("_detail"):
                data[key] = values[:MAX_USAGE_DETAILS]
                continue

            if all(isinstance(value, str) for value in values):
                data[key] = sorted(set(values))

    return references


# ==========================================================
# SYMBOL REFERENCE BUILDING
# ==========================================================


def build_symbol_references(
    modules,
    target_symbols,
    root_path,
    definer_module=None,
):
    """
    Builds reference facts for target symbols.

    Usage categories:

        called_by
            Confirmed direct runtime calls.

        callback_called
            Confirmed target callables passed as arguments.

        event_bound_by
            Explicit event/subscription bindings.

        called_by_ambiguous
            Heuristic short-name matches.

        imported_from
            Confirmed imports.

        inherited_by
            Confirmed inheritance relationships.

    Ambiguous matches never become confirmed consumers.
    """
    bare_symbols = set(target_symbols)

    if definer_module:
        qualified_map = {
            f"{definer_module}.{symbol}": symbol
            for symbol in bare_symbols
        }
    else:
        qualified_map = {
            symbol: symbol
            for symbol in bare_symbols
        }

    target_symbols = set(qualified_map.keys())

    references = {
        symbol: _empty_reference()
        for symbol in target_symbols
    }

    needles = _search_needles(
        bare_symbols,
        definer_module,
    )

    for module_id, module in modules.items():
        path = _module_path(
            root_path,
            module,
        )

        key = _cache_key(path)

        if key is None:
            continue

        # --------------------------------------------------
        # CHEAP TEXTUAL PREFILTER
        # --------------------------------------------------

        if needles.isdisjoint(
            _identifiers_for(path, key)
        ):
            continue

        tree = module.ast_tree

        if tree is None:
            continue

        visitor = SymbolReferenceVisitor(
            target_symbols
        )

        visitor.visit(tree)

        # --------------------------------------------------
        # DIRECT CALLS
        # --------------------------------------------------

        for item in visitor.called:
            if isinstance(item, tuple):
                symbol, lineno, context = item
            else:
                symbol = item
                lineno = None
                context = None

            if symbol not in references:
                continue

            references[symbol]["called_by"].append(
                module_id
            )

            references[symbol][
                "called_by_detail"
            ].append(
                {
                    "module": module_id,
                    "line": lineno,
                    "context": context,
                }
            )

        # --------------------------------------------------
        # CALLBACK CALLS
        # --------------------------------------------------

        for item in visitor.callback_called:
            if isinstance(item, tuple):
                symbol, lineno, context = item
            else:
                symbol = item
                lineno = None
                context = None

            if symbol not in references:
                continue

            references[symbol][
                "callback_called"
            ].append(
                module_id
            )

            references[symbol][
                "callback_called_detail"
            ].append(
                {
                    "module": module_id,
                    "line": lineno,
                    "context": context,
                }
            )

        # --------------------------------------------------
        # AMBIGUOUS MATCHES
        # --------------------------------------------------

        for item in visitor.called_ambiguous:
            if isinstance(item, tuple):
                symbol, lineno, context = item
            else:
                symbol = item
                lineno = None
                context = None

            if symbol not in references:
                continue

            references[symbol][
                "called_by_ambiguous"
            ].append(
                module_id
            )

            references[symbol][
                "called_by_ambiguous_detail"
            ].append(
                {
                    "module": module_id,
                    "reason": (
                        "short_name_match_no_confirmed_import"
                    ),
                    "line": lineno,
                    "context": context,
                }
            )

        # --------------------------------------------------
        # EVENT BINDINGS
        # --------------------------------------------------

        for item in visitor.event_bound:
            if isinstance(item, tuple):
                symbol, lineno, context = item
            else:
                symbol = item
                lineno = None
                context = None

            if symbol not in references:
                continue

            references[symbol][
                "event_bound_by"
            ].append(
                module_id
            )

            references[symbol][
                "event_bound_by_detail"
            ].append(
                {
                    "module": module_id,
                    "line": lineno,
                    "context": context,
                }
            )

        # --------------------------------------------------
        # INHERITANCE
        # --------------------------------------------------

        for item in visitor.inherited:
            if len(item) == 3:
                child_name, symbol, lineno = item
            else:
                child_name, symbol = item
                lineno = None

            if symbol not in references:
                continue

            references[symbol][
                "inherited_by"
            ].append(
                module_id
            )

            references[symbol][
                "inherited_by_detail"
            ].append(
                {
                    "module": module_id,
                    "child": child_name,
                    "line": lineno,
                }
            )

        # --------------------------------------------------
        # IMPORTS
        # --------------------------------------------------

        for imp in module.imports:
            imp_module = getattr(
                imp,
                "module",
                None,
            )

            if (
                definer_module
                and not _import_matches_symbol(
                    imp_module or "",
                    definer_module,
                )
            ):
                continue

            for imported_name in imp.names:
                for symbol in target_symbols:
                    bare_symbol = qualified_map[symbol]

                    if imported_name == bare_symbol:
                        references[symbol][
                            "imported_from"
                        ].append(module_id)

    references = _normalize_references(
        references
    )

    return {
        qualified_map[qualified]: data
        for qualified, data in references.items()
    }


# ==========================================================
# MODULE IMPORT USERS
# ==========================================================


def find_import_users(
    target_module_id,
    modules,
):
    """
    Finds modules importing the target module.
    """
    users = []

    short_name = target_module_id.split(".")[-1]

    for module_id, module in modules.items():
        if module_id == target_module_id:
            continue

        for imp in module.imports:
            imported = imp.module

            if not imported:
                continue

            if (
                imported == target_module_id
                or imported.endswith("." + short_name)
            ):
                users.append(module_id)
                break

    return sorted(set(users))


# ==========================================================
# PUBLIC EXPORTS
# ==========================================================

__all__ = [
    "MAX_USAGE_DETAILS",
    "build_symbol_references",
    "find_import_users",
    "reset_caches",
]