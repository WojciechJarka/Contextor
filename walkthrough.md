# GRAPH-R15-I1 — TRWAŁE REGRESJE SOURCE/FINGERPRINT INTEGRITY

## PREFLIGHT

**DIRECT_EVIDENCE** — Contextor MCP przed edycją: canonical revision 1587; _real_baseline i _assert_failed_update_atomic z tests/test_incremental_failed_commit_atomicity.py miały workspace_sync=verified; implementacje produkcyjnych guardów incremental oraz store readera także były świeże i zsynchronizowane.

**DIRECT_EVIDENCE** — HEAD: 82e6943c886bea730559c916c8b710e652a693fb; początkowy git status --short był pusty. Test atomowości miał 216 linii i kończył się testem test_failed_candidate_report_before_publication_is_atomic. Plik tests/test_full_analysis_source_fingerprint_atomicity.py nie istniał.

**DIRECT_EVIDENCE** — istniejące helpery:
- _real_baseline(tmp_path: Path, sources: dict[str, str]) -> _Baseline w liniach 54–82: tworzy repo tymczasowe, uruchamia pełną analizę, hydratuje engine i zapisuje baseline state/FileState/manifest/registry/metadata.
- _assert_failed_update_atomic(baseline: _Baseline, case: str, acknowledgement_calls: int) -> None w liniach 89–134: porównuje identity i projekcję canonical state, FileState, manifest, registry checkpoint i metadata committed generation.
- anchor na końcu pliku potwierdzony przez Contextor: linie 194–216.

**CONTRACT_PROVED** — locked_committed_snapshot w contextor/core/live_state/store.py:2039–2057 ma dekorator @contextmanager, pobiera store lock, wykonuje yield load_snapshot(...) i zwalnia lock w finally. load_snapshot weryfikuje snapshot i zwraca payload, metadata (linia 2609). Unpack (state, metadata) z polecenia jest zgodny z rzeczywistym kontraktem.

**DIRECT_EVIDENCE** — incremental guardy istnieją w bieżącym produkcyjnym kodzie: semantic no-op przy engine.py:835–875 i commit path przy engine.py:1270–1310. Oba porównują tracked SHA z fingerprintem przygotowanego źródła i rzucają RuntimeError("Source changed during incremental analysis") dla niepustych, różnych SHA.

## LITERAL_TEST_EDITS

**DIRECT_EVIDENCE** — wstawiono dokładnie dwa wskazane testy na końcu tests/test_incremental_failed_commit_atomicity.py oraz utworzono wskazany plik z dokładną treścią testu pełnej analizy. Zmian produkcyjnych nie wykonywano.

**DIRECT_EVIDENCE** — nie utrwalono tych edycji. Po pierwszym przebiegu wskazany test pełnej analizy nie przechodził jeszcze w swoim stabilnym przygotowaniu fixture: pełna analiza zgłosiła kolizję nazw VALUE między syntetycznymi modułami, zanim doszła do monkeypatcha indeksatora ani do zmiany source A→B. Polecenie wymaga dokładnie tej treści, więc nie zmieniałem nazw ani walidacji. Zgodnie z fail-closed, wycofałem wyłącznie swoje testowe dodatki. Nowy plik usunięto; plik incremental przywrócono do HEAD.

**DIRECT_EVIDENCE** — po wycofaniu testowych dodatków git status --short jest czysty; nie pozostał żaden diff source/test. W raporcie nie prezentuję odrzuconego patcha jako rzeczywistego diffu.

## INCREMENTAL_UPDATED_RACE

**DIRECT_EVIDENCE** — pierwszy celowany pytest przebiegł testem test_source_change_after_prepare_rejects_updated_commit; test przeszedł.

**CONTRACT_PROVED** — test tworzy baseline przez _real_baseline, zapisuje wariant A z dodatkowym symbolem, a wrapper wywołuje prawdziwe prepare_source_update, po czym deterministycznie zapisuje wariant B. Oczekuje dokładnego RuntimeError. _assert_failed_update_atomic sprawdza rollback canonical state, FileState, manifest, registry i committed metadata. Końcowe has_changed(source) potwierdza, że B wymaga ponownej analizy.

## INCREMENTAL_NOOP_RACE

**DIRECT_EVIDENCE** — ten sam celowany pytest przebiegł test_source_change_after_prepare_rejects_semantic_noop; test przeszedł.

**CONTRACT_PROVED** — wariant A to zmiana komentarza, a test potwierdza prepared.delta.imports_added == []; wrapper zmienia source na B po przygotowaniu. RuntimeError oraz _assert_failed_update_atomic potwierdzają odmowę i rollback. Końcowe has_changed(source) potwierdza pozostawienie B do ponownej analizy.

