# -*- coding: utf-8 -*-
"""
repo_guardian/core/name_collision.py
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List
import ast


class CollisionKind(Enum):
    IMPORT_IMPORT = "import_import"
    SEMANTIC_COLLISION = "semantic_collision"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CollisionReport:
    name: str
    kind: CollisionKind
    symbols: List[str]
    risk_score: int
    risk_level: RiskLevel
    explanation: str
    nodes: List[str] = field(default_factory=list)
    artifact_type: str = "unknown"
    conflicting_code: Dict[str, str] = field(default_factory=dict)


# ============================================================
# FILTERS
# ============================================================

IGNORED_NAMES = {
    "__init__",
    "__new__",
    "__repr__",
    "__str__",
    "__eq__",
    "__hash__",
    "__all__",
}


IGNORED_AST_VISITORS = {
    "visit_ClassDef",
    "visit_FunctionDef",
    "visit_Name",
    "visit_Call",
    "visit_Assign",
    "generic_visit",
}


COMMON_LOCAL_NAMES = {
    "path",
    "name",
    "result",
    "raw",
    "tree",
    "node",
    "value",
    "data",
    "item",
    "args",
    "kwargs",
    "status",
    "total",
    "used",
    "symbols",
    "references",
}


# ============================================================
# SCOPE TRACKER
# ============================================================

class ScopeCollector(ast.NodeVisitor):

    def __init__(self, module_id):
        self.module_id = module_id
        self.scope = []
        self.symbols = []


    def current_scope(self):
        if not self.scope:
            return self.module_id

        return ".".join(
            [self.module_id] + self.scope
        )


    def add_symbol(self, node, name, kind):

        if name in IGNORED_NAMES:
            return

        if name.startswith("__"):
            return

        if name in IGNORED_AST_VISITORS:
            return


        self.symbols.append(
            {
                "name": name,
                "kind": kind,
                "qualified": (
                    f"{self.current_scope()}.{name}"
                ),
                "scope": self.current_scope(),
                "file": self.module_id,
                "source": (
                    ast.unparse(node)
                    if hasattr(ast, "unparse")
                    else str(node)
                ),
            }
        )


    def visit_ClassDef(self, node):

        self.add_symbol(
            node,
            node.name,
            "class"
        )

        self.scope.append(node.name)

        self.generic_visit(node)

        self.scope.pop()



    def visit_FunctionDef(self, node):

        self.add_symbol(
            node,
            node.name,
            "function"
        )

        self.scope.append(node.name)

        self.generic_visit(node)

        self.scope.pop()



    def visit_AsyncFunctionDef(self, node):

        self.visit_FunctionDef(node)



    def visit_Assign(self, node):

        # tylko modułowe zmienne
        if len(self.scope) == 0:

            for target in node.targets:

                if isinstance(target, ast.Name):

                    self.add_symbol(
                        node,
                        target.id,
                        "variable"
                    )

        # lokalne zmienne ignorujemy

        self.generic_visit(node)



# ============================================================
# VALIDATOR
# ============================================================

def validate_name_collisions(symbol_registry_or_modules):

    symbol_map = defaultdict(list)


    modules_iter = []

    if hasattr(symbol_registry_or_modules, "modules"):
        modules_iter = (
            symbol_registry_or_modules.modules.values()
        )

    elif isinstance(symbol_registry_or_modules, dict):
        modules_iter = symbol_registry_or_modules.values()

    elif isinstance(symbol_registry_or_modules, list):
        modules_iter = symbol_registry_or_modules


    for module in modules_iter:

        module_path = getattr(
            module,
            "file_path",
            getattr(module, "path", None)
        )

        module_id = getattr(
            module,
            "name",
            getattr(module, "id", str(module))
        )


        if not module_path:
            continue


        path = Path(module_path)

        if not path.exists():
            continue


        try:
            tree = ast.parse(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            continue


        collector = ScopeCollector(
            module_id
        )

        collector.visit(tree)


        for symbol in collector.symbols:

            key = (
                symbol["name"],
                symbol["kind"]
            )

            symbol_map[key].append(
                symbol
            )


    reports = []


    for (name, kind), occurrences in symbol_map.items():


        # dokładnie ten sam qualified symbol
        # nie jest problemem

        scopes = {
            x["qualified"]
            for x in occurrences
        }


        if len(scopes) <= 1:
            continue


        # ignorowanie typowych nazw lokalnych

        if name in COMMON_LOCAL_NAMES:
            continue



        files = {
            x["file"]
            for x in occurrences
        }


        if len(files) <= 1:
            continue



        conflicting_code = {
            x["qualified"]:
            x["source"]
            for x in occurrences
        }



        nodes = list(files)



        reports.append(
            CollisionReport(

                name=name,

                kind=CollisionKind.SEMANTIC_COLLISION,

                symbols=list(scopes),

                risk_score=65,

                risk_level=RiskLevel.MEDIUM,

                explanation=(
                    f"Possible semantic collision for "
                    f"{kind} '{name}' "
                    f"between different scopes."
                ),

                nodes=nodes,

                artifact_type=kind,

                conflicting_code=conflicting_code
            )
        )


    return reports
