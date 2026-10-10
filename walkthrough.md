# L32G_B2_COW_PARSE_FRESHNESS_FAIL_CLOSED_IMPLEMENTATION

## FILES_CHANGED_THIS_TASK

Pliki produkcyjne i testowe zmienione w tym zadaniu:

- C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py
- C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py
- C:\Temp\Contextor_Repo\tests\test_refresh_plan_execution.py
- C:\Temp\Contextor_Repo\tests\test_live_e2e_corrections.py
- C:\Temp\Contextor_Repo\tests\test_syntax_diagnostics_full_analysis.py
- C:\Temp\Contextor_Repo\tests\test_live_state_ipc.py

Raport zapisano w C:\Temp\Contextor_Repo\walkthrough.md. Diff raportu nie jest częścią FULL_DIFFS.

## CURRENT_SOURCE_VERIFICATION

Contextor MCP pobrał kompletne implementacje, bez preview i bez truncation:

- _prepare_candidate_state, plik C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\plan_executor.py, linie LIVE 681–765; source_contract: implementation_is_complete=true, no_partial_symbol_source=true.
- mark_module_parse_failure, plik C:\Temp\Contextor_Repo\contextor\core\analysis\state_manager.py, linie LIVE 272–296; source_contract: implementation_is_complete=true, no_partial_symbol_source=true.
- IncrementalAnalysisEngine._commit_syntax_candidate, plik C:\Temp\Contextor_Repo\contextor\core\analysis\incremental\engine.py, linie LIVE 126–206; pełna implementacja, workspace_sync=verified.

Bieżące bloki zmienione przez patch:

    raw_parse_freshness = getattr(
        state,
        "module_parse_freshness",
        {},
    )
    if not isinstance(raw_parse_freshness, dict):
        raise ValueError(
            "Canonical module_parse_freshness is invalid; "
            "fresh full analysis is required."
        )

CandidateState otrzymuje teraz:

    module_parse_freshness=dict(raw_parse_freshness),

W mark_module_parse_failure, po docstringu i przed odczytem mapy:

    truth = module_current_truth(state, module_name)
    if truth["state"] == "unavailable":
        raise ValueError(
            "Canonical module parse freshness is untrusted; "
            "fresh full analysis is required."
        )

Pozostała część mark_module_parse_failure jest bez zmian. Nie zmieniono module_current_truth, clear_module_parse_failure, RepositoryAnalysisState, clone_for_update, snapshot schema, parsera, lineage, LIVE IPC ani produkcyjnego Desktop watchera.

Contextor call context wykazał:
- _prepare_candidate_state ma jednego bezpośredniego callera w tym module: execute_refresh_plan, LIVE linia 799.
- IncrementalAnalysisEngine._commit_syntax_candidate ma dwa bezpośrednie wywołania z IncrementalAnalysisEngine.update_file, LIVE linie 588 i 636.
- _commit_syntax_candidate wywołuje mark_module_parse_failure w pełnej implementacji pobranej z LIVE.
- Contextor klasyfikuje get_symbol_call_context jako intra_module. Zewnętrzne wywołania potwierdzają źródło oraz file context, nie należy traktować tego grafu jako dowodu między-modułowej kompletności.
- get_file_edit_context podał dla plan_executor 10 bezpośrednich i 144 tranzytywne moduły konsumenckie; dla state_manager 84 bezpośrednie i 209 tranzytywnych. Liczby to statyczny blast-radius context, nie wynik wykonania runtime.

## RED_RESULT

Przed zmianami produkcyjnymi uruchomiono nowy, focused subset regresji. Wynik: 19 failed przed patchem, zgodnie z oczekiwanym RED.

Nieprawidłowe wartości całej mapy przechodziły przez dotychczasową normalizację/coercion, a ścieżki syntax failure, semantic no-op, updated/deleted i LIVE mutation nie odrzucały wymaganych przypadków. Nieznany marker celu mógł wejść w ścieżkę LKG. Po RED nie zmieniano wymagań testów; zastosowano dwa dokładne bloki produkcyjne określone w zadaniu.

## GREEN_RESULT

Po patchu:

