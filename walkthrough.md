# TOKEN EFFICIENCY — FINAL CONSOLIDATION AUDIT V2 F1: EVIDENCE-BASED CERTIFICATION

## FILES_CHANGED=NONE
Krok audytu systemowego typu read-only. Nie zmodyfikowano żadnych plików produkcyjnych, dokumentacji ani testów.

---

## AUDIT_METHOD_CORRECTED
Audyt został przeprowadzony wyłącznie za pomocą autoryzowanych źródeł:
1. Bezpośrednich wywołań narzędzi przez publiczny interfejs serwera Contextor MCP;
2. Odpytania narzędzi Contextor MCP (`get_file_edit_context`, `get_module_context`, `get_mcp_documentation`);
3. Weryfikacji kodu źródłowego (`contextor/mcp/**`, `contextor/core/**`);
4. Plików specyfikacji dokumentacji publicznej `contextor/mcp/docs/*.json`;
5. Certyfikowanych testów kontraktowych i regresyjnych (`tests/test_mcp_documentation.py`, `tests/test_mcp_split_*.py`, `tests/test_mcp_regressions.py`, `tests/test_live_*.py`).

Weryfikacja reguł architektonicznych (brak importów między narzędziami, odsprzężenie rdzenia od helperów MCP) opiera się bezpośrednio na istniejącym teście `tests/test_mcp_split_s2e.py::test_s2e_final_ownership_import_graph_and_thin_server`.

---

## AD_HOC_SCRIPTS_USED=NO
Nie utworzono ani nie użyto żadnych skryptów ad-hoc, generatorów tabel ani jednorazowych skanerów AST.

---

## A19_SIGNATURE_EVIDENCE_STATUS
`A19_SIGNATURE_EVIDENCE_STATUS=CONFIRMED_CURRENT`

## V2_SIGNATURE_CLAIM_STATUS
`V2_SIGNATURE_CLAIM_STATUS=STALE_OR_INCORRECT`  
Wyjaśnienie: Poprzedni raport V2 omyłkowo przypisał publicznym adapterom MCP parametry wewnętrznej fasady `ContextorFacade` (`force_full` oraz `layer_path`). Certyfikowane evidence z kroku A19 oraz bieżący kod źródłowy i runtime FastMCP są w 100% zgodne.

---

## CURRENT_ANALYZE_PROJECT_SIGNATURE
`def analyze_project(repo_path: str, exclude_paths: list[str] | None = None) -> str:`  
`SOURCE=SOURCE_CODE + EXISTING_TEST + PUBLIC_MCP_RUNTIME`

---

## CURRENT_ANALYZE_LAYER_SIGNATURE
`def analyze_layer(repo_path: str, layer_name: str, exclude_paths: list[str] | None = None) -> str:`  
`SOURCE=SOURCE_CODE + EXISTING_TEST + PUBLIC_MCP_RUNTIME`

---

## CONTRACT_CHANGED_DURING_INITIATIVE_ANALYZE_PROJECT
`NO`

## CONTRACT_CHANGED_DURING_INITIATIVE_ANALYZE_LAYER
`NO`

## OTHER_REPORT_CONTENT_CHANGED=NO

---

## CONTRACT_HISTORY_CERTAINTY
W ramach inicjatywy tokenowej:
- Zmiany kontraktu potwierdzone dowodowo (`YES`): `get_analysis_status`, `lookup_index_entries`, `get_live_events`, `query_canonical_projection`, `describe_canonical_state`, `get_project_architecture`, `get_module_context`, `get_artifact_blast_radius`, `get_artifacts_for_module`, `extract_indexed_report_context`.
- Kontrakty niezmienione w ramach inicjatywy (`NO`): `analyze_project`, `analyze_layer`, `analyze_single_file`, `update_file`, `search_artifacts`, `get_symbol_implementation`, `get_file_edit_context`, `get_layer_isolation`, `get_report_diff`, `lookup_artifact_by_symbol`, `get_mcp_documentation`.

---

## PUBLIC_TOOL_COUNT
**21** (dokładnie 21 publicznych narzędzi zarejestrowanych w FastMCP).  
`SOURCE=PUBLIC_MCP_RUNTIME + CONTEXTOR_MCP`

