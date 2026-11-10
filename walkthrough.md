# P5-M05-D2 — Class fact and definition state contract

## PREFLIGHT

- DIRECT_EVIDENCE: HEAD `3544ee0ee9523fefca2ff772da80626b9cb53333`; initial `git status --short` was empty. The prior tracked `walkthrough.md` is replaced for this task; no pre-existing worktree changes were overwritten.
- DIRECT_EVIDENCE: Contextor MCP canonical LIVE revision 1274, `package_model.py` `canonical_state=fresh`, `workspace_sync=verified`, `provenance=live`; `cycle_semantics=stale`. Active backend executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` (PID 14072). Contextor symbol implementation, source range, call context and lineage were consulted before literal source searches.
- DIRECT_EVIDENCE: FILES_CHANGED=`walkthrough.md` only. Production/test/docs ACTUAL_DIFF=DIFFS=NONE. No tests or experiments were run.

## EXACT_CLASS_FACT_SOURCES

All following excerpts are verbatim from `contextor/core/cycle_semantics/package_model.py` at canonical revision 1274, verified by Contextor `get_source_range` and `get_symbol_implementation`.

### `_ClassFact` — lines 71-82

```python
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
```

### `_BUILTIN_TYPE_ID`, `_BUILTIN_CLASS_FACTS`, `_BUILTIN_EXCEPTION_CLASS_IDENTITIES` — lines 94-155

```python
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
```

### `_merge_class_mros` — lines 158-191

```python
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
```

## CONSTANT_DEPENDENCIES

- CODE_PATH_PROVED: `_BUILTIN_CLASS_FACTS` constructs five frozen `_ClassFact` instances and reads `_BUILTIN_TYPE_ID` in each metaclass field and the `type` MRO (`package_model.py:94-151`). `_BUILTIN_EXCEPTION_CLASS_IDENTITIES` reads those facts' identities for exactly three names (`:152-155`).
- DIRECT_EVIDENCE: Direct required import `dataclass` is at `package_model.py:12`; `_ClassFact` and `_merge_class_mros` use built-in `str`, `bool`, `tuple`, `list`, `any`, `next`, `len` and `None` (`:71-82,158-191`). No other module-level constant/helper is referenced by `_merge_class_mros` itself beyond the `_ClassFact` annotation.
- CODE_PATH_PROVED: Evaluator reads builtin facts/type ID during base and metaclass selection (`:2143-2160,2178-2190`), exception identity set for multiple bases (`:2238-2243`), and type ID when constructing derived class facts (`:2263-2268`). These are read-only module-global accesses; the evaluator-local `class_facts_by_identity` is a distinct mapping.

## STATE_INITIALIZATION

Verbatim current evaluator block at `package_model.py:1563-1576`:

```python
    prepared_class_bases: dict[
        str, tuple[tuple[_ClassFact, ...], _ClassFact]
    ] = {}
    class_facts_by_identity: dict[str, _ClassFact] = {
        fact.identity: fact for fact in _BUILTIN_CLASS_FACTS.values()
    }

    function_definitions: dict[
        str,
        dict[str, tuple[_Step, ...]],
    ] = {
        name: {}
        for name in programs
    }
