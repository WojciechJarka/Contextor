from contextor.core.domain.graph import ProjectGraph
from contextor.core.domain.validation import ValidationError
from contextor.core.graph.cycles import detect_cycles


def validate_cycles(graph: ProjectGraph, progress_callback=None) -> list[ValidationError]:
    """Converts raw cycles from the analyzer into architectural errors."""
    cycles = detect_cycles(graph.hard_edges, progress_callback=progress_callback)
    errors = []
    for cycle in cycles:
        chain = " -> ".join(cycle)
        errors.append(
            ValidationError(
                kind="ArchitectureCycle",
                message=f"Cyclic dependency detected in architecture: {chain}",
                nodes=cycle,
            )
        )
    return errors
