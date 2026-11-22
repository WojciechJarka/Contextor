# P10-FINAL-R2-I1-R1 — EVIDENCE SCOPE CONTRACT

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP przed edycją: LIVE revision 1533, canonical_state=fresh, syntax_errors=0; package_model.py, namespace_bound_model.py i oba testy: workspace_sync=verified. Anchory: `tests/test_cycle_semantics_package_model.py:3260-3263` w `test_p9_i1_known_builtin_decorator_identity` oraz `tests/test_cycle_semantics_namespace_bound_model.py:1162-1165` w `test_p9_i1_source_bound_decorator_identity`.
- DIRECT_EVIDENCE: istniejące zmiany I1 pozostawiono. `git status --short` wykazuje także wcześniej zmieniony `audyt.txt`; nie odczytywano go ani nie zmieniano. Nie użyto `git restore`, staging, commit, push ani restartu.
- CODE_PATH_PROVED: oba testy przekazują jawny kontrakt `("builtins", "property"): "PASSIVE_PROPERTY"`; wynik może mieć użyte założenie Call, więc asercja scope musi odzwierciedlać `model.assumed_external_call_effects` bez rozróżniania nazw przypadków.

## DOKŁADNIE DWA ZASTĄPIENIA

1. `tests/test_cycle_semantics_package_model.py`, `test_p9_i1_known_builtin_decorator_identity`: do dotychczasowej wartości asercji `evidence_scope` dopisano warunkowy suffix `|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED` wtedy i tylko wtedy, gdy `model.assumed_external_call_effects` jest niepuste.
2. `tests/test_cycle_semantics_namespace_bound_model.py`, `test_p9_i1_source_bound_decorator_identity`: identyczne zastąpienie. Żadnych innych asercji nie zmieniono w R1. Dodatkowe różnice względem HEAD w diffie poniżej pochodzą z zachowanego I1.

## TARGETED TESTS — CPython 3.15.2

Kolejno, bez pełnego pytest i FULL:

1. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py -k "p9_i1_known_builtin_decorator_identity"`: **15 passed, 226 deselected**.
2. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_namespace_bound_model.py -k "p8 or p9"`: **18 passed, 46 deselected**.
3. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_package_model.py -k "p8 or r11 or p9"`: **59 passed, 182 deselected**.
4. `.venv/Scripts/python.exe -m pytest -q tests/test_cycle_semantics_external_call_effects.py tests/test_cycle_semantics_annotation_effects_i3.py tests/test_cycle_semantics_annotation_union_i1.py tests/test_cycle_semantics_conditional_class_identity_i2.py`: **58 passed**.

## POST-CHANGE MCP AUDIT

- DIRECT_EVIDENCE: `get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo", fields=[])`: LIVE revision **1535**, `canonical_state=fresh`, provenance=live, `syntax_errors.count=0` / availability=fresh. Rodzina `cycle_semantics=stale` jest odrębna od świeżej składni i nie stanowi wyniku tego testu.
- DIRECT_EVIDENCE: `get_module_context(compact=true)` dla `execution/calls.py`, `package_model.py`, `namespace_bound_model.py`, dwóch edytowanych testów i `test_cycle_semantics_external_call_effects.py`: każdy ma `workspace_sync=verified`, `canonical_state=fresh`, revision 1535.
- DIRECT_EVIDENCE: `get_symbol_lineage` dla `contextor.core.cycle_semantics.execution.calls::_CallableEffectFact`, LIVE 1535: definicja `calls.py:17`, pola `canonical_identity` i `import_origin` przy `calls.py:20-21`, użycia konstrukcji/faktu przy `calls.py:25,35,42`. Ograniczenie lineage: lokalne użycia między modułami sprawdzono również po źródle.
- CODE_PATH_PROVED: `calls.py:17-29` tworzy fakt standardowego `builtins.property` z `provenance="CONVENTIONAL_BUILTIN"` i canonical identity. `calls.py:63-91` waliduje jawne deklaracje efektu. `package_model.py:1518-1563` odróżnia `CONVENTIONAL_BUILTIN` od `ASSUMED_EXTERNAL_CALL_EFFECT`; ten drugi zapisuje `AssumedExternalCallEffect` tylko przy konsumpcji. `package_model.py:2135-2167` przy zewnętrznym FROM tworzy `_CallableEffectFact` tylko gdy istnieje deklaracja dla pary import module/symbol; bez niej pozostaje sentinel `ASSUMED_EXTERNAL`. `package_model.py:2669,2687` wymaga `accept_callable_effect` przed dopuszczeniem wywołania. `package_model.py:1572-1605` wyprowadza suffix evidence_scope z faktycznie użytych założeń, a nie z samego importu.
- CONTRACT_PROVED w tym zakresie: pasywny import nie jest automatycznie dowodem efektu późniejszego Call. Tożsamość i pasywność zewnętrznego callable są objęte jawnym, warunkowym kontraktem; suffix mówi wprost `NOT_RUNTIME_ATTESTED`. Zwykłe lokalne `MODEL_PASS` i utrwalony historyczny `cycle_semantics` nie certyfikują wykonania runtime.

