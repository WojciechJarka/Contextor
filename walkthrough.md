# SP-T4-REMAINING-R2B — KOREKTA RECOVERY AVAILABILITY

## PRECHECK

- DIRECT_EVIDENCE — Contextor MCP przed zmianą: LIVE revision 1458, provenance live, canonical state fresh, global workspace_sync unverified, resync_required=false. Syntax diagnostics 0/fresh; graph fresh; structural cycles 16/fresh.
- DIRECT_EVIDENCE — MCP symbol preview dla test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation: workspace_sync=verified, canonical revision 1458, provenance live. Source anchor w LIVE pasował dokładnie do podanego bloku recovery.
- DIRECT_EVIDENCE — Git przed zmianą: HEAD 4c3578c344882e141d22cca5277a433d008e875e; status czysty. Plik testowy nie miał wcześniejszego diffu.
- CPython target: 3.15.2; repo .venv.

## EXACT_CHANGE

Zmieniono wyłącznie drugą asercję availability w test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation, dodając:

    "soft_dependent_potential_cycles": "unavailable",

Pozostałe asercje, testy i kod produkcyjny pozostały bez zmian.

## TARGETED_RESULTS

Uruchomiono wyłącznie poniższe node IDs z tests/test_mcp_diagnostics.py na CPython 3.15.2, z --tb=long:

| Node ID | Wynik |
|---|---|
| tests/test_mcp_diagnostics.py::test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation | PASS |
| tests/test_mcp_diagnostics.py::test_get_name_collisions_hides_fresh_details_during_resync | PASS |
| tests/test_mcp_diagnostics.py::test_wrapper_diagnostics_exception_cannot_replace_successful_tool_result | PASS |

Wynik: 3 passed, 2 warnings in 4.66s. Dwa ostrzeżenia to AuthlibDeprecationWarning z importów Authlib/JWT i Authlib HTTPX. Brak tracebacków. Nie uruchamiano pełnego pytest ani FULL.

## CONTRACT_VERIFICATION

- CODE_PATH_PROVED — MCP odczytał contextor/core/diagnostics_projection.py:22-64. Po resync_required=False funkcja wymaga cycles_state=fresh i dependency_graph.hard_edges/soft_edges typu Mapping; w przeciwnym razie zwraca availability=unavailable.
- DIRECT_EVIDENCE — test tworzy SimpleNamespace z resync_required oraz markerami składni/collisions/cycles, ale bez dependency_graph (tests/test_mcp_diagnostics.py:119-171). Zatem po usunięciu resync, trzy rodziny raportują fresh, a soft-dependent potential-cycle diagnostyka pozostaje unavailable.
- CONTRACT_PROVED — dodana wartość odpowiada aktualnej gałęzi źródła dla syntetycznego stanu bez dependency_graph; wszystkie trzy wskazane testy przechodzą.
- MCP post-change audit: LIVE revision 1459, provenance live, canonical state fresh, global workspace_sync unverified, resync_required=false; syntax diagnostics 0/fresh; graph fresh; cycles 16/fresh.
- Per-file MCP audit: tests/test_mcp_diagnostics.py ma workspace_sync=verified na revision 1459. MCP get_source_range odczytał zmieniony anchor dokładnie w żądanej postaci.
- HEAD po zadaniu pozostał 4c3578c344882e141d22cca5277a433d008e875e. Zmiana pliku testowego jest niezacommitowana, zgodnie z instrukcją.

## FILES_CHANGED

- tests/test_mcp_diagnostics.py
- walkthrough.md — nadpisany raport; wyłączony z własnego diffu.

## FULL_DIFFS

~~~diff
diff --git a/tests/test_mcp_diagnostics.py b/tests/test_mcp_diagnostics.py
index d92f950..b04d364 100644
--- a/tests/test_mcp_diagnostics.py
+++ b/tests/test_mcp_diagnostics.py
@@ -164,6 +164,7 @@ def test_resync_diagnostics_summary_hides_fresh_payloads_without_mutation():
         "syntax_errors": "fresh",
         "name_collisions": "fresh",
         "cycles": "fresh",
+        "soft_dependent_potential_cycles": "unavailable",
     }
     assert recovered["syntax_errors"]["count"] == 1
     assert recovered["name_collisions"]["count"] == 1
~~~
