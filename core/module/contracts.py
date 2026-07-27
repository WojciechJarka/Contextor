# -*- coding: utf-8 -*-

"""
repo_guardian/core/module/contracts.py

Module identity contracts
"""


from dataclasses import dataclass, field

from .imports import ImportRef


@dataclass(frozen=True)
class Module:

    module_id: str

    path: str

    absolute_path: str

    imports: list[ImportRef] = field(
        default_factory=list
    )
