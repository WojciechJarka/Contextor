# F1-I1 — korekta dwóch przestarzałych testów get_analysis_status

FILES_CHANGED: tests/mcp/tools/test_analysis_status_concurrency.py
walkthrough.md jest raportem i pozostaje wyłączony z listy plików wymagających diffu.
Nie zmieniono produkcji, dokumentacji, fixture, helperów ani pozostałych testów.

## PREFLIGHT

DIRECT_EVIDENCE:
- Contextor MCP jako pierwsze źródło potwierdził test file w canonical_revision=1575, canonical_state=fresh, workspace_sync=verified, provenance=live; syntax diagnostics: checked_and_none, errors=[], source_path zgodny z plikiem.
- Contextor pobrał kompletne ciała obu funkcji, odpowiednio tests/mcp/tools/test_analysis_status_concurrency.py:952-967 i :982-999. Kontrakt fixture jest zgodny z raportem F1-D1:
  - job 1 ma status running w pierwszym teście oraz queued w drugim;
  - oba używają owner_pid=os.getpid()+100000;
  - nowsze rekordy terminalne pozostają bez zmian: job 2 completed w pierwszym; job 2 failed i job 3 completed w drugim;
  - timestampy mtime pozostają 1_000_000_000, 2_000_000_000 i 3_000_000_000 ns zgodnie z testem.
- HEAD przed zmianą: 5b15765534e96329e06dfc5c44074b411c3983b0. Git status przed zmianą: main zgodny z origin/main; pre-existing M CHANGELOG.md i M walkthrough.md; test nie był wcześniej zmieniony. Pliku CHANGELOG.md nie dotykano.
- Contextor potwierdził bieżący kontrakt produkcji w contextor/mcp/tools/get_analysis_status.py:59-62: przy dokładnie jednym aktywnym zadaniu wybierany jest active_jobs[0]; przy zerowej liczbie aktywnych wybierany jest najnowszy rekord trwały. W :72-98 obcy owner_pid powoduje status interrupted i error owner_process_changed. MCP docs get_analysis_status opisują „One active job is preferred”.

INFERENCE:
- Fixture nie zmienił się względem F1-D1; nie było podstaw do BLOCKED. Oczekiwany wynik wynika z aktualnego kodu i dokumentacji, a nie z założenia dopisanego do testu.

## ROOT_CAUSE

DIRECT_EVIDENCE:
- Dwie stare asercje oczekiwały nowszego terminalnego rekordu mimo jednego starszego queued/running. Historia F1-D1 wykazała, że produkcja i dokumentacja przeszły na priorytet pojedynczego active w commicie 4c0a37f, bez aktualizacji tych asercji.
- W obu fixture job 1 ma obcy owner_pid. Po wyborze job 1 gałąź get_analysis_status ustawia interrupted oraz owner_process_changed. Nowszy terminalny rekord nie jest wybrany przy jednym active.

INFERENCE:
- Przyczyną poprzedniego FAIL było przestarzałe oczekiwanie testowe; korekta asercji dopasowuje je do obecnego publicznego kontraktu. Produkcja pozostała niezmieniona.

## EXACT_TEST_CORRECTIONS

DIRECT_EVIDENCE:
- Linia 952: nazwa zmieniona na test_analysis_status_concurrency__single_active_is_preferred_over_newer_completed.
- W pierwszym teście asercje statusu i job_id zastąpiono oczekiwaniami interrupted, ID 00000000000000000000000000000001 oraz error=owner_process_changed (:966-968).
- Linia 983: nazwa zmieniona na test_analysis_status_concurrency__single_queued_job_is_preferred_over_terminal_jobs.
- W drugim teście usunięto wyłącznie komentarz o wyborze najnowszego terminalnego rekordu; asercje zastąpiono tymi samymi trzema oczekiwaniami (:997-1000).
- Konstrukcje rekordów, statusy, owner_pid, timestampy, helper _create_job i pozostałe testy są niezmienione.

## TARGETED_TESTS

DIRECT_EVIDENCE:
- Uruchomiono dokładnie:
    .venv/Scripts/python.exe -m pytest -q tests/mcp/tools/test_analysis_status_concurrency.py -k "single_active_is_preferred_over_newer_completed or single_queued_job_is_preferred_over_terminal_jobs" -vv
  Wynik: 2 passed, 59 deselected, 2 warnings, 7.78 s. Asercje error=owner_process_changed przeszły; nie uruchamiano dodatkowego odczytu res ani nie dostosowywano oczekiwań.
