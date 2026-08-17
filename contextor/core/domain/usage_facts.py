"""
contextor/core/domain/usage_facts.py

Compact, report-agnostic outbound usage facts for a single module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class ModuleUsageFacts:
    """
    Outbound usage facts extracted for one module.

    All collection fields are stored as sorted tuples of immutable primitives
    to guarantee determinism, hashability, fast equality checking, and zero
    report-formatting coupling.
    """

    imports: Tuple[str, ...] = ()
    direct_calls: Tuple[str, ...] = ()
    runtime_calls: Tuple[str, ...] = ()
    callback_calls: Tuple[str, ...] = ()
    event_bindings: Tuple[str, ...] = ()
    inheritance_refs: Tuple[Tuple[str, str], ...] = ()  # (child_class, base_symbol)
    qualified_refs: Tuple[str, ...] = ()
    aliases: Tuple[Tuple[str, str], ...] = ()           # (local_alias, imported_target)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize usage facts to a plain dictionary."""
        return {
            "imports": list(self.imports),
            "direct_calls": list(self.direct_calls),
            "runtime_calls": list(self.runtime_calls),
            "callback_calls": list(self.callback_calls),
            "event_bindings": list(self.event_bindings),
            "inheritance_refs": [list(item) for item in self.inheritance_refs],
            "qualified_refs": list(self.qualified_refs),
            "aliases": [list(item) for item in self.aliases],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "ModuleUsageFacts":
        """Deserialize usage facts from a dictionary."""
        if not data:
            return cls()

        imports = tuple(sorted(set(data.get("imports", []))))
        direct_calls = tuple(sorted(set(data.get("direct_calls", []))))
        runtime_calls = tuple(sorted(set(data.get("runtime_calls", []))))
        callback_calls = tuple(sorted(set(data.get("callback_calls", []))))
        event_bindings = tuple(sorted(set(data.get("event_bindings", []))))
        qualified_refs = tuple(sorted(set(data.get("qualified_refs", []))))

        raw_inh = data.get("inheritance_refs", [])
        inheritance_refs = tuple(
            sorted(set(tuple(item) for item in raw_inh if len(item) == 2))
        )

        raw_aliases = data.get("aliases", [])
        aliases = tuple(
            sorted(set(tuple(item) for item in raw_aliases if len(item) == 2))
        )

        return cls(
            imports=imports,
            direct_calls=direct_calls,
            runtime_calls=runtime_calls,
            callback_calls=callback_calls,
            event_bindings=event_bindings,
            inheritance_refs=inheritance_refs,
            qualified_refs=qualified_refs,
            aliases=aliases,
        )

