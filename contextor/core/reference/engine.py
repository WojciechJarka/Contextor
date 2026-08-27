"""
contextor/core/reference/engine.py

Główny silnik zbierający referencje (Symbol Reference Engine).

NOTE:
Usage detail arrays (`*_detail`) are intentionally capped at
MAX_USAGE_DETAILS to prevent massive I/O bloat in the artifact
usage report.
"""

from __future__ import annotations

import re
import ast
from pathlib import Path

from contextor.core.domain.usage_facts import ModuleUsageFacts
from contextor.core.source import SourceError, read_source

from .visitor import SymbolReferenceVisitor
from .resolution import _absolute_import_module, _resolve_reexport
from .shared import (
    MAX_USAGE_DETAILS,
    _REEXPORT_CACHE,
    _build_reexport_map,
    _empty_reference,
    _export_module_name,
    _normalize_references,
    reset_reexport_cache,
)

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
    reset_reexport_cache()


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
# SYMBOL REFERENCE BUILDING
# ==========================================================


def build_symbol_references(
    modules,
    target_symbols,
    root_path,
    definer_module=None,
    reference_index=None,
):
    """
    Builds reference facts for target symbols using the run-scoped single-pass reference index.
    """
    if reference_index is not None:
        return reference_index.build_symbol_references(
            target_symbols, definer_module=definer_module
        )

    from .index import build_repository_reference_index

    index = build_repository_reference_index(modules, root_path)
    return index.build_symbol_references(
        target_symbols, definer_module=definer_module
    )


