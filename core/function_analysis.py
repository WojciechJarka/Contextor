# -*- coding: utf-8 -*-

"""
repo_guardian/core/function_analysis.py

Function-level AST intelligence.

Extracts facts:

- signatures
- complexity
- nesting
- returns
- calls
- side effects
- mutations

Nie ocenia jakości.
Nie liczy ryzyka architektury.

Źródło reguł efektów:
    repo_guardian.core.risk_analysis
"""


import ast


from repo_guardian.core.risk_analysis import (
    analyze_effects,
)

MUTATING_METHODS = {
    "append", "extend", "insert", "remove", 
    "pop", "clear", "update", "setdefault", 
    "add", "discard"
}



# ==========================================================
# SIGNATURE
# ==========================================================


def build_signature(
    node: ast.FunctionDef
):
    """
    Buduje prostą sygnaturę funkcji.
    """

    args = []


    for arg in node.args.args:

        args.append(
            arg.arg
        )


    if node.args.vararg:

        args.append(
            "*" +
            node.args.vararg.arg
        )


    if node.args.kwarg:

        args.append(
            "**" +
            node.args.kwarg.arg
        )


    return (

        f"{node.name}("

        +

        ", ".join(args)

        +

        ")"

    )



# ==========================================================
# COMPLEXITY
# ==========================================================


class ComplexityVisitor(
    ast.NodeVisitor
):

    def __init__(self):

        self.complexity = 1
        self.nested_if = 0
        self.max_depth = 0
        self.current_depth = 0
        self.returns = 0



    def _branch(self):

        self.complexity += 1



    def visit_If(
        self,
        node
    ):

        self._branch()

        self.current_depth += 1

        self.max_depth = max(
            self.max_depth,
            self.current_depth
        )

        self.nested_if += 1

        self.generic_visit(
            node
        )

        self.current_depth -= 1



    def visit_For(
        self,
        node
    ):

        self._branch()

        self.generic_visit(
            node
        )



    def visit_AsyncFor(
        self,
        node
    ):

        self.visit_For(
            node
        )



    def visit_While(
        self,
        node
    ):

        self._branch()

        self.generic_visit(
            node
        )



    def visit_Try(
        self,
        node
    ):

        self._branch()

        self.generic_visit(
            node
        )



    def visit_With(
        self,
        node
    ):

        self._branch()

        self.generic_visit(
            node
        )



    def visit_Return(
        self,
        node
    ):

        self.returns += 1



def analyze_complexity(
    node
):

    visitor = ComplexityVisitor()

    visitor.visit(
        node
    )


    lines = None


    if hasattr(
        node,
        "end_lineno"
    ):

        lines = (
            node.end_lineno
            -
            node.lineno
            +
            1
        )


    return {

        "cyclomatic":
            visitor.complexity,


        "lines":
            lines,


        "nested_if":
            visitor.nested_if,


        "max_depth":
            visitor.max_depth,


        "returns":
            visitor.returns,

    }



# ==========================================================
# CALL EXTRACTION
# ==========================================================


class FunctionCallVisitor(
    ast.NodeVisitor
):

    def __init__(self):

        self.calls = set()



    def visit_Call(
        self,
        node
    ):

        name = None


        if isinstance(
            node.func,
            ast.Name
        ):

            name = node.func.id



        elif isinstance(
            node.func,
            ast.Attribute
        ):

            parts = []

            current = node.func


            while isinstance(
                current,
                ast.Attribute
            ):

                parts.append(
                    current.attr
                )

                current = current.value



            if isinstance(
                current,
                ast.Name
            ):

                parts.append(
                    current.id
                )



            name = ".".join(
                reversed(parts)
            )



        if name:

            self.calls.add(
                name
            )


        self.generic_visit(
            node
        )



def analyze_calls(
    node
):

    visitor = FunctionCallVisitor()

    visitor.visit(
        node
    )


    return sorted(
        visitor.calls
    )



# ==========================================================
# MUTABILITY
# ==========================================================


class FunctionMutationVisitor(
    ast.NodeVisitor
):

    def __init__(
        self,
        args
    ):

        self.args = set(
            args
        )

        self.modified = set()



    def visit_Assign(
        self,
        node
    ):

        for target in node.targets:

            self._check_target(
                target
            )

        self.generic_visit(
            node
        )



    def visit_AugAssign(
        self,
        node
    ):

        self._check_target(
            node.target
        )

        self.generic_visit(
            node
        )



    def visit_Call(
        self,
        node
    ):

        if isinstance(
            node.func,
            ast.Attribute
        ):

            if isinstance(
                node.func.value,
                ast.Name
            ):

                if (
                    node.func.value.id
                    in self.args
                ):
                    if node.func.attr in MUTATING_METHODS:
                        self.modified.add(
                            node.func.value.id
                        )


        self.generic_visit(
            node
        )



    def _check_target(
        self,
        target
    ):

        if isinstance(
            target,
            ast.Attribute
        ):

            if isinstance(
                target.value,
                ast.Name
            ):

                if target.value.id in self.args:

                    self.modified.add(
                        target.value.id
                    )



        elif isinstance(
            target,
            ast.Name
        ):

            if target.id in self.args:

                self.modified.add(
                    target.id
                )

        elif isinstance(
            target,
            ast.Subscript
        ):
            if isinstance(target.value, ast.Name):
                if target.value.id in self.args:
                    self.modified.add(target.value.id)
            elif isinstance(target.value, ast.Attribute) and isinstance(target.value.value, ast.Name):
                if target.value.value.id in self.args:
                    self.modified.add(target.value.value.id)



def analyze_mutations(
    node
):

    args = [

        arg.arg

        for arg in node.args.args

    ]


    visitor = FunctionMutationVisitor(
        args
    )


    visitor.visit(
        node
    )


    return sorted(
        visitor.modified
    )



# ==========================================================
# FUNCTION API
# ==========================================================


def analyze_functions(
    tree
):

    result = {}



    for node in ast.walk(tree):


        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):


            result[node.name] = {

                "signature":
                    build_signature(
                        node
                    ),


                "kind":
                    (
                        "async_function"
                        if isinstance(
                            node,
                            ast.AsyncFunctionDef
                        )
                        else
                        "function"
                    ),


                "visibility":
                    (
                        "private"
                        if node.name.startswith("_")
                        else
                        "public"
                    ),


                "complexity":
                    analyze_complexity(
                        node
                    ),


                "calls":
                    analyze_calls(
                        node
                    ),


                "side_effects":
                    analyze_effects(
                        node
                    ),


                "mutates":
                    analyze_mutations(
                        node
                    ),

            }


    return result
