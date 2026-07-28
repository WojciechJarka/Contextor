# -*- coding: utf-8 -*-

"""
repo_guardian/core/public_api.py

PUBLIC API EXTRACTION


Layer:

    FACT EXTRACTION


Responsibility:

- extracting public module surface
- filtering private symbols
- normalizing API names


Source of truth:

    symbol_analysis.extract_file_symbols()
    SymbolFacts


Does not do:

- __all__ analysis
- imports resolution
- usage checking
- dead code detection
- scoring
- risk analysis


Contract:

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


Public rule:

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
    Checks if name is public.

    Python convention:

        _private

    is not part of the public API.
    """

    return bool(name) and not name.startswith(
        "_"
    )



def _symbol_name(
    symbol: str
) -> str:
    """
    Gets the final part of the symbol.

    Example:

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
    Gets public symbols from a category.
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
    Extracts public API of the module.

    Based exclusively on symbol facts.

    Supported categories:

    - classes
    - functions
    - methods
    - globals


    Returns:

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
