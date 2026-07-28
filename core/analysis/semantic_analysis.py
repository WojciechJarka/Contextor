# -*- coding: utf-8 -*-

"""
repo_guardian/core/analysis/semantic_analysis.py

Deprecated.
Functionality migrated to `state_analysis.py` and `function_analysis.py`.
Returns empty structures for backwards compatibility with legacy contexts.
"""

def analyze_module_semantics(tree):
    return {
        "import_usage": {},
        "mutability": []
    }
