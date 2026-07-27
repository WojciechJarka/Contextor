# -*- coding: utf-8 -*-

"""
repo_guardian/core/facts/references.py

CANONICAL SYMBOL REFERENCE GRAPH

Źródło prawdy relacji symbolicznych.

Buduje fakty:

- imported_by
- called_by
- inherited_by
- instantiated_by

Nie robi:

- scoringu
- dead code
- ryzyka
- refactoring advice

"""

import ast

from pathlib import Path
from dataclasses import dataclass, field


from .symbols import (
    SymbolRegistry,
)



# ==========================================================
# DATA MODEL
# ==========================================================


@dataclass
class SymbolReference:

    imported_by: set[str] = field(
        default_factory=set
    )

    called_by: set[str] = field(
        default_factory=set
    )

    inherited_by: set[str] = field(
        default_factory=set
    )

    instantiated_by: set[str] = field(
        default_factory=set
    )



@dataclass
class ReferenceGraph:

    references: dict[str, SymbolReference] = field(
        default_factory=dict
    )


    def ensure(
        self,
        symbol_id: str
    ):

        if symbol_id not in self.references:

            self.references[
                symbol_id
            ] = SymbolReference()



    def get(
        self,
        symbol_id: str
    ):

        return self.references.get(
            symbol_id,
            SymbolReference()
        )



# ==========================================================
# RESOLUTION HELPERS
# ==========================================================


def _resolve_name(
    name: str,
    registry: SymbolRegistry,
) -> list[str]:
    """
    Rozwiązuje nazwę AST
    do kanonicznych symboli.


    Przykład:

    AuthManager

    może wskazać:

    core.auth.AuthManager
    """


    result = []


    for symbol_id, symbol in registry.symbols.items():

        if symbol.name == name:

            result.append(
                symbol_id
            )


    return sorted(
        result
    )



def _attribute_name(
    node
):

    if isinstance(
        node,
        ast.Name
    ):

        return node.id


    if isinstance(
        node,
        ast.Attribute
    ):

        parent = _attribute_name(
            node.value
        )


        if parent:

            return (
                f"{parent}.{node.attr}"
            )


        return node.attr


    return None



# ==========================================================
# VISITOR
# ==========================================================


class ReferenceVisitor(
    ast.NodeVisitor
):


    def __init__(
        self,
        module_id,
        registry,
        graph,
    ):

        self.module_id = module_id

        self.registry = registry

        self.graph = graph

        self.aliases = {}

        self.current_class = None



    # ------------------------------------------------------
    # IMPORTS
    # ------------------------------------------------------


    def visit_ImportFrom(
        self,
        node
    ):


        for item in node.names:

            local = (
                item.asname
                or item.name
            )


            target = (
                f"{node.module}.{item.name}"
                if node.module
                else item.name
            )


            self.aliases[
                local
            ] = target



            for symbol_id in _resolve_name(
                item.name,
                self.registry
            ):

                self.graph.ensure(
                    symbol_id
                )

                self.graph.references[
                    symbol_id
                ].imported_by.add(
                    self.module_id
                )


        self.generic_visit(
            node
        )



    def visit_Import(
        self,
        node
    ):


        for item in node.names:

            local = (
                item.asname
                or item.name.split(".")[-1]
            )


            self.aliases[
                local
            ] = item.name


        self.generic_visit(
            node
        )



    # ------------------------------------------------------
    # CLASS CONTEXT
    # ------------------------------------------------------


    def visit_ClassDef(
        self,
        node
    ):

        old = self.current_class

        self.current_class = node.name


        for base in node.bases:

            name = _attribute_name(
                base
            )


            if not name:
                continue


            for symbol_id in _resolve_name(
                name.split(".")[-1],
                self.registry
            ):

                self.graph.ensure(
                    symbol_id
                )

                self.graph.references[
                    symbol_id
                ].inherited_by.add(
                    self.module_id
                )


        self.generic_visit(
            node
        )


        self.current_class = old



    # ------------------------------------------------------
    # CALLS
    # ------------------------------------------------------


    def visit_Call(
        self,
        node
    ):


        name = _attribute_name(
            node.func
        )


        if not name:

            return



        short = (
            name.split(".")[-1]
        )


        for symbol_id in _resolve_name(
            short,
            self.registry
        ):


            self.graph.ensure(
                symbol_id
            )


            self.graph.references[
                symbol_id
            ].called_by.add(
                self.module_id
            )


        self.generic_visit(
            node
        )



# ==========================================================
# BUILDER
# ==========================================================


def build_reference_graph(
    modules,
    registry,
    root_path,
):
    """
    Buduje globalny graf referencji.

    Jedno źródło prawdy dla użycia symboli.
    """

    graph = ReferenceGraph()



    for module_id, module in sorted(
        modules.items()
    ):


        file_path = (
            Path(root_path)
            /
            module.path
        )


        try:

            tree = ast.parse(
                file_path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:

            continue



        visitor = ReferenceVisitor(

            module_id,

            registry,

            graph,

        )


        visitor.visit(
            tree
        )



    return graph
