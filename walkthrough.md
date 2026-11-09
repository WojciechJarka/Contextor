# P3-D1 — semantyczne wiązanie baz klas

## FILES_CHANGED

- contextor/core/cycle_semantics/package_model.py
- tests/test_cycle_semantics_package_model.py
- tests/test_cycle_semantics_passive_classes.py

Raport walkthrough.md nadpisano dla tego zadania. CHANGELOG.md był zmieniony przed P3-D1 i nie został zmodyfikowany w tym zadaniu. Nie zmieniono publicznego schematu assessment ani dokumentacji MCP.

## OLD_HARDCODE_REMOVED

CHECK_BUILTIN_CLASS_BASE(ValueError) i jego specjalny warunek nie występują już w kompilatorze ani evaluatorze. Walidator akceptuje najwyżej jedną bazę będącą prostym AST Name; jej rzeczywiste wiązanie rozwiązuje evaluator. Katalog faktów builtin obejmuje ograniczone, sprawdzone klasy object, BaseException, Exception, ValueError. type jest rozpoznawany wyłącznie jako udowodniona metaklasa dla dokładnego metaclass=type.

Contextor MCP przed edycją potwierdził lokalizacje _safe_passive_class_definition (296), _compile (m.in. 999–1125), _Step (80), operacje namespace ALIAS/ATTR (2270–2337), importy FROM (1980–2072) i DEFINE_PASSIVE_CLASS (2196–2221). Call-context _compile na rewizji 1225 wskazuje 5 lokalnych caller edges (w tym rekurencję, _compile_reachable_prefix i evaluator) oraz 10 callees; narzędzie jawnie ogranicza zakres do call facts wewnątrz modułu. File-edit context wykazał 22 bezpośrednich konsumentów i 195 test modules w indeksie; żadna zmiana nie dotknęła API assessment. get_symbol_lineage wskazał centralny przepływ namespace i ograniczenie dynamicznego lineage. Nie traktuję niepełnego statycznego call graph jako dowodu o dynamicznych wywołaniach.

## CLASS_IDENTITY_AND_BASE_RESOLUTION

Dodano prywatny, frozen=True _ClassFact: identity definicji, origin BUILTIN/INDEXED_SOURCE, identity bezpośredniej bazy, identity metaklasy, własny __init_subclass__ oraz safe_to_subclass. Identity klasy źródłowej to kwalifikowany moduł i pozycja definicji (linia/kolumna); brak prawidłowej pozycji kończy kompilację w UNKNOWN. Redefinicja tej samej nazwy ma inną pozycję i nowy fakt. Fakt builtin ma stałą identity builtin. Namespace przechowuje fakt, nie tekstową nazwę klasy.

ALIAS, FROM i obsługiwane ATTR zachowują istniejący obiekt faktu (nie tworzą klasy). Rebinding nazwy nie zmienia wcześniej skopiowanego aliasu. Conditional frozen-dataclass marker nadal jest tekstowym markerem wyłącznie dla istniejącego warunkowego przepływu adnotacji i nie jest _ClassFact, więc nie może stać się bazą.

Dla każdej zwykłej klasy compiler emituje PREPARE_PASSIVE_CLASS przed krokami ciała. Evaluator rozwiązuje bazę według kolejności: lokalne namespace (musi zawierać _ClassFact), następnie ograniczony katalog builtin tylko jeżeli nazwa nie jest lokalnie związana; bez jawnej bazy używa faktu object. Fakt bazy jest zapamiętany po identity definicji aż do DEFINE_PASSIVE_CLASS, także gdy ciało zawiesza się na reentrant import. Nazwa klasy pojawia się w module namespace dopiero przy końcowym DEFINE. Wcześniejszy import tej nazwy nadal daje istniejący early-binding hazard.

## METACLASS_PROOF

Każdy obsługiwany fakt ma metaclass identity builtins.type. Zwykła klasa dziedziczy ten dowód z jedynej udowodnionej bazy. Jawne metaclass=type jest dopuszczone tylko dla dokładnego prostego Name i odrzucane jako UNKNOWN, jeśli namespace modułu wcześniej związał type. Inne metaclass keywords nie przechodzą walidacji. Fakt klasy ze źródła nie jest klasyfikowany przez nazwę AST bazy.

