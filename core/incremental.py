# -*- coding: utf-8 -*-

"""
repo_guardian/core/incremental.py

INCREMENTAL GRAPH CACHE

Implementuje warstwę pamięci podręcznej
dla deterministycznych wyników analizy grafu.

Aktualnie cacheuje:
    ProjectGraph

Docelowo rozszerzalny o:
    AnalysisResult

Założenia:

- deterministyczny hash wejścia
- LRU eviction
- brak zależności od kolejności importów
- brak mutacji wyników cache

Uwzględnia:
- module_id
- ścieżkę modułu
- import metadata
- zakres importu
- type-only classification

"""


import hashlib

from typing import (
    Tuple,
)

from collections import (
    OrderedDict,
)


from repo_guardian.core.domain.graph import (
    ProjectGraph,
)



# ==========================================================
# CACHE CONFIG
# ==========================================================


# Maksymalna liczba zapamiętanych grafów.
#
# Celowo stała:
# - przewidywalne zużycie pamięci
# - deterministyczne zachowanie
# - brak zewnętrznej konfiguracji


_CACHE_MAX_SIZE = 128



_CACHE: "OrderedDict[str, ProjectGraph]" = (
    OrderedDict()
)



# ==========================================================
# IMPORT SERIALIZATION
# ==========================================================


def _serialize_import(
    imp
) -> tuple:
    """
    Stabilizuje reprezentację ImportRef.

    Nie używa repr obiektu,
    ponieważ repr może zmienić się
    przy refaktorze klasy.

    Uwzględnia tylko dane
    wpływające na graf.
    """


    return (

        imp.module or "",

        getattr(
            imp,
            "level",
            0
        ),

        tuple(
            sorted(
                getattr(
                    imp,
                    "names",
                    []
                )
            )
        ),

        getattr(
            imp,
            "is_from_import",
            False
        ),

        getattr(
            imp,
            "is_local",
            False
        ),

        getattr(
            imp,
            "type_only",
            False
        ),

    )



# ==========================================================
# HASHING
# ==========================================================


def _hash_modules(
    modules: dict
) -> str:
    """
    Generuje deterministyczny hash indeksu modułów.

    Hash invaliduje cache gdy zmieni się:

    - struktura modułów
    - ścieżka modułu
    - import
    - relative level
    - symbole
    - typ importu
    - lokalny zakres importu
    - type-only classification


    Kolejność importów nie ma znaczenia.
    """


    parts = []


    for module_id in sorted(
        modules.keys()
    ):

        module = modules[
            module_id
        ]


        imports = [

            _serialize_import(
                imp
            )

            for imp in module.imports

        ]


        parts.append(

            (

                module_id,

                module.path,

                tuple(
                    sorted(
                        imports
                    )
                ),

            )

        )


    raw = repr(
        parts
    )


    return hashlib.sha256(

        raw.encode(
            "utf-8"
        )

    ).hexdigest()



# ==========================================================
# CACHE OPERATIONS
# ==========================================================


def _cache_get(
    key: str
):
    """
    Pobiera element cache.

    Aktualizuje kolejność LRU.
    """


    if key not in _CACHE:

        return None



    _CACHE.move_to_end(
        key
    )


    return _CACHE[key]



def _cache_put(
    key: str,
    graph: ProjectGraph
):
    """
    Dodaje wynik do cache.

    Obsługuje eviction.
    """


    _CACHE[key] = graph


    _CACHE.move_to_end(
        key
    )


    while len(
        _CACHE
    ) > _CACHE_MAX_SIZE:

        _CACHE.popitem(
            last=False
        )



# ==========================================================
# PUBLIC API
# ==========================================================


def get_cached_graph(
    modules: dict,
    builder_fn
) -> Tuple[ProjectGraph, bool]:
    """
    Zwraca ProjectGraph oraz informację
    czy wynik pochodził z cache.


    Returns:

        (
            ProjectGraph,
            cache_hit
        )


    cache_hit:

        True:
            istniejący wynik

        False:
            wygenerowano nowy graf


    Polityka:

    - LRU
    - maksymalnie 128 wpisów
    - deterministyczny klucz

    """


    cache_key = _hash_modules(
        modules
    )



    cached = _cache_get(
        cache_key
    )


    if cached is not None:

        return (

            cached,

            True

        )



    graph: ProjectGraph = builder_fn(
        modules
    )



    _cache_put(
        cache_key,
        graph
    )


    return (

        graph,

        False

    )
