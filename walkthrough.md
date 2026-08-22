# TOKEN EFFICIENCY — STEP A12.4F3: FINAL DIAGNOSTICS-INVARIANCE PROOF AND PUBLIC SIZE-TERMINOLOGY CORRECTION

## FILES_CHANGED
- `C:\Temp\Contextor_Repo\contextor\mcp\docs\extract_indexed_report_context.json`

---

## F3_ACTUAL_DIFF

```diff
diff --git a/contextor/mcp/docs/extract_indexed_report_context.json b/contextor/mcp/docs/extract_indexed_report_context.json
index 42f65ab..ebe6178 100644
--- a/contextor/mcp/docs/extract_indexed_report_context.json
+++ b/contextor/mcp/docs/extract_indexed_report_context.json
@@ -10,3 +10,3 @@
     "``representation`` (default ``None``) selects the serialization format:\n- ``None``: preserves legacy behavior controlled by ``resolve_indices``;\n- ``'named'``: emits human-readable symbol names using representation-independent canonical artifact-ID ordering;\n- ``'indexed'``: emits compact indexed IDs using the same canonical ordering and attaches ``resolve_via: 'lookup_index_entries'``;\n- ``'auto'``: stateless candidate size negotiation. When indexed representation materially reduces serialized payload size, returns a compact decision response with directly executable retry options; otherwise returns a direct named result.\nNon-None ``representation`` takes deterministic precedence over ``resolve_indices``. When ``total > max_items``, explicit representation modes use canonical artifact-ID bounding, which may differ from legacy symbol-string bounding. Under ``representation='auto'``, ``expand`` descriptors in direct-auto results preserve ``representation='auto'`` (E1): ``retry_with_full_evidence`` expands evidence scope but may return a decision response if the expanded payload is material; ``retry_fully_lossless`` requests complete top-level and nested scope under auto. An immediate lossless domain payload is obtained by passing explicit ``representation='named'`` or ``'indexed'`` with ``max_items=None, evidence_limit=None``."
```

---

## OMITTED_BLOCKS_REPRESENTATION_INVARIANT
`YES`

## OMITTED_BLOCKS_SOURCE_REASON
W `contextor/core/report_query.py` (`rewrite_selected_indices`, linie 641, 647, 654) walidacja obecności `artifact_id` i `definer_module` w katalogu (`artifact_name()` i `module_name()`) wykonuje się bezwarunkowo, niezależnie od wartości flagi `resolve_names` (`True` lub `False`). Ponieważ `selected_blocks` jest ścisłym podzbiorem bloków przetworzonych w `res_base = query_indexed_report(..., resolve_indices=False)`, zbiór `omitted_blocks` dla kandydata jest podzbiorem `res_base["diagnostics"]["omitted_blocks"]` i nie może zawierać żadnego nowego wpisu.

---

## DROPPED_REFERENCES_REPRESENTATION_INVARIANT
`YES`

## DROPPED_REFERENCES_SOURCE_REASON
W `contextor/core/report_query.py` (`rewrite_selected_indices`, linie 678–686 dla `consumer_module_indices` oraz linie 606–611 dla zagnieżdżonych `usage`) sprawdzenie `module_name(consumer_id)` i ewentualne dołączenie do `diagnostics["dropped_references"]` następuje przed rozgałęzieniem `if resolve_names:`. Zarówno w trybie indeksowanym (`resolve_names=False`), jak i nazwanym (`resolve_names=True`) nieznane identyfikatory modułów są wykrywane i rejestrowane w identyczny sposób.

---

## RESOLVED_FROM_RECOVERY_REPRESENTATION_INVARIANT
`YES`

## RESOLVED_FROM_RECOVERY_SOURCE_REASON
W `contextor/core/report_query.py` (`rewrite_selected_indices`, linie 665, 669, 690 oraz 612) sprawdzenia `if artifact_source == "recovery":` oraz `if definer_source == "recovery":` / `consumer_source == "recovery"` są wykonywane zarówno dla `resolve_names=False`, jak i `resolve_names=True`. Zatem `res_base["diagnostics"]["resolved_from_recovery"]` zawiera już wszystkie odzyskane wpisy dla całego dopasowanego zakresu zapytania.

---

## CURRENT_MERGE_CORRECT
`YES` (wszystkie rodzaje diagnostyk są representation-invariant na poziomie kodu źródłowego; obecna implementacja inicjalizująca `merged_diagnostics` z pełnego `res_base["diagnostics"]` i deduplikująca ewentualne wpisy recovery jest w 100% poprawna i kompletna).

---

## DIAGNOSTICS_FIX
`NONE_REQUIRED` (kod produkcyjny poprawnie zachowuje diagnostyki zapytania i nie wymaga zmian).

---

## FULL_SCOPE_DIAGNOSTICS_PRESERVED
`YES` (pełne diagnostyki zapytania dla całego zakresu dopasowań są zachowane w odpowiedzi pomimo ograniczenia `max_items`).

---

## CANDIDATE_SPECIFIC_DIAGNOSTICS_PRESERVED
`YES` (diagnostyki generowane podczas budowania odpowiedzi kandydata są w pełni reprezentowane w zwracanym obiekcie).

---

## AUTO_SIZE_EXACTNESS_PRESERVED
`YES` (wartości `sizes.named_bytes` i `sizes.indexed_bytes` w odpowiedzi decyzyjnej `auto` dokładnie odpowiadają zserializowanym bajtom UTF-8 wykonywalnych opcji `options["named"]` i `options["indexed"]`).

---

## DOC_SIZE_TERMINOLOGY_CORRECTED
`YES` (sformułowanie w `extract_indexed_report_context.json` zmieniono z `saves material payload tokens` na `materially reduces serialized payload size`).

---

## LEGACY_REPRESENTATION_NONE_UNCHANGED
`YES`

---

## A12_3_SEMANTICS_UNCHANGED
`YES`

---

## TARGETED_TEST_COMMANDS
```powershell
.venv\Scripts\pytest.exe tests/test_mcp_split_s2e.py tests/test_mcp_documentation.py tests/test_mcp_regressions.py -k "extract_indexed_report_context or test_documentation_has_exact_public_tool_file_coverage or test_s2e_registration_order_bindings_signatures_and_descriptions" -v
```

---

## TARGETED_TEST_RESULTS
- `tests/test_mcp_split_s2e.py::test_s2e_registration_order_bindings_signatures_and_descriptions` **PASSED**
- `tests/test_mcp_documentation.py::test_documentation_has_exact_public_tool_file_coverage` **PASSED**
- `tests/test_mcp_regressions.py::test_extract_indexed_report_context_returns_every_shared_resolver_block` **PASSED**
- `tests/test_mcp_regressions.py::test_extract_indexed_report_context_can_filter_to_public_api` **PASSED**
- `tests/test_mcp_regressions.py::test_extract_indexed_report_context_nested_progressive_disclosure` **PASSED**
- `tests/test_mcp_regressions.py::test_extract_indexed_report_context_representation_negotiation` **PASSED**
- **Wynik:** **6 passed, 84 deselected in 3.57s** (100% PASS).

---

## REPRESENTATION_HELPER_MODIFIED
`NO` (`contextor/mcp/representation.py` nie był modyfikowany).

---

## UNEXPECTED_SCOPE_CHANGES
`NONE`

---

## MCP_RESTART_REQUIRED=YES

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

## NEXT_STEP_PROPOSAL
STEP A12.4 CERTIFIED IN SOURCE — manual MCP restart required for final runtime certification; no further source-design steps required.
