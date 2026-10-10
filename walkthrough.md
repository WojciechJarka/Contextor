# L32H2D2B_POST_AUDIT_CONTRACT_HARDENING

## FILES_CHANGED_THIS_TASK

- C:\Temp\Contextor_Repo\contextor\core\api\facade.py
- C:\Temp\Contextor_Repo\tests\test_full_analysis_coordination.py
- Raport: C:\Temp\Contextor_Repo\walkthrough.md

## PUBLICATION_RESULT_CONTRACT

DIRECT_EVIDENCE: przed edycją publiczne `ContextorFacade.analyze_single_file` walidowało target i nabywało lease przed wejściem do prywatnego body. Prywatne `_analyze_single_file_uncoordinated` zaczynało od `publication_result.update(status="not_attempted", revision=None, warning=None)`. Wczesny `ValueError` oraz `FullAnalysisBusyError` pozostawiały stare pola w przekazanym słowniku. Literalna poprawka kopiuje tę inicjalizację na sam początek publicznego wrappera i zachowuje ją w private body. Publiczna sygnatura, walidacja, lease i publikacja LIVE nie zostały zmienione.

## RED_RESULT

Dwa nowe testy przed patchem: 2 failed. W obu stan początkowy `{"status":"stale","revision":99,"warning":"old"}` pozostał niezmieniony po wczesnym wyjątku. Test A: out-of-repository `ValueError`, brak lease. Test B: wstrzyknięty `FullAnalysisBusyError`, private body niewykonane; fixture porównuje drzewo tymczasowe przed/po, bez nowych plików registry/snapshot.

## GREEN_RESULT

Komenda focused obejmująca dwa nowe testy, scoped coordination, invalid scope, denied lease, real LIVE single-file publish, recovery i output reuse: 13 passed, 1 zewnętrzne ostrzeżenie AuthlibDeprecationWarning. `py_compile` facade oraz testu: PASS. `git diff --check`: PASS. Nie uruchomiono pełnego suite.

## EXACT_PRODUCTION_DIFF

Jedyna produkcyjna zmiana: sześciowierszowa inicjalizacja `publication_result` na początku publicznego wrappera w `C:\Temp\Contextor_Repo\contextor\core\api\facade.py`. Pełny diff w FULL_DIFFS.

## IMPORT_CYCLE_EDGES

DIRECT_EVIDENCE z `get_module_context`: `contextor.core.api.facade -> contextor.core.analysis.full_analysis_coordinator` oraz edge odwrotny są obecne w canonical graph. Anchory: facade.py:1309–1311 i :1542–1544 importują `acquire_full_analysis` / `release_full_analysis` wewnątrz publicznych wrapperów; full_analysis_coordinator.py:660 importuje `ContextorFacade` wewnątrz `run_full_analysis_exclusive`. Event LIVE revision 234 z poprzedniego etapu zawiera `diagnostic_changes: ADDED cycle [facade, full_analysis_coordinator, facade]`; przed zmianą revision 231 diagnostics cycles=0. Po tej poprawce cycles=1.

## HARD_SOFT_CLASSIFICATION

CONTRACT_PROVED: Contextor klasyfikuje obie krawędzie jako `hard_dependency` w `get_module_context`, mimo że importy są lokalne wewnątrz funkcji. `resolve_module_edges` daje hard dla `result.kind == MODULE`, soft tylko dla type-only lub FALLBACK; `ImportRef.is_local` nie jest w tym rozstrzygnięciu wyjątkiem. `validate_cycles` wykrywa cykle z `graph.hard_edges` i tworzy `ArchitectureCycle`. Stąd wykryty cykl jest rzeczywistą diagnostyką Contextora, nie tylko arbitralną wizualizacją importów.

## ACYCLIC_EXTRACTION_DEPENDENCIES

CODE_PATH_PROVED na kompletnym pliku koordynatora (Contextor `get_source_range` 1–207, 208–409, 410–700): niskopoziomowe `acquire_full_analysis` / `release_full_analysis` nie odwołują się do facade. Zależność zwrotna jest tylko w `run_full_analysis_exclusive` przy `analysis_fn is None`. Wspólna własność blokad i helperów oznacza, że ewentualny niezależny niższy owner musiałby zachować jeden zestaw stanu; samo skopiowanie funkcji lub słowników dałoby różne lock ownership. To warunek źródłowy, nie projekt patcha.

Literalne elementy współdzielonego stanu:

```python
ORPHAN_RECOVERY_TIMEOUT_SECONDS = 5.0
_PROCESS_LOCKS: dict[str, threading.Lock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()
_ADMISSION_LOCKS: dict[str, threading.Lock] = {}
_ADMISSION_LOCKS_GUARD = threading.Lock()
_ADMISSION_TRACE_FIELD_NAMES = (
    "op", "path", "job_id", "idempotency_key", "queue_order",
    "accepted_revision", "started_revision", "origin",
)
```

