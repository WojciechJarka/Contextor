# -*- coding: utf-8 -*-

"""
repo_guardian/core/validator/collisions.py

Semantic API collision detector.

Detects only real public symbol collisions between modules.
Ignores local variables, methods, nested functions and Python internals.
"""

import ast
from collections import defaultdict
from pathlib import Path

from ..domain.module import Module
from ..domain.validation import ValidationError


IGNORED_NAMES = {
    "__all__",
    "__version__",
    "__author__",
    "__init__",
    "__new__",
    "__repr__",
    "__str__",
}


def _ignore(name: str) -> bool:
    if name in IGNORED_NAMES:
        return True

    if name.startswith("__") and name.endswith("__"):
        return True

    return False


class PublicSymbolCollector(ast.NodeVisitor):

    def __init__(self, source: str, module_path: str):
        self.source = source
        self.module_path = module_path
        self.symbols = []

        self.class_depth = 0
        self.function_depth = 0


    def _add(self, name, kind, node):

        if _ignore(name):
            return

        code = ast.get_source_segment(
            self.source,
            node
        ) or name

        self.symbols.append(
            {
                "name": name,
                "type": kind,
                "file": self.module_path,
                "code": code,
            }
        )


    def visit_ClassDef(self, node):

        # tylko klasy top-level
        if self.class_depth == 0:
            self._add(
                node.name,
                "class",
                node
            )

        self.class_depth += 1
        self.generic_visit(node)
        self.class_depth -= 1



    def visit_FunctionDef(self, node):

        # tylko funkcje top-level
        if (
            self.class_depth == 0
            and self.function_depth == 0
        ):
            self._add(
                node.name,
                "function",
                node
            )

        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1



    def visit_AsyncFunctionDef(self, node):

        self.visit_FunctionDef(node)



    def visit_Assign(self, node):

        # tylko globalne stałe/API
        if (
            self.class_depth == 0
            and self.function_depth == 0
        ):

            for target in node.targets:

                if isinstance(target, ast.Name):

                    self._add(
                        target.id,
                        "variable",
                        node
                    )



def validate_name_collisions(
    modules: dict[str, Module],
) -> list[ValidationError]:

    errors = []

    name_map = defaultdict(list)


    for module_path, module in modules.items():

        file_path = (
            getattr(module, "absolute_path", None)
            or getattr(module, "path", None)
        )

        if not file_path:
            continue


        path = Path(file_path)

        if not path.exists():
            continue


        try:
            source = path.read_text(
                encoding="utf-8"
            )

            tree = ast.parse(source)

        except Exception:
            continue


        collector = PublicSymbolCollector(
            source,
            module_path
        )

        collector.visit(tree)


        for symbol in collector.symbols:

            name_map[
                (
                    symbol["name"],
                    symbol["type"]
                )
            ].append(symbol)



    for (name, artifact_type), occurrences in name_map.items():

        files = {
            x["file"]
            for x in occurrences
        }


        if len(files) <= 1:
            continue


        codes = {
            x["code"]
            for x in occurrences
        }


        code_snippets = {
            x["file"]: x["code"]
            for x in occurrences
        }


        if len(codes) > 1:

            error = ValidationError(
                kind="NAME_COLLISION",
                message=(
                    f"Semantic API collision for "
                    f"{artifact_type} '{name}' "
                    f"across modules: "
                    f"{', '.join(files)}"
                ),
                nodes=list(files),
            )

            error.code_snippets = code_snippets
            error.artifact_type = artifact_type
            error.is_identical = False

            errors.append(error)



        else:

            error = ValidationError(
                kind="IDENTICAL_DEFINITION_DUPLICATE",
                message=(
                    f"Identical public definition "
                    f"{artifact_type} '{name}' "
                    f"across modules"
                ),
                nodes=list(files),
            )

            error.code_snippets = code_snippets
            error.artifact_type = artifact_type
            error.is_identical = True

            errors.append(error)


    return errors
