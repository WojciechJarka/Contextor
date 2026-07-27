# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/cycles.py

Cycle validation.
"""

from ..domain.graph import (
    ProjectGraph,
)

from ..domain.validation import (
    ValidationError,
)

from ..cycles import (
    detect_cycles,
)


def validate_cycles(
    graph: ProjectGraph,
) -> list[ValidationError]:
    """
    Validate dependency cycles.
    """

    errors: list[ValidationError] = []

    cycles = detect_cycles(
        graph.hard_edges
    )

    for cycle in cycles:

        errors.append(
            ValidationError(
                kind="CYCLE",
                message=" -> ".join(cycle),
                nodes=cycle,
            )
        )

    return errors