**LIMITATION** — helper _assert_failed_update_atomic sprawdza wszystkie wymienione wyżej struktury w RAM i metadata committed; testy te nie są odczytem LIVE ownera ani listenera.

## FULL_ANALYSIS_RACE

**DIRECT_EVIDENCE** — uruchomiono wskazany nowy test. Zawiódł on przed uzyskaniem stabilnej baseline generation, na tests/test_full_analysis_source_fingerprint_atomicity.py:55:

~~~text
assert not errors, errors
AssertionError: [ValidationError(kind='NAME_COLLISION', message="Semantic API collision for variable 'VALUE' across modules: consumer,...", artifact_type='variable', is_identical=False)]
~~~

Testowe źródła definiują VALUE w dep_alpha.py, dep_beta.py i consumer.py. Pełna analiza odmawia już pierwszego run_full_analysis_exclusive; funkcja change_source_after_index nie została podłączona i source nie został zmieniony przez race wrapper. Zatem test nie dostarcza dowodu na wynik pełnoanalitycznego wyścigu ani na zachowanie starej generation.

**INFERENCE** — kolizja jest niezależna od fingerprint guardu. Zmiana VALUE na unikalne nazwy mogłaby pozwolić fixture przejść, ale byłaby zmianą wymaganej literalnej treści. Nie zastosowałem tej korekty bez poprawionego polecenia.

## ROLLBACK_AND_GENERATION

**DIRECT_EVIDENCE** — oba incremental race’y zakończyły się PASS; asercje helpera obejmowały rollback state/FileState/manifest/registry oraz niezmienność committed metadata. B pozostało wykrywane jako zmieniony source.

**UNKNOWN** — pełnoanalityczny test nie dotarł do zapisu metadata ani do locked_committed_snapshot, bo jego pierwsza stabilna analiza zwróciła NAME_COLLISION. Nie ma z tego przebiegu dowodu, że generation pozostała stara ani że reader odczytał ją po wyścigu.

**DIRECT_EVIDENCE** — nie uruchamiano LIVE ownera, listenera ani testu na aktywnym store. Nieudana pełna analiza użyła tmp_path oraz ustawiła cache/output/state/registry pod tym katalogiem; nie mutowała aktywnego Contextor LIVE/store.

## TARGETED_TESTS

**DIRECT_EVIDENCE** — pierwsze polecenie dla dwóch incremental testów i nowego full testu zakończyło się 2 passed, 1 failed in 15.59s. Dwa incremental race’y przeszły; nowy test full zawiódł w baseline na NAME_COLLISION.

**NOT_RUN** — ze względu na fail-closed nie uruchomiłem pełnego tests/test_incremental_failed_commit_atomicity.py, pełnego nowego pliku ani tests/test_live_watcher_startup_reconciliation.py::test_full_analysis_publishes_current_filestate_generation. Nie powtarzałem znanego failing fixture i nie zmieniałem go, by uzyskać zielony test.

**DIRECT_EVIDENCE** — nie uruchomiono FULL suite, restartu ani testu z aktywnym LIVE.

## POST_CHANGE_MCP

**DIRECT_EVIDENCE** — MCP preflight przed edycją potwierdził revision 1587, aktualne implementacje helperów, workspace sync verified i kontrakt store readera.

**NOT_RUN** — po fail-closed nie uruchamiałem MCP diagnostyki zmienionych testów ani ich call-context. Testowe edycje zostały wycofane; aktualny Git nie zawiera tych zmian. Nie używałem MCP update_file i nie restartowałem backendu.

## FULL_DIFFS

FILES_CHANGED:
- Brak source/test diffów. Testowe edycje wycofano po stwierdzeniu, że literalny full fixture nie przechodzi przez istniejącą walidację kolizji.
- walkthrough.md — raport zadania; self-diff raportu nie jest zamieszczany.

ACTUAL_DIFF=DIFFS=NONE

## CONCLUSIONS

**BLOCKED_SEMANTIC_INTEGRITY** — wymagany nowy test pełnej analizy nie osiąga warunku testowanego race’u: jego literalny stabilny fixture jest odrzucany z powodu kolizji top-level nazwy VALUE w trzech modułach. Nie zmieniałem wskazanej treści, ponieważ użytkownik wymagał exact content; nie maskowałem też walidacji.

**DIRECT_EVIDENCE** — dwa incremental testy przeszły i zweryfikowały rollback. Pełny test, dalsze wskazane testy oraz post-change MCP pozostają niezweryfikowane. Nie ma podstaw do zgłoszenia PASS całego zadania.

**WYMAGANE DO WZNOWIENIA** — poprawiona literalna zawartość full fixture z niekolidującymi nazwami albo jawna instrukcja, że można poprawić wyłącznie identyfikatory testowego fixture.