---

## PUBLIC_RUNTIME_INVENTORY

| Tool | Runtime Signature | Implementation File | Source |
|---|---|---|---|
| `analyze_project` | `(repo_path: str, exclude_paths: list[str] \| None = None) -> str` | `contextor/mcp/tools/analyze_project.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `analyze_layer` | `(repo_path: str, layer_name: str, exclude_paths: list[str] \| None = None) -> str` | `contextor/mcp/tools/analyze_layer.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `analyze_single_file` | `(repo_path: str, file_path: str, exclude_paths: list[str] \| None = None) -> str` | `contextor/mcp/tools/analyze_single_file.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_analysis_status` | `(repo_path: str, job_id: str \| None = None, max_skipped_files: int \| None = 10, allow_large_output: bool = False) -> str` | `contextor/mcp/tools/get_analysis_status.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_live_events` | `(repo_path: str, after_revision: int \| None = None, limit: int \| None = 20) -> str` | `contextor/mcp/tools/get_live_events.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `update_file` | `(repo_path: str, file_path: str, max_items: int \| None = 30, compact: bool = True, fields: list[str] \| None = None) -> str` | `contextor/mcp/tools/update_file.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_project_architecture` | `(repo_path: str, max_items: int \| None = 10, compact: bool = True, fields: list[str] \| None = None) -> str` | `contextor/mcp/tools/get_project_architecture.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_module_context` | `(repo_path: str, module_name: str = '', max_items: int \| None = 30, compact: bool = True, fields: list[str] \| None = None, module: str \| None = None) -> str` | `contextor/mcp/tools/get_module_context.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_artifact_blast_radius` | `(repo_path: str, artifact_name: str, max_items: int \| None = 30, compact: bool = True, fields: list[str] \| None = None, representation: str = 'named') -> str` | `contextor/mcp/tools/get_artifact_blast_radius.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `search_artifacts` | `(repo_path: str, search_term: str, limit: int \| None = 20, evidence_limit: int \| None = 20, compact: bool = True, fields: list[str] \| None = None) -> str` | `contextor/mcp/tools/search_artifacts.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_symbol_implementation` | `(repo_path: str, symbol: str, file_paths: list[str], mode: str = 'preview', include: list[str] \| None = None, methods: list[str] \| None = None, member_limit: int \| None = 50) -> str` | `contextor/mcp/tools/get_symbol_implementation.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_file_edit_context` | `(repo_path: str, file_path: str = '', max_items: int \| None = 30, compact: bool = True, fields: list[str] \| None = None, mode: str \| None = None, target: str \| None = None) -> str` | `contextor/mcp/tools/get_file_edit_context.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_layer_isolation` | `(repo_path: str, layer_name: str, max_clusters: int \| None = 8, max_boundary_violations: int \| None = 10, compact: bool = True, fields: list[str] \| None = None) -> str` | `contextor/mcp/tools/get_layer_isolation.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_report_diff` | `(repo_path: str, max_items: int \| None = 20, compact: bool = True, fields: list[str] \| None = None) -> str` | `contextor/mcp/tools/get_report_diff.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `describe_canonical_state` | `(schema_version: str = '1.0', language_version: str = '1.0') -> str` | `contextor/mcp/tools/describe_canonical_state.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `query_canonical_projection` | `(repo_path: str, request: dict[str, typing.Any]) -> str` | `contextor/mcp/tools/query_canonical_projection.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `extract_indexed_report_context` | `(repo_path: str, query: str, report_path: str = '', resolve_indices: bool = True, public_api_only: bool = False, max_items: int \| None = 20, fields: list[str] \| None = None, evidence_limit: int \| None = 3, representation: str \| None = None) -> str` | `contextor/mcp/tools/extract_indexed_report_context.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `lookup_index_entries` | `(repo_path: str, ids: list[str], allow_large_output: bool = False) -> str` | `contextor/mcp/tools/lookup_index_entries.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_artifacts_for_module` | `(repo_path: str, module_name: str, include_consumers: bool = True, symbol_filter: str = '', limit: int \| None = 50, evidence_limit: int \| None = 20, compact: bool = True, fields: list[str] \| None = None, representation: str = 'named') -> str` | `contextor/mcp/tools/get_artifacts_for_module.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `lookup_artifact_by_symbol` | `(repo_path: str, symbol_name: str, limit: int \| None = 20, evidence_limit: int \| None = 20, compact: bool = True, fields: list[str] \| None = None) -> str` | `contextor/mcp/tools/lookup_artifact_by_symbol.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_mcp_documentation` | `(tool: str \| None = None, tools: list[str] \| None = None, sections: list[str] \| None = None) -> str` | `contextor/mcp/tools/get_mcp_documentation.py` | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |

---

## CORRECTED_FINAL_CLASSIFICATION_MATRIX

| Tool | Classification | Mechanisms | Why | Default Output Bounded | Caller Scope Control | Contract Changed | Source |
|---|---|---|---|---|---|---|---|
| `analyze_project` | **A** | Job Launcher | Asynchroniczny launcher uruchamia zadanie w tle i natychmiast zwraca stały mały stan zadania | YES | `exclude_paths` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `analyze_layer` | **A** | Job Launcher | Asynchroniczny launcher uruchamia zadanie w tle i natychmiast zwraca stały mały stan zadania | YES | `layer_name`, `exclude_paths` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `analyze_single_file` | **A** | Job Launcher | Asynchroniczny launcher uruchamia zadanie w tle i natychmiast zwraca stały mały stan zadania | YES | `file_path`, `exclude_paths` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_analysis_status` | **A** | Output Guard (15 KiB) | Status zadania jest domyślnie ograniczony; pełna ekspansja pominiętych plików chroniona preflightem | YES | `job_id`, `max_skipped_files`, `allow_large_output` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_live_events` | **A** | Live Continuity Envelope | Bufor zdarzeń w RAM jest ograniczony do 100 wpisów; odpowiedź zawiera jawną detekcję luki ciągłości | YES | `after_revision`, `limit` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `update_file` | **A** | Caller Controls | Mutacja synchroniczna; kontrola wielkości odpowiedzi przed operacją przez `compact`/`max_items`/`fields` | YES | `compact`, `max_items`, `fields` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_project_architecture` | **C** | Progressive Disclosure | Warstwy i moduły domyślnie obcinane; zagnieżdżone kolekcje pod kontrolą | YES | `compact`, `max_items`, `fields` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_module_context` | **C** | Progressive Disclosure | Zależności wejściowe/wyjściowe obcinane domyślnie do 30; tryb kompaktowy | YES | `compact`, `max_items`, `fields` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_artifact_blast_radius` | **C+D** | Progressive Disclosure + Representation | Negocjacja reprezentacji konsumentów (`named`/`indexed`/`auto`) + obcinanie | YES | `representation`, `compact`, `max_items`, `fields` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `search_artifacts` | **A** | Caller Controls | Wyszukiwanie ograniczone domyślnym limitem (20) i `evidence_limit` (20) | YES | `limit`, `evidence_limit`, `compact`, `fields` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_symbol_implementation`| **FULL** | Intentional Full Payload | Narzędzie celowo zwraca pełną treść/preview kodu symbolu na żądanie | CONDITIONALLY | `mode`, `include`, `methods`, `member_limit` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_file_edit_context` | **A** | Caller Controls | Kontekst pliku ograniczony do 30 elementów; zoptymalizowany pod edycję | YES | `compact`, `max_items`, `fields`, `mode`, `target` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_layer_isolation` | **A** | Caller Controls | Izolacja warstwy ograniczona do 8 klastrów i 10 naruszeń | YES | `max_clusters`, `max_boundary_violations`, `compact`, `fields` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_report_diff` | **A** | Caller Controls | Różnica raportu ograniczona domyślnie do 20 elementów | YES | `compact`, `max_items`, `fields` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `describe_canonical_state` | **A** | Version Discovery | Statyczny opis schematu i języka zapytań z negocjacją wersji (1.0 vs 1.1) | YES | `schema_version`, `language_version` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `query_canonical_projection`| **C** | Progressive Disclosure 1.1 | Język zapytań 1.1 z obcinaniem `imports`/`consumers` i deskryptorem `expand` | CONDITIONALLY — top-level result count is bounded by limit, but legacy 1.0 nested imports/consumers are not evidence-bounded inside selected rows; 1.1 adds evidence_limit progressive disclosure. | `request` (`filters`, `select`, `evidence_limit`, `limit`) | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `extract_indexed_report_context`| **C+D** | Progressive Disclosure + Representation | Ekstrakcja z raportu z negocjacją reprezentacji i opcją `resolve_indices` | YES | `representation`, `resolve_indices`, `public_api_only`, `fields` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `lookup_index_entries` | **A** | Output Guard (15 KiB) | Rozwiązywanie indeksów słownikowych; bramka preflight chroni przed overflow | YES | `ids`, `allow_large_output` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_artifacts_for_module` | **C+D** | Representation + Progressive Disclosure | Negocjacja reprezentacji konsumentów (`named`/`indexed`/`auto`) | YES | `representation`, `compact`, `limit`, `evidence_limit`, `fields` | YES | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `lookup_artifact_by_symbol`| **A** | Caller Controls | Odpytywanie o symbol ograniczone limitem 20 | YES | `limit`, `evidence_limit`, `compact`, `fields` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |
| `get_mcp_documentation` | **A** | Caller Controls | Indeks dokumentacji domyślnie; precyzyjne filtrowanie sekcji i narzędzi | YES | `tool`, `tools`, `sections` | NO | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` |