- Nowe focused regresje wraz z wybranym zestawem LKG/snapshot/recovery i watcher requeue: 28 passed, 1 warning, 13.41 s.
- Pełne ukierunkowane pliki i wcześniejszy B1 lineage test:
  
      & .\.venv\Scripts\python.exe -m pytest -q tests/test_live_e2e_corrections.py tests/test_refresh_plan_execution.py tests/test_syntax_diagnostics_full_analysis.py tests/test_live_state_ipc.py tests/analysis/test_lineage_live_query.py

  Wynik: 211 passed, 1 warning, 102.16 s. Warning dotyczył deprecation Authlib z venv.
- In-memory compile() dla wszystkich sześciu zmienionych plików: OK; bez zapisu bytecode.
- git diff --check dla sześciu plików: exit 0, bez błędów whitespace. Git wypisał jedynie informację o przyszłej konwersji LF na CRLF.
- Nie uruchamiano pełnego repository pytest.

## COW_INPUT_MATRIX

Test _prepare_candidate_state odrzuca ValueError z komunikatem „Canonical module_parse_freshness is invalid” dla każdej wartości całej mapy:

| Wejście | Oczekiwane i sprawdzone |
|---|---|
| None | odrzucone; ta sama wartość pozostaje w stanie |
| False | odrzucone; bez normalizacji do {} |
| 0 | odrzucone; bez normalizacji do {} |
| pusty string | odrzucony |
| pusta lista | odrzucona |
| pusta krotka | odrzucona |
| pusty set | odrzucony |
| ["bad"] | odrzucone |
| 17 | odrzucone |
| [("provider", {"state": "stale"})] | odrzucone mimo możliwego dict(...) |

Kompatybilność valid/legacy sprawdzona:
- brak legacy atrybutu daje pusty candidate dict;
- prawidłowy pusty dict daje odrębny pusty outer dict;
- prawidłowe fresh i stale wpisy są shallow-copied, bez zmiany referencji nested entries;
- malformed individual entry w poprawnym outer dict zostaje bez zmian i zachowuje referencję;
- źródłowy outer dict i obiekt state nie są modyfikowane przez _prepare_candidate_state.

## SYNTAX_FAILURE_ATOMICITY

Rzeczywisty IncrementalAnalysisEngine fixture sprawdza parserem plik provider z błędem składni oraz malformed whole-map wartości None i listę par. update_file kończy się ValueError przed publikacją kandydata. Testy potwierdzają, że:
- dokładny obiekt mapy pozostaje w stanie źródłowym;
- modules i artifacts zachowują pierwotne obiekty;
- provider i unrelated pozostają unavailable;
- nie powstaje successful/RECOVERED update.

Osobny rzeczywisty syntax branch z wpisem provider={"state":"unknown"} kończy się ValueError z guardu mark_module_parse_failure. Ten sam wpis i mapa pozostają niezmienione, a provenance nadal jest untrusted.

## UNTRUSTED_TO_LKG_GUARD

Bezpośrednia regresja wywołuje mark_module_parse_failure na wpisie state="unknown"; funkcja odrzuca zmianę ValueError przed zapisem stale. Rzeczywisty syntax failure potwierdza ten sam guard przez _commit_syntax_candidate.

Granica kontraktu: guard sprawdza module_current_truth dla wskazanego modułu. Prawidłowy stale marker nie jest unavailable, więc dozwolona aktualizacja błędu składniowego dla już zaufanego LKG pozostaje kompatybilna.

## UPDATED_AND_DELETED_GATES

- Zwykły zaktualizowany plik odrzuca malformed falsey whole-map wartość False.
- Usunięty moduł odrzuca coercible whole-map listę par.
- Obie ścieżki kończą się przed commit; testy sprawdzają tożsamość pierwotnej mapy oraz tożsamość canonical modules/artifacts.
- Udana aktualizacja modułu provider przy poprawnym outer dict i malformed wpisie unrelated zachowuje wpis unrelated, jego referencję i stan untrusted; moduł provider przechodzi normalną ścieżkę fresh.

## NOOP_VS_EARLY_UNCHANGED

