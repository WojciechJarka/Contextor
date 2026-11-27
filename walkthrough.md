# GRAPH-R10-I2 — zachowanie kontraktu Missing trusted source SHA-256

## FILES_CHANGED

- contextor/core/analysis/incremental/engine.py
- walkthrough.md — raport tego zadania, poza zakresem source/test.
- ACTUAL_DIFF: pełny aktualny diff engine.py znajduje się w FULL_DIFFS.
- ACTUAL_DIFF dla pozostałych source/test: NONE. Nie zmieniono testów ani innych plików źródłowych.

## PREFLIGHT

**DIRECT_EVIDENCE**

- Contextor MCP przed edycją: engine.py canonical_revision=1585, canonical_state=fresh, workspace_sync=verified, provenance=live.
- HEAD: 3f7029a0591649b6c28cf32a3451aacf14813941.
- Git status przed tym etapem zawierał M engine.py i M walkthrough.md z GRAPH-R10-I1. HEAD nie zmienił się.
- Dokładne kotwice MCP pasowały:
  - semantic no-op guard: engine.py:851-870; update_state na 852, poprzedni porównawczy guard bezpośrednio po nim, manifest poniżej;
  - updated commit guard: engine.py:1288-1305; update_state na 1288, poprzedni guard przed manifestem;
  - dotychczasowy expected_source_fingerprint, normalny call i parametr z I1 pozostają.
- Przygotowanie test harnessu używało wyłącznie istniejącego testowego helpera. Nie uruchamiano LIVE ownera, listenera ani backendu.

## TWO_LITERAL_CORRECTIONS

**DIRECT_EVIDENCE**

- Semantic no-op: po update_state pobierany jest tracked_sha256. Guard działa wyłącznie, jeśli tracked_sha256 jest niepusty i różni się od expected_source_fingerprint.
- _apply_delta_and_commit: po update_state pobierany jest tracked_sha256. Guard działa wyłącznie, gdy expected_source_fingerprint jest ustawiony, tracked_sha256 jest niepusty i wartości się różnią.
- Następujące wywołania _updated_module_usage_manifest pozostają nietknięte.
- Parametr expected_source_fingerprint, przekazanie go tylko w niedeletowanej ścieżce oraz None dla DELETED pozostają bez zmian.
- Nie dodano walidatora, statusu, retry ani obsługi przechwytującej RuntimeError.

## MISSING_SHA_CONTRACT

**DIRECT_EVIDENCE**

- Pusty get_tracked_sha256 omija nowy porównawczy guard.
- Następnie istniejące _updated_module_usage_manifest otrzymuje niezmienione tracked SHA; jego walidacja nadal zgłasza Missing trusted source SHA-256.
- Nie duplikowano tego błędu w nowym guardzie.

## MISMATCH_CONTRACT

**DIRECT_EVIDENCE**

- Dwa niepuste i różne fingerprinty zgłaszają RuntimeError("Source changed during incremental analysis").
- Równe fingerprinty kontynuują dotychczasową ścieżkę.
- Dla DELETED expected_source_fingerprint jest None; nowy guard w _apply_delta_and_commit nie wykonuje porównania.
- Oba guards pozostają w swoich istniejących granicach transakcyjnych. RuntimeError propaguje się po rollbacku.

## TARGETED_PYTEST

**DIRECT_EVIDENCE**

Wymagane moduły:

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_incremental_failed_commit_atomicity.py tests/test_incremental_consumer_manifest_parity.py
~~~

Wynik: 12 passed, 2 warnings in 24.10s. Ostrzeżenia to istniejące deprecations Authlib.

Dodatkowy test:

~~~text
.venv/Scripts/python.exe -m pytest -q tests/test_live_state_consistency.py::test_import_mutation
~~~

Wynik: 1 passed in 5.74s.

Wśród 12 testów przeszły również trzy kontrakty pustego tracked SHA, które w GRAPH-R10-I1 wcześniej oczekiwały Missing trusted source SHA-256.

## CONTROLLED_RACE_REGRESSION

**DIRECT_EVIDENCE**

- Trwałego skryptu GRAPH-R9 nie znaleziono. Użyto istniejącego _real_baseline i _assert_failed_update_atomic z tests/test_incremental_failed_commit_atomicity.py, w odizolowanych TemporaryDirectory. Cache, state, output i registry wskazywały katalog tymczasowy. Test użył bezpośredniego IncrementalAnalysisEngine; nie uruchomiono LIVE ownera/listenera.
- UPDATED A→B: oryginalny prepare przetworzył A, synchroniczny wrapper zapisał B przed powrotem do engine. RefreshPlan był niepusty. RuntimeError propagował się.
- Semantic UNCHANGED A→B: przygotowane A miało tylko zmianę komentarza na końcu i pusty plan; po prepare zapisano B z innym importem. RuntimeError propagował się.
- W obu przypadkach kontrola porównywała dwa niepuste, różne SHA. B pozostawał aktualnym źródłem po odrzuceniu kandydata.

**CODE_PATH_PROVED**

- Wyjątek updatera w LIVE występuje przed wywołaniem persistera (ipc.py:2126-2131; persister jest dalej w _execute_update_file), zatem failed invocation nie dochodzi do publikacji nowej committed generation.

