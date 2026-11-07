"""Conservative graph/source agreement for restricted regular-package imports."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass

from .model_identity import indexed_to_logical_module, logical_to_indexed_module
from .typing_guard import (
    _typing_guard_parent_initializers,
    _typing_guard_passive_initializer,
    recognize_typing_guard,
    type_only_candidate_statement_ids,
)


@dataclass(frozen=True)
class PackageGraphConsistency:
    status: str
    reason: str | None
    unmodeled_external_imports: tuple[tuple[str, int, str, str], ...] = ()
    unmodeled_namespace_parents: tuple[tuple[str, int, str, str], ...] = ()
    internal_graph_state: str = "NOT_PROVED"
    checked_source_modules: tuple[str, ...] = ()


def assess_package_graph_consistency(
    hard_edges: Mapping[str, object],
    sources: Mapping[str, ast.Module],
    evidence_source_modules: tuple[str, ...],
) -> PackageGraphConsistency:
    """Check indexed imports and retain unmodeled import candidates."""
    def unknown(reason: str) -> PackageGraphConsistency:
        return PackageGraphConsistency("INDETERMINATE", reason)

    if not isinstance(hard_edges, Mapping) or not isinstance(sources, Mapping):
        return unknown("GRAPH_SOURCE_IMPORT_MISMATCH")
    indexed = frozenset(hard_edges)
    indexed_roots = frozenset(name.split(".", 1)[0] for name in indexed)
    unmodeled_external_imports: list[tuple[str, int, str, str]] = []
    unmodeled_namespace_parents: list[tuple[str, int, str, str]] = []
    if any(name not in indexed or not isinstance(sources.get(name), ast.Module)
           for name in evidence_source_modules):
        return unknown("MISSING_INDEXED_TARGET")

    def target(name: str) -> str | None:
        return logical_to_indexed_module(name, indexed)

    def parent_classification(name: str) -> tuple[str, tuple[str, ...]]:
        parts = name.split(".")
        namespace_parents: list[str] = []
        for length in range(1, len(parts)):
            parent = ".".join(parts[:length])
            initializer = parent + ".__init__"
            if initializer in indexed:
                if parent in indexed or not isinstance(
                    sources.get(initializer), ast.Module
                ):
                    return "INVALID", ()
                continue
            if parent in indexed or not any(
                module.startswith(parent + ".") for module in indexed
            ):
                return "INVALID", ()
            namespace_parents.append(parent)
        if namespace_parents:
            return "NAMESPACE_CANDIDATE", tuple(namespace_parents)
        return "REGULAR", ()

    def missing_namespace_base(name: str) -> tuple[str, ...] | None:
        if name in indexed or name + ".__init__" in indexed:
            return None
        if not any(module.startswith(name + ".") for module in indexed):
            return None
        parent_state, namespace_parents = parent_classification(name)
        if parent_state == "INVALID":
            return None
        return (*namespace_parents, name)

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
                        or parent_classification(
                            child_logical
                        )[0] != "REGULAR"
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
        type_only_ids = (
            type_only_candidate_statement_ids(
                sources[module_id],
                indexed,
            )
        )

        parents_proved = all(
            (
                parent_id in indexed
                and isinstance(
                    sources.get(parent_id),
                    ast.Module,
                )
                and _typing_guard_passive_initializer(
                    sources[parent_id]
                )
            )
            for parent_id in (
                _typing_guard_parent_initializers(
                    module_id
                )
            )
        )

        if not parents_proved:
            type_only_ids = frozenset()

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
                        if alias.name.split(".", 1)[0] in indexed_roots:
                            namespace_parents = missing_namespace_base(alias.name)
                            if namespace_parents is None:
                                return unknown("MISSING_INDEXED_TARGET")
                            unmodeled_namespace_parents.extend(
                                (module_id, node.lineno, alias.name, parent)
                                for parent in namespace_parents
                            )
                            continue
                        unmodeled_external_imports.append(
                            (module_id, node.lineno, "import", alias.name)
                        )
                        continue
                    if resolved != alias.name and resolved != alias.name + ".__init__":
                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
                    if resolved == alias.name and any(
                        module.startswith(alias.name + ".")
                        for module in indexed
                    ):
                        return unknown("AMBIGUOUS_PACKAGE_TARGET")
                    if resolved.endswith(".__init__") and not isinstance(
                        sources.get(resolved), ast.Module
                    ):
                        return unknown("MISSING_REQUIRED_INITIALIZER")
                    parent_state, namespace_parents = parent_classification(
                        alias.name
                    )
                    if parent_state == "INVALID":
                        return unknown("MISSING_REQUIRED_INITIALIZER")
                    unmodeled_namespace_parents.extend(
                        (module_id, node.lineno, alias.name, parent)
                        for parent in namespace_parents
                    )
                    if (
                        resolved != module_id
                        and id(node) not in type_only_ids
                    ):
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
                    if node.level or base.split(".", 1)[0] in indexed_roots:
                        if node.level:
                            return unknown("MISSING_INDEXED_TARGET")
                        namespace_parents = missing_namespace_base(base)
                        if namespace_parents is None:
                            return unknown("MISSING_INDEXED_TARGET")
                        unmodeled_namespace_parents.extend(
                            (module_id, node.lineno, base, parent)
                            for parent in namespace_parents
                        )
                        continue
                    unmodeled_external_imports.append(
                        (module_id, node.lineno, "from", base)
                    )
                    continue
                if resolved == base and any(
                    module.startswith(base + ".") for module in indexed
                ):
                    return unknown("AMBIGUOUS_PACKAGE_TARGET")
                parent_state, namespace_parents = parent_classification(base)
                if parent_state == "INVALID":
                    return unknown("MISSING_REQUIRED_INITIALIZER")
                unmodeled_namespace_parents.extend(
                    (module_id, node.lineno, base, parent)
                    for parent in namespace_parents
                )
                if resolved != module_id:
                    expected.add(resolved)
                if resolved.endswith(".__init__"):
                    # A named member may be an initializer attribute or child.
                    # Preserve the initializer hard edge and require indexed
                    # child source before admitting that bounded form.
                    if not (node.level and node.module is None):
                        initializer = sources.get(resolved)
                        if not isinstance(initializer, ast.Module):
                            return unknown("MISSING_REQUIRED_INITIALIZER")
                        for alias in node.names:
                            if (
                                not alias.name.isidentifier()
                                or alias.name.startswith("__")
                                or (
                                    alias.asname is not None
                                    and (
                                        not alias.asname.isidentifier()
                                        or alias.asname.startswith("__")
                                    )
                                )
                            ):
                                return unknown("UNSUPPORTED_IMPORT_FORM")
                            child = target(base + "." + alias.name)
                            if (
                                child is not None
                                and (
                                    child not in evidence_source_modules
                                    or not isinstance(
                                        sources.get(child), ast.Module
                                    )
                                )
                            ):
                                return unknown(
                                    "OPTIONAL_NAMED_CHILD_SOURCE_UNAVAILABLE"
                                )
                        continue
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

    checked_source_modules = tuple(sorted(evidence_source_modules))
    internal_graph_state = "INDEXED_AST_GRAPH_MATCH_FOR_SELECTED_SOURCES"
    if unmodeled_namespace_parents:
        return PackageGraphConsistency(
            "INDETERMINATE",
            "NAMESPACE_IMPORT_RESOLUTION_UNMODELED",
            tuple(sorted(unmodeled_external_imports)),
            tuple(sorted(unmodeled_namespace_parents)),
            internal_graph_state,
            checked_source_modules,
        )
    if unmodeled_external_imports:
        return PackageGraphConsistency(
            "INDETERMINATE",
            "EXTERNAL_IMPORT_EXECUTION_UNMODELED",
            tuple(sorted(unmodeled_external_imports)),
            internal_graph_state=internal_graph_state,
            checked_source_modules=checked_source_modules,
        )
    return PackageGraphConsistency(
        "CONSISTENT",
        None,
        internal_graph_state=internal_graph_state,
        checked_source_modules=checked_source_modules,
    )
