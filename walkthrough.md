# TOKEN EFFICIENCY — STEP A4.4: POST-RESTART RUNTIME CERTIFICATION & REAL PAYLOAD MEASUREMENT OF GET_ARTIFACTS_FOR_MODULE

## FILES_CHANGED=NONE

---

## POST_RESTART_RUNTIME_LOADED

1. **Unsupported representation probe:**
   - Wywołanie: `get_artifacts_for_module(..., representation="xml")`
   - Runtime error:
     ```json
     {
       "error": "Unsupported representation for get_artifacts_for_module",
       "representation": "xml",
       "allowed_representations": [
         "auto",
         "indexed",
         "named"
       ]
     }
     ```
2. **Early domain-only fields probe:**
   - Wywołanie: `get_artifacts_for_module(..., fields=["module"], representation="auto")`
   - Odpowiedź: `{"module": "contextor.__main__"}` (brak metadanych, brak artefaktów, brak expand).

---

## CANONICAL_STATE_STATUS

- `get_analysis_status`: Canonical LIVE state aktywny.
- `get_live_events`: `status="ok"`, `revision=1162`, `desktop_watcher` aktywny.

---

## DEFAULT_COMPACT_MEASUREMENTS

| Moduł | Total (T) | Returned | Truncated | Expand | Top Symbole (Salience Order) | Evidence Range | Response Bytes |
|---|---|---|---|---|---|---|---|
| **SMALL** (`contextor.__main__`) | 3 | 3 | False | Absent | `main` (1), `_hide_console` (0), `_run_gui` (0) | min 0, max 1 | **1,045 B** |
| **MEDIUM** (`contextor.core.repository_identity`) | 14 | 10 | True | Present | `read_repository_identity` (6), `registry_meta_path` (3), `require_repository_identity` (3), `ensure_repository_identity` (1), `registered_repository_identities` (1) | min 0, max 3 | **4,944 B** |
| **LARGE_PROD** (`contextor.core.analysis.incremental.engine`) | 33 | 10 | True | Present | `IncrementalAnalysisEngine` (29), `IncrementalUpdateResult` (7), `IncrementalAnalysisEngine._calculate_degree_deltas` (1), `affected_modules` (0) | min 0, max 3 | **4,439 B** |
| **LARGE_OBSERVED** (`tests.test_mcp_regressions`) | 78 | 10 | True | Present | `_live_engine_fixture` (0), `_patch_empty_registries` (0), `_write_process_record` (0) (alfabetycznie przy 0 fan-in) | min 0, max 0 | **4,653 B** |

---

## BASELINE_COMPARISON

| Moduł | Baseline PRE-A4 | Final A4 Runtime | Bytes Saved | % Saved | Like-for-Like |
|---|---|---|---|---|---|
| **SMALL** | 1,133 B | 1,045 B | +88 B | **7.8%** | LIKE_FOR_LIKE=YES (T=3) |
| **MEDIUM** | 5,027 B | 4,944 B | +83 B | **1.7%** | LIKE_FOR_LIKE=YES (T=14) |
| **LARGE_PROD** | 12,012 B | 4,439 B | +7,573 B | **63.0%** | LIKE_FOR_LIKE=YES (T=33) |
| **LARGE_OBSERVED** | 22,192 B | 4,653 B | +17,539 B | **79.0%** | STATE_CHANGED_NOT_STRICTLY_LIKE_FOR_LIKE (T=78 vs 77 baseline) |

---

## LARGE_PROD_COMPACT_CONTRACT

Na `contextor.core.analysis.incremental.engine`:
- **A. Compact Named (`compact=True, representation="named"`):** 4,439 B, czytelne nazwy modułów w `evidence`, deskryptor `expand` obecny.
- **B. Compact Auto (`compact=True, representation="auto"`):** 4,544 B, brak koperty decyzyjnej, `consumer_representation={"representation": "named", "requested_representation": "auto"}`.
- **C. Compact Indexed (`compact=True, representation="indexed"`):** 4,331 B, identyfikatory modułów w `evidence` (`["224/2", "20/1", "78/1"]`), klucze artefaktów i `full_name` niezmienione, metadane M2 obecne (`representation="indexed"`, `index_kind="module"`, `resolve_via="lookup_index_entries"`).
- **D. Compact Fields (`compact=True, limit=50, fields=["artifacts"], representation="named"`):** 4,214 B, top-level dokładnie `{"artifacts", "expand"}`.

---

## EXPAND_RUNTIME_CERTIFICATION

1. **Direct execution `**expand` z D:**
   - Wywołanie: `get_artifacts_for_module(..., compact=False, limit=50, evidence_limit=20, include_consumers=True, symbol_filter="", representation="named", fields=["artifacts"])`
   - Wynik: 13,889 B, top-level dokładnie `{"artifacts"}`, 33 artefakty w kolejności alfabetycznej, brak obcięcia prezentacji.
2. **Boundary Probe 1 (`compact=True, limit=5`):** `artifact_count=5`, `truncated=True`, `expand=ABSENT`.
3. **Boundary Probe 2 (`compact=False, limit=5`):** `artifact_count=5`, `truncated=True`, `expand=ABSENT`.
4. **Boundary Probe 3 (`compact=True, limit=None`):** `artifact_count=10`, `truncated=True`, `expand` obecny z `"limit": null`.

---

## MEDIUM_LOSSLESS_NAMED_VS_INDEXED

- `named_bytes`: 6,065 B
- `indexed_bytes`: 5,812 B
- `bytes_saved`: 253 B
- `percent_saved`: 4.2%
- Liczba wystąpień konsumentów w Named: 16
- Liczba unikalnych modułów konsumenckich: 12
- Metadane M2 w Indexed: obecne.

