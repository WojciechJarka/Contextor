# -*- coding: utf-8 -*-

"""
repo_guardian/core/facts/symbols.py

CANONICAL SYMBOL MODEL

Single source of truth for project symbols.

Responsible for:
- symbol identification
- location
- symbol kind
- public visibility
- module relations

Does not analyze:
- usage
- scoring
- risk
- refactoring
"""


from dataclasses import dataclass, field
from typing import Literal


SymbolKind = Literal[
    "function",
    "class",
    "method",
    "variable",
]


@dataclass(frozen=True)
class SymbolLocation:
    """
    Symbol location in code.
    """

    file: str

    line: int



@dataclass(frozen=True)
class SymbolRecord:
    """
    Canonical symbol record.

    Each symbol in the system
    must have a single identifier.
    """

    id: str

    module_id: str

    name: str

    kind: SymbolKind

    location: SymbolLocation

    public: bool = True

    parent: str | None = None



    def short_name(self) -> str:
        """
        Local name.

    e.g.

    repo.auth.AuthManager

    ->

    AuthManager
        """

        return self.name



    def qualified_name(self) -> str:
        """
        Fully qualified symbol name.
        """

        return self.id



@dataclass
class SymbolRegistry:
    """
    Container for all project symbols.

    Source of truth for:
    - export analysis
    - reference engine
    - API consumers
    - dead code
    """

    symbols: dict[str, SymbolRecord] = field(
        default_factory=dict
    )


    def add(
        self,
        symbol: SymbolRecord
    ):
        """
        Adds a symbol.

        Overwriting the same ID
        is logically not allowed,
        but the last version wins.
        """

        self.symbols[
            symbol.id
        ] = symbol



    def get(
        self,
        symbol_id: str
    ) -> SymbolRecord | None:

        return self.symbols.get(
            symbol_id
        )



    def by_module(
        self,
        module_id: str
    ) -> list[SymbolRecord]:

        return sorted(
            [
                s
                for s in self.symbols.values()
                if s.module_id == module_id
            ],
            key=lambda x: x.id
        )



    def public_symbols(
        self
    ) -> list[SymbolRecord]:

        return sorted(
            [
                s
                for s in self.symbols.values()
                if s.public
            ],
            key=lambda x: x.id
        )



    def ids(
        self
    ) -> list[str]:

        return sorted(
            self.symbols.keys()
        )
