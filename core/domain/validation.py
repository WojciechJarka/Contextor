# -*- coding: utf-8 -*-

"""
repo_guardian/core/domain/validation.py

Validation domain model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationError:

    kind: str

    message: str

    nodes: list[str]
