# CPA_FILE_UPDATE_COMPLETENESS_SIGNATURE_REPRO

## STATUS

STATUS=CONFIRMED_INCREMENTAL_CANONICAL_COMPLETENESS_DEFECT

Discovery przed edycją wykonana przez Contextor. Dodano jeden targeted test, bez zmian production. Uruchomiono wyłącznie nowy node ID, dwa przebiegi po korekcie jednej błędnej precondition; oba przebiegi zakończyły się FAIL. Drugi przebieg dotarł do porównania signature incremental/full i wykazał jednoznaczny canonical mismatch. Nie uruchomiono innych testów.

## HEAD_BEFORE

HEAD_BEFORE=9edaa5237163539f91cfc0240cc85ae9c09d98ec
Branch=main

HEAD po zmianie testu jest taki sam. Przed patchem git status wykazywał wyłącznie wcześniejszą zmianę walkthrough.md z zaakceptowanego poprzedniego kroku. Wskazane production files i target test file nie miały diffu względem HEAD. Raport walkthrough został nadpisany zgodnie z bieżącym zadaniem.

## SOURCE_DRIFT

SOURCE_DRIFT=NONE

Przed edycją potwierdzono HEAD i brak driftu w:
- contextor/core/analysis/incremental/engine.py
- contextor/core/analysis/incremental/preparation.py
- contextor/core/symbol_engine/extractor.py
- contextor/core/symbol_engine/domain.py
- tests/test_completeness_freshness_parity_proof.py

Contextor zwrócił engine.py jako LIVE/fresh, workspace_sync=verified, revision=1467. Aktualne source anchors zgodziły się z zaakceptowanym discovery. Jedyny patch wprowadza nową funkcję testową.

## CANONICAL_OWNER

Canonical updater: C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py — IncrementalAnalysisEngine.update_file oraz _commit_syntax_candidate.

Przygotowanie i structural delta: C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\preparation.py — prepare_source_update i calculate_file_delta.

Nowy payload signature powstaje w extract_file_symbols → SymbolFacts.to_dict:
- C:\Temp\Contextor_Repo\contextor\core\symbol_engine\extractor.py
- C:\Temp\Contextor_Repo\contextor\core\symbol_engine\domain.py

Planowane canonical definitions instalowane są przez ścieżkę execute_refresh_plan / _apply_delta_and_commit. Gałąź pustego planu w update_file wywołuje _commit_syntax_candidate oraz state_manager.update_state; nie przekazuje prep.new_artifacts do instalacji definitions.

## TEST_FILE

C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py

Contextor wskazał istniejący test_full_canonical_parity_import_and_graph w tym pliku: tworzy IncrementalAnalysisEngine, używa engine.update_file, buduje fresh oracle przez _build_full_static_state i porównuje canonical families przez _assert_full_parity. Ten fixture/oracle był najwęższym istniejącym miejscem dla tego reproduktora. _assert_full_parity porównuje cały symbols payload, ale nowy test dodatkowo odczytuje signature jawnie, aby mismatch był bezpośredni.

Contextor test coverage dla engine.py ma evidence_scope=static_dependency_reachability, total=95 test modules. To pomocnicza mapa zależności testów, nie wykonany dowód zachowania. Source range i implementacja helpera potwierdziły lokalny oracle i fixture.

## TEST_NODE_ID

tests/test_completeness_freshness_parity_proof.py::test_incremental_signature_change_matches_full_oracle

## REPRO_CONTRACT

Test wykonuje kolejno:
1. Tworzy target.py z def foo(a): return a.
2. Uruchamia normalne engine.update_file dla baseline i potwierdza canonical artifacts signature def foo(a).
3. Zmienia wyłącznie nagłówek funkcji na def foo(a, b=0): return a.
4. Ponownie wywołuje engine.update_file.
5. Potwierdza, że delta nie ma added/removed symbols ani imports.
6. Czyta signature z incremental canonical state.
7. Buduje fresh/full oracle tego samego tmp_path przez istniejący _build_full_static_state i czyta canonical signature.
8. Porównuje signature i raportuje obie wartości w komunikacie asercji.

Nie testuje calculate_file_delta w izolacji; mismatch pochodzi z pełnej single-file update path oraz canonical state.

## DIRECT_EVIDENCE