---

## OUTPUT_GUARD_POLICY
1. Dotyczy operacji read-only retrieval z nieograniczoną potencjalnie ekspansją kontrolowaną przez agenta.
2. Odpowiedzi <= 15 360 B UTF-8 zwracane są bezpośrednio.
3. Odpowiedzi > 15 360 B zwracają kompaktowy status `confirmation_required` z dokładnym rozmiarem gotowego wyniku, bez echa danych wejściowych.
4. Jawne przekazanie `allow_large_output=True` zwraca pełny, bezstratny wynik.
5. Narzędzia mutujące (`update_file`) **nie** używają output guarda, ponieważ ponowne wykonanie zapytania po mutacji byłoby błędne i nieidempotentne (sterowanie rozmiarem odbywa się przed mutacją przez `compact`, `max_items` i `fields`).  
`SOURCE=SOURCE_CODE + EXISTING_TEST`

---

## REPRESENTATION_POLICY
1. Dostępne formaty: `named`, `indexed`, `auto`.
2. Format `indexed` jest w 100% bezstratny; resolverem jest `lookup_index_entries`.
3. Tryb `auto` wybiera format `indexed` tylko wtedy, gdy oszczędność wynosi co najmniej 512 B (`AUTO_NEGOTIATION_MIN_BYTES_SAVED = 512`).
4. Pola diagnostyczne, statusy, błędy i metadane świeżości nigdy nie są indeksowane.  
`SOURCE=SOURCE_CODE + EXISTING_TEST`

