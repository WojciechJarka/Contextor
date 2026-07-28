# -*- coding: utf-8 -*-

"""
repo_guardian/core/incremental.py

INCREMENTAL GRAPH CACHE

Implements a caching layer
for deterministic graph analysis results.

Currently caches:
    ProjectGraph

Eventually extensible to:
    AnalysisResult

Assumptions:

- deterministic input hash
- LRU eviction
- no dependency on import order
- no mutation of cache results

Takes into account:
- module_id
- module path
- import metadata
- import scope
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


# Maximum number of remembered graphs.
#
# Deliberately constant:
# - predictable memory consumption
# - deterministic behavior
# - no external configuration


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
    Stabilizes the ImportRef representation.

    Does not use object repr,
    because repr can change
    when the class is refactored.

    Only accounts for data
    that affects the graph.
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
    Generates a deterministic hash of the module index.

    The hash invalidates the cache when the following changes:

    - module structure
    - module path
    - import
    - relative level
    - symbols
    - import type
    - local import scope
    - type-only classification


    Import order does not matter.
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
    Retrieves a cache item.

    Updates LRU ordering.
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
    Adds a result to the cache.

    Handles eviction.
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
    Returns a ProjectGraph and information
    whether the result came from the cache.


    Returns:

        (
            ProjectGraph,
            cache_hit
        )


    cache_hit:

        True:
            existing result

        False:
            generated new graph


    Policy:

    - LRU
    - max 128 entries
    - deterministic key

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
