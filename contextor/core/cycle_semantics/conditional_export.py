"""Conditional source-order evidence for package reexports.

This module never executes indexed Python source.

Import statements are source evidence, not proof
that a concrete runtime import path is reachable.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ConditionalImportHop:
    source_id: str
    target_id: str
    line: int
    column: int
    requested_member: str


@dataclass(frozen=True)
class ConditionalReexportAssessment:
    status: str
    reason: str
    chain: tuple[str, ...]
    export_name: str
    package_reexport_line: int | None
    provider_definition_line: int | None
    hops: tuple[ConditionalImportHop, ...]
    evidence_scope: str = (
        "CONDITIONAL_SOURCE_ORDER_ONLY"
    )
    prefix_execution_status: str = (
        "UNVERIFIED_TRANSITIVE_PREFIX"
    )
    runtime_execution_status: str = (
        "UNKNOWN_NOT_EVALUATED"
    )


def _logical_module(indexed_id: str) -> str:
    if indexed_id.endswith(".__init__"):
        return indexed_id[:-len(".__init__")]

    return indexed_id


def _from_target(
    indexed_owner: str,
    statement: ast.ImportFrom,
) -> str | None:
    if statement.level == 0:
        return statement.module

    logical = _logical_module(indexed_owner)

    if indexed_owner.endswith(".__init__"):
        base = logical.split(".")
    else:
        base = logical.split(".")[:-1]

    climb = statement.level - 1

    if not base or climb >= len(base):
        return None

    base = base[:len(base) - climb]

    if statement.module:
        base.extend(statement.module.split("."))

    return ".".join(base)


def _exact_hop(
    sources: Mapping[str, ast.Module],
    source_id: str,
    target_id: str,
) -> ConditionalImportHop | None:
    tree = sources[source_id]
    target = _logical_module(target_id)

    matches: list[ConditionalImportHop] = []

    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom):
            continue

        if _from_target(source_id, statement) != target:
            continue

        if len(statement.names) != 1:
            return None

        alias = statement.names[0]

        if alias.name == "*":
            return None

        matches.append(
            ConditionalImportHop(
                source_id=source_id,
                target_id=target_id,
                line=statement.lineno,
                column=statement.col_offset,
                requested_member=alias.name,
            )
        )

    if len(matches) != 1:
        return None

    return matches[0]


def analyze_conditional_reexport_order(
    indexed_sources: Mapping[str, ast.Module],
    chain: tuple[str, ...],
    export_name: str,
) -> ConditionalReexportAssessment:
    """Validate a source-backed delayed-reexport pattern.

    The caller supplies the candidate chain.
    This function validates, but does not discover,
    execute or certify that chain as runtime-reachable.
    """

    chain_out = (
        chain
        if isinstance(chain, tuple)
        and all(isinstance(x, str) for x in chain)
        else ()
    )

    symbol_out = (
        export_name
        if isinstance(export_name, str)
        else ""
    )

    def result(
        status: str,
        reason: str,
        *,
        hops: tuple[ConditionalImportHop, ...] = (),
        reexport_line: int | None = None,
        definition_line: int | None = None,
    ) -> ConditionalReexportAssessment:
        return ConditionalReexportAssessment(
            status=status,
            reason=reason,
            chain=chain_out,
            export_name=symbol_out,
            package_reexport_line=reexport_line,
            provider_definition_line=definition_line,
            hops=hops,
        )

    if (
        not isinstance(indexed_sources, Mapping)
        or not chain_out
        or len(chain_out) < 4
        or chain_out[0] != chain_out[-1]
        or not chain_out[0].endswith(".__init__")
        or not symbol_out.isidentifier()
        or symbol_out.startswith("__")
        or len(set(chain_out[:-1])) != len(chain_out) - 1
    ):
        return result("UNKNOWN", "INVALID_INPUT_OR_CHAIN")

    if any(
        not isinstance(indexed_sources.get(name), ast.Module)
        for name in chain_out
    ):
        return result("UNKNOWN", "SOURCE_NOT_AVAILABLE")

    # AST parsing is weaker than CPython compilation.
    # An invalid, even never-called function body
    # prevents the containing module from importing.
    #
    # Validate only the modules in the supplied chain.
    # Compile code objects without executing them.
    for indexed_id in chain_out[:-1]:
        try:
            compile(
                indexed_sources[indexed_id],
                "<conditional_export:" + indexed_id + ">",
                "exec",
                dont_inherit=True,
            )
        except (
            SyntaxError,
            TypeError,
            ValueError,
            RecursionError,
            OverflowError,
        ):
            return result(
                "UNKNOWN",
                "SOURCE_NOT_COMPILABLE",
            )

    hops_list: list[ConditionalImportHop] = []

    for source_id, target_id in zip(
        chain_out,
        chain_out[1:],
    ):
        hop = _exact_hop(
            indexed_sources,
            source_id,
            target_id,
        )

        if hop is None:
            return result(
                "UNKNOWN",
                "IMPORT_HOP_NOT_UNIQUELY_PROVED",
            )

        hops_list.append(hop)

    hops = tuple(hops_list)

    if (
        hops[0].requested_member != symbol_out
        or hops[-1].requested_member != symbol_out
    ):
        return result(
            "UNKNOWN",
            "REEXPORT_AND_LOOKUP_NOT_MATCHED",
            hops=hops,
        )

    package_tree = indexed_sources[chain_out[0]]
    reexport_line = hops[0].line

    # Only a docstring or Pass can precede the
    # initial package reexport in this proof subset.
    # Anything else may bind or mutate package state.
    for statement in package_tree.body:
        if statement.lineno >= reexport_line:
            break

        if isinstance(statement, ast.Pass):
            continue

        if (
            isinstance(statement, ast.Expr)
            and isinstance(
                statement.value,
                ast.Constant,
            )
            and type(statement.value.value) is str
        ):
            continue

        return result(
            "UNKNOWN",
            "EARLIER_PACKAGE_EFFECT_UNSUPPORTED",
            hops=hops,
            reexport_line=reexport_line,
        )

    provider = chain_out[1]
    provider_tree = indexed_sources[provider]

    definitions = [
        statement
        for statement in provider_tree.body
        if isinstance(statement, ast.FunctionDef)
        and statement.name == symbol_out
    ]

    if len(definitions) != 1:
        return result(
            "UNKNOWN",
            "PROVIDER_DEFINITION_NOT_UNIQUE",
            hops=hops,
            reexport_line=reexport_line,
        )

    definition_line = definitions[0].lineno

    if definition_line <= hops[1].line:
        return result(
            "UNKNOWN",
            "PROVIDER_DEFINITION_NOT_DELAYED",
            hops=hops,
            reexport_line=reexport_line,
            definition_line=definition_line,
        )

    return result(
        "CONDITIONAL_DELAYED_REEXPORT",
        "SOURCE_IMPORT_CHAIN_PRECEDES_EXPORT_DEFINITION",
        hops=hops,
        reexport_line=reexport_line,
        definition_line=definition_line,
    )
