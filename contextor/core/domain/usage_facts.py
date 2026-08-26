"""
contextor/core/domain/usage_facts.py

Compact, report-agnostic outbound usage facts for a single module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


SymbolCallFact = Tuple[str, str, int, str]
ReferenceEvidenceFact = Tuple[str, str, str, int]


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
    symbol_calls: Tuple[SymbolCallFact, ...] = ()
    symbol_calls_materialized: bool = False
    reference_evidence: Tuple[ReferenceEvidenceFact, ...] = ()

    def __getattribute__(self, name: str):
        if name == "symbol_calls_materialized":
            return bool(
                object.__getattribute__(self, "__dict__").get(name, False)
            )
        return object.__getattribute__(self, name)

    def __getattr__(self, name: str):
        # Pickle restores old dataclass instances without fields added later.
        if name in ("symbol_calls", "reference_evidence"):
            return ()
        raise AttributeError(name)

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
            "symbol_calls": [
                {
                    "caller": item[0],
                    "callee": item[1],
                    "line": item[2],
                    "call_kind": item[3],
                }
                for item in getattr(self, "symbol_calls", ())
            ],
            "symbol_calls_materialized": bool(
                vars(self).get("symbol_calls_materialized", False)
            ),
            "reference_evidence": [
                {
                    "target": item[0],
                    "channel": item[1],
                    "caller": item[2],
                    "line": item[3],
                }
                for item in getattr(self, "reference_evidence", ())
            ],
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
        symbol_calls = tuple(
            sorted(
                {
                    (
                        str(item["caller"]),
                        str(item["callee"]),
                        int(item["line"]),
                        str(item.get("call_kind", "direct")),
                    )
                    for item in data.get("symbol_calls", [])
                    if isinstance(item, dict)
                }
            )
        )

        raw_ref_ev = data.get("reference_evidence", [])
        reference_evidence = tuple(
            sorted(
                {
                    (
                        str(item["target"]),
                        str(item["channel"]),
                        str(item.get("caller", "")),
                        int(item.get("line", 0)),
                    )
                    for item in raw_ref_ev
                    if isinstance(item, dict)
                    and "target" in item
                    and "channel" in item
                }
            )
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
            symbol_calls=symbol_calls,
            symbol_calls_materialized=bool(
                data.get("symbol_calls_materialized", False)
            ),
            reference_evidence=reference_evidence,
        )


@dataclass(frozen=True)
class UsageDelta:
    """
    Pure, deterministic value model representing differences between two ModuleUsageFacts.
    """

    module_path: str
    added_imports: Tuple[str, ...] = ()
    removed_imports: Tuple[str, ...] = ()
    added_direct_calls: Tuple[str, ...] = ()
    removed_direct_calls: Tuple[str, ...] = ()
    added_runtime_calls: Tuple[str, ...] = ()
    removed_runtime_calls: Tuple[str, ...] = ()
    added_callback_calls: Tuple[str, ...] = ()
    removed_callback_calls: Tuple[str, ...] = ()
    added_event_bindings: Tuple[str, ...] = ()
    removed_event_bindings: Tuple[str, ...] = ()
    added_inheritance_refs: Tuple[Tuple[str, str], ...] = ()
    removed_inheritance_refs: Tuple[Tuple[str, str], ...] = ()
    added_qualified_refs: Tuple[str, ...] = ()
    removed_qualified_refs: Tuple[str, ...] = ()
    added_aliases: Tuple[Tuple[str, str], ...] = ()
    removed_aliases: Tuple[Tuple[str, str], ...] = ()
    added_symbol_calls: Tuple[SymbolCallFact, ...] = ()
    removed_symbol_calls: Tuple[SymbolCallFact, ...] = ()
    added_reference_evidence: Tuple[ReferenceEvidenceFact, ...] = ()
    removed_reference_evidence: Tuple[ReferenceEvidenceFact, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Returns True if no usage channel changed."""
        return not any(
            [
                self.added_imports,
                self.removed_imports,
                self.added_direct_calls,
                self.removed_direct_calls,
                self.added_runtime_calls,
                self.removed_runtime_calls,
                self.added_callback_calls,
                self.removed_callback_calls,
                self.added_event_bindings,
                self.removed_event_bindings,
                self.added_inheritance_refs,
                self.removed_inheritance_refs,
                self.added_qualified_refs,
                self.removed_qualified_refs,
                self.added_aliases,
                self.removed_aliases,
                self.added_symbol_calls,
                self.removed_symbol_calls,
                self.added_reference_evidence,
                self.removed_reference_evidence,
            ]
        )


def _diff_tuples(
    old_tup: Tuple[Any, ...], new_tup: Tuple[Any, ...]
) -> Tuple[Tuple[Any, ...], Tuple[Any, ...]]:
    old_set = set(old_tup)
    new_set = set(new_tup)
    added = tuple(sorted(new_set - old_set))
    removed = tuple(sorted(old_set - new_set))
    return added, removed


def diff_usage_facts(
    module_path: str,
    old_facts: ModuleUsageFacts | None,
    new_facts: ModuleUsageFacts | None,
) -> UsageDelta:
    """
    Computes pure UsageDelta between old and new ModuleUsageFacts for a module.
    """
    old_f = old_facts or ModuleUsageFacts()
    new_f = new_facts or ModuleUsageFacts()

    add_imp, rem_imp = _diff_tuples(old_f.imports, new_f.imports)
    add_dc, rem_dc = _diff_tuples(old_f.direct_calls, new_f.direct_calls)
    add_rc, rem_rc = _diff_tuples(old_f.runtime_calls, new_f.runtime_calls)
    add_cc, rem_cc = _diff_tuples(old_f.callback_calls, new_f.callback_calls)
    add_eb, rem_eb = _diff_tuples(old_f.event_bindings, new_f.event_bindings)
    add_inh, rem_inh = _diff_tuples(old_f.inheritance_refs, new_f.inheritance_refs)
    add_qr, rem_qr = _diff_tuples(old_f.qualified_refs, new_f.qualified_refs)
    add_alias, rem_alias = _diff_tuples(old_f.aliases, new_f.aliases)
    add_symbol_calls, rem_symbol_calls = _diff_tuples(
        getattr(old_f, "symbol_calls", ()),
        getattr(new_f, "symbol_calls", ()),
    )
    add_refev, rem_refev = _diff_tuples(
        getattr(old_f, "reference_evidence", ()),
        getattr(new_f, "reference_evidence", ()),
    )

    return UsageDelta(
        module_path=module_path,
        added_imports=add_imp,
        removed_imports=rem_imp,
        added_direct_calls=add_dc,
        removed_direct_calls=rem_dc,
        added_runtime_calls=add_rc,
        removed_runtime_calls=rem_rc,
        added_callback_calls=add_cc,
        removed_callback_calls=rem_cc,
        added_event_bindings=add_eb,
        removed_event_bindings=rem_eb,
        added_inheritance_refs=add_inh,
        removed_inheritance_refs=rem_inh,
        added_qualified_refs=add_qr,
        removed_qualified_refs=rem_qr,
        added_aliases=add_alias,
        removed_aliases=rem_alias,
        added_symbol_calls=add_symbol_calls,
        removed_symbol_calls=rem_symbol_calls,
        added_reference_evidence=add_refev,
        removed_reference_evidence=rem_refev,
    )
