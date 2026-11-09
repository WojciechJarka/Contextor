# F1M — weryfikacja rzeczywistej adopcji F1H

## DESKTOP_PROCESS_IDENTITY

DIRECT_EVIDENCE: bieżący pointer runtime trace `C:\Users\DafoO\AppData\Roaming\Contextor\logs\contextor_runtime_active.json` wskazuje `desktop_pid=14968`, `sid=d-14968-20261109_142305_899`, sesję rozpoczętą `2026-11-09T14:23:05.899Z`. Aktywny plik: `C:\Users\DafoO\AppData\Roaming\Contextor\logs\contextor_runtime_20261109_142305_899_14968.jsonl`.

Win32_Process potwierdza, że PID **14968 nadal działa**, powstał `2026-11-09T14:23:02.947493Z`, parent PID 10988, rzeczywisty executable procesu `C:\Python315\python.exe`, polecenie: `"C:\Temp\Contextor_Repo\.venv\Scripts\python.exe" "C:\Temp\Contextor_Repo\main.py" --gui`. Parent 10988 to launcher venv z tym samym poleceniem, utworzony `2026-11-09T14:23:02.929494Z`. Pole `sys.executable` zapisane przez sam proces wynosi `C:\Temp\Contextor_Repo\.venv\Scripts\python.exe`. Rozróżnienie launcher/real interpreter wynika z Windows venv; trace PID należy do procesu 14968.

Contextor MCP użyto jako pierwszy odczyt: `get_live_events(limit=1)` podał LIVE revision 1203, activity_epoch `480745c885e44d8e97ca47ee5e232751`. Jego najnowszy event dotyczył LIVE service PID 14600; **nie** użyto tego PID jako tożsamości GUI.

## ATTESTATION_EVENT

Najnowszy wpis `GUI/F1H_LOADED_CODE_ATTESTATION` w aktywnym Desktop runtime trace:

- `ts=2026-11-09T15:23:06.395+01:00` (`14:23:06.395Z`), około 3,45 s po utworzeniu PID 14968 i 0,50 s po otwarciu sesji trace;
- `pid=14968`, `tid=8948`, `sid=d-14968-20261109_142305_899`, `d=GUI`, `ev=F1H_LOADED_CODE_ATTESTATION`, `status=MATCH`;
- `path=C:\Temp\Contextor_Repo\contextor\core\cycle_semantics\package_model.py`.

PID i SID wpisu są identyczne z aktywnym pointerem i żywym procesem `main.py --gui`. Jest to wpis Desktop, nie pytest ani historyczny LIVE. Nie uruchamiano testów ani restartu w F1M.

## LOADED_CODE_HASHES

Pełne `result` poprawnie parsuje się jako JSON. `loaded_sha256` = `source_sha256` = `4aeaa598ee0010c256cf4b353eba5ee48b5480ef0b6b7a5c57b903f9055c2e98`. Obie wartości są pełnymi 64-znakowymi małymi hex. Status `MATCH` według zaimplementowanego kontraktu F1L oznacza również tożsamość funkcji pobranej z globals `scenarios.evaluate_package_import_order` z `package_model._compile`, zgodność ścieżki `co_filename`, hash kodu załadowanego i kodu skompilowanego z aktualnych bajtów.

## NAME_ATTRIBUTE_RESULTS

Z tego samego `result`:

- `NAME=["FROM","UNMODELED_STATEMENT"]`;
- `ATTRIBUTE=["IMPORT","UNMODELED_STATEMENT"]`;
- `python="3.15.2 (tags/v3.15.2:5e58eaa, Oct 25 2026, 17:27:03) [MSC v.1951 64 bit (AMD64)]"`;
- `executable="C:\Temp\Contextor_Repo\.venv\Scripts\python.exe"`.

Obie próby wykonały załadowaną funkcję na syntetycznym AST, bez wykonywania importów zawartych w AST. Zdarzenie dotyczy kodu w tym samym procesie, w którym Desktop wykonuje analizę.

## EVIDENCE_INTEGRITY

`result` ma dokładnie **410 znaków**, poniżej limitu `runtime_trace._MAX_TEXT=500`; JSON jest kompletny i parsowalny. Nie ma ucięcia hasha, sekwencji, wersji ani executable. Pointer, SID, PID, command line i czasy są spójne. Wpis powstał w aktualnej sesji Desktop, a PID jest nadal aktywny. Odczyt dotyczy chwili zdarzenia; sam trace nie jest ciągłą atestacją przyszłych zmian w pamięci procesu.

## FINAL_VERDICT

Adopcja F1H przez rzeczywisty aktywny proces Desktop **PROVED** na podstawie wpisu `MATCH` z PID 14968, pełnego result, zgodnych hashy i obu prób NAME/ATTRIBUTE, powiązanego z aktywną sesją `main.py --gui`. To certyfikuje załadowany `_compile` w Desktop w chwili atestacji; nie jest dowodem bezpieczeństwa dowolnego wykonania CPython.

`FILES_CHANGED`: brak zmian produkcji/testów/docs; nadpisano wyłącznie wymagany raport. `ACTUAL_DIFF=DIFFS=NONE` dla source/test/docs. Bez testów, FULL, restartów, commitów i push.