---

## LARGE_PROD_LOSSLESS_NAMED_VS_INDEXED

- `named_bytes`: 14,599 B
- `indexed_bytes`: 13,568 B
- `bytes_saved`: 1,031 B
- `percent_saved`: 7.1%
- Liczba wystąpień konsumentów w Named: 37
- Liczba unikalnych modułów konsumenckich: 29
- Metadane M2 w Indexed: obecne.
- Porównanie z symulacją projektową (15,688 B vs 13,984 B, est. 1,704 B / 10.9%):
  - Rzeczywisty runtime Named: 14,599 B (mniejszy niż symulacja dzięki zwięzłym sygnaturom)
  - Rzeczywista redukcja: 1,031 B (7.1%).

---

## MEDIUM_AUTO_RESULT

- Wywołanie: `compact=False, limit=None, evidence_limit=None, representation="auto"`
- Wynik: Bezpośrednia odpowiedź Named z `consumer_representation={"representation": "named", "requested_representation": "auto"}` (oszczędność 253 B < 512 B threshold).

---

## LARGE_PROD_AUTO_RESULT

- Wywołanie: `compact=False, limit=None, evidence_limit=None, representation="auto"`
- Wynik: `status="representation_decision_required"`
- Klucze koperty (dokładnie 11): `status`, `requested_representation`, `module`, `module_id`, `total_artifact_count`, `truncated`, `decision_scope_count`, `scope_truncated`, `evidence`, `sizes`, `options`.
- Brak: `artifact_count`, `artifacts`, `expand`.
- `evidence`: Salience-ranked (top 3):
  1. `IncrementalAnalysisEngine` (29)
  2. `IncrementalUpdateResult` (7)
  3. `IncrementalAnalysisEngine._calculate_degree_deltas` (1)
- `sizes`:
  - `named_bytes`: 14,599 B
  - `indexed_bytes`: 13,568 B
  - `bytes_saved`: 1,031 B
  - `percent_saved`: 7.1%
- `options`:
  - `named`: `{"representation": "named", "compact": false, "limit": null, "evidence_limit": null, "include_consumers": true, "symbol_filter": ""}`
  - `indexed`: `{"representation": "indexed", "compact": false, "limit": null, "evidence_limit": null, "include_consumers": true, "symbol_filter": ""}`
  - `bounded_named`: `{"representation": "named", "compact": false, "limit": 10, "evidence_limit": 5, "include_consumers": true, "symbol_filter": ""}`

---

## DECISION_UNION_RUNTIME_CERTIFICATION

- Wykonanie retry `**options["named"]`: dokładnie 14,599 B (zgodność co do bajtu z `sizes.named_bytes`).
- Wykonanie retry `**options["indexed"]`: dokładnie 13,568 B (zgodność co do bajtu z `sizes.indexed_bytes`).

---

## FIELDS_DECISION_RUNTIME_CERTIFICATION

- Wywołanie: `fields=["artifacts"], representation="auto"`
- Wynik decyzji:
  - Zachowano pełną 11-kluczową kopertę decyzyjną.
  - `sizes`: `named_bytes=14332`, `indexed_bytes=13301`, `bytes_saved=1031`, `percent_saved=7.2%`.
  - `options.named["fields"] == ["artifacts"]`
  - `options.indexed["fields"] == ["artifacts"]`
- Wykonanie retry `**options["named"]`: dokładnie 14,332 B, top-level wyłącznie `{"artifacts"}`.
- Wykonanie retry `**options["indexed"]`: dokładnie 13,301 B, top-level wyłącznie `{"artifacts", "consumer_representation"}`.

---

## ZERO_CONSUMER_RUNTIME_PROBE

Na module `tests.test_mcp_regressions` (wszystkie symbole mają 0 konsumentów):
- `compact=False, representation="indexed"`: brak błędu, brak metadanych `consumer_representation`.
- `compact=False, representation="auto"`: brak błędu, brak negocjacji/decyzji, brak metadanych `consumer_representation`.

---

## BATCH_RESOLVER_RESULT

Dla 29 unikalnych module IDs z LARGE_PROD:
- Wywołanie: `lookup_index_entries(repo_path, ids=[29 IDs])`
- `resolved_count / requested_count`: **29 / 29 (100%)**
- Wszystkie wpisy posiadają `status="active"`.
- Rozwiązanie całego zbioru konsumentów nastąpiło w jednym wywołaniu batchowym.

---

## A3_RUNTIME_SAFETY_CHECK

Na `IncrementalAnalysisEngine` w `get_artifact_blast_radius`:
- Named: 29 konsumentów, pełna ścieżka nazw.
- Indexed: 29 konsumentów, identyfikatory z metadanymi M2 (`resolve_via="lookup_index_entries"`).
- Auto: Poprawna koperta decyzyjna A3 (`named_bytes=1329`, `indexed_bytes=529`, `bytes_saved=800 / 60.2%`).

---

## REALIZED_TOKEN_EFFICIENCY_RESULT

- **Default compact reduction:**
  - `LARGE_PROD`: z 12,012 B do 4,439 B (**-63.0%** / -7.6 KB).
  - `LARGE_OBSERVED`: z 22,192 B do 4,653 B (**-79.0%** / -17.5 KB).
- **Lossless indexed compression:**
  - `LARGE_PROD`: z 14,599 B do 13,568 B (**-1,031 B**).
- Wszystkie mechanizmy (salience cap 10, C2 bounded evidence max 3, M2 metadata, bezstanowe auto negotiation, batch resolver) działają w runtime w 100% poprawnie.

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
STEP A4 CLOSED — select and measure the next genuinely high-cost MCP tool before deciding whether any refactor is justified.
