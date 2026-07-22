# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/validate.py

Validator entry point.

The validator performs lightweight architectural validation.
It detects obvious architectural violations only.

Risk scoring and refactoring analysis are performed by
the reporting layer.
"""

from ..domain.module import (
    Module,
)

from ..domain.validation import (
    ValidationError,
)

from ..domain.graph import (
    ProjectGraph,
)

from .cycles import (
    validate_cycles,
)

from .layers import (
    validate_layer_rules,
    validate_forbidden_dependencies,
)

from .collisions import (
    validate_name_collisions,
)

def validate(
    modules: dict[str, Module],
    graph: ProjectGraph,
) -> list[ValidationError]:
    """
    Validate project architecture.
    """

    errors: list[ValidationError] = []

    errors.extend(
        validate_cycles(
            graph
        )
    )

    errors.extend(
        validate_layer_rules(
            modules,
            graph,
        )
    )

    errors.extend(
        validate_forbidden_dependencies(
            modules,
            graph,
        )
    )

    # Dodane sprawdzenie kolizji nazw semantycznych
    errors.extend(
        validate_name_collisions(
            modules,
        )
    )

    return errors
def validate(
    modules: dict[str, Module],
    graph: ProjectGraph,
) -> list[ValidationError]:
    """
    Validate project architecture.
    """

    errors: list[ValidationError] = []

    errors.extend(
        validate_cycles(
            graph
        )
    )

    errors.extend(
        validate_layer_rules(
            modules,
            graph,
        )
    )

    errors.extend(
        validate_forbidden_dependencies(
            modules,
            graph,
        )
    )

    return errors
