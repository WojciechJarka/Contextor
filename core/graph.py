# -*- coding: utf-8 -*-

"""
repo_guardian/core/graph.py

WARSTWA: GRAPH BUILDER

Buduje czysty graf zależności projektu
na podstawie wyników resolvera.

Typy krawędzi:

hard_edges:
    realne zależności runtime

soft_edges:
    zależności niepewne:
    - FALLBACK resolvera
    - type-only imports
    - potencjalnie dynamiczne zależności


UNKNOWN:
    ignorowane.
    Nie trafiają do grafu.

GRAPH BUILDER:
    - nie interpretuje architektury
    - nie liczy ryzyka
    - nie analizuje AST

Źródło prawdy:
    resolver + ImportRef
"""


from .domain.module import (
    Module,
)

from .domain.graph import (
    ProjectGraph,
)

from .resolver import (
    build_trie,
    resolve_internal,
)



# ==========================================================
# HELPERS
# ==========================================================


def _is_type_only_import(
    import_ref
) -> bool:
    """
    Type-only imports traktujemy
    jako soft dependency.

    ImportRef nie posiada jeszcze
    pełnego AST contextu,
    dlatego bazujemy na istniejącym
    polu lokalnym.

    Docelowo może zostać rozszerzone
    o import_usage analyzer.
    """

    return getattr(
        import_ref,
        "type_only",
        False
    )



def _add_edge(
    graph: dict[str, set[str]],
    source: str,
    target: str,
):
    """
    Centralny zapis krawędzi.

    Zapewnia:
    - brak duplikatów
    - deterministyczność
    """

    if source == target:

        return


    graph.setdefault(
        source,
        set()
    ).add(
        target
    )



# ==========================================================
# PUBLIC API
# ==========================================================


def build_graph(
    modules: dict[str, Module]
) -> ProjectGraph:
    """
    Buduje ProjectGraph.

    Pipeline:

        Module
          |
          v
       resolver
          |
          v
     MODULE/FALLBACK
          |
          v
     ProjectGraph


    Returns:

        ProjectGraph(
            hard_edges,
            soft_edges
        )
    """



    hard_edges: dict[str, set[str]] = {}

    soft_edges: dict[str, set[str]] = {}



    # ======================================================
    # Resolver index
    # ======================================================


    trie = build_trie(
        modules.keys()
    )



    # ======================================================
    # Deterministic traversal
    # ======================================================


    for module_id in sorted(
        modules.keys()
    ):


        module = modules[module_id]


        hard_edges.setdefault(
            module_id,
            set()
        )


        soft_edges.setdefault(
            module_id,
            set()
        )



        # --------------------------------------------------
        # Import order does not affect graph
        # --------------------------------------------------

        imports = sorted(

            module.imports,

            key=lambda imp:
            (
                imp.module or "",
                imp.level,
                tuple(
                    sorted(
                        imp.names
                    )
                ),
                imp.is_from_import,
                imp.is_local,
            )
        )



        for imp in imports:


            try:

                result = resolve_internal(
                    imp,
                    trie,
                    current_module_id=module_id,
                )

            except Exception:

                # resolver failure
                # must not destroy repository analysis

                continue



            # ==================================================
            # UNKNOWN
            # ==================================================

            if (
                result.kind == "UNKNOWN"
                or
                not result.target_module
            ):

                continue



            target = result.target_module



            # ==================================================
            # SELF IMPORT
            # ==================================================

            if target == module_id:

                continue



            # ==================================================
            # TYPE ONLY
            # ==================================================

            if _is_type_only_import(
                imp
            ):

                _add_edge(
                    soft_edges,
                    module_id,
                    target,
                )

                continue



            # ==================================================
            # HARD DEPENDENCY
            # ==================================================

            if result.kind == "MODULE":

                _add_edge(
                    hard_edges,
                    module_id,
                    target,
                )


            # ==================================================
            # SOFT DEPENDENCY
            # ==================================================

            elif result.kind == "FALLBACK":

                _add_edge(
                    soft_edges,
                    module_id,
                    target,
                )



    return ProjectGraph(

        hard_edges={
            key: value
            for key, value
            in sorted(
                hard_edges.items()
            )
        },

        soft_edges={
            key: value
            for key, value
            in sorted(
                soft_edges.items()
            )
        },

    )
