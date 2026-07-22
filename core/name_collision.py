# -*- coding: utf-8 -*-
"""
repo_guardian/core/name_collision.py

Semantic Name Collision Detector

Detects:
- duplicate public classes
- duplicate public functions
- conflicting exported constants

Ignores:
- locals
- arguments
- methods
- AST visitors
- __init__
- __all__
- temporary variables
- implementation details
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List
import ast
import hashlib


# ============================================================
# ENUMS
# ============================================================


class CollisionKind(Enum):
    DUPLICATE_PUBLIC_SYMBOL = "duplicate_public_symbol"
    SEMANTIC_COLLISION = "semantic_collision"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# REPORT
# ============================================================


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

    confidence: float = 0.0



# ============================================================
# IGNORE RULES
# ============================================================


IGNORED_NAMES = {

    "__init__",
    "__all__",

    "main",

    "run",

    "path",
    "name",
    "result",
    "results",

    "data",
    "item",
    "value",

    "tree",
    "visitor",

    "args",
    "kwargs",

    "self",

    "modules",
    "metrics",
    "cycles",
    "debt",

    "errors",
    "references",
    "symbols",

}


IGNORED_PREFIXES = (
    "_",
)



IGNORED_FUNCTION_PATTERNS = {

    "visit_ClassDef",
    "visit_FunctionDef",
    "visit_Assign",
    "generic_visit",

}



# ============================================================
# HELPERS
# ============================================================


def _is_public(name: str) -> bool:

    if name in IGNORED_NAMES:
        return False

    if name.startswith(IGNORED_PREFIXES):
        return False

    return True



def _fingerprint(node: ast.AST) -> str:

    """
    Creates structural fingerprint.

    Different formatting
    != different implementation.
    """

    try:

        dump = ast.dump(
            node,
            annotate_fields=False,
            include_attributes=False
        )

    except Exception:

        dump = str(node)


    return hashlib.sha1(
        dump.encode("utf-8")
    ).hexdigest()



def _source(node):

    try:

        return ast.unparse(node)

    except Exception:

        return str(node)



# ============================================================
# SYMBOL EXTRACTION
# ============================================================


def _extract_public_symbols(
    tree,
    module_id
):

    symbols = []


    for node in tree.body:


        # -------------------------
        # Classes
        # -------------------------

        if isinstance(node, ast.ClassDef):

            if not _is_public(node.name):
                continue


            symbols.append(
                {
                    "name": node.name,
                    "type": "class",
                    "module": module_id,
                    "node": node,
                    "fingerprint": _fingerprint(node),
                    "source": _source(node),
                }
            )


        # -------------------------
        # Functions
        # -------------------------

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            if not _is_public(node.name):
                continue


            if node.name in IGNORED_FUNCTION_PATTERNS:
                continue


            symbols.append(
                {
                    "name": node.name,
                    "type": "function",
                    "module": module_id,
                    "node": node,
                    "fingerprint": _fingerprint(node),
                    "source": _source(node),
                }
            )


        # -------------------------
        # Constants only
        # -------------------------

        elif isinstance(
            node,
            ast.Assign
        ):

            for target in node.targets:


                if not isinstance(
                    target,
                    ast.Name
                ):
                    continue


                name = target.id


                # only uppercase constants

                if (
                    name.isupper()
                    and _is_public(name)
                ):

                    symbols.append(
                        {
                            "name": name,
                            "type": "constant",
                            "module": module_id,
                            "node": node,
                            "fingerprint": _fingerprint(node),
                            "source": _source(node),
                        }
                    )


    return symbols



# ============================================================
# MAIN VALIDATOR
# ============================================================


def validate_name_collisions(
    registry
) -> List[CollisionReport]:


    modules = []


    if hasattr(
        registry,
        "modules"
    ):

        modules = registry.modules.values()


    elif isinstance(
        registry,
        dict
    ):

        modules = registry.values()


    elif isinstance(
        registry,
        list
    ):

        modules = registry



    symbol_map = defaultdict(list)



    for module in modules:


        path = getattr(
            module,
            "file_path",
            getattr(
                module,
                "path",
                None
            )
        )


        module_id = getattr(
            module,
            "name",
            getattr(
                module,
                "id",
                str(module)
            )
        )


        if not path:
            continue


        file = Path(path)


        if not file.exists():
            continue


        try:

            tree = ast.parse(
                file.read_text(
                    encoding="utf-8"
                )
            )


        except Exception:

            continue



        for symbol in _extract_public_symbols(
            tree,
            module_id
        ):

            key = (
                symbol["name"],
                symbol["type"]
            )

            symbol_map[key].append(
                symbol
            )



    reports = []



    for (
        name,
        artifact_type
    ), occurrences in symbol_map.items():


        modules = {
            x["module"]
            for x in occurrences
        }


        if len(modules) < 2:
            continue



        fingerprints = {
            x["fingerprint"]
            for x in occurrences
        }


        # same implementation
        # probably harmless

        if len(fingerprints) == 1:

            continue



        risk = 80


        if artifact_type == "class":

            risk = 90

        elif artifact_type == "function":

            risk = 85

        elif artifact_type == "constant":

            risk = 60



        reports.append(

            CollisionReport(

                name=name,

                kind=CollisionKind.SEMANTIC_COLLISION,

                symbols=list(modules),

                risk_score=risk,

                risk_level=(
                    RiskLevel.HIGH
                    if risk >= 80
                    else RiskLevel.MEDIUM
                ),

                explanation=(
                    f"Public {artifact_type} "
                    f"'{name}' has different "
                    f"implementations across modules."
                ),

                nodes=list(modules),

                artifact_type=artifact_type,

                conflicting_code={
                    x["module"]:
                    x["source"]

                    for x in occurrences
                },

                confidence=0.9,

            )
        )


    return reports
