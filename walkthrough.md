# P5-M05-I3 — Class facts and definition state extraction

## PREFLIGHT

- DIRECT_EVIDENCE: Initial HEAD `3544ee0ee9523fefca2ff772da80626b9cb53333`; initial `git status --short` showed only ` M walkthrough.md` from D2. That report was replaced. No pre-existing production/test changes were overwritten.
- DIRECT_EVIDENCE: Contextor MCP pre-change canonical LIVE revision 1274; `package_model.py` and `execution/state.py` `canonical_state=fresh`, `workspace_sync=verified`. Active backend executable `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe` (PID 14072).
- DIRECT_EVIDENCE: `package_model.py:71-191,1563-1576` matched D2 source and supplied exact blocks; `execution/state.py` contained the two accepted state classes/factories; `execution/class_facts.py` did not exist. `_ClassFact`, builtin constants and `_merge_class_mros` were still defined in `package_model.py`.
- CODE_PATH_PROVED: Independent semantic check found a literal move of frozen `_ClassFact`, builtin fact instances, C3 helper and per-invocation mapping comprehensions. The supplied phrase “immutable builtin reference data” is imprecise: `_BUILTIN_CLASS_FACTS` remains a mutable dict containing frozen facts. No new policy or Contextor-specific exception was introduced.

## FILES_CHANGED

- `contextor/core/cycle_semantics/execution/class_facts.py` — new module.
- `contextor/core/cycle_semantics/execution/state.py` — imports and definition-state class/factory.
- `contextor/core/cycle_semantics/package_model.py` — imports, old definitions removed and state factory use.
- `walkthrough.md` — this report, exempt from production/test FULL_DIFF counting.

## EXACT_IMPLEMENTATION

- DIRECT_EVIDENCE: New `class_facts.py` contains the specified class, constants and unchanged C3 helper. `state.py` retains previous definitions and adds only the specified imports, dataclass and factory. `package_model.py` re-exports the moved symbols by imports and binds three existing evaluator locals from `_new_definition_state(programs)`. Full task diffs below.

## CLASS_IDENTITY_CHECKS

- CONTRACT_PROVED: Backend venv assertions passed: all five `package_model` names are identical by `is` to `class_facts` names; `_safe_class_namespace_value.__globals__["_ClassFact"]` and evaluator `__globals__["_merge_class_mros"]` resolve the moved identities. `_compile` and evaluator retain `__module__ = contextor.core.cycle_semantics.package_model`.
- DIRECT_EVIDENCE: Relocated `_ClassFact.__module__` and `_merge_class_mros.__module__` are `contextor.core.cycle_semantics.execution.class_facts`; `_DefinitionState.__module__` and `_new_definition_state.__module__` are `contextor.core.cycle_semantics.execution.state`. Constants have no `__module__` attribute.

## DEFINITION_STATE_ISOLATION

- CONTRACT_PROVED: Backend venv assertions passed: builtin facts retain object identity, while two factory calls return distinct `prepared_class_bases`, `class_facts_by_identity`, outer `function_definitions` and inner per-module maps. Writing `first.function_definitions["pkg"]["f"]` leaves the second instance unchanged. Output: `IDENTITY_AND_ISOLATION=PASS`.

## TARGETED_TEST_RESULTS

- DIRECT_EVIDENCE: Exact seven-file backend venv command `-m pytest -q tests/test_cycle_semantics_package_model.py tests/test_cycle_semantics_passive_classes.py tests/test_cycle_semantics_passive_functions.py tests/test_cycle_semantics_package_model_literals.py tests/test_cycle_semantics_package_model_annotations315.py tests/test_cycle_semantics_decorator_definition_effects.py tests/test_f1h_runtime_attestation.py -rs` → **472 passed, 2 third-party deprecation warnings in 42.11 s**. SCC02 was excluded; its two earlier failures remain unresolved.
- DIRECT_EVIDENCE: `git diff --check` emitted no whitespace errors. The combined inspection command returned 1 solely because `git diff --no-index -- NUL ...class_facts.py` displayed a new-file difference.

## MCP_POST_CHANGE_AUDIT

