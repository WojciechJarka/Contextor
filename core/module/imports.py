# -*- coding: utf-8 -*-

"""
repo_guardian/core/module/imports.py

CONTRACTS:
    import extraction domain

Źródło prawdy:
    AST indexer

Nie zawiera:
    resolver logic
    graph logic
    reporting logic
"""


from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ImportRef:
    """
    Surowa reprezentacja importu.

    Tworzona przez AST indexer.

    Nie wie:
        - czy moduł istnieje
        - czy import jest poprawny
        - jaka jest architektura
    """

    module: str | None

    level: int

    names: list[str]

    is_from_import: bool

    is_local: bool

    type_only: bool = False

    scope: Literal[
        "global",
        "local"
    ] = "global"