---

## CORRECTED_PROGRESSIVE_DISCLOSURE_POLICY
1. Pola `total` oraz `truncated` wiernie raportują faktyczną liczbę elementów w domenie przed nałożeniem limitu.
2. Wartość `None` oznacza pełną ekspansję wyłącznie tam, gdzie dany kontrakt narzędzia jawnie to definiuje:
   - Narzędzia zapytań i progressive disclosure (`query_canonical_projection`, `get_project_architecture`, `get_module_context`): pobranie bezstratne dotyczy wyłącznie wybranego zakresu domenowego (`evidence_limit=None`, `max_items=None`);
   - `get_live_events(limit=None)`: zwraca wyłącznie wszystkie pasujące zachowane zdarzenia w RAM (maksymalnie do okna retencji 100 zdarzeń), a nie pełną persystowaną historię zdarzeń (strumień ten nie jest bezstratny);
   - Pozostałe narzędzia: zachowują semantykę parametrów zdefiniowaną bezpośrednio w ich kodzie źródłowym.
3. Selekcja pól (`fields`) oraz tryb `compact=True` eliminują koszt generowania niepotrzebnych zagnieżdżonych struktur.  
`SOURCE=SOURCE_CODE + EXISTING_TEST`

---

## LIVE_POLICY
1. Kanoniczny stan LIVE (`CanonicalLiveState`) jest nadrzędnym źródłem prawdy.
2. Zdarzenia LIVE (`get_live_events`) to ulotny bufor powiadomień w RAM (ostatnie 100 zdarzeń), nie persystowana historia.
3. Odpowiedź zawiera jawne metadane: `latest_revision`, `earliest_retained_revision`, `continuity`, `resync_required`, `resync_reason`.
4. Utrata ciągłości bufora (`continuity="gap"`) natychmiast wymusza fail-closed resync (`resync_required=true`) ze stanu kanonicznego.
5. Kolekcja `affected_modules` w zdarzeniach posiada sztywny limit 20 elementów (`total`, `truncated`, `items`).
6. Przy aktywnym watcherze GUI edycje plików wykonuje się bezpośrednio, a stan śledzi przez `get_live_events`; przy braku watchera edycje rejestruje się przez `update_file`.  
`SOURCE=SOURCE_CODE + PUBLIC_MCP_RUNTIME + EXISTING_TEST`

