"""Conservative graph/source agreement for restricted regular-package imports."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass

from .model_identity import indexed_to_logical_module, logical_to_indexed_module


@dataclass(frozen=True)
class PackageGraphConsistency:
    status: str
    reason: str | None


def assess_package_graph_consistency(
    hard_edges: Mapping[str, object],
    sources: Mapping[str, ast.Module],
    evidence_source_modules: tuple[str, ...],
) -> PackageGraphConsistency:
    """Require exact indexed targets for every supported source import."""
    def unknown(reason: str) -> PackageGraphConsistency:
        return PackageGraphConsistency("INDETERMINATE", reason)

    if not isinstance(hard_edges, Mapping) or not isinstance(sources, Mapping):
        return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
    indexed = frozenset(hard_edges)
    if any(name not in indexed or not isinstance(sources.get(name), ast.Module)
           for name in evidence_source_modules):
        return unknown("MISSING_INDEXED_TARGET")

    def target(name: str) -> str | None:
        return logical_to_indexed_module(name, indexed)

    def regular_parents(name: str) -> bool:
        parts = name.split(".")
        return all(
            target(".".join(parts[:length]))
            == ".".join(parts[:length]) + ".__init__"
            and ".".join(parts[:length]) + ".__init__" in sources
            for length in range(1, len(parts))
        )

    def relative_base(module_id: str, level: int, named: str | None) -> str | None:
        logical = indexed_to_logical_module(module_id)
        context = logical if module_id.endswith(".__init__") else logical.rpartition(".")[0]
        parts = context.split(".") if context else []
        if level < 1 or level > len(parts):
            return None
        prefix = ".".join(parts[:len(parts) - level + 1])
        return prefix + ("." + named if named else "")

    for module_id in evidence_source_modules:
        expected: set[str] = set()
        for node in ast.walk(sources[module_id]):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not all(part.isidentifier() for part in alias.name.split(".")):
                        return unknown("UNSUPPORTED_IMPORT_FORM")
                    resolved = target(alias.name)
                    if resolved is None:
                        return unknown("MISSING_INDEXED_TARGET")
                    if resolved != alias.name and resolved != alias.name + ".__init__":
                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
                    if "." in alias.name and not regular_parents(alias.name):
                        return unknown("MISSING_REQUIRED_INITIALIZER")
                    if resolved != module_id:
                        expected.add(resolved)
            elif isinstance(node, ast.ImportFrom):
                if any(alias.name == "*" for alias in node.names):
                    return unknown("UNSUPPORTED_IMPORT_FORM")
                if node.level:
                    base = relative_base(module_id, node.level, node.module)
                    if base is None:
                        return unknown("RELATIVE_IMPORT_OUT_OF_BOUNDS")
                else:
                    base = node.module
                if not base or not all(part.isidentifier() for part in base.split(".")):
                    return unknown("UNSUPPORTED_IMPORT_FORM")
                resolved = target(base)
                if resolved is None:
                    return unknown("MISSING_INDEXED_TARGET")
                if "." in base and not regular_parents(base):
                    return unknown("MISSING_REQUIRED_INITIALIZER")
                if resolved != module_id:
                    expected.add(resolved)
                if resolved.endswith(".__init__"):
                    # The named-member form may be an initializer attribute or
                    # a child. Only explicit relative sibling imports with a
                    # provably unbound child are covered in this phase.
                    if not (node.level and node.module is None):
                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
                    initializer = sources.get(resolved)
                    if initializer is None:
                        return unknown("MISSING_REQUIRED_INITIALIZER")
                    # Only an inert initializer proves that the imported
                    # name cannot be a pre-existing package attribute.
                    if any(
                        not isinstance(statement, ast.Pass)
                        and not (
                            isinstance(statement, ast.Expr)
                            and isinstance(statement.value, ast.Constant)
                            and isinstance(statement.value.value, str)
                        )
                        for statement in initializer.body
                    ):
                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
                    for alias in node.names:
                        if not alias.name.isidentifier():
                            return unknown("AMBIGUOUS_PACKAGE_TARGET")
                        child = target(base + "." + alias.name)
                        if child is None:
                            return unknown("MISSING_INDEXED_TARGET")
                        if child != module_id:
                            expected.add(child)

        if expected != set(hard_edges[module_id]):
            return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")

    return PackageGraphConsistency("CONSISTENT", None)