## D1 — PONOWNA WERYFIKACJA

Źródła AST: `pkg.__init__ = "from dataclasses import dataclass, field\\n@dataclass(frozen=True)\\nclass C:\\n x: int = field()\\n"`; `pkg.child = "from pkg import C\\n"`. Model: `annotation_semantics="DEFERRED"`, `_compile_on_first_import=True`, pasywny import zewnętrzny i dekoracja frozen jako założenia. Porównanie na identycznym AST:

- Bez `_assumed_external_callable_effects`: **UNKNOWN**, `assumed_external_call_effects=()`, scope bazowy; eventy: `START_IMPORT`, cztery `ASSUMED_EXTERNAL_IMPORT`; brak publikacji dekoracji.
- Z `{("dataclasses", "field"): "PASSIVE_DEFAULTLESS_DATACLASS_FIELD"}`: warunkowy **MODEL_PASS**, jeden `AssumedExternalCallEffect(import_module="dataclasses", imported_symbol="field", effect="PASSIVE_DEFAULTLESS_DATACLASS_FIELD")`, scope z `|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED`; potem `CLASS_LOCAL_BIND`, `ASSUMED_FROZEN_DATACLASS_DECORATION`, `DEFINE_PASSIVE_CLASS`, `READY`.
- Izolowany CPython 3.15.2, skrypt poza repo `C:\\Temp\\p10_r2_field_counterexample.py`: standardowe `field()` daje `RESULT <class 'int'>`. Podmieniony w `sys.modules['dataclasses']` moduł z `field()` importującym `pkg.child` daje `FIELD_IMPORT_CHILD`, po czym `ImportError: cannot import name 'C' from 'pkg'`. Różnica jest zgodna z jawną granicą założenia; kontrakt nie atestuje realnego callable w danym runtime.

## FILES_CHANGED

W R1: `tests/test_cycle_semantics_package_model.py`, `tests/test_cycle_semantics_namespace_bound_model.py`, `walkthrough.md`. Zachowane zmiany I1 względem HEAD: `contextor/core/cycle_semantics/execution/calls.py`, `contextor/core/cycle_semantics/package_model.py`, `contextor/core/cycle_semantics/namespace_bound_model.py`, obydwa wymienione testy oraz nowy `tests/test_cycle_semantics_external_call_effects.py`. `walkthrough.md` jest raportem i nie ma własnego diffu. `audyt.txt` jest zastaną, nietkniętą zmianą użytkownika.

## FULL_DIFFS SOURCE/TESTS WZGLĘDEM HEAD

