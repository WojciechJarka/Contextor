# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/rules.py

Architecture validation rules.
"""

# ==========================================================
# LAYER RULES
# ==========================================================

FORBIDDEN_LAYER_RULES = [
    (
        "ui",
        "cli",
        "ui -> cli dependency",
    ),
    (
        "cli",
        "ui",
        "cli -> ui dependency",
    ),
]


# ==========================================================
# PREFIX RULES
# ==========================================================

FORBIDDEN_PREFIX_RULES = [
    (
        "ui",
        "core.internal",
        "ui accessing internal core implementation",
    ),
]
