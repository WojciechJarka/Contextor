# GRAPH-R14-I1 — FULL ANALYSIS SOURCE/FILESTATE INTEGRITY

## PREFLIGHT

**DIRECT_EVIDENCE** — Contextor MCP jako pierwsze źródło: przed zmianą contextor/core/api/facade.py miał revision 1586, canonical state fresh, provenance live, workspace_sync=verified; syntax diagnostics: 0. HEAD przed i po zmianie: 84c7af6e5dca9ff0b22daf1fa311f70551eb9c8b.

**DIRECT_EVIDENCE** — przed patchem git status --short wykazywał wyłącznie wcześniejszą modyfikację walkthrough.md. Po patchu i testach: M contextor/core/api/facade.py oraz M walkthrough.md. Testy nie zmieniły plików. Raport jest jedynym dodatkowym plikiem zmienionym zgodnie z wymaganiem raportowania.

**DIRECT_EVIDENCE** — dokładny anchor w metodzie ContextorFacade.analyze_project był bezpośrednio przed component_started = time.monotonic(), po przygotowaniu file_state_payload i stanu, przed save_engine_state(...). Patch dopasował ten anchor; nie zmieniano innych miejsc w facade.py.

**CONTRACT_PROVED** — sprawdzono semantykę kontraktu niezależnie od oczekiwanego wyniku testu: indeksator przypisuje SHA-256 do identyfikatora modułu, a FileState jest aktualizowany dla module.absolute_path i payload jest indeksowany tą ścieżką. Kontrola zestawia zatem dwa fingerprinty tego samego zmaterializowanego modułu, bez ponownego odczytu źródła i bez nadpisywania któregokolwiek fingerprintu.

**INFERENCE** — odmowa przed save_engine_state zapobiega zapisaniu nowej committed generation w ścieżce tego wywołania. Nie oznacza to rollbacku raportów ani plików pomocniczych zapisanych wcześniej przez pipeline.

## LITERAL_PATCH

**DIRECT_EVIDENCE** — do contextor/core/api/facade.py, w ContextorFacade.analyze_project, dodano wyłącznie poniższy blok bezpośrednio przed końcowym pomiarem i save_engine_state(...) (aktualnie linie 1594–1625; wywołanie zapisu zaczyna się w linii 1627):

~~~python
            indexed_fingerprints = index.source_fingerprints_by_module
            committed_files = (
                file_state_payload.get("files")
                if isinstance(file_state_payload, dict)
                else None
            )
            if not isinstance(committed_files, dict):
                raise RuntimeError(
                    "Full analysis FileState payload is unavailable"
                )

            for module_id, module in state.modules.items():
                expected_sha256 = indexed_fingerprints.get(module_id)
                file_record = committed_files.get(module.absolute_path)
                actual_sha256 = (
                    file_record.get("sha256")
                    if isinstance(file_record, dict)
                    else None
                )

                if not expected_sha256 or not actual_sha256:
                    raise RuntimeError(
                        "Missing trusted source SHA-256 for "
                        f"module {module_id}"
                    )

                if actual_sha256 != expected_sha256:
                    raise RuntimeError(
                        "Source changed during full analysis: "
                        f"{module_id}"
                    )
~~~

**DIRECT_EVIDENCE** — nie zmieniono index_repository, _process_single_file, execute_global_pipeline, FileStateManager, save_snapshot, publish_committed_and_wait ani entrypointów MCP/Desktop. Nie dodano retry, nowego API ani warunku opartego o nazwę modułu/importu.

## MODULE_FINGERPRINT_COVERAGE

**DIRECT_EVIDENCE** — RepositoryIndex.source_fingerprints_by_module jest mapą dict[str, str] w contextor/core/symbol_engine/indexer.py:1669–1709. record_indexed_source_fingerprint w tym pliku (1958–1986) odrzuca nieprawidłowe wejście i zapisuje lowercase 64-znakowy SHA-256 pod module_id. Ścieżki indeksowania inline i worker zapisują fingerprint pod tym samym ID, pod którym indeksator materializuje moduł (m.in. okolice 2857 i 3017).

**DIRECT_EVIDENCE** — ContextorFacade.analyze_project pobiera moduły z wyniku indeksatora; RepositoryAnalysisState.modules jest mapą identyfikatora do modułu (contextor/core/analysis/state_manager.py:87–110). Klasyfikacja type-only modyfikuje istniejące klucze, nie tworzy nowych identyfikatorów (indexer.py:647–779, 2784–2826).

