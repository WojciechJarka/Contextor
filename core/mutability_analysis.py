# -*- coding: utf-8 -*-

"""
repo_guardian/core/mutability_analysis.py

AST mutability detector.

Detects function arguments mutated inside function body.
Facts only.
"""


import ast


class MutabilityVisitor(ast.NodeVisitor):

    def __init__(self, arguments):

        self.arguments = set(arguments)
        self.mutated = set()


    def visit_Assign(self, node):

        for target in node.targets:
            self._check_target(target)

        self.generic_visit(node)


    def visit_AugAssign(self, node):

        self._check_target(
            node.target
        )

        self.generic_visit(node)


    def visit_Call(self, node):

        if isinstance(
            node.func,
            ast.Attribute
        ):

            if isinstance(
                node.func.value,
                ast.Name
            ):

                name = node.func.value.id

                if name in self.arguments:
                    self.mutated.add(name)

        self.generic_visit(node)


    def _check_target(self, target):

        if isinstance(
            target,
            ast.Name
        ):

            if target.id in self.arguments:
                self.mutated.add(target.id)


        elif isinstance(
            target,
            ast.Attribute
        ):

            if isinstance(
                target.value,
                ast.Name
            ):

                if target.value.id in self.arguments:
                    self.mutated.add(
                        target.value.id
                    )


def _extract_arguments(node):

    arguments = []


    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef)
    ):

        for arg in node.args.args:
            arguments.append(
                arg.arg
            )


    return arguments



def analyze_mutability(node):

    mutated = set()


    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef)
    ):

        visitor = MutabilityVisitor(
            _extract_arguments(node)
        )

        visitor.visit(node)

        mutated.update(
            visitor.mutated
        )


    elif isinstance(
        node,
        ast.Module
    ):

        for item in node.body:

            if isinstance(
                item,
                (ast.FunctionDef, ast.AsyncFunctionDef)
            ):

                visitor = MutabilityVisitor(
                    _extract_arguments(item)
                )

                visitor.visit(item)

                mutated.update(
                    visitor.mutated
                )


    return sorted(
        mutated
    )
