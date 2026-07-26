# -*- coding: utf-8 -*-

"""
repo_guardian/core/api_consumers.py

API CONSUMER AGGREGATOR

Warstwa:
    FACT AGGREGATION

Odpowiedzialność:

- składanie informacji o użytkownikach API
- normalizacja referencji symboli
- rozdzielenie typów użycia


Nie robi:

- scoringu
- dead code
- architektury
- refaktoryzacji


Źródło prawdy:

    symbol_reference.py
"""


# ==========================================================
# NORMALIZATION
# ==========================================================


def _normalize_list(
    value
):
    """
    Normalizuje wejście.

    Obsługuje:

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
    Buduje mapę konsumentów symboli API.

    Parameters:

        symbols:
            lista symboli modułu


        references:
            wynik:

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
        # Runtime = realne wywołania
        # Callback i event binding są
        # osobnymi kategoriami.
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


        # Dopasowania trafione WYŁĄCZNIE przez fallback po krótkiej
        # nazwie (patrz symbol_reference.py::_classify_match) -
        # zgadywanki, nigdy nie liczą się do consumers/consumer_count,
        # ale warto je pokazać LLM-owi zamiast po cichu gubić sygnał.
        ambiguous_calls = _normalize_list(
            reference.get(
                "called_by_ambiguous"
            )
        )


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


def get_runtime_consumers(
    consumer_data
):
    """
    Zwraca moduły używające symbolu
    poprzez wywołanie runtime.
    """

    if not consumer_data:
        return []


    return sorted(
        set(
            consumer_data
            .get(
                "usage",
                {}
            )
            .get(
                "runtime_calls",
                []
            )
        )
    )



def get_import_consumers(
    consumer_data
):
    """
    Zwraca moduły importujące API.
    """

    if not consumer_data:
        return []


    return sorted(
        set(
            consumer_data
            .get(
                "usage",
                {}
            )
            .get(
                "api_imports",
                []
            )
        )
    )



def get_inheritance_consumers(
    consumer_data
):
    """
    Zwraca moduły dziedziczące
    po symbolu.
    """

    if not consumer_data:
        return []


    return sorted(
        set(
            consumer_data
            .get(
                "usage",
                {}
            )
            .get(
                "inheritance",
                []
            )
        )
    )
# ==========================================================
# API SURFACE SUMMARY
# ==========================================================


def summarize_api_consumers(
    consumers
):
    """
    Buduje podsumowanie całego API modułu.

    Nie ocenia jakości.

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

        usage = item.get(
            "usage",
            {}
        )


        has_activity = (

            bool(
                usage.get(
                    "direct_calls"
                )
            )

            or

            bool(
                usage.get(
                    "callback_calls"
                )
            )

            or

            bool(
                usage.get(
                    "event_bindings"
                )
            )

            or

            bool(
                usage.get(
                    "api_imports"
                )
            )

            or

            bool(
                usage.get(
                    "inheritance"
                )
            )
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



# ==========================================================
# COMPATIBILITY ALIAS
# ==========================================================


def build_api_consumers(
    symbols,
    references
):

    return extract_api_consumers(
        symbols,
        references
    )



# ==========================================================
# PUBLIC EXPORTS
# ==========================================================


__all__ = [

    "extract_api_consumers",

    "build_api_consumers",

    "get_runtime_consumers",

    "get_import_consumers",

    "get_inheritance_consumers",

    "summarize_api_consumers",

]    
