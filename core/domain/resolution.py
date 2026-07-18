# -*- coding: utf-8 -*-

"""
repo_guardian/core/domain/resolution.py

Resolver result model.
"""

from dataclasses import dataclass

from typing import Optional, Literal


@dataclass(frozen=True)
class ResolutionResult:
    """
    Wynik resolvera importów.
    """

    target_module: Optional[str]

    kind: Literal[
        "MODULE",
        "FALLBACK",
        "UNKNOWN",
    ]

    used_symbol: Optional[str] = None