Rozróżniono dwie ścieżki:

- Parsed semantic no-op: źródło zmieniono wyłącznie komentarzem. Parsowanie kończy się poprawnie, ale update dochodzi do candidate commit; malformed whole map None jest odrzucona, a canonical modules/mapa pozostają nietknięte.
- Early filesystem UNCHANGED: źródło nie zmieniono. Wynik pozostaje UNCHANGED; monkeypatch sprawdza, że parser nie jest wywołany. Nieprawidłowy wpis celu pozostaje w miejscu, a module_current_truth nadal zwraca unavailable/untrusted.

## LKG_RECOVERY_COMPATIBILITY

Istniejący test tests/test_live_e2e_corrections.py::test_syntax_error_marks_authoritative_last_known_good_and_recovery pozostał zielony. Weryfikuje:
- poprawny moduł po błędzie składni staje się stale/last_known_good;
- zachowane symbole nadal są dostępne jako LKG;
- błąd zachowuje error, line_number i column_number;
- poprawiony, ponownie parsowalny plik zwraca RECOVERED i current/fresh.

Zmieniony test test_reading_malformed_parse_freshness_does_not_claim_recovery wykonuje zweryfikowane parse dla celu z wcześniejszym malformed wpisem. Istniejący clear semantics może usunąć wpis celu po poprawnym parse; status nie jest fałszywie RECOVERED, a module_current_truth po parse jest fresh/current.

## SNAPSHOT_HYDRATION_REGRESSION

test_malformed_snapshot_map_rejects_hydrated_syntax_update:
- zapisuje snapshot z truthy listą par jako module_parse_freshness;
- hydratuje stan przez load_engine_state;
- wywołuje targeted syntax update;
- potwierdza odrzucenie bez zmiany obiektu hydrated mapy ani modules;
- ponowne odczytanie snapshotu potwierdza zachowanie poprzedniej malformed generacji, bez opublikowania nowej empty/fresh generacji.

## LIVE_JOB_AND_REVISION_ATOMICITY

test_live_mutation_job_failure_preserves_malformed_parse_freshness_atomically uruchamia lokalny LIVE fixture (bez restartu aktualnego serwisu) i sprawdza:
- mutation job kończy się failed z canonical_mutation_execution_failed oraz detail z fail-closed ValueError;
- ten sam canonical state object pozostaje authoritative;
- revision zostaje 0;
- malformed module_parse_freshness=None pozostaje unavailable;
- persister nie jest wywołany;
- dziennik nie zawiera udanego update_file event.

test_desktop_watcher_requeues_failed_mutation_status sprawdza, że Desktop watcher usuwa failed job z inflight i umieszcza ścieżkę w pending do ponowienia; nie oznacza błędu jako completed. Zmiana watcher lifecycle nie została wykonana.

## SOURCE_SYNC_VERIFICATION

Końcowy Contextor fetch dla obu zmienionych funkcji podał canonical_state=fresh, provenance=live, workspace_sync=verified, canonical_revision=184. Końcowy get_file_edit_context podał workspace_sync=verified dla wszystkich sześciu zmienionych plików; wszystkie miały fresh canonical state i brak syntax diagnostics. get_project_architecture podał resync_required=false. Per-file Contextor wynik jest mocniejszym dowodem synchronizacji źródeł niż agregat architecture, którego workspace_sync był unverified.

Pobrania symboli dla obu zmienionych funkcji wskazały implementation_is_complete=true i no_partial_symbol_source=true. Lineage obu symboli zwrócił preview ze względu na payload większy od progu auto; tych preview nie traktowano jako pełnej implementacji. Call context i pełne implementacje zostały osobno pobrane. Nie zaakceptowano żadnego truncated/preview source jako implementacji.

## LIVE_REVISION_BEFORE_AFTER

