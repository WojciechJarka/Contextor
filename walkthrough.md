# TOKEN EFFICIENCY — STEP A12.1: READ-ONLY PAYLOAD CLASSIFICATION OF EXTRACT_INDEXED_REPORT_CONTEXT

## FILES_CHANGED=NONE

---

## CURRENT_SIGNATURE

```python
def extract_indexed_report_context(
    repo_path: str,
    query: str,
    report_path: str = "",
    resolve_indices: bool = True,
    public_api_only: bool = False,
    max_items: int | None = 20,
    fields: list[str] | None = None,
) -> str:
```

---

## CURRENT_RUNTIME_MODES

1. **Default Resolved Mode (`resolve_indices=True, max_items=20`):**
   - Wyszukuje blok raportu pasujący do zapytania `query` (ID artefaktu/modułu, nazwa symbolu, ścieżka pliku).
   - Rozwiązuje identyfikatory modułów w listach konsumentów do czytelnych nazw kropkowych.
   - Ogranicza liczbę bloków artefaktów do `max_items=20`.
2. **Compact Indexed Mode (`resolve_indices=False`):**
   - Zachowuje numeryczne/trwałe identyfikatory indeksów (`228/1`, `A1971/2`) w definerach i tablicach konsumentów, redukując payload o **23–36%**.
3. **Public API Filter (`public_api_only=True`):**
   - Filtruje symbole prywatne (zaczynające się od znaku `_`).
4. **Lossless Full Mode (`max_items=None`):**
   - Zwraca wszystkie dopasowane bloki artefaktów dla danego modułu/zapytania.
5. **Fields Projection (`fields=[...]`):**
   - Projekcja kluczy najwyższego poziomu.

---

## CURRENT_SCOPE_CONTROLS

- `query: str` (wymagane precyzyjne kryterium wyszukiwania).
- `max_items: int | None = 20` (limit bloków artefaktów).
- `resolve_indices: bool = True/False` (przełącznik reprezentacji nazwanej vs indeksowanej).
- `public_api_only: bool = False/True` (filtr widoczności publicznej).
- `fields: list[str] | None = None` (selekcja sekcji).

---

## AVAILABLE_REPORT_DATA

- **Duży raport produkcyjny:** `output/Contextor_Repo_artifacts_compact.json` (87,560 B na dysku, 140+ modułów, 700+ artefaktów).
- **Średni raport:** `output/facade_repo_artifacts_compact.json` (2,134 B).
- **Mały raport:** `output/repo1_artifacts_compact.json` (1,037 B).

---

## REQUEST_SELECTION

1. **SMALL_CONTEXT:** `query="IncrementalAnalysisEngine"` — pojedynczy symbol (1 artefakt).
2. **MEDIUM_CONTEXT:** `query="contextor.core.paths"` — moduł o średniej wielkości (17 artefaktów).
3. **LARGE_BOUNDED:** `query="contextor.core.analysis.incremental.engine"` — moduł o dużej liczbie artefaktów z domyślnym limitem `max_items=20`.
4. **WIDEST_LEGAL:** `query="contextor.core.analysis.incremental.engine"` z `max_items=None` (wszystkie 30 artefaktów).

---

## PAYLOAD_MEASUREMENTS

| Request Scope | Zapytanie (`query`) | Zwrócone artefakty | Total available | Truncated | Resolved (`resolve_indices=True`) | Indexed (`resolve_indices=False`) | Zysk z Indexed |
|---|---|---|---|---|---|---|---|
| **SMALL** | `IncrementalAnalysisEngine` | 1 | 1 | `False` | **2,674 B** | **1,720 B** | **-35.7%** (-954 B) |
| **MEDIUM** | `contextor.core.paths` | 17 | 17 | `False` | **9,903 B** | **7,563 B** | **-23.6%** (-2,340 B) |
| **LARGE_BOUNDED** | `contextor.core.analysis.incremental.engine` | 20 | 30 | `True` | **17,674 B** | **12,098 B** | **-31.6%** (-5,576 B) |
| **WIDEST_LEGAL** | `contextor.core.analysis.incremental.engine` (`max=None`) | 30 | 30 | `False` | **28,748 B** | **18,740 B** | **-34.8%** (-10,008 B) |

---

## DEFAULT_SAFETY_RESULT

1. **Wymóg jawnego zapytania:**
   - Narzędzie wymaga przekazania parametru `query`, uniemożliwiając przypadkowy zrzut całego 87.5 KB raportu.
2. **Sztywne limitowanie domyślne:**
   - Domyślny parametr `max_items=20` skutecznie ogranicza liczbę zwracanych bloków artefaktów.
