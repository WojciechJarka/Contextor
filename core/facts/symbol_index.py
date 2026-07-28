# -*- coding: utf-8 -*-

"""
repo_guardian/core/facts/symbol_index.py

CANONICAL SYMBOL INDEX BUILDER

AST -> SymbolRegistry

Odpowiedzialność:
- znalezienie deklaracji symboli
- nadanie stabilnych ID
- zapis lokalizacji
- zapis hierarchii symboli

Nie analizuje:
- użycia
- importów
- referencji
- dead code
- jakości
"""


import ast

from pathlib import Path


from .symbols import (
    SymbolRegistry,
    SymbolRecord,
    SymbolLocation,
)



# ==========================================================
# HELPERS
# ==========================================================


def _symbol_id(
    module_id: str,
    name: str,
    parent: str | None = None,
) -> str:
    """
    Buduje stabilny identyfikator.

    Przykłady:

    module.Class

    module.function

    module.Class.method
    """

    if parent:

        return (
            f"{module_id}.{parent}.{name}"
        )


    return (
        f"{module_id}.{name}"
    )



def _public(
    name: str
) -> bool:
    """
    Python convention.

    _private -> false
    """

    return not name.startswith("_")



# ==========================================================
# AST VISITOR
# ==========================================================


class SymbolIndexVisitor(
    ast.NodeVisitor
):


    def __init__(
        self,
        module_id: str,
        file_path: str,
    ):

        self.module_id = module_id

        self.file_path = file_path

        self.registry = SymbolRegistry()

        self.class_stack: list[str] = []



    # ------------------------------------------------------
    # FUNCTIONS
    # ------------------------------------------------------


    def visit_FunctionDef(
        self,
        node
    ):

        self._add_function(
            node
        )

        self.generic_visit(
            node
        )



    def visit_AsyncFunctionDef(
        self,
        node
    ):

        self._add_function(
            node
        )

        self.generic_visit(
            node
        )



    def _add_function(
        self,
        node
    ):

        parent = (
            self.class_stack[-1]
            if self.class_stack
            else None
        )


        kind = (
            "method"
            if parent
            else "function"
        )


        record = SymbolRecord(

            id=_symbol_id(
                self.module_id,
                node.name,
                parent,
            ),

            module_id=self.module_id,

            name=node.name,

            kind=kind,

            location=SymbolLocation(

                file=self.file_path,

                line=node.lineno,

            ),

            public=_public(
                node.name
            ),

            parent=parent,

        )


        self.registry.add(
            record
        )



    # ------------------------------------------------------
    # CLASSES
    # ------------------------------------------------------


    def visit_ClassDef(
        self,
        node
    ):


        record = SymbolRecord(

            id=_symbol_id(
                self.module_id,
                node.name,
            ),

            module_id=self.module_id,

            name=node.name,

            kind="class",

            location=SymbolLocation(

                file=self.file_path,

                line=node.lineno,

            ),

            public=_public(
                node.name
            ),

        )


        self.registry.add(
            record
        )


        self.class_stack.append(
            node.name
        )


        self.generic_visit(
            node
        )


        self.class_stack.pop()



    # ------------------------------------------------------
    # MODULE VARIABLES
    # ------------------------------------------------------


    def visit_Assign(
        self,
        node
    ):


        for target in node.targets:


            if not isinstance(
                target,
                ast.Name
            ):
                continue



            record = SymbolRecord(

                id=_symbol_id(
                    self.module_id,
                    target.id,
                ),

                module_id=self.module_id,

                name=target.id,

                kind="variable",

                location=SymbolLocation(

                    file=self.file_path,

                    line=node.lineno,

                ),

                public=_public(
                    target.id
                ),

            )


            self.registry.add(
                record
            )



# ==========================================================
# PUBLIC API
# ==========================================================


def build_facts_symbol_index(
    modules: dict,
    root_path: str,
) -> SymbolRegistry:
    """
    Buduje globalny indeks symboli projektu.

    Źródła:
        Module index
        AST


    Wynik:

        SymbolRegistry
    """


    registry = SymbolRegistry()



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



        visitor = SymbolIndexVisitor(

            module_id,

            str(file_path),

        )


        visitor.visit(
            tree
        )


        for symbol in visitor.registry.symbols.values():

            registry.add(
                symbol
            )



    return registry
