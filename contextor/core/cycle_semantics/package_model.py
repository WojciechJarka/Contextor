"""Restricted package-aware recursive import initialization evidence.

Only regular, indexed Python packages and simple import/constant/attribute AST.
Never executes analyzed code or certifies general runtime safety.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from contextor.core.cycle_semantics.package_layout import build_package_layout
from contextor.core.cycle_semantics.namespace_path_model import (
    SearchPortion,
    resolve_namespace_path,
)
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
class ReachedUnmodeledImport:
    importer: str
    operation: str
    target: str
    symbol: str | None
    line: int | None
    column: int | None


@dataclass(frozen=True)
class AssumedFrozenDataclassDecoration:
    module: str
    class_name: str
    decorator: str
    line: int
    column: int


@dataclass(frozen=True)
class PackageImportAssessment:
    entry_module: str
    outcome: str
    target_module: str | None
    symbol: str | None
    events: tuple[PackageModelEvent, ...]
    evidence_scope: str = "RESTRICTED_REGULAR_PACKAGE_MODEL"
    reached_unmodeled_import: (
        ReachedUnmodeledImport | None
    ) = None
    assumed_external_imports: (
        tuple[ReachedUnmodeledImport, ...]
    ) = ()
    assumed_dataclass_decorations: (
        tuple[AssumedFrozenDataclassDecoration, ...]
    ) = ()


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
    source_line: int | None = None
    source_column: int | None = None
    annotation_builtin_names: tuple[str, ...] = ()


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
    statement: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    allow_dunder: bool = False,
    annotation_semantics: str | None = None,
    allow_builtin_property: bool = False,
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
        or (
            bool(statement.decorator_list)
            and not (
                allow_builtin_property
                and type(statement) is ast.FunctionDef
                and len(statement.decorator_list) == 1
                and type(statement.decorator_list[0])
                is ast.Name
                and statement.decorator_list[0].id
                == "property"
            )
        )
        or (statement.returns is not None and annotation_semantics not in {
            "DEFERRED", "STRINGIFIED",
        })
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

    if annotation_semantics not in {"DEFERRED", "STRINGIFIED"} and any(
        parameter.annotation is not None for parameter in parameters
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


def _exact_frozen_dataclass_decorator(
    decorator: ast.AST,
) -> bool:
    return (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Name)
        and decorator.func.id == "dataclass"
        and not decorator.args
        and len(decorator.keywords) == 1
        and decorator.keywords[0].arg == "frozen"
        and isinstance(
            decorator.keywords[0].value,
            ast.Constant,
        )
        and decorator.keywords[0].value.value is True
        and type(
            decorator.keywords[0].value.value
        ) is bool
    )


def _exact_restricted_dataclass_hash_field_call(
    node: ast.AST,
) -> bool:
    return (
        type(node) is ast.Call
        and type(node.func) is ast.Name
        and node.func.id == "field"
        and not node.args
        and len(node.keywords) == 1
        and node.keywords[0].arg == "hash"
        and type(node.keywords[0].value) is ast.Constant
        and type(node.keywords[0].value.value) is bool
        and node.keywords[0].value.value is False
    )


def _restricted_dataclass_field_annotation(
    node: ast.AST,
) -> bool:
    if isinstance(node, ast.Name):
        return (
            node.id.isidentifier()
            and not node.id.startswith("__")
            and node.id != "ast"
        )

    if type(node) is ast.Attribute:
        return (
            type(node.value) is ast.Name
            and node.value.id == "ast"
            and node.attr == "AST"
        )

    if isinstance(node, ast.Constant):
        return type(node.value) is str

    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, ast.BitOr):
            return False

        if (
            isinstance(node.left, ast.Constant)
            and type(node.left.value) is type(None)
            and not isinstance(node.right, ast.BinOp)
        ):
            return _restricted_dataclass_field_annotation(
                node.right
            )

        if (
            isinstance(node.right, ast.Constant)
            and type(node.right.value) is type(None)
            and not isinstance(node.left, ast.BinOp)
        ):
            return _restricted_dataclass_field_annotation(
                node.left
            )

        return False

    if isinstance(node, ast.Tuple):
        return all(
            _restricted_dataclass_field_annotation(item)
            for item in node.elts
        )

    if isinstance(node, ast.Subscript):
        return (
            _restricted_dataclass_field_annotation(
                node.value
            )
            and _restricted_dataclass_field_annotation(
                node.slice
            )
        )

    return False


def _safe_passive_class_definition(
    statement: ast.ClassDef,
    *,
    annotation_semantics: str | None = None,
    allow_conditional_frozen_dataclass: bool = False,
) -> bool:
    """Validate a class whose body has no unknown effects.

    Class body evaluation is not generally passive.
    Only a literal docstring, Pass, safe method
    definitions and restricted imports are modeled.

    Direct class-body imports execute before class-name
    binding. Method bodies remain deferred.
    """
    conditional_dataclass = (
        allow_conditional_frozen_dataclass
        and annotation_semantics == "DEFERRED"
        and len(statement.decorator_list) == 1
        and _exact_frozen_dataclass_decorator(
            statement.decorator_list[0]
        )
    )
    if (
        not statement.name.isidentifier()
        or statement.name.startswith("__")
        or (
            bool(statement.bases)
            and (
                conditional_dataclass
                or len(statement.bases) != 1
                or type(statement.bases[0]) is not ast.Name
                or statement.bases[0].id != "ValueError"
            )
        )
        or statement.keywords
        or (
            bool(statement.decorator_list)
            and not conditional_dataclass
        )
        or getattr(statement, "type_params", ())
    ):
        return False

    if conditional_dataclass:
        seen_default_field = False

        uses_field_call = any(
            isinstance(item, ast.AnnAssign)
            and item.value is not None
            and _exact_restricted_dataclass_hash_field_call(
                item.value
            )
            for item in statement.body
        )

        uses_property = any(
            type(item) is ast.FunctionDef
            and len(item.decorator_list) == 1
            and type(item.decorator_list[0]) is ast.Name
            and item.decorator_list[0].id == "property"
            for item in statement.body
        )

        protected_names = set()

        if uses_field_call:
            protected_names.add("field")

        if uses_property:
            protected_names.add("property")

        if any(
            (
                isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and item.target.id in protected_names
            )
            or (
                isinstance(
                    item,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                )
                and item.name in protected_names
            )
            for item in statement.body
        ):
            return False

        for body_statement in statement.body:
            if isinstance(
                body_statement,
                (ast.Import, ast.ImportFrom, ast.Assign),
            ):
                return False

            if isinstance(body_statement, ast.AnnAssign):
                if not _restricted_dataclass_field_annotation(
                    body_statement.annotation
                ):
                    return False

                default_value = body_statement.value

                if default_value is None:
                    if seen_default_field:
                        return False
                else:
                    literal_default = (
                        type(default_value) is ast.Constant
                        and type(default_value.value) in {
                            type(None),
                            bool,
                            int,
                            float,
                            complex,
                            str,
                            bytes,
                        }
                    )

                    if (
                        not literal_default
                        and not
                        _exact_restricted_dataclass_hash_field_call(
                            default_value
                        )
                    ):
                        return False

                    seen_default_field = True

            if isinstance(
                body_statement,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                if body_statement.name.startswith("__"):
                    return False

    for index, body_statement in enumerate(
        statement.body
    ):
        if isinstance(body_statement, ast.Pass):
            continue

        if isinstance(body_statement, (ast.Import, ast.ImportFrom)):
            continue

        if isinstance(body_statement, ast.AnnAssign):
            if _safe_annassign(
                body_statement, annotation_semantics,
            ):
                continue

            if (
                conditional_dataclass
                and type(body_statement.target) is ast.Name
                and body_statement.simple == 1
                and body_statement.target.id.isidentifier()
                and not body_statement.target.id.startswith("__")
                and _exact_restricted_dataclass_hash_field_call(
                    body_statement.value
                )
            ):
                continue

            return False

        if isinstance(body_statement, ast.Assign):
            if (
                len(body_statement.targets) != 1
                or not isinstance(
                    body_statement.targets[0], ast.Name
                )
                or not body_statement.targets[0].id.isidentifier()
                or body_statement.targets[0].id.startswith("__")
                or not _pure_literal_expression(
                    body_statement.value
                )
            ):
                return False

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
            isinstance(
                body_statement,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
            and _safe_passive_function_definition(
                body_statement,
                allow_dunder=True,
                annotation_semantics=annotation_semantics,
                allow_builtin_property=conditional_dataclass,
            )
        ):
            continue

        return False

    return True


def _bounded_integer_arithmetic(
    expression: ast.AST,
    *,
    depth: int,
    node_budget: int,
) -> tuple[bool, int]:
    """Recognize bounded, exact built-in integer arithmetic only."""
    used = 0

    def calculate(
        node: ast.AST,
        node_depth: int,
    ) -> int | None:
        nonlocal used

        if node_depth > 16 or used >= node_budget:
            return None

        used += 1

        if type(node) is ast.Constant:
            if type(node.value) is not int:
                return None
            value = node.value

        elif type(node) is ast.UnaryOp:
            if type(node.op) not in (ast.UAdd, ast.USub):
                return None

            operand = calculate(
                node.operand,
                node_depth + 1,
            )
            if operand is None:
                return None

            value = (
                operand
                if type(node.op) is ast.UAdd
                else -operand
            )

        elif type(node) is ast.BinOp:
            if type(node.op) not in (
                ast.Add,
                ast.Sub,
                ast.Mult,
            ):
                return None

            left = calculate(node.left, node_depth + 1)
            if left is None:
                return None

            right = calculate(node.right, node_depth + 1)
            if right is None:
                return None

            if type(node.op) is ast.Add:
                value = left + right
            elif type(node.op) is ast.Sub:
                value = left - right
            else:
                value = left * right

        else:
            return None

        if value.bit_length() > 64:
            return None

        return value

    accepted = calculate(expression, depth) is not None
    return accepted, used


def _pure_literal_expression(expr: ast.AST) -> bool:
    pending: list[tuple[ast.AST, int, bool]] = [
        (expr, 0, False)
    ]
    visited = 0

    while pending:
        node, depth, hashable_required = pending.pop()
        visited += 1

        if visited > 256 or depth > 16:
            return False

        if type(node) is ast.Constant:
            if type(node.value) not in {
                type(None), bool, int, float,
                complex, str, bytes,
            }:
                return False
            continue

        if type(node) is ast.UnaryOp:
            if (
                type(node.op) not in (ast.UAdd, ast.USub)
                or type(node.operand) is not ast.Constant
                or type(node.operand.value)
                not in (int, float, complex)
            ):
                return False

            pending.append(
                (node.operand, depth + 1, hashable_required)
            )
            continue

        if type(node) is ast.BinOp:
            accepted, counted = _bounded_integer_arithmetic(
                node,
                depth=depth,
                node_budget=257 - visited,
            )

            visited += counted - 1

            if not accepted or visited > 256:
                return False

            continue

        if type(node) is ast.Tuple:
            pending.extend(
                (item, depth + 1, hashable_required)
                for item in reversed(node.elts)
            )
            continue

        if type(node) is ast.List:
            if hashable_required:
                return False

            pending.extend(
                (item, depth + 1, False)
                for item in reversed(node.elts)
            )
            continue

        if type(node) is ast.Set:
            if hashable_required:
                return False

            pending.extend(
                (item, depth + 1, True)
                for item in reversed(node.elts)
            )
            continue

        if type(node) is ast.Dict:
            if (
                hashable_required
                or len(node.keys) != len(node.values)
                or any(key is None for key in node.keys)
            ):
                return False

            for key, value in reversed(
                list(zip(node.keys, node.values))
            ):
                pending.append(
                    (value, depth + 1, False)
                )
                pending.append(
                    (key, depth + 1, True)
                )
            continue

        return False

    return True


def _pure_all_assignment(value: ast.AST) -> bool:
    return (
        type(value) in (ast.List, ast.Tuple)
        and _pure_literal_expression(value)
        and all(
            type(item) is ast.Constant
            and type(item.value) is str
            for item in value.elts
        )
    )


def _safe_annassign(
    statement: ast.AnnAssign,
    annotation_semantics: str | None,
) -> bool:
    if (
        annotation_semantics not in {"DEFERRED", "STRINGIFIED"}
        or not isinstance(statement.target, ast.Name)
        or statement.simple != 1
        or not statement.target.id.isidentifier()
        or statement.target.id.startswith("__")
    ):
        return False
    return (
        statement.value is None
        or _pure_literal_expression(statement.value)
    )


def _compile(
    tree: ast.Module,
    logical: str,
    package: bool,
    _depth: int = 0,
    typing_guard: RecognizedTypingGuard | None = None,
    annotation_semantics: str | None = None,
    assume_frozen_dataclass: bool = False,
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

        if isinstance(stmt, ast.Import):
            if getattr(stmt, "is_lazy", False):
                return None
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
                        source_line=stmt.lineno,
                        source_column=stmt.col_offset,
                    )
                )

        elif isinstance(stmt, ast.ImportFrom):
            if getattr(stmt, "is_lazy", False):
                return None
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
                            source_line=stmt.lineno,
                            source_column=stmt.col_offset,
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
                        source_line=stmt.lineno,
                        source_column=stmt.col_offset,
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
                steps.append(_Step("UNMODELED_STATEMENT"))
                return tuple(steps)
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
                annotation_semantics=annotation_semantics,
                assume_frozen_dataclass=assume_frozen_dataclass,
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

            if not name.isidentifier():
                return None

            value = stmt.value

            if name.startswith("__"):
                if not (
                    _depth == 0
                    and (
                        (
                            name == "__all__"
                            and _pure_all_assignment(value)
                        )
                        or (
                            name == "__version__"
                            and type(value) is ast.Constant
                            and type(value.value) is str
                        )
                    )
                ):
                    return None

            if _pure_literal_expression(value):
                steps.append(_Step("BIND", binding=name))

            elif isinstance(value, ast.Name):
                if (
                    not value.id.isidentifier()
                    or value.id.startswith("__")
                ):
                    return None

                steps.append(
                    _Step(
                        "ALIAS",
                        target=value.id,
                        binding=name,
                    )
                )

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

        elif isinstance(stmt, ast.AnnAssign):
            if not _safe_annassign(stmt, annotation_semantics):
                return None
            if stmt.value is not None:
                steps.append(_Step("BIND", binding=stmt.target.id))

        elif isinstance(stmt, ast.ClassDef):
            conditional_dataclass = (
                assume_frozen_dataclass
                and bool(stmt.decorator_list)
            )
            if not _safe_passive_class_definition(
                stmt, annotation_semantics=annotation_semantics,
                allow_conditional_frozen_dataclass=(
                    conditional_dataclass
                ),
            ):
                return None

            if stmt.bases:
                steps.append(
                    _Step(
                        "CHECK_BUILTIN_CLASS_BASE",
                        target="ValueError",
                    )
                )

            for body_statement in stmt.body:
                if isinstance(body_statement, ast.Assign):
                    steps.append(
                        _Step(
                            "BIND",
                            binding=body_statement.targets[0].id,
                            class_local=True,
                        )
                    )
                    continue

                if not isinstance(
                    body_statement,
                    (ast.Import, ast.ImportFrom),
                ):
                    if (
                        isinstance(body_statement, ast.AnnAssign)
                        and body_statement.value is not None
                    ):
                        if _exact_restricted_dataclass_hash_field_call(
                            body_statement.value
                        ):
                            steps.append(
                                _Step(
                                    "CHECK_DATACLASS_FIELD_FACTORY",
                                    target="field",
                                )
                            )

                        steps.append(
                            _Step(
                                "BIND",
                                binding=body_statement.target.id,
                                class_local=True,
                            )
                        )

                    if (
                        type(body_statement) is ast.FunctionDef
                        and len(body_statement.decorator_list) == 1
                        and type(body_statement.decorator_list[0])
                        is ast.Name
                        and body_statement.decorator_list[0].id
                        == "property"
                    ):
                        steps.append(
                            _Step(
                                "CHECK_BUILTIN_PROPERTY",
                                target="property",
                            )
                        )

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
                    assume_frozen_dataclass=assume_frozen_dataclass,
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

            if conditional_dataclass:
                steps.append(
                    _Step(
                        "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
                        binding=stmt.name,
                        source_line=stmt.decorator_list[0].lineno,
                        source_column=stmt.decorator_list[0].col_offset,
                        annotation_builtin_names=tuple(sorted({
                            node.id
                            for field in stmt.body
                            if isinstance(field, ast.AnnAssign)
                            for node in ast.walk(field.annotation)
                            if isinstance(node, ast.Name)
                        })),
                    )
                )
            else:
                steps.append(
                    _Step(
                        "DEFINE_PASSIVE_CLASS",
                        binding=stmt.name,
                    )
                )

        elif isinstance(stmt, ast.FunctionDef):
            if not _safe_passive_function_definition(
                stmt, annotation_semantics=annotation_semantics,
            ):
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
                        assume_frozen_dataclass=assume_frozen_dataclass,
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

        elif isinstance(stmt, ast.AsyncFunctionDef):
            if not _safe_passive_function_definition(
                stmt,
                annotation_semantics=annotation_semantics,
            ):
                return None

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


def _compile_reachable_prefix(
    tree: ast.Module,
    logical: str,
    package: bool,
    *,
    typing_guard: RecognizedTypingGuard | None,
    annotation_semantics: str | None,
    assume_frozen_dataclass: bool = False,
) -> tuple[_Step, ...] | None:
    """Preserve modeled effects before the first unsupported statement.

    This helper is used only for a module actually entered by
    the opt-in import-order simulator.

    The caller must already have validated the complete
    original AST with CPython compile(), without execution.

    An unsupported statement is an unavoidable UNKNOWN
    boundary, never an instruction that may be skipped.
    """

    complete = _compile(
        tree,
        logical,
        package,
        typing_guard=typing_guard,
        annotation_semantics=annotation_semantics,
        assume_frozen_dataclass=assume_frozen_dataclass,
    )

    if complete is not None:
        return complete

    if not tree.body:
        return None

    def compile_prefix(
        count: int,
    ) -> tuple[_Step, ...] | None:
        return _compile(
            ast.Module(
                body=tree.body[:count],
                type_ignores=[],
            ),
            logical,
            package,
            typing_guard=typing_guard,
            annotation_semantics=annotation_semantics,
            assume_frozen_dataclass=assume_frozen_dataclass,
        )

    # The existing restricted compiler processes top-level
    # statements in order and aborts on its first refusal.
    # Prefix support is monotonic for the same full-tree
    # typing guard and annotation semantics.

    low = 0
    high = len(tree.body)

    while low + 1 < high:
        middle = (low + high) // 2

        if compile_prefix(middle) is None:
            high = middle
        else:
            low = middle

    accepted = compile_prefix(low)

    if (
        accepted is None
        or compile_prefix(high) is not None
    ):
        return None

    return accepted + (
        _Step("UNMODELED_STATEMENT"),
    )


def evaluate_package_import_order(
    indexed_sources: Mapping[str, ast.AST],
    entry_module: str,
    *,
    _session: _PackageSourceSession | None = None,
    annotation_semantics: str | None = None,
    _compile_on_first_import: bool = False,
    _assume_passive_external_imports: bool = False,
    _assume_frozen_dataclass_decoration: bool = False,
) -> PackageImportAssessment:
    """Simulate a restricted closed regular-package source set.

    Indexed package __init__ IDs are translated to logical package names.
    The operation budget prevents unbounded model execution.

    Results cannot certify general Python import safety.
    """
    events: list[PackageModelEvent] = []
    assumed_external_imports: list[ReachedUnmodeledImport] = []
    assumed_dataclass_decorations: list[
        AssumedFrozenDataclassDecoration
    ] = []

    def result(
        outcome: str,
        target: str | None = None,
        symbol: str | None = None,
        *,
        reached_unmodeled_import: (
            ReachedUnmodeledImport | None
        ) = None,
    ) -> PackageImportAssessment:
        return PackageImportAssessment(
            entry_module,
            outcome,
            target,
            symbol,
            tuple(events),
            evidence_scope=(
                "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
                "ASSUMPTIONS_NOT_RUNTIME_PROOF"
                if _assume_frozen_dataclass_decoration is True
                else "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
                "ASSUMPTION_NOT_RUNTIME_PROOF"
                if _assume_passive_external_imports is True
                else "RESTRICTED_REGULAR_PACKAGE_MODEL"
            ),
            reached_unmodeled_import=reached_unmodeled_import,
            assumed_external_imports=tuple(
                assumed_external_imports
            ),
            assumed_dataclass_decorations=tuple(
                assumed_dataclass_decorations
            ),
        )

    if (
        not isinstance(indexed_sources, Mapping)
        or not isinstance(entry_module, str)
        or annotation_semantics not in {
            None, "STOCK_EAGER", "STRINGIFIED", "DEFERRED",
        }
        or type(_compile_on_first_import) is not bool
        or type(_assume_passive_external_imports) is not bool
        or type(_assume_frozen_dataclass_decoration) is not bool
        or (
            _assume_frozen_dataclass_decoration
            and (
                not _compile_on_first_import
                or not _assume_passive_external_imports
            )
        )
        or (
            _assume_passive_external_imports
            and not _compile_on_first_import
        )
        or (
            _compile_on_first_import
            and _session is not None
        )
    ):
        return result("UNKNOWN")

    if any(
        not isinstance(name, str)
        or not isinstance(tree, ast.Module)
        for name, tree in indexed_sources.items()
    ):
        return result("UNKNOWN")

    if any(
        getattr(node, "is_lazy", False)
        for tree in indexed_sources.values()
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
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
    pending_programs: set[str] = set()

    for name, tree in logical_sources.items():
        if not valid_chain(name):
            return result("UNKNOWN", name)

        indexed_id = nodes[name].indexed_module_ids[0]
        has_future_annotations = any(
            isinstance(statement, ast.ImportFrom)
            and statement.module == "__future__"
            and any(alias.name == "annotations" for alias in statement.names)
            for statement in tree.body
        )
        if annotation_semantics == "STRINGIFIED" and not has_future_annotations:
            return result("UNKNOWN", name)
        if _compile_on_first_import:
            programs[name] = []
            pending_programs.add(name)
            continue
        typing_guard = recognize_typing_guard(
            indexed_sources[indexed_id],
            frozenset(indexed_sources),
        )
        if (
            _session is not None
            and annotation_semantics is None
            and name in _session.compiled_steps
        ):
            program = _session.compiled_steps[name]
        else:
            program = _compile(
                tree,
                name,
                name in packages,
                typing_guard=typing_guard,
                annotation_semantics=(
                    "STRINGIFIED" if has_future_annotations
                    else annotation_semantics
                ),
            )
            if (
                program is not None
                and _session is not None
                and annotation_semantics is None
            ):
                _session.compiled_steps[name] = program

        if program is None:
            return result("UNKNOWN", name)

        # The interpreter can splice function body steps into
        # programs[module]. Never execute a cached list directly.
        programs[name] = list(program)

    # A package may prebind a same-named attribute before a later
    # from-import; the attribute takes priority. Keep more complex
    # package-owned import/rebinding sequences indeterminate.
    for package in (
        packages if not _compile_on_first_import else ()
    ):
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
                "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
            }
            and step.binding in children
            for step in programs[package]
        ):
            return result("UNKNOWN", package)

        writes_child = any(
            step.binding in children
            and (
                step.op in {"BIND", "ALIAS"}
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
    indexed_roots = frozenset(
        name.split(".", 1)[0]
        for name in programs
    )

    while frames:
        step_budget -= 1

        if step_budget < 0:
            return result("UNKNOWN")

        module, index = frames[-1]

        if module in pending_programs:
            tree = logical_sources[module]
            indexed_id = nodes[module].indexed_module_ids[0]

            has_future_annotations = any(
                isinstance(statement, ast.ImportFrom)
                and statement.module == "__future__"
                and any(
                    alias.name == "annotations"
                    for alias in statement.names
                )
                for statement in tree.body
            )

            typing_guard = recognize_typing_guard(
                indexed_sources[indexed_id],
                frozenset(indexed_sources),
            )

            program = _compile_reachable_prefix(
                tree,
                module,
                module in packages,
                typing_guard=typing_guard,
                annotation_semantics=(
                    "STRINGIFIED"
                    if has_future_annotations
                    else annotation_semantics
                ),
                assume_frozen_dataclass=(
                    _assume_frozen_dataclass_decoration
                ),
            )

            if program is None:
                return result("UNKNOWN", module)

            if module in packages:
                children = {
                    name.rsplit(".", 1)[1]
                    for name in programs
                    if (
                        "." in name
                        and name.rsplit(".", 1)[0] == module
                    )
                }

                if any(
                    step.op in {
                        "DEFINE_FUNCTION",
                        "DEFINE_OPAQUE_FUNCTION",
                        "DEFINE_PASSIVE_CLASS",
                        "DEFINE_CONDITIONAL_FROZEN_DATACLASS",
                    }
                    and step.binding in children
                    for step in program
                ):
                    return result("UNKNOWN", module)

                writes_child = any(
                    step.binding in children
                    and (
                        step.op in {"BIND", "ALIAS"}
                        or (
                            step.op == "FROM"
                            and step.target != module
                        )
                    )
                    for step in program
                )

                if writes_child and any(
                    step.op in {
                        "IMPORT",
                        "FROM",
                        "CALL_FUNCTION",
                    }
                    for step in program
                ):
                    return result("UNKNOWN", module)

            programs[module] = list(program)
            pending_programs.remove(module)

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

        if step.op in {
            "IMPORT",
            "FROM",
            "PREPARE_FROM_MEMBER",
        }:
            target = step.target

            if not target or target not in programs:
                if (
                    _assume_passive_external_imports
                    and target
                    and target not in programs
                    and module != bootstrap
                    and target.split(".", 1)[0]
                    not in indexed_roots
                ):
                    assumed_external_imports.append(
                        ReachedUnmodeledImport(
                            importer=module,
                            operation=step.op,
                            target=target,
                            symbol=step.symbol,
                            line=step.source_line,
                            column=step.source_column,
                        )
                    )
                    events.append(
                        PackageModelEvent(
                            module,
                            "ASSUMED_EXTERNAL_IMPORT",
                            target,
                            step.symbol,
                        )
                    )
                    if (
                        step.op in {"IMPORT", "FROM"}
                        and not step.function_local
                        and not step.class_local
                    ):
                        namespaces[module][step.binding] = (
                            "\x00ASSUMED_EXTERNAL:"
                            + target
                            + (
                                ":" + step.symbol
                                if step.op == "FROM"
                                else ""
                            )
                        )
                    frames[-1] = (module, index + 1)
                    continue
                blocker = (
                    ReachedUnmodeledImport(
                        importer=module,
                        operation=step.op,
                        target=target,
                        symbol=step.symbol,
                        line=step.source_line,
                        column=step.source_column,
                    )
                    if target and module != bootstrap
                    else None
                )
                return result(
                    "UNKNOWN",
                    target,
                    reached_unmodeled_import=blocker,
                )

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

        elif step.op == "CHECK_DATACLASS_FIELD_FACTORY":
            if (
                step.target != "field"
                or namespaces[module].get("field")
                != "\x00ASSUMED_EXTERNAL:dataclasses:field"
            ):
                return result(
                    "UNKNOWN",
                    module,
                    step.target,
                )

        elif step.op == "CHECK_BUILTIN_PROPERTY":
            if (
                step.target != "property"
                or "property" in namespaces[module]
            ):
                return result(
                    "UNKNOWN",
                    module,
                    step.target,
                )

        elif step.op == "DEFINE_CONDITIONAL_FROZEN_DATACLASS":
            if (
                namespaces[module].get("dataclass")
                != "\x00ASSUMED_EXTERNAL:dataclasses:dataclass"
                or any(
                    (
                        namespaces[module].get(name)
                        != "\x00ASSUMED_EXTERNAL:ast"
                        if name == "ast"
                        else (
                            name in namespaces[module]
                            if name in {
                                "str",
                                "int",
                                "bool",
                                "float",
                                "bytes",
                                "dict",
                                "list",
                                "set",
                                "tuple",
                            }
                            else not (
                                type(namespaces[module].get(name))
                                is str
                                and namespaces[module][name].startswith(
                                    "\x00PASSIVE_CLASS:"
                                )
                            )
                        )
                    )
                    for name in step.annotation_builtin_names
                )
            ):
                return result("UNKNOWN", module, step.binding)

            assumed_dataclass_decorations.append(
                AssumedFrozenDataclassDecoration(
                    module=module,
                    class_name=step.binding,
                    decorator="dataclasses.dataclass(frozen=True)",
                    line=step.source_line,
                    column=step.source_column,
                )
            )
            namespaces[module][step.binding] = (
                "\x00PASSIVE_CLASS:"
                + module
                + ":"
                + step.binding
            )
            events.append(
                PackageModelEvent(
                    module,
                    "ASSUMED_FROZEN_DATACLASS_DECORATION",
                    symbol=step.binding,
                )
            )
            events.append(
                PackageModelEvent(
                    module,
                    "DEFINE_PASSIVE_CLASS",
                    symbol=step.binding,
                )
            )

        elif step.op == "CHECK_BUILTIN_CLASS_BASE":
            if (
                step.target != "ValueError"
                or "ValueError" in namespaces[module]
            ):
                return result(
                    "UNKNOWN",
                    module,
                    step.target,
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
            if not step.class_local:
                namespaces[module][step.binding] = None

            events.append(
                PackageModelEvent(
                    module,
                    "CLASS_LOCAL_BIND" if step.class_local else "BIND",
                    symbol=step.binding,
                )
            )

        elif step.op == "ALIAS":
            if (
                not step.target
                or not step.binding
                or step.target not in namespaces[module]
            ):
                return result(
                    "UNKNOWN",
                    module,
                    step.target,
                )

            namespaces[module][step.binding] = (
                namespaces[module][step.target]
            )

            events.append(
                PackageModelEvent(
                    module,
                    "ALIAS",
                    target=step.target,
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

        elif step.op == "UNMODELED_STATEMENT":
            return result("UNKNOWN", module)

        else:
            return result("UNKNOWN")

        frames[-1] = (module, index + 1)

    return result("MODEL_PASS")


@dataclass(frozen=True)
class ConditionalNamespaceModelAssessment:
    entry_module: str
    outcome: str
    reason: str | None
    model_assessment: PackageImportAssessment | None
    namespace_parents: tuple[str, ...]
    authority: str = (
        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_"
        "NOT_RUNTIME_OR_LIVE_PROOF"
    )
    target_python_version: tuple[int, int] | None = None
    external_import_policy: str = "STOP_AT_UNMODELED"
    class_decorator_policy: str = "STOP_AT_UNMODELED"


def _conditional_annotation_mode_for_target(
    target_python_version: tuple[int, int] | None,
) -> tuple[str | None, str | None]:
    """Select documented CPython annotation semantics.

    The explicit target version must match the interpreter
    executing this restricted model. This does not prove the
    interpreter used by an analyzed application.
    """

    if target_python_version is None:
        return None, None

    if (
        type(target_python_version) is not tuple
        or len(target_python_version) != 2
        or any(
            type(part) is not int
            for part in target_python_version
        )
    ):
        return None, "INVALID_TARGET_PYTHON_VERSION"

    if target_python_version not in {
        (3, 10),
        (3, 11),
        (3, 12),
        (3, 13),
        (3, 14),
        (3, 15),
    }:
        return None, "UNSUPPORTED_TARGET_PYTHON_VERSION"

    if (
        sys.implementation.name != "cpython"
        or target_python_version != (
            sys.version_info.major,
            sys.version_info.minor,
        )
    ):
        return None, "TARGET_INTERPRETER_UNVERIFIED"

    if target_python_version >= (3, 14):
        return "DEFERRED", None

    return "STOCK_EAGER", None


def _conditional_reachable_source_cohort(
    indexed_sources: Mapping[str, ast.AST],
    entry_module: str,
    namespace_parents: tuple[str, ...],
) -> dict[str, ast.AST] | None:
    """Over-approximate physical sources possibly loaded by an entry.

    Examine every lexical import, including imports in deferred
    or guarded scopes. Include regular parent initializers and
    optional from-import child modules.

    This may include sources never executed. It must never
    infer execution safety from an omitted source.

    The caller must validate the FULL source inventory and
    namespace path layout before invoking this function.
    """

    physical_by_logical: dict[str, str] = {}

    for indexed_id in indexed_sources:
        logical = (
            indexed_id.removesuffix(".__init__")
            if indexed_id.endswith(".__init__")
            else indexed_id
        )

        if logical in physical_by_logical:
            return None

        physical_by_logical[logical] = indexed_id

    known_namespaces = frozenset(namespace_parents)

    if (
        entry_module not in physical_by_logical
        and entry_module not in known_namespaces
    ):
        return None

    pending = [entry_module]
    visited: set[str] = set()
    selected: dict[str, ast.AST] = {}

    while pending:
        logical = pending.pop()

        if logical in visited:
            continue

        visited.add(logical)

        parts = logical.split(".")

        for length in range(1, len(parts)):
            parent = ".".join(parts[:length])

            if parent in physical_by_logical:
                pending.append(parent)

        indexed_id = physical_by_logical.get(logical)

        if indexed_id is None:
            continue

        tree = indexed_sources[indexed_id]
        selected[indexed_id] = tree

        is_package = indexed_id.endswith(".__init__")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    requested = alias.name

                    if (
                        requested in physical_by_logical
                        or requested in known_namespaces
                    ):
                        pending.append(requested)

            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    base = node.module
                else:
                    context = (
                        logical.split(".")
                        if is_package
                        else logical.split(".")[:-1]
                    )

                    climb = node.level - 1

                    if (
                        not context
                        or climb >= len(context)
                    ):
                        continue

                    components = context[
                        :len(context) - climb
                    ]

                    if node.module:
                        components.extend(
                            node.module.split(".")
                        )

                    base = ".".join(components)

                if (
                    not base
                    or not all(
                        part.isidentifier()
                        for part in base.split(".")
                    )
                ):
                    continue

                if (
                    base in physical_by_logical
                    or base in known_namespaces
                ):
                    pending.append(base)

                for alias in node.names:
                    if (
                        alias.name == "*"
                        or not alias.name.isidentifier()
                    ):
                        continue

                    child = base + "." + alias.name

                    if (
                        child in physical_by_logical
                        or child in known_namespaces
                    ):
                        pending.append(child)

    return selected


def evaluate_conditional_namespace_import_order(
    indexed_sources: Mapping[str, ast.AST],
    entry_module: str,
    portions: tuple[SearchPortion, ...],
    *,
    target_python_version: tuple[int, int] | None = None,
    assume_passive_external_imports: bool = False,
    assume_frozen_dataclass_decoration: bool = False,
) -> ConditionalNamespaceModelAssessment:
    """Evaluate a supplied closed PEP 420 inventory conditionally.

    This assumes standard finder behavior for the supplied ordered
    inventory. It does not authenticate actual runtime import state,
    sys.path, sys.modules, custom finders, external portions,
    source bytes or canonical LIVE freshness.

    Namespace parents are represented by an empty initialization
    program only within this private conditional evaluation.
    No synthetic source is written or indexed.

    The result is never eligible for MODEL_PASS warning suppression.
    """

    annotation_mode, version_error = (
        _conditional_annotation_mode_for_target(
            target_python_version
        )
    )
    external_import_policy = (
        "ASSUME_PASSIVE_EXTERNAL_SUCCESS"
        if assume_passive_external_imports is True
        else "STOP_AT_UNMODELED"
    )
    class_decorator_policy = (
        "ASSUME_PASSIVE_FROZEN_DATACLASS"
        if assume_frozen_dataclass_decoration is True
        else "STOP_AT_UNMODELED"
    )

    def reject(
        reason: str,
        parents: tuple[str, ...] = (),
    ) -> ConditionalNamespaceModelAssessment:
        return ConditionalNamespaceModelAssessment(
            entry_module=entry_module,
            outcome="UNKNOWN",
            reason=reason,
            model_assessment=None,
            namespace_parents=parents,
            target_python_version=(
                target_python_version
                if version_error is None
                else None
            ),
            external_import_policy=external_import_policy,
            class_decorator_policy=class_decorator_policy,
        )

    if type(assume_frozen_dataclass_decoration) is not bool:
        return reject("INVALID_DATACLASS_DECORATOR_ASSUMPTION")
    if (
        assume_frozen_dataclass_decoration
        and not assume_passive_external_imports
    ):
        return reject("DATACLASS_ASSUMPTION_REQUIRES_EXTERNAL_POLICY")

    if type(assume_passive_external_imports) is not bool:
        return reject("INVALID_EXTERNAL_IMPORT_ASSUMPTION")

    if version_error is not None:
        return reject(version_error)

    if (
        not isinstance(indexed_sources, Mapping)
        or type(entry_module) is not str
        or not entry_module
        or type(portions) is not tuple
        or not portions
        or any(
            type(portion) is not SearchPortion
            or type(portion.files) is not frozenset
            or any(
                type(filename) is not str
                for filename in portion.files
            )
            for portion in portions
        )
    ):
        return reject("INVALID_CONDITIONAL_INPUT")

    if (
        not indexed_sources
        or any(
            type(module_id) is not str
            or not isinstance(tree, ast.Module)
            for module_id, tree in indexed_sources.items()
        )
    ):
        return reject("INVALID_CONDITIONAL_SOURCE_COHORT")

    try:
        layout = build_package_layout(indexed_sources)
    except (TypeError, ValueError):
        return reject("INVALID_CONDITIONAL_LAYOUT")

    nodes = {
        node.name: node
        for node in layout.nodes
    }

    namespace_parents = tuple(sorted(
        node.name
        for node in layout.nodes
        if node.kind == "NAMESPACE_CANDIDATE"
    ))

    if not namespace_parents:
        return reject("NO_NAMESPACE_PARENT")

    if any(
        node.kind not in {
            "REGULAR_PACKAGE",
            "MODULE_FILE",
            "NAMESPACE_CANDIDATE",
        }
        for node in layout.nodes
    ):
        return reject(
            "AMBIGUOUS_CONDITIONAL_LAYOUT",
            namespace_parents,
        )

    expected_files = tuple(sorted(
        module_id.replace(".", "/") + ".py"
        for module_id in indexed_sources
    ))

    inventory_files = tuple(sorted(
        filename
        for portion in portions
        for filename in portion.files
        if filename.endswith(".py")
    ))

    if inventory_files != expected_files:
        return reject(
            "INVENTORY_SOURCE_DOMAIN_MISMATCH",
            namespace_parents,
        )

    for node in layout.nodes:
        resolution = resolve_namespace_path(
            portions,
            node.name,
            standard_finder_assumed=True,
        )

        if resolution.status != "CONDITIONAL":
            return reject(
                "CONDITIONAL_PATH_UNRESOLVED:" + node.name,
                namespace_parents,
            )

        if node.kind == "NAMESPACE_CANDIDATE":
            if (
                resolution.kind != "NAMESPACE_PACKAGE"
                or resolution.source is not None
                or not resolution.portions
            ):
                return reject(
                    "NAMESPACE_PATH_KIND_MISMATCH:" + node.name,
                    namespace_parents,
                )
            continue

        if (
            len(node.indexed_module_ids) != 1
            or resolution.kind != node.kind
        ):
            return reject(
                "CONDITIONAL_SOURCE_KIND_MISMATCH:" + node.name,
                namespace_parents,
            )

        expected_path = (
            node.indexed_module_ids[0].replace(".", "/")
            + ".py"
        )

        selected_candidates = {
            portion.root_id + ":" + expected_path
            for portion in portions
            if expected_path in portion.files
        }

        if resolution.source not in selected_candidates:
            return reject(
                "CONDITIONAL_SOURCE_PATH_MISMATCH:" + node.name,
                namespace_parents,
            )

    # An implicit namespace has no executable __init__.py.
    # Do not let a synthetic model-only initializer become
    # an explicitly importable source module.
    synthetic_ids = {
        name + ".__init__"
        for name in namespace_parents
    }

    for tree in indexed_sources.values():
        for statement in ast.walk(tree):
            if isinstance(statement, ast.Import):
                if any(
                    alias.name in synthetic_ids
                    for alias in statement.names
                ):
                    return reject(
                        "SYNTHETIC_INITIALIZER_REFERENCE",
                        namespace_parents,
                    )

            elif isinstance(statement, ast.ImportFrom):
                if (
                    statement.level == 0
                    and statement.module in namespace_parents
                    and any(
                        alias.name == "__init__"
                        for alias in statement.names
                    )
                ):
                    return reject(
                        "SYNTHETIC_INITIALIZER_REFERENCE",
                        namespace_parents,
                    )

    selected = _conditional_reachable_source_cohort(
        indexed_sources,
        entry_module,
        namespace_parents,
    )

    if selected is None:
        return reject(
            "CONDITIONAL_SOURCE_COHORT_UNRESOLVED",
            namespace_parents,
        )

    augmented = dict(selected)

    needed_names: set[str] = {entry_module}

    for indexed_id in selected:
        logical = (
            indexed_id.removesuffix(".__init__")
            if indexed_id.endswith(".__init__")
            else indexed_id
        )

        parts = logical.split(".")

        for length in range(1, len(parts) + 1):
            needed_names.add(
                ".".join(parts[:length])
            )

    for parent in namespace_parents:
        if parent in needed_names:
            augmented[parent + ".__init__"] = (
                ast.Module(
                    body=[],
                    type_ignores=[],
                )
            )

    # Reuse the existing import-order simulator.
    # Its internal observations remain model-relative.
    # Never change or promote its execution outcomes.
    model = evaluate_package_import_order(
        augmented,
        entry_module,
        annotation_semantics=annotation_mode,
        _compile_on_first_import=True,
        _assume_passive_external_imports=(
            assume_passive_external_imports
        ),
        _assume_frozen_dataclass_decoration=(
            assume_frozen_dataclass_decoration
        ),
    )

    conditional_outcomes = {
        "MODEL_PASS": "CONDITIONAL_MODEL_PASS",
        "EARLY_BINDING_HAZARD":
            "CONDITIONAL_EARLY_BINDING_HAZARD",
        "MISSING_EXPORT": "CONDITIONAL_MISSING_EXPORT",
        "MISSING_ATTRIBUTE": "CONDITIONAL_MISSING_ATTRIBUTE",
    }

    outcome = conditional_outcomes.get(
        model.outcome,
        "UNKNOWN",
    )

    return ConditionalNamespaceModelAssessment(
        entry_module=entry_module,
        outcome=outcome,
        reason=(
            None
            if outcome != "UNKNOWN"
            else "RESTRICTED_MODEL_UNKNOWN"
        ),
        model_assessment=model,
        namespace_parents=namespace_parents,
        target_python_version=target_python_version,
        external_import_policy=external_import_policy,
        class_decorator_policy=class_decorator_policy,
    )
