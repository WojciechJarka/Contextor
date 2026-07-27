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

# ==========================================================
# IMPORT USAGE
# ==========================================================


class ImportUsageVisitor(ast.NodeVisitor):

    def __init__(self, imports):

        self.imports = imports
        self.usage = defaultdict(int)
        self.aliases = {}

    def visit_Import(self, node):

        for item in node.names:
            name = item.asname or item.name.split(".")[0]
            self.aliases[name] = item.name

    def visit_ImportFrom(self, node):

        for item in node.names:
            name = item.asname or item.name
            self.aliases[name] = (
                f"{node.module}.{item.name}"
                if node.module
                else item.name
            )

    def visit_Name(self, node):

        if node.id in self.aliases:
            self.usage[
                self.aliases[node.id]
            ] += 1

        self.generic_visit(node)


def analyze_import_usage(tree):

    visitor = ImportUsageVisitor([])

    visitor.visit(tree)

    result = {}

    for alias, count in visitor.usage.items():

        result[alias] = {
            "used": count,
            "classification": "runtime"
        }

    for alias in visitor.aliases.values():

        result.setdefault(
            alias,
            {
                "used": 0,
                "classification": "unused"
            }
        )

    return result



# ==========================================================
# RISK SIGNALS
# ==========================================================


RISK_CALLS = {

    "exec": "exec",
    "eval": "eval",
    "compile": "reflection",

    "open": "filesystem_write",

    "connect": "network_io",

    "Thread": "threading",

    "setattr": "monkey_patch",
    "globals": "global_state",
    "locals": "reflection",
}


class RiskVisitor(ast.NodeVisitor):

    def __init__(self):

        self.risks = set()

    def visit_Call(self,node):

        name = None

        if isinstance(node.func, ast.Name):
            name = node.func.id

        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr


        if name in RISK_CALLS:
            self.risks.add(
                RISK_CALLS[name]
            )

        self.generic_visit(node)



def analyze_risks(tree):

    visitor = RiskVisitor()
    visitor.visit(tree)

    return sorted(
        visitor.risks
    )



# ==========================================================
# SIDE EFFECTS
# ==========================================================


SIDE_EFFECT_CALLS = {

    "open": "filesystem",

    "print": "logging",

    "sleep": "time",

    "random": "random",

    "connect": "network",

    "execute": "database",
}


class SideEffectVisitor(ast.NodeVisitor):

    def __init__(self):

        self.effects = set()

    def visit_Call(self,node):

        name = None

        if isinstance(node.func, ast.Name):
            name = node.func.id

        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr


        if name in SIDE_EFFECT_CALLS:

            self.effects.add(
                SIDE_EFFECT_CALLS[name]
            )

        self.generic_visit(node)



def analyze_side_effects(tree):

    visitor = SideEffectVisitor()

    visitor.visit(tree)

    return sorted(
        visitor.effects
    )



# ==========================================================
# EXCEPTION MAP
# ==========================================================


class ExceptionVisitor(ast.NodeVisitor):

    def __init__(self):

        self.raises=set()
        self.caught=set()


    def visit_Raise(self,node):

        if isinstance(
            node.exc,
            ast.Call
        ):

            if isinstance(
                node.exc.func,
                ast.Name
            ):

                self.raises.add(
                    node.exc.func.id
                )

        self.generic_visit(node)



    def visit_ExceptHandler(self,node):

        if node.type:

            if isinstance(
                node.type,
                ast.Name
            ):
                self.caught.add(
                    node.type.id
                )

        self.generic_visit(node)



def analyze_exceptions(tree):

    visitor = ExceptionVisitor()

    visitor.visit(tree)

    return {

        "raises": sorted(
            visitor.raises
        ),

        "caught": sorted(
            visitor.caught
        )
    }
    
# ==========================================================
# MUTABILITY
# ==========================================================


def analyze_mutability(
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
            analyze_import_usage(
                tree
            ),

        "side_effects":
            analyze_side_effects(
                tree
            ),

        "risks":
            analyze_risks(
                tree
            ),

        "exceptions":
            analyze_exceptions(
                tree
            ),

       "mutability":
            analyze_mutability(
                tree
            )
    }
