# -*- coding: utf-8 -*-

"""
repo_guardian/core/domain/imports.py

Domain model:
raw AST import representation.
"""

from dataclasses import dataclass

from typing import Optional


@dataclass(frozen=True)
class ImportRef:
    """
    Surowy fakt o imporcie AST.
    """

    module: Optional[str]

    level: int

    names: list[str]

    is_from_import: bool

    is_local: bool = False

    type_only: bool = False
