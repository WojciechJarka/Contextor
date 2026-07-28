# -*- coding: utf-8 -*-

"""
repo_guardian/core/risk_analysis.py

AST risk and side effect extraction.
[REFACTORED - EffectVisitor migrated to function_analysis.py as FunctionMutationVisitor]
"""

import ast
import math

from repo_guardian.core.domain.rules import SIDE_EFFECT_RULES, RISK_RULES

def analyze_effects(tree):
    """
    Deprecated. EffectVisitor overhead removed.
    Returns empty set to satisfy existing module interfaces
    if still imported anywhere else (like facade).
    """
    return {
        "side_effects": [],
        "risks": []
    }
