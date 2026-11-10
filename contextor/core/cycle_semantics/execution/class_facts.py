from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _ClassFact:
    """Provenance and creation facts for one passive class definition."""

    identity: str
    origin: str
    direct_bases: tuple[str, ...]
    linear_mro: tuple[str, ...]
    metaclass_identity: str
    defines_init_subclass: bool
    safe_to_subclass: bool
    passive_metaclass_creation: bool = False


_BUILTIN_TYPE_ID = "builtins.type"

_BUILTIN_CLASS_FACTS = {
    "type": _ClassFact(
        identity=_BUILTIN_TYPE_ID,
        origin="BUILTIN",
        direct_bases=("builtins.object",),
        linear_mro=(_BUILTIN_TYPE_ID, "builtins.object"),
        metaclass_identity=_BUILTIN_TYPE_ID,
        defines_init_subclass=False,
        safe_to_subclass=True,
        passive_metaclass_creation=True,
    ),
    "object": _ClassFact(
        identity="builtins.object",
        origin="BUILTIN",
        direct_bases=(),
        linear_mro=("builtins.object",),
        metaclass_identity=_BUILTIN_TYPE_ID,
        defines_init_subclass=False,
        safe_to_subclass=True,
    ),
    "BaseException": _ClassFact(
        identity="builtins.BaseException",
        origin="BUILTIN",
        direct_bases=("builtins.object",),
        linear_mro=("builtins.BaseException", "builtins.object"),
        metaclass_identity=_BUILTIN_TYPE_ID,
        defines_init_subclass=False,
        safe_to_subclass=True,
    ),
    "Exception": _ClassFact(
        identity="builtins.Exception",
        origin="BUILTIN",
        direct_bases=("builtins.BaseException",),
        linear_mro=(
            "builtins.Exception",
            "builtins.BaseException",
            "builtins.object",
        ),
        metaclass_identity=_BUILTIN_TYPE_ID,
        defines_init_subclass=False,
        safe_to_subclass=True,
    ),
    "ValueError": _ClassFact(
        identity="builtins.ValueError",
        origin="BUILTIN",
        direct_bases=("builtins.Exception",),
        linear_mro=(
            "builtins.ValueError",
            "builtins.Exception",
            "builtins.BaseException",
            "builtins.object",
        ),
        metaclass_identity=_BUILTIN_TYPE_ID,
        defines_init_subclass=False,
        safe_to_subclass=True,
    ),
}

_BUILTIN_EXCEPTION_CLASS_IDENTITIES = frozenset({
    _BUILTIN_CLASS_FACTS[name].identity
    for name in ("BaseException", "Exception", "ValueError")
})


def _merge_class_mros(
    bases: tuple[_ClassFact, ...],
) -> tuple[str, ...] | None:
    """Return the C3 merge of proven base MROs, or None if inconsistent."""
    sequences = [list(base.linear_mro) for base in bases]
    sequences.append([base.identity for base in bases])
    merged: list[str] = []

    while any(sequences):
        candidate = next(
            (
                sequence[0]
                for sequence in sequences
                if not any(
                    sequence[0] in other[1:]
                    for other in sequences
                    if other
                )
            ),
            None,
        )
        if candidate is None:
            return None

        merged.append(candidate)
        remaining = []
        for sequence in sequences:
            if sequence and sequence[0] == candidate:
                sequence = sequence[1:]
            if sequence:
                remaining.append(sequence)
        sequences = remaining

    return tuple(merged)
