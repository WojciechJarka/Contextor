# -*- coding: utf-8 -*-

"""
repo_guardian/core/activity.py

SYMBOL ACTIVITY INTERPRETER

Warstwa:
    INTERPRETATION

Jedyna definicja aktywności symbolu.

Nie zbiera faktów.
Nie generuje raportów.
Nie zna architektury projektu.

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


def _collect_evidence(
    symbol,
    references=None,
    local_calls=None
):
    """
    Tylko zbiera fakty.
    Nie interpretuje.
    """

    references = references or {}

    ref = references.get(
        symbol,
        {}
    )

    local_calls = set(
        local_calls or []
    )

    called_by = ref.get(
        "called_by",
        []
    )

    event_bound_by = ref.get(
        "event_bound_by",
        []
    )

    imported_from = ref.get(
        "imported_from",
        []
    )

    inherited_by = ref.get(
        "inherited_by",
        []
    )


    return {

        "called_by":
            bool(called_by),

        "events":
            bool(event_bound_by),

        "imports":
            bool(imported_from),

        "inheritance":
            bool(inherited_by),

        "local_calls":
            symbol in local_calls,

        "sources":
            sorted(
                set(
                    list(called_by)
                    +
                    list(event_bound_by)
                    +
                    list(imported_from)
                    +
                    list(inherited_by)
                )
            ),

    }



# ==========================================================
# STATUS
# ==========================================================


def _has_runtime_activity(
    evidence
):
    return any(
        [
            evidence["called_by"],
            evidence["imports"],
            evidence["inheritance"],
            evidence["local_calls"],
        ]
    )


def _has_callback_activity(
    evidence
):
    return evidence["events"]


def _determine_status(
    symbol,
    evidence,
    public_symbols
):

    if _has_runtime_activity(
        evidence
    ):
        return STATUS_LIVE


    if _has_callback_activity(
        evidence
    ):
        return "live_callback"


    if symbol in public_symbols:

        return STATUS_UNUSED_PUBLIC


    return STATUS_UNUSED_INTERNAL



# ==========================================================
# CONFIDENCE
# ==========================================================


def _determine_confidence(
    evidence
):

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
    symbols,
    references=None,
    public_symbols=None,
    local_calls=None,
    analyze_scope="all"
):
    """
    Klasyfikuje aktywność symboli.

    analyze_scope:

        all
            analizuje wszystkie symbole

        public
            analizuje tylko public_symbols


    Domyślnie:
        all

    Powód:
        interpreter nie powinien zakładać,
        że analizujemy fasadę API.
    """


    public_symbols = set(
        public_symbols or []
    )


    if analyze_scope == "public":

        symbols = [
            s
            for s in symbols
            if s in public_symbols
        ]


    result = {}


    for symbol in symbols:


        evidence = _collect_evidence(
            symbol,
            references,
            local_calls
        )


        result[symbol] = {

            "status":
                _determine_status(
                    symbol,
                    evidence,
                    public_symbols
                ),

            "evidence":
                {
                    "called_by":
                        evidence["called_by"],

                    "events":
                        evidence["events"],

                    "imports":
                        evidence["imports"],

                    "inheritance":
                        evidence["inheritance"],

                    "local_calls":
                        evidence["local_calls"],
                },

            "sources":
                evidence["sources"],

            "confidence":
                _determine_confidence(
                    evidence
                ),

        }


    return result



# ==========================================================
# SUMMARY
# ==========================================================


def summarize_activity(
    activity
):

    result = {

        STATUS_LIVE:
            0,

        STATUS_LIVE_CALLBACK:
            0,

        STATUS_UNUSED_PUBLIC:
            0,

        STATUS_UNUSED_INTERNAL:
            0,

    }


    for item in activity.values():

        status = item.get(
            "status"
        )

        if status in result:

            result[status] += 1


    return {

        "total_symbols":
            len(activity),

        "live":
            result[STATUS_LIVE],

        "live_callback":
            result[STATUS_LIVE_CALLBACK],

        "unused_public_api":
            result[STATUS_UNUSED_PUBLIC],

        "unused_internal_candidates":
            result[STATUS_UNUSED_INTERNAL],

    }



__all__ = [

    "classify_symbol_activity",

    "summarize_activity",

    "STATUS_LIVE",

    "STATUS_UNUSED_PUBLIC",

    "STATUS_UNUSED_INTERNAL",

]