- Przed zmianami: LIVE canonical revision 176, canonical_state=fresh, resync_required=false; oba produkcyjne pliki i cztery pliki testowe miały zweryfikowane źródła w Contextor.
- Po zmianach: revision 184.
- get_live_events(after_revision=176) zwrócił ciągłe zdarzenia desktop_watcher UPDATED w revision 177–184, bez truncation i bez luki; końcowe resync_required=false.
- Revision 181/182 odpowiadały zmianie plan_executor.py/state_manager.py; 177–180 oraz 183–184 odpowiadały czterem plikom testowym.
- Nie wykonano restartu MCP, Desktop ani LIVE i nie użyto manual update_file.

## REMAINING_RISKS

- Contextor source sync i świeże source contexts potwierdzają indeks/kanoniczne źródło, nie reload zaimportowanych modułów w już działającym procesie serwera. Serving-process reload nie był certyfikowany. Testy uruchomiono w osobnym procesie pytest.
- get_symbol_call_context ma udokumentowany zakres intra_module; nie dowodzi między-modułowej kompletności call graph. Wnioski o atomowości LIVE pochodzą także z implementacji i ukierunkowanej regresji IPC.
- Git line-ending notices ostrzegały o LF→CRLF przy przyszłym zapisie Git; git diff --check nie wykrył whitespace errors.
- Nie stwierdzono dodatkowego produkcyjnego bypassu w badanych ścieżkach; w ramach zadania nie rozszerzano zakresu.

## RESTART_REQUIRED

Nie wykonano restartu. Wymóg reloadu zaimportowanego kodu w aktualnym serving process pozostaje niezweryfikowany; bieżący raport potwierdza source/workspace sync i testy w świeżym procesie, nie runtime reload certification.

## FINAL_VERDICT

PATCH_AND_TARGETED_TESTS_PASS. Dwa wskazane bloki produkcyjne są obecne w dokładnych ownerach; targeted regression gate: 211 passed; compile i diff check przeszły; Contextor potwierdził synchronizację źródeł do revision 184 i resync_required=false. Serving-process reload pozostaje niecertyfikowany. Nie uruchamiano full repository pytest ani restartów.

## FULL_DIFFS

Poniżej kompletny bieżący git diff dla wszystkich sześciu zmienionych plików produkcyjnych i testowych.
Post-write check potwierdził, że osadzony diff jest identyczny z bieżącym git diff po normalizacji newline i zawiera sześć nagłówków diff --git. Ścieżki w nagłówkach standardowego diffu są względne względem C:\Temp\Contextor_Repo; ich absolutne ścieżki Windows są wymienione w FILES_CHANGED_THIS_TASK.


