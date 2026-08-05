"""
contextor/core/reference/engine.py

Główny silnik zbierający referencje (Symbol Reference Engine).

NOTE: Usage detail arrays (`_detail`) are intentionally capped at 
`MAX_USAGE_DETAILS` to prevent massive I/O bloat in the artifact usage report.
"""

import re
from pathlib import Path

from contextor.core.source import SourceError, read_source

from .visitor import SymbolReferenceVisitor

# ==========================================================
# PROCESS-LOCAL IDENTIFIER CACHE
# ==========================================================
#
# build_symbol_references() is called once per defining module and has to
# consider every other module as a potential consumer, which made the
# pipeline O(N^2) in file reads and AST walks.
#
# The prefilter below reduces that to the modules that could actually
# match. It needs only the set of identifier tokens per file, which is
# far cheaper to keep than an AST - parsed trees come from the shared
# cache behind Module.ast_tree, so there is exactly one tree cache.
#
# Entries are keyed by path plus a content fingerprint, so an edited file
# is never served from a stale entry. reset_caches() drops the whole
# thing between analyses in the long-lived GUI process.


_IDENTIFIER_CACHE: dict[str, frozenset[str]] = {}

# One stat() per file per analysis instead of one per file per defining
# module; the repository is a fixed snapshot for the duration of a run.
_FINGERPRINT_CACHE: dict[str, str | None] = {}

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def reset_caches() -> None:
    """
    Drops cached file state. Call at the start of an analysis run.
    """

    _IDENTIFIER_CACHE.clear()
    _FINGERPRINT_CACHE.clear()


def _cache_key(path: Path) -> str | None:
    """
    Identity of a file version: path plus mtime plus size.
    """

    key = str(path)

    if key in _FINGERPRINT_CACHE:
        return _FINGERPRINT_CACHE[key]

    try:
        stat = path.stat()
        fingerprint = f"{key}|{stat.st_mtime_ns}|{stat.st_size}"
    except OSError:
        fingerprint = None

    _FINGERPRINT_CACHE[key] = fingerprint

    return fingerprint


def _identifiers_for(path: Path, key: str) -> frozenset[str]:
    """
    Every identifier-like token appearing in the file, including tokens
    inside string literals (so dynamic getattr("name") lookups count).
    """

    cached = _IDENTIFIER_CACHE.get(key)

    if cached is not None:
        return cached

    try:
        names = frozenset(_IDENTIFIER_RE.findall(read_source(path)))
    except SourceError:
        names = frozenset()

    _IDENTIFIER_CACHE[key] = names

    return names


def _search_needles(bare_symbols: set[str], definer_module: str | None) -> set[str]:
    """
    Tokens that must appear in a file for it to possibly reference any
    target symbol.

    Sound because every match path in resolution._classify_match compares
    either a full dotted name or its last component against a target
    symbol, and both are built from identifiers present in the source.
    """

    needles: set[str] = set()

    for symbol in bare_symbols:
        needles.update(symbol.split("."))

    if definer_module:
        needles.update(definer_module.split("."))

    return needles


def _empty_reference():
    return {
        "called_by": [],
        "called_by_detail": [],
        "called_by_ambiguous": [],
        "called_by_ambiguous_detail": [],
        "event_bound_by": [],
        "event_bound_by_detail": [],
        "imported_from": [],
        "inherited_by": [],
        "inherited_by_detail": [],
    }


def _module_path(root_path, module) -> Path:
    """
    Absolute source path of a module.

    The indexer stores an already-absolute path; joining it onto
    root_path is a no-op in that case and still handles relative paths.
    """

    raw = getattr(module, "absolute_path", None) or module.path

    return Path(root_path) / raw


def _import_matches_symbol(imported, symbol):
    if not imported:
        return False
    if imported == symbol:
        return True
    if imported.endswith("." + symbol):
        return True
    if symbol.endswith("." + imported):
        return True
    return False


MAX_USAGE_DETAILS = 15

def _normalize_references(references):
    for data in references.values():
        for key, values in data.items():
            if isinstance(values, list) and all(isinstance(v, str) for v in values):
                data[key] = sorted(set(values))
            elif isinstance(values, list) and key.endswith("_detail"):
                data[key] = values[:MAX_USAGE_DETAILS]
    return references


def build_symbol_references(modules, target_symbols, root_path, definer_module=None):
    bare_symbols = set(target_symbols)

    if definer_module:
        qualified_map = {f"{definer_module}.{symbol}": symbol for symbol in bare_symbols}
    else:
        qualified_map = {symbol: symbol for symbol in bare_symbols}

    target_symbols = set(qualified_map.keys())
    references = {symbol: _empty_reference() for symbol in target_symbols}

    needles = _search_needles(bare_symbols, definer_module)

    for module_id, module in modules.items():
        path = _module_path(root_path, module)

        key = _cache_key(path)

        if key is None:
            continue

        # Cheap textual prefilter. A module that does not even mention
        # any component of a target symbol cannot reference it, so the
        # expensive parse and AST walk are skipped entirely.
        if needles.isdisjoint(_identifiers_for(path, key)):
            continue

        tree = module.ast_tree

        if tree is None:
            continue

        visitor = SymbolReferenceVisitor(target_symbols)
        visitor.visit(tree)

        for item in visitor.called:
            symbol, lineno, context = item if isinstance(item, tuple) else (item, None, None)
            if symbol in references:
                references[symbol]["called_by"].append(module_id)
                references[symbol]["called_by_detail"].append(
                    {"module": module_id, "line": lineno, "context": context}
                )

        for item in visitor.called_ambiguous:
            symbol, lineno, context = item if isinstance(item, tuple) else (item, None, None)
            if symbol in references:
                references[symbol]["called_by_ambiguous"].append(module_id)
                references[symbol]["called_by_ambiguous_detail"].append(
                    {
                        "module": module_id,
                        "reason": "short_name_match_no_confirmed_import",
                        "line": lineno,
                        "context": context,
                    }
                )

        for item in visitor.event_bound:
            symbol, lineno, context = item if isinstance(item, tuple) else (item, None, None)
            if symbol in references:
                references[symbol]["event_bound_by"].append(module_id)
                references[symbol]["event_bound_by_detail"].append(
                    {"module": module_id, "line": lineno, "context": context}
                )

        for item in visitor.inherited:
            if len(item) == 3:
                child_name, symbol, lineno = item
            else:
                child_name, symbol = item
                lineno = None
            if symbol in references:
                references[symbol]["inherited_by"].append(module_id)
                references[symbol]["inherited_by_detail"].append(
                    {"module": module_id, "child": child_name, "line": lineno}
                )

        for imp in module.imports:
            imp_module = getattr(imp, "module", None)
            if definer_module and not _import_matches_symbol(imp_module or "", definer_module):
                continue
            for imported_name in imp.names:
                for symbol in target_symbols:
                    bare_symbol = qualified_map[symbol]
                    if imported_name == bare_symbol:
                        references[symbol]["imported_from"].append(module_id)

    references = _normalize_references(references)

    return {qualified_map[qualified]: data for qualified, data in references.items()}


def find_import_users(target_module_id, modules):
    users = []
    short_name = target_module_id.split(".")[-1]

    for module_id, module in modules.items():
        if module_id == target_module_id:
            continue
        for imp in module.imports:
            imported = imp.module
            if not imported:
                continue
            if imported == target_module_id or imported.endswith("." + short_name):
                users.append(module_id)
                break

    return sorted(set(users))