```diff
diff --git a/contextor/core/cycle_semantics/execution/calls.py b/contextor/core/cycle_semantics/execution/calls.py
index 81e787d..bcf2232 100644
--- a/contextor/core/cycle_semantics/execution/calls.py
+++ b/contextor/core/cycle_semantics/execution/calls.py
@@ -1,5 +1,6 @@
 from __future__ import annotations
 
+from collections.abc import Mapping
 from dataclasses import dataclass
 
 from .steps import _Step
@@ -13,28 +14,32 @@ class _RestrictedFunction:
 
 
 @dataclass(frozen=True)
-class _KnownBuiltinCallable:
-    canonical_identity: str
+class _CallableEffectFact:
     effect: str
+    provenance: str
+    canonical_identity: str | None = None
+    import_origin: tuple[str, str] | None = None
 
 
 _KNOWN_BUILTIN_CALLABLES = {
-    "property": _KnownBuiltinCallable(
-        "builtins.property", "PASSIVE_PROPERTY",
+    "property": _CallableEffectFact(
+        effect="PASSIVE_PROPERTY",
+        provenance="CONVENTIONAL_BUILTIN",
+        canonical_identity="builtins.property",
     ),
 }
 
 
 def _known_builtin_callable(
     name: str | None,
-) -> _KnownBuiltinCallable | None:
+) -> _CallableEffectFact | None:
     return _KNOWN_BUILTIN_CALLABLES.get(name)
 
 
 def _resolve_known_builtin_callable(
     name: str | None,
     namespace: dict[str, object | None],
-) -> _KnownBuiltinCallable | None:
+) -> _CallableEffectFact | None:
     if name is None:
         return None
     value = (
@@ -44,11 +49,50 @@ def _resolve_known_builtin_callable(
     )
     return (
         value
-        if type(value) is _KnownBuiltinCallable
+        if type(value) is _CallableEffectFact
         else None
     )
 
 
+_SUPPORTED_CALL_EFFECTS = frozenset({
+    "PASSIVE_PROPERTY",
+    "PASSIVE_DEFAULTLESS_DATACLASS_FIELD",
+})
+
+
+def _validate_external_callable_effects(
+    declared: Mapping[tuple[str, str], str] | None,
+) -> dict[tuple[str, str], str] | None:
+    if declared is None:
+        return {}
+
+    if not isinstance(declared, Mapping):
+        return None
+
+    validated: dict[tuple[str, str], str] = {}
+
+    for key, effect in declared.items():
+        if (
+            type(key) is not tuple
+            or len(key) != 2
+            or type(key[0]) is not str
+            or type(key[1]) is not str
+            or not key[0]
+            or not all(
+                part.isidentifier()
+                for part in key[0].split(".")
+            )
+            or not key[1].isidentifier()
+            or type(effect) is not str
+            or effect not in _SUPPORTED_CALL_EFFECTS
+        ):
+            return None
+
+        validated[key] = effect
+
+    return validated
+
+
 @dataclass(frozen=True, eq=False)
 class _DecoratorSnapshot:
     names: tuple[str, ...]
diff --git a/contextor/core/cycle_semantics/namespace_bound_model.py b/contextor/core/cycle_semantics/namespace_bound_model.py
index d7a88cd..d488948 100644
--- a/contextor/core/cycle_semantics/namespace_bound_model.py
+++ b/contextor/core/cycle_semantics/namespace_bound_model.py
@@ -60,6 +60,9 @@ def evaluate_source_bound_conditional_namespace_import_order(
     target_python_version: tuple[int, int] | None = None,
     assume_passive_external_imports: bool = False,
     assume_frozen_dataclass_decoration: bool = False,
+    assumed_external_callable_effects: (
+        Mapping[tuple[str, str], str] | None
+    ) = None,
 ) -> SourceBoundConditionalNamespaceAssessment:
     """Parse indexed byte snapshots and conditionally evaluate PEP 420.
 
@@ -225,6 +228,9 @@ def evaluate_source_bound_conditional_namespace_import_order(
         assume_frozen_dataclass_decoration=(
             assume_frozen_dataclass_decoration
         ),
+        assumed_external_callable_effects=(
+            assumed_external_callable_effects
+        ),
     )
 
     # Never convert CONDITIONAL_MODEL_PASS into MODEL_PASS.
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 6aa45d6..366609c 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -67,6 +67,7 @@ from .execution.lifecycle import (
     _start_module_frame,
 )
 from .execution.calls import (
+    _CallableEffectFact,
     _RestrictedFunction,
     _execute_restricted_call,
     _execute_restricted_object_call,
@@ -74,6 +75,7 @@ from .execution.calls import (
     _new_restricted_function,
     _resolve_known_builtin_callable,
     _snapshot_named_decorators,
+    _validate_external_callable_effects,
 )
 
 
@@ -104,6 +106,13 @@ class AssumedFrozenDataclassDecoration:
     column: int
 
 
+@dataclass(frozen=True)
+class AssumedExternalCallEffect:
+    import_module: str
+    imported_symbol: str
+    effect: str
+
+
 def _safe_class_namespace_value(value: object) -> bool:
     """Values admitted in a passive class namespace cannot be descriptors."""
     if isinstance(value, _ClassFact) or value is None:
@@ -134,6 +143,9 @@ class PackageImportAssessment:
     assumed_dataclass_decorations: (
         tuple[AssumedFrozenDataclassDecoration, ...]
     ) = ()
+    assumed_external_call_effects: (
+        tuple[AssumedExternalCallEffect, ...]
+    ) = ()
 
     @property
     def builtin_environment_precondition(self) -> str:
@@ -1483,6 +1495,9 @@ def evaluate_package_import_order(
     _compile_on_first_import: bool = False,
     _assume_passive_external_imports: bool = False,
     _assume_frozen_dataclass_decoration: bool = False,
+    _assumed_external_callable_effects: (
+        Mapping[tuple[str, str], str] | None
+    ) = None,
 ) -> PackageImportAssessment:
     """Simulate a restricted closed regular-package source set.
 
@@ -1500,6 +1515,52 @@ def evaluate_package_import_order(
         AssumedFrozenDataclassDecoration
     ] = []
 
+    validated_call_effects = (
+        _validate_external_callable_effects(
+            _assumed_external_callable_effects
+        )
+    )
+
+    used_external_call_effects: list[
+        AssumedExternalCallEffect
+    ] = []
+
+    def accept_callable_effect(
+        value: object,
+        required_effect: str,
+    ) -> bool:
+        if (
+            type(value) is not _CallableEffectFact
+            or value.effect != required_effect
+        ):
+            return False
+
+        if value.provenance == "CONVENTIONAL_BUILTIN":
+            return (
+                value.canonical_identity is not None
+                and value.import_origin is None
+            )
+
+        if (
+            value.provenance
+            != "ASSUMED_EXTERNAL_CALL_EFFECT"
+            or value.import_origin is None
+            or value.canonical_identity is not None
+        ):
+            return False
+
+        origin_module, origin_symbol = value.import_origin
+
+        used_external_call_effects.append(
+            AssumedExternalCallEffect(
+                import_module=origin_module,
+                imported_symbol=origin_symbol,
+                effect=value.effect,
+            )
+        )
+
+        return True
+
     def result(
         outcome: str,
         target: str | None = None,
@@ -1516,13 +1577,20 @@ def evaluate_package_import_order(
             symbol,
             tuple(events),
             evidence_scope=(
-                "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
-                "ASSUMPTIONS_NOT_RUNTIME_PROOF"
-                if _assume_frozen_dataclass_decoration is True
-                else "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
-                "ASSUMPTION_NOT_RUNTIME_PROOF"
-                if _assume_passive_external_imports is True
-                else "RESTRICTED_REGULAR_PACKAGE_MODEL"
+                (
+                    "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+                    "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+                    if _assume_frozen_dataclass_decoration is True
+                    else "CONDITIONAL_PASSIVE_EXTERNAL_IMPORT_"
+                    "ASSUMPTION_NOT_RUNTIME_PROOF"
+                    if _assume_passive_external_imports is True
+                    else "RESTRICTED_REGULAR_PACKAGE_MODEL"
+                )
+                + (
+                    "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
+                    if used_external_call_effects
+                    else ""
+                )
             ),
             reached_unmodeled_import=reached_unmodeled_import,
             assumed_external_imports=tuple(
@@ -1531,6 +1599,9 @@ def evaluate_package_import_order(
             assumed_dataclass_decorations=tuple(
                 assumed_dataclass_decorations
             ),
+            assumed_external_call_effects=tuple(
+                used_external_call_effects
+            ),
         )
 
     if (
@@ -1542,6 +1613,11 @@ def evaluate_package_import_order(
         or type(_compile_on_first_import) is not bool
         or type(_assume_passive_external_imports) is not bool
         or type(_assume_frozen_dataclass_decoration) is not bool
+        or validated_call_effects is None
+        or (
+            bool(validated_call_effects)
+            and not _assume_passive_external_imports
+        )
         or (
             _assume_frozen_dataclass_decoration
             and (
@@ -2062,18 +2138,24 @@ def evaluate_package_import_order(
                         and not step.function_local
                         and not step.class_local
                     ):
-                        known_builtin = (
-                            _known_builtin_callable(step.symbol)
+                        declared_effect = (
+                            validated_call_effects.get(
+                                (target, step.symbol)
+                            )
                             if (
-                                _assume_frozen_dataclass_decoration
-                                and step.op == "FROM"
-                                and target == "builtins"
+                                step.op == "FROM"
+                                and type(step.symbol) is str
                             )
                             else None
                         )
                         namespaces[module][step.binding] = (
-                            known_builtin
-                            if known_builtin is not None
+                            _CallableEffectFact(
+                                effect=declared_effect,
+                                provenance="ASSUMED_EXTERNAL_CALL_EFFECT",
+                                canonical_identity=None,
+                                import_origin=(target, step.symbol),
+                            )
+                            if declared_effect is not None
                             else (
                                 "\x00ASSUMED_EXTERNAL:"
                                 + target
@@ -2584,8 +2666,10 @@ def evaluate_package_import_order(
         elif step.op == "CHECK_DATACLASS_FIELD_FACTORY":
             if (
                 not step.target
-                or namespaces[module].get(step.target)
-                != "\x00ASSUMED_EXTERNAL:dataclasses:field"
+                or not accept_callable_effect(
+                    namespaces[module].get(step.target),
+                    "PASSIVE_DEFAULTLESS_DATACLASS_FIELD",
+                )
             ):
                 return result(
                     "UNKNOWN",
@@ -2600,8 +2684,10 @@ def evaluate_package_import_order(
             )
             if (
                 not step.binding
-                or callable_fact is None
-                or callable_fact.effect != "PASSIVE_PROPERTY"
+                or not accept_callable_effect(
+                    callable_fact,
+                    "PASSIVE_PROPERTY",
+                )
             ):
                 return result(
                     "UNKNOWN",
@@ -3397,6 +3483,9 @@ def evaluate_conditional_namespace_import_order(
     target_python_version: tuple[int, int] | None = None,
     assume_passive_external_imports: bool = False,
     assume_frozen_dataclass_decoration: bool = False,
+    assumed_external_callable_effects: (
+        Mapping[tuple[str, str], str] | None
+    ) = None,
 ) -> ConditionalNamespaceModelAssessment:
     """Evaluate a supplied closed PEP 420 inventory conditionally.
 
@@ -3677,6 +3766,9 @@ def evaluate_conditional_namespace_import_order(
         _assume_frozen_dataclass_decoration=(
             assume_frozen_dataclass_decoration
         ),
+        _assumed_external_callable_effects=(
+            assumed_external_callable_effects
+        ),
     )
 
     conditional_outcomes = {
diff --git a/tests/test_cycle_semantics_namespace_bound_model.py b/tests/test_cycle_semantics_namespace_bound_model.py
index 7a0b750..90f2291 100644
--- a/tests/test_cycle_semantics_namespace_bound_model.py
+++ b/tests/test_cycle_semantics_namespace_bound_model.py
@@ -126,7 +126,10 @@ _FROZEN_CLASS = (
 )
 
 
-def _dataclass_result(source, *, decorate=False, external=True, child=None):
+def _dataclass_result(
+    source, *, decorate=False, external=True, child=None,
+    assumed_effects=None,
+):
     return evaluate_source_bound_conditional_namespace_import_order(
         *_external_case(source, child=child),
         "pkg.ns.a",
@@ -134,6 +137,7 @@ def _dataclass_result(source, *, decorate=False, external=True, child=None):
         target_python_version=(3, 15),
         assume_passive_external_imports=external,
         assume_frozen_dataclass_decoration=decorate,
+        assumed_external_callable_effects=assumed_effects,
     )
 
 
@@ -1034,6 +1038,10 @@ def test_p8_public_defaultless_field_order(class_body, expected_outcome):
         + "import pkg.ns.b\n",
         decorate=True,
         child="pass\n",
+        assumed_effects={
+            ("dataclasses", "field"):
+                "PASSIVE_DEFAULTLESS_DATACLASS_FIELD",
+        },
     )
 
     assert result.outcome == expected_outcome
@@ -1129,6 +1137,9 @@ def test_p9_i1_source_bound_decorator_identity(
         decorate=True,
         external=True,
         child=child,
+        assumed_effects={
+            ("builtins", "property"): "PASSIVE_PROPERTY",
+        },
     )
 
     assert result.outcome == (
@@ -1151,6 +1162,11 @@ def test_p9_i1_source_bound_decorator_identity(
     assert model.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        + (
+            "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
+            if model.assumed_external_call_effects
+            else ""
+        )
     )
     assert model.builtin_environment_precondition == (
         "CONVENTIONAL_BUILTINS_ASSUMED_NOT_RUNTIME_ATTESTED"
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index f8e38eb..4f0a9d2 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -784,6 +784,10 @@ def _r11_module_result(
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=assume,
+        _assumed_external_callable_effects={
+            ("dataclasses", "field"):
+                "PASSIVE_DEFAULTLESS_DATACLASS_FIELD",
+        },
     )
 
 
@@ -2975,6 +2979,10 @@ def _p8_field_result(class_body, *, import_line=None, prelude=""):
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("dataclasses", "field"):
+                "PASSIVE_DEFAULTLESS_DATACLASS_FIELD",
+        },
     )
 
 
@@ -3241,6 +3249,9 @@ def test_p9_i1_known_builtin_decorator_identity(
         _compile_on_first_import=True,
         _assume_passive_external_imports=True,
         _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects={
+            ("builtins", "property"): "PASSIVE_PROPERTY",
+        },
     )
 
     assert model.outcome == (
@@ -3249,6 +3260,11 @@ def test_p9_i1_known_builtin_decorator_identity(
     assert model.evidence_scope == (
         "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
         "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+        + (
+            "|EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
+            if model.assumed_external_call_effects
+            else ""
+        )
     )
     assert (
         model.builtin_environment_precondition
diff --git a/tests/test_cycle_semantics_external_call_effects.py b/tests/test_cycle_semantics_external_call_effects.py
new file mode 100644
--- /dev/null
+++ b/tests/test_cycle_semantics_external_call_effects.py
@@ -0,0 +1,176 @@
+import ast
+
+from contextor.core.cycle_semantics.package_model import (
+    evaluate_package_import_order,
+)
+
+
+FIELD_EFFECT = "PASSIVE_DEFAULTLESS_DATACLASS_FIELD"
+PROPERTY_EFFECT = "PASSIVE_PROPERTY"
+
+
+def _run(source, effects=None):
+    return evaluate_package_import_order(
+        {
+            "pkg.__init__": ast.parse(source),
+            "pkg.child": ast.parse(
+                "from pkg import C\n"
+            ),
+        },
+        "pkg",
+        annotation_semantics="DEFERRED",
+        _compile_on_first_import=True,
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+        _assumed_external_callable_effects=effects,
+    )
+
+
+def _source(import_line, default="field()"):
+    return (
+        import_line
+        + "@dataclass(frozen=True)\n"
+        + "class C:\n"
+        + "    x: int = "
+        + default
+        + "\n"
+    )
+
+
+def test_import_success_is_not_call_effect_proof():
+    result = _run(
+        _source(
+            "from dataclasses import dataclass, field\n"
+        )
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_external_call_effects == ()
+    assert not any(
+        event.operation
+        == "ASSUMED_FROZEN_DATACLASS_DECORATION"
+        for event in result.events
+    )
+
+
+def test_declared_effect_preserves_field():
+    result = _run(
+        _source(
+            "from dataclasses import dataclass, field\n",
+            "field(hash=False, compare=False)",
+        ),
+        {("dataclasses", "field"): FIELD_EFFECT},
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert len(result.assumed_external_call_effects) == 1
+    row = result.assumed_external_call_effects[0]
+    assert (
+        row.import_module,
+        row.imported_symbol,
+        row.effect,
+    ) == (
+        "dataclasses",
+        "field",
+        FIELD_EFFECT,
+    )
+    assert (
+        "EXTERNAL_CALL_EFFECT_ASSUMED_NOT_RUNTIME_ATTESTED"
+        in result.evidence_scope
+    )
+
+
+def test_declared_effect_is_independent_of_import_name():
+    result = _run(
+        _source(
+            "from dataclasses import dataclass\n"
+            "from some_external_module import factory as field\n"
+        ),
+        {
+            ("some_external_module", "factory"):
+                FIELD_EFFECT,
+        },
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert (
+        result.assumed_external_call_effects[0].import_module
+        == "some_external_module"
+    )
+
+
+def test_rebinding_invalidates_callable_fact():
+    result = _run(
+        _source(
+            "from dataclasses import dataclass, field\n"
+            "field = None\n"
+        ),
+        {("dataclasses", "field"): FIELD_EFFECT},
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_external_call_effects == ()
+
+
+def test_wrong_effect_does_not_authorize_call():
+    result = _run(
+        _source(
+            "from dataclasses import dataclass, field\n"
+        ),
+        {("dataclasses", "field"): PROPERTY_EFFECT},
+    )
+
+    assert result.outcome == "UNKNOWN"
+
+
+def test_invalid_effect_contract_is_unknown():
+    result = _run(
+        _source(
+            "from dataclasses import dataclass, field\n"
+        ),
+        {("dataclasses", "field"): "UNKNOWN_EFFECT"},
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert result.assumed_external_call_effects == ()
+
+
+def test_imported_property_needs_own_effect_proof():
+    source = (
+        "from dataclasses import dataclass\n"
+        "from builtins import property as prop\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+        "    @prop\n"
+        "    def value(self):\n"
+        "        return 1\n"
+    )
+
+    without = _run(source)
+    with_contract = _run(
+        source,
+        {("builtins", "property"): PROPERTY_EFFECT},
+    )
+
+    assert without.outcome == "UNKNOWN"
+    assert with_contract.outcome == "MODEL_PASS"
+    assert (
+        with_contract.assumed_external_call_effects[0].effect
+        == PROPERTY_EFFECT
+    )
+
+
+def test_conventional_builtin_property_remains():
+    result = _run(
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class C:\n"
+        "    x: int\n"
+        "    @property\n"
+        "    def value(self):\n"
+        "        return 1\n"
+    )
+
+    assert result.outcome == "MODEL_PASS"
+    assert result.assumed_external_call_effects == ()
```

## WERDYKT

**PASS** — dwa wskazane zastąpienia wykonane, wszystkie cztery ukierunkowane grupy testów przeszły, LIVE źródeł i testów zsynchronizowany, składnia świeża bez błędów. Założony efekt zewnętrznego Call pozostaje warunkowy, niepotwierdzony przez runtime.