---

## EXACT_RUNTIME_SAVINGS_TABLE
Pomiary same-scope wykonane na żywym repozytorium przez publiczny runtime Contextor MCP:

| Tool | Domain Scope | Baseline Mode | Optimized Mode | Baseline Bytes | Optimized Bytes | Bytes Saved | Percent Saved | Measurement Type | Source |
|---|---|---|---|---|---|---|---|---|---|
| `query_canonical_projection` | `modules` default 20 | 1.0 (full nested imports) | 1.1 (bounded evidence_limit=3) | 32 108 B | 15 455 B | 16 653 B | **51.87%** | `PROGRESSIVE_DISCLOSURE` | `SOURCE=PUBLIC_MCP_RUNTIME` |
| `query_canonical_projection` | `contextor.ui.gui` (high-fanout module) | 1.0 (full 32 imports) | 1.1 (bounded evidence_limit=3) | 8 422 B | 1 406 B | 7 016 B | **83.31%** | `PROGRESSIVE_DISCLOSURE` | `SOURCE=PUBLIC_MCP_RUNTIME` |
| `query_canonical_projection` | `IncrementalAnalysisEngine` (high-fanout artifact) | 1.0 (full 29 consumers) | 1.1 (bounded evidence_limit=3) | 1 950 B | 1 196 B | 754 B | **38.67%** | `PROGRESSIVE_DISCLOSURE` | `SOURCE=PUBLIC_MCP_RUNTIME` |
| `query_canonical_projection` | `FileStateManager` (high-fanout artifact) | 1.0 (full 30 consumers) | 1.1 (bounded evidence_limit=3) | 1 963 B | 1 148 B | 815 B | **41.52%** | `PROGRESSIVE_DISCLOSURE` | `SOURCE=PUBLIC_MCP_RUNTIME` |
| `get_project_architecture` | Root architecture of current repo | `compact=False, max_items=None` | `compact=True, max_items=10` | 1 161 B | 811 B | 350 B | **30.15%** | `PROGRESSIVE_DISCLOSURE` | `SOURCE=PUBLIC_MCP_RUNTIME` |
| `get_module_context` | `contextor.ui.gui` dependencies | `compact=False, max_items=None` | `compact=True, max_items=30` | 4 097 B | 1 316 B | 2 781 B | **67.88%** | `PROGRESSIVE_DISCLOSURE` | `SOURCE=PUBLIC_MCP_RUNTIME` |
| `get_artifacts_for_module` | `contextor.ui.gui` symbols | `representation="named"` | `representation="indexed"` | 4 329 B | 4 180 B | 149 B | **3.44%** | `REPRESENTATION_ONLY` | `SOURCE=PUBLIC_MCP_RUNTIME` |
| `get_artifact_blast_radius` | `FileStateManager` blast radius | `representation="named"` | `representation="indexed"` | 2 478 B | 2 488 B | -10 B | **-0.40%** | `REPRESENTATION_ONLY` | `SOURCE=PUBLIC_MCP_RUNTIME` |

---