- DIRECT_EVIDENCE: Canonical LIVE revision advanced 1274 → 1277. A transient `package_model.py workspace_sync=out_of_sync` at revision 1276 was followed by `workspace_sync=verified` for all three modules at revision 1277. Source/module/graph/topology families are fresh; syntax errors 0. `cycle_semantics` remains stale.
- DIRECT_EVIDENCE: Hard edges: `package_model → execution.class_facts`, `package_model → execution.state`; `execution.state → execution.class_facts` and `execution.state → execution.steps`. `execution.class_facts` has zero outbound hard edges. Neither execution module has a hard edge back to `package_model`. Structural cycle count 16 normalized DFS back-edge paths; active warning count 16.
- UNKNOWN: Current cyclic SCC count was not exposed in the selected LIVE queries. Fresh source/workspace sync does not prove loaded runtime adoption; no backend restart was made.
- DIRECT_EVIDENCE: During audit, an external `Auto-commit: Cleanup and update` created HEAD `415a12a42425a7be5ecadaaa91f1dcd1ad45483d` containing the `state.py` and `package_model.py` task edits. This agent issued no commit or push. The new `class_facts.py` was still untracked when `git status` was checked after that auto-commit. The full task diff below compares the initial HEAD to resulting source, including the new file.

## FULL_DIFFS

### `contextor/core/cycle_semantics/execution/class_facts.py`

```diff
diff --git a/contextor/core/cycle_semantics/execution/class_facts.py b/contextor/core/cycle_semantics/execution/class_facts.py
new file mode 100644
index 0000000..59f9e1b
--- /dev/null
+++ b/contextor/core/cycle_semantics/execution/class_facts.py
@@ -0,0 +1,119 @@
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+
+@dataclass(frozen=True)
+class _ClassFact:
+    """Provenance and creation facts for one passive class definition."""
+
+    identity: str
+    origin: str
+    direct_bases: tuple[str, ...]
+    linear_mro: tuple[str, ...]
+    metaclass_identity: str
+    defines_init_subclass: bool
+    safe_to_subclass: bool
+    passive_metaclass_creation: bool = False
+
+
+_BUILTIN_TYPE_ID = "builtins.type"
+
+_BUILTIN_CLASS_FACTS = {
+    "type": _ClassFact(
+        identity=_BUILTIN_TYPE_ID,
+        origin="BUILTIN",
+        direct_bases=("builtins.object",),
+        linear_mro=(_BUILTIN_TYPE_ID, "builtins.object"),
+        metaclass_identity=_BUILTIN_TYPE_ID,
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+        passive_metaclass_creation=True,
+    ),
+    "object": _ClassFact(
+        identity="builtins.object",
+        origin="BUILTIN",
+        direct_bases=(),
+        linear_mro=("builtins.object",),
+        metaclass_identity=_BUILTIN_TYPE_ID,
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    ),
+    "BaseException": _ClassFact(
+        identity="builtins.BaseException",
+        origin="BUILTIN",
+        direct_bases=("builtins.object",),
+        linear_mro=("builtins.BaseException", "builtins.object"),
+        metaclass_identity=_BUILTIN_TYPE_ID,
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    ),
+    "Exception": _ClassFact(
+        identity="builtins.Exception",
+        origin="BUILTIN",
+        direct_bases=("builtins.BaseException",),
+        linear_mro=(
+            "builtins.Exception",
+            "builtins.BaseException",
+            "builtins.object",
+        ),
+        metaclass_identity=_BUILTIN_TYPE_ID,
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    ),
+    "ValueError": _ClassFact(
+        identity="builtins.ValueError",
+        origin="BUILTIN",
+        direct_bases=("builtins.Exception",),
+        linear_mro=(
+            "builtins.ValueError",
+            "builtins.Exception",
+            "builtins.BaseException",
+            "builtins.object",
+        ),
+        metaclass_identity=_BUILTIN_TYPE_ID,
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    ),
+}
+
+_BUILTIN_EXCEPTION_CLASS_IDENTITIES = frozenset({
+    _BUILTIN_CLASS_FACTS[name].identity
+    for name in ("BaseException", "Exception", "ValueError")
+})
+
+
+def _merge_class_mros(
+    bases: tuple[_ClassFact, ...],
+) -> tuple[str, ...] | None:
+    """Return the C3 merge of proven base MROs, or None if inconsistent."""
+    sequences = [list(base.linear_mro) for base in bases]
+    sequences.append([base.identity for base in bases])
+    merged: list[str] = []
+
+    while any(sequences):
+        candidate = next(
+            (
+                sequence[0]
+                for sequence in sequences
+                if not any(
+                    sequence[0] in other[1:]
+                    for other in sequences
+                    if other
+                )
+            ),
+            None,
+        )
+        if candidate is None:
+            return None
+
+        merged.append(candidate)
+        remaining = []
+        for sequence in sequences:
+            if sequence and sequence[0] == candidate:
+                sequence = sequence[1:]
+            if sequence:
+                remaining.append(sequence)
+        sequences = remaining
+
+    return tuple(merged)
```

