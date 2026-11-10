# P3-R2-T1 — external import side-effect regression

## PREFLIGHT

Contextor MCP first: HEAD `3cbd8cc471197c54b15cf327d93adcb5797aa874` zgodny z oczekiwanym; canonical revision 1256, cycle_semantics stale; source funkcji `evaluate_conditional_namespace_import_order` i `analyze_cycle_scenarios` workspace_sync verified przed zmianą. Wskazany plik testowy istniał; source/tests poza nim nie były zmienione. Planowany przed edycją zakres diffu: wyłącznie jeden syntetyczny test oraz `import builtins` w `tests/test_cycle_semantics_external_import_authority.py`, bez production patch.

Preflight na dokładnie wskazanym programie, bez edycji modelu: `CONDITIONAL_MODEL_PASS`, inner `MODEL_PASS`, dwa assumed external records i jeden assumed frozen dataclass record. Warunek wejścia do implementacji regresji został spełniony; nie dopasowywano programu w celu wymuszenia PASS.

## FILES_CHANGED

FILES_CHANGED: `tests/test_cycle_semantics_external_import_authority.py`. `walkthrough.md` jest wyłącznie raportem. Brak produkcyjnych zmian.

## CONTROL_RUNTIME_RESULT

Po adwersarialnym przebiegu uruchomiono osobny `sys.executable -I -S -c` subprocess CPython 3.15.2 z jawnie dodanym `tmp_path` do `sys.path`. `ext_mutator.py` zawierał tylko `pass`; `import pkg.ns.a` zakończył się `returncode=0`. Test wymagał `control.returncode == 0` i potwierdził, że `builtins.property` procesu pytest nadal jest pierwotnym obiektem. To także negatywny świadek braku zanieczyszczenia następnego przebiegu przez adwersarialny subprocess.

## ADVERSARIAL_RUNTIME_RESULT

Oddzielny `python -I -S -c` subprocess, ten sam syntetyczny regular `pkg` z namespace child `pkg.ns`, ale `ext_mutator.py` wykonał `import builtins; builtins.property = 1`. `import pkg.ns.a` zakończył się niezerowym kodem. Test bezpośrednio sprawdził traceback: zawiera `a.py`, linię `@property` oraz końcowy typ/komunikat `TypeError: 'int' object is not callable`. Import `ext_mutator` wykonuje efekt przed definicją `Graph.value`; proces pytest nie importował syntetycznego pakietu i jego `builtins.property` pozostało niezmienione.

## CONDITIONAL_MODEL_RESULT

Dokładne AST: `pkg.__init__`, `pkg.ns.a`, `pkg.ns.b`; jedna `SearchPortion(root_id='repo')` z `pkg/__init__.py`, `pkg/ns/a.py`, `pkg/ns/b.py`. Parametry `target_python_version=(3,15)`, `assume_passive_external_imports=True`, `assume_frozen_dataclass_decoration=True`. Wynik: `CONDITIONAL_MODEL_PASS`, `reason=None`, inner `MODEL_PASS`, `authority=CONDITIONAL_ORDERED_INVENTORY_AND_AST_NOT_RUNTIME_OR_LIVE_PROOF`, `evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`.

Dokładne assumed external records: `(pkg.ns.a, FROM, dataclasses, dataclass, 1:0)`; `(pkg.ns.a, IMPORT, ext_mutator, None, 2:0)`. Assumed frozen dataclass: `(pkg.ns.a, Graph, dataclasses.dataclass(frozen=True), 4:1)`. Te records są nieudowodnionymi założeniami, nie runtime evidence. Wynik warunkowy jest identyczny dla wariantów control/adversarial, ponieważ model nie wykonuje `ext_mutator`.

## ORDINARY_BOUNDARY_RESULT

`analyze_cycle_scenarios` na zadanym hard graph (`pkg.__init__:[]`, `pkg.ns.a:[pkg.ns.b]`, `pkg.ns.b:[pkg.ns.a]`) zwrócił jeden SCC: `classification=INDETERMINATE`, `coverage=NONE`, `reason=NAMESPACE_IMPORT_RESOLUTION_UNMODELED`, `model_kind=REGULAR_PACKAGE`, zero entry assessments. Zwykła ścieżka nie przejmuje `CONDITIONAL_MODEL_PASS` ani założeń zewnętrznych; nie modyfikowano warning eligibility.

## REGRESSION_TESTS

Jeden nowy test tworzy dokładnie podane źródła w `tmp_path`, sprawdza conditional model authority i records, ordinary SCC refusal, a następnie dwa niezależne CPython subprocessy. Adwersarialny uruchamiany jest przed kontrolnym, więc kontrola sprawdza również izolację efektu. Nie importowano syntetycznych modułów w procesie pytest. Nie tworzono LIVE evidence/receipts.

## TARGETED_TEST_RESULTS

`& .\.venv\Scripts\python.exe -m pytest -q tests/test_cycle_semantics_external_import_authority.py` → **7 passed in 2.14s**, exit code 0. `git diff --check` → exit code 0. Bez pełnego pytest.

## MCP_POST_CHANGE_AUDIT

Po edycji/teście Contextor MCP nadal wskazuje canonical revision `1256`, graph/cycles fresh, cycle_semantics stale, syntax errors 0, structural DFS paths 16, warning view `structural=16, model_pass=0, active=16`. Odczytowy IPC snapshot potwierdził state_id `20261109_210842`, 16 cycles i graph SHA-256 `2b45d940afccdaefb3c0f4a686b83bcbc2687e0d8b167cadc986106b01eedf6f`, zgodny z baseline. `get_live_events(after_revision=1256)` nie zgłosił zdarzenia watcher. Odczyt symbolu nowego testu zwrócił `status=stale_source`, `workspace_sync=out_of_sync`; **synchronizacja indeksu nowego testu nie jest potwierdzona**. Brak FULL, `update_file`, restartu i publikacji.