**CODE_PATH_PROVED** — nowa pętla przechodzi po każdym wpisie state.modules; brak mapy fingerprintów dla któregokolwiek wpisu kończy analizę błędem. Pliki pominięte przez indeksator i nieobecne w state.modules nie są dodawane do kontroli.

**DIRECT_EVIDENCE** — kontrolowany stabilny przebieg z trzema syntetycznymi plikami (dep_alpha.py, dep_beta.py, consumer.py) zakończył się powodzeniem, więc kontrola przeszła dla materializowanych modułów tego fixture.

**UNKNOWN** — nie wykonano osobnego przebiegu wymuszającego brak pojedynczego indeksatorowego fingerprintu. Odmowę tego przypadku potwierdza kod, nie eksperyment runtime.

## FILESTATE_MAPPING

**DIRECT_EVIDENCE** — execute_global_pipeline w contextor/core/reporting_engine/pipeline.py:575–635 iteruje po modules.items(), bierze module.absolute_path, aktualizuje nim FileStateManager i zachowuje ten klucz ścieżki dla FileState. FileStateManager.build_payload w contextor/core/analysis/state_manager.py:454–462 zwraca {"_meta": ..., "files": {...}}; kluczem files jest śledzona ścieżka, a rekord zawiera między innymi mtime_ns, size, sha256.

**CODE_PATH_PROVED** — nowa kontrola mapuje module_id → state.modules[module_id].absolute_path → file_state_payload["files"][absolute_path]["sha256"] i porównuje z index.source_fingerprints_by_module[module_id]. Nie oblicza fingerprintu przez późniejszy odczyt source.

**DIRECT_EVIDENCE** — w stabilnym fixture produkcyjny reader zweryfikował committed snapshot, a FileState rekordu consumer.py miał SHA-256 równy fingerprintowi indeksatora.

## MISSING_SHA_BEHAVIOR

**CODE_PATH_PROVED** — brak obiektu file_state_payload["files"] typu dict powoduje RuntimeError("Full analysis FileState payload is unavailable").

**CODE_PATH_PROVED** — brak albo pusty indeksatorowy SHA-256 lub brak/pusty SHA-256 rekordu FileState powoduje RuntimeError("Missing trusted source SHA-256 for module {module_id}"). Brak danych nie jest zgodnością.

**UNKNOWN** — osobny eksperyment z celowo usuniętym rekordem lub fingerprintem nie był wymagany i nie został wykonany. Nie zgłaszam dynamicznego PASS dla tej gałęzi.

## MISMATCH_BEHAVIOR

**CODE_PATH_PROVED** — dwa niepuste fingerprinty są porównywane przed rozpoczęciem końcowego pomiaru publikacji i przed save_engine_state. Nierówność powoduje RuntimeError("Source changed during full analysis: {module_id}").

**DIRECT_EVIDENCE** — kontrolowany wyścig zmienił consumer.py po powrocie oryginalnego index_repository, z A (import dep_alpha) na B (import dep_beta). Indeksator zachował SHA(A); FileState payload powstał po zmianie i miał SHA(B). Wywołanie odmówiło committed save dokładnie z Source changed during full analysis: consumer.

**INFERENCE** — odmowa nie zapisuje FileState SHA(B) razem z Module.imports z A, ponieważ wyjątek wystąpił przed wejściem do save_engine_state. Wynik został dodatkowo sprawdzony przez porównanie metadanych oraz walidowany reader poniżej.

## STABLE_FULL_ANALYSIS

**DIRECT_EVIDENCE** — wykonano CPython 3.15.2 i produkcyjną ścieżkę run_full_analysis_exclusive → ContextorFacade.analyze_project → indeksator/pipeline/persister na izolowanym repozytorium stable-b/repo. Nie uruchamiano LIVE ownera, listenera ani backendu MCP.

Wynik:
- errors=[]; zwrócono AnalysisResult.
- consumer.py treść B: import dep_beta.
- indeksatorowy SHA(B) i committed FileState SHA(B): 333dd7a004a385d35952f3e8de128b1f6ec5379b57a408c5ca480d4522124d75.
- Module.imports: ["dep_beta"].
- hard edge: consumer → dep_beta; soft edges: [].
- produkcyjny reader zwalidował snapshot; metadane readera zgadzały się z aktywną metadaną (reader_metadata_matches=true).
- repo_id: ctx_407bb5ab; root: katalog tymczasowy stable-b/repo; revision: 1; state_id: 20261127_183228.
- endpoint LIVE nie istniał; wynik live_publish_status="not_attempted".

