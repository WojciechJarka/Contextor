"""Restricted package-aware recursive import initialization evidence.

Only regular, indexed Python packages and simple import/constant/attribute AST.
Never executes analyzed code or certifies general runtime safety.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from contextor.core.cycle_semantics.model_environment import (
    STANDARD_BUILTINS_PRECONDITION,
)
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
from .execution.steps import _Step
from .execution.expressions import (
    _bounded_integer_arithmetic,
    _pure_literal_expression,
    _safe_annassign,
)
from .execution.definition_checks import (
    _exact_frozen_dataclass_decorator,
    _exact_restricted_dataclass_hash_field_call,
    _restricted_dataclass_field_annotation,
)
from .execution.class_facts import (
    _ClassFact,
    _BUILTIN_TYPE_ID,
    _BUILTIN_CLASS_FACTS,
    _BUILTIN_EXCEPTION_CLASS_IDENTITIES,
    _merge_class_mros,
)
from .execution.state import (
    _new_module_initialization_state,
    _new_execution_cursor,
    _new_definition_state,
    _FunctionFrame,
    _frame_position,
    _advance_frame,
)
from .execution.imports import (
    _missing_piece,
    _execute_ready_import,
    _execute_prepare_from_member,
    _resolve_from_child,
    _execute_from_binding,
    _classify_external_import,
)
from .execution.lifecycle import (
    _complete_module_frame,
    _start_module_frame,
)
from .execution.calls import (
    _execute_restricted_call,
    _new_restricted_function,
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


def _safe_class_namespace_value(value: object) -> bool:
    """Values admitted in a passive class namespace cannot be descriptors."""
    if isinstance(value, _ClassFact) or value is None:
        return True
    if type(value) is str:
        return not value.startswith("\x00ASSUMED_EXTERNAL:")
    return False


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

    @property
    def builtin_environment_precondition(self) -> str:
        return STANDARD_BUILTINS_PRECONDITION


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

    explicit_named_metaclass = (
        len(statement.keywords) == 1
        and statement.keywords[0].arg == "metaclass"
        and type(statement.keywords[0].value) is ast.Name
    )

    if (
        not statement.name.isidentifier()
        or statement.name.startswith("__")
        or any(
            isinstance(
                item,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
            and item.name in {
                "__slots__",
                "__qualname__",
                "__classcell__",
            }
            for item in statement.body
        )
        or (
            bool(statement.bases)
            and (
                conditional_dataclass
                or any(
                    type(base) is not ast.Name
                    for base in statement.bases
                )
            )
        )
        or (bool(statement.keywords) and not explicit_named_metaclass)
        or (conditional_dataclass and statement.keywords)
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
            passive_metaclass_body = all(
                type(item) is ast.Pass
                or (
                    index == 0
                    and type(item) is ast.Expr
                    and type(item.value) is ast.Constant
                    and type(item.value.value) is str
                )
                for index, item in enumerate(stmt.body)
            )
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

            if not conditional_dataclass:
                if (
                    type(stmt.lineno) is not int
                    or stmt.lineno < 1
                    or type(stmt.col_offset) is not int
                    or stmt.col_offset < 0
                ):
                    return None

                definition_id = (
                    f"{logical}:{stmt.lineno}:{stmt.col_offset}"
                )
                steps.append(
                    _Step(
                        "PREPARE_PASSIVE_CLASS",
                        target=(
                            stmt.bases[0].id if stmt.bases else None
                        ),
                        base_names=tuple(
                            base.id
                            for base in stmt.bases
                        ),
                        binding=stmt.name,
                        source_line=stmt.lineno,
                        source_column=stmt.col_offset,
                        definition_id=definition_id,
                        explicit_metaclass_name=(
                            stmt.keywords[0].value.id
                            if stmt.keywords else None
                        ),
                        passive_metaclass_body=passive_metaclass_body,
                    )
                )

            has_init_subclass = any(
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == "__init_subclass__"
                for item in stmt.body
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
                        source_line=stmt.lineno,
                        source_column=stmt.col_offset,
                        definition_id=(
                            f"{logical}:{stmt.lineno}:{stmt.col_offset}"
                        ),
                        defines_init_subclass=has_init_subclass,
                        passive_metaclass_body=passive_metaclass_body,
                    )
                )

        elif isinstance(stmt, ast.FunctionDef):
            if not _safe_passive_function_definition(
                stmt, annotation_semantics=annotation_semantics,
            ):
                return None

            args = stmt.args

            restricted_callable = (
                not args.posonlyargs
                and len(args.args) <= 1
                and args.vararg is None
                and not args.kwonlyargs
                and args.kwarg is None
                and not args.defaults
                and not args.kw_defaults
            )

            function_steps: list[_Step] = []

            if restricted_callable:
                for body_statement in stmt.body:
                    if isinstance(body_statement, ast.Pass):
                        continue

                    if (
                        isinstance(body_statement, ast.Return)
                        and body_statement.value is None
                    ):
                        function_steps.append(
                            _Step("RETURN_FUNCTION")
                        )
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
                        parameters=tuple(
                            parameter.arg
                            for parameter in args.args
                        ),
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
                or len(expression.args) > 1
                or expression.keywords
                or any(
                    not isinstance(argument, ast.Constant)
                    or type(argument.value)
                    not in (type(None), bool, int, str)
                    for argument in expression.args
                )
            ):
                return None

            steps.append(
                _Step(
                    "CALL_FUNCTION",
                    target=expression.func.id,
                    call_argument_values=tuple(
                        argument.value
                        for argument in expression.args
                    ),
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

    statement = tree.body[low]
    location = (
        statement.decorator_list[0]
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef))
        and statement.decorator_list
        else statement
    )
    line = getattr(location, "lineno", None)
    column = getattr(location, "col_offset", None)

    return accepted + (
        _Step(
            "UNMODELED_STATEMENT",
            target=type(statement).__name__,
            source_line=line if type(line) is int and line >= 1 else None,
            source_column=(
                column if type(column) is int and column >= 0 else None
            ),
        ),
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

    MODEL_PASS assesses the restricted model assuming conventional builtin
    bindings. The evaluator does not attest the actual contents of
    __builtins__, builtins, or the import environment, and cannot certify
    general Python import safety.
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

    module_initialization_state = (
        _new_module_initialization_state(programs)
    )
    states = module_initialization_state.states
    namespaces = module_initialization_state.namespaces
    definition_state = _new_definition_state()
    prepared_class_bases = definition_state.prepared_class_bases
    class_facts_by_identity = definition_state.class_facts_by_identity

    bootstrap = "\x00ENTRY"
    execution_cursor = _new_execution_cursor(bootstrap)
    frames = execution_cursor.frames

    indexed_roots = frozenset(
        name.split(".", 1)[0]
        for name in programs
    )

    while frames:
        execution_cursor.step_budget -= 1

        if execution_cursor.step_budget < 0:
            return result("UNKNOWN")

        active_frame = frames[-1]
        module, index = _frame_position(active_frame)

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
            active_frame.steps
            if isinstance(active_frame, _FunctionFrame)
            else (
                (_Step("IMPORT", entry_module, binding=None),)
                if module == bootstrap
                else programs[module]
            )
        )

        if index >= len(steps):
            if isinstance(active_frame, _FunctionFrame):
                frames.pop()
                execution_cursor.step_budget += 1
            else:
                _complete_module_frame(
                    module,
                    bootstrap=bootstrap,
                    frames=frames,
                    states=states,
                    namespaces=namespaces,
                    emit_event=lambda event_module, operation, target, symbol: (
                        events.append(
                            PackageModelEvent(
                                event_module,
                                operation,
                                target,
                                symbol,
                            )
                        )
                    ),
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
                external_decision = _classify_external_import(
                    step,
                    module=module,
                    bootstrap=bootstrap,
                    programs=programs,
                    indexed_roots=indexed_roots,
                    assume_passive_external_imports=(
                        _assume_passive_external_imports
                    ),
                )

                if external_decision == "UNKNOWN_CLASS_LOCAL":
                    return result("UNKNOWN", module, target)

                if external_decision == "ASSUME":
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
                    frames[-1] = _advance_frame(frames[-1])
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

            next_piece = _missing_piece(target, states)

            if next_piece:
                if next_piece not in programs:
                    return result("UNKNOWN", next_piece)

                _start_module_frame(
                    next_piece,
                    importer=module,
                    frames=frames,
                    states=states,
                    emit_event=lambda event_module, operation, target, symbol: (
                        events.append(
                            PackageModelEvent(
                                event_module,
                                operation,
                                target,
                                symbol,
                            )
                        )
                    ),
                )
                continue

            if step.op == "PREPARE_FROM_MEMBER":
                prepare_control = _execute_prepare_from_member(
                    step,
                    packages=packages,
                    programs=programs,
                    states=states,
                    namespaces=namespaces,
                    frames=frames,
                )

                if prepare_control.action == "RETURN_UNKNOWN":
                    return result(
                        "UNKNOWN",
                        prepare_control.target,
                        prepare_control.symbol,
                    )

                if prepare_control.action == "START_CHILD":
                    child = prepare_control.target
                    _start_module_frame(
                        child,
                        importer=module,
                        frames=frames,
                        states=states,
                        emit_event=lambda event_module, operation, target, symbol: (
                            events.append(
                                PackageModelEvent(
                                    event_module,
                                    operation,
                                    target,
                                    symbol,
                                )
                            )
                        ),
                    )
                    continue

                events.append(
                    PackageModelEvent(
                        module,
                        "PREPARE_FROM_MEMBER",
                        target,
                        step.symbol,
                    )
                )

            elif step.op == "IMPORT":
                import_control = _execute_ready_import(
                    step,
                    module=module,
                    bootstrap=bootstrap,
                    namespaces=namespaces,
                )

                if import_control.action == "RETURN_UNKNOWN":
                    return result(
                        "UNKNOWN",
                        import_control.target,
                        import_control.symbol,
                    )

                if import_control.event_operation is not None:
                    events.append(
                        PackageModelEvent(
                            module,
                            import_control.event_operation,
                            target,
                            step.binding,
                        )
                    )

            else:
                member = step.symbol

                # CPython checks a package attribute before attempting
                # to load a same-named child module. An existing binding
                # takes precedence over the indexed child candidate.
                from_child_control = _resolve_from_child(
                    step,
                    packages=packages,
                    programs=programs,
                    states=states,
                    namespaces=namespaces,
                    frames=frames,
                )

                if from_child_control.action == "RETURN_UNKNOWN":
                    return result(
                        "UNKNOWN",
                        from_child_control.target,
                        from_child_control.symbol,
                    )

                if from_child_control.action == "REENTRANT_CHILD":
                    child = from_child_control.target

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

                    frames[-1] = _advance_frame(frames[-1])
                    continue

                if from_child_control.action == "START_CHILD":
                    child = from_child_control.target
                    _start_module_frame(
                        child,
                        importer=module,
                        frames=frames,
                        states=states,
                        emit_event=lambda event_module, operation, target, symbol: (
                            events.append(
                                PackageModelEvent(
                                    event_module,
                                    operation,
                                    target,
                                    symbol,
                                )
                            )
                        ),
                    )
                    continue

                from_binding_control = _execute_from_binding(
                    step,
                    module=module,
                    states=states,
                    namespaces=namespaces,
                    class_namespace_admissible=(
                        _safe_class_namespace_value
                    ),
                )

                if from_binding_control.action == "RETURN_UNKNOWN":
                    return result(
                        "UNKNOWN",
                        from_binding_control.target,
                        from_binding_control.symbol,
                    )

                if from_binding_control.action == "RETURN_OUTCOME":
                    events.append(
                        PackageModelEvent(
                            module,
                            from_binding_control.event_operation,
                            target,
                            member,
                        )
                    )

                    return result(
                        from_binding_control.outcome,
                        from_binding_control.target,
                        from_binding_control.symbol,
                    )

                events.append(
                    PackageModelEvent(
                        module,
                        from_binding_control.event_operation,
                        target,
                        member,
                    )
                )

        elif step.op == "DEFINE_FUNCTION":
            namespaces[module][step.binding] = (
                _new_restricted_function(
                    module,
                    step.function_body,
                    step.parameters,
                )
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
                                isinstance(
                                    namespaces[module].get(name),
                                    _ClassFact,
                                )
                                or (
                                    type(namespaces[module].get(name))
                                    is str
                                    and namespaces[module][name].startswith(
                                        "\x00PASSIVE_CLASS:"
                                    )
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

        elif step.op == "PREPARE_PASSIVE_CLASS":
            if not step.binding or not step.definition_id:
                return result("UNKNOWN", module, step.binding)

            if (
                step.explicit_metaclass_name == "type"
                and "type" in namespaces[module]
            ):
                return result("UNKNOWN", module, "type")

            base_names = step.base_names or (
                (step.target,) if step.target is not None else ()
            )
            if not base_names:
                base_facts = (_BUILTIN_CLASS_FACTS["object"],)
            else:
                resolved_base_facts = []
                for base_name in base_names:
                    if base_name in namespaces[module]:
                        base_fact = namespaces[module][base_name]
                    else:
                        base_fact = _BUILTIN_CLASS_FACTS.get(base_name)

                    if (
                        not isinstance(base_fact, _ClassFact)
                        or type(base_fact.linear_mro) is not tuple
                        or not base_fact.linear_mro
                        or base_fact.linear_mro[0]
                        != base_fact.identity
                        or base_fact.linear_mro[-1]
                        != _BUILTIN_CLASS_FACTS["object"].identity
                        or any(
                            type(identity) is not str
                            for identity in base_fact.linear_mro
                        )
                        or len(set(base_fact.linear_mro))
                        != len(base_fact.linear_mro)
                    ):
                        return result(
                            "UNKNOWN",
                            module,
                            base_name,
                        )

                    resolved_base_facts.append(base_fact)

                base_facts = tuple(resolved_base_facts)

            candidate_ids = [base.metaclass_identity for base in base_facts]
            if step.explicit_metaclass_name is not None:
                name = step.explicit_metaclass_name
                explicit = (
                    namespaces[module][name]
                    if name in namespaces[module]
                    else _BUILTIN_CLASS_FACTS.get(name)
                )
                if not isinstance(explicit, _ClassFact):
                    return result("UNKNOWN", module, name)
                candidate_ids.insert(0, explicit.identity)
            if not candidate_ids:
                candidate_ids = [_BUILTIN_TYPE_ID]

            candidates = [
                class_facts_by_identity.get(identity)
                for identity in candidate_ids
            ]
            if any(not isinstance(candidate, _ClassFact) for candidate in candidates):
                return result("UNKNOWN", module, step.binding)
            winners = [
                candidate for candidate in candidates
                if all(
                    other.identity in candidate.linear_mro
                    for other in candidates
                )
            ]
            winner_ids = {candidate.identity for candidate in winners}
            if len(winner_ids) != 1:
                return result("UNKNOWN", module, step.binding)
            selected = winners[0]
            if not selected.passive_metaclass_creation:
                return result("UNKNOWN", module, step.binding)
            prepared_class_bases[step.definition_id] = (base_facts, selected)

        elif step.op == "DEFINE_PASSIVE_CLASS":
            prepared = prepared_class_bases.pop(
                step.definition_id or "",
                None,
            )
            if (
                not isinstance(prepared, tuple)
                or len(prepared) != 2
                or not isinstance(prepared[0], tuple)
                or not prepared[0]
                or not isinstance(prepared[1], _ClassFact)
                or any(
                    not isinstance(base_fact, _ClassFact)
                    for base_fact in prepared[0]
                )
            ):
                return result("UNKNOWN", module, step.binding)
            base_facts, selected_metaclass = prepared

            if len({base.identity for base in base_facts}) != len(base_facts):
                return result("UNKNOWN", module, step.binding)

            if any(not base.safe_to_subclass for base in base_facts):
                return result("UNKNOWN", module, step.binding)

            if len(base_facts) > 1 and any(
                identity in _BUILTIN_EXCEPTION_CLASS_IDENTITIES
                for base in base_facts
                for identity in base.linear_mro
            ):
                return result("UNKNOWN", module, step.binding)

            inherited_mro = _merge_class_mros(base_facts)
            if inherited_mro is None:
                return result("UNKNOWN", module, step.binding)

            identity = step.definition_id
            if not identity:
                return result("UNKNOWN", module, step.binding)

            class_fact = _ClassFact(
                identity=identity,
                origin="INDEXED_SOURCE",
                direct_bases=tuple(
                    base.identity for base in base_facts
                ),
                linear_mro=(identity, *inherited_mro),
                metaclass_identity=selected_metaclass.identity,
                defines_init_subclass=step.defines_init_subclass,
                safe_to_subclass=not step.defines_init_subclass,
                passive_metaclass_creation=(
                    len(base_facts) == 1
                    and _BUILTIN_TYPE_ID in base_facts[0].linear_mro
                    and base_facts[0].passive_metaclass_creation
                    and step.passive_metaclass_body
                ),
            )
            class_facts_by_identity[identity] = class_fact
            namespaces[module][step.binding] = (
                class_fact
            )

            events.append(
                PackageModelEvent(
                    module,
                    "DEFINE_PASSIVE_CLASS",
                    symbol=step.binding,
                )
            )

        elif step.op == "RETURN_FUNCTION":
            if not isinstance(active_frame, _FunctionFrame):
                return result("UNKNOWN", module)

            frames.pop()
            continue

        elif step.op == "CALL_FUNCTION":
            local_bindings: dict[str, object | None] = {}

            body = _execute_restricted_call(
                step,
                module=module,
                namespaces=namespaces,
                local_bindings=local_bindings,
            )

            if body is None:
                return result("UNKNOWN", module, step.target)

            events.append(
                PackageModelEvent(
                    module,
                    "CALL_FUNCTION",
                    symbol=step.target,
                )
            )

            frames[-1] = _advance_frame(frames[-1])
            frames.append(
                _FunctionFrame(
                    module,
                    0,
                    body,
                    local_bindings,
                )
            )
            continue

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
            if _compile_on_first_import:
                events.append(PackageModelEvent(
                    module,
                    "UNMODELED_STATEMENT",
                    step.target,
                    (
                        f"{step.source_line}:{step.source_column}"
                        if step.source_line is not None
                        and step.source_column is not None
                        else None
                    ),
                ))
            return result("UNKNOWN", module)

        else:
            return result("UNKNOWN")

        frames[-1] = _advance_frame(frames[-1])

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
