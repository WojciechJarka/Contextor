"""
repo_guardian/core/graph.py

GRAPH BUILDER v2.0


WARSTWA:

    GRAPH BUILDER


Odpowiedzialność:

- budowa grafu zależności projektu
- konwersja resolver facts -> EdgeInfo
- zachowanie confidence
- zachowanie typu zależności


Nie:

- nie interpretuje architektury
- nie liczy ryzyka
- nie analizuje AST
- nie wykonuje scoringu


Źródło prawdy:

    resolver
    ImportRef
    EdgeInfo


"""

from __future__ import annotations


from .domain.module import (
    Module,
)


from .domain.graph import (
    EdgeInfo,
    ProjectGraph,
)


from .resolver import (
    build_trie,
    resolve_internal,
)



# ==========================================================
# CONFIDENCE
# ==========================================================


CONFIDENCE_MODULE = 1.0

CONFIDENCE_TYPE_ONLY = 0.65

CONFIDENCE_FALLBACK = 0.45



# ==========================================================
# HELPERS
# ==========================================================


def _is_type_only_import(
    import_ref
) -> bool:
    """
    Detect type-only imports.
    """

    return getattr(
        import_ref,
        "type_only",
        False
    )



def _edge_exists(
    edges,
    target
):
    """
    Prevent duplicate edges.
    """

    return any(

        edge.target == target

        for edge in edges

    )



def _add_edge(
    graph,
    source,
    edge
):
    """
    Central edge insertion.

    Keeps deterministic ordering.
    """


    graph.setdefault(
        source,
        []
    )


    existing = graph[source]


    for item in existing:


        if (

            item.target == edge.target

            and

            item.edge_type == edge.edge_type

        ):

            return



    existing.append(
        edge
    )



# ==========================================================
# EDGE FACTORY
# ==========================================================


def _create_edge(
    target,
    edge_type,
    confidence,
    reason
):

    return EdgeInfo(

        target=target,

        edge_type=edge_type,

        confidence=confidence,

        reason=reason,

        count=1,

    )



# ==========================================================
# PUBLIC API
# ==========================================================


def build_graph(
    modules: dict[str, Module]
) -> ProjectGraph:
    """
    Builds project dependency graph.


    Pipeline:


        Module

          |

          v


       resolver


          |

          v


       EdgeInfo


          |

          v


       ProjectGraph


    """



    hard_edges = {}

    soft_edges = {}



    trie = build_trie(
        modules.keys()
    )



    for module_id in sorted(
        modules.keys()
    ):


        module = modules[module_id]



        hard_edges.setdefault(
            module_id,
            []
        )


        soft_edges.setdefault(
            module_id,
            []
        )



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

                    _create_edge(

                        target,

                        edge_type="type_only_import",

                        confidence=CONFIDENCE_TYPE_ONLY,

                        reason="type_only",

                    )

                )


                continue



            # ==================================================
            # MODULE
            # ==================================================

            if result.kind == "MODULE":


                _add_edge(

                    hard_edges,

                    module_id,

                    _create_edge(

                        target,

                        edge_type="import",

                        confidence=CONFIDENCE_MODULE,

                        reason="resolved_module",

                    )

                )


            # ==================================================
            # FALLBACK
            # ==================================================

            elif result.kind == "FALLBACK":


                _add_edge(

                    soft_edges,

                    module_id,

                    _create_edge(

                        target,

                        edge_type="fallback_import",

                        confidence=CONFIDENCE_FALLBACK,

                        reason="resolver_fallback",

                    )

                )



    # ======================================================
    # DETERMINISTIC SORTING
    # ======================================================


    for graph in (
        hard_edges,
        soft_edges,
    ):


        for module_id in graph:


            graph[module_id] = sorted(

                graph[module_id],

                key=lambda edge:

                (

                    edge.target,

                    edge.edge_type,

                )

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



# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [

    "build_graph",

]
