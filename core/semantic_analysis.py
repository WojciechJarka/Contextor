# -*- coding: utf-8 -*-

"""
repo_guardian/core/semantic_analysis.py

AST semantic extraction layer.

Facts only.
No quality judgement.

Extracts:
- import usage
- side effects
- risk signals
- exceptions
- argument mutations
"""

import ast
from collections import defaultdict
from repo_guardian.core.mutability_analysis import analyze_mutability as analyze_mutability_impl

# (Removed duplicate ImportUsageVisitor. See core.import_analysis instead)
from repo_guardian.core.import_analysis import extract_import_usage




# No longer used classes. Removed.


def _analyze_mutability(
    tree
):
    """
    Deleguje wykrywanie mutacji
    do wspólnego mutability extractor.

    semantic_analysis nie posiada
    własnej implementacji.
    """

    return analyze_mutability_impl(
        tree
    )

# ==========================================================
# PUBLIC
# ==========================================================


def analyze_module_semantics(
    tree
):

    return {

        "import_usage":
            extract_import_usage(
                tree
            ),

       "mutability":
            _analyze_mutability(
                tree
            )
    }
