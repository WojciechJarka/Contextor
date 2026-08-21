# TOKEN EFFICIENCY — STEP A1.2: BOUNDED_ITEMS & CURRENT COMPLETENESS SEMANTICS

## FILES_CHANGED=NONE

---

## BOUNDED_ITEMS_IMPLEMENTATION

Kompletna implementacja symbolu `contextor.mcp.query_helpers::bounded_items` (linie 10–16 w `contextor/mcp/query_helpers.py`):

```python
def bounded_items(items: list, limit: int | None) -> tuple[list, int, bool]:
    total = len(items)
    if limit is None:
        return items, total, False
    safe_limit = max(0, int(limit))
    selected = items[:safe_limit]
    return selected, total, total > len(selected)
```

---

## MAX_ITEMS_NONE_SEMANTICS

- Gdy `limit is None`:
  - Funkcja natychmiast zwraca `items, total, False`.
  - Zwracana jest **pełna, nieobcięta kolekcja**, dokładna liczba elementów `total = len(items)` oraz flaga `truncated = False`.
  - Jest to w 100% bezstratna ścieżka (lossless).

---

## MAX_ITEMS_ZERO_SEMANTICS

- Gdy `limit == 0`:
  - `safe_limit = max(0, int(0)) -> 0`.
  - `selected = items[:0] -> []`.
  - Zwraca `([], total, total > 0)`:
    - Jeśli `total > 0`: zwraca pustą listę elementów oraz `truncated = True`.
    - Jeśli `total == 0`: zwraca pustą listę elementów oraz `truncated = False`.

---

## CURRENT_LOSSLESS_PATH

- Wywołanie `get_module_context(repo_path, module_name, compact=False, max_items=None)` stanowi w obecnym kodzie **istniejącą ścieżkę bezstratną (lossless complete)**:
  - `compact=False` włącza gałąź `full_result` z kluczem `"items"`.
  - `max_items=None` przekazuje `limit=None` do `bounded_items`, co skutkuje zwróceniem wszystkich elementów bez obcinania (`truncated=False`).

---

## COMPACT_COMPLETENESS_SEMANTICS

- W `get_module_context`:
  - Gdy `compact=True` (wartość domyślna): zwracany jest słownik `compact_result`, który **zawsze usuwa klucz `items`**, niezależnie od wartości `total` czy `max_items`.
  - W efekcie, gdy np. moduł posiada 1 zależność wejściową (`total = 1`), a `max_items = 30`, odpowiedź przyjmuje postać:
    ```json
    "dependencies_inbound_who_calls_me": {
      "total": 1,
      "truncated": false
    }
    ```
  - **`SEMANTIC_GAP_COMPACT_COMPLETENESS`:** Odpowiedź deklaruje `truncated: false` (ponieważ kolekcja nie przekroczyła `max_items`), ale jednocześnie nie udostępnia żadnego elementu (brak klucza `items`). Flaga `truncated` oznacza obecnie jedynie stan obcięcia przez `bounded_items`, a nie obecność kompletnych danych w payloadzie.

---

## EXISTING_TEST_CONTRACTS

1. **Brak klucza `items` przy `compact=True`:**
   - Test `tests/test_mcp_regressions.py::test_mcp_canonical_queries_support_fields_filtering` (l. 2057–2064):
     ```python
     assert result["dependencies_inbound_who_calls_me"] == {
         "total": 1,
         "truncated": False,
     }
     assert result["dependencies_outbound_who_i_call"] == {
         "total": 2,
         "truncated": False,
     }
     ```
     Asertuje dokładną strukturę słownika bez klucza `items`.

2. **Obecność klucza `items` i `truncated=True` przy `compact=False`:**
   - `tests/test_mcp_regressions.py::test_mcp_canonical_queries_support_fields_filtering` (l. 2078–2085):
     ```python
     assert set(full["dependencies_inbound_who_calls_me"]["items"]) == {"pkg.caller"}
     assert full["dependencies_inbound_who_calls_me"]["total"] == 1
     assert full["dependencies_inbound_who_calls_me"]["truncated"] is False
     assert len(full["dependencies_outbound_who_i_call"]["items"]) == 1
     assert full["dependencies_outbound_who_i_call"]["total"] == 2
     assert full["dependencies_outbound_who_i_call"]["truncated"] is True
     ```

3. **Zachowanie metryk i źródeł:**
   - `tests/test_incremental_local_metrics.py::test_stage2c_get_module_context_behavior_preserved` (l. 605–617):
     Weryfikuje wartości `fan_in`, `fan_out` oraz `degree_metrics_source: "live_canonical_graph"` w domyślnym trybie compact.

---

## SEMANTIC_GAPS

1. **`SEMANTIC_GAP_COMPACT_COMPLETENESS`:** W `compact=True` klient otrzymuje `truncated: false`, ale 0 elementów `items`.
2. **`SEMANTIC_GAP_BINARY_COMPACT`:** Brak poziomu pośredniego `summary` z ograniczoną próbką relacji (bounded evidence top N w zwięzłej formie token-efficient).
3. **`SEMANTIC_GAP_EXPANSION_DISCOVERY`:** Payload obcięty (`truncated: true`) nie zawiera jawnego pola sugerującego sposób pobrania pełnej listy (np. `next_offset` lub `expand_via: {"compact": false, "max_items": null}`).

---

## NEXT_SMALLEST_DESIGN_DECISION

- Zdefiniować docelowy model wielopoziomowego disclosure dla `get_module_context`:
  1. Domyślny widok summary (zwięzłe metryki + bounded evidence bez powielania metadanych per-item).
  2. Widok pełny/rozszerzony (lossless z `items`, zachowujący wsteczną kompatybilność z istniejącymi asercjami `compact=False`).

---

## STEP_VERDICT

`PASS`

---

## NEXT_STEP_PROPOSAL

**TOKEN EFFICIENCY — STEP A1.3: GET_MODULE_CONTEXT TOKEN-OPTIMIZED RESPONSE SPECIFICATION**
- Opracować dokładną specyfikację formatu JSON dla `get_module_context` (summary vs full vs fields).
- Zaprezentować kalkulację oszczędności tokenów (before/after) na realnych danych repozytorium.