Własna metaklasa, konflikt metaklas, więcej niż jedna baza, dynamiczna baza, nierozpoznana nazwa lub lokalny alias, którego wartość nie jest faktem klasy, kończą w UNKNOWN. Evaluator nie wywołuje __prepare__, __new__, __init__ ani analizowanego kodu.

## CLASS_CREATION_EFFECT_BOUNDARY

Compiler nadal dopuszcza tylko ograniczone ciała pasywne. Baza i metaclass=type są rozstrzygane w fazie przygotowania. Importy w ciele pozostają w kolejności wykonywania przed wiązaniem klasy. Dla importów klasowych z indeksowanego źródła evaluator dopuszcza wyłącznie znane proste wartości, moduły, funkcje i fakty klas; nieznany/założony zewnętrzny obiekt skutkuje UNKNOWN, ponieważ mógłby mieć __set_name__. Proste literały i funkcje ograniczonego kompilatora nie tworzą dowolnych deskryptorów.

Fakt nowej klasy zapamiętuje własny hook __init_subclass__. Taka klasa może zostać utworzona na bezpiecznej bazie, ale nie jest uznawana za bezpieczną bazę dla dalszego dziedziczenia. Przy próbie podklasowania faktu z własnym lub odziedziczonym niestandardowym hookiem evaluator zwraca UNKNOWN dopiero przy zakończeniu tworzenia klasy po przetworzeniu modelowanych kroków ciała. Inne niestandardowe hooki, deskryptory i dynamiczne __mro_entries__ nie są uznawane za pasywne.

Standardowy kontrakt środowiska builtins z P2 pozostaje jawny i nieatestowany runtime. Nie zmieniono scenariuszy SCC, kryteriów receipt ani warning eligibility; żaden wynik nie jest certyfikatem wykonania runtime.

## CPYTHON_WITNESSES

Wersja: CPython 3.15.2 z .venv\Scripts\python.exe. Test helper _actual zapisuje syntetyczne pakiety do katalogu tymczasowego i wykonuje import wyłącznie w subprocess sys.executable -I -B -c; analizowany pakiet nie jest importowany przez proces testowy. Dla każdej nowo przyjętej ścieżki pozytywnej sprawdzono ordinary evaluator oraz rzeczywisty import: brak jawnej bazy, object, Exception, BaseException, ValueError, user class jako baza, alias, baza z indeksowanego modułu, metaclass=type i alias do starej definicji po redefinicji nazwy.

Negatywne/differential witnessy obejmują przesłonięcia object/Exception/ValueError/type, brak bazy, alias do liczby, hook bazowy rzucający wyjątek, własną metaklasę, wiele baz poprawnych, sprzeczny MRO, konflikt metaklas, dynamiczne __mro_entries__, reentrant import przed związaniem klasy, class-body import, warunkową frozen dataclass jako niedozwoloną bazę oraz deskryptor z efektownym __set_name__. UNKNOWN dla poprawnego custom-meta/many-bases/__mro_entries__ jest oczekiwany fail-closed wynik, nie błędny MODEL_PASS. CPython świadkowie zakończyły się zgodnie z oczekiwanym sukcesem lub błędem.

## TARGETED_TESTS

Interpreter testów: Python 3.15.2. Uruchomiono celowany subset 8 plików:

tests/test_cycle_semantics_package_model.py, tests/test_cycle_semantics_passive_classes.py, tests/test_cycle_semantics_namespace_bound_model.py, tests/test_cycle_semantics_package_model_annotations315.py, tests/test_cycle_semantics_package_model_literals.py, tests/test_cycle_semantics_package_model_async_alias.py, tests/test_cycle_semantics_namespace_path_model.py, tests/test_p1d3_package_cycle_integration.py.

Wynik: **649 passed**. Nie uruchomiono pełnego pytest. Próbki runtime były uruchamiane wyłącznie w subprocessach. R8/R10/R11, wcześniejsze zachowanie ValueError, importy klasowe i early-binding regresje pozostały przechodzące.

## MCP_POST_CHANGE_AUDIT

Desktop watcher potwierdził source/test aktualizacje sekwencyjnie; bez update_file. Ostatnia rewizja: **1225**, continuity continuous, bez resync. Zmiana package_model.py ma workspace_sync=verified; file-edit context: składnia checked_and_none, 0 błędów, availability=fresh.

