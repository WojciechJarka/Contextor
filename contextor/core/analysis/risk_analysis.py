"""
contextor/core/risk_analysis.py

AST risk and side effect extraction.
[REFACTORED - EffectVisitor migrated to function_analysis.py as FunctionMutationVisitor]
"""


def analyze_effects(tree):
    """
    Deprecated. EffectVisitor overhead removed.
    Returns empty set to satisfy existing module interfaces
    if still imported anywhere else (like facade).
    """
    return {"side_effects": [], "risks": []}
