"""Restricted package-aware recursive import initialization evidence.

Only regular, indexed Python packages and simple import/constant/attribute AST.
Never executes analyzed code or certifies general runtime safety.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass

from contextor.core.cycle_semantics.package_layout import build_package_layout


@dataclass(frozen=True)
class PackageModelEvent:
    module: str
    operation: str
    target: str | None = None
    symbol: str | None = None


@dataclass(frozen=True)
class PackageImportAssessment:
    entry_module: str
    outcome: str
    target_module: str | None
    symbol: str | None
    events: tuple[PackageModelEvent, ...]
    evidence_scope: str = "RESTRICTED_REGULAR_PACKAGE_MODEL"


@dataclass(frozen=True)
class _Step:
    op: str
    target: str | None = None
    symbol: str | None = None
    binding: str | None = None
    explicit_alias: bool = False


def _compile(
    tree: ast.Module,
    logical: str,
    package: bool,
) -> tuple[_Step, ...] | None:
    steps: list[_Step] = []

    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if (
                    not all(part.isidentifier() for part in alias.name.split("."))
                    or (
                        alias.asname is not None
                        and (
                            not alias.asname.isidentifier()
                            or alias.asname.startswith("__")
                        )
                    )
                ):
                    return None

                steps.append(
                    _Step(
                        "IMPORT",
                        alias.name,
                        binding=alias.asname or alias.name.split(".")[0],
                        explicit_alias=alias.asname is not None,
                    )
                )

        elif isinstance(stmt, ast.ImportFrom):
            # Python resolves the entire fromlist before its STORE_NAME steps.
            # This model processes single members only, to avoid false proofs.
            if len(stmt.names) != 1:
                return None
            if stmt.level:
                context = (
                    logical.split(".")
                    if package
                    else logical.split(".")[:-1]
                )
                climb = stmt.level - 1

                if not context or climb >= len(context):
                    return None

                base = context[:len(context) - climb]

                if stmt.module:
                    if not all(
                        part.isidentifier()
                        for part in stmt.module.split(".")
                    ):
                        return None
                    base.extend(stmt.module.split("."))

                target = ".".join(base)
            else:
                target = stmt.module

            if not target or not all(
                part.isidentifier() for part in target.split(".")
            ):
                return None

            for alias in stmt.names:
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
                    return None

                steps.append(
                    _Step(
                        "FROM",
                        target,
                        alias.name,
                        alias.asname or alias.name,
                    )
                )

        elif isinstance(stmt, ast.Assign):
            if (
                len(stmt.targets) != 1
                or not isinstance(stmt.targets[0], ast.Name)
            ):
                return None

            name = stmt.targets[0].id
            if name.startswith("__"):
                return None

            value = stmt.value

            if (
                isinstance(value, ast.Constant)
                and type(value.value) in (
                    type(None),
                    bool,
                    int,
                    float,
                    complex,
                    str,
                    bytes,
                )
            ):
                steps.append(_Step("BIND", binding=name))

            elif (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and not value.attr.startswith("__")
            ):
                steps.append(
                    _Step(
                        "ATTR",
                        value.value.id,
                        value.attr,
                        name,
                    )
                )
            else:
                return None

        elif isinstance(stmt, ast.Pass):
            continue

        else:
            return None

    return tuple(steps)


def evaluate_package_import_order(
    indexed_sources: Mapping[str, ast.AST],
    entry_module: str,
) -> PackageImportAssessment:
    """Simulate a restricted closed regular-package source set.

    Indexed package __init__ IDs are translated to logical package names.
    The operation budget prevents unbounded model execution.

    Results cannot certify general Python import safety.
    """
    events: list[PackageModelEvent] = []

    def result(
        outcome: str,
        target: str | None = None,
        symbol: str | None = None,
    ) -> PackageImportAssessment:
        return PackageImportAssessment(
            entry_module,
            outcome,
            target,
            symbol,
            tuple(events),
        )

    if (
        not isinstance(indexed_sources, Mapping)
        or not isinstance(entry_module, str)
    ):
        return result("UNKNOWN")

    if any(
        not isinstance(name, str)
        or not isinstance(tree, ast.Module)
        for name, tree in indexed_sources.items()
    ):
        return result("UNKNOWN")

    try:
        layout = build_package_layout(indexed_sources)
    except (TypeError, ValueError):
        return result("UNKNOWN")

    nodes = {node.name: node for node in layout.nodes}

    logical_sources: dict[str, ast.Module] = {}
    packages: set[str] = set()

    for name, node in nodes.items():
        if node.kind not in {
            "REGULAR_PACKAGE",
            "MODULE_FILE",
        }:
            return result("UNKNOWN", name)

        indexed_id = node.indexed_module_ids[0]

        if indexed_id not in indexed_sources:
            return result("UNKNOWN", name)

        logical_sources[name] = indexed_sources[indexed_id]

        if node.kind == "REGULAR_PACKAGE":
            packages.add(name)

    def valid_chain(target: str) -> bool:
        if target not in logical_sources:
            return False

        parts = target.split(".")

        return all(
            ".".join(parts[:length]) in packages
            for length in range(1, len(parts))
        )

    if not valid_chain(entry_module):
        return result("UNKNOWN", entry_module)

    programs: dict[str, tuple[_Step, ...]] = {}

    for name, tree in logical_sources.items():
        if not valid_chain(name):
            return result("UNKNOWN", name)

        program = _compile(tree, name, name in packages)

        if program is None:
            return result("UNKNOWN", name)

        programs[name] = program

    # A package may prebind a same-named attribute before a later
    # from-import; the attribute takes priority. Keep more complex
    # package-owned import/rebinding sequences indeterminate.
    for package in packages:
        children = {
            name.rsplit(".", 1)[1]
            for name in programs
            if "." in name and name.rsplit(".", 1)[0] == package
        }
        writes_child = any(
            step.binding in children
            and (
                step.op == "BIND"
                or (step.op == "FROM" and step.target != package)
            )
            for step in programs[package]
        )
        if writes_child and any(
            step.op in {"IMPORT", "FROM"}
            for step in programs[package]
        ):
            return result("UNKNOWN", package)

    states = {
        name: "NEW"
        for name in programs
    }

    namespaces: dict[str, dict[str, str | None]] = {
        name: {}
        for name in programs
    }

    bootstrap = "\x00ENTRY"
    frames: list[tuple[str, int]] = [(bootstrap, 0)]

    def chain(name: str) -> tuple[str, ...]:
        parts = name.split(".")

        return tuple(
            ".".join(parts[:index])
            for index in range(1, len(parts) + 1)
        )

    def missing_piece(name: str) -> str | None:
        for piece in chain(name):
            if piece not in states:
                return piece

            if states[piece] == "NEW":
                return piece

        return None

    step_budget = 10000

    while frames:
        step_budget -= 1

        if step_budget < 0:
            return result("UNKNOWN")

        module, index = frames[-1]

        steps = (
            (_Step("IMPORT", entry_module, binding=None),)
            if module == bootstrap
            else programs[module]
        )

        if index >= len(steps):
            frames.pop()

            if module != bootstrap:
                states[module] = "READY"
                events.append(
                    PackageModelEvent(module, "READY")
                )

                if "." in module:
                    parent, child = module.rsplit(".", 1)
                    namespaces[parent][child] = module

                    events.append(
                        PackageModelEvent(
                            parent,
                            "BIND_CHILD",
                            module,
                            child,
                        )
                    )

            continue

        step = steps[index]

        if step.op in {"IMPORT", "FROM"}:
            target = step.target

            if not target or target not in programs:
                return result("UNKNOWN", target)

            next_piece = missing_piece(target)

            if next_piece:
                if next_piece not in programs:
                    return result("UNKNOWN", next_piece)

                states[next_piece] = "INITIALIZING"

                events.append(
                    PackageModelEvent(
                        module,
                        "START_IMPORT",
                        next_piece,
                    )
                )

                frames.append((next_piece, 0))
                continue

            if step.op == "IMPORT":
                if module != bootstrap:
                    if step.explicit_alias and "." in target:
                        parent, child = target.rsplit(".", 1)

                        if namespaces[parent].get(child) != target:
                            return result("UNKNOWN", target, child)

                    binding_target = (
                        target
                        if step.explicit_alias
                        else target.split(".")[0]
                    )

                    namespaces[module][step.binding] = binding_target

                    events.append(
                        PackageModelEvent(
                            module,
                            "IMPORT",
                            target,
                            step.binding,
                        )
                    )

            else:
                member = step.symbol

                # CPython checks a package attribute before attempting
                # to load a same-named child module. An existing binding
                # takes precedence over the indexed child candidate.
                if target in packages and member not in namespaces[target]:
                    child = target + "." + member

                    if child in programs:
                        # Reentrant fromlist fallback through sys.modules is
                        # intentionally unsupported by this restricted model.
                        if states[child] != "NEW":
                            return result("UNKNOWN", child, member)

                        next_child = missing_piece(child)

                        if next_child != child:
                            return result("UNKNOWN", child, member)

                        states[child] = "INITIALIZING"

                        events.append(
                            PackageModelEvent(
                                module,
                                "START_IMPORT",
                                child,
                            )
                        )

                        frames.append((child, 0))
                        continue

                if member not in namespaces[target]:
                    outcome = (
                        "EARLY_BINDING_HAZARD"
                        if states[target] == "INITIALIZING"
                        else "MISSING_EXPORT"
                    )

                    events.append(
                        PackageModelEvent(
                            module,
                            outcome,
                            target,
                            member,
                        )
                    )

                    return result(outcome, target, member)

                namespaces[module][step.binding] = namespaces[target][member]

                events.append(
                    PackageModelEvent(
                        module,
                        "FROM",
                        target,
                        member,
                    )
                )

        elif step.op == "BIND":
            namespaces[module][step.binding] = None

            events.append(
                PackageModelEvent(
                    module,
                    "BIND",
                    symbol=step.binding,
                )
            )

        elif step.op == "ATTR":
            reference = namespaces[module].get(step.target)

            if reference not in namespaces:
                return result(
                    "UNKNOWN",
                    step.target,
                    step.symbol,
                )

            if step.symbol not in namespaces[reference]:
                outcome = (
                    "EARLY_BINDING_HAZARD"
                    if states[reference] == "INITIALIZING"
                    else "MISSING_ATTRIBUTE"
                )

                events.append(
                    PackageModelEvent(
                        module,
                        outcome,
                        reference,
                        step.symbol,
                    )
                )

                return result(
                    outcome,
                    reference,
                    step.symbol,
                )

            namespaces[module][step.binding] = namespaces[reference][step.symbol]

            events.append(
                PackageModelEvent(
                    module,
                    "ATTR",
                    reference,
                    step.symbol,
                )
            )

        else:
            return result("UNKNOWN")

        frames[-1] = (module, index + 1)

    return result("MODEL_PASS")