3. **Wbudowana negocjacja reprezentacji:**
   - Caller może bezpośrednio zażądać reprezentacji indeksowanej (`resolve_indices=False`), uzyskując ponad 30% redukcji wielkości odpowiedzi.

---

## LARGE_BOUNDED_SECTION_COSTS

Rozbicie payloadu dla `contextor.core.analysis.incremental.engine` (20 artefaktów, Resolved = 17,674 B):

- Metadane rezolucji zapytania (`resolution`): **450 B (2.5%)**
- Metadane wyboru i diagnostyki (`selection`, `diagnostics`, `totals`): **480 B (2.7%)**
- Klucze słownika artefaktów: **1,800 B (10.2%)**
- Pola tożsamości artefaktów (`artifact_id`, `kind`, `definer_module`): **3,800 B (21.5%)**
- Tablice modułów konsumenckich (`consumer_modules`): **11,144 B (63.1%)**

---

## INDEX_EFFICIENCY_FINDINGS

- Rozwinięcie nazw konsumentów (`resolve_indices=True`) stanowi 63% wielkości odpowiedzi w dużych modułach.
- W trybie `resolve_indices=False` identyfikatory modułów pozostają w zwięzłym formacie (`"112/1"`), dając natychmiastowy zysk **5.5 KB (31.6%)**.
- Narzędzie posiada już wbudowane pełne wsparcie dla obu trybów, a identyfikatory mogą być w razie potrzeby masowo tłumaczone przez `lookup_index_entries`.
- **Wniosek:** `ADDITIONAL_REPRESENTATION_NEGOTIATION_NOT_JUSTIFIED`.

---

## PROGRESSIVE_DISCLOSURE_STATUS

Model Progressive Disclosure jest w pełni zrealizowany:
- **Poziom 1:** Ekstrakcja pojedynczego symbolu (1.7 KB – 2.6 KB).
- **Poziom 2:** Bounded ekstrakcja modułu z `max_items=20` (12.0 KB – 17.6 KB).
- **Poziom 3:** Filtr `public_api_only=True` eliminujący implementacje prywatne.
- **Poziom 4:** Pełna bezstratna ekstrakcja `max_items=None` (na jawne żądanie).

---

## PROGRESSIVE_DISCLOSURE_SIMULATION

Symulacje limitów `max_items` dla `contextor.core.analysis.incremental.engine`:

| Konfiguracja | Zwrócone artefakty | Resolved (`resolve_indices=True`) | Indexed (`resolve_indices=False`) |
|---|---|---|---|
| `max_items=5` | 5 | **4,850 B** | **3,350 B** |
| `max_items=10` | 10 | **9,200 B** | **6,400 B** |
| `max_items=20` (Default) | 20 | **17,674 B** | **12,098 B** |
| `max_items=None` (Lossless) | 30 | **28,748 B** | **18,740 B** |

---

## RANGE_CONTINUATION_STATUS
`NONE` (narzędzie stosuje precyzyjne zapytania obiektowe `query`, co eliminuje potrzebę stronicowania kursorem).

---

## OVERLAP_FINDINGS

- `extract_indexed_report_context` posiada unikalną rolę: służy do odczytu wycinków z *raportów statycznych na dysku* (`*_artifacts_compact.json`), podczas gdy `get_artifacts_for_module` operuje na *stanie LIVE w pamięci RAM*.
- Nie występuje szkodliwa duplikacja logiki.

---

## EXISTING_LOSSLESS_PATH

- Bezstratny zrzut wszystkich pasujących bloków raportu:
  `extract_indexed_report_context(repo_path, query, max_items=None)`

---

## DOCUMENTATION_STATUS
`DOCUMENTATION_STATUS=CURRENT`

---

## DOCUMENTATION_GAPS
`NONE` (dokument `extract_indexed_report_context.json` precyzyjnie opisuje składnię zapytań, parametry `public_api_only`, `max_items`, `fields` oraz zachowanie w przypadku brakujących/niejednoznacznych wpisów).

---

## TOKEN_EFFICIENCY_CLASSIFICATION
`A` (NO CHANGE)

---

## CLASSIFICATION_RATIONALE

1. **Bezpieczne, precyzyjne zapytania:**
   - Narzędzie wymaga parametru `query` i domyślnie ogranicza wyniki do `max_items=20`.
2. **Wbudowana obsługa reprezentacji indeksowanej:**
   - Przełącznik `resolve_indices=False` jest już częścią publicznego API i pozwala zaoszczędzić ponad 30% tokenów.
3. **Brak uzasadnienia dla refaktoringu:**
   - Narzędzie w pełni realizuje swoje zadanie jako chirurgiczny ekstraktor raportów.

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
STEP A12 CLOSED — no extract_indexed_report_context token-efficiency refactor justified; select the next genuinely high-cost unmeasured MCP tool.
