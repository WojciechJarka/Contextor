"""Conservative graph/source agreement for restricted regular-package imports."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass

from .model_identity import indexed_to_logical_module, logical_to_indexed_module
from .typing_guard import recognize_typing_guard


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

    def restricted_relative_initializer(
        initializer_id: str,
    ) -> bool:
        tree = sources.get(initializer_id)

        if (
            not initializer_id.endswith(".__init__")
            or not isinstance(tree, ast.Module)
        ):
            return False

        package_name = initializer_id.removesuffix(
            ".__init__"
        )

        child_names: set[str] = set()

        for indexed_id in indexed:
            prefix = package_name + "."

            if not indexed_id.startswith(prefix):
                continue

            remainder = indexed_id[len(prefix):]

            if remainder and remainder != "__init__":
                child_names.add(
                    remainder.split(".", 1)[0]
                )

        def valid_body(
            statements: list[ast.stmt],
            depth: int,
        ) -> bool:
            if depth >= 32:
                return False

            for statement in statements:
                if isinstance(statement, ast.Pass):
                    continue

                if (
                    isinstance(statement, ast.Expr)
                    and isinstance(
                        statement.value,
                        ast.Constant,
                    )
                    and type(
                        statement.value.value
                    ) is str
                ):
                    continue

                if isinstance(
                    statement,
                    ast.Assign,
                ):
                    if (
                        len(statement.targets) != 1
                        or not isinstance(
                            statement.targets[0],
                            ast.Name,
                        )
                        or not isinstance(
                            statement.value,
                            ast.Constant,
                        )
                        or type(
                            statement.value.value
                        ) not in {
                            type(None),
                            bool,
                            int,
                            float,
                            complex,
                            str,
                            bytes,
                        }
                    ):
                        return False

                    binding = statement.targets[0].id

                    if (
                        not binding.isidentifier()
                        or binding.startswith("__")
                        or binding in child_names
                    ):
                        return False

                    continue

                if isinstance(
                    statement,
                    ast.ImportFrom,
                ):
                    if (
                        statement.level != 1
                        or statement.module is not None
                        or len(statement.names) != 1
                    ):
                        return False

                    alias = statement.names[0]

                    if (
                        not alias.name.isidentifier()
                        or alias.name.startswith("__")
                        or alias.asname is not None
                    ):
                        return False

                    child_logical = (
                        package_name
                        + "."
                        + alias.name
                    )

                    child_indexed = target(
                        child_logical
                    )

                    if (
                        child_indexed is None
                        or child_indexed == initializer_id
                        or child_indexed not in sources
                        or not regular_parents(
                            child_logical
                        )
                    ):
                        return False

                    continue

                if isinstance(statement, ast.If):
                    condition = statement.test

                    if not (
                        isinstance(
                            condition,
                            ast.Constant,
                        )
                        and type(
                            condition.value
                        ) is bool
                    ):
                        return False

                    if not valid_body(
                        statement.body,
                        depth + 1,
                    ):
                        return False

                    if not valid_body(
                        statement.orelse,
                        depth + 1,
                    ):
                        return False

                    continue

                return False

            return True

        return valid_body(tree.body, 0)

    def initializer_direct_child_binding(
        initializer_id: str,
        member: str,
    ) -> bool:
        if not restricted_relative_initializer(
            initializer_id
        ):
            return False

        initializer = sources.get(initializer_id)

        if not isinstance(initializer, ast.Module):
            return False

        return any(
            isinstance(statement, ast.ImportFrom)
            and statement.level == 1
            and statement.module is None
            and len(statement.names) == 1
            and statement.names[0].name == member
            and statement.names[0].asname is None
            for statement in initializer.body
        )

    for module_id in evidence_source_modules:
        expected: set[str] = set()
        typing_guard = recognize_typing_guard(
            sources[module_id],
            indexed,
        )
        for node in ast.walk(sources[module_id]):
            if (
                typing_guard is not None
                and node is typing_guard.marker_statement
            ):
                continue

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
                    if not restricted_relative_initializer(
                        resolved
                    ):
                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
                    for alias in node.names:
                        if not alias.name.isidentifier():
                            return unknown("AMBIGUOUS_PACKAGE_TARGET")
                        child = target(base + "." + alias.name)
                        if child is None:
                            return unknown("MISSING_INDEXED_TARGET")

                        suppressed_by_canonical_reexport = (
                            module_id != resolved
                            and initializer_direct_child_binding(
                                resolved,
                                alias.name,
                            )
                        )

                        if (
                            child != module_id
                            and not suppressed_by_canonical_reexport
                        ):
                            expected.add(child)

        if expected != set(hard_edges[module_id]):
            return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")

    return PackageGraphConsistency("CONSISTENT", None)
