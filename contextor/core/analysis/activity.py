"""
core/analysis/activity.py

SYMBOL ACTIVITY INTERPRETER

Layer:
    INTERPRETATION

The sole definition of symbol activity status.

Does not gather facts.
Does not generate reports.
Has no architectural project knowledge.

Input:
    facts:
        called_by
        event_bound_by
        imported_from
        inherited_by

Output:
    symbol_activity
"""


# ==========================================================
# CONSTANTS
# ==========================================================

STATUS_LIVE = "live"

STATUS_LIVE_CALLBACK = "live_callback"

STATUS_UNUSED_PUBLIC = "unused_public_api"

STATUS_UNUSED_INTERNAL = "unused_internal_candidate"


CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"


# ==========================================================
# EVIDENCE
# ==========================================================


def _collect_evidence(symbol, references=None, local_calls=None):
    """
    Strictly gathers facts.
    Does not interpret.
    """

    references = references or {}

    ref = references.get(symbol, {})

    local_calls = set(local_calls or [])

    called_by = ref.get("called_by", [])

    event_bound_by = ref.get("event_bound_by", [])

    imported_from = ref.get("imported_from", [])

    inherited_by = ref.get("inherited_by", [])

    return {
        "called_by": bool(called_by),
        "events": bool(event_bound_by),
        "imports": bool(imported_from),
        "inheritance": bool(inherited_by),
        "local_calls": symbol in local_calls,
        "sources": sorted(
            set(list(called_by) + list(event_bound_by) + list(imported_from) + list(inherited_by))
        ),
    }


# ==========================================================
# STATUS
# ==========================================================


def _has_runtime_activity(evidence):
    return any(
        [
            evidence["called_by"],
            evidence["imports"],
            evidence["inheritance"],
            evidence["local_calls"],
        ]
    )


def _has_callback_activity(evidence):
    return evidence["events"]


def _determine_status(symbol, evidence, public_symbols):
    # Protect built-in (dunder) methods from being marked as "dead code"
    # Python natively invokes them during the class lifecycle.
    if (
        "__" in symbol
        and symbol.split(".")[-1].startswith("__")
        and symbol.split(".")[-1].endswith("__")
    ):
        return "live_framework"

    if _has_runtime_activity(evidence):
        return STATUS_LIVE

    if _has_callback_activity(evidence):
        return "live_callback"

    if symbol in public_symbols:
        return STATUS_UNUSED_PUBLIC

    return STATUS_UNUSED_INTERNAL


# ==========================================================
# CONFIDENCE
# ==========================================================


def _determine_confidence(evidence):

    count = sum(
        [
            evidence["called_by"],
            evidence["events"],
            evidence["imports"],
            evidence["inheritance"],
            evidence["local_calls"],
        ]
    )

    if count >= 2:
        return CONFIDENCE_HIGH

    if count == 1:
        return CONFIDENCE_MEDIUM

    return CONFIDENCE_LOW


# ==========================================================
# PUBLIC API
# ==========================================================


def classify_symbol_activity(
    symbols, references=None, public_symbols=None, local_calls=None, analyze_scope="all"
):
    """
    Classifies symbol activity.

    analyze_scope:

        all
            analyzes all symbols

        public
            analyzes only public_symbols

    Default:
        all

    Reason:
        The interpreter should not assume
        that we are only analyzing the API facade.
    """

    public_symbols = set(public_symbols or [])

    if analyze_scope == "public":
        symbols = [s for s in symbols if s in public_symbols]

    result = {}

    for symbol in symbols:
        evidence = _collect_evidence(symbol, references, local_calls)

        result[symbol] = {
            "status": _determine_status(symbol, evidence, public_symbols),
            "evidence": {
                "called_by": evidence["called_by"],
                "events": evidence["events"],
                "imports": evidence["imports"],
                "inheritance": evidence["inheritance"],
                "local_calls": evidence["local_calls"],
            },
            "sources": evidence["sources"],
            "confidence": _determine_confidence(evidence),
        }

    return result


# ==========================================================
# SUMMARY
# ==========================================================


def summarize_activity(activity):
    from collections import Counter

    counts = Counter(item.get("status") for item in activity.values())

    return {
        "total_symbols": len(activity),
        "live": counts[STATUS_LIVE],
        "live_callback": counts["live_callback"],
        "unused_public_api": counts[STATUS_UNUSED_PUBLIC],
        "unused_internal_candidates": counts[STATUS_UNUSED_INTERNAL],
    }


__all__ = [
    "classify_symbol_activity",
    "summarize_activity",
    "STATUS_LIVE",
    "STATUS_UNUSED_PUBLIC",
    "STATUS_UNUSED_INTERNAL",
]
