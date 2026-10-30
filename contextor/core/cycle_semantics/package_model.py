"""Restricted package-aware recursive import initialization evidence.

Only regular, indexed Python packages and simple import/constant/attribute AST.
Never executes analyzed code or certifies general runtime safety.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from contextor.core.cycle_semantics.package_layout import build_package_layout
from contextor.core.cycle_semantics.typing_guard import (
    RecognizedTypingGuard,
    matches_typing_guard,
    recognize_typing_guard,
)


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
    function_body: tuple[_Step, ...] = ()
    function_local: bool = False
    class_local: bool = False


@dataclass
class _PackageSourceSession:
    """Ephemeral SCC-local cache; never published or shared across analyses."""

    source_trees: tuple[tuple[str, ast.Module], ...] | None = None
    layout: object | None = None
    validated_code: set[str] = field(default_factory=set)
    compiled_steps: dict[str, tuple[_Step, ...]] = field(
        default_factory=dict
    )


def _safe_passive_function_definition(
    statement: ast.FunctionDef,
    *,
    allow_dunder: bool = False,
) -> bool:
    """A definition whose creation has no unknown evaluations.

    Its body may be opaque because function bodies are deferred.
    Only literal default expressions are supported.
    """
    if (
        not statement.name.isidentifier()
        or (
            statement.name.startswith("__")
            and not allow_dunder
        )
        or statement.decorator_list
        or statement.returns is not None
        or statement.type_comment is not None
        or getattr(statement, "type_params", ())
    ):
        return False

    arguments = statement.args

    parameters = (
        tuple(arguments.posonlyargs)
        + tuple(arguments.args)
        + tuple(arguments.kwonlyargs)
        + (
            (arguments.vararg,)
            if arguments.vararg is not None
            else ()
        )
        + (
            (arguments.kwarg,)
            if arguments.kwarg is not None
            else ()
        )
    )

    if any(
        parameter.annotation is not None
        for parameter in parameters
    ):
        return False

    def safe_default(value: ast.AST) -> bool:
        return (
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
        )

    if any(
        not safe_default(value)
        for value in arguments.defaults
    ):
        return False

    if any(
        value is not None and not safe_default(value)
        for value in arguments.kw_defaults
    ):
        return False

    return True


def _safe_passive_class_definition(
    statement: ast.ClassDef,
) -> bool:
    """Validate a class whose body has no unknown effects.

    Class body evaluation is not generally passive.
    Only a literal docstring, Pass, safe method
    definitions and restricted imports are modeled.

    Direct class-body imports execute before class-name
    binding. Method bodies remain deferred.
    """
    if (
        not statement.name.isidentifier()
        or statement.name.startswith("__")
        or statement.bases
        or statement.keywords
        or statement.decorator_list
        or getattr(statement, "type_params", ())
    ):
        return False

    for index, body_statement in enumerate(
        statement.body
    ):
        if isinstance(body_statement, ast.Pass):
            continue

        if isinstance(body_statement, (ast.Import, ast.ImportFrom)):
            continue

        if (
            index == 0
            and isinstance(body_statement, ast.Expr)
            and isinstance(
                body_statement.value,
                ast.Constant,
            )
            and type(body_statement.value.value) is str
        ):
            continue

        if (
            isinstance(body_statement, ast.FunctionDef)
            and _safe_passive_function_definition(
                body_statement,
                allow_dunder=True,
            )
        ):
            continue

        return False

    return True


def _compile(
    tree: ast.Module,
    logical: str,
    package: bool,
    _depth: int = 0,
    typing_guard: RecognizedTypingGuard | None = None,
) -> tuple[_Step, ...] | None:
    steps: list[_Step] = []

    if _depth >= 32:
        return None

    for statement_index, stmt in enumerate(tree.body):
        if (
            _depth == 0
            and statement_index == 0
            and isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and type(stmt.value.value) is str
        ):
            # A module docstring literal has no import-time side effects.
            # The restricted model cannot observe __doc__ through its
            # supported attribute/import operations.
            continue

        if (
            _depth == 0
            and typing_guard is not None
            and stmt is typing_guard.marker_statement
        ):
            steps.append(
                _Step(
                    "TYPING_MARKER_IMPORT",
                    target="typing",
                    symbol="TYPE_CHECKING",
                    binding=(
                        "TYPE_CHECKING"
                        if typing_guard.form == "NAME"
                        else "typing"
                    ),
                )
            )
            continue

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
            # CPython resolves the fromlist during IMPORT_NAME,
            # before individual IMPORT_FROM / STORE_NAME operations.
            if not stmt.names:
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

            if len(stmt.names) > 1:
                # Validate every member before emitting phase steps.
                if any(
                    not alias.name.isidentifier()
                    or alias.name.startswith("__")
                    or (
                        alias.asname is not None
                        and (
                            not alias.asname.isidentifier()
                            or alias.asname.startswith("__")
                        )
                    )
                    for alias in stmt.names
                ):
                    return None

                for alias in stmt.names:
                    steps.append(
                        _Step(
                            "PREPARE_FROM_MEMBER",
                            target,
                            alias.name,
                        )
                    )

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

        elif isinstance(stmt, ast.If):
            condition = stmt.test

            if (
                isinstance(condition, ast.Constant)
                and type(condition.value) is bool
            ):
                selected = (
                    stmt.body
                    if condition.value
                    else stmt.orelse
                )
            elif (
                _depth == 0
                and typing_guard is not None
                and matches_typing_guard(
                    condition,
                    typing_guard.form,
                )
            ):
                selected = stmt.orelse
            else:
                if (
                    not isinstance(condition, ast.Compare)
                    or not isinstance(condition.left, ast.Name)
                    or condition.left.id != "__name__"
                    or len(condition.ops) != 1
                    or not isinstance(
                        condition.ops[0],
                        (ast.Eq, ast.NotEq),
                    )
                    or len(condition.comparators) != 1
                    or not isinstance(
                        condition.comparators[0],
                        ast.Constant,
                    )
                    or type(
                        condition.comparators[0].value
                    ) is not str
                    or condition.comparators[0].value
                    != "__main__"
                ):
                    return None

                selected = (
                    stmt.orelse
                    if isinstance(condition.ops[0], ast.Eq)
                    else stmt.body
                )

            selected_steps = _compile(
                ast.Module(
                    body=selected,
                    type_ignores=[],
                ),
                logical,
                package,
                _depth=_depth + 1,
            )

            if selected_steps is None:
                return None

            steps.extend(selected_steps)

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

        elif isinstance(stmt, ast.ClassDef):
            if not _safe_passive_class_definition(stmt):
                return None

            for body_statement in stmt.body:
                if not isinstance(
                    body_statement,
                    (ast.Import, ast.ImportFrom),
                ):
                    continue

                fragment = ast.Module(
                    body=[body_statement],
                    type_ignores=[],
                )
                compiled = _compile(
                    fragment,
                    logical,
                    package,
                    _depth=_depth + 1,
                )
                if (
                    compiled is None
                    or any(
                        item.op not in {
                            "IMPORT",
                            "FROM",
                            "PREPARE_FROM_MEMBER",
                        }
                        for item in compiled
                    )
                ):
                    return None

                steps.extend(
                    replace(item, class_local=True)
                    for item in compiled
                )

            steps.append(
                _Step(
                    "DEFINE_PASSIVE_CLASS",
                    binding=stmt.name,
                )
            )

        elif isinstance(stmt, ast.FunctionDef):
            if not _safe_passive_function_definition(stmt):
                return None

            args = stmt.args

            restricted_callable = not (
                args.posonlyargs
                or args.args
                or args.vararg is not None
                or args.kwonlyargs
                or args.kwarg is not None
                or args.defaults
                or args.kw_defaults
            )

            function_steps: list[_Step] = []

            if restricted_callable:
                for body_statement in stmt.body:
                    if isinstance(body_statement, ast.Pass):
                        continue

                    if not isinstance(
                        body_statement,
                        (ast.Import, ast.ImportFrom),
                    ):
                        restricted_callable = False
                        break

                    fragment = ast.Module(
                        body=[body_statement],
                        type_ignores=[],
                    )

                    compiled = _compile(
                        fragment,
                        logical,
                        package,
                    )

                    if (
                        compiled is None
                        or any(
                            item.op not in {
                                "IMPORT",
                                "FROM",
                                "PREPARE_FROM_MEMBER",
                            }
                            for item in compiled
                        )
                    ):
                        restricted_callable = False
                        break

                    function_steps.extend(
                        replace(
                            item,
                            function_local=True,
                        )
                        for item in compiled
                    )

            if restricted_callable:
                steps.append(
                    _Step(
                        "DEFINE_FUNCTION",
                        binding=stmt.name,
                        function_body=tuple(function_steps),
                    )
                )
            else:
                steps.append(
                    _Step(
                        "DEFINE_OPAQUE_FUNCTION",
                        binding=stmt.name,
                    )
                )

        elif isinstance(stmt, ast.Expr):
            expression = stmt.value

            if (
                not isinstance(expression, ast.Call)
                or not isinstance(expression.func, ast.Name)
                or expression.func.id.startswith("__")
                or expression.args
                or expression.keywords
            ):
                return None

            steps.append(
                _Step(
                    "CALL_FUNCTION",
                    target=expression.func.id,
                )
            )

        elif isinstance(stmt, ast.Pass):
            continue

        else:
            return None

    return tuple(steps)


def evaluate_package_import_order(
    indexed_sources: Mapping[str, ast.AST],
    entry_module: str,
    *,
    _session: _PackageSourceSession | None = None,
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

    # Reuse source-independent preparation only for the exact same
    # AST objects inside one SCC evaluation. This private cache must
    # never outlive the analyze_cycle_scenarios invocation.
    if _session is not None:
        if type(_session) is not _PackageSourceSession:
            return result("UNKNOWN")

        current_sources = tuple(sorted(indexed_sources.items()))

        if _session.source_trees is None:
            _session.source_trees = current_sources
        elif (
            len(_session.source_trees) != len(current_sources)
            or any(
                stored_name != name or stored_tree is not tree
                for (stored_name, stored_tree), (name, tree)
                in zip(_session.source_trees, current_sources)
            )
        ):
            return result("UNKNOWN")

    # An unsupported package layout cannot establish MODEL_PASS.
    # Retain fail-fast rejection before CPython compilation.
    if _session is not None and _session.layout is not None:
        layout = _session.layout
    else:
        try:
            layout = build_package_layout(indexed_sources)
        except (TypeError, ValueError):
            return result("UNKNOWN")
        if _session is not None:
            _session.layout = layout

    nodes = {node.name: node for node in layout.nodes}
    unsupported_layout = next(
        (
            node.name
            for node in layout.nodes
            if node.kind not in {
                "REGULAR_PACKAGE",
                "MODULE_FILE",
            }
        ),
        None,
    )
    if unsupported_layout is not None:
        return result("UNKNOWN", unsupported_layout)

    # AST parsing alone does not enforce every CPython
    # compilation rule. Even an uncalled function body
    # may contain a compile-time SyntaxError.
    #
    # Compile code objects WITHOUT executing them.
    # Fail closed instead of accepting an invalid
    # opaque function definition as MODEL_PASS.
    for indexed_id, tree in indexed_sources.items():
        if (
            _session is not None
            and indexed_id in _session.validated_code
        ):
            continue

        try:
            compile(
                tree,
                "<cycle_semantics:" + indexed_id + ">",
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
            return result("UNKNOWN", indexed_id)

        if _session is not None:
            _session.validated_code.add(indexed_id)

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

    programs: dict[str, list[_Step]] = {}

    for name, tree in logical_sources.items():
        if not valid_chain(name):
            return result("UNKNOWN", name)

        indexed_id = nodes[name].indexed_module_ids[0]
        typing_guard = recognize_typing_guard(
            indexed_sources[indexed_id],
            frozenset(indexed_sources),
        )
        if (
            _session is not None
            and name in _session.compiled_steps
        ):
            program = _session.compiled_steps[name]
        else:
            program = _compile(
                tree,
                name,
                name in packages,
                typing_guard=typing_guard,
            )
            if program is not None and _session is not None:
                _session.compiled_steps[name] = program

        if program is None:
            return result("UNKNOWN", name)

        # The interpreter can splice function body steps into
        # programs[module]. Never execute a cached list directly.
        programs[name] = list(program)

    # A package may prebind a same-named attribute before a later
    # from-import; the attribute takes priority. Keep more complex
    # package-owned import/rebinding sequences indeterminate.
    for package in packages:
        children = {
            name.rsplit(".", 1)[1]
            for name in programs
            if "." in name and name.rsplit(".", 1)[0] == package
        }
        # A function and a direct indexed child with the
        # same package attribute name need richer shadowing
        # and import-binding semantics.
        if any(
            step.op in {
                "DEFINE_FUNCTION",
                "DEFINE_OPAQUE_FUNCTION",
                "DEFINE_PASSIVE_CLASS",
            }
            and step.binding in children
            for step in programs[package]
        ):
            return result("UNKNOWN", package)

        writes_child = any(
            step.binding in children
            and (
                step.op == "BIND"
                or (step.op == "FROM" and step.target != package)
            )
            for step in programs[package]
        )
        if writes_child and any(
            step.op in {"IMPORT", "FROM", "CALL_FUNCTION"}
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

    function_definitions: dict[
        str,
        dict[str, tuple[_Step, ...]],
    ] = {
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

        if step.op == "TYPING_MARKER_IMPORT":
            if not step.binding:
                return result("UNKNOWN")

            namespaces[module][step.binding] = (
                "\x00TYPING_MARKER:" + module + ":" + step.binding
            )

            events.append(
                PackageModelEvent(
                    module,
                    "TYPING_MARKER_IMPORT",
                    target="typing",
                    symbol="TYPE_CHECKING",
                )
            )

        elif step.op in {
            "IMPORT",
            "FROM",
            "PREPARE_FROM_MEMBER",
        }:
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

            if step.op == "PREPARE_FROM_MEMBER":
                member = step.symbol

                if (
                    target in packages
                    and member not in namespaces[target]
                ):
                    child = target + "." + member

                    if child in programs:
                        if states[child] == "NEW":
                            if missing_piece(child) != child:
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

                        if states[child] == "INITIALIZING":
                            if not any(
                                active == child
                                for active, _ in frames
                            ):
                                return result("UNKNOWN", child, member)

                        elif states[child] == "READY":
                            return result("UNKNOWN", child, member)

                events.append(
                    PackageModelEvent(
                        module,
                        "PREPARE_FROM_MEMBER",
                        target,
                        member,
                    )
                )

            elif step.op == "IMPORT":
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

                    if not step.function_local and not step.class_local:
                        namespaces[module][step.binding] = binding_target

                    events.append(
                        PackageModelEvent(
                            module,
                            (
                                "FUNCTION_LOCAL_IMPORT"
                                if step.function_local
                                else "CLASS_LOCAL_IMPORT"
                                if step.class_local
                                else "IMPORT"
                            ),
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
                        # CPython 3.10 IMPORT_FROM can fall back to sys.modules
                        # for a child that has not yet been attached to its
                        # parent package. Model only the active same-thread case.
                        if states[child] == "INITIALIZING":
                            if not any(
                                active == child
                                for active, _ in frames
                            ):
                                return result("UNKNOWN", child, member)

                            if not step.function_local and not step.class_local:
                                namespaces[module][step.binding] = child

                            events.append(
                                PackageModelEvent(
                                    module,
                                    (
                                        "FUNCTION_LOCAL_FROM_REENTRANT_CHILD"
                                        if step.function_local
                                        else "CLASS_LOCAL_FROM_REENTRANT_CHILD"
                                        if step.class_local
                                        else "FROM_REENTRANT_CHILD"
                                    ),
                                    child,
                                    member,
                                )
                            )

                            frames[-1] = (module, index + 1)
                            continue

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

                if not step.function_local and not step.class_local:
                    namespaces[module][step.binding] = namespaces[target][member]

                events.append(
                    PackageModelEvent(
                        module,
                        (
                            "FUNCTION_LOCAL_FROM"
                            if step.function_local
                            else "CLASS_LOCAL_FROM"
                            if step.class_local
                            else "FROM"
                        ),
                        target,
                        member,
                    )
                )

        elif step.op == "DEFINE_FUNCTION":
            function_definitions[module][step.binding] = (
                step.function_body
            )

            namespaces[module][step.binding] = (
                "\x00FUNCTION:" + module + ":" + step.binding
            )

            events.append(
                PackageModelEvent(
                    module,
                    "DEFINE_FUNCTION",
                    symbol=step.binding,
                )
            )

        elif step.op == "DEFINE_OPAQUE_FUNCTION":
            namespaces[module][step.binding] = (
                "\x00OPAQUE_FUNCTION:"
                + module
                + ":"
                + step.binding
            )

            events.append(
                PackageModelEvent(
                    module,
                    "DEFINE_OPAQUE_FUNCTION",
                    symbol=step.binding,
                )
            )

        elif step.op == "DEFINE_PASSIVE_CLASS":
            namespaces[module][step.binding] = (
                "\x00PASSIVE_CLASS:"
                + module
                + ":"
                + step.binding
            )

            events.append(
                PackageModelEvent(
                    module,
                    "DEFINE_PASSIVE_CLASS",
                    symbol=step.binding,
                )
            )

        elif step.op == "CALL_FUNCTION":
            expected_binding = (
                "\x00FUNCTION:" + module + ":" + step.target
            )

            if (
                namespaces[module].get(step.target)
                != expected_binding
                or step.target
                not in function_definitions[module]
            ):
                return result(
                    "UNKNOWN",
                    module,
                    step.target,
                )

            # Expand the function's restricted import-only body
            # at its actual call site. This changes only the
            # in-memory compiled execution sequence, never
            # caller AST or source bytes.
            body_steps = function_definitions[module][step.target]

            programs[module][
                index + 1:index + 1
            ] = list(body_steps)

            events.append(
                PackageModelEvent(
                    module,
                    "CALL_FUNCTION",
                    symbol=step.target,
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