- Contextor search_source/get_source_range pokazał istniejący fixture i helper _build_full_static_state. Helper uruchamia ContextorFacade.analyze_project na małym tmp_path, następnie hydrate_repository_engine i zwraca świeży engine.state.
- Contextor implementation calculate_file_delta dla istniejącego modułu porównuje zbiory nazw importowanych modułów oraz nazwy artefaktów; nie porównuje signatures.
- Contextor search_source potwierdził SymbolFacts.signatures i body_fingerprints oraz extract_file_symbols zwracające facts.to_dict().
- Literal source przed patchem: engine.py gałąź plan.is_empty woła _commit_syntax_candidate, state_manager.update_state i zwraca; nie instaluje prep.new_artifacts.
- Pierwszy przebieg testu zatrzymał się na tymczasowym warunku shadow_plan.is_empty. Wynik pokazał, że dla tej zmiany plan zawierał wyłącznie patch_families collision_facts/collisions, bez recompute_modules. Collision facts nie były więc w tym fixture niezmienione i plan nie był pusty. Usunięto tylko tę dodatkową precondition; nie usunięto ani nie osłabiono porównania canonical signatures.
- Drugi przebieg przeszedł baseline, incremental update i fresh/full oracle. Structural delta added/removed/import lists były puste. Ostatnia asercja porównująca canonical signatures zawiodła:
  incremental signature = def foo(a)
  full signature = def foo(a, b=0)

## TEST_RESULT

Pierwszy przebieg tego samego node ID: FAIL na precondition shadow_plan.is_empty; wynik pokazał plan ograniczony do collision_facts/collisions.

Po usunięciu wyłącznie tej precondition, drugi przebieg tego samego node ID: FAIL na końcowej asercji incremental_signature == full_signature. Test wykonał fresh/full oracle; failure nie pochodzi z błędnego klucza, fixture setup ani delta helpera. Pozostawiono test w stanie oczekiwanego FAIL na mismatch; nie poprawiano production ani asercji końcowej.

Uruchomione node IDs:
- tests/test_completeness_freshness_parity_proof.py::test_incremental_signature_change_matches_full_oracle — dwa przebiegi.

Nie uruchomiono adjacent node ani full suite.

## OBSERVED_INCREMENTAL_SIGNATURE

def foo(a)

## OBSERVED_FULL_SIGNATURE

def foo(a, b=0)

## CLASSIFICATION

CLASSIFICATION=CONFIRMED_INCREMENTAL_CANONICAL_COMPLETENESS_DEFECT

Bezpośrednio potwierdzono, że zmiana signature tej samej funkcji zostawia starą signature w incremental canonical artifacts, podczas gdy fresh/full canonical state zawiera nową. W tym reproduktorze plan nie był pusty, bo zmieniły się collision facts; plan ograniczał się do collision_facts/collisions i nadal nie instalował nowych definitions. To potwierdza correctness gap dla single-file canonical signature completeness, ale nie potwierdza osobno wariantu, w którym collision facts pozostają niezmienione i plan jest pusty.

## FILES_CHANGED

- C:\Temp\Contextor_Repo\tests\test_completeness_freshness_parity_proof.py — dodano jeden targeted regression test.
- C:\Temp\Contextor_Repo\walkthrough.md — nadpisano raport poprzedniego kroku zgodnie z instrukcją.

Production files: bez zmian.
HEAD: bez zmian.

### ACTUAL_DIFF — tests/test_completeness_freshness_parity_proof.py

diff --git a/tests/test_completeness_freshness_parity_proof.py b/tests/test_completeness_freshness_parity_proof.py
index dfc80b2..6385b80 100644
--- a/tests/test_completeness_freshness_parity_proof.py
+++ b/tests/test_completeness_freshness_parity_proof.py
@@ -848,6 +848,41 @@ def test_full_canonical_parity_import_and_graph(tmp_path):
     _assert_full_parity(engine.state, oracle)

 
+def test_incremental_signature_change_matches_full_oracle(tmp_path):
+    f_target = tmp_path / "target.py"
+    f_target.write_text("def foo(a):\n    return a\n", encoding="utf-8")
+
+    cache_dir = tmp_path / "cache"
+    cache_dir.mkdir()
+    engine = IncrementalAnalysisEngine(
+        RepositoryAnalysisState(modules={}),
+        PersistentIdentityRegistry(str(tmp_path)),
+        FileStateManager(str(cache_dir)),
+        str(tmp_path),
+    )
+    engine.update_file(str(f_target))
+
+    initial_signature = engine.state.artifacts["target"]["symbols"]["signatures"]["foo"]
+    assert initial_signature == "def foo(a)"
+
+    f_target.write_text("def foo(a, b=0):\n    return a\n", encoding="utf-8")
+    result = engine.update_file(str(f_target))
+
+    assert result.delta.artifacts_added == []
+    assert result.delta.artifacts_removed == []
+    assert result.delta.imports_added == []
+    assert result.delta.imports_removed == []
+    incremental_signature = engine.state.artifacts["target"]["symbols"]["signatures"]["foo"]
+    oracle = _build_full_static_state(tmp_path)
+    full_signature = oracle.artifacts["target"]["symbols"]["signatures"]["foo"]
+
+    assert full_signature == "def foo(a, b=0)"
+    assert incremental_signature == full_signature, (
+        "canonical incremental signature differs from fresh full oracle: "
+        f"incremental={incremental_signature!r}, full={full_signature!r}"
+    )
+
+
 def test_full_canonical_parity_module_add_and_delete(tmp_path):
