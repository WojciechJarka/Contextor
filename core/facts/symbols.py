# -*- coding: utf-8 -*-

"""
repo_guardian/core/facts/symbols.py

CANONICAL SYMBOL MODEL

Jedno źródło prawdy dla symboli projektu.

Odpowiada za:
- identyfikację symbolu
- lokalizację
- typ symbolu
- publiczność
- relacje modułowe

Nie analizuje:
- użycia
- scoringu
- ryzyka
- refaktoryzacji
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
    Lokalizacja symbolu w kodzie.
    """

    file: str

    line: int



@dataclass(frozen=True)
class SymbolRecord:
    """
    Kanoniczny rekord symbolu.

    Każdy symbol w systemie
    musi mieć jeden identyfikator.
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
        Nazwa lokalna.

        np.

        repo.auth.AuthManager

        ->

        AuthManager
        """

        return self.name



    def qualified_name(self) -> str:
        """
        Pełna nazwa symbolu.
        """

        return self.id



@dataclass
class SymbolRegistry:
    """
    Kontener wszystkich symboli projektu.

    Źródło prawdy dla:
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
        Dodaje symbol.

        Nadpisanie tego samego ID
        jest niedozwolone logicznie,
        ale ostatnia wersja wygrywa.
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