def _legacy_build_symbol_references(
    modules,
    target_symbols,
    root_path,
    definer_module=None,
):
    """
    Legacy reference extraction path preserved as a test/reference helper.
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
    reexports = _build_reexport_map(modules)

    references = {
        symbol: _empty_reference()
        for symbol in target_symbols
    }

    needles = _search_needles(
        bare_symbols,
        definer_module,
    )
    needles.update(
        exported.split(".")[-1]
        for exported, original in reexports.items()
        if original in target_symbols
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

        exporter = _export_module_name(module_id)
        exposes_target = any(
            exported.startswith(exporter + ".") and original in target_symbols
            for exported, original in reexports.items()
        )
        if not exposes_target and needles.isdisjoint(_identifiers_for(path, key)):
            continue

        tree = module.ast_tree

        if tree is None:
            continue

        visitor = SymbolReferenceVisitor(
            target_symbols,
            reexports=reexports,
            current_module=module_id,
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
        # QUALIFIED REFS (non-call qualified attributes)
        # --------------------------------------------------

        for item in visitor.qualified_refs:
            if isinstance(item, tuple):
                symbol, lineno, context = item
            else:
                symbol = item
                lineno = None
                context = None

            if symbol not in references:
                continue

            references[symbol][
                "qualified_refs"
            ].append(
                module_id
            )

            references[symbol][
                "qualified_refs_detail"
            ].append(
                {
                    "module": module_id,
                    "line": lineno,
                    "context": context,
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

            for imported_name in imp.names:
                source_module = _absolute_import_module(
                    module_id, imp_module, getattr(imp, "level", 0)
                )
                for symbol in target_symbols:
                    bare_symbol = qualified_map[symbol]
                    imported_identity = _resolve_reexport(
                        f"{source_module}.{imported_name}", reexports
                    )
                    if imported_identity == symbol or (
                        imported_name == "*"
                        and (
                            symbol.startswith(source_module + ".")
                            or any(
                                exported.startswith(source_module + ".")
                                and original == symbol
                                for exported, original in reexports.items()
                            )
                        )
                    ):
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
# CANONICAL MODULE USAGE FACTS EXTRACTOR
# ==========================================================


def extract_module_usage_facts(
    module_path: str,
    source_or_tree: str | ast.AST | None,
    imports: list | None = None,
    target_symbols: set | None = None,
    reexports: dict | None = None,
) -> ModuleUsageFacts:
    """
    Extract outbound ModuleUsageFacts for a single module.

    Canonical producer of per-module outbound usage facts.
    REUSES production SymbolReferenceVisitor - zero duplicate AST visitors created.
    """
    from contextor.core.domain.usage_facts import ModuleUsageFacts, SymbolCallFact

    if source_or_tree is None:
        raw_imports = tuple(
            sorted(
                set(
                    imp.module
                    for imp in (imports or [])
                    if getattr(imp, "module", None)
                )
            )
        )
        return ModuleUsageFacts(imports=raw_imports)

    if isinstance(source_or_tree, str):
        try:
            tree = ast.parse(source_or_tree)
        except SyntaxError:
            raw_imports = tuple(
                sorted(
                    set(
                        imp.module
                        for imp in (imports or [])
                        if getattr(imp, "module", None)
                    )
                )
            )
            return ModuleUsageFacts(imports=raw_imports)
    else:
        tree = source_or_tree

    local_symbols = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_symbols[node.name] = f"{module_path}.{node.name}"
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    local_name = f"{node.name}.{member.name}"
                    local_symbols[local_name] = f"{module_path}.{local_name}"

    visitor = SymbolReferenceVisitor(
        target_symbols=set(target_symbols or set()) | set(local_symbols.values()),
        reexports=reexports or {},
        current_module=module_path,
        local_symbols=local_symbols,
    )
    visitor.visit(tree)

    import_names = set()
    if imports:
        for imp in imports:
            mod_name = getattr(imp, "module", None)
            if mod_name:
                import_names.add(mod_name)
    for _local_name, imported_target in visitor.aliases.items():
        if imported_target:
            import_names.add(imported_target)

    local_resolved_names = set(local_symbols.values())
    all_calls = set(
        item[0] if isinstance(item, tuple) else item
        for item in visitor.called
        if (item[0] if isinstance(item, tuple) else item) not in local_resolved_names
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            from .resolution import _attribute_name
            name = _attribute_name(node.func)
            if name:
                all_calls.add(name)

    direct_calls = tuple(sorted(all_calls))

    dyn_calls = set(
        item[0] if isinstance(item, tuple) else item
        for item in visitor.called_ambiguous
        if (item[0] if isinstance(item, tuple) else item) not in local_resolved_names
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            from .resolution import _attribute_name
            name = _attribute_name(node.func)
            if (
                name == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                dyn_calls.add(node.args[1].value)

    runtime_calls = tuple(sorted(dyn_calls))
    cb_set = set(
        item[0] if isinstance(item, tuple) else item
        for item in visitor.callback_called
    )
    ev_set = set(
        item[0] if isinstance(item, tuple) else item
        for item in visitor.event_bound
    )
    callback_keys = {"command", "callback", "handler", "func", "on_click", "on_change", "on_submit"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            from .resolution import _attribute_name
            for kw in node.keywords:
                if kw.arg in callback_keys:
                    kn = _attribute_name(kw.value)
                    if kn:
                        cb_set.add(kn)
            func_name = _attribute_name(node.func)
            if func_name and func_name.rsplit(".", 1)[-1] in {"bind", "subscribe", "on"}:
                if len(node.args) >= 1:
                    arg_n = _attribute_name(node.args[-1])
                    if arg_n:
                        ev_set.add(arg_n)

    callback_calls = tuple(sorted(cb_set))
    event_bindings = tuple(sorted(ev_set))

    inh_set = set(
        (item[0], item[1]) if len(item) >= 2 else (item[0], "")
        for item in visitor.inherited
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            from .resolution import _attribute_name
            for base in node.bases:
                b_name = _attribute_name(base)
                if b_name:
                    inh_set.add((node.name, b_name))

    inheritance_refs = tuple(sorted(inh_set))

    aliases = tuple(
        sorted(
            set(
                (str(k), str(v))
                for k, v in visitor.aliases.items()
                if k and v
            )
        )
    )

    call_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for child in ast.walk(node.func):
                if isinstance(child, ast.Attribute):
                    call_funcs.add(child)

    qual_refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node not in call_funcs:
            from .resolution import _attribute_name
            name = _attribute_name(node)
            if name and "." in name:
                qual_refs.add(name)

    qualified_refs = tuple(sorted(qual_refs))

    local_callees = {
        dotted: f"{module_path}::{local_name}"
        for local_name, dotted in local_symbols.items()
    }
    symbol_calls = tuple(
        sorted(
            {
                (
                    str(caller),
                    local_callees[callee],
                    int(line),
                    "direct",
                )
                for callee, line, caller in visitor.symbol_called
                if caller and line is not None and callee in local_callees
            }
        )
    )


    reference_evidence = tuple(
        sorted(
            {
                (
                    str(t),
                    str(ch),
                    str(caller),
                    int(line),
                )
                for t, ch, caller, line in visitor.reference_evidence
                if t and ch
            }
        )
    )

    return ModuleUsageFacts(
        imports=tuple(sorted(import_names)),
        direct_calls=direct_calls,
        runtime_calls=runtime_calls,
        callback_calls=callback_calls,
        event_bindings=event_bindings,
        inheritance_refs=inheritance_refs,
        qualified_refs=qualified_refs,
        aliases=aliases,
        symbol_calls=symbol_calls,
        symbol_calls_materialized=True,
        reference_evidence=reference_evidence,
        reference_evidence_materialized=True,
    )


# ==========================================================
# CANONICAL REFERENCE PROJECTION
# ==========================================================


class CanonicalReferenceEvidenceUnavailable(RuntimeError):
    """Raised when required canonical reference facts are unavailable, stale, or incomplete."""
    pass


def _usage_fact_contains_target(
    fact_target: str,
    definer_module: str,
    symbol: str,
    aliases: tuple[tuple[str, str], ...] = (),
) -> bool:
    """Check whether an outbound usage fact target matches the requested definer::symbol."""
    canonical_identity = f"{definer_module}.{symbol}"

    if fact_target == canonical_identity or fact_target == symbol:
        return True

    for local_alias, target in aliases:
        if fact_target == local_alias and target == canonical_identity:
            return True
        if fact_target.startswith(f"{local_alias}.") and canonical_identity.startswith(f"{target}."):
            suffix = fact_target[len(local_alias) + 1:]
            if f"{target}.{suffix}" == canonical_identity:
                return True

    if fact_target.endswith(f".{symbol}"):
        if fact_target == canonical_identity or fact_target.endswith(f".{canonical_identity}"):
            return True
        prefix = fact_target[:-len(symbol) - 1]
        for local_alias, target in aliases:
            if prefix == local_alias and (target == definer_module or target.endswith(definer_module)):
                return True

    return False


def build_symbol_references_from_canonical(
    *,
    definer_module: str,
    symbols: list[str],
    artifact_consumption: dict[str, Any],
    module_usages: dict[str, Any],
    current_modules: set[str] | None = None,
) -> dict[str, Any]:
    """
    Pure in-memory projection of symbol references from canonical artifact_consumption and module_usages facts.
    Produces the exact same dict shape and content as build_symbol_references without any file I/O or AST parsing.

    Confirmed references (imports, direct_calls, callbacks, events, qualified_refs, inheritance, runtime)
    are strictly artifact_consumption-gated inbound edges.
    Ambiguous candidates (called_by_ambiguous) are scanned from canonical current module_usages evidence
    and are intentionally unconfirmed.
    """
    candidate_modules = (
        current_modules
        if current_modules is not None
        else set(module_usages)
    )

    for module_id in candidate_modules:
        facts = module_usages.get(module_id)
        if facts is None:
            raise CanonicalReferenceEvidenceUnavailable(
                f"Missing module_usages for current module {module_id}"
            )
        if not getattr(
            facts,
            "reference_evidence_materialized",
            False,
        ):
            raise CanonicalReferenceEvidenceUnavailable(
                f"Reference evidence not materialized for current module {module_id}"
            )

    result: dict[str, Any] = {}

    for symbol in symbols:
        result[symbol] = _empty_reference()

        target_key = f"{definer_module}::{symbol}"
        consumption = artifact_consumption.get(target_key)

        confirmed_consumers = consumption.get("consumers", ()) if consumption else ()
        channels_by_consumer = consumption.get("channels", {}) if consumption else {}

        for consumer in confirmed_consumers:
            if current_modules is not None and consumer not in current_modules:
                raise CanonicalReferenceEvidenceUnavailable(
                    f"Consumer {consumer} is not current"
                )

            facts = module_usages.get(consumer)
            if facts is None:
                raise CanonicalReferenceEvidenceUnavailable(
                    f"Missing module_usages for confirmed consumer {consumer}"
                )

            if not getattr(
                facts,
                "reference_evidence_materialized",
                False,
            ):
                raise CanonicalReferenceEvidenceUnavailable(
                    f"Reference evidence not materialized for confirmed consumer {consumer}"
                )

            channels = channels_by_consumer.get(consumer, ())
            aliases = getattr(facts, "aliases", ())
            reference_evidence = getattr(facts, "reference_evidence", ())

            for channel in channels:
                if channel in ("api_imports", "imports"):
                    result[symbol]["imported_from"].append(consumer)

                elif channel == "direct_calls":
                    result[symbol]["called_by"].append(consumer)
                    for item in reference_evidence:
                        if item[1] == "direct_calls" and _usage_fact_contains_target(
                            item[0], definer_module, symbol, aliases
                        ):
                            result[symbol]["called_by_detail"].append(
                                {
                                    "module": consumer,
                                    "line": item[3] if item[3] else None,
                                    "context": item[2] if item[2] else None,
                                }
                            )

                elif channel == "callback_calls":
                    result[symbol]["callback_called"].append(consumer)
                    for item in reference_evidence:
                        if item[1] == "callback_calls" and _usage_fact_contains_target(
                            item[0], definer_module, symbol, aliases
                        ):
                            result[symbol]["callback_called_detail"].append(
                                {
                                    "module": consumer,
                                    "line": item[3] if item[3] else None,
                                    "context": item[2] if item[2] else None,
                                }
                            )

                elif channel == "event_bindings":
                    result[symbol]["event_bound_by"].append(consumer)
                    for item in reference_evidence:
                        if item[1] == "event_bindings" and _usage_fact_contains_target(
                            item[0], definer_module, symbol, aliases
                        ):
                            result[symbol]["event_bound_by_detail"].append(
                                {
                                    "module": consumer,
                                    "line": item[3] if item[3] else None,
                                    "context": item[2] if item[2] else None,
                                }
                            )

                elif channel == "qualified_refs":
                    result[symbol]["qualified_refs"].append(consumer)
                    for item in reference_evidence:
                        if item[1] == "qualified_refs" and _usage_fact_contains_target(
                            item[0], definer_module, symbol, aliases
                        ):
                            result[symbol]["qualified_refs_detail"].append(
                                {
                                    "module": consumer,
                                    "line": item[3] if item[3] else None,
                                    "context": item[2] if item[2] else None,
                                }
                            )

                elif channel == "inheritance":
                    result[symbol]["inherited_by"].append(consumer)
                    for item in reference_evidence:
                        if item[1] == "inheritance" and _usage_fact_contains_target(
                            item[0], definer_module, symbol, aliases
                        ):
                            result[symbol]["inherited_by_detail"].append(
                                {
                                    "module": consumer,
                                    "child": item[2],
                                    "line": item[3] if item[3] else None,
                                }
                            )

                elif channel == "runtime_calls":
                    result[symbol]["runtime_calls"].append(consumer)

        # Ambiguous calls can come from any module
        for mod in candidate_modules:
            mod_facts = module_usages[mod]
            mod_aliases = getattr(mod_facts, "aliases", ())
            for item in getattr(mod_facts, "reference_evidence", ()):
                if item[1] == "called_ambiguous" and _usage_fact_contains_target(
                    item[0], definer_module, symbol, mod_aliases
                ):
                    result[symbol]["called_by_ambiguous"].append(mod)
                    result[symbol]["called_by_ambiguous_detail"].append(
                        {
                            "module": mod,
                            "reason": "short_name_match_no_confirmed_import",
                            "line": item[3] if item[3] else None,
                            "context": item[2] if item[2] else None,
                        }
                    )

    return _normalize_references(result)


# ==========================================================
# PUBLIC EXPORTS
# ==========================================================

__all__ = [
    "MAX_USAGE_DETAILS",
    "CanonicalReferenceEvidenceUnavailable",
    "build_symbol_references",
    "build_symbol_references_from_canonical",
    "extract_module_usage_facts",
    "find_import_users",
    "reset_caches",
]
