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
class ExternalImportScopeRecord:
    importer: str
    line: int
    column: int
    form: str
    target: str
    primary_scope: str
    ancestry_flags: tuple[str, ...]
    site_ordinal: int
    alias_ordinal: int | None = None
    local_binding: str | None = None
    from_members: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class PackageGraphConsistency:
    status: str
    reason: str | None
    unmodeled_external_imports: tuple[tuple[str, int, str, str], ...] = ()
    unmodeled_namespace_parents: tuple[tuple[str, int, str, str], ...] = ()
    internal_graph_state: str = "NOT_PROVED"
    checked_source_modules: tuple[str, ...] = ()
    external_scope_records: tuple[ExternalImportScopeRecord, ...] = ()
    external_execution_gate: str = "NOT_ESTABLISHED"


def _external_import_scope_index(
    tree: ast.Module,
) -> dict[int, tuple[str, tuple[str, ...], int]]:
    """Classify lexical import locations, never execution safety."""
    parents: dict[int, ast.AST | None] = {id(tree): None}

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    function_types = (ast.FunctionDef, ast.AsyncFunctionDef)
    try_types = (ast.Try, getattr(ast, "TryStar", ast.Try))
    loop_types = (ast.For, ast.AsyncFor, ast.While)
    with_types = (ast.With, ast.AsyncWith)

    result: dict[int, tuple[str, tuple[str, ...], int]] = {}

    import_nodes = sorted(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ),
        key=lambda node: (
            node.lineno,
            node.col_offset,
        ),
    )

    for site_ordinal, node in enumerate(import_nodes):

        ancestors: list[ast.AST] = []
        parent = parents.get(id(node))

        while parent is not None:
            ancestors.append(parent)
            parent = parents.get(id(parent))

        ancestors.reverse()

        definitions = [
            item for item in ancestors
            if isinstance(item, (*function_types, ast.ClassDef))
        ]

        function_positions = [
            index for index, item in enumerate(definitions)
            if isinstance(item, function_types)
        ]

        if function_positions:
            position = function_positions[-1]
            function = definitions[position]

            if (
                position > 0
                and isinstance(definitions[position - 1], ast.ClassDef)
            ):
                primary = "METHOD_BODY"
            elif isinstance(function, ast.AsyncFunctionDef):
                primary = "ASYNC_FUNCTION_BODY"
            else:
                primary = "FUNCTION_BODY"

        elif any(
            isinstance(item, ast.ClassDef)
            for item in definitions
        ):
            primary = "CLASS_BODY"

        else:
            primary = "MODULE_BODY"

        flags: list[str] = []

        if any(isinstance(item, ast.If) for item in ancestors):
            flags.append("IF")

        if any(isinstance(item, try_types) for item in ancestors):
            flags.append("TRY")

        if any(
            isinstance(item, ast.ExceptHandler)
            for item in ancestors
        ):
            flags.append("EXCEPT_HANDLER")

        if any(isinstance(item, loop_types) for item in ancestors):
            flags.append("LOOP")

        if any(isinstance(item, with_types) for item in ancestors):
            flags.append("WITH")

        if any(isinstance(item, ast.Match) for item in ancestors):
            flags.append("MATCH")

        result[id(node)] = (
            primary,
            tuple(flags),
            site_ordinal,
        )

    return result


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
    external_scopes: list[ExternalImportScopeRecord] = []
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

        scope_index = _external_import_scope_index(
            sources[module_id]
        )

        for node in ast.walk(sources[module_id]):
            if (
                typing_guard is not None
                and node is typing_guard.marker_statement
            ):
                continue

            if isinstance(node, ast.Import):
                for alias_ordinal, alias in enumerate(node.names):
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
                        primary, flags, site_ordinal = scope_index[id(node)]
                        external_scopes.append(
                            ExternalImportScopeRecord(
                                importer=module_id,
                                line=node.lineno,
                                column=node.col_offset,
                                form="import",
                                target=alias.name,
                                primary_scope=primary,
                                ancestry_flags=flags,
                                site_ordinal=site_ordinal,
                                alias_ordinal=alias_ordinal,
                                local_binding=(
                                    alias.asname or alias.name.split(".")[0]
                                ),
                            )
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
                    primary, flags, site_ordinal = scope_index[id(node)]
                    external_scopes.append(
                        ExternalImportScopeRecord(
                            importer=module_id,
                            line=node.lineno,
                            column=node.col_offset,
                            form="from",
                            target=base,
                            primary_scope=primary,
                            ancestry_flags=flags,
                            site_ordinal=site_ordinal,
                            from_members=tuple(
                                (
                                    alias.name,
                                    alias.asname or alias.name,
                                )
                                for alias in node.names
                            ),
                        )
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

    ordered_external_scopes = tuple(
        sorted(
            external_scopes,
            key=lambda row: (
                row.importer,
                row.line,
                row.form,
                row.target,
                row.column,
                row.primary_scope,
                row.ancestry_flags,
                row.site_ordinal,
                (
                    row.alias_ordinal
                    if row.alias_ordinal is not None
                    else -1
                ),
            ),
        )
    )

    external_effects_deferred_only = (
        bool(unmodeled_external_imports)
        and len(ordered_external_scopes)
        == len(unmodeled_external_imports)
        and all(
            row.primary_scope in {
                "FUNCTION_BODY",
                "ASYNC_FUNCTION_BODY",
                "METHOD_BODY",
            }
            for row in ordered_external_scopes
        )
    )

    external_gate = (
        "NOT_ESTABLISHED"
        if not unmodeled_external_imports
        else (
            "LEXICALLY_DEFERRED_ONLY"
            if external_effects_deferred_only
            else "OPAQUE_EXECUTION_POSSIBLE"
        )
    )

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
            external_scope_records=ordered_external_scopes,
            external_execution_gate=external_gate,
        )
    if unmodeled_external_imports:
        return PackageGraphConsistency(
            "INDETERMINATE",
            "EXTERNAL_IMPORT_EXECUTION_UNMODELED",
            tuple(sorted(unmodeled_external_imports)),
            internal_graph_state=internal_graph_state,
            checked_source_modules=checked_source_modules,
            external_scope_records=ordered_external_scopes,
            external_execution_gate=external_gate,
        )
    return PackageGraphConsistency(
        "CONSISTENT",
        None,
        internal_graph_state=internal_graph_state,
        checked_source_modules=checked_source_modules,
    )