### `contextor/core/cycle_semantics/execution/state.py`

```diff
diff --git a/contextor/core/cycle_semantics/execution/state.py b/contextor/core/cycle_semantics/execution/state.py
index fca6811..2e261ce 100644
--- a/contextor/core/cycle_semantics/execution/state.py
+++ b/contextor/core/cycle_semantics/execution/state.py
@@ -3,6 +3,9 @@ from __future__ import annotations
 from dataclasses import dataclass
 from typing import Mapping
 
+from .class_facts import _ClassFact, _BUILTIN_CLASS_FACTS
+from .steps import _Step
+
 
 @dataclass
 class _ModuleInitializationState:
@@ -38,3 +41,31 @@ def _new_execution_cursor(
         frames=[(bootstrap, 0)],
         step_budget=10000,
     )
+
+
+@dataclass
+class _DefinitionState:
+    prepared_class_bases: dict[
+        str, tuple[tuple[_ClassFact, ...], _ClassFact]
+    ]
+    class_facts_by_identity: dict[str, _ClassFact]
+    function_definitions: dict[
+        str,
+        dict[str, tuple[_Step, ...]],
+    ]
+
+
+def _new_definition_state(
+    programs: Mapping[str, object],
+) -> _DefinitionState:
+    return _DefinitionState(
+        prepared_class_bases={},
+        class_facts_by_identity={
+            fact.identity: fact
+            for fact in _BUILTIN_CLASS_FACTS.values()
+        },
+        function_definitions={
+            name: {}
+            for name in programs
+        },
+    )
```

### `contextor/core/cycle_semantics/package_model.py`

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index efcd6cd..00eb8df 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -35,9 +35,17 @@ from .execution.definition_checks import (
     _exact_restricted_dataclass_hash_field_call,
     _restricted_dataclass_field_annotation,
 )
+from .execution.class_facts import (
+    _ClassFact,
+    _BUILTIN_TYPE_ID,
+    _BUILTIN_CLASS_FACTS,
+    _BUILTIN_EXCEPTION_CLASS_IDENTITIES,
+    _merge_class_mros,
+)
 from .execution.state import (
     _new_module_initialization_state,
     _new_execution_cursor,
+    _new_definition_state,
 )
 
 
@@ -68,20 +76,6 @@ class AssumedFrozenDataclassDecoration:
     column: int
 
 
-@dataclass(frozen=True)
-class _ClassFact:
-    """Provenance and creation facts for one passive class definition."""
-
-    identity: str
-    origin: str
-    direct_bases: tuple[str, ...]
-    linear_mro: tuple[str, ...]
-    metaclass_identity: str
-    defines_init_subclass: bool
-    safe_to_subclass: bool
-    passive_metaclass_creation: bool = False
-
-
 def _safe_class_namespace_value(value: object) -> bool:
     """Values admitted in a passive class namespace cannot be descriptors."""
     if isinstance(value, _ClassFact) or value is None:
@@ -91,106 +85,6 @@ def _safe_class_namespace_value(value: object) -> bool:
     return False
 
 