## ROLLBACK_VERIFICATION

**DIRECT_EVIDENCE**

W obu kontrolowanych race’ach istniejący _assert_failed_update_atomic zakończył się bez błędu i potwierdził:

- zachowanie tożsamości obiektu RepositoryAnalysisState oraz równość jego projection z baseline;
- rollback całego FileStateManager._state;
- równość module_usages_manifest;
- przywrócenie registry checkpoint;
- niezmienione committed metadata state_id/revision;
- tracked SHA po rollbacku wrócił do wcześniejszego baseline;
- B pozostał na dysku, a has_changed(B) zwróciło True.

Wynik obu przypadków: niezgodny candidate nie został zatwierdzony, a B wymaga kolejnej analizy.

## POST_CHANGE_MCP

**DIRECT_EVIDENCE**

- Contextor MCP po edycji: engine.py canonical_revision=1586, canonical_state=fresh, workspace_sync=verified, provenance=live.
- get_file_edit_context: syntax_diagnostics=checked_and_none, availability=fresh, errors=[], total=0.
- get_source_range potwierdził oba skorygowane guardy i zachowane wywołania manifestu.
- get_symbol_call_context na revision 1586 potwierdził update_file → _apply_delta_and_commit dla niedeletowanej ścieżki na linii 906 oraz zachowaną ścieżkę DELETED na 685.
- get_symbol_lineage rozwiązał update_file jako A537/1; lineage i lineage_query_index były fresh. Narrow lineage raportował workspace_sync=unverified zgodnie ze swoim kontraktem bez odczytu hash pliku; module context i get_file_edit_context raportowały verified.
- get_live_events(after_revision=1585) zwrócił revision 1586, operation=update_file, origin=desktop_watcher, status=UPDATED, continuity=continuous, resync_required=false.
- Nie restartowano backendu i nie utożsamiano rewizji canonical z atestacją dokładnego kodu załadowanego w każdym długotrwałym procesie.

## FULL_DIFFS

~~~diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 502baf7..1fb3ef1 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -784,6 +784,9 @@ class IncrementalAnalysisEngine:
             )
             checked_and_none = {"status": "checked_and_none", "errors": []}
 
+            expected_source_fingerprint = (
+                prep.typing_guard_source_evidence["source_fingerprint"]
+            )
             delta = prep.delta
             usage_delta = prep.usage_delta
             new_imports = prep.new_imports
@@ -849,6 +852,16 @@ class IncrementalAnalysisEngine:
                     )
                     self.state.typing_guard_evidence = updated_evidence
                     self.state_manager.update_state(file_path)
+                    tracked_sha256 = self.state_manager.get_tracked_sha256(
+                        file_path
+                    )
+                    if (
+                        tracked_sha256
+                        and tracked_sha256 != expected_source_fingerprint
+                    ):
+                        raise RuntimeError(
+                            "Source changed during incremental analysis"
+                        )
                     self.state.module_usages_manifest = _updated_module_usage_manifest(
                         self.state.module_usages_manifest,
                         module_path,
@@ -901,6 +914,7 @@ class IncrementalAnalysisEngine:
                 force_full_graph=force_full_graph,
                 classified_modules=classified_modules,
                 updated_typing_guard_evidence=updated_evidence,
+                expected_source_fingerprint=expected_source_fingerprint,
             )
 
             if plan.refresh_completeness == "requires_resync":
@@ -996,6 +1010,7 @@ class IncrementalAnalysisEngine:
         force_full_graph: bool = False,
         classified_modules: dict[str, Module] | None = None,
         updated_typing_guard_evidence: dict[str, object] | None = None,
+        expected_source_fingerprint: str | None = None,
     ) -> tuple[Set[str], bool, dict]:
         """
         Executes planned RefreshPlan phases and performs atomic persistent & RAM commit.
@@ -1273,6 +1288,17 @@ class IncrementalAnalysisEngine:
             "INCREMENTAL_FILE_STATE_START",
         )
         self.state_manager.update_state(file_path)
+        tracked_sha256 = self.state_manager.get_tracked_sha256(
+            file_path
+        )
+        if (
+            expected_source_fingerprint is not None
+            and tracked_sha256
+            and tracked_sha256 != expected_source_fingerprint
+        ):
+            raise RuntimeError(
+                "Source changed during incremental analysis"
+            )
         self.state.module_usages_manifest = _updated_module_usage_manifest(
             self.state.module_usages_manifest,
             delta.module_path,
~~~

## CONCLUSIONS

**DIRECT_EVIDENCE**

- Obie korekty zachowują kontrakt pustego trusted SHA i wykrywają różnicę dwóch niepustych fingerprintów.
- 12 wymaganych testów, dodatkowy test test_import_mutation oraz oba deterministyczne race’y przeszły.
- Rollback state/FileState/manifest/registry i committed metadata został potwierdzony w obu race’ach.
- Zmieniono wyłącznie engine.py oraz walkthrough.md. Nie zmieniano testów; nie uruchamiano FULL; bez ownera, listenera, restartu, staging, commit i push.

**INFERENCE**

- Wyniki potwierdzają wymagany zakres zachowania dla pustych, równych i różnych niepustych fingerprintów w sprawdzonych ścieżkach.
