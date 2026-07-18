# -*- coding: utf-8 -*-

"""
repo_guardian/core/module/resolution.py

resolution contracts
"""


from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class ResolutionResult:

    target_module: Optional[str]

    kind: Literal[
        "MODULE",
        "FALLBACK",
        "UNKNOWN"
    ]

    used_symbol: Optional[str] = None
