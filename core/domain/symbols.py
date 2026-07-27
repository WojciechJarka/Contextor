# -*- coding: utf-8 -*-

"""
repo_guardian/core/domain/symbols.py


CANONICAL SYMBOL DOMAIN MODEL


Cel modułu:

    Definiuje jedyny wspólny model symboli
    używany przez analizatory repozytorium.


Warstwa:

    DOMAIN / FACT MODEL


Odpowiedzialność:

- reprezentacja symbolu Python
- reprezentacja symboli modułu
- podstawowe filtrowanie i indeksowanie


Nie robi:

- parsowania AST
- wykrywania symboli
- analizy użycia
- analizy importów
- analizy zależności
- scoringu
- ryzyka
- dead code
- raportowania


Źródła danych:

    symbol_analysis.py


Użycie:

    AST extractor
          |
          v
    SymbolRef
          |
          v
    ModuleSymbols
          |
          v
    dalsze warstwy analizy


Założenia:

- SymbolRef jest pojedynczym faktem.
- Model nie interpretuje znaczenia symbolu.
- Model nie wie, czy symbol jest ważny.
- Model nie wie, czy symbol jest używany.


Przykłady:

Klasa:

    SymbolRef(
        name="Client",
        module="app.client",
        kind="class"
    )


Metoda:

    SymbolRef(
        name="run",
        module="app.client",
        kind="method",
        parent="Client"
    )


qualified_name:

    Client.run


"""


from dataclasses import dataclass, field
from typing import Literal
from dataclasses import dataclass

@dataclass(frozen=True)
class CallResolution:
    call_site: str
    symbol: str
    possible_targets: list[str]
    confidence: float
    resolution: str
    reason: str

# ==========================================================
# SYMBOL TYPES
# ==========================================================


SymbolKind = Literal[
    "class",
    "function",
    "method",
    "global",
]



# ==========================================================
# SYMBOL REFERENCE
# ==========================================================


@dataclass(
    frozen=True
)
class SymbolRef:
    """
    Pojedynczy symbol projektu.

    Jest niemutowalnym faktem.

    Nie przechowuje:

    - użycia
    - referencji
    - konsumentów
    - ryzyka
    - zależności


    Attributes:

        name:
            lokalna nazwa symbolu.


        module:
            moduł, w którym symbol istnieje.


        kind:
            rodzaj symbolu.


        parent:
            rodzic dla metod.

            Przykład:

                class Client:
                    def run()


            reprezentacja:

                name="run"
                parent="Client"


        exported:
            informacja, czy symbol został
            wykryty jako eksportowany API.

    """


    name: str

    module: str

    kind: SymbolKind


    parent: str | None = None


    exported: bool = False



    @property
    def qualified_name(
        self
    ) -> str:
        """
        Pełna nazwa symbolu.

        Przykłady:

            Client

        albo:

            Client.run

        """

        if self.parent:

            return (
                f"{self.parent}.{self.name}"
            )


        return self.name



    @property
    def module_symbol_name(
        self
    ) -> str:
        """
        Nazwa z modułem.

        Przykład:

            app.client.Client

        """

        return (
            f"{self.module}.{self.qualified_name}"
        )



# ==========================================================
# MODULE SYMBOL COLLECTION
# ==========================================================


@dataclass
class ModuleSymbols:
    """
    Kolekcja symboli pojedynczego modułu.


    Przykład:

        module:

            repo_guardian.core.foo


        symbols:

            Foo
            Foo.run
            helper


    Klasa nie analizuje symboli.
    Jest tylko kontenerem domenowym.

    """


    module: str


    symbols: list[SymbolRef] = field(
        default_factory=list
    )



    def add(
        self,
        symbol: SymbolRef
    ) -> None:
        """
        Dodaje symbol.

        """

        self.symbols.append(
            symbol
        )



    def extend(
        self,
        symbols: list[SymbolRef]
    ) -> None:
        """
        Dodaje wiele symboli.
        """

        self.symbols.extend(
            symbols
        )



    def by_kind(
        self,
        kind: SymbolKind
    ) -> list[SymbolRef]:
        """
        Zwraca symbole danego typu.
        """

        return [
            symbol
            for symbol in self.symbols
            if symbol.kind == kind
        ]



    def exported_symbols(
        self
    ) -> list[SymbolRef]:
        """
        Zwraca symbole oznaczone jako API.
        """

        return [
            symbol
            for symbol in self.symbols
            if symbol.exported
        ]



    def names(
        self
    ) -> list[str]:
        """
        Lista nazw kwalifikowanych.

        Przykład:

            [
                "Client",
                "Client.run"
            ]

        """

        return sorted(
            {
                symbol.qualified_name
                for symbol in self.symbols
            }
        )



    def contains(
        self,
        name: str
    ) -> bool:
        """
        Sprawdza istnienie symbolu.
        """

        return any(
            symbol.qualified_name == name
            for symbol in self.symbols
        )



# ==========================================================
# HELPERS
# ==========================================================


def symbol_names(
    symbols: list[SymbolRef]
) -> list[str]:
    """
    Zwraca stabilną listę nazw symboli.

    Używane tam, gdzie warstwa wyżej
    nadal pracuje na prostych stringach.

    """

    return sorted(
        {
            symbol.qualified_name
            for symbol in symbols
        }
    )



def group_by_kind(
    symbols: list[SymbolRef]
) -> dict[str, list[SymbolRef]]:
    """
    Grupuje symbole według rodzaju.

    Wynik:

    {
        "class": [],
        "function": [],
        "method": [],
        "global": []
    }

    """

    result = {
        "class": [],
        "function": [],
        "method": [],
        "global": [],
    }


    for symbol in symbols:

        result[
            symbol.kind
        ].append(
            symbol
        )


    return result



# ==========================================================
# EXPORTS
# ==========================================================


__all__ = [

    "SymbolKind",

    "SymbolRef",

    "ModuleSymbols",

    "symbol_names",

    "group_by_kind",

]
