# -*- coding: utf-8 -*-

"""
repo_guardian/core/facts/context.py

REPOSITORY FACT CONTEXT

Centralny kontener faktów projektu.

Łączy:

- Module index
- Dependency graph
- Symbol registry
- Symbol reference graph


Nie zawiera:

- scoringu
- hotspotów
- debt
- rekomendacji
"""


from dataclasses import dataclass


from repo_guardian.core.domain.graph import (
    ProjectGraph,
)


from .symbols import (
    SymbolRegistry,
)


from .references import (
    ReferenceGraph,
)



@dataclass(frozen=True)
class RepositoryContext:
    """
    Pełny stan analizy repozytorium.

    Wszystkie warstwy raportujące
    powinny korzystać z tego obiektu.
    """

    modules: dict

    graph: ProjectGraph

    symbols: SymbolRegistry

    references: ReferenceGraph

    root_path: str



    # ======================================================
    # MODULE LOOKUP
    # ======================================================


    def module(
        self,
        module_id: str,
    ):

        return self.modules.get(
            module_id
        )



    # ======================================================
    # SYMBOL LOOKUP
    # ======================================================


    def symbol(
        self,
        symbol_id: str,
    ):

        return self.symbols.get(
            symbol_id
        )



    def module_symbols(
        self,
        module_id: str,
    ):

        return self.symbols.by_module(
            module_id
        )



    # ======================================================
    # REFERENCE LOOKUP
    # ======================================================


    def references_for(
        self,
        symbol_id: str,
    ):

        return self.references.get(
            symbol_id
        )



    # ======================================================
    # DEPENDENCY LOOKUP
    # ======================================================


    def dependencies(
        self,
        module_id: str,
    ) -> list[str]:

        return sorted(
            self.graph.hard_edges.get(
                module_id,
                set()
            )
        )



    def dependents(
        self,
        module_id: str,
    ) -> list[str]:

        result = []


        for source, targets in (
            self.graph.hard_edges.items()
        ):

            if module_id in targets:

                result.append(
                    source
                )


        return sorted(
            result
        )



    def soft_dependencies(
        self,
        module_id: str,
    ) -> list[str]:

        return sorted(
            self.graph.soft_edges.get(
                module_id,
                set()
            )
        )
