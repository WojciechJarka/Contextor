# -*- coding: utf-8 -*-

"""
repo_guardian/core/public_api.py

PUBLIC API EXTRACTION


Warstwa:

    FACT EXTRACTION


Odpowiedzialność:

- wyciąganie publicznej powierzchni modułu
- filtrowanie symboli prywatnych
- normalizacja nazw API


Źródło prawdy:

    symbol_analysis.extract_file_symbols()
    SymbolFacts


Nie robi:

- analizy __all__
- rozwiązywania importów
- sprawdzania użycia
- dead code detection
- scoringu
- risk analysis


Kontrakt:

Input:

{
    "classes": [],
    "functions": [],
    "methods": [],
    "globals": []
}


Output:

[
    "ClassName",
    "function_name",
    "Class.method",
    "CONSTANT"
]


Reguła publiczności:

    foo       -> public
    Class.foo -> public
    _foo      -> private
    Class._x  -> private
"""


# ==========================================================
# HELPERS
# ==========================================================


def _is_public_name(
    name: str
) -> bool:
    """
    Sprawdza czy nazwa jest publiczna.

    Python convention:

        _private

    nie jest częścią publicznego API.
    """

    return bool(name) and not name.startswith(
        "_"
    )



def _symbol_name(
    symbol: str
) -> str:
    """
    Pobiera końcową część symbolu.

    Przykład:

        Service.run

    =>

        run
    """

    return symbol.split(
        "."
    )[-1]



def _collect_category(
    symbols,
    category
):
    """
    Pobiera publiczne symbole z kategorii.
    """

    result = []


    for item in symbols.get(
        category,
        []
    ):

        if _is_public_name(
            _symbol_name(item)
        ):

            result.append(
                item
            )


    return result



# ==========================================================
# PUBLIC API
# ==========================================================


def extract_public_api(
    symbols: dict
) -> list[str]:
    """
    Ekstrahuje publiczny API modułu.

    Oparte wyłącznie o fakty symboli.

    Obsługiwane kategorie:

    - classes
    - functions
    - methods
    - globals


    Zwraca:

        sorted(list[str])

    """

    if not symbols:

        return []


    public = []


    for category in (
        "classes",
        "functions",
        "methods",
        "globals",
    ):

        public.extend(
            _collect_category(
                symbols,
                category
            )
        )


    return sorted(
        set(public)
    )



# ==========================================================
# COMPATIBILITY
# ==========================================================


build_public_api = (
    extract_public_api
)



__all__ = [

    "extract_public_api",

    "build_public_api",

]
