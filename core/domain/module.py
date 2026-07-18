# -*- coding: utf-8 -*-

"""
repo_guardian/core/domain/module.py

Repository module model.
"""

from dataclasses import dataclass

from .imports import ImportRef


@dataclass(frozen=True)
class Module:
    """
    Reprezentuje moduł projektu.
    """

    module_id: str

    path: str

    absolute_path: str

    imports: list[ImportRef]