Wymagane typy: `FullAnalysisLease` (fields: repo_key, token, owner, lock_path, repo_id, lock_fd, owner_pid, owner_process_start_identity), `FullAnalysisBusyError`. Helpery w tej samej jednostce: `_select_admission_trace_fields`, `_get_process_lock`, `_get_admission_lock`, `_acquire_process_lock_until`, `_canonical_writer_admission`, `_prepare_lock_fd`, `_try_lock_fd`, `_unlock_fd`, `_read_lease_metadata`, `_lease_metadata_path`, `_read_lease_metadata_file`, `_write_lease_metadata_file`, `_process_identity`, `_lease_owner_state`, `_log_orphan_recovery`, `_resolve_lock_path`. External owners: `AnalysisCancelled`, `repo_cache_dir`, `repo_key`, `read_repository_identity`, `trace_event`, `process_identity` (lokalny import). OS/stdlib: contextmanager, json, os, threading, time, uuid, dataclass, Path, typing. Niskopoziomowe ciało nie wymaga `ContextorFacade`; `run_full_analysis_exclusive` wymaga publicznego `analyze_project` przy domyślnym `analysis_fn=None`.

## CURRENT_COORDINATOR_API_CONSUMERS

DIRECT_EVIDENCE z Contextor blast radius i targeted `rg`: produkcyjne importy koordynatora występują w `C:\Temp\Contextor_Repo\contextor\cli.py` (`run_full_analysis_exclusive`), `C:\Temp\Contextor_Repo\contextor\mcp_worker.py` (run), `C:\Temp\Contextor_Repo\contextor\mcp\analysis_jobs.py` (run), `C:\Temp\Contextor_Repo\contextor\core\analysis\profile_runner.py` (run, BusyError), `C:\Temp\Contextor_Repo\contextor\core\live_state\runtime.py` (acquire/release), `C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py` (acquire/release), `C:\Temp\Contextor_Repo\contextor\ui\gui.py` (BusyError, acquire/release, run), `C:\Temp\Contextor_Repo\contextor\core\api\facade.py` (acquire/release). Publiczny moduł jest również importowany przez testy: `test_full_analysis_coordination.py`, `test_live_desktop_integration.py`, `test_live_mutation_coordinator.py`, `test_live_watcher_startup_reconciliation.py`, `test_mcp_incremental_hydration.py`, `test_live_single_file_reuse.py`, `test_mcp_regressions.py`, `test_profile_runner.py`. `test_full_analysis_coordination.py` importuje ponadto prywatne `_lease_metadata_path`, `_prepare_lock_fd`, `_resolve_lock_path`, `_try_lock_fd`, `_unlock_fd`; są częścią obecnej testowej powierzchni zgodności.

## MONKEYPATCH_COMPATIBILITY

DIRECT_EVIDENCE: testy podmieniają `coordinator.acquire_full_analysis` i/lub `release_full_analysis` w `test_full_analysis_coordination.py` (m.in. linie 88–89, 549–550), `test_mcp_incremental_hydration.py` (232–233, 270, 319–320), `test_live_mutation_coordinator.py` (350–351), `test_live_watcher_startup_reconciliation.py` (463, 573). GUI testy podmieniają symbole zaimportowane do `gui` (`test_live_desktop_integration.py:443–444`). Każda przyszła zmiana ownera musi uwzględnić semantykę takich monkeypatchy; nie wykonano jej w tym zadaniu.

## ARCHITECTURAL_INVARIANT_ASSESSMENT

CONTRACT_PROVED: cykl jest hard/hard, `validate_cycles` mapuje go na `ArchitectureCycle`, a publiczne diagnostics podaje `cycles.count=1`, `attention_required=true`. Narusza poprzednio obserwowany stan zero-cycles i invariant bez cykli architektonicznych. UNKNOWN: dodatkowa formalna reguła granicy warstw contract/runtime; `get_layer_isolation` dla obu nazw odpowiedział, że nie ma dedykowanego raportu ani top-level index. Zgodnie z zakazem nie uruchomiono `analyze_layer`.

## MINIMUM_ACYCLIC_PATCH_OWNERS

Potwierdzone końce krawędzi i powierzchnia zgodności do decyzji audytora: `C:\Temp\Contextor_Repo\contextor\core\api\facade.py`, `C:\Temp\Contextor_Repo\contextor\core\analysis\full_analysis_coordinator.py`; lokalizacja ewentualnego niezależnego ownera pozostaje decyzją audytora. Testy zgodności i monkeypatchy wymienione powyżej. Ukrycie zależności przez importlib, global callback, service locator lub zmianę klasyfikacji importu nie usuwa realnej zależności; takich zmian nie wykonano.

