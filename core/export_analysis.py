# -*- coding: utf-8 -*-

"""
repo_guardian/core/export_analysis.py

MODULE EXPORT ANALYSIS

Warstwa:
    FACT EXTRACTION


Odpowiedzialność:

- wykrywanie symboli eksportowanych przez moduł
- wykrywanie aliasów
- wykrywanie publicznego API


Nie robi:

- dead code scoring
- architecture
- dependency analysis
- risk


Źródło prawdy:

    AST module tree

"""


import ast



# ==========================================================
# HELPERS
# ==========================================================


def _is_public(
    name
):
    """
    Sprawdza publiczność symbolu.

    Python convention:

        _private

    nie jest API.
    """

    return bool(
        name
    ) and not name.startswith(
        "_"
    )



def _add_unique(
    target,
    value
):

    if value not in target:

        target.append(
            value
        )



# ==========================================================
# EXPORT EXTRACTION
# ==========================================================


def extract_exports(
    tree
):
    """
    Ekstrahuje eksporty modułu.


    Returns:

    {
        symbols: [],

        functions: [],

        classes: [],

        constants: [],

        aliases: []
    }


    Nie interpretuje:

        __all__

    ponieważ wymaga osobnej semantyki.

    """

    symbols = []

    functions = []

    classes = []

    constants = []

    aliases = []



    for node in tree.body:


        # --------------------------------------------------
        # FUNCTIONS
        # --------------------------------------------------

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            if _is_public(
                node.name
            ):

                _add_unique(
                    symbols,
                    node.name
                )

                _add_unique(
                    functions,
                    node.name
                )



        # --------------------------------------------------
        # CLASSES
        # --------------------------------------------------

        elif isinstance(
            node,
            ast.ClassDef
        ):

            if _is_public(
                node.name
            ):

                _add_unique(
                    symbols,
                    node.name
                )

                _add_unique(
                    classes,
                    node.name
                )



        # --------------------------------------------------
        # ASSIGNMENTS
        # --------------------------------------------------

        elif isinstance(
            node,
            ast.Assign
        ):


            for target in node.targets:


                if not isinstance(
                    target,
                    ast.Name
                ):

                    continue



                name = target.id


                if not _is_public(
                    name
                ):

                    continue



                _add_unique(
                    symbols,
                    name
                )


                _add_unique(
                    constants,
                    name
                )



                if isinstance(
                    node.value,
                    ast.Name
                ):

                    if (
                        node.value.id
                        !=
                        name
                    ):

                        aliases.append(
                            {
                                "name":
                                    name,

                                "target":
                                    node.value.id
                            }
                        )



    return {

        "symbols":
            sorted(
                symbols
            ),


        "functions":
            sorted(
                functions
            ),


        "classes":
            sorted(
                classes
            ),


        "constants":
            sorted(
                constants
            ),


        "aliases":
            sorted(
                aliases,
                key=lambda x:
                    (
                        x["name"],
                        x["target"]
                    )
            )

    }

# ==========================================================
# UNUSED CANDIDATES
# ==========================================================


def find_unused_public_api(
    symbols,
    usage,
    exports=None,
    local_calls=None,
    references=None
):
    """
    Znajduje potencjalnie nieużywane symbole.

    Jest to analiza faktów.

    Nie oznacza automatycznie dead-code.


    Parameters:

        symbols:
            wszystkie symbole modułu


        usage:
            wynik symbol_usage() (użycie międzymodułowe)


        exports:
            wynik extract_exports()


        local_calls:
            wywołania wewnątrz tego samego pliku
            (np. symbols["calls"] z extract_file_symbols)


    Returns:

        lista kandydatów


    """


    used = set()

    references = references or {}

    #
    # lokalne referencje (międzymodułowe)
    #

    if usage:


        used.update(
            usage.keys()
        )



    #
    # lokalne wywołania wewnątrz pliku
    #

    if local_calls:


        used.update(
            local_calls
        )



    #
    # publiczne eksporty
    #

    exported = set()



    if exports:


        exported.update(
            exports.get(
                "symbols",
                []
            )
        )



        for alias in exports.get(
            "aliases",
            []
        ):

            name = alias.get(
                "name"
            )

            if name:

                exported.add(
                    name
                )



    candidates = []



    for symbol in symbols:

        #
        # używany lokalnie / między modułami
        #

        if symbol in used:
            continue

        #
        # publiczne API
        #

        if symbol in exported:
            continue

        #
        # wykryte referencje semantyczne
        #

        ref = references.get(symbol, {})

        if ref.get("event_bound_by"):
            continue

        if ref.get("imported_from"):
            continue

        candidates.append(symbol)



    return sorted(
        set(
            candidates
        )
    )



# ==========================================================
# EXPORT SUMMARY
# ==========================================================


def summarize_exports(
    exports
):
    """
    Tworzy prosty opis API modułu.

    Bez oceny jakości.
    """


    if not exports:

        return {

            "symbol_count": 0,

            "public_api": False,

        }



    symbols = exports.get(
        "symbols",
        []
    )


    return {

        "symbol_count":
            len(
                symbols
            ),


        "function_count":
            len(
                exports.get(
                    "functions",
                    []
                )
            ),


        "class_count":
            len(
                exports.get(
                    "classes",
                    []
                )
            ),


        "constant_count":
            len(
                exports.get(
                    "constants",
                    []
                )
            ),


        "alias_count":
            len(
                exports.get(
                    "aliases",
                    []
                )
            ),


        "public_api":
            bool(
                symbols
            )

    }



# ==========================================================
# COMPATIBILITY
# ==========================================================


find_unused_symbols = (
    find_unused_public_api
)

find_unreferenced_symbols = (
    find_unused_public_api
)
