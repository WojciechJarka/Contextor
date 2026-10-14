"""Conservative lexical activation requirements for explicit imports.

This is not a reachability, safety, or runtime-failure classifier.
"""

from __future__ import annotations

from dataclasses import dataclass

from .provenance import ImportProvenance


_SCOPE_REQUIREMENT = {
    "CLASS": "EXECUTE_CLASS_DEFINITION",
    "FUNCTION": "CALL_FUNCTION_BODY",
    "ASYNC_FUNCTION": "RESUME_COROUTINE_BODY",
}


@dataclass(frozen=True)
class ImportExecutionContext:
    ordinal: int
    line: int
    phase: str
    activation_requirements: tuple[str, ...]
    control_kinds: tuple[str, ...]
    guard_evaluation: str
    initialization_reachability: str


@dataclass(frozen=True)
class ExecutionContextProjection:
    module_id: str
    source_fingerprint: str
    contexts: tuple[ImportExecutionContext, ...]


def project_execution_context(
    provenance: ImportProvenance,
) -> ExecutionContextProjection:
    """Project lexical facts without inferring a safe import cycle.

    MODULE_OR_CLASS_CANDIDATE does not imply unconditional execution.
    CALL_DEPENDENT does not imply safety during module initialization.
    """
    if not isinstance(provenance, ImportProvenance):
        raise TypeError("provenance must be ImportProvenance")

    output: list[ImportExecutionContext] = []
    seen_ordinals: set[int] = set()

    for occurrence in provenance.occurrences:
        if occurrence.ordinal in seen_ordinals:
            raise ValueError("duplicate import occurrence ordinal")
        seen_ordinals.add(occurrence.ordinal)

        requirements = tuple(
            _SCOPE_REQUIREMENT.get(scope.kind, "UNKNOWN_SCOPE_ACTIVATION")
            for scope in occurrence.scopes
        )
        scope_types = {scope.kind for scope in occurrence.scopes}

        if "UNKNOWN_SCOPE_ACTIVATION" in requirements:
            phase = "UNKNOWN"
        elif scope_types & {"FUNCTION", "ASYNC_FUNCTION"}:
            phase = "CALL_DEPENDENT"
        else:
            phase = "MODULE_OR_CLASS_CANDIDATE"

        output.append(
            ImportExecutionContext(
                ordinal=occurrence.ordinal,
                line=occurrence.line,
                phase=phase,
                activation_requirements=requirements,
                control_kinds=tuple(frame.kind for frame in occurrence.controls),
                guard_evaluation=(
                    "UNEVALUATED" if occurrence.controls else "NO_LEXICAL_CONTROL"
                ),
                initialization_reachability="UNKNOWN",
            )
        )

    return ExecutionContextProjection(
        module_id=provenance.module_id,
        source_fingerprint=provenance.source_fingerprint,
        contexts=tuple(output),
    )
