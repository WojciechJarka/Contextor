# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/helpers.py

Validator helper functions.
"""


def get_layer(module_id: str) -> str:
    """
    Return the architectural layer of a module.

    Example:
        core.reporting -> core
        ui.gui -> ui
    """

    return module_id.split(".")[0]
