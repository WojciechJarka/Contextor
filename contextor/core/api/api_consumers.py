"""
contextor/core/api/api_consumers.py

API CONSUMER AGGREGATOR

Layer:
FACT AGGREGATION

Responsibilities:

- Assembling information about API users
- Normalizing symbol references
- Separating usage types

Does not do:

- Scoring
- Dead code detection
- Architectural mapping
- Refactoring planning

Source of truth:

    contextor.core.reference.engine
"""

# ==========================================================
# NORMALIZATION
# ==========================================================


def _normalize_list(value):
    """
    Normalizes a collection of consumer module identifiers.

    Supports:
        None
        list
        set
        tuple
    """
    if not value:
        return []

    return sorted(set(value))


def _normalize_detail(value):
    """
    Normalizes reference detail records.

    Detail records are dictionaries and therefore must not be
    passed through set() directly.
    """
    if not value:
        return []

    return list(value)


# ==========================================================
# CONSUMER BUILDING
# ==========================================================


def extract_api_consumers(symbols, references, signatures=None):
    """
    Builds an API symbol consumers map.

    Parameters:
        symbols:
            List of module symbols.

        references:
            Output from build_symbol_references().

    Returns:
        {
            symbol: {
                "signature": str,
                "consumers": [],
                "usage": {},
                "consumer_count": {},
            }
        }

    Consumer classification is based exclusively on the reference
    categories produced by the Symbol Reference Engine.

    Usage categories are intentionally kept separate:

        direct_calls
            Confirmed runtime calls.

        callback_calls
            Confirmed callables passed as arguments.

        event_bindings
            Explicit event/subscription bindings.

        qualified_refs
            Confirmed non-call qualified attribute references.

        api_imports
            Confirmed imports.

        inheritance
            Confirmed inheritance relationships.

    Ambiguous short-name matches are retained as diagnostic
    evidence but never contribute to consumers or consumer_count.
    """

    result = {}

    for symbol in symbols:
        reference = references.get(symbol, {})

        # --------------------------------------------------
        # CONFIRMED USAGE CATEGORIES
        # --------------------------------------------------

        direct_calls = _normalize_list(
            reference.get("called_by")
        )

        callback_calls = _normalize_list(
            reference.get("callback_called")
            or reference.get("callback_calls")
        )

        event_bindings = _normalize_list(
            reference.get("event_bound_by")
        )

        api_imports = _normalize_list(
            reference.get("imported_from")
        )

        inheritance = _normalize_list(
            reference.get("inherited_by")
        )

        runtime_calls = _normalize_list(
            reference.get("runtime_calls")
        )

        qualified_refs = _normalize_list(
            reference.get("qualified_refs")
        )

        # --------------------------------------------------
        # AMBIGUOUS USAGE
        # --------------------------------------------------
        #
        # These matches originate exclusively from short-name
        # fallback matching. They are diagnostic evidence only.
        #

        raw_ambiguous_detail = reference.get(
            "called_by_ambiguous_detail",
            [],
        )

        ambiguous_calls = []
        seen_ambiguous = set()

        for item in raw_ambiguous_detail:
            if not isinstance(item, dict):
                continue

            module = item.get("module")
            reason = item.get("reason")

            key = (module, reason)

            if key in seen_ambiguous:
                continue

            seen_ambiguous.add(key)

            item_copy = dict(item)

            # Explicit heuristic confidence.
            item_copy["confidence"] = 0.3

            ambiguous_calls.append(item_copy)

        ambiguous_calls.sort(
            key=lambda item: (
                item.get("module") or "",
                item.get("line") or 0,
            )
        )

        # --------------------------------------------------
        # CONSUMERS
        # --------------------------------------------------

        consumers = sorted(
            set(
                direct_calls
                + runtime_calls
                + qualified_refs
                + callback_calls
                + event_bindings
                + api_imports
                + inheritance
            )
        )

        # Defensive self-reference filtering.
        consumers = [
            consumer
            for consumer in consumers
            if consumer != "core.api_consumers"
            and consumer != "contextor.core.api.api_consumers"
        ]

        # --------------------------------------------------
        # RESULT
        # --------------------------------------------------

        result[symbol] = {
            "signature": (
                signatures.get(symbol, "")
                if signatures
                else ""
            ),
            "consumers": consumers,
            "usage": {
                "direct_calls": direct_calls,
                "direct_calls_detail": _normalize_detail(
                    reference.get("called_by_detail")
                ),
                "callback_calls": callback_calls,
                "callback_calls_detail": _normalize_detail(
                    reference.get("callback_called_detail")
                ),
                "event_bindings": event_bindings,
                "event_bindings_detail": _normalize_detail(
                    reference.get("event_bound_by_detail")
                ),
                "runtime_calls": runtime_calls,
                "qualified_refs": qualified_refs,
                "qualified_refs_detail": _normalize_detail(
                    reference.get("qualified_refs_detail")
                ),
                "api_imports": api_imports,
                "inheritance": inheritance,
                "inheritance_detail": _normalize_detail(
                    reference.get("inherited_by_detail")
                ),
                "ambiguous_calls": ambiguous_calls,
            },
            "consumer_count": {
                "total": len(consumers),
                "direct_calls": len(direct_calls),
                "callbacks": len(callback_calls),
                "events": len(event_bindings),
                "qualified_refs": len(qualified_refs),
                "api_imports": len(api_imports),
                "inheritance": len(inheritance),
            },
        }

    return result


# ==========================================================
# API SURFACE SUMMARY
# ==========================================================


def summarize_api_consumers(consumers):
    """
    Builds an overview of the module's entire API.

    Does not assess quality.

    Example:

        {
            "total_symbols": int,
            "total_consumers": int,
            "internal_symbols": int,
            "consumer_modules": [...],
            "dead_symbols": [...],
        }
    """
    all_consumers = set()
    dead_symbols = []

    for symbol, data in consumers.items():
        symbol_consumers = data.get("consumers", [])

        if not symbol_consumers:
            dead_symbols.append(symbol)

        all_consumers.update(symbol_consumers)

    return {
        "total_symbols": len(consumers),
        "total_consumers": len(all_consumers),
        "internal_symbols": len(
            [symbol for symbol in consumers if symbol.startswith("_")]
        ),
        "consumer_modules": sorted(all_consumers),
        "dead_symbols": sorted(dead_symbols),
    }


# ==========================================================
# PUBLIC EXPORTS
# ==========================================================

__all__ = [
    "extract_api_consumers",
    "summarize_api_consumers",
]