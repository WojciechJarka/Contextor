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
from typing import Any

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


COLLISION_FACT_KEYS = (
    "name",
    "type",
    "file",
    "file_path",
    "code",
    "line_start",
    "line_end",
    "col_start",
    "col_end",
)


from collections.abc import ItemsView, KeysView, ValuesView


class CollisionFactKeys(KeysView):
    """View of CollisionFact keys with deterministic legacy order."""
    def __repr__(self) -> str:
        return f"dict_keys({list(self._mapping)})"


class CollisionFactItems(ItemsView):
    """View of CollisionFact items with deterministic legacy order."""
    def __repr__(self) -> str:
        return f"dict_items({list(self._mapping.items())})"


class CollisionFactValues(ValuesView):
    """View of CollisionFact values with deterministic legacy order."""
    def __repr__(self) -> str:
        return f"dict_values({list(self._mapping.values())})"


class CollisionFact(dict):
    """
    Collision fact dictionary with lazy AST unparsing for the 'code' field.
    Preserves exact legacy dictionary key order, contract, and schema while
    deferring ast.unparse until the 'code' field is explicitly accessed.
    """
    __slots__ = ("_node", "_rendered_code")

    def __init__(
        self,
        name: str,
        kind: str,
        module_path: str,
        file_path: str = "",
        node: ast.AST | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        col_start: int | None = None,
        col_end: int | None = None,
        code: str | None = None,
    ):
        super().__init__()
        super().__setitem__("name", name)
        super().__setitem__("type", kind)
        super().__setitem__("file", module_path)
        super().__setitem__("file_path", file_path)
        super().__setitem__("line_start", line_start)
        super().__setitem__("line_end", line_end)
        super().__setitem__("col_start", col_start)
        super().__setitem__("col_end", col_end)
        self._node = node
        self._rendered_code = code

    def _get_code(self) -> str:
        if self._rendered_code is None:
            if self._node is not None:
                try:
                    self._rendered_code = ast.unparse(self._node)
                except Exception:
                    self._rendered_code = super().__getitem__("name")
            else:
                self._rendered_code = super().__getitem__("name")
        return self._rendered_code

    def __getitem__(self, key: str) -> Any:
        if key == "code":
            return self._get_code()
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "code":
            return self._get_code()
        return super().get(key, default)

    def __contains__(self, key: object) -> bool:
        if key == "code":
            return True
        return super().__contains__(key)

    def __iter__(self):
        for k in COLLISION_FACT_KEYS:
            yield k

    def __len__(self) -> int:
        return len(COLLISION_FACT_KEYS)

    def keys(self) -> KeysView:
        return CollisionFactKeys(self)

    def items(self) -> ItemsView:
        return CollisionFactItems(self)

    def values(self) -> ValuesView:
        return CollisionFactValues(self)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, dict):
            return False
        if len(self) != len(other):
            return False
        for k in COLLISION_FACT_KEYS:
            if k not in other or self[k] != other[k]:
                return False
        return True

    def __repr__(self) -> str:
        d = {k: self[k] for k in COLLISION_FACT_KEYS}
        return repr(d)

    def copy(self) -> dict[str, Any]:
        return {k: self[k] for k in COLLISION_FACT_KEYS}

    def __reduce__(self):
        # Pickles as a standard plain dict with exact schema to eliminate AST node references across persistence/IPC
        rendered_code = self._rendered_code if self._rendered_code is not None else ""
        d = {
            "name": super().__getitem__("name"),
            "type": super().__getitem__("type"),
            "file": super().__getitem__("file"),
            "file_path": super().__getitem__("file_path"),
            "code": rendered_code,
            "line_start": super().__getitem__("line_start"),
            "line_end": super().__getitem__("line_end"),
            "col_start": super().__getitem__("col_start"),
            "col_end": super().__getitem__("col_end"),
        }
        return (dict, (d,))


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

        self.symbols: list[dict[str, Any]] = []

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

        self.symbols.append(
            CollisionFact(
                name=name,
                kind=kind,
                module_path=self.module_path,
                file_path=self.absolute_path,
                node=node,
                line_start=getattr(node, "lineno", None),
                line_end=getattr(node, "end_lineno", None),
                col_start=getattr(node, "col_offset", None),
                col_end=getattr(node, "end_col_offset", None),
            )
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
        """
        if self.class_depth != 0 or self.function_depth != 0:
            return

        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue

            name = target.id
            if not name.isupper():
                continue

            self._add(
                name,
                "variable",
                node,
            )


def extract_module_collision_facts(
    tree: ast.AST,
    module_path: str,
    absolute_path: str = "",
) -> list[dict]:
    """
    Extract public API symbol facts from one parsed AST for collision analysis.
    """
    collector = PublicSymbolCollector(
        module_path,
        absolute_path=str(absolute_path),
    )
    collector.visit(tree)
    return collector.symbols


def extract_repository_collision_facts(
    modules: dict[str, Module],
) -> dict[str, list[dict]]:
    """
    Extract public API symbol collision facts across all modules in the repository.
    Reuses current-run module ASTs without re-reading from disk where available.
    """
    facts: dict[str, list[dict]] = {}
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
        facts[module_path] = extract_module_collision_facts(
            tree,
            module_path,
            str(file_path),
        )
    return facts


def compute_collisions_from_facts(
    collision_facts: dict[str, list[dict]],
) -> list[ValidationError]:
    """
    Pure aggregation of module collision facts into ValidationError collision results.
    Renders AST source definitions lazily only for candidate collision symbols.
    """
    errors: list[ValidationError] = []
    registry = defaultdict(list)

    for module_path, symbols in collision_facts.items():
        for symbol in symbols:
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


def validate_name_collisions(
    modules: dict[str, Module],
    collision_facts: dict[str, list[dict]] | None = None,
) -> list[ValidationError]:
    """
    Detect public API collisions across repository modules.
    Reuses collision_facts if already computed in the current analysis run.
    """
    if collision_facts is None:
        collision_facts = extract_repository_collision_facts(modules)
    return compute_collisions_from_facts(collision_facts)
