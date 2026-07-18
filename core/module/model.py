# -*- coding: utf-8 -*-

"""
repo_guardian/core/module/model.py

Unified module contract.

Single source of truth
between analyzers and reporting.
"""


from dataclasses import dataclass, field

from typing import Any



@dataclass
class ModuleIdentity:

    module_id: str

    path: str

    absolute_path: str



@dataclass
class ModuleDependencies:

    hard: set[str] = field(
        default_factory=set
    )

    soft: set[str] = field(
        default_factory=set
    )

    dependents: set[str] = field(
        default_factory=set
    )



@dataclass
class ModuleMetrics:

    complexity: float = 0.0

    risk: float = 0.0

    api_size: int = 0

    dependency_count: int = 0

    consumer_count: int = 0



@dataclass
class ModuleFindings:

    risks: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    opportunities: list[str] = field(
        default_factory=list
    )



@dataclass
class ModuleContext:

    identity: ModuleIdentity

    source_module: Any | None = None

    symbols: dict = field(
        default_factory=dict
    )

    dependencies: ModuleDependencies = field(
        default_factory=ModuleDependencies
    )

    metrics: ModuleMetrics = field(
        default_factory=ModuleMetrics
    )

    findings: ModuleFindings = field(
        default_factory=ModuleFindings
    )

    analyses: dict = field(
        default_factory=dict
    )
