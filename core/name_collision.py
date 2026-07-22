# ============================================================
# Repo Guardian — NAME COLLISION DETECTOR
# Version: 2.0
#
# Purpose:
#   Detect real public symbol collisions.
#
# DOES NOT detect:
#   - local variables
#   - function arguments
#   - AST visitor methods
#   - temporary names
#   - duplicated __init__/run/visit_*
#
# Detects:
#   - duplicated public functions
#   - duplicated public classes
#   - duplicated exported constants
#
# Architecture:
#
#   SymbolRegistry
#          |
#          v
#   CollisionDetector
#          |
#          v
#   CollisionReport
#
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Any


# ============================================================
# CONFIGURATION
# ============================================================


IGNORED_SYMBOL_NAMES = {
    "__init__",
    "__new__",
    "__str__",
    "__repr__",
    "__len__",
    "__iter__",
    "run",
    "main",
    "visit",
    "visit_ClassDef",
    "visit_FunctionDef",
}


IGNORED_KINDS = {
    "method",
    "attribute",
    "variable",
    "local",
    "argument",
}


ALLOWED_COLLISION_KINDS = {
    "function",
    "class",
    "constant",
}


# ============================================================
# RESULT MODEL
# ============================================================


@dataclass
class CollisionRecord:

    symbol: str

    kind: str

    locations: list[str]

    message: str



    def to_dict(self):

        return asdict(self)



# ============================================================
# HELPERS
# ============================================================


def _symbol_name(symbol: Any) -> str:

    return (
        getattr(symbol, "name", None)
        or getattr(symbol, "symbol", None)
        or ""
    )



def _symbol_kind(symbol: Any) -> str:

    return (
        getattr(symbol, "kind", None)
        or ""
    )



def _symbol_module(symbol: Any) -> str:

    return (
        getattr(symbol, "module_id", None)
        or getattr(symbol, "module", None)
        or ""
    )



def _is_public(symbol: Any) -> bool:

    public = getattr(symbol, "public", None)

    if public is not None:
        return bool(public)


    name = _symbol_name(symbol)

    return (
        bool(name)
        and not name.startswith("_")
    )



def _full_location(symbol: Any) -> str:

    module = _symbol_module(symbol)

    name = _symbol_name(symbol)

    if module:
        return f"{module}.{name}"

    return name



# ============================================================
# NORMALIZATION
# ============================================================


def collect_symbols(registry: Any) -> list[Any]:

    """
    Supports:

    SymbolRegistry
    dict[str, Symbol]
    list[Symbol]

    """

    if registry is None:
        return []


    if hasattr(registry, "all"):

        return list(
            registry.all()
        )


    if isinstance(registry, dict):

        return list(
            registry.values()
        )


    if isinstance(registry, (list, tuple, set)):

        return list(registry)


    return []



# ============================================================
# MAIN DETECTOR
# ============================================================


def detect_name_collisions(
    registry: Any,
) -> list[CollisionRecord]:

    """
    Detect only real namespace collisions.

    Input:
        SymbolRegistry

    Output:
        list[CollisionRecord]

    """


    symbols = collect_symbols(
        registry
    )


    grouped: dict[tuple[str, str], list[Any]] = {}


    for symbol in symbols:


        name = _symbol_name(symbol)

        kind = _symbol_kind(symbol)


        if not name:
            continue


        if name in IGNORED_SYMBOL_NAMES:
            continue


        if kind in IGNORED_KINDS:
            continue


        if kind not in ALLOWED_COLLISION_KINDS:
            continue


        if not _is_public(symbol):
            continue


        key = (
            name,
            kind,
        )


        grouped.setdefault(
            key,
            []
        ).append(
            symbol
        )



    collisions = []



    for (
        name,
        kind
    ), items in grouped.items():


        locations = [
            _full_location(item)
            for item in items
        ]


        unique_locations = sorted(
            set(locations)
        )


        if len(unique_locations) < 2:
            continue



        collisions.append(

            CollisionRecord(

                symbol=name,

                kind=kind,

                locations=unique_locations,

                message=(
                    f"Public {kind} collision "
                    f"for symbol '{name}'"
                ),

            )

        )


    return collisions



# ============================================================
# COMPATIBILITY API
# ============================================================


def validate_name_collisions(
    registry: Any,
):

    """
    Backwards compatible validator entry.
    """

    return detect_name_collisions(
        registry
    )



def generate_collision_report(
    registry: Any,
):

    collisions = detect_name_collisions(
        registry
    )


    return {

        "total_collisions":
            len(collisions),

        "collisions":
            [
                item.to_dict()
                for item in collisions
            ]

    }



__all__ = [

    "CollisionRecord",

    "detect_name_collisions",

    "validate_name_collisions",

    "generate_collision_report",

]
