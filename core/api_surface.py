# -*- coding: utf-8 -*-
"""
repo_guardian/core/api_surface.py

AST API Surface Extractor.

Ekstrahuje publiczną powierzchnię modułu:
- funkcje
- klasy
- metody
- sygnatury
- widoczność
- decorators
- static/class methods

Nie ocenia jakości kodu.
Tylko fakty z AST.
"""

import ast
from pathlib import Path


# ==========================================================
# HELPERS
# ==========================================================


def _visibility(name: str) -> str:
    if name.startswith("_"):
        return "private"

    return "public"



def _annotation(node):
    if node is None:
        return None

    try:
        return ast.unparse(node)

    except Exception:
        return None



def _default_value(node):
    if node is None:
        return None

    try:
        return ast.unparse(node)

    except Exception:
        return None



def _signature(node):

    args = []

    defaults = (
        [None] *
        (
            len(node.args.args)
            -
            len(node.args.defaults)
        )
        +
        list(node.args.defaults)
    )


    for arg, default in zip(
        node.args.args,
        defaults
    ):

        args.append(
            {
                "name": arg.arg,
                "annotation": _annotation(
                    arg.annotation
                ),
                "default": _default_value(
                    default
                ),
            }
        )


    return {
        "parameters": args,

        "returns": _annotation(
            node.returns
        )
    }



# ==========================================================
# VISITOR
# ==========================================================


class APISurfaceVisitor(ast.NodeVisitor):

    def __init__(self):

        self.functions = {}
        self.methods = {}
        self.classes = {}

        self.class_stack = []

        self.decorators = {}


    def _decorator_names(self,node):

        result = []

        for dec in node.decorator_list:

            try:
                result.append(
                    ast.unparse(dec)
                )

            except Exception:
                pass

        return result



    def visit_ClassDef(
        self,
        node
    ):

        name = node.name

        self.classes[name] = {

            "kind":
                "class",

            "visibility":
                _visibility(name),

            "bases":
                [
                    ast.unparse(base)
                    for base in node.bases
                    if base
                ],

            "decorators":
                self._decorator_names(
                    node
                )

        }


        self.class_stack.append(
            name
        )

        self.generic_visit(node)

        self.class_stack.pop()



    def visit_FunctionDef(
        self,
        node
    ):

        name = node.name

        full_name = name


        is_method = (
            len(self.class_stack)
            > 0
        )


        if is_method:

            full_name = (
                f"{self.class_stack[-1]}"
                f".{name}"
            )


        decorators = (
            self._decorator_names(
                node
            )
        )


        entry = {

            "kind":
                "method"
                if is_method
                else
                "function",

            "visibility":
                _visibility(name),

            "signature":
                _signature(node),

            "decorators":
                decorators,

            "classmethod":
                "classmethod"
                in decorators,

            "staticmethod":
                "staticmethod"
                in decorators,

        }


        if is_method:

            self.methods[full_name] = entry

        else:

            self.functions[name] = entry


        self.generic_visit(node)



# ==========================================================
# PUBLIC API
# ==========================================================


def extract_api_surface(
    file_path: str | Path
) -> dict:

    path = Path(
        file_path
    )


    try:

        tree = ast.parse(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return {
            "functions": {},
            "methods": {},
            "classes": {},
        }


    visitor = APISurfaceVisitor()

    visitor.visit(
        tree
    )


    return {

        "functions":
            visitor.functions,

        "methods":
            visitor.methods,

        "classes":
            visitor.classes,

    }

# ==========================================================
# API METADATA
# ==========================================================


def extract_api_metadata(
    file_path: str | Path
) -> dict:
    """
    Statystyki API modułu.

    Nie interpretuje jakości.
    Tylko agreguje fakty AST.

    Przeznaczenie:
    - LLM context
    - refactor analysis
    - API pressure models
    """

    api = extract_api_surface(
        file_path
    )


    functions = api.get(
        "functions",
        {}
    )

    methods = api.get(
        "methods",
        {}
    )

    classes = api.get(
        "classes",
        {}
    )


    all_symbols = (
        list(functions.values())
        +
        list(methods.values())
        +
        list(classes.values())
    )


    public_count = sum(
        1
        for item in all_symbols
        if item.get(
            "visibility"
        ) == "public"
    )


    private_count = sum(
        1
        for item in all_symbols
        if item.get(
            "visibility"
        ) == "private"
    )


    classmethod_count = sum(
        1
        for item in methods.values()
        if item.get(
            "classmethod"
        )
    )


    staticmethod_count = sum(
        1
        for item in methods.values()
        if item.get(
            "staticmethod"
        )
    )


    return {

        "total_symbols":
            len(all_symbols),


        "functions":
            len(functions),


        "methods":
            len(methods),


        "classes":
            len(classes),


        "public_symbols":
            public_count,


        "private_symbols":
            private_count,


        "classmethods":
            classmethod_count,


        "staticmethods":
            staticmethod_count,
    }

# ==========================================================
# FLATTENED API VIEW
# ==========================================================


def extract_flat_api_surface(
    file_path: str | Path
) -> dict:
    """
    Kompaktowy widok API dla raportów LLM.

    Łączy:
    - functions
    - methods
    - classes

    Nie usuwa pełnego API surface.
    Jest tylko warstwą prezentacji.
    """

    raw = extract_api_surface(
        file_path
    )

    result = {}


    for name, data in raw.get(
        "functions",
        {}
    ).items():

        result[name] = data


    for name, data in raw.get(
        "methods",
        {}
    ).items():

        result[name] = data


    for name, data in raw.get(
        "classes",
        {}
    ).items():

        result[name] = data


    return result