diff --git a/contextor/core/analysis/incremental/plan_executor.py b/contextor/core/analysis/incremental/plan_executor.py
index 55ac25f..1238cd2 100644
--- a/contextor/core/analysis/incremental/plan_executor.py
+++ b/contextor/core/analysis/incremental/plan_executor.py
@@ -680,6 +680,16 @@ def _rebuild_consumer_slice(
 
 def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
     """Initializes Copy-on-Write candidate state from current canonical state."""
+    raw_parse_freshness = getattr(
+        state,
+        "module_parse_freshness",
+        {},
+    )
+    if not isinstance(raw_parse_freshness, dict):
+        raise ValueError(
+            "Canonical module_parse_freshness is invalid; "
+            "fresh full analysis is required."
+        )
     return CandidateState(
         modules=dict(state.modules),
         reexport_facts_by_module=dict(
@@ -691,7 +701,7 @@ def _prepare_candidate_state(state: RepositoryAnalysisState) -> CandidateState:
             or {}
         ),
         artifacts=dict(state.artifacts),
-        module_parse_freshness=dict(getattr(state, "module_parse_freshness", {}) or {}),
+        module_parse_freshness=dict(raw_parse_freshness),
         syntax_diagnostics_by_path=dict(getattr(state, "syntax_diagnostics_by_path", {}) or {}),
         syntax_diagnostics_state=getattr(state, "syntax_diagnostics_state", "not_materialized"),
         module_usages=dict(getattr(state, "module_usages", {}) or {}),
diff --git a/contextor/core/analysis/state_manager.py b/contextor/core/analysis/state_manager.py
index 450edc9..241902b 100644
--- a/contextor/core/analysis/state_manager.py
+++ b/contextor/core/analysis/state_manager.py
@@ -278,6 +278,12 @@ def mark_module_parse_failure(
     column_number: int | None,
 ) -> None:
     """Mark retained module facts as last-known-good after a parse failure."""
+    truth = module_current_truth(state, module_name)
+    if truth["state"] == "unavailable":
+        raise ValueError(
+            "Canonical module parse freshness is untrusted; "
+            "fresh full analysis is required."
+        )
     freshness = getattr(state, "module_parse_freshness", None)
     if not isinstance(freshness, dict):
         freshness = {}
diff --git a/tests/test_live_e2e_corrections.py b/tests/test_live_e2e_corrections.py
index 8bf8f3f..d55f4d0 100644
--- a/tests/test_live_e2e_corrections.py
+++ b/tests/test_live_e2e_corrections.py
@@ -16,6 +16,7 @@ from contextor.core.analysis.state_manager import (
     FileStateManager,
     RepositoryAnalysisState,
     load_engine_state,
+    mark_module_parse_failure,
     module_current_truth,
     save_engine_state,
 )
@@ -499,9 +500,213 @@ def test_reading_malformed_parse_freshness_does_not_claim_recovery(tmp_path):
 
     assert module_current_truth(engine.state, "provider")["state"] == "unavailable"
     assert engine.state.module_parse_freshness["provider"] is entry
-    source.write_text("def helper(value: int) -> int:\n    return value + 1\n")
+    source.write_text(
+        "def helper(value: int) -> int:\n    return value + 1\n# verified parse\n"
+    )
     result = engine.update_file(str(source))
     assert result.status != "RECOVERED"
+    assert module_current_truth(engine.state, "provider")["state"] == "fresh"
+
+
+def test_mark_module_parse_failure_rejects_untrusted_target_entry():
+    entry = {"state": "unknown"}
+    raw_map = {"provider": entry}
+    state = SimpleNamespace(module_parse_freshness=raw_map)
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical module parse freshness is untrusted",
+    ):
+        mark_module_parse_failure(
+            state,
+            "provider",
+            error="invalid syntax",
+            line_number=1,
+            column_number=1,
+        )
+
+    assert state.module_parse_freshness is raw_map
+    assert state.module_parse_freshness["provider"] is entry
+    assert module_current_truth(state, "provider")["provenance"] == "untrusted"
+
+
+@pytest.mark.parametrize(
+    "raw_map",
+    [None, [("provider", {"state": "stale"})]],
+    ids=["falsey_none", "truthy_coercible_pairs"],
+)
+def test_syntax_failure_rejects_malformed_whole_parse_freshness_map(
+    tmp_path,
+    raw_map,
+):
+    source, engine = _engine_for_file(tmp_path)
+    engine.state.module_parse_freshness = raw_map
+    original_modules = engine.state.modules
+    original_artifacts = engine.state.artifacts
+    source.write_text("def broken(\n")
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical module_parse_freshness is invalid",
+    ):
+        engine.update_file(str(source))
+
+    assert engine.state.module_parse_freshness is raw_map
+    assert engine.state.modules is original_modules
+    assert engine.state.artifacts is original_artifacts
+    assert module_current_truth(engine.state, "provider")["state"] == "unavailable"
+    assert module_current_truth(engine.state, "unrelated")["state"] == "unavailable"
+
+
+def test_syntax_failure_does_not_promote_untrusted_target_entry_to_lkg(tmp_path):
+    source, engine = _engine_for_file(tmp_path)
+    entry = {"state": "unknown"}
+    raw_map = {"provider": entry}
+    engine.state.module_parse_freshness = raw_map
+    source.write_text("def broken(\n")
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical module parse freshness is untrusted",
+    ):
+        engine.update_file(str(source))
+
+    assert engine.state.module_parse_freshness is raw_map
+    assert engine.state.module_parse_freshness["provider"] is entry
+    assert module_current_truth(engine.state, "provider")["provenance"] == "untrusted"
+
+
+def test_semantic_noop_rejects_malformed_parse_freshness_map(tmp_path):
+    source, engine = _engine_for_file(tmp_path)
+    raw_map = None
+    engine.state.module_parse_freshness = raw_map
+    original_modules = engine.state.modules
+    source.write_text(
+        "def helper(value: int) -> int:\n    return value + 1\n# semantically unchanged\n"
+    )
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical module_parse_freshness is invalid",
+    ):
+        engine.update_file(str(source))
+
+    assert engine.state.module_parse_freshness is raw_map
+    assert engine.state.modules is original_modules
+    assert module_current_truth(engine.state, "provider")["state"] == "unavailable"
+    assert module_current_truth(engine.state, "unrelated")["state"] == "unavailable"
+
+
+@pytest.mark.parametrize(
+    ("operation", "raw_map"),
+    [
+        ("updated", False),
+        ("deleted", [("provider", {"state": "stale"})]),
+    ],
+    ids=["ordinary_update", "module_delete"],
+)
+def test_updated_and_deleted_candidates_reject_malformed_parse_freshness(
+    tmp_path,
+    operation,
+    raw_map,
+):
+    source, engine = _engine_for_file(tmp_path)
+    engine.state.module_parse_freshness = raw_map
+    original_modules = engine.state.modules
+    original_artifacts = engine.state.artifacts
+    if operation == "updated":
+        source.write_text(
+            "def helper(value: int) -> int:\n    return value + 2\n"
+        )
+    else:
+        source.unlink()
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical module_parse_freshness is invalid",
+    ):
+        engine.update_file(str(source))
+
+    assert engine.state.module_parse_freshness is raw_map
+    assert engine.state.modules is original_modules
+    assert engine.state.artifacts is original_artifacts
+    assert module_current_truth(engine.state, "provider")["state"] == "unavailable"
+
+
+def test_successful_update_preserves_unrelated_malformed_parse_entry(tmp_path):
+    source, engine = _engine_for_file(tmp_path)
+    unrelated_entry = {"state": "unknown"}
+    raw_map = {"unrelated": unrelated_entry}
+    engine.state.module_parse_freshness = raw_map
+    source.write_text(
+        "def helper(value: int) -> int:\n    return value + 2\n"
+    )
+
+    result = engine.update_file(str(source))
+
+    assert result.status == "UPDATED"
+    assert engine.state.module_parse_freshness == raw_map
+    assert engine.state.module_parse_freshness is not raw_map
+    assert engine.state.module_parse_freshness["unrelated"] is unrelated_entry
+    assert module_current_truth(engine.state, "provider")["state"] == "fresh"
+    assert module_current_truth(engine.state, "unrelated")["provenance"] == "untrusted"
+
+
+def test_early_unchanged_keeps_untrusted_target_marker_without_parsing(
+    tmp_path,
+    monkeypatch,
+):
+    source, engine = _engine_for_file(tmp_path)
+    entry = {"state": "unknown"}
+    raw_map = {"provider": entry}
+    engine.state.module_parse_freshness = raw_map
+
+    def unexpected_parse(**_kwargs):
+        pytest.fail("early UNCHANGED must not parse the source")
+
+    monkeypatch.setattr(
+        "contextor.core.analysis.incremental.engine.prepare_source_update",
+        unexpected_parse,
+    )
+
+    result = engine.update_file(str(source))
+
+    assert result.status == "UNCHANGED"
+    assert engine.state.module_parse_freshness is raw_map
+    assert engine.state.module_parse_freshness["provider"] is entry
+    assert module_current_truth(engine.state, "provider")["provenance"] == "untrusted"
+
+
+def test_malformed_snapshot_map_rejects_hydrated_syntax_update(tmp_path):
+    source, engine = _engine_for_file(tmp_path)
+    raw_map = [("provider", {"state": "stale"})]
+    engine.state.module_parse_freshness = raw_map
+    cache = tmp_path / "cache"
+    assert save_engine_state(engine.state, str(cache), "state-malformed-update")
+    loaded = load_engine_state(str(cache), "state-malformed-update")
+    assert loaded is not None
+    original_map = loaded.module_parse_freshness
+    original_modules = loaded.modules
+    source.write_text("def broken(\n")
+    hydrated_engine = IncrementalAnalysisEngine(
+        loaded,
+        engine.registry,
+        engine.state_manager,
+        str(tmp_path),
+    )
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical module_parse_freshness is invalid",
+    ):
+        hydrated_engine.update_file(str(source))
+
+    assert loaded.module_parse_freshness is original_map
+    assert loaded.modules is original_modules
+    assert module_current_truth(loaded, "provider")["state"] == "unavailable"
+    previous_generation = load_engine_state(str(cache), "state-malformed-update")
+    assert previous_generation is not None
+    assert previous_generation.module_parse_freshness == raw_map
 
 
 def test_global_search_and_static_context_do_not_leak_parse_stale_truth(
diff --git a/tests/test_live_state_ipc.py b/tests/test_live_state_ipc.py
index ab6ec5b..6e5dcab 100644
--- a/tests/test_live_state_ipc.py
+++ b/tests/test_live_state_ipc.py
@@ -1937,6 +1937,40 @@ def test_desktop_watcher_reports_create_edit_and_delete_without_manual_update(tm
         thread.join(timeout=2)
 
 
+def test_desktop_watcher_requeues_failed_mutation_status(tmp_path, monkeypatch):
+    target = tmp_path / "sample.py"
+    target.write_text("value = 1\n", encoding="utf-8")
+    statuses = []
+    client = SimpleNamespace(
+        snapshot=lambda: {"status": "error"},
+        mutation_status=lambda job_id: {
+            "status": "ok",
+            "job_id": job_id,
+            "state": "failed",
+            "error": "canonical_mutation_execution_failed",
+        }
+    )
+    watcher = DesktopLiveWatcher(
+        tmp_path,
+        client,
+        on_status=statuses.append,
+    )
+    job = SimpleNamespace(
+        path=str(target),
+        trace_op="failed-watcher-update",
+        started_at=time.monotonic(),
+    )
+    watcher._inflight_updates["job-1"] = job
+    monkeypatch.setattr("contextor.core.runtime_trace.trace_event", lambda *_a, **_k: None)
+
+    completed = watcher._poll_inflight_updates()
+
+    assert completed == []
+    assert "job-1" not in watcher._inflight_updates
+    assert str(target) in watcher._pending_paths
+    assert statuses == ["LIVE update failed; deferring watcher update: sample.py"]
+
+
 def test_first_run_watcher_waits_for_initial_canonical_state(tmp_path):
     identity = PersistentIdentityRegistry(str(tmp_path))
     manager = FileStateManager(str(repo_cache_dir(tmp_path)))
diff --git a/tests/test_refresh_plan_execution.py b/tests/test_refresh_plan_execution.py
index ba8e893..26ecca2 100644
--- a/tests/test_refresh_plan_execution.py
+++ b/tests/test_refresh_plan_execution.py
@@ -11,6 +11,7 @@ from unittest.mock import patch
 import pytest
 
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
+from contextor.core.analysis.incremental.plan_executor import _prepare_candidate_state
 from contextor.core.analysis.state_manager import FileStateManager, RepositoryAnalysisState
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.domain.module import Module
@@ -284,3 +285,66 @@ def test_case_g_noop_unchanged(tmp_path):
     # Re-saving same content
     res = engine.update_file(str(f_target))
     assert res.status == "UNCHANGED"
+
+
+@pytest.mark.parametrize(
+    "raw_map",
+    [
+        None,
+        False,
+        0,
+        "",
+        [],
+        (),
+        set(),
+        ["bad"],
+        17,
+        [("provider", {"state": "stale"})],
+    ],
+    ids=repr,
+)
+def test_prepare_candidate_state_rejects_malformed_parse_freshness_maps(raw_map):
+    state = RepositoryAnalysisState()
+    state.module_parse_freshness = raw_map
+
+    with pytest.raises(
+        ValueError,
+        match="Canonical module_parse_freshness is invalid",
+    ):
+        _prepare_candidate_state(state)
+
+    assert state.module_parse_freshness is raw_map
+
+
+def test_prepare_candidate_state_preserves_legacy_and_valid_parse_freshness_cow():
+    legacy_state = RepositoryAnalysisState()
+    del legacy_state.module_parse_freshness
+
+    legacy_candidate = _prepare_candidate_state(legacy_state)
+
+    assert legacy_candidate.module_parse_freshness == {}
+
+    empty_state = RepositoryAnalysisState(module_parse_freshness={})
+    empty_candidate = _prepare_candidate_state(empty_state)
+
+    assert empty_candidate.module_parse_freshness == {}
+    assert empty_candidate.module_parse_freshness is not empty_state.module_parse_freshness
+
+    fresh_entry = {"state": "fresh"}
+    stale_entry = {"state": "stale", "error": "invalid syntax"}
+    malformed_entry = {"state": "unknown"}
+    raw_map = {
+        "fresh": fresh_entry,
+        "stale": stale_entry,
+        "malformed": malformed_entry,
+    }
+    state = RepositoryAnalysisState(module_parse_freshness=raw_map)
+
+    candidate = _prepare_candidate_state(state)
+
+    assert candidate.module_parse_freshness == raw_map
+    assert candidate.module_parse_freshness is not raw_map
+    assert candidate.module_parse_freshness["fresh"] is fresh_entry
+    assert candidate.module_parse_freshness["stale"] is stale_entry
+    assert candidate.module_parse_freshness["malformed"] is malformed_entry
+    assert state.module_parse_freshness is raw_map
diff --git a/tests/test_syntax_diagnostics_full_analysis.py b/tests/test_syntax_diagnostics_full_analysis.py
index f0b95d4..4b5c65b 100644
--- a/tests/test_syntax_diagnostics_full_analysis.py
+++ b/tests/test_syntax_diagnostics_full_analysis.py
@@ -1,8 +1,10 @@
+import time
 from types import SimpleNamespace
 
 from contextor.core.analysis.state_manager import (
     RepositoryAnalysisState,
     build_syntax_diagnostics_from_index,
+    module_current_truth,
 )
 from contextor.core.api.facade import ContextorFacade
 from contextor.core.analysis.incremental_engine import IncrementalAnalysisEngine
@@ -321,3 +323,60 @@ def test_live_persistence_failure_does_not_publish_half_updated_syntax_fact(tmp_
         assert server._state.module_parse_freshness == {}
     finally:
         server.close()
+
+
+def test_live_mutation_job_failure_preserves_malformed_parse_freshness_atomically(
+    tmp_path,
+    monkeypatch,
+):
+    monkeypatch.setenv("CONTEXTOR_DISABLE_PROCESS_POOL", "1")
+    source, server, state = _live_syntax_fixture(tmp_path)
+    state.module_parse_freshness = None
+    persisted = []
+    server._persister = lambda candidate, revision: persisted.append(
+        (candidate, revision)
+    )
+    source.write_text("def value(\n", encoding="utf-8")
+
+    try:
+        accepted = server._dispatch(
+            {
+                "operation": "submit_update_file",
+                "file_path": str(source),
+                "idempotency_key": "malformed-parse-freshness",
+            }
+        )
+        assert accepted["status"] == "accepted"
+        job_id = accepted["job_id"]
+
+        deadline = time.monotonic() + 3.0
+        job_status = {}
+        while time.monotonic() < deadline:
+            job_status = server._dispatch(
+                {"operation": "mutation_status", "job_id": job_id}
+            )
+            if job_status.get("state") in {"failed", "completed"}:
+                break
+            time.sleep(0.01)
+
+        assert job_status.get("state") == "failed"
+        assert job_status["response"] == {
+            "status": "error",
+            "error": "canonical_mutation_execution_failed",
+            "detail": (
+                "Canonical module_parse_freshness is invalid; "
+                "fresh full analysis is required."
+            ),
+        }
+        assert server._state is state
+        assert server._revision == 0
+        assert state.module_parse_freshness is None
+        assert module_current_truth(state, "provider")["state"] == "unavailable"
+        assert persisted == []
+
+        events = server._dispatch(
+            {"operation": "get_events", "after_revision": 0, "limit": None}
+        )
+        assert not any(event["operation"] == "update_file" for event in events["events"])
+    finally:
+        server.close()


