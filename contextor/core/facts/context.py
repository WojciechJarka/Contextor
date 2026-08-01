"""
contextor/core/facts/context.py

REPOSITORY FACT CONTEXT

Central container of project facts.

Combines:

- Module index
- Dependency graph
- Symbol registry
- Symbol reference graph


Does not include:

- scoring
- hotspots
- debt
- recommendations
"""

from dataclasses import dataclass

from contextor.core.domain.graph import (
    ProjectGraph,
)

from .references import (
    ReferenceGraph,
)
from .symbols import (
    SymbolRegistry,
)


@dataclass(frozen=True)
class RepositoryContext:
    """
    Full state of repository analysis.

    All reporting layers
    should use this object.
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

        return self.modules.get(module_id)

    # ======================================================
    # SYMBOL LOOKUP
    # ======================================================

    def symbol(
        self,
        symbol_id: str,
    ):

        return self.symbols.get(symbol_id)

    def module_symbols(
        self,
        module_id: str,
    ):

        return self.symbols.by_module(module_id)

    # ======================================================
    # REFERENCE LOOKUP
    # ======================================================

    def references_for(
        self,
        symbol_id: str,
    ):

        return self.references.get(symbol_id)

    # ======================================================
    # DEPENDENCY LOOKUP
    # ======================================================

    def dependencies(
        self,
        module_id: str,
    ) -> list[str]:

        return sorted(self.graph.hard_edges.get(module_id, set()))

    def dependents(
        self,
        module_id: str,
    ) -> list[str]:

        result = []

        for source, targets in self.graph.hard_edges.items():
            if module_id in targets:
                result.append(source)

        return sorted(result)

    def soft_dependencies(
        self,
        module_id: str,
    ) -> list[str]:

        return sorted(self.graph.soft_edges.get(module_id, set()))
