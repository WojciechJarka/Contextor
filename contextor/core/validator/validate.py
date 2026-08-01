"""
contextor/core/validator/validate.py

Validator entry point.
"""

from ..domain.graph import ProjectGraph
from ..domain.module import Module
from ..domain.validation import ValidationError
from ..errors import checkpoint
from .collisions import validate_name_collisions
from .cycles import validate_cycles
from .layers import (
    validate_forbidden_dependencies,
    validate_layer_rules,
)


def validate(
    modules: dict[str, Module], graph: ProjectGraph, progress_callback=None
) -> list[ValidationError]:
    """
    Validate project architecture.
    """

    errors: list[ValidationError] = []

    checkpoint(progress_callback, "Validating cycles...")
    errors.extend(validate_cycles(graph, progress_callback=progress_callback))

    checkpoint(progress_callback, "Validating layer rules...")
    errors.extend(validate_layer_rules(modules, graph))

    checkpoint(progress_callback, "Validating forbidden dependencies...")
    errors.extend(validate_forbidden_dependencies(modules, graph))

    checkpoint(progress_callback, "Validating name collisions...")
    errors.extend(validate_name_collisions(modules))

    return errors