## FULL_DIFFS

Pełny rzeczywisty git diff jedynego pliku zmienionego w zadaniu:

```diff
diff --git a/tests/test_cycle_semantics_external_import_authority.py b/tests/test_cycle_semantics_external_import_authority.py
index a9a3247..d6cdedc 100644
--- a/tests/test_cycle_semantics_external_import_authority.py
+++ b/tests/test_cycle_semantics_external_import_authority.py
@@ -1,6 +1,7 @@
 """External import effects are not ordinary execution evidence."""
 
 import ast
+import builtins
 import subprocess
 import sys
 
@@ -169,3 +170,109 @@ def test_unproved_typing_guard_stops_ordinary_and_conditional_models(
     }
     assert conditional.outcome != "CONDITIONAL_MODEL_PASS"
     assert ordinary.outcome != "MODEL_PASS"
+
+
+def test_conditional_external_side_effect_is_not_runtime_authority(tmp_path):
+    assert sys.version_info[:3] == (3, 15, 2)
+
+    sources = {
+        "pkg.__init__": "pass\n",
+        "pkg.ns.a": (
+            "from dataclasses import dataclass\n"
+            "import ext_mutator\n"
+            "\n"
+            "@dataclass(frozen=True)\n"
+            "class Graph:\n"
+            "    @property\n"
+            "    def value(self):\n"
+            "        return 1\n"
+            "\n"
+            "token = 1\n"
+            "import pkg.ns.b\n"
+        ),
+        "pkg.ns.b": "from pkg.ns.a import token\n",
+    }
+    trees = {name: ast.parse(source) for name, source in sources.items()}
+    portion = SearchPortion(
+        "repo",
+        frozenset({"pkg/__init__.py", "pkg/ns/a.py", "pkg/ns/b.py"}),
+    )
+    conditional = evaluate_conditional_namespace_import_order(
+        trees,
+        "pkg.ns.a",
+        (portion,),
+        target_python_version=(3, 15),
+        assume_passive_external_imports=True,
+        assume_frozen_dataclass_decoration=True,
+    )
+
+    assert conditional.outcome == "CONDITIONAL_MODEL_PASS"
+    assert conditional.reason is None
+    assert conditional.authority == (
+        "CONDITIONAL_ORDERED_INVENTORY_AND_AST_NOT_RUNTIME_OR_LIVE_PROOF"
+    )
+    model = conditional.model_assessment
+    assert model is not None
+    assert model.outcome == "MODEL_PASS"
+    assert model.evidence_scope == (
+        "CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_"
+        "ASSUMPTIONS_NOT_RUNTIME_PROOF"
+    )
+    assert tuple(
+        (item.importer, item.operation, item.target, item.symbol,
+         item.line, item.column)
+        for item in model.assumed_external_imports
+    ) == (
+        ("pkg.ns.a", "FROM", "dataclasses", "dataclass", 1, 0),
+        ("pkg.ns.a", "IMPORT", "ext_mutator", None, 2, 0),
+    )
+    assert tuple(
+        (item.module, item.class_name, item.decorator,
+         item.line, item.column)
+        for item in model.assumed_dataclass_decorations
+    ) == ((
+        "pkg.ns.a", "Graph", "dataclasses.dataclass(frozen=True)", 4, 1,
+    ),)
+
+    edges = {
+        "pkg.__init__": set(),
+        "pkg.ns.a": {"pkg.ns.b"},
+        "pkg.ns.b": {"pkg.ns.a"},
+    }
+    ordinary = analyze_cycle_scenarios(edges, trees)
+    assert len(ordinary.components) == 1
+    assert ordinary.components[0].classification != (
+        "MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS"
+    )
+
+    package = tmp_path / "pkg"
+    namespace = package / "ns"
+    namespace.mkdir(parents=True)
+    (package / "__init__.py").write_text(sources["pkg.__init__"])
+    (namespace / "a.py").write_text(sources["pkg.ns.a"])
+    (namespace / "b.py").write_text(sources["pkg.ns.b"])
+    mutator = tmp_path / "ext_mutator.py"
+    command = [
+        sys.executable, "-I", "-S", "-c",
+        "import sys;sys.path.insert(0,sys.argv[1]);import pkg.ns.a",
+        str(tmp_path),
+    ]
+    original_property = builtins.property
+
+    mutator.write_text("import builtins\nbuiltins.property = 1\n")
+    adversarial = subprocess.run(
+        command, capture_output=True, text=True, timeout=10,
+    )
+    assert adversarial.returncode != 0
+    assert "TypeError: 'int' object is not callable" in adversarial.stderr
+    assert 'File "' in adversarial.stderr
+    assert "a.py" in adversarial.stderr
+    assert "@property" in adversarial.stderr
+    assert builtins.property is original_property
+
+    mutator.write_text("pass\n")
+    control = subprocess.run(
+        command, capture_output=True, text=True, timeout=10,
+    )
+    assert control.returncode == 0, control.stderr
+    assert builtins.property is original_property
```

## FINAL_VERDICT

`CONTRACT_ALREADY_FAIL_CLOSED` dla ordinary authority: warunkowy model daje `CONDITIONAL_MODEL_PASS` wyłącznie przy jawnych, nieudowodnionych założeniach, podczas gdy adwersarialny CPython kończy się `TypeError`, a ordinary SCC pozostaje `INDETERMINATE`. Regresja przechodzi; MCP source sync nowego testu pozostaje `out_of_sync` w obserwowanym post-audicie. STOP.
