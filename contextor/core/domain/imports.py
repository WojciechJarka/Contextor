"""
contextor/core/domain/imports.py

Domain model:
raw AST import representation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportRef:
    """
    Surowy fakt o imporcie AST.
    """

    module: str | None

    level: int

    names: list[str]

    is_from_import: bool

    is_local: bool = False

    type_only: bool = False
