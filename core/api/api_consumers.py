# -*- coding: utf-8 -*-

"""
core/api/api_consumers.py

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

    symbol_reference.py
"""


# ==========================================================
# NORMALIZATION
# ==========================================================


def _normalize_list(
    value
):
    """
    Normalizes the input structure.

    Supports:
        None
        list
        set
        tuple
    """

    if not value:
        return []

    return sorted(
        set(value)
    )



# ==========================================================
# CONSUMER BUILDING
# ==========================================================


def extract_api_consumers(
    symbols,
    references
):
    """
    Builds an API symbol consumers map.

    Parameters:

        symbols:
            List of module symbols.

        references:
            Output from:
                build_symbol_references()


    Returns:

        {
            symbol:
            {
                consumers: [],
                usage: {},
                consumer_count: {}
            }
        }

    """

    result = {}


    for symbol in symbols:

        reference = references.get(
            symbol,
            {}
        )


        direct_calls = _normalize_list(
            reference.get(
                "called_by"
            )
        )


        callback_calls = _normalize_list(
            reference.get(
                "callback_calls"
            )
        )


        event_bindings = _normalize_list(
            reference.get(
                "event_bound_by"
            )
        )


        #
        # Runtime = actual real calls
        # Callback and event bindings are
        # separated into distinct categories.
        #
        runtime_calls = sorted(
            set(
                direct_calls
                +
                callback_calls
            )
        )


        api_imports = _normalize_list(
            reference.get(
                "imported_from"
            )
        )


        inheritance = _normalize_list(
            reference.get(
                "inherited_by"
            )
        )


        # Matches hit EXCLUSIVELY via fallback by short name
        # (see symbol_reference.py::_classify_match) -
        # these are guesses. They never count towards consumers/consumer_count,
        # but are worth exposing to the LLM instead of silently dropping the signal.
        raw_ambiguous_detail = reference.get(
            "called_by_ambiguous_detail", []
        )
        
        ambiguous_calls = []
        _seen_amb = set()
        for item in raw_ambiguous_detail:
            key = (item.get("module"), item.get("reason"))
            if key not in _seen_amb:
                _seen_amb.add(key)
                # Dopisujemy confidence, zgodnie z wytycznymi Phase 7.1
                item_copy = dict(item)
                item_copy["confidence"] = 0.3
                ambiguous_calls.append(item_copy)
        
        ambiguous_calls = sorted(ambiguous_calls, key=lambda x: x["module"])


        consumers = sorted(
            set(
                runtime_calls
                +
                event_bindings
                +
                api_imports
                +
                inheritance
            )
        )


        consumers = [
            item
            for item in consumers
            if item != "core.api_consumers"
        ]


        result[symbol] = {

            "consumers":
                consumers,


            "usage":
            {
                "direct_calls":
                    direct_calls,


                "callback_calls":
                    callback_calls,


                "event_bindings":
                    event_bindings,


                "runtime_calls":
                    runtime_calls,


                "api_imports":
                    api_imports,


                "inheritance":
                    inheritance,


                "ambiguous_calls":
                    ambiguous_calls,
            },


            "consumer_count":
            {
                "total":
                    len(
                        consumers
                    ),


                "callbacks":
                    len(
                        callback_calls
                    ),


                "events":
                    len(
                        event_bindings
                    ),


                "api_imports":
                    len(
                        api_imports
                    ),


                "inheritance":
                    len(
                        inheritance
                    ),

            }

        }


    return result



# ==========================================================
# CONSUMER FILTERS
# ==========================================================


# ==========================================================
# API SURFACE SUMMARY
# ==========================================================


def summarize_api_consumers(
    consumers
):
    """
    Builds an overview of the module's entire API.

    Does not assess quality.

    Przykład:

    {
        total_symbols: 10,
        used_symbols: 7,
        unused_symbols: 3
    }

    """

    total = len(
        consumers
    )


    used = 0


    for item in consumers.values():
        usage = item.get("usage", {})

        has_activity = any(
            usage.get(k) for k in [
                "direct_calls", "callback_calls", "event_bindings", "api_imports", "inheritance"
            ]
        )

        if has_activity:
            used += 1



    return {

        "total_symbols":
            total,


        "used_symbols":
            used,


        "unused_symbols":
            total - used,

    }



# Removed build_api_consumers

# ==========================================================
# PUBLIC EXPORTS
# ==========================================================


__all__ = [

    "extract_api_consumers",

    "summarize_api_consumers",

]    
