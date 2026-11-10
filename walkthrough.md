# P3-R2-T1-C1 — remove hardcoded Python version

## PREFLIGHT

Contextor MCP first: canonical revision `1257`, state_id `20261109_210842`, target test symbol `workspace_sync=verified`. HEAD `f415f793c3bab4f03bf11912c028311772b182e1`; przed edycją brak source/test worktree changes. AST wskazanej funkcji `test_conditional_external_side_effect_is_not_runtime_authority` obejmuje linie 175–278. W niej anchor `assert sys.version_info[:3] == (3, 15, 2)` występował dokładnie raz, a `target_python_version=(3, 15),` dokładnie raz; w całym pliku drugi anchor występował trzy razy, więc zakres funkcji był konieczny. Zmieniono tylko oba wskazane miejsca.

## ACTIVE_BACKEND_INTERPRETER_EVIDENCE

Read-only IPC `authority_status`: aktywny LIVE owner PID `13968`, service `c3dbe3bf94ef45ce8d453ba1984fd27d`, process_start_identity `134387828093072108`; `desktop_claim_status` wskazuje tego samego ownera z Desktop PID `12736`. OS Win32_Process: LIVE backend PID 13968 i MCP backend PID 13404 mają command line rozpoczynający się od **`C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`**; Windows pokazuje bazowy obraz wykonywalny `C:\Python315\python.exe` jako child procesu venv launcher. Desktop backend używa tej samej ścieżki venv. Nie wybrano interpretera z PATH ani nazwy katalogu bez powiązania z procesem.

Odczyt uruchomiony dokładnie przez tę zaobserwowaną absolutną ścieżkę zwrócił: `sys.executable=C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`, `sys.prefix=C:\Temp\Contextor_Repo\.venv`, `sys.base_prefix=C:\Python315`, `sys.version_info=(3,15,2,'final',0)`, `sys.prefix != sys.base_prefix=True`. `pyvenv.cfg` wiąże venv z `C:\Python315\python.exe`, version `3.15.2`. Dane `sys.*` pochodzą z nowego procesu uruchomionego przez **ten sam executable path**, gdyż istniejący IPC nie udostępnia introspekcji `sys.*` wewnątrz bieżącego ownera; tożsamość uruchomionego backendu jest potwierdzona OS process command line i IPC service identity.

## EXACT_FILES_CHANGED

FILES_CHANGED: `tests/test_cycle_semantics_external_import_authority.py`. Usunięto jedną asercję stałej wersji; tylko w tej funkcji zmieniono `target_python_version` na `sys.version_info[:2]`. Pozostałe wywołania niezmienione. `walkthrough.md` jest wyłącznie raportem; brak zmian production/config.

## TARGETED_TEST_RESULTS

Dokładna komenda z aktywnym venv: `& 'C:\Temp\Contextor_Repo\.venv\Scripts\python.exe' -m pytest -q tests/test_cycle_semantics_external_import_authority.py` → **7 passed in 8.80s**, exit code 0. Izolowane subprocessy testu nadal używają `sys.executable`. `git diff --check` → exit code 0. Bez full pytest.

## MCP_POST_CHANGE_AUDIT

Watcher zgłosił `UPDATED` docelowego testu w canonical revision `1258`. Po zmianie Contextor symbol ma `workspace_sync=verified`; syntax errors `0`; graph/cycles fresh, 16 structural DFS paths; graph SHA-256 `2b45d940afccdaefb3c0f4a686b83bcbc2687e0d8b167cadc986106b01eedf6f`, niezmieniony. IPC state_id `20261109_210842`, revision `1258`; cycle_semantics **stale**. Warning view: structural `16`, MODEL_PASS `0`, active `16`. Bez FULL, `update_file`, restartu i publikacji.

## FULL_DIFFS

Pełny rzeczywisty git diff jedynego pliku zmienionego w bieżącym zadaniu:

```diff
diff --git a/tests/test_cycle_semantics_external_import_authority.py b/tests/test_cycle_semantics_external_import_authority.py
index d6cdedc..90723e3 100644
--- a/tests/test_cycle_semantics_external_import_authority.py
+++ b/tests/test_cycle_semantics_external_import_authority.py
@@ -173,8 +173,6 @@ def test_unproved_typing_guard_stops_ordinary_and_conditional_models(
 
 
 def test_conditional_external_side_effect_is_not_runtime_authority(tmp_path):
-    assert sys.version_info[:3] == (3, 15, 2)
-
     sources = {
         "pkg.__init__": "pass\n",
         "pkg.ns.a": (
@@ -201,7 +199,7 @@ def test_conditional_external_side_effect_is_not_runtime_authority(tmp_path):
         trees,
         "pkg.ns.a",
         (portion,),
-        target_python_version=(3, 15),
+        target_python_version=sys.version_info[:2],
         assume_passive_external_imports=True,
         assume_frozen_dataclass_decoration=True,
     )
```

## FINAL_VERDICT

`PASS` dla dokładnej dwulinijkowej zmiany i celowanego testu. Aktywny backend i test korzystają z tej samej zweryfikowanej ścieżki venv; brak nowej stałej wersji w zmienionej funkcji. MCP potwierdził source sync; cycle_semantics pozostaje stale. STOP.
