"""
contextor/core/domain/resolution.py

Resolver result model.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ResolutionResult:
    """
    Import resolver result.
    """

    target_module: str | None

    kind: Literal[
        "MODULE",
        "FALLBACK",
        "UNKNOWN",
    ]

    used_symbol: str | None = None
