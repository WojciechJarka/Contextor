# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/validate.py

Validator entry point.
"""

from ..domain.module import Module
from ..domain.validation import ValidationError
from ..domain.graph import ProjectGraph

from .cycles import validate_cycles
from .layers import (
    validate_layer_rules,
    validate_forbidden_dependencies,
)

from .collisions import validate_name_collisions


def validate(
    modules: dict[str, Module],
    graph: ProjectGraph,
    progress_callback=None
) -> list[ValidationError]:
    """
    Validate project architecture.
    """

    errors: list[ValidationError] = []

    if progress_callback and not progress_callback(0, 0, "Validating cycles..."): return errors
    errors.extend(
        validate_cycles(
            graph,
            progress_callback=progress_callback
        )
    )

    if progress_callback and not progress_callback(0, 0, "Validating layer rules..."): return errors
    errors.extend(
        validate_layer_rules(
            modules,
            graph,
        )
    )

    if progress_callback and not progress_callback(0, 0, "Validating forbidden dependencies..."): return errors
    errors.extend(
        validate_forbidden_dependencies(
            modules,
            graph,
        )
    )

    if progress_callback and not progress_callback(0, 0, "Validating name collisions..."): return errors
    errors.extend(
        validate_name_collisions(
            modules,
        )
    )


    return errors
