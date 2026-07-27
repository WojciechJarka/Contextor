# -*- coding: utf-8 -*-

"""
repo_guardian.core.module.types

Canonical domain models.

This module replaces the old:
    core.types

during migration.

No behaviour changes.
Only contract relocation.
"""


from dataclasses import dataclass

from typing import (
    Optional,
    Literal,
)



@dataclass(frozen=True)
class ImportRef:
    """
    Raw AST import representation.
    """

    module: str | None

    level: int

    names: list[str]

    is_from_import: bool

    is_local: bool



@dataclass(frozen=True)
class Module:
    """
    Indexed project module.
    """

    module_id: str

    path: str

    absolute_path: str

    imports: list[ImportRef]



@dataclass(frozen=True)
class ProjectGraph:
    """
    Dependency graph of project modules.
    """

    hard_edges: dict[str, set[str]]

    soft_edges: dict[str, set[str]]



@dataclass(frozen=True)
class ResolutionResult:
    """
    Result of import resolution.
    """

    target_module: Optional[str]

    kind: Literal[
        "MODULE",
        "FALLBACK",
        "UNKNOWN",
    ]

    used_symbol: Optional[str] = None



@dataclass(frozen=True)
class ValidationError:
    """
    Architecture validation issue.
    """

    rule: str

    message: str

    module: Optional[str] = None
