"""
contextor/core/domain/validation.py

Validation domain model.
"""

from dataclasses import dataclass, field


@dataclass
class ValidationError:
    kind: str
    message: str
    nodes: list[str] = field(default_factory=list)
    code_snippets: dict = field(default_factory=dict)
    artifact_type: str | None = None
    is_identical: bool | None = None