-_BUILTIN_TYPE_ID = "builtins.type"
-_BUILTIN_CLASS_FACTS = {
-    "type": _ClassFact(
-        identity=_BUILTIN_TYPE_ID,
-        origin="BUILTIN",
-        direct_bases=("builtins.object",),
-        linear_mro=(_BUILTIN_TYPE_ID, "builtins.object"),
-        metaclass_identity=_BUILTIN_TYPE_ID,
-        defines_init_subclass=False,
-        safe_to_subclass=True,
-        passive_metaclass_creation=True,
-    ),
-    "object": _ClassFact(
-        identity="builtins.object",
-        origin="BUILTIN",
-        direct_bases=(),
-        linear_mro=("builtins.object",),
-        metaclass_identity=_BUILTIN_TYPE_ID,
-        defines_init_subclass=False,
-        safe_to_subclass=True,
-    ),
-    "BaseException": _ClassFact(
-        identity="builtins.BaseException",
-        origin="BUILTIN",
-        direct_bases=("builtins.object",),
-        linear_mro=("builtins.BaseException", "builtins.object"),
-        metaclass_identity=_BUILTIN_TYPE_ID,
-        defines_init_subclass=False,
-        safe_to_subclass=True,
-    ),
-    "Exception": _ClassFact(
-        identity="builtins.Exception",
-        origin="BUILTIN",
-        direct_bases=("builtins.BaseException",),
-        linear_mro=(
-            "builtins.Exception",
-            "builtins.BaseException",
-            "builtins.object",
-        ),
-        metaclass_identity=_BUILTIN_TYPE_ID,
-        defines_init_subclass=False,
-        safe_to_subclass=True,
-    ),
-    "ValueError": _ClassFact(
-        identity="builtins.ValueError",
-        origin="BUILTIN",
-        direct_bases=("builtins.Exception",),
-        linear_mro=(
-            "builtins.ValueError",
-            "builtins.Exception",
-            "builtins.BaseException",
-            "builtins.object",
-        ),
-        metaclass_identity=_BUILTIN_TYPE_ID,
-        defines_init_subclass=False,
-        safe_to_subclass=True,
-    ),
-}
-_BUILTIN_EXCEPTION_CLASS_IDENTITIES = frozenset({
-    _BUILTIN_CLASS_FACTS[name].identity
-    for name in ("BaseException", "Exception", "ValueError")
-})
-
-
-def _merge_class_mros(
-    bases: tuple[_ClassFact, ...],
-) -> tuple[str, ...] | None:
-    """Return the C3 merge of proven base MROs, or None if inconsistent."""
-    sequences = [list(base.linear_mro) for base in bases]
-    sequences.append([base.identity for base in bases])
-    merged: list[str] = []
-
-    while any(sequences):
-        candidate = next(
-            (
-                sequence[0]
-                for sequence in sequences
-                if not any(
-                    sequence[0] in other[1:]
-                    for other in sequences
-                    if other
-                )
-            ),
-            None,
-        )
-        if candidate is None:
-            return None
-
-        merged.append(candidate)
-        remaining = []
-        for sequence in sequences:
-            if sequence and sequence[0] == candidate:
-                sequence = sequence[1:]
-            if sequence:
-                remaining.append(sequence)
-        sequences = remaining
-
-    return tuple(merged)
-
-
 @dataclass(frozen=True)
 class PackageImportAssessment:
     entry_module: str
@@ -1560,20 +1454,10 @@ def evaluate_package_import_order(
     )
     states = module_initialization_state.states
     namespaces = module_initialization_state.namespaces
-    prepared_class_bases: dict[
-        str, tuple[tuple[_ClassFact, ...], _ClassFact]
-    ] = {}
-    class_facts_by_identity: dict[str, _ClassFact] = {
-        fact.identity: fact for fact in _BUILTIN_CLASS_FACTS.values()
-    }
-
-    function_definitions: dict[
-        str,
-        dict[str, tuple[_Step, ...]],
-    ] = {
-        name: {}
-        for name in programs
-    }
+    definition_state = _new_definition_state(programs)
+    prepared_class_bases = definition_state.prepared_class_bases
+    class_facts_by_identity = definition_state.class_facts_by_identity
+    function_definitions = definition_state.function_definitions
 
     bootstrap = "\x00ENTRY"
     execution_cursor = _new_execution_cursor(bootstrap)
```

## FINAL_VERDICT

- CONTRACT_PROVED: Exact source extraction, identity/isolation assertions and focused regressions passed. Contextor confirmed all three sources synchronized by revision 1277, zero syntax errors, no reverse hard import and unchanged structural cycle count. `cycle_semantics` remains stale, so no fresh semantic-classification or runtime-adoption claim is made. STOP after implementation and audit.