## SOURCE_SYNC_VERIFICATION / LIVE_REVISION_BEFORE_AFTER

LIVE przed: 240. Po: 242. `get_live_events(after_revision=240)`: revision 241 test file, 242 facade, oba origin=desktop_watcher; continuity=continuous, resync_required=false, cycles.count=1. Po odświeżeniu `get_symbol_implementation` publicznego wrappera: complete=true, workspace_sync=verified, revision 242, nowy blok obecny. Source/test status: tylko dwa autoryzowane pliki plus walkthrough.md. Brak manual update_file i restartu. Nowy proces pytest nie certyfikuje reloadu istniejących procesów.

## REMAINING_RISKS

- Hard/hard cycle pozostaje i blokuje architectural final pass; auditor ma zaprojektować dosłowny acyclic patch.
- Polityka granicy warstw nie została potwierdzona dedykowanym raportem.
- Runtime serving-code reload po zmianie facade nie został wykonany ani certyfikowany.

## FINAL_VERDICT

PUBLICATION_RESULT_CONTRACT_FIXED_TARGETED_PASS; ARCHITECTURAL_FINAL_PASS_WITHHELD. Nie zgłaszam L32H FINAL PASS.

## FULL_DIFFS

Pełny surowy diff wszystkich plików zmienionych w tym zadaniu; walkthrough.md jako raport nie jest source/test diff.

```diff

diff --git a/contextor/core/api/facade.py b/contextor/core/api/facade.py
index d927b65..7c90062 100644
--- a/contextor/core/api/facade.py
+++ b/contextor/core/api/facade.py
@@ -1533,6 +1533,12 @@ class ContextorFacade:
         additional_excludes: list[str] | None = None,
         publication_result: dict[str, Any] | None = None,
     ) -> str:
+        if publication_result is not None:
+            publication_result.update(
+                status="not_attempted",
+                revision=None,
+                warning=None,
+            )
         from contextor.core.analysis.full_analysis_coordinator import (
             acquire_full_analysis,
             release_full_analysis,
diff --git a/tests/test_full_analysis_coordination.py b/tests/test_full_analysis_coordination.py
index 75bbd19..10cfbdc 100644
--- a/tests/test_full_analysis_coordination.py
+++ b/tests/test_full_analysis_coordination.py
@@ -239,6 +239,65 @@ def test_scoped_facade_non_python_target_does_not_acquire_lease(tmp_path, monkey
         facade.ContextorFacade.analyze_single_file(str(target), str(repo))
 
 
+def test_invalid_scoped_file_resets_publication_result_before_validation(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    from contextor.core.api import facade
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    outside = tmp_path / "outside.py"
+    outside.write_text("VALUE = 1\n", encoding="utf-8")
+    publication = {"status": "stale", "revision": 99, "warning": "old"}
+    monkeypatch.setattr(
+        coordinator,
+        "acquire_full_analysis",
+        lambda *_a, **_k: pytest.fail("invalid target acquired lease"),
+    )
+
+    with pytest.raises(ValueError, match="outside the repository root"):
+        facade.ContextorFacade.analyze_single_file(
+            str(outside), str(repo), publication_result=publication
+        )
+    assert publication == {
+        "status": "not_attempted", "revision": None, "warning": None,
+    }
+
+
+def test_denied_scoped_file_resets_publication_result_without_mutation(
+    tmp_path, isolated_dirs, monkeypatch
+):
+    from contextor.core.api import facade
+    from contextor.core.analysis import full_analysis_coordinator as coordinator
+
+    repo = tmp_path / "repo"
+    repo.mkdir()
+    target = repo / "module.py"
+    target.write_text("VALUE = 1\n", encoding="utf-8")
+    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
+    publication = {"status": "stale", "revision": 99, "warning": "old"}
+    monkeypatch.setattr(
+        coordinator,
+        "acquire_full_analysis",
+        lambda *_a, **_k: (_ for _ in ()).throw(FullAnalysisBusyError("denied")),
+    )
+    monkeypatch.setattr(
+        facade.ContextorFacade,
+        "_analyze_single_file_uncoordinated",
+        staticmethod(lambda *_a, **_k: pytest.fail("private body executed")),
+    )
+
+    with pytest.raises(FullAnalysisBusyError, match="denied"):
+        facade.ContextorFacade.analyze_single_file(
+            str(target), str(repo), publication_result=publication
+        )
+    assert publication == {
+        "status": "not_attempted", "revision": None, "warning": None,
+    }
+    assert sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")) == before
+
+
 @pytest.mark.parametrize("method,target_kind", [("analyze_layer", "layer"), ("analyze_single_file", "file")])
 def test_scoped_facade_denied_lease_does_not_start_body_or_identity(
     tmp_path, isolated_dirs, monkeypatch, method, target_kind
```
