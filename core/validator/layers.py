# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/layers.py

Layer and dependency validation.
"""

from ..domain.module import (
    Module,
)

from ..domain.graph import (
    ProjectGraph,
)

from ..domain.validation import (
    ValidationError,
)
from .helpers import (
    get_layer,
)

from .rules import (
    FORBIDDEN_LAYER_RULES,
    FORBIDDEN_PREFIX_RULES,
)


def validate_layer_rules(
    modules: dict[str, Module],
    graph: ProjectGraph,
) -> list[ValidationError]:

    errors: list[ValidationError] = []

    hard_edges = graph.hard_edges

    for module_id in modules:

        source_layer = get_layer(
            module_id
        )

        for dependency in hard_edges.get(
            module_id,
            set(),
        ):

            target_layer = get_layer(
                dependency
            )

            for (
                forbidden_source,
                forbidden_target,
                description,
            ) in FORBIDDEN_LAYER_RULES:

                if (
                    source_layer == forbidden_source
                    and target_layer == forbidden_target
                ):

                    errors.append(
                        ValidationError(
                            kind="LAYER",
                            message=(
                                f"{description}: "
                                f"{module_id} -> {dependency}"
                            ),
                            nodes=[
                                module_id,
                                dependency,
                            ],
                        )
                    )

    return errors


def validate_forbidden_dependencies(
    modules: dict[str, Module],
    graph: ProjectGraph,
) -> list[ValidationError]:

    errors: list[ValidationError] = []

    hard_edges = graph.hard_edges

    for module_id in modules:

        source_layer = get_layer(
            module_id
        )

        for dependency in hard_edges.get(
            module_id,
            set(),
        ):

            for (
                forbidden_source,
                forbidden_prefix,
                description,
            ) in FORBIDDEN_PREFIX_RULES:

                if (
                    source_layer == forbidden_source
                    and dependency.startswith(
                        forbidden_prefix
                    )
                ):

                    errors.append(
                        ValidationError(
                            kind="FORBIDDEN_DEPENDENCY",
                            message=(
                                f"{description}: "
                                f"{module_id} -> {dependency}"
                            ),
                            nodes=[
                                module_id,
                                dependency,
                            ],
                        )
                    )

    return errors
