# -*- coding: utf-8 -*-

"""
repo_guardian/core/cycles.py

DIRECTED GRAPH CYCLE DETECTOR

Odpowiedzialność:

- wykrywanie cykli w grafie zależności
- zwracanie ścieżek cykli

Nie ocenia:
- ryzyka
- jakości
- długu architektonicznego


Źródło prawdy:

    ProjectGraph.hard_edges


Output:

[
    [
        "core.a",
        "core.b",
        "core.a"
    ]
]


Każdy cykl reprezentowany
deterministycznie.
"""



from typing import (
    Dict,
    Set,
    List,
)



# ==========================================================
# NORMALIZATION
# ==========================================================


def _canonical_cycle(
    cycle: list[str]
) -> tuple[str, ...]:
    """
    Normalizuje cykl.

    Usuwa różnice:

        A,B,C,A

    oraz

        B,C,A,B


    do jednej reprezentacji.
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
    Wykrywa cykle skierowane.

    Algorytm:
        DFS coloring

    states:

        0:
            nieodwiedzony

        1:
            aktualnie na stosie

        2:
            zakończony
    """


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



    return [

        list(cycle)
        +
        [
            cycle[0]
        ]

        for cycle in sorted(
            found
        )

    ]



# ==========================================================
# COMPATIBILITY ALIAS
# ==========================================================


find_cycles = detect_cycles