**DIRECT_EVIDENCE** — wszystkie katalogi repo/cache/output/state/registry eksperymentu znajdowały się pod nowym TemporaryDirectory: C:\Users\DafoO\AppData\Local\Temp\contextor-graph-r14-d83gi0gq. Ustawiono przed importem Contextora CONTEXTOR_CACHE_DIR, CONTEXTOR_OUTPUT_DIR, CONTEXTOR_STATE_DIR i CONTEXTOR_REGISTRY_DIR na podkatalogi tego rootu oraz CONTEXTOR_DISABLE_PROCESS_POOL=1.

**CONTRACT_PROVED** — runtime_trace.runtime_logs_dir() zwraca state_dir() / "logs" (contextor/core/paths.py:37–40), a state_dir() respektuje CONTEXTOR_STATE_DIR (paths.py:310–324). trace_event wyznacza ścieżkę przez aktywny pointer; bez niego nie dopisuje rekordu. Ponieważ katalog state był nowy i ustawiony pod TemporaryDirectory, ścieżka ewentualnego trace również pozostawała w tym katalogu. Nie zmieniano globalnych ustawień aktywnego backendu.

**DIRECT_EVIDENCE** — katalog tymczasowy został usunięty po eksperymencie i sprawdzono, że już nie istnieje. Nie zapisano w aktywnym cache/store Contextora.

## CONTROLLED_RACE

**DIRECT_EVIDENCE** — fixture race miał stabilną, wcześniej committed generację A: consumer.py zawierał import dep_alpha, SHA(A) a4d7debd525117aec714e16ba88ad33d5b1dbdfa24467fd5cba79d910e6bf2cb; jej zwalidowany snapshot zawierał Module.imports=["dep_alpha"] i hard edge consumer → dep_alpha.

**DIRECT_EVIDENCE** — wrapper wywołał oryginalny index_repository, a dopiero po jego powrocie zapisał wariant B. To był kontrolowany punkt zmiany; sleep ani timing losowy nie użyto. Indeksatorowa mapa dla consumer zachowała SHA(A); FileState odczytał B, SHA(B) 333dd7a004a385d35952f3e8de128b1f6ec5379b57a408c5ca480d4522124d75.

**DIRECT_EVIDENCE** — run_full_analysis_exclusive propagował RuntimeError: Source changed during full analysis: consumer. Nie zwrócono sukcesu analizy. Eksperyment nie tworzył LIVE ownera/listenera; endpoint dla izolowanego repo nie istniał.

**INFERENCE** — kontrolowany punkt testuje granicę indexer → późniejszy FileState acknowledgment bez zastępowania produkcyjnego indeksatora, pipeline ani persistera. Nie jest testem mutacji aktywnego repo Contextora.

## COMMITTED_GENERATION_VERIFICATION

**DIRECT_EVIDENCE** — przed wyścigiem metadane race generation wynosiły: repo_id ctx_596ee7a5, revision 1, state_id 20261127_183228, root w tym samym TemporaryDirectory. Po odmowie metadana była identyczna (metadata_unchanged=true).

**DIRECT_EVIDENCE** — istniejący walidowany locked_committed_snapshot odczytał snapshot po wyścigu. Reader potwierdził zgodność metadanych; snapshot nadal zawierał A: Module.imports=["dep_alpha"], hard edge consumer → dep_alpha, FileState SHA(A). Nie użyto bezpośredniego pickle.load.

**CODE_PATH_PROVED** — nowa kontrola stoi przed save_engine_state; run_full_analysis_exclusive propaguje wyjątek z facade, a lease jest zwalniany w finally (contextor/core/analysis/full_analysis_coordinator.py:41–128). W tej ścieżce nie dochodzi do committed generation save ani dalszej publikacji LIVE.

**DIRECT_EVIDENCE** — pipeline może wcześniej utworzyć raporty i pomocniczy file_state.json w izolowanych katalogach output/cache. Nie stwierdzono rollbacku tych plików i nie deklaruje się atomowości całego output directory. Gwarancja dotyczy odmowy committed generation.

## TARGETED_PYTEST

**DIRECT_EVIDENCE** — MCP potwierdził node ID oraz treść dwóch wymaganych testów:
- tests/test_live_watcher_startup_reconciliation.py::test_full_analysis_publishes_current_filestate_generation
- tests/test_full_analysis_coordination.py::test_lease_is_held_during_publication

