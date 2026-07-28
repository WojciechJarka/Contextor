# -*- coding: utf-8 -*-

"""
repo_guardian/core/domain/module.py

Repository module model.
"""

from dataclasses import dataclass
from functools import lru_cache
import ast

@lru_cache(maxsize=1024)
def _get_cached_ast(absolute_path: str):
    try:
        with open(absolute_path, 'r', encoding='utf-8') as f:
            return ast.parse(f.read())
    except Exception:
        return None

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

    @property
    def ast_tree(self):
        return _get_cached_ast(self.absolute_path)
