# P3-D3-CONT — semantic metaclass selection

## FILES_CHANGED

- `contextor/core/cycle_semantics/package_model.py`
- `tests/test_cycle_semantics_passive_classes.py`

`walkthrough.md` jest raportem, bez CHANGELOG, FULL, restartu, commitu, push ani zmiany historii Git. HEAD: `f309f10f4665f6c44c0c19727378c033f2a62769`. Przed tym etapem oba pliki source/test zawierały niezapisane w commicie P3-D1F/D2; zachowane. FULL_DIFFS poniżej obejmuje całe aktualne różnice względem HEAD, wraz z tym stanem wejściowym.

## PREVIOUS_PREFLIGHT_REUSED

P3-D3 preflight w poprzednim etapie: canonical owner `package_model.py`, Contextor revision 1236, `_ClassFact` i PREPARE/DEFINE przejrzane. Kontynuowano od tego punktu. Lokalnego `AGENTS.md` w katalogu repo brak; obowiązują dostarczone w rozmowie zasady, szczególnie pkt 15. Poza wcześniejszym discovery pobrano Contextor symbol lineage, implementację i blast radius. Statyczny consumer `_ClassFact` to moduł testowy; dynamiczne użycia nie są kompletnie reprezentowane przez graf.

## TYPE_BASE_CLASS_FACT

CODE_PATH_PROVED: dodano `builtins.type` do istniejącego katalogu `_ClassFact`: identity, bezpośrednią bazę object, MRO type/object, metaclass_identity type i dodatni dowód standardowego tworzenia. PREPARE rozwiązuje `type` zwykłą ścieżką baz. Lokalnie przesłonięte `type` pozostaje UNKNOWN. CPython 3.15.2 witness A potwierdza `class Meta(type): pass`, `type(Meta) is type` i MRO Meta/type/object.

## METACLASS_PASSIVITY_PROOF

CODE_PATH_PROVED: nowe frozen pole `passive_metaclass_creation` ma domyślnie False; True ma builtin type oraz źródłowa klasa z jedną bazą, udowodnionym łańcuchem do type, pasywną bazą metaklasową i ciałem ograniczonym do pass/pierwszego literalnego docstring. Kontrakt `_safe_passive_class_definition` nadal wyklucza niedozwolone dekoratory, type params i keywordy. Bezpieczna zwykła metoda w ciele nie daje metaklasowego dowodu. `safe_to_subclass` pozostaje osobnym faktem. Nieznane własne `__prepare__`, `__new__`, `__init__`, `__call__`, `__getattribute__` i inne metody/atrybuty blokują użycie jako metaklasy; `__call__` nie jest wywoływane przez samą definicję klasy.

## METACLASS_SELECTION

CODE_PATH_PROVED: PREPARE bierze snapshot baz, rozwiązuje jawne `metaclass=Name` z aktualnego namespace lub dopuszczonego builtin katalogu, pobiera metaclass_identity baz, wymaga faktów po identity, wybiera jedyną najbardziej pochodną kandydaturę na podstawie MRO i wymaga jej pasywnego dowodu. Konflikt lub brak faktu daje UNKNOWN przed DEFINE. Wybrana metaklasa jest w snapshot przed ciałem klasy. DEFINE sprawdza snapshot, safe_to_subclass, ograniczenia baz wyjątku i C3, zapisuje rzeczywistą tożsamość metaklasy i wiąże klasę dopiero na końcu. Pasywna metaklasa nie omija innych bramek.

## IDENTITY_AND_REBINDING

Lokalny rejestr faktów według identity żyje wyłącznie w jednej ewaluacji. ALIAS, FROM i obsługiwany ATTR przenoszą sam obiekt faktu; redefinicja nazwy tworzy nowe identity bez utraty starego faktu. Świadki F/G/H weryfikują alias, FROM i stary alias po redefinicji. Brak globalnego cache i importowania analizowanego kodu przez evaluator.

## REENTRANT_K_L_WITNESSES

Naprawiono błędne cytowanie z R2 poprzez dwa syntetyczne pakiety w testach. Każdy runtime witness uruchamia osobny CPython 3.15.2 `-I -B` subprocess. K: import FROM podczas ciała C, przed końcowym związaniem, zwraca `EARLY_BINDING_HAZARD` w modelu; CPython zgłasza `cannot import name 'C'`; nie ma zdarzenia DEFINE dla C. L: import FROM po związaniu C, MODEL_PASS; CPython widzi ten sam obiekt C i `type(C) is Meta`. Events modelu zawierają DEFINE Meta i C przed importem L.

## CPYTHON315_DIFFERENTIAL