LIVE przy rewizji 1225: hard graph/cycles fresh, **16** strukturalnych ścieżek DFS (jak przed zmianą), 16 aktywnych warningów, 0 model-pass paths; brak warning transitions w commicie 1224→1225. Soft-dependent potential graph fresh, **1** potencjalny SCC (contextor.mcp.analysis_jobs, contextor.mcp.query_helpers) bez zmiany. Syntax errors 0 fresh; name collisions 17 fresh. cycle_semantics pozostaje stale, więc nie twierdzę, że semantyczna analiza SCC została odświeżona ani że zmiana została adoptowana przez proces runtime. Nie wywołano FULL ani restartu.

## FULL_DIFFS

Poniżej pełny diff każdego zmienionego production/test pliku. walkthrough.md jest raportem i nie wlicza się do listy production/test diffów. CHANGELOG.md jest pre-existing change poza tym zadaniem.

~~~diff
diff --git a/contextor/core/cycle_semantics/package_model.py b/contextor/core/cycle_semantics/package_model.py
index 47ed25f..8cb970b 100644
--- a/contextor/core/cycle_semantics/package_model.py
+++ b/contextor/core/cycle_semantics/package_model.py
@@ -53,6 +53,48 @@ class AssumedFrozenDataclassDecoration:
     column: int
 
 
+@dataclass(frozen=True)
+class _ClassFact:
+    """Provenance and creation facts for one passive class definition."""
+
+    identity: str
+    origin: str
+    direct_base: str | None
+    metaclass_identity: str
+    defines_init_subclass: bool
+    safe_to_subclass: bool
+
+
+def _safe_class_namespace_value(value: object) -> bool:
+    """Values admitted in a passive class namespace cannot be descriptors."""
+    if isinstance(value, _ClassFact) or value is None:
+        return True
+    if type(value) is str:
+        return not value.startswith("\x00ASSUMED_EXTERNAL:")
+    return False
+
+
+_BUILTIN_TYPE_ID = "builtins.type"
+_BUILTIN_CLASS_FACTS = {
+    "object": _ClassFact(
+        "builtins.object", "BUILTIN", None,
+        _BUILTIN_TYPE_ID, False, True,
+    ),
+    "BaseException": _ClassFact(
+        "builtins.BaseException", "BUILTIN", "builtins.object",
+        _BUILTIN_TYPE_ID, False, True,
+    ),
+    "Exception": _ClassFact(
+        "builtins.Exception", "BUILTIN", "builtins.BaseException",
+        _BUILTIN_TYPE_ID, False, True,
+    ),
+    "ValueError": _ClassFact(
+        "builtins.ValueError", "BUILTIN", "builtins.Exception",
+        _BUILTIN_TYPE_ID, False, True,
+    ),
+}
+
+
 @dataclass(frozen=True)
 class PackageImportAssessment:
     entry_module: str
@@ -89,6 +131,9 @@ class _Step:
     source_line: int | None = None
     source_column: int | None = None
     annotation_builtin_names: tuple[str, ...] = ()
+    definition_id: str | None = None
+    defines_init_subclass: bool = False
+    explicit_type_metaclass: bool = False
 
 
 @dataclass
@@ -316,6 +361,14 @@ def _safe_passive_class_definition(
             statement.decorator_list[0]
         )
     )
+
+    explicit_type_metaclass = (
+        len(statement.keywords) == 1
+        and statement.keywords[0].arg == "metaclass"
+        and type(statement.keywords[0].value) is ast.Name
+        and statement.keywords[0].value.id == "type"
+    )
+
     if (
         not statement.name.isidentifier()
         or statement.name.startswith("__")
@@ -325,10 +378,10 @@ def _safe_passive_class_definition(
                 conditional_dataclass
                 or len(statement.bases) != 1
                 or type(statement.bases[0]) is not ast.Name
-                or statement.bases[0].id != "ValueError"
             )
         )