```

- CODE_PATH_PROVED: These mappings are allocated for each evaluator invocation after `programs` and module namespaces exist (`package_model.py:1459-1512,1554-1576`). They are not fields of `_PackageSourceSession` (`:213-222`), are not returned in `PackageImportAssessment` (`:195-210,1278-1300`), and are not captured by nested `result`, `valid_chain`, `chain` or `missing_piece` (`:1269-1300,1445-1454,1582-1598`).

## STATE_READ_WRITE_CONTRACT

| Mapping | Reads | Modifications and order |
|---|---|---|
| `prepared_class_bases` | `DEFINE_PASSIVE_CLASS` pops by `step.definition_id or ""` at `package_model.py:2213-2229`; then validates tuple, bases and selected metaclass. | `PREPARE_PASSIVE_CLASS` stores `(base_facts,selected)` under `step.definition_id` after base/metaclass checks (`:2130-2211`). `DEFINE_PASSIVE_CLASS` removes it via `pop` (`:2214-2217`). Preparation must run before definition; missing/invalid value yields UNKNOWN (`:2218-2229`). |
| `class_facts_by_identity` | `PREPARE_PASSIVE_CLASS` resolves candidate metaclass identities using `.get` (`:2178-2210`). | Seeded from builtin facts (`:1566-1568`); `DEFINE_PASSIVE_CLASS` assigns new `class_fact` by identity before binding it in the module namespace (`:2253-2273`). Later class preparations see previous facts. |
| `function_definitions` | `CALL_FUNCTION` tests `step.target in function_definitions[module]` and reads its body (`:2283-2304`). | Per-module maps initialized from `programs` (`:1570-1576`). `DEFINE_FUNCTION` stores `step.function_body` under `step.binding` before writing namespace marker/event (`:2002-2017`). Call requires both stored body and current exact namespace marker, else UNKNOWN (`:2283-2298`). It inserts body steps into the invocation-local mutable program (`:2300-2315`). |

- CODE_PATH_PROVED: A class's final module binding occurs only after `_merge_class_mros`, class-fact construction and identity-map assignment (`package_model.py:2245-2281`). An alias/rebinding can preserve an older `_ClassFact` object in the namespace, while later class definitions use a new `definition_id` and new fact (`:2249-2273,2342-2344`).

## PRIVATE_DEPENDENCY_GRAPH

- DIRECT_EVIDENCE: `_ClassFact` has no private helper call and depends on `dataclass` (`package_model.py:12,71-82`). `_BUILTIN_TYPE_ID → _BUILTIN_CLASS_FACTS` at `:97,100-101,111,120,133,147`; `_ClassFact → _BUILTIN_CLASS_FACTS` constructors at `:96,106,115,124,137`; `_BUILTIN_CLASS_FACTS → _BUILTIN_EXCEPTION_CLASS_IDENTITIES` at `:153`. These arrows denote value consumption by the right-hand definition.
- CODE_PATH_PROVED: `_ClassFact` is used by `_safe_class_namespace_value` (`:85-91`), `_merge_class_mros` annotation (`:158-191`), evaluator initialization (`:1563-1568`), conditional class checks (`:2081-2089`), base/metaclass checks (`:2153-2197,2218-2229`) and new fact construction (`:2253-2269`). `_merge_class_mros` has direct caller evaluator at `:2245`, confirmed by Contextor call context.
- CODE_PATH_PROVED: Transitive path for class completion is `_BUILTIN_TYPE_ID/_BUILTIN_CLASS_FACTS/_ClassFact → class_facts_by_identity and base selection → _merge_class_mros → new _ClassFact → class_facts_by_identity/namespaces` (`:94-155,1563-1568,2130-2273`). There is no private helper call cycle among the identified definitions (`:71-191`).
- DIRECT_EVIDENCE: Contextor lineage for `_ClassFact` confirms bindings at builtin constructors `:96,106,115,124,137` and `_merge_class_mros` annotation `:159`; source inspection supplies additional evaluator-local uses not exposed in the bounded lineage section.

## EXTERNAL_COMPATIBILITY

- DIRECT_EVIDENCE: Current repository search found direct imports of `_ClassFact` and `_merge_class_mros` from `package_model` in `tests/test_cycle_semantics_passive_classes.py:10-14`. That file constructs `_ClassFact` values and calls `_merge_class_mros` at `:866-965`. No other current production/test direct import of these two or of the three constants was found; the constants and three maps are otherwise referenced only inside `package_model.py` (`:71-191,1563-1576,2002-2304`).
- DIRECT_EVIDENCE: Literal search of current production/tests found no monkeypatch, `is` identity comparison, `__module__`, `__globals__`, or reflective `getattr` access naming these five class symbols/constants or three local mapping names. The evaluator does use `isinstance(...,_ClassFact)` as a runtime class-identity-sensitive check (`:87,2081-2089,2153-2197,2218-2229`), and tests import the class directly (`tests/test_cycle_semantics_passive_classes.py:12`).
- CODE_PATH_PROVED: `_BUILTIN_CLASS_FACTS`, `_BUILTIN_TYPE_ID`, `_BUILTIN_EXCEPTION_CLASS_IDENTITIES`, `_ClassFact`, and `_merge_class_mros` are resolved from `package_model` module globals by the evaluator at the cited sites. The three execution maps are evaluator locals and not module globals (`:1563-1576`).
- UNKNOWN: Static repository search cannot exclude third-party imports or dynamic/reflection consumers beyond current source.

## REGRESSION_CONTRACTS

- DIRECT_EVIDENCE: Class identity/alias/rebinding: `tests/test_cycle_semantics_passive_classes.py:476 test_p3_d1_old_alias_keeps_redefined_class_identity`, `:495 test_p3_d1_reentrant_import_sees_class_unbound`; `tests/test_cycle_semantics_package_model.py:138 test_frozen_dataclass_rebound_name_does_not_bind_class`, `:479 test_r9_rejects_shadowed_builtin_before_class_body`.
- DIRECT_EVIDENCE: Preparation/final binding: `tests/test_cycle_semantics_passive_classes.py:144 test_c24_class_export_binding_order_hazard`, `:279 test_c24_class_body_import_executes_before_class_binding`, `:1015 test_p3_d3_reentrant_before_class_binding`, `:1036 test_p3_d3_import_after_class_binding`, `:1066 test_k09_a_class_name_bound_after_body`, `:1106 test_k09_b_module_binding_after_class`.
- DIRECT_EVIDENCE: MRO/metaclass: `tests/test_cycle_semantics_passive_classes.py:418 test_p3_d1_proven_class_bases_match_cpython`, `:760 test_p3_d2_supported_multiple_inheritance_matches_cpython`, `:866 test_p3_d2_c3_merge_preserves_order_and_common_ancestor`, `:917 test_p3_d2_c3_merge_rejects_conflicting_parent_order`, `:985 test_p3_d3_semantic_metaclass_selection`.
- DIRECT_EVIDENCE: Function storage/shadowing: `tests/test_cycle_semantics_package_model.py:2401 test_b0g4c5_deferred_function_import_not_executed`, `:2420 test_b0g4c5_call_activates_early_binding_hazard`, `:2468 test_b0g4c5_repeated_calls_import_child_once`, `:2542 test_b0g4c5_shadowed_function_call_unknown`; `tests/test_cycle_semantics_passive_functions.py:99 test_c23_existing_restricted_function_preserved`.
- DIRECT_EVIDENCE: Cache/repetition isolation: `tests/test_cycle_semantics_package_model.py:1715 test_warn_5i_preparation_reused_between_entries`, `:1776 test_warn_5i_function_expansion_does_not_mutate_cache`, `:1825 test_warn_5i_session_rejects_different_ast_identity`, `:2632 test_b0g4c5_deterministic_ast_unchanged`.
- DIRECT_EVIDENCE: Unsupported class mechanisms remain UNKNOWN: `tests/test_cycle_semantics_passive_classes.py:266 test_c24_unsupported_class_definitions_unknown`, `:466 test_p3_d1_unproven_class_mechanisms_stay_unknown`, `:559 test_p3_d1_unknown_set_name_descriptor_stays_unknown`, `:826 test_p3_d2_unproven_or_invalid_multiple_inheritance_stays_unknown`, `:1005 test_p3_d3_unproved_metaclass_effects_are_unknown`.
- UNKNOWN: These are existing source-level test contracts; no tests were executed for this discovery.

## UNRESOLVED_GAPS

- UNKNOWN: Canonical `cycle_semantics` is stale, so current semantic classification is not established by this discovery.
- UNKNOWN: External dynamic consumers and current runtime adoption of source were not attested. The evidence above describes verified repository source and existing tests.

## FINAL_DISCOVERY_VERDICT

- DIRECT_EVIDENCE: Complete current class-fact and constant sources, state initialization, map read/write sites, direct consumers and existing regressions are recorded above. No implementation or architecture design is proposed. STOP after discovery.
