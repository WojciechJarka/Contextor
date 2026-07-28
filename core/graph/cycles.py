# -*- coding: utf-8 -*-

"""
repo_guardian/core/cycles.py

DIRECTED GRAPH CYCLE DETECTOR

Responsibilities:

- detecting cycles in the dependency graph
- returning cycle paths

Does not evaluate:
- risk
- quality
- architectural debt


Source of truth:

    ProjectGraph.hard_edges


Output:

[
    [
        "core.a",
        "core.b",
        "core.a"
    ]
]


Each cycle is represented
deterministically.
"""



from typing import (
    Dict,
    Set,
    List,
)
import hashlib
import json
import os

_CYCLES_CACHE_FILE = ".guardian_cycles_cache.json"

def _hash_edges(edges: Dict[str, Set[str]]) -> str:
    canonical = {k: sorted(list(v)) for k, v in sorted(edges.items())}
    dumped = json.dumps(canonical)
    return hashlib.md5(dumped.encode("utf-8")).hexdigest()



# ==========================================================
# NORMALIZATION
# ==========================================================


def _canonical_cycle(
    cycle: list[str]
) -> tuple[str, ...]:
    """
    Normalizes a cycle.

    Removes differences like:

        A,B,C,A

    and

        B,C,A,B


    into a single representation.
    """


    if not cycle:

        return tuple()



    nodes = cycle[:-1]


    rotations = []


    for index in range(
        len(nodes)
    ):

        rotated = (
            nodes[index:]
            +
            nodes[:index]
        )

        rotations.append(
            tuple(rotated)
        )


    return min(
        rotations
    )



# ==========================================================
# DFS ENGINE
# ==========================================================


def detect_cycles(
    edges: Dict[str, Set[str]]
) -> List[List[str]]:
    """
    Detects directed cycles (with disk Cache support for performance).
    """

    edge_hash = _hash_edges(edges)
    
    if os.path.exists(_CYCLES_CACHE_FILE):
        try:
            with open(_CYCLES_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if cache.get("hash") == edge_hash:
                    return cache.get("cycles", [])
        except Exception:
            pass

    state = {

        node: 0

        for node in edges

    }


    stack: list[str] = []


    found: set[tuple[str, ...]] = set()



    def visit(
        node: str
    ):


        state[node] = 1


        stack.append(
            node
        )


        for target in sorted(
            edges.get(
                node,
                set()
            )
        ):


            # ------------------------------------------------
            # back edge = cycle
            # ------------------------------------------------

            if state.get(
                target,
                0
            ) == 1:


                try:

                    index = stack.index(
                        target
                    )

                except ValueError:

                    continue



                cycle = (
                    stack[index:]
                    +
                    [
                        target
                    ]
                )


                found.add(
                    _canonical_cycle(
                        cycle
                    )
                )



            elif state.get(
                target,
                0
            ) == 0:


                visit(
                    target
                )



        stack.pop()


        state[node] = 2



    # ------------------------------------------------------
    # deterministic traversal
    # ------------------------------------------------------

    nodes = set(
        edges.keys()
    )


    for targets in edges.values():

        nodes.update(
            targets
        )



    for node in sorted(
        nodes
    ):

        if state.get(
            node,
            0
        ) == 0:

            visit(
                node
            )



    result = [
        list(cycle) + [cycle[0]]
        for cycle in sorted(found)
    ]
    
    try:
        with open(_CYCLES_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"hash": edge_hash, "cycles": result}, f)
    except Exception:
        pass
        
    return result



# ==========================================================
# COMPATIBILITY ALIAS
# ==========================================================


find_cycles = detect_cycles
