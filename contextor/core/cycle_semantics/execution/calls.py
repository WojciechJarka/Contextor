from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .steps import _Step


@dataclass(frozen=True, eq=False)
class _RestrictedFunction:
    defining_module: str
    body: tuple[_Step, ...]
    parameters: tuple[str, ...] = ()


@dataclass(frozen=True)
class _CallOutcomeContract:
    """Conditional semantics through class-name binding.

    Invocation must have no unmodeled side effects
    or exceptions for the admitted arguments.

    The result must have the declared exact standard
    semantics, including its later behavior during
    class creation.

    For an external import all three properties are
    caller assumptions, not runtime attestations.
    """

    invocation: str
    result: str
    lifecycle: str


@dataclass(frozen=True)
class _ClassDecoratorOutcomeContract:
    factory: _CallOutcomeContract
    application: _CallOutcomeContract
    return_identity: str


_FROZEN_DATACLASS_DECORATOR_CONTRACT = (
    _ClassDecoratorOutcomeContract(
        factory=_CallOutcomeContract(
            invocation=(
                "NO_UNMODELED_FACTORY_EFFECTS_OR_EXCEPTIONS"
            ),
            result=(
                "EXACT_STANDARD_FROZEN_DATACLASS_DECORATOR"
            ),
            lifecycle=(
                "NO_UNKNOWN_EFFECTS_BEFORE_APPLICATION"
            ),
        ),
        application=_CallOutcomeContract(
            invocation=(
                "NO_UNMODELED_DECORATION_EFFECTS_OR_EXCEPTIONS"
            ),
            result=(
                "EXACT_STANDARD_FROZEN_DATACLASS_TRANSFORMATION"
            ),
            lifecycle=(
                "NO_UNKNOWN_EFFECTS_BEFORE_CLASS_BINDING"
            ),
        ),
        return_identity="INPUT_CLASS",
    )
)


_CALL_OUTCOME_CONTRACTS = {
    "PASSIVE_PROPERTY": _CallOutcomeContract(
        invocation=(
            "NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS"
        ),
        result=(
            "EXACT_BUILTINS_PROPERTY_OF_DECORATED_FUNCTION"
        ),
        lifecycle=(
            "NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING"
        ),
    ),
    "PASSIVE_DEFAULTLESS_DATACLASS_FIELD":
        _CallOutcomeContract(
            invocation=(
                "NO_EFFECTS_OR_EXCEPTIONS_FOR_ADMITTED_ARGUMENTS"
            ),
            result=(
                "EXACT_STDLIB_FIELD_NO_DEFAULT_OR_FACTORY_"
                "PRESERVE_LITERAL_HASH_COMPARE"
            ),
            lifecycle=(
                "NO_UNKNOWN_RESULT_HOOKS_BEFORE_CLASS_BINDING"
            ),
        ),
}


@dataclass(frozen=True)
class _CallableEffectFact:
    effect: str
    provenance: str
    outcome_contract: _CallOutcomeContract
    canonical_identity: str | None = None
    import_origin: tuple[str, str] | None = None


_KNOWN_BUILTIN_CALLABLES = {
    "property": _CallableEffectFact(
        effect="PASSIVE_PROPERTY",
        provenance="CONVENTIONAL_BUILTIN",
        outcome_contract=(
            _CALL_OUTCOME_CONTRACTS["PASSIVE_PROPERTY"]
        ),
        canonical_identity="builtins.property",
    ),
}


def _known_builtin_callable(
    name: str | None,
) -> _CallableEffectFact | None:
    return _KNOWN_BUILTIN_CALLABLES.get(name)


def _resolve_known_builtin_callable(
    name: str | None,
    namespace: dict[str, object | None],
) -> _CallableEffectFact | None:
    if name is None:
        return None
    value = (
        namespace[name]
        if name in namespace
        else _known_builtin_callable(name)
    )
    return (
        value
        if type(value) is _CallableEffectFact
        else None
    )


_SUPPORTED_CALL_EFFECTS = frozenset(
    _CALL_OUTCOME_CONTRACTS
)


def _validate_external_callable_effects(
    declared: Mapping[tuple[str, str], str] | None,
) -> dict[tuple[str, str], str] | None:
    if declared is None:
        return {}

    if not isinstance(declared, Mapping):
        return None

    validated: dict[tuple[str, str], str] = {}

    for key, effect in declared.items():
        if (
            type(key) is not tuple
            or len(key) != 2
            or type(key[0]) is not str
            or type(key[1]) is not str
            or not key[0]
            or not all(
                part.isidentifier()
                for part in key[0].split(".")
            )
            or not key[1].isidentifier()
            or type(effect) is not str
            or effect not in _SUPPORTED_CALL_EFFECTS
        ):
            return None

        validated[key] = effect

    return validated


@dataclass(frozen=True, eq=False)
class _DecoratorSnapshot:
    names: tuple[str, ...]
    values: tuple[object, ...]


def _snapshot_named_decorators(
    names: tuple[str, ...],
    namespace: dict[str, object | None],
) -> _DecoratorSnapshot | None:
    if not names:
        return None

    values: list[object] = []

    for name in names:
        if (
            not name
            or not name.isidentifier()
            or name.startswith("__")
            or name not in namespace
        ):
            return None

        values.append(namespace[name])

    return _DecoratorSnapshot(
        names=names,
        values=tuple(values),
    )


def _new_restricted_function(
    defining_module: str,
    body: tuple[_Step, ...],
    parameters: tuple[str, ...] = (),
) -> _RestrictedFunction:
    return _RestrictedFunction(
        defining_module=defining_module,
        body=body,
        parameters=parameters,
    )


def _execute_restricted_call(
    step: _Step,
    *,
    module: str,
    namespaces: dict[str, dict[str, object | None]],
    local_bindings: dict[str, object | None],
) -> tuple[_Step, ...] | None:
    value = namespaces[module].get(step.target)

    if (
        not isinstance(value, _RestrictedFunction)
        or value.defining_module != module
        or len(value.parameters)
        != len(step.call_argument_values)
    ):
        return None

    local_bindings.update(
        zip(
            value.parameters,
            step.call_argument_values,
        )
    )

    return value.body


def _execute_restricted_object_call(
    value: object,
    argument: object,
    *,
    module: str,
    local_bindings: dict[str, object | None],
) -> tuple[_Step, ...] | None:
    if (
        not isinstance(value, _RestrictedFunction)
        or value.defining_module != module
        or len(value.parameters) != 1
    ):
        return None

    local_bindings[value.parameters[0]] = argument
    return value.body