Pierwsze uruchomienie: **2 passed in 3.97s**.

MCP potwierdził także istniejący test persistence failure:
- tests/test_live_state_store.py::test_cleanup_failure_cannot_mask_persistence_failure_or_leak_lock

Uruchomienie trzech celowanych testów: **3 passed in 2.30s**. Pełny pytest suite nie uruchamiano.

## POST_CHANGE_MCP

**DIRECT_EVIDENCE** — po zmianie get_live_events(after_revision=1586) wykazał revision 1587, desktop_watcher, update_file, UPDATED, ciągłość rewizji i resync_required=false.

**DIRECT_EVIDENCE** — get_symbol_implementation dla ContextorFacade.analyze_project potwierdził po zmianie canonical_state=fresh, revision 1587, provenance live, workspace_sync=verified. get_file_edit_context dla facade.py, indexer.py i state_manager.py pokazał revision 1587, syntax checked_and_none, errors []. Source range potwierdził dosłowny guard przed save_engine_state.

**DIRECT_EVIDENCE** — lineage dla ContextorFacade.analyze_project rozwiązał się w revision 1587 z kompletnymi semantic anchor bindings. Sam wynik lineage oznaczał workspace_sync=unverified; nie używam go jako dowodu synchronizacji source. Tę gwarancję potwierdzają oddzielnie powyższe odczyty implementacji/edit context.

**DIRECT_EVIDENCE** — post-change git diff zawiera tylko zamierzony blok w facade.py; HEAD pozostał bez zmian. Backenda nie restartowano. Nowy kod na dysku nie jest dowodem adopcji przez wcześniej działający proces.

## FULL_DIFFS

FILES_CHANGED:
- contextor/core/api/facade.py — jedyny zmieniony plik source.
- walkthrough.md — raport zadania; jego własny diff nie jest raportowany.

ACTUAL_DIFF — pełny rzeczywisty diff contextor/core/api/facade.py:

~~~diff
diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index aa5eaaf..6432926 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1591,6 +1591,38 @@ class ContextorFacade:
                         "prepared_optional_scc_preparation"
                     ] = cycle_source_preparation
 
+            indexed_fingerprints = index.source_fingerprints_by_module
+            committed_files = (
+                file_state_payload.get("files")
+                if isinstance(file_state_payload, dict)
+                else None
+            )
+            if not isinstance(committed_files, dict):
+                raise RuntimeError(
+                    "Full analysis FileState payload is unavailable"
+                )
+
+            for module_id, module in state.modules.items():
+                expected_sha256 = indexed_fingerprints.get(module_id)
+                file_record = committed_files.get(module.absolute_path)
+                actual_sha256 = (
+                    file_record.get("sha256")
+                    if isinstance(file_record, dict)
+                    else None
+                )
+
+                if not expected_sha256 or not actual_sha256:
+                    raise RuntimeError(
+                        "Missing trusted source SHA-256 for "
+                        f"module {module_id}"
+                    )
+
+                if actual_sha256 != expected_sha256:
+                    raise RuntimeError(
+                        "Source changed during full analysis: "
+                        f"{module_id}"
+                    )
+
             component_started = time.monotonic()
             meta = save_engine_state(
                 state,
~~~

## CONCLUSIONS

**DIRECT_EVIDENCE** — zgodny stabilny przebieg B utworzył zwalidowaną generation z Module.imports, grafem i FileState dla B. Kontrolowana zmiana A→B po indeksacji została odrzucona przed committed save, a poprzednia generation A pozostała niezmieniona według metadanych i walidowanego readera.

**CODE_PATH_PROVED** — brak payloadu lub SHA odmawia analizy; różne niepuste SHA odmawiają committed save; zgodne SHA kontynuują istniejącą ścieżkę save_engine_state i publikacji bez zmiany jej kontraktu.

**UNKNOWN** — nie badano awarii po zakończeniu kontroli, lecz przed lub w trakcie dalszego zapisu; nie deklaruje się pełnego rollbacku output directory. Działający backend nie został zrestartowany, więc adopcja nowego kodu przez istniejący proces pozostaje niepotwierdzona.

**FINAL** — literalna kontrola source fingerprint ↔ FileState jest wdrożona w jedynym wskazanym pliku source. Wymagane focused tests i stabilny/wyścigowy eksperyment izolowany przeszły.