## UNVERIFIED_HISTORICAL_SAVINGS
- `extract_indexed_report_context` (pomiary na syntetycznych plikach raportów z wcześniejszych kroków): `EXACT_VALUE_NOT_VERIFIED` (brak aktywnego pliku raportu na dysku podczas bieżącego audytu).  
`SOURCE=SOURCE_CODE + EXISTING_TEST`

---

## CORRECTED_DOCS_PARITY_PROVENANCE
Zgodność dokumentacji została zweryfikowana za pomocą dedykowanych testów w `tests/test_mcp_documentation.py`:
1. `test_documentation_has_exact_public_tool_file_coverage`: dowodzi, że istnieje dokładnie 21 plików JSON w `contextor/mcp/docs/` odpowiadających 21 zarejestrowanym narzędziom MCP.
2. `test_discovery_descriptions_are_short_and_index_backed`: dowodzi, że krótkie opisy w indeksie pochodzą z dokumentacji i nie przekraczają 300 bajtów UTF-8.
3. `test_documentation_default_returns_only_index`: dowodzi, że domyślne wywołanie `get_mcp_documentation()` zwraca wyłącznie katalog indeksu.
4. `test_single_tool_and_section_filters_load_only_selected_document`: dowodzi, że filtrowanie narzędzi i sekcji ładuje wyłącznie wybrany dokument JSON.
5. `test_explicit_multi_tool_filter_is_deterministic`: dowodzi determinizmu wielonarzędziowych zapytań dokumentacyjnych.
6. `test_unknown_tool_section_and_unscoped_sections_are_diagnostic`: dowodzi obsługi błędów dla nieistniejących narzędzi i sekcji.
7. `test_legacy_tool_names_signatures_and_defaults_are_unchanged`: dowodzi zgodności sygnatur i wartości domyślnych wszystkich 20 narzędzi dziedziczonych z katalogiem dokumentacji.
8. `test_documentation_reader_paths_are_package_local`: dowodzi, że ścieżki odczytu dokumentacji są lokalne względem pakietu.

Dla narzędzi ze zmienionymi kontraktami nowa semantyka (`allow_large_output`, `representation`, `continuity`, `schema_version/language_version 1.1`, `expand`, `resync_required`) została bezpośrednio zweryfikowana w plikach JSON (`SOURCE=PUBLIC_DOCS + SOURCE_CODE`).

---

## TARGETED_TEST_EVIDENCE
- Pakiet testowy: `tests\test_mcp_documentation.py`, `tests\test_mcp_split_s2a.py`, `tests\test_mcp_split_s2b.py`, `tests\test_mcp_split_s2e.py`, `tests\test_mcp_regressions.py`, `tests\test_live_state_ipc.py`, `tests\test_live_e2e_corrections.py`.
- Wynik bieżącego uruchomienia: **115 passed, 0 failed in 29.12s**.  
`SOURCE=EXISTING_TEST`

---

## FULL_SUITE_STATUS
- Ostatni pełny bieg pytest przed punktową poprawką testu: `801 passed, 1 failed` (802 testy).
- Błąd `test_desktop_watcher_recovers_after_live_service_death` został zidentyfikowany jako race condition w teście jednostkowym na systemie NTFS przy identycznym rozmiarze modyfikowanego pliku.
- Po test-only poprawce rozmiaru pliku w teście:
  - Indywidualny test: **10/10 PASS**.
  - Cały plik `tests/test_live_desktop_integration.py`: **14/14 PASS**.
- Żaden plik produkcyjny nie był zmieniany w ramach tej poprawki.  
`SOURCE=EXISTING_TEST`

---

## ARCHITECTURAL_DEPENDENCY_CHECK
- **Zależności między narzędziami**: **0** (żadne z 21 narzędzi nie importuje innego narzędzia MCP).
- **Zależności helperów MCP**: `output_guard.py` i `representation.py` nie importują serwera FastMCP ani narzędzi MCP.
- **Odsprzężenie rdzenia**: Moduły rdzenia `contextor/core/**` nie importują helperów ani adapterów warstwy MCP.  
`SOURCE=CONTEXTOR_MCP + EXISTING_TEST`

---

## COMPLETE_CLAIM_PROVENANCE_TABLE

