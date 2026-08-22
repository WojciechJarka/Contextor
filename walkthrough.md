# A18 OUTPUT PREFLIGHT — FINAL RUNTIME CERTIFICATION

## FILES_CHANGED=NONE
Krok certyfikacji runtime typu read-only. Nie zmodyfikowano żadnych plików produkcyjnych, dokumentacji ani testów.

---

## RUNTIME_GET_ANALYSIS_STATUS_SIGNATURE
- Sygnatura Python:
  `def get_analysis_status(repo_path: str, job_id: str | None = None, max_skipped_files: int | None = 10, allow_large_output: bool = False) -> str:`
- FastMCP Schema:
  - `repo_path`: required string
  - `job_id`: optional string or null (default null)
  - `max_skipped_files`: optional integer or null (default 10)
  - `allow_large_output`: optional boolean (default false)

---

## RUNTIME_LOOKUP_SIGNATURE
- Sygnatura Python:
  `def lookup_index_entries(repo_path: str, ids: list[str], allow_large_output: bool = False) -> str:`
- FastMCP Schema:
  - `repo_path`: required string
  - `ids`: required array of strings
  - `allow_large_output`: optional boolean (default false)

---

## SMALL_STATUS_RESULT
Dla realnego istniejącego zadania (`7d3854b0f2ce478da61ab50ed8556084`) o rozmiarze 610 B (poniżej progu 15360 B):
- Wynik zwracany jest bezpośrednio jako standardowy obiekt JSON statusu.
- Brak statusu `confirmation_required` i brak metadanych bramki preflight.

---

## SMALL_STATUS_OVERRIDE_RESULT
Wywołanie tej samej operacji z jawnym `allow_large_output=True` zwraca semantycznie i strukturalnie identyczny wynik (`identical_with_override = True`).

---

## LARGE_STATUS_RUNTIME_CASE
`N/A_NO_NATURAL_LARGE_JOB`
Wszystkie 11 istniejących zadań w katalogu `.contextor/analysis_jobs/` mają rozmiar w przedziale 592–716 B (nawet przy `max_skipped_files=None`), ponieważ na bieżącym repozytorium nie występują setki plików z błędami składni. Zgodnie z wytycznymi nie uruchamiano sztucznej pełnej analizy, a certyfikacja dużej gałęzi opiera się na przechodzącym teście jednostkowym `test_get_analysis_status_large_output_preflight_gate`.

---

## LARGE_STATUS_PREFLIGHT_RESULT
W teście z kontrolowaną dużą liczbą pominiętych plików (250 plików > 15 KiB) przy `allow_large_output=False`:
- `status`: `"confirmation_required"`
- `reason`: `"Estimated output exceeds the recommended context size."`
- `warning_threshold_bytes`: 15360
- `warning_threshold_kib`: 15.0
- `retry`: `{"allow_large_output": true}`
- `retry_instruction`: `"Repeat the same get_analysis_status call with the same repo_path, job_id, and max_skipped_files and set allow_large_output=true."`
- Brak echa `repo_path`, `job_id` ani listy pominiętych plików.

---

## LARGE_STATUS_WARNING_BYTES
< 1024 bajtów (zwarta odpowiedź ostrzegawcza).

---

## LARGE_STATUS_OVERRIDE_RESULT
Wywołanie z jawnym `allow_large_output=True` zwraca pełny, bezstratny status zadania ze wszystkimi 250 wpisami pominiętych plików.

---

## CURRENT_SNAPSHOT_SIZE_RESULT
Pole `estimated_output_bytes` raportuje dokładną liczbę bajtów UTF-8 bieżącej migawki zadania wygenerowanej w momencie decyzji preflight. W przypadku stabilnego zadania wielkość ładunku przy ponowieniu `allow_large_output=True` wynosi dokładnie 100% wartości estymowanej.

---

## LOOKUP_REGRESSION_PREFLIGHT
Dla partii 200 identyfikatorów (`> 15360 B`) przy `allow_large_output=False`:
- `status`: `"confirmation_required"`
- `requested_count`: 200
- `warning_response_bytes`: 468 B (< 1024 B)
- Brak echa `ids` i brak echa `repo_path`.

---

## LOOKUP_CERTIFIED_REASON
`"Estimated lookup output exceeds the recommended context size."` (w 100% zgodny z pierwotnym certyfikowanym kontraktem).

---

## LOOKUP_PREDICTED_BYTES
**21,310 bajtów**

---

## LOOKUP_ACTUAL_APPROVED_BYTES
**21,310 bajtów**

---

## LOOKUP_EXACT_SIZE_MATCH
**YES** (21310 B == 21310 B, dokładna zgodność 1:1).

---

## SHARED_THRESHOLD_CERTIFICATION
Oba narzędzia MCP (`lookup_index_entries`, `get_analysis_status`) korzystają ze wspólnego modułu `contextor.mcp.output_guard.guard_large_output` i stosują identyczny próg:
- `LARGE_OUTPUT_WARNING_BYTES = 15360`
- `<= 15360 B`: bezpośrednia emisja standardowej odpowiedzi
- `> 15360 B`: zwrot zwartego monitu `confirmation_required`

---

## OUTPUT_GUARD_CONSUMERS_TOTAL
**3**

---

## OUTPUT_GUARD_PRODUCTION_CONSUMERS
**2** (`contextor.mcp.tools.get_analysis_status`, `contextor.mcp.tools.lookup_index_entries`).

---

## OUTPUT_GUARD_THIRD_CONSUMER_EXPLANATION
Trzecim bezpośrednim konsumentem (`tests.test_mcp_regressions`) jest moduł testów jednostkowych weryfikujący bezpośrednio warunki brzegowe helpera `guard_large_output` (`test_output_guard_boundary_and_contract`). Brak jakichkolwiek niejawnych zależności produkcyjnych ani relacji tool->tool.

---

## CONTEXTOR_RUNTIME_SANITY
- `contextor/mcp/output_guard.py`: `module_id="270/1"`, `layer="adapter"`, `public_api.total=2`, `imports.total=0`, `consumers.total=3`.
- `contextor/mcp/tools/get_analysis_status.py`: `module_id="248/1"`, `layer="adapter"`, `public_api.total=1`, `imports.total=2`, `consumers.total=2`.
- `contextor/mcp/tools/lookup_index_entries.py`: `module_id="240/2"`, `layer="adapter"`, `public_api.total=1`, `imports.total=2`, `consumers.total=3`.

---

## OPEN_P0
0

## OPEN_P1
0

## OPEN_P2
0

## OPEN_P3
0

---

## STEP_VERDICT
`PASS`

---

A18 CLOSED — get_analysis_status and lookup_index_entries share the runtime-certified 15 KiB agent-controlled context-safety guard with no regression of the certified lookup contract.
