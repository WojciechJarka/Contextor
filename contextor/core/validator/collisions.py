"""
contextor/core/validator/collisions.py

Semantic API collision detector.

Detects only real public symbol collisions between modules.

Rules:
- only top-level public classes/functions
- only exported-style constants (UPPER_CASE)
- ignores private helpers (_name)
- ignores methods
- ignores nested functions
- ignores Python internals
- ignores conventional per-module entrypoints (main, run)
- normalizes source before comparing implementations
"""

import ast
from collections import defaultdict
from pathlib import Path

from ..domain.module import Module
from ..domain.validation import ValidationError
from ..source import SourceError, parse_source

IGNORED_NAMES = {
    "__all__",
    "__version__",
    "__author__",
    "__init__",
    "__new__",
    "__repr__",
    "__str__",
    # conventional per-module entrypoints: every module is allowed
    # to define its own main()/run() without that being a real
    # semantic API collision (e.g. cli.main vs main.main).
    "main",
    "run",
}


def _ignore(name: str) -> bool:
    """
    Ignore non API symbols.
    """

    if not name:
        return True

    if name in IGNORED_NAMES:
        return True

    # Python magic methods
    if name.startswith("__") and name.endswith("__"):
        return True

    # private/internal helpers
    if name.startswith("_"):
        return True

    # Visitor patterns and extremely generic names
    if name.startswith("visit_") or name in {"get", "add", "build"}:
        return True

    return False


def _normalize_code(code: str) -> str:
    """
    Normalize source snippets.

    Avoid false collisions caused only by formatting.
    """

    return "\n".join(line.strip() for line in code.splitlines() if line.strip())


class PublicSymbolCollector(ast.NodeVisitor):
    """
    Collect only public module-level API symbols.
    """

    def __init__(
        self,
        module_path: str,
        absolute_path: str = "",
    ):
        self.module_path = module_path
        self.absolute_path = absolute_path

        self.symbols = []

        self.class_depth = 0
        self.function_depth = 0

    def _add(
        self,
        name: str,
        kind: str,
        node: ast.AST,
    ):
        """
        Add public symbol.
        """

        if _ignore(name):
            return

        code = ""
        try:
            # Semantic extraction (Python 3.9+)
            code = ast.unparse(node)
        except Exception:
            # Fallback to pure string match if unparse fails
            code = name

        self.symbols.append(
            {
                "name": name,
                "type": kind,
                "file": self.module_path,
                "file_path": self.absolute_path,
                "code": code,
                "line_start": getattr(
                    node,
                    "lineno",
                    None,
                ),
                "line_end": getattr(
                    node,
                    "end_lineno",
                    None,
                ),
                "col_start": getattr(
                    node,
                    "col_offset",
                    None,
                ),
                "col_end": getattr(
                    node,
                    "end_col_offset",
                    None,
                ),
            }
        )

    def visit_ClassDef(
        self,
        node: ast.ClassDef,
    ):
        """
        Collect only top-level classes.
        """

        if self.class_depth == 0 and self.function_depth == 0:
            self._add(
                node.name,
                "class",
                node,
            )

        self.class_depth += 1

        self.generic_visit(node)

        self.class_depth -= 1

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ):
        """
        Collect only top-level functions.
        """

        if self.class_depth == 0 and self.function_depth == 0:
            self._add(
                node.name,
                "function",
                node,
            )

        self.function_depth += 1

        self.generic_visit(node)

        self.function_depth -= 1

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ):
        """
        Async functions use same rules.
        """

        self.visit_FunctionDef(node)

    def visit_Assign(
        self,
        node: ast.Assign,
    ):
        """
        Collect only public constants.

        Example:

            RULES = {...}

        Ignore:

            value = 10
            temp = []
        """

        if self.class_depth != 0 or self.function_depth != 0:
            return

        for target in node.targets:
            if not isinstance(
                target,
                ast.Name,
            ):
                continue

            name = target.id

            # only exported constants
            if not name.isupper():
                continue

            self._add(
                name,
                "variable",
                node,
            )


def validate_name_collisions(
    modules: dict[str, Module],
) -> list[ValidationError]:
    """
    Detect public API collisions.
    """

    errors: list[ValidationError] = []

    registry = defaultdict(list)

    for module_path, module in modules.items():
        file_path = getattr(module, "absolute_path", None) or getattr(module, "path", None)

        if not file_path:
            continue

        tree = getattr(module, "ast_tree", None)

        if tree is None:
            path = Path(file_path)
            if not path.exists():
                continue
            try:
                tree = parse_source(path)
            except SourceError:
                continue

        collector = PublicSymbolCollector(
            module_path,
            absolute_path=str(file_path),
        )

        collector.visit(tree)

        for symbol in collector.symbols:
            key = (
                symbol["name"],
                symbol["type"],
            )

            registry[key].append(symbol)

    for (
        name,
        artifact_type,
    ), occurrences in registry.items():
        files = {item["file"] for item in occurrences}

        if len(files) <= 1:
            continue

        normalized_codes = {_normalize_code(item["code"]) for item in occurrences}

        code_snippets = {item["file"]: item["code"] for item in occurrences}

        symbol_details = []

        for item in occurrences:
            symbol_details.append(
                {
                    "module": item["file"],
                    "name": item["name"],
                    "artifact_type": item["type"],
                    "file_path": item.get("file_path", ""),
                    "location": {
                        "line_start": item.get("line_start"),
                        "line_end": item.get("line_end"),
                        "column_start": item.get("col_start"),
                        "column_end": item.get("col_end"),
                    },
                    # "source" deliberately removed - identical to
                    # conflicting_code[symbol_details.module],
                    # duplicating just the code text without new
                    # information.
                }
            )

        if len(normalized_codes) > 1:
            error = ValidationError(
                kind="NAME_COLLISION",
                message=(
                    f"Semantic API collision for "
                    f"{artifact_type} '{name}' "
                    f"across modules: "
                    f"{', '.join(sorted(files))}"
                ),
                nodes=sorted(files),
            )

            error.code_snippets = code_snippets
            error.symbol_details = symbol_details
            error.artifact_type = artifact_type
            error.is_identical = False

            errors.append(error)

        else:
            error = ValidationError(
                kind="IDENTICAL_DEFINITION_DUPLICATE",
                message=(
                    f"Identical public definition "
                    f"{artifact_type} '{name}' "
                    f"across modules: "
                    f"{', '.join(sorted(files))}"
                ),
                nodes=sorted(files),
            )

            error.code_snippets = code_snippets
            error.symbol_details = symbol_details
            error.artifact_type = artifact_type
            error.is_identical = True

            errors.append(error)

    return errors