- Uruchomiono dokładnie:
    .venv/Scripts/python.exe -m pytest -q tests/mcp/tools/test_analysis_status_concurrency.py
  Wynik: 61 passed, 2 warnings, 7.89 s.
- Nie uruchomiono pełnego pytest ani innych testów.

## MCP_POST_CHANGE

DIRECT_EVIDENCE:
- Po edycji Contextor zgłosił canonical_revision=1576, canonical_state=fresh, workspace_sync=verified, provenance=live dla zmienionego test file.
- Syntax diagnostics pliku: checked_and_none, materialized=true, errors=[], total=0.
- Watcher event: revision=1576, operation=update_file, origin=desktop_watcher, status=UPDATED, file_path=tests/mcp/tools/test_analysis_status_concurrency.py. Ciągłość od revision 1575: continuous, resync_required=false.
- Niezmieniony produkcyjny plik contextor/mcp/tools/get_analysis_status.py pozostał canonical_state=fresh i workspace_sync=verified przy revision 1576. Jego gałąź one-active-first (:59-62) oraz owner_process_changed (:72-98) zgadzają się z poprawionymi testami. Oba testy wywołują implementację bezpośrednio; weryfikacja kontraktu pochodzi ze źródła i MCP docs, a wynik testów potwierdza słownik res w asercjach.

UNKNOWN:
- Nie sprawdzano adopcji zmiany przez proces MCP poza obserwowanym watcher event; nie zmieniano kodu MCP/runtime i nie wykonywano restartu.

## FULL_DIFFS

DIRECT_EVIDENCE — kompletny diff tests/mcp/tools/test_analysis_status_concurrency.py z git diff:

    diff --git a/tests/mcp/tools/test_analysis_status_concurrency.py b/tests/mcp/tools/test_analysis_status_concurrency.py
    index e44309b..8608831 100644
    --- a/tests/mcp/tools/test_analysis_status_concurrency.py
    +++ b/tests/mcp/tools/test_analysis_status_concurrency.py
    @@ -949,7 +949,7 @@ def test_analysis_status_concurrency__explicit_job_id_bypasses_ambiguity(tmp_pat
         assert res["job_id"] == j1["job_id"]
     
     
    -def test_analysis_status_concurrency__single_active_does_not_override_newer_completed_latest(tmp_path):
    +def test_analysis_status_concurrency__single_active_is_preferred_over_newer_completed(tmp_path):
         root = tmp_path
         _create_job(
             root,
    @@ -963,8 +963,9 @@ def test_analysis_status_concurrency__single_active_does_not_override_newer_comp
         raw = get_analysis_status(str(root), job_id=None)
         res = json.loads(raw)
     
    -    assert res["status"] == "completed"
    -    assert res["job_id"] == j2["job_id"]
    +    assert res["status"] == "interrupted"
    +    assert res["job_id"] == "00000000000000000000000000000001"
    +    assert res["error"] == "owner_process_changed"
     
     
     def test_analysis_status_concurrency__zero_active_preserves_latest_terminal(tmp_path):
    @@ -979,7 +980,7 @@ def test_analysis_status_concurrency__zero_active_preserves_latest_terminal(tmp_
         assert res["job_id"] == j2["job_id"]
     
     
    -def test_analysis_status_concurrency__completed_jobs_do_not_count_as_active(tmp_path):
    +def test_analysis_status_concurrency__single_queued_job_is_preferred_over_terminal_jobs(tmp_path):
         root = tmp_path
         _create_job(
             root,
    @@ -994,9 +995,9 @@ def test_analysis_status_concurrency__completed_jobs_do_not_count_as_active(tmp_
         raw = get_analysis_status(str(root), job_id=None)
         res = json.loads(raw)
     
    -    # active_count is 1 (job 1), so no ambiguity; latest mtime is job 3 (completed)
    -    assert res["status"] == "completed"
    -    assert res["job_id"] == j3["job_id"]
    +    assert res["status"] == "interrupted"
    +    assert res["job_id"] == "00000000000000000000000000000001"
    +    assert res["error"] == "owner_process_changed"
     
     
     def test_analysis_status_concurrency__active_candidates_are_deterministic_newest_first(tmp_path):
    
## FINAL_STATUS

- Zmieniono wyłącznie dwie wskazane funkcje w tests/mcp/tools/test_analysis_status_concurrency.py.
- Testy celowane: 2 passed; cały wskazany plik: 61 passed.
- Post-change LIVE state: revision 1576, fresh, workspace_sync verified, syntax diagnostics bez błędów, watcher event potwierdzony.
- Bez zmian produkcji, dokumentacji, fixture/helperów, pozostałych testów; bez FULL, commit, push, staging i restartów.

