# -*- coding: utf-8 -*-

"""
repo_guardian/core/facts/build.py

REPOSITORY FACT BUILDER

Buduje pełny kontekst faktów repozytorium.

Pipeline:

    repository
        |
        v
    modules index
        |
        v
    dependency graph
        |
        v
    symbol registry
        |
        v
    reference graph
        |
        v
    RepositoryContext


Nie zawiera:
- scoringu
- hotspotów
- debt
- raportowania
"""


from repo_guardian.core.indexer import (
    build_index,
)


from repo_guardian.core.graph import (
    build_graph,
)


from .symbol_index import (
    build_facts_symbol_index,
)


from .references import (
    build_reference_graph,
)


from .context import (
    RepositoryContext,
)



# ==========================================================
# PUBLIC BUILDER
# ==========================================================


def build_repository_context(
    root_path: str,
) -> RepositoryContext:
    """
    Buduje kompletny stan faktów repozytorium.

    Jedyny zalecany entrypoint
    dla warstw wyżej.
    """


    # ------------------------------------------------------
    # MODULE INDEX
    # ------------------------------------------------------

    modules = build_index(
        root_path
    )


    # ------------------------------------------------------
    # DEPENDENCY GRAPH
    # ------------------------------------------------------

    graph = build_graph(
        modules
    )


    # ------------------------------------------------------
    # SYMBOL INDEX
    # ------------------------------------------------------

    symbols = build_facts_symbol_index(
        modules,
        root_path,
    )


    # ------------------------------------------------------
    # SYMBOL REFERENCES
    # ------------------------------------------------------

    references = build_reference_graph(
        modules,
        symbols,
        root_path,
    )


    # ------------------------------------------------------
    # CONTEXT
    # ------------------------------------------------------

    return RepositoryContext(

        modules=modules,

        graph=graph,

        symbols=symbols,

        references=references,

        root_path=root_path,

    )