12 pozytywnych przypadków A-L ma po jednym syntetycznym pakiecie, ordinary MODEL_PASS, osobnym izolowanym subprocess CPython 3.15.2 i asercjach rzeczywistego typu/MRO tam, gdzie dotyczy. A: Meta(type); B: jawna Meta; C: dziedziczenie C; D: N(Meta); E: użycie N; F: alias; G: FROM; H: stary alias po redefinicji; I: jawne type z bazą o metaklasie Meta; J: wspólna Meta; K: wybór N ponad Meta; L: jawna Meta zgodna z bazą. Wszystkie przeszły. Wynik subprocess to bezpośredni CPython witness, a MODEL_PASS to wynik osobnego evaluatora.

## NEGATIVE_REGRESSIONS

7 nowych przypadków metod/atrybutów metaklasy: UNKNOWN przed DEFINE C. Wcześniejsze P3-D1/D1F/D2 obejmują konflikt metaklas, dynamiczne bazy, `__mro_entries__`, shadowed type, `__set_name__`, `__init_subclass__`, nazwy specjalne i C3. Jeden wcześniejszy przypadek `class Meta(type): pass; class Child(metaclass=Meta): pass` przeniesiono z oczekiwanego UNKNOWN do pozytywnego P3-D3, zgodnie z nowym kontraktem. Nie promowano conditional dataclass do ordinary MODEL_PASS.

## TARGETED_TESTS

- `tests/test_cycle_semantics_passive_classes.py`: 87 passed.
- `tests/test_cycle_semantics_package_model.py -k 'r8 or r9 or r10 or r11'`: 94 passed, 113 deselected.
- `git diff --check`: bez błędów.

## MCP_POST_CHANGE_AUDIT

Contextor po zmianach: canonical revision 1241, `workspace_sync=verified` osobno dla production i test, syntax errors=0, 16 structural DFS paths, 1 soft-dependent potential SCC. Liczby są takie same jak w preflight, ale nie przeprowadzono porównania tożsamości wszystkich ścieżek; brak nowego cyklu nie jest osobno udowodniony. `cycle_semantics=stale`; nie wykonano FULL, więc runtime adoption i świeża projekcja ostrzeżeń pozostają UNKNOWN. Nie użyto `update_file`.

## REMAINING_UNKNOWN_BOUNDARIES

Niestandardowe lub zewnętrzne metaklasy, wiele baz bez dodatniego dowodu, dynamiczne `__mro_entries__`, modyfikacje metaklas poza obsługiwanym modelem, class decorators poza istniejącym warunkowym kontraktem, zmienione `__build_class__` i runtime builtins. Statyczny MODEL_PASS jest zależny od istniejącego P2 conventional-builtins precondition, a nie runtime attestation. Nie certyfikowano persistent MCP process adoption.

## FULL_DIFFS

Poniżej pełne `git diff --no-ext-diff -- contextor/core/cycle_semantics/package_model.py tests/test_cycle_semantics_passive_classes.py` względem HEAD. Uwzględnia poprzednie niezatwierdzone P3-D1F/D2.

```diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 8cb970b..78a68ab 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -59,10 +59,12 @@ class _ClassFact:
 
     identity: str
     origin: str
-    direct_base: str | None
+    direct_bases: tuple[str, ...]
+    linear_mro: tuple[str, ...]
     metaclass_identity: str
     defines_init_subclass: bool
     safe_to_subclass: bool
+    passive_metaclass_creation: bool = False
 
 
 def _safe_class_namespace_value(value: object) -> bool:
@@ -76,23 +78,102 @@ def _safe_class_namespace_value(value: object) -> bool:
 
 _BUILTIN_TYPE_ID = "builtins.type"
 _BUILTIN_CLASS_FACTS = {
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
     "object": _ClassFact(
-        "builtins.object", "BUILTIN", None,
-        _BUILTIN_TYPE_ID, False, True,
+        identity="builtins.object",
+        origin="BUILTIN",
+        direct_bases=(),
+        linear_mro=("builtins.object",),
+        metaclass_identity=_BUILTIN_TYPE_ID,
+        defines_init_subclass=False,
+        safe_to_subclass=True,
     ),
     "BaseException": _ClassFact(
-        "builtins.BaseException", "BUILTIN", "builtins.object",
-        _BUILTIN_TYPE_ID, False, True,
+        identity="builtins.BaseException",
+        origin="BUILTIN",
+        direct_bases=("builtins.object",),
+        linear_mro=("builtins.BaseException", "builtins.object"),
+        metaclass_identity=_BUILTIN_TYPE_ID,
+        defines_init_subclass=False,
+        safe_to_subclass=True,
     ),
     "Exception": _ClassFact(
-        "builtins.Exception", "BUILTIN", "builtins.BaseException",
-        _BUILTIN_TYPE_ID, False, True,
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
     ),
     "ValueError": _ClassFact(
-        "builtins.ValueError", "BUILTIN", "builtins.Exception",
-        _BUILTIN_TYPE_ID, False, True,
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
     ),
 }
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
 
 
 @dataclass(frozen=True)
@@ -133,7 +214,9 @@ class _Step:
     annotation_builtin_names: tuple[str, ...] = ()
     definition_id: str | None = None
     defines_init_subclass: bool = False
-    explicit_type_metaclass: bool = False
+    base_names: tuple[str, ...] = ()
+    explicit_metaclass_name: str | None = None
+    passive_metaclass_body: bool = False
 
 
 @dataclass
@@ -362,25 +445,38 @@ def _safe_passive_class_definition(
         )
     )
 
-    explicit_type_metaclass = (
+    explicit_named_metaclass = (
         len(statement.keywords) == 1
         and statement.keywords[0].arg == "metaclass"
         and type(statement.keywords[0].value) is ast.Name
-        and statement.keywords[0].value.id == "type"
     )
 
     if (
         not statement.name.isidentifier()
         or statement.name.startswith("__")
+        or any(
+            isinstance(
+                item,
+                (ast.FunctionDef, ast.AsyncFunctionDef),
+            )
+            and item.name in {
+                "__slots__",
+                "__qualname__",
+                "__classcell__",
+            }
+            for item in statement.body
+        )
         or (
             bool(statement.bases)
             and (
                 conditional_dataclass
-                or len(statement.bases) != 1
-                or type(statement.bases[0]) is not ast.Name
+                or any(
+                    type(base) is not ast.Name
+                    for base in statement.bases
+                )
             )
         )
-        or (bool(statement.keywords) and not explicit_type_metaclass)
+        or (bool(statement.keywords) and not explicit_named_metaclass)
         or (conditional_dataclass and statement.keywords)
         or (
             bool(statement.decorator_list)
@@ -1050,6 +1146,16 @@ def _compile(
                 steps.append(_Step("BIND", binding=stmt.target.id))
 
         elif isinstance(stmt, ast.ClassDef):
+            passive_metaclass_body = all(
+                type(item) is ast.Pass
+                or (
+                    index == 0
+                    and type(item) is ast.Expr
+                    and type(item.value) is ast.Constant
+                    and type(item.value.value) is str
+                )
+                for index, item in enumerate(stmt.body)
+            )
             conditional_dataclass = (
                 assume_frozen_dataclass
                 and bool(stmt.decorator_list)
@@ -1080,11 +1186,19 @@ def _compile(
                         target=(
                             stmt.bases[0].id if stmt.bases else None
                         ),
+                        base_names=tuple(
+                            base.id
+                            for base in stmt.bases
+                        ),
                         binding=stmt.name,
                         source_line=stmt.lineno,
                         source_column=stmt.col_offset,
                         definition_id=definition_id,
-                        explicit_type_metaclass=bool(stmt.keywords),
+                        explicit_metaclass_name=(
+                            stmt.keywords[0].value.id
+                            if stmt.keywords else None
+                        ),
+                        passive_metaclass_body=passive_metaclass_body,
                     )
                 )
 
@@ -1204,6 +1318,7 @@ def _compile(
                             f"{logical}:{stmt.lineno}:{stmt.col_offset}"
                         ),
                         defines_init_subclass=has_init_subclass,
+                        passive_metaclass_body=passive_metaclass_body,
                     )
                 )
 
@@ -1731,7 +1846,12 @@ def evaluate_package_import_order(
         name: {}
         for name in programs
     }
-    prepared_class_bases: dict[str, _ClassFact] = {}
+    prepared_class_bases: dict[
+        str, tuple[tuple[_ClassFact, ...], _ClassFact]
+    ] = {}
+    class_facts_by_identity: dict[str, _ClassFact] = {
+        fact.identity: fact for fact in _BUILTIN_CLASS_FACTS.values()
+    }
 
     function_definitions: dict[
         str,
@@ -2298,39 +2418,118 @@ def evaluate_package_import_order(
                 return result("UNKNOWN", module, step.binding)
 
             if (
-                step.explicit_type_metaclass
+                step.explicit_metaclass_name == "type"
                 and "type" in namespaces[module]
             ):
                 return result("UNKNOWN", module, "type")
 
-            if step.target is None:
-                base_fact = _BUILTIN_CLASS_FACTS["object"]
-            elif step.target in namespaces[module]:
-                base_fact = namespaces[module][step.target]
+            base_names = step.base_names or (
+                (step.target,) if step.target is not None else ()
+            )
+            if not base_names:
+                base_facts = (_BUILTIN_CLASS_FACTS["object"],)
             else:
-                base_fact = _BUILTIN_CLASS_FACTS.get(step.target)
+                resolved_base_facts = []
+                for base_name in base_names:
+                    if base_name in namespaces[module]:
+                        base_fact = namespaces[module][base_name]
+                    else:
+                        base_fact = _BUILTIN_CLASS_FACTS.get(base_name)
 
-            if (
-                not isinstance(base_fact, _ClassFact)
-                or base_fact.metaclass_identity != _BUILTIN_TYPE_ID
-            ):
-                return result(
-                    "UNKNOWN",
-                    module,
-                    step.target,
-                )
+                    if (
+                        not isinstance(base_fact, _ClassFact)
+                        or type(base_fact.linear_mro) is not tuple
+                        or not base_fact.linear_mro
+                        or base_fact.linear_mro[0]
+                        != base_fact.identity
+                        or base_fact.linear_mro[-1]
+                        != _BUILTIN_CLASS_FACTS["object"].identity
+                        or any(
+                            type(identity) is not str
+                            for identity in base_fact.linear_mro
+                        )
+                        or len(set(base_fact.linear_mro))
+                        != len(base_fact.linear_mro)
+                    ):
+                        return result(
+                            "UNKNOWN",
+                            module,
+                            base_name,
+                        )
+
+                    resolved_base_facts.append(base_fact)
 
-            prepared_class_bases[step.definition_id] = base_fact
+                base_facts = tuple(resolved_base_facts)
+
+            candidate_ids = [base.metaclass_identity for base in base_facts]
+            if step.explicit_metaclass_name is not None:
+                name = step.explicit_metaclass_name
+                explicit = (
+                    namespaces[module][name]
+                    if name in namespaces[module]
+                    else _BUILTIN_CLASS_FACTS.get(name)
+                )
+                if not isinstance(explicit, _ClassFact):
+                    return result("UNKNOWN", module, name)
+                candidate_ids.insert(0, explicit.identity)
+            if not candidate_ids:
+                candidate_ids = [_BUILTIN_TYPE_ID]
+
+            candidates = [
+                class_facts_by_identity.get(identity)
+                for identity in candidate_ids
+            ]
+            if any(not isinstance(candidate, _ClassFact) for candidate in candidates):
+                return result("UNKNOWN", module, step.binding)
+            winners = [
+                candidate for candidate in candidates
+                if all(
+                    other.identity in candidate.linear_mro
+                    for other in candidates
+                )
+            ]
+            winner_ids = {candidate.identity for candidate in winners}
+            if len(winner_ids) != 1:
+                return result("UNKNOWN", module, step.binding)
+            selected = winners[0]
+            if not selected.passive_metaclass_creation:
+                return result("UNKNOWN", module, step.binding)
+            prepared_class_bases[step.definition_id] = (base_facts, selected)
 
         elif step.op == "DEFINE_PASSIVE_CLASS":
-            base_fact = prepared_class_bases.pop(
+            prepared = prepared_class_bases.pop(
                 step.definition_id or "",
                 None,
             )
-            if not isinstance(base_fact, _ClassFact):
+            if (
+                not isinstance(prepared, tuple)
+                or len(prepared) != 2
+                or not isinstance(prepared[0], tuple)
+                or not prepared[0]
+                or not isinstance(prepared[1], _ClassFact)
+                or any(
+                    not isinstance(base_fact, _ClassFact)
+                    for base_fact in prepared[0]
+                )
+            ):
+                return result("UNKNOWN", module, step.binding)
+            base_facts, selected_metaclass = prepared
+
+            if len({base.identity for base in base_facts}) != len(base_facts):
                 return result("UNKNOWN", module, step.binding)
 
-            if not base_fact.safe_to_subclass:
+            if any(not base.safe_to_subclass for base in base_facts):
+                return result("UNKNOWN", module, step.binding)
+
+            if len(base_facts) > 1 and any(
+                identity in _BUILTIN_EXCEPTION_CLASS_IDENTITIES
+                for base in base_facts
+                for identity in base.linear_mro
+            ):
+                return result("UNKNOWN", module, step.binding)
+
+            inherited_mro = _merge_class_mros(base_facts)
+            if inherited_mro is None:
                 return result("UNKNOWN", module, step.binding)
 
             identity = step.definition_id
@@ -2340,11 +2539,21 @@ def evaluate_package_import_order(
             class_fact = _ClassFact(
                 identity=identity,
                 origin="INDEXED_SOURCE",
-                direct_base=base_fact.identity,
-                metaclass_identity=_BUILTIN_TYPE_ID,
+                direct_bases=tuple(
+                    base.identity for base in base_facts
+                ),
+                linear_mro=(identity, *inherited_mro),
+                metaclass_identity=selected_metaclass.identity,
                 defines_init_subclass=step.defines_init_subclass,
                 safe_to_subclass=not step.defines_init_subclass,
+                passive_metaclass_creation=(
+                    len(base_facts) == 1
+                    and _BUILTIN_TYPE_ID in base_facts[0].linear_mro
+                    and base_facts[0].passive_metaclass_creation
+                    and step.passive_metaclass_body
+                ),
             )
+            class_facts_by_identity[identity] = class_fact
             namespaces[module][step.binding] = (
                 class_fact
             )
diff --git a/tests/test_cycle_semantics_passive_classes.py b/tests/test_cycle_semantics_passive_classes.py
index 979dbf2..c59c20e 100644
--- a/tests/test_cycle_semantics_passive_classes.py
+++ b/tests/test_cycle_semantics_passive_classes.py
@@ -9,6 +9,8 @@ from dataclasses import asdict
 import pytest
 
 from contextor.core.cycle_semantics.package_model import (
+    _ClassFact,
+    _merge_class_mros,
     evaluate_package_import_order,
 )
 
@@ -23,7 +25,7 @@ def _model(sources, entry):
     )
 
 
-def _actual(tmp_path, sources, entry):
+def _actual(tmp_path, sources, entry, probe=""):
     for module, source in sources.items():
         parts = module.split(".")
         path = tmp_path.joinpath(
@@ -50,7 +52,8 @@ def _actual(tmp_path, sources, entry):
             (
                 "import importlib,sys;"
                 "sys.path.insert(0,sys.argv[1]);"
-                "importlib.import_module(sys.argv[2])"
+                "m=importlib.import_module(sys.argv[2]);"
+                + probe
             ),
             str(tmp_path),
             entry,
@@ -439,16 +442,6 @@ def test_p3_d1_proven_class_bases_match_cpython(
             "class Child(Base): pass",
             False,
         ),
-        (
-            "class Meta(type): pass\n"
-            "class Child(metaclass=Meta): pass",
-            True,
-        ),
-        (
-            "class Left: pass\nclass Right: pass\n"
-            "class Child(Left, Right): pass",
-            True,
-        ),
         (
             "class A: pass\nclass B: pass\nclass C(A, B): pass\n"
             "class D(B, A): pass\nclass E(C, D): pass",
@@ -577,3 +570,487 @@ def test_p3_d1_unknown_set_name_descriptor_stays_unknown(tmp_path):
     process = _actual(tmp_path, sources, "pkg.a")
     assert process.returncode != 0
     assert "descriptor hook" in process.stderr
+
+
+@pytest.mark.parametrize(
+    ("name", "terminal_error"),
+    [
+        ("__slots__", "TypeError: 'function' object is not iterable"),
+        (
+            "__qualname__",
+            "TypeError: type __qualname__ must be a str, not function",
+        ),
+        (
+            "__classcell__",
+            "TypeError: __classcell__ must be a nonlocal cell, "
+            "not <class 'function'>",
+        ),
+    ],
+)
+def test_p3_d1f_type_new_reserved_method_names_are_unknown(
+    tmp_path, name, terminal_error,
+):
+    class_name = {
+        "__slots__": "A",
+        "__qualname__": "B",
+        "__classcell__": "C",
+    }[name]
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            f"class {class_name}:\n"
+            f"    def {name}(self):\n"
+            "        pass"
+        ),
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "UNKNOWN"
+    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == class_name
+        for event in result.events
+    )
+
+    process = _actual(tmp_path, sources, "pkg.a")
+
+    assert process.returncode != 0
+    assert terminal_error in process.stderr
+
+
+def test_p3_d1f_reserved_method_name_cycle_does_not_export_class(
+    tmp_path,
+):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class A:\n"
+            "    def __slots__(self):\n"
+            "        pass\n"
+            "from pkg.b import B"
+        ),
+        "pkg.b": "from pkg.a import A\nclass B: pass",
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "UNKNOWN"
+    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "A"
+        for event in result.events
+    )
+    assert not any(
+        event.operation == "FROM"
+        and event.module == "pkg.b"
+        and event.symbol == "A"
+        for event in result.events
+    )
+
+    process = _actual(tmp_path, sources, "pkg.a")
+
+    assert process.returncode != 0
+    assert "TypeError: 'function' object is not iterable" in process.stderr
+
+
+@pytest.mark.parametrize(
+    ("method", "body"),
+    [("__init__", "pass"), ("__repr__", 'return "C"')],
+)
+def test_p3_d1f_regular_dunder_methods_remain_passive(
+    tmp_path, method, body,
+):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class C:\n"
+            f"    def {method}(self):\n"
+            f"        {body}"
+        ),
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "C"
+        for event in result.events
+    )
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+@pytest.mark.parametrize(
+    ("entry", "source", "extra", "class_symbol"),
+    [
+        (
+            "pkg.a",
+            "class Left: pass\nclass Right: pass\n"
+            "class Child(Left, Right): pass",
+            {},
+            "Child",
+        ),
+        (
+            "pkg.a",
+            "class Left: pass\nclass Right: pass\n"
+            "class Child(Left, Right, metaclass=type): pass",
+            {},
+            "Child",
+        ),
+        (
+            "pkg.a",
+            "class First: pass\nclass Second: pass\n"
+            "class Third: pass\n"
+            "class Child(First, Second, Third): pass",
+            {},
+            "Child",
+        ),
+        (
+            "pkg.a",
+            "class Root: pass\nclass Left(Root): pass\n"
+            "class Right(Root): pass\n"
+            "class Diamond(Left, Right): pass",
+            {},
+            "Diamond",
+        ),
+        (
+            "pkg.a",
+            "class First: pass\nclass Second: pass\n"
+            "AliasFirst = First\nAliasSecond = Second\n"
+            "class Child(AliasFirst, AliasSecond): pass",
+            {},
+            "Child",
+        ),
+        (
+            "pkg.use",
+            "from pkg.base import First, Second\n"
+            "class Child(First, Second): pass",
+            {"pkg.base": "class First: pass\nclass Second: pass"},
+            "Child",
+        ),
+        (
+            "pkg.a",
+            "class Base: pass\nclass Child(Base, object): pass",
+            {},
+            "Child",
+        ),
+        (
+            "pkg.a",
+            "class Base: pass\nOldBase = Base\n"
+            "class Base: pass\nclass Child(OldBase, Base): pass",
+            {},
+            "Child",
+        ),
+        (
+            "pkg.a",
+            "class Left: pass\nfrom pkg.b import Right\n"
+            "class Child(Left, Right): pass",
+            {
+                "pkg.b": (
+                    "from pkg.a import Left\nclass Right: pass"
+                ),
+            },
+            "Child",
+        ),
+    ],
+)
+def test_p3_d2_supported_multiple_inheritance_matches_cpython(
+    tmp_path, entry, source, extra, class_symbol,
+):
+    sources = {"pkg.__init__": "pass", entry: source, **extra}
+
+    result = _model(sources, entry)
+
+    assert result.outcome == "MODEL_PASS"
+    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == class_symbol
+        for event in result.events
+    )
+    assert _actual(tmp_path, sources, entry).returncode == 0
+
+
+@pytest.mark.parametrize(
+    ("source", "extra", "failed_class", "runtime_error"),
+    [
+        (
+            "class Base: pass\nclass Child(Base): pass\n"
+            "class Broken(object, Child): pass",
+            {},
+            "Broken",
+            None,
+        ),
+        (
+            "class Base: pass\nAlias = Base\n"
+            "class Broken(Base, Alias): pass",
+            {},
+            "Broken",
+            None,
+        ),
+        (
+            "from pkg.base import Base as Left\n"
+            "from pkg.base import Base as Right\n"
+            "class Broken(Left, Right): pass",
+            {"pkg.base": "class Base: pass"},
+            "Broken",
+            None,
+        ),
+        (
+            "class Root: pass\nclass Left(Root): pass\n"
+            "class Right(Root): pass\n"
+            "class First(Left, Right): pass\n"
+            "class Second(Right, Left): pass\n"
+            "class Broken(First, Second): pass",
+            {},
+            "Broken",
+            None,
+        ),
+        (
+            "Base = 7\nclass Broken(Base, object): pass",
+            {},
+            "Broken",
+            None,
+        ),
+        (
+            "class Broken(SyntaxError, OSError): pass",
+            {},
+            "Broken",
+            "multiple bases have instance lay-out conflict",
+        ),
+    ],
+)
+def test_p3_d2_unproven_or_invalid_multiple_inheritance_stays_unknown(
+    tmp_path, source, extra, failed_class, runtime_error,
+):
+    sources = {"pkg.__init__": "pass", "pkg.a": source, **extra}
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "UNKNOWN"
+    assert result.evidence_scope == "RESTRICTED_REGULAR_PACKAGE_MODEL"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == failed_class
+        for event in result.events
+    )
+
+    process = _actual(tmp_path, sources, "pkg.a")
+    assert process.returncode != 0
+    if runtime_error is not None:
+        assert runtime_error in process.stderr
+
+
+def test_p3_d2_multiple_exception_bases_remain_conservatively_unknown(
+    tmp_path,
+):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "class CustomError(ValueError, Exception): pass",
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "UNKNOWN"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == "CustomError"
+        for event in result.events
+    )
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+def test_p3_d2_c3_merge_preserves_order_and_common_ancestor():
+    object_fact = _ClassFact(
+        identity="builtins.object",
+        origin="BUILTIN",
+        direct_bases=(),
+        linear_mro=("builtins.object",),
+        metaclass_identity="builtins.type",
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    )
+    root = _ClassFact(
+        identity="pkg.root:1:0",
+        origin="INDEXED_SOURCE",
+        direct_bases=("builtins.object",),
+        linear_mro=("pkg.root:1:0", "builtins.object"),
+        metaclass_identity="builtins.type",
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    )
+    left_identity = "pkg.left:1:0"
+    left = _ClassFact(
+        identity=left_identity,
+        origin="INDEXED_SOURCE",
+        direct_bases=(root.identity,),
+        linear_mro=(left_identity, root.identity, "builtins.object"),
+        metaclass_identity="builtins.type",
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    )
+    right = _ClassFact(
+        identity="pkg.right:1:0",
+        origin="INDEXED_SOURCE",
+        direct_bases=(root.identity,),
+        linear_mro=("pkg.right:1:0", root.identity, "builtins.object"),
+        metaclass_identity="builtins.type",
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    )
+
+    assert _merge_class_mros((left, right)) == (
+        left.identity,
+        right.identity,
+        root.identity,
+        "builtins.object",
+    )
+    assert _merge_class_mros((root, object_fact)) == (
+        root.identity,
+        "builtins.object",
+    )
+
+
+def test_p3_d2_c3_merge_rejects_conflicting_parent_order():
+    first = _ClassFact(
+        identity="pkg.first:1:0",
+        origin="INDEXED_SOURCE",
+        direct_bases=("builtins.object",),
+        linear_mro=("pkg.first:1:0", "builtins.object"),
+        metaclass_identity="builtins.type",
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    )
+    second = _ClassFact(
+        identity="pkg.second:1:0",
+        origin="INDEXED_SOURCE",
+        direct_bases=("builtins.object",),
+        linear_mro=("pkg.second:1:0", "builtins.object"),
+        metaclass_identity="builtins.type",
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    )
+    left_order = _ClassFact(
+        identity="pkg.left_order:1:0",
+        origin="INDEXED_SOURCE",
+        direct_bases=(first.identity, second.identity),
+        linear_mro=(
+            "pkg.left_order:1:0",
+            first.identity,
+            second.identity,
+            "builtins.object",
+        ),
+        metaclass_identity="builtins.type",
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    )
+    right_order = _ClassFact(
+        identity="pkg.right_order:1:0",
+        origin="INDEXED_SOURCE",
+        direct_bases=(second.identity, first.identity),
+        linear_mro=(
+            "pkg.right_order:1:0",
+            second.identity,
+            first.identity,
+            "builtins.object",
+        ),
+        metaclass_identity="builtins.type",
+        defines_init_subclass=False,
+        safe_to_subclass=True,
+    )
+
+    assert _merge_class_mros((left_order, right_order)) is None
+
+
+@pytest.mark.parametrize(
+    ("source", "extra", "probe"),
+    [
+        ("class Meta(type): pass", {}, "assert type(m.Meta) is type;assert m.Meta.__mro__==(m.Meta,type,object)"),
+        ("class Meta(type): pass\nclass C(metaclass=Meta): pass", {}, "assert type(m.C) is m.Meta;assert m.C.__mro__==(m.C,object)"),
+        ("class Meta(type): pass\nclass C(metaclass=Meta): pass\nclass D(C): pass", {}, "assert type(m.D) is m.Meta;assert m.D.__mro__==(m.D,m.C,object)"),
+        ("class Meta(type): pass\nclass N(Meta): pass", {}, "assert m.N.__mro__==(m.N,m.Meta,type,object)"),
+        ("class Meta(type): pass\nclass N(Meta): pass\nclass C(metaclass=N): pass", {}, "assert type(m.C) is m.N"),
+        ("class Meta(type): pass\nAlias=Meta\nclass C(metaclass=Alias): pass", {}, "assert type(m.C) is m.Meta"),
+        ("from pkg.meta import Meta\nclass C(metaclass=Meta): pass", {"pkg.meta": "class Meta(type): pass"}, "assert type(m.C) is __import__('pkg.meta',fromlist=['Meta']).Meta"),
+        ("class Meta(type): pass\nOld=Meta\nclass Meta(type): pass\nclass C(metaclass=Old): pass", {}, "assert type(m.C) is m.Old and m.Old is not m.Meta"),
+        ("class Meta(type): pass\nclass A(metaclass=Meta): pass\nclass C(A,metaclass=type): pass", {}, "assert type(m.C) is m.Meta"),
+        ("class Meta(type): pass\nclass A(metaclass=Meta): pass\nclass B(metaclass=Meta): pass\nclass C(A,B): pass", {}, "assert type(m.C) is m.Meta;assert m.C.__mro__==(m.C,m.A,m.B,object)"),
+        ("class Meta(type): pass\nclass N(Meta): pass\nclass A(metaclass=Meta): pass\nclass B(metaclass=N): pass\nclass C(A,B): pass", {}, "assert type(m.C) is m.N"),
+        ("class Meta(type): pass\nclass A(metaclass=Meta): pass\nclass C(A,metaclass=Meta): pass", {}, "assert type(m.C) is m.Meta"),
+    ],
+)
+def test_p3_d3_semantic_metaclass_selection(tmp_path, source, extra, probe):
+    sources = {"pkg.__init__": "pass", "pkg.a": source, **extra}
+    result = _model(sources, "pkg.a")
+    assert result.outcome == "MODEL_PASS", result
+    actual = _actual(tmp_path, sources, "pkg.a", probe)
+    assert actual.returncode == 0, actual.stderr
+
+
+@pytest.mark.parametrize(
+    "body",
+    [
+        "def __prepare__(cls,*args): return {}",
+        "def __new__(cls,*args): return super().__new__(cls,*args)",
+        "def __init__(cls,*args): pass",
+        "def __call__(cls,*args): return super().__call__(*args)",
+        "def __getattribute__(cls,name): return super().__getattribute__(name)",
+        "def method(cls): pass",
+        "flag = 1",
+    ],
+)
+def test_p3_d3_unproved_metaclass_effects_are_unknown(body):
+    source = "class Meta(type):\n    " + body.replace("\n", "\n    ") + "\nclass C(metaclass=Meta): pass"
+    result = _model({"pkg.__init__": "pass", "pkg.a": source}, "pkg.a")
+    assert result.outcome == "UNKNOWN"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS" and event.symbol == "C"
+        for event in result.events
+    )
+
+
+def test_p3_d3_reentrant_before_class_binding(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class Meta(type): pass\n"
+            "class C(metaclass=Meta):\n"
+            "    from pkg.b import Seen"
+        ),
+        "pkg.b": "from pkg.a import C as Seen",
+    }
+    modeled = _model(sources, "pkg.a")
+    assert modeled.outcome == "EARLY_BINDING_HAZARD"
+    assert not any(
+        event.operation == "DEFINE_PASSIVE_CLASS" and event.symbol == "C"
+        for event in modeled.events
+    )
+    actual = _actual(tmp_path, sources, "pkg.a")
+    assert actual.returncode != 0
+    assert "cannot import name 'C'" in actual.stderr
+
+
+def test_p3_d3_import_after_class_binding(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class Meta(type): pass\n"
+            "class C(metaclass=Meta): pass\n"
+            "from pkg.b import Seen"
+        ),
+        "pkg.b": "from pkg.a import C as Seen",
+    }
+    modeled = _model(sources, "pkg.a")
+    assert modeled.outcome == "MODEL_PASS"
+    assert [
+        event.operation for event in modeled.events
+        if event.operation == "DEFINE_PASSIVE_CLASS"
+    ] == ["DEFINE_PASSIVE_CLASS", "DEFINE_PASSIVE_CLASS"]
+    actual = _actual(
+        tmp_path, sources, "pkg.a",
+        "assert m.Seen is m.C;assert type(m.C) is m.Meta",
+    )
+    assert actual.returncode == 0, actual.stderr
```

## FINAL_VERDICT

SOURCE_AND_FOCUSED_REGRESSION_PASS. Semantyczny wybór pasywnej metaklasy jest udowodniony w ograniczonym ordinary modelu przez źródło, negatywne bramki i osobne CPython 3.15.2 witnesses. Nie deklaruje się runtime adoption ani świeżej cycle_semantics bez FULL. STOP.
