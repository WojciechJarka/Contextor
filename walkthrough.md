# SP-T4-POSTFULL-R2 — CANDIDATE MOCK CONTRACT

## PRECHECK

- **DIRECT_EVIDENCE — Contextor MCP przed zmianą:** LIVE revision 1461, provenance=live, canonical_state=fresh, resync_required=false. Globalne workspace_sync=unverified; plik testowy per-file workspace_sync=verified.
- **DIRECT_EVIDENCE — Git przed zmianą:** HEAD 3f3250d6c0f5d8a5e669b8019b9ee32397a9f0a3. Status zawierał wyłącznie wcześniejszy walkthrough.md; test i produkcja były czyste.
- **DIRECT_EVIDENCE — interpreter:** C:\Temp\Contextor_Repo\.venv\Scripts\python.exe, CPython 3.15.2.
- **DIRECT_EVIDENCE — anchor MCP i lokalny:** tests/test_incremental_phase_trace.py:_candidate(), pole modules={} przy linii 70, w konstrukcji SimpleNamespace.

## EXACT_CHANGE

W _candidate() dodano wyłącznie typing_guard_evidence={} bezpośrednio po modules={}. Pozostałe pola i wartości helpera, testy, _engine(), _outcome(), _run() oraz kod produkcyjny pozostały bez zmian.

## TARGETED_RESULTS

Uruchomiono jednym poleceniem wyłącznie cztery podane node IDs z --tb=long:

- test_identity_sync_success_emits_order_and_no_missing_owners — PASS
- test_non_identity_path_emits_skip_and_default_lineage_scope — PASS
- test_registry_diagnostic_gap_is_observed_without_repair_or_raise — PASS
- test_identity_sync_lineage_failure_propagates_without_file_state — PASS

Wynik procesu: 4 passed in 0.96s. Nie wystąpiły FAIL ani tracebacki. Nie uruchamiano całego pliku ani pełnego pytest.

## MOCK_CONTRACT

- **CODE_PATH_PROVED:** bieżący engine publikuje candidate.typing_guard_evidence do RepositoryAnalysisState. Fabryka _candidate() tworzyła SimpleNamespace bez tego pola; dodanie go dopasowuje wymagany atrybut publikacji wykorzystywany przez testowy mock.
- **DIRECT_EVIDENCE — MCP post-change:** Desktop watcher zgłosił revision 1462, operation=update_file, origin=desktop_watcher, status=UPDATED dla tests/test_incremental_phase_trace.py. Per-file workspace_sync=verified na revision 1462.
- Testy nadal monkeypatchują engine_module.execute_refresh_plan. PASS potwierdza ścieżki _apply_delta_and_commit po dostarczeniu syntetycznego PlanExecutionOutcome i candidate; nie wykonuje prawdziwego execute_refresh_plan.
- _candidate() pozostaje ręcznie utworzonym SimpleNamespace, niezależnym od RepositoryAnalysisState i _prepare_candidate_state. Pozostałe syntetyczne wartości candidate/outcome nie zostały w tym zadaniu zmienione ani zweryfikowane jako pełny wynik rzeczywistego executora.

## LIMITATIONS

- **DIRECT_EVIDENCE — LIVE:** canonical revision=1462, provenance=live, canonical_state=fresh, resync_required=false. Globalne workspace_sync=unverified.
- Syntax diagnostics: 0/fresh; graph=fresh; cycles=fresh, structural count=16; cycle_semantics family=stale.
- Diagnostyka LIVE dotyczy repozytorium i nie zastępuje wyników czterech testów. Zmiana była wyłącznie testowa, więc restart nie był wymagany; nie wywołano MCP update_file.
- HEAD pozostał 3f3250d6c0f5d8a5e669b8019b9ee32397a9f0a3. Bez zmian produkcji i issues.md.

## FILES_CHANGED

- tests/test_incremental_phase_trace.py — dodano jedno pole mock candidate.
- walkthrough.md — raport bieżącego zadania; raport nie jest wliczony do FULL_DIFFS.

## FULL_DIFFS

~~~diff
diff --git a/tests/test_incremental_phase_trace.py b/tests/test_incremental_phase_trace.py
index 6834cfe..6166b76 100644
--- a/tests/test_incremental_phase_trace.py
+++ b/tests/test_incremental_phase_trace.py
@@ -67,7 +67,7 @@ class FakeStateManager:
 
 def _candidate():
     return SimpleNamespace(
-        modules={}, reexport_facts_by_module={},
+        modules={}, typing_guard_evidence={}, reexport_facts_by_module={},
         artifacts={},
         layer_information={},
         module_parse_freshness={},
~~~