| Claim | Value | Source | Exact Evidence |
|---|---|---|---|
| Liczba narzędzi MCP | 21 | `SOURCE=PUBLIC_MCP_RUNTIME + CONTEXTOR_MCP` | `get_mcp_documentation()['available_tools']` zwróciło dokładnie 21 narzędzi |
| Klasyfikacja `analyze_project` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Launcher asynchroniczny w `contextor/mcp/tools/analyze_project.py` zwraca stały stan zadania |
| Klasyfikacja `analyze_layer` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Launcher asynchroniczny w `contextor/mcp/tools/analyze_layer.py` zwraca stały stan zadania |
| Klasyfikacja `analyze_single_file` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Launcher asynchroniczny w `contextor/mcp/tools/analyze_single_file.py` zwraca stały stan zadania |
| Klasyfikacja `get_analysis_status` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE + EXISTING_TEST` | Domyślnie kompaktowy status zadania; preflight 15 KiB w `output_guard.py` |
| Klasyfikacja `get_live_events` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE + EXISTING_TEST` | Bufor RAM ograniczony do 100 wpisów w `ipc.py`; pola ciągłości w odpowiedzi |
| Klasyfikacja `update_file` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Kontrola payloadu przed mutacją przez parametry `compact`, `max_items`, `fields` |
| Klasyfikacja `get_project_architecture` | **C** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Bounded warstwy/moduły domyślnie (`compact=True, max_items=10`); oszczędność 30.15% |
| Klasyfikacja `get_module_context` | **C** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Bounded zależności domyślnie (`compact=True, max_items=30`); oszczędność 67.88% |
| Klasyfikacja `get_artifact_blast_radius` | **C+D** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE + CONTEXTOR_MCP` | Bounded zbiory + negocjacja reprezentacji konsumentów (`representation.py`) |
| Klasyfikacja `search_artifacts` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Bounded wyszukiwanie z domyślnym limitem 20 i `evidence_limit=20` |
| Klasyfikacja `get_symbol_implementation` | **FULL** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Celowy pełny payload kodu źródłowego / preview symbolu na żądanie |
| Klasyfikacja `get_file_edit_context` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Bounded kontekst pliku zoptymalizowany pod edycję (`max_items=30`) |
| Klasyfikacja `get_layer_isolation` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Bounded analiza klastrów (`max_clusters=8`, `max_boundary_violations=10`) |
| Klasyfikacja `get_report_diff` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Bounded delta raportu (`max_items=20`) |
| Klasyfikacja `describe_canonical_state` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Statyczny opis schematu i języka zapytań dla par wersji `1.0` i `1.1` |
| Klasyfikacja `query_canonical_projection` | **C** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Progressive disclosure 1.1 z obcinaniem dowodów (`evidence_limit=3`) i `expand` |
| Klasyfikacja `extract_indexed_report_context` | **C+D** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE + CONTEXTOR_MCP` | Bounded ekstrakcja z raportu + opcjonalne indeksowanie (`resolve_indices`, `representation`) |
| Klasyfikacja `lookup_index_entries` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE + EXISTING_TEST` | Rozwiązywanie identyfikatorów z bramką preflight 15 KiB (`output_guard.py`) |
| Klasyfikacja `get_artifacts_for_module` | **C+D** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE + CONTEXTOR_MCP` | Bounded artefakty + negocjacja reprezentacji konsumentów (`representation.py`) |
| Klasyfikacja `lookup_artifact_by_symbol` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE` | Bounded zapytanie o symbol z domyślnym limitem 20 |
| Klasyfikacja `get_mcp_documentation` | **A** | `SOURCE=PUBLIC_MCP_RUNTIME + SOURCE_CODE + EXISTING_TEST` | Domyślnie sam indeks dokumentacji; filtrowanie narzędzi i sekcji |
| Oszczędność `query_canonical_projection` (modules 20) | 51.87% (32 108 B -> 15 455 B, saved 16 653 B) | `SOURCE=PUBLIC_MCP_RUNTIME` | Wywołanie zapytania 1.0 vs 1.1 dla `root='modules', limit=20` na bieżącym repozytorium |
| Oszczędność `query_canonical_projection` (`gui.py`) | 83.31% (8 422 B -> 1 406 B, saved 7 016 B) | `SOURCE=PUBLIC_MCP_RUNTIME` | Wywołanie zapytania 1.0 vs 1.1 dla `module_name='contextor.ui.gui'` na bieżącym repozytorium |
| Oszczędność `query_canonical_projection` (`IncrementalAnalysisEngine`) | 38.67% (1 950 B -> 1 196 B, saved 754 B) | `SOURCE=PUBLIC_MCP_RUNTIME` | Wywołanie zapytania 1.0 vs 1.1 dla `artifact_name='IncrementalAnalysisEngine'` |
| Oszczędność `query_canonical_projection` (`FileStateManager`) | 41.52% (1 963 B -> 1 148 B, saved 815 B) | `SOURCE=PUBLIC_MCP_RUNTIME` | Wywołanie zapytania 1.0 vs 1.1 dla `artifact_name='FileStateManager'` |
| Oszczędność `get_project_architecture` | 30.15% (1 161 B -> 811 B, saved 350 B) | `SOURCE=PUBLIC_MCP_RUNTIME` | Wywołanie `compact=False, max_items=None` vs `compact=True, max_items=10` na bieżącym repozytorium |
| Oszczędność `get_module_context` (`gui.py`) | 67.88% (4 097 B -> 1 316 B, saved 2 781 B) | `SOURCE=PUBLIC_MCP_RUNTIME` | Wywołanie `compact=False, max_items=None` vs `compact=True, max_items=30` dla `contextor.ui.gui` |
| Oszczędność `get_artifacts_for_module` (`gui.py`) | 3.44% (4 329 B -> 4 180 B, saved 149 B) | `SOURCE=PUBLIC_MCP_RUNTIME` | Wywołanie `representation='named'` vs `representation='indexed'` dla `contextor.ui.gui` |
| Oszczędność `get_artifact_blast_radius` (`FileStateManager`) | -0.40% (2 478 B -> 2 488 B, saved -10 B) | `SOURCE=PUBLIC_MCP_RUNTIME` | Wywołanie `representation='named'` vs `representation='indexed'` dla `FileStateManager` |
| Konsumenci `output_guard` | `get_analysis_status`, `lookup_index_entries` | `SOURCE=CONTEXTOR_MCP` | Contextor `get_module_context('contextor.mcp.output_guard')` |
| Konsumenci `representation` | `extract_indexed_report_context`, `get_artifact_blast_radius`, `get_artifacts_for_module` | `SOURCE=CONTEXTOR_MCP` | Contextor `get_module_context('contextor.mcp.representation')` |
| Próg bramki `output_guard` | 15 360 B (15 KiB) | `SOURCE=SOURCE_CODE + EXISTING_TEST` | Stała `LARGE_OUTPUT_WARNING_BYTES = 15360` w `output_guard.py` |
| Próg `representation auto` | 512 B | `SOURCE=SOURCE_CODE + EXISTING_TEST` | Stała `AUTO_NEGOTIATION_MIN_BYTES_SAVED = 512` w `representation.py` |
| Retencja zdarzeń LIVE | 100 zdarzeń | `SOURCE=SOURCE_CODE + EXISTING_TEST` | `CanonicalLiveServer._events` obcinane przez `del self._events[:-100]` w `ipc.py` |
| Ciągłość zdarzeń LIVE | Jawna detekcja luki ciągłości | `SOURCE=PUBLIC_MCP_RUNTIME + EXISTING_TEST` | Pola `continuity`, `resync_required`, `resync_reason` w odpowiedzi `get_live_events` |
| Zgodność dokumentacji | 21/21 plików zgodnych | `SOURCE=PUBLIC_DOCS + EXISTING_TEST` | Testy `tests/test_mcp_documentation.py` (8/8 PASS) oraz weryfikacja plików JSON |

---

## UNRESOLVED_TOOLS
**NONE (0)**

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

## OVERALL_VERDICT
`PASS`

---

TOKEN EFFICIENCY INITIATIVE CLOSED — final consolidation evidence is internally consistent, fully provenance-traceable, and contains no inferred metrics or stale contract claims.