-        or statement.keywords
+        or (bool(statement.keywords) and not explicit_type_metaclass)
+        or (conditional_dataclass and statement.keywords)
         or (
             bool(statement.decorator_list)
             and not conditional_dataclass
@@ -1009,14 +1062,38 @@ def _compile(
             ):
                 return None
 
-            if stmt.bases:
+            if not conditional_dataclass:
+                if (
+                    type(stmt.lineno) is not int
+                    or stmt.lineno < 1
+                    or type(stmt.col_offset) is not int
+                    or stmt.col_offset < 0
+                ):
+                    return None
+
+                definition_id = (
+                    f"{logical}:{stmt.lineno}:{stmt.col_offset}"
+                )
                 steps.append(
                     _Step(
-                        "CHECK_BUILTIN_CLASS_BASE",
-                        target="ValueError",
+                        "PREPARE_PASSIVE_CLASS",
+                        target=(
+                            stmt.bases[0].id if stmt.bases else None
+                        ),
+                        binding=stmt.name,
+                        source_line=stmt.lineno,
+                        source_column=stmt.col_offset,
+                        definition_id=definition_id,
+                        explicit_type_metaclass=bool(stmt.keywords),
                     )
                 )
 
+            has_init_subclass = any(
+                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
+                and item.name == "__init_subclass__"
+                for item in stmt.body
+            )
+
             for body_statement in stmt.body:
                 if isinstance(body_statement, ast.Assign):
                     steps.append(
@@ -1121,6 +1198,12 @@ def _compile(
                     _Step(
                         "DEFINE_PASSIVE_CLASS",
                         binding=stmt.name,
+                        source_line=stmt.lineno,
+                        source_column=stmt.col_offset,
+                        definition_id=(
+                            f"{logical}:{stmt.lineno}:{stmt.col_offset}"
+                        ),
+                        defines_init_subclass=has_init_subclass,
                     )
                 )
 
@@ -1644,10 +1727,11 @@ def evaluate_package_import_order(
         for name in programs
     }
 
-    namespaces: dict[str, dict[str, str | None]] = {
+    namespaces: dict[str, dict[str, object | None]] = {
         name: {}
         for name in programs
     }
+    prepared_class_bases: dict[str, _ClassFact] = {}
 
     function_definitions: dict[
         str,
@@ -1824,6 +1908,9 @@ def evaluate_package_import_order(
                     and target.split(".", 1)[0]
                     not in indexed_roots
                 ):
+                    if step.class_local:
+                        return result("UNKNOWN", module, target)
+
                     assumed_external_imports.append(
                         ReachedUnmodeledImport(
                             importer=module,
@@ -2053,8 +2140,15 @@ def evaluate_package_import_order(
 
                     return result(outcome, target, member)
 
+                imported_value = namespaces[target][member]
+                if (
+                    step.class_local
+                    and not _safe_class_namespace_value(imported_value)
+                ):
+                    return result("UNKNOWN", target, member)
+
                 if not step.function_local and not step.class_local:
-                    namespaces[module][step.binding] = namespaces[target][member]
+                    namespaces[module][step.binding] = imported_value
 
                 events.append(
                     PackageModelEvent(
@@ -2150,10 +2244,16 @@ def evaluate_package_import_order(
                                 "tuple",
                             }
                             else not (
-                                type(namespaces[module].get(name))
-                                is str
-                                and namespaces[module][name].startswith(
-                                    "\x00PASSIVE_CLASS:"
+                                isinstance(
+                                    namespaces[module].get(name),
+                                    _ClassFact,
+                                )
+                                or (
+                                    type(namespaces[module].get(name))
+                                    is str
+                                    and namespaces[module][name].startswith(
+                                        "\x00PASSIVE_CLASS:"
+                                    )
                                 )
                             )
                         )
@@ -2193,10 +2293,26 @@ def evaluate_package_import_order(
                 )
             )
 
-        elif step.op == "CHECK_BUILTIN_CLASS_BASE":
+        elif step.op == "PREPARE_PASSIVE_CLASS":
+            if not step.binding or not step.definition_id:
+                return result("UNKNOWN", module, step.binding)
+
+            if (
+                step.explicit_type_metaclass
+                and "type" in namespaces[module]
+            ):
+                return result("UNKNOWN", module, "type")
+
+            if step.target is None:
+                base_fact = _BUILTIN_CLASS_FACTS["object"]
+            elif step.target in namespaces[module]:
+                base_fact = namespaces[module][step.target]
+            else:
+                base_fact = _BUILTIN_CLASS_FACTS.get(step.target)
+
+            if (
+                not isinstance(base_fact, _ClassFact)
+                or base_fact.metaclass_identity != _BUILTIN_TYPE_ID
+            ):
+                return result(
+                    "UNKNOWN",
+                    module,
+                    step.target,
+                )
+
+            prepared_class_bases[step.definition_id] = base_fact
+
         elif step.op == "DEFINE_PASSIVE_CLASS":
+            base_fact = prepared_class_bases.pop(
+                step.definition_id or "",
+                None,
+            )
+            if not isinstance(base_fact, _ClassFact):
+                return result("UNKNOWN", module, step.binding)
+
+            if not base_fact.safe_to_subclass:
+                return result("UNKNOWN", module, step.binding)
+
+            identity = step.definition_id
+            if not identity:
+                return result("UNKNOWN", module, step.binding)
+
+            class_fact = _ClassFact(
+                identity=identity,
+                origin="INDEXED_SOURCE",
+                direct_base=base_fact.identity,
+                metaclass_identity=_BUILTIN_TYPE_ID,
+                defines_init_subclass=step.defines_init_subclass,
+                safe_to_subclass=not step.defines_init_subclass,
+            )
             namespaces[module][step.binding] = (
-                "\x00PASSIVE_CLASS:"
-                + module
-                + ":"
-                + step.binding
+                class_fact
             )
 
             events.append(
diff --git a/tests/test_cycle_semantics_package_model.py b/tests/test_cycle_semantics_package_model.py
index 5bbfe1a..72a01da 100644
--- a/tests/test_cycle_semantics_package_model.py
+++ b/tests/test_cycle_semantics_package_model.py
@@ -436,8 +436,26 @@ def test_r9_simple_builtin_exception_subclass():
 @pytest.mark.parametrize(
     "declaration",
     [
-        "class CustomError(Exception):",
-        "class CustomError(BaseException):",
+        "class BuiltinObjectSubclass(object):",
+        "class BuiltinExceptionSubclass(Exception):",
+        "class BuiltinBaseExceptionSubclass(BaseException):",
+        "class ExplicitType(metaclass=type):",
+    ],
+)
+def test_r9_supported_builtin_class_origins(declaration):
+    result = _r9_builtin_base_result(declaration + "\n    pass\n")
+
+    assert result.outcome == "MODEL_PASS"
+    assert any(
+        event.operation == "DEFINE_PASSIVE_CLASS"
+        and event.symbol == declaration.split()[1].split("(")[0]
+        for event in result.events
+    )
+
+
+@pytest.mark.parametrize(
+    "declaration",
+    [
         "class CustomError(UnknownBase):",
         "class CustomError(pkg.ValueError):",
         "class CustomError(ValueError, Exception):",
~~~
diff --git a/tests/test_cycle_semantics_passive_classes.py b/tests/test_cycle_semantics_passive_classes.py
index 7e3c58b..979dbf2 100644
--- a/tests/test_cycle_semantics_passive_classes.py
+++ b/tests/test_cycle_semantics_passive_classes.py
@@ -385,3 +385,195 @@ def test_c24_determinism_and_ast_immutability():
     }
 
     json.dumps(asdict(first))
+
+
+@pytest.mark.parametrize(
+    ("source", "extra"),
+    [
+        ("class Child(object): pass", {}),
+        ("class Child(Exception): pass", {}),
+        ("class Child(BaseException): pass", {}),
+        ("class Child(ValueError): pass", {}),
+        ("class Base: pass\nclass Child(Base): pass", {}),
+        (
+            "class Base: pass\nBaseAlias = Base\n"
+            "class Child(BaseAlias): pass",
+            {},
+        ),
+        (
+            "from pkg.base import Base\nclass Child(Base): pass",
+            {"pkg.base": "class Base: pass"},
+        ),
+        ("class Child(metaclass=type): pass", {}),
+        (
+            "class Base: pass\nOldBase = Base\nclass Base: pass\n"
+            "class Child(OldBase): pass",
+            {},
+        ),
+    ],
+)
+def test_p3_d1_proven_class_bases_match_cpython(
+    tmp_path, source, extra,
+):
+    sources = {"pkg.__init__": "pass", "pkg.a": source, **extra}
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+@pytest.mark.parametrize(
+    ("source", "runtime_succeeds"),
+    [
+        ("object = 1\nclass Child(object): pass", False),
+        ("Exception = 1\nclass Child(Exception): pass", False),
+        ("ValueError = 1\nclass Child(ValueError): pass", False),
+        ("type = 1\nclass Child(metaclass=type): pass", False),
+        ("class Child(MissingBase): pass", False),
+        ("Base = 1\nclass Child(Base): pass", False),
+        (
+            "class Base:\n"
+            "    def __init_subclass__(cls):\n"
+            "        raise RuntimeError('hook')\n"
+            "class Child(Base): pass",
+            False,
+        ),
+        (
+            "class Meta(type): pass\n"
+            "class Child(metaclass=Meta): pass",
+            True,
+        ),
+        (
+            "class Left: pass\nclass Right: pass\n"
+            "class Child(Left, Right): pass",
+            True,
+        ),
+        (
+            "class A: pass\nclass B: pass\nclass C(A, B): pass\n"
+            "class D(B, A): pass\nclass E(C, D): pass",
+            False,
+        ),
+        (
+            "class MetaA(type): pass\nclass MetaB(type): pass\n"
+            "class A(metaclass=MetaA): pass\n"
+            "class B(metaclass=MetaB): pass\n"
+            "class C(A, B): pass",
+            False,
+        ),
+        (
+            "class Proxy:\n"
+            "    def __mro_entries__(self, bases):\n"
+            "        return (object,)\n"
+            "proxy = Proxy()\nclass Child(proxy): pass",
+            True,
+        ),
+    ],
+)
+def test_p3_d1_unproven_class_mechanisms_stay_unknown(
+    tmp_path, source, runtime_succeeds,
+):
+    sources = {"pkg.__init__": "pass", "pkg.a": source}
+
+    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
+    process = _actual(tmp_path, sources, "pkg.a")
+    assert (process.returncode == 0) is runtime_succeeds
+
+
+def test_p3_d1_old_alias_keeps_redefined_class_identity(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class Base:\n"
+            "    def __init_subclass__(cls):\n"
+            "        raise RuntimeError('old hook')\n"
+            "OldBase = Base\n"
+            "class Base: pass\n"
+            "class Child(OldBase): pass"
+        ),
+    }
+
+    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
+    process = _actual(tmp_path, sources, "pkg.a")
+    assert process.returncode != 0
+    assert "old hook" in process.stderr
+
+
+def test_p3_d1_reentrant_import_sees_class_unbound(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": (
+            "class Base: pass\n"
+            "class Child(Base):\n"
+            "    import pkg.b"
+        ),
+        "pkg.b": "from pkg.a import Child",
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "EARLY_BINDING_HAZARD"
+    assert result.symbol == "Child"
+    process = _actual(tmp_path, sources, "pkg.a")
+    assert process.returncode != 0
+    assert "ImportError" in process.stderr
+
+
+@pytest.mark.parametrize("name", ["object", "Exception", "ValueError"])
+def test_p3_d1_shadowed_builtin_base_is_unknown(tmp_path, name):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": f"{name} = 1\nclass Child({name}): pass",
+    }
+
+    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
+    assert _actual(tmp_path, sources, "pkg.a").returncode != 0
+
+
+def test_p3_d1_class_body_import_remains_supported(tmp_path):
+    sources = {
+        "pkg.__init__": "pass",
+        "pkg.a": "class Child(object):\n    import pkg.b",
+        "pkg.b": "value = 1",
+    }
+
+    result = _model(sources, "pkg.a")
+
+    assert result.outcome == "MODEL_PASS"
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+def test_p3_d1_conditional_dataclass_is_not_a_proven_base(tmp_path):
+    source = (
+        "from dataclasses import dataclass\n"
+        "@dataclass(frozen=True)\n"
+        "class Base: pass\n"
+        "class Child(Base): pass"
+    )
+    sources = {"pkg.__init__": "pass", "pkg.a": source}
+    result = evaluate_package_import_order(
+        {name: ast.parse(value) for name, value in sources.items()},
+        "pkg.a",
+        annotation_semantics="DEFERRED",
+        _assume_passive_external_imports=True,
+        _assume_frozen_dataclass_decoration=True,
+    )
+
+    assert result.outcome == "UNKNOWN"
+    assert _actual(tmp_path, sources, "pkg.a").returncode == 0
+
+
+def test_p3_d1_unknown_set_name_descriptor_stays_unknown(tmp_path):
+    source = (
+        "class Descriptor:\n"
+        "    def __set_name__(self, owner, name):\n"
+        "        raise RuntimeError('descriptor hook')\n"
+        "class Subject:\n"
+        "    value = Descriptor()"
+    )
+    sources = {"pkg.__init__": "pass", "pkg.a": source}
+
+    assert _model(sources, "pkg.a").outcome == "UNKNOWN"
+    process = _actual(tmp_path, sources, "pkg.a")
+    assert process.returncode != 0
+    assert "descriptor hook" in process.stderr
+

