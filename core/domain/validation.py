# -*- coding: utf-8 -*-
"""
repo_guardian/core/domain/validation.py

Validation domain model.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationError:
    kind: str
    message: str
    nodes: list[str] = field(default_factory=list)
    code_snippets: dict = field(default_factory=dict)
    artifact_type: Optional[str] = None
    is_identical: Optional[bool] = None
