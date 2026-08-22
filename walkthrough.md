# TOKEN EFFICIENCY — STEP A20.1: MEASURE AND CLASSIFY update_file

## FILES_CHANGED=NONE
Krok pomiarowy i klasyfikacyjny typu read-only. Nie zmodyfikowano żadnych plików produkcyjnych, dokumentacji ani testów.

---

## PUBLIC_SIGNATURE
`def update_file(repo_path: str, file_path: str, max_items: int | None = 30, compact: bool = True, fields: list[str] | None = None) -> str:`

---

## AUTHORITATIVE_IMPLEMENTATION
`C:\Temp\Contextor_Repo\contextor\mcp\tools\update_file.py`

---

## AUTHORITATIVE_LIVE_OWNER
- `contextor.mcp.runtime` (`get_or_init_engine`)
- `contextor.core.live_state` (`connect(root).update_file(...)`)
- `contextor.core.analysis.state_manager` (`save_engine_state`)

---

## PRECONDITIONS
Wymaga wcześniejszej inicjalizacji stanu silnika analizy (`analyze_project`). W przypadku braku aktywnej sesji narzędzie zwraca fail-fast obiekt `{"status": "NO_SESSION", ...}`.

---

## DESKTOP_WATCHER_WORKFLOW
Dokumentacja publiczna (`contextor/mcp/docs/update_file.json`) jasno rozróżnia dwa niezależne workflow:
1. **Desktop App / Watcher aktywny**: Desktop watcher automatycznie aktualizuje stan kanoniczny po edycji pliku. Agent **nie powinien** wywoływać `update_file`, lecz odczytywać zdarzenia przez `get_live_events`.
2. **Brak aktywnego watchera**: Agent wywołuje `update_file` synchronicznie po edycji pliku w celu natychmiastowej inkrementalnej aktualizacji grafu i silnika analizy.

---

## OUTPUT_SHAPE
Struktura odpowiedzi JSON:
- **Status i ścieżka**: `status`, `file_path`
- **Świeżość podsystemów grafu**: `graph_state`, `dependencies_state`, `blast_radius_state`, `local_metrics_state`, `global_metrics_state`, `artifact_consumption_state`
- **Wpływ na moduły**: `affected_modules` (`total`, `truncated`, `items` [gdy `compact=False`])
- **Trwałość stanu**: `live_state_persisted`
- **Różnica semantyczna**: `semantic_diff` (`changed_symbol_count`, `body_change_count`, `body_only_changes_tracked`, `symbols_added`, `symbols_removed`, `signatures_changed`, `bodies_changed`, `affected_symbols`)
- **Ostrzeżenie restartu procesu**: `runtime_restart_required`, `runtime_state`, `runtime_warning` (opcjonalne, gdy edytowano plik serwera MCP)
- **Delta modułu**: `delta` (`module_path`, `is_new`, `is_deleted`, `imports_added`, `imports_removed`, `artifacts_added`, `artifacts_removed`) (opcjonalne)

---

## FAIL_FAST_MEASUREMENT
Stan braku sesji (`status="NO_SESSION"`):
- **Rozmiar**: **153 bajty** UTF-8
- **Tryb**: `RUNTIME`

---

## MODIFY_MEASUREMENT
Typowa modyfikacja pliku źródłowego:
- **Domyślny tryb kompaktowy (`compact=True`)**: **934 bajty** UTF-8 (~0.91 KiB)
- **Tryb szczegółowy (`compact=False, max_items=30`)**: **1,431 bajtów** UTF-8 (~1.40 KiB)
- **Tryb**: `SOURCE_SIMULATION`

---

## ADD_MEASUREMENT
Dodanie nowego pliku (`status="CREATED"`, `compact=True`):
- **Rozmiar**: **1,243 bajty** UTF-8 (~1.21 KiB)
- **Tryb**: `SOURCE_SIMULATION`

---

## DELETE_MEASUREMENT
Usunięcie pliku (`status="DELETED"`, `compact=True`):
- **Rozmiar**: **1,222 bajty** UTF-8 (~1.19 KiB)
- **Tryb**: `SOURCE_SIMULATION`

---

## LARGEST_AVAILABLE_MEASUREMENT
Ekstremalny przypadek testowy (50 zmodyfikowanych sygnatur, 50 dodanych symboli, 50 dotkniętych modułów, ostrzeżenie restartu MCP, `compact=False, max_items=None`):
- **Rozmiar**: **13,316 bajtów** UTF-8 (~13.00 KiB <= 15 KiB)
- **Tryb**: `SOURCE_SIMULATION`

---

## MEASUREMENT_MODES
- `FAIL_FAST`: `RUNTIME` (rzeczywiste wywołanie na niezinicjalizowanym repozytorium).
- `MODIFY / ADD / DELETE / LARGEST`: `SOURCE_SIMULATION` (wierna symulacja generatora odpowiedzi `_semantic_artifact_diff`, `_semantic_diff_view` i `bounded_items` bez niepotrzebnej modyfikacji stanu produkcyjnego).

---

## NESTED_COLLECTIONS_AND_BOUNDS
Wszystkie kolekcje zagnieżdżone w odpowiedzi posiadają wbudowane mechanizmy ograniczające:
1. `affected_modules`: `bounded_items(..., max_items)` (`total`, `truncated`, `items` tylko gdy `compact=False`).
2. `semantic_diff.symbols_added`: `bounded_items(..., max_items)`.
3. `semantic_diff.symbols_removed`: `bounded_items(..., max_items)`.
4. `semantic_diff.signatures_changed`: `bounded_items(..., max_items)`.
5. `semantic_diff.bodies_changed`: `bounded_items(..., max_items)`.
6. `semantic_diff.affected_symbols`: `bounded_items(..., max_items)`.

---

## CARDINALITY_GROWTH_ANALYSIS
- **Symbole zmienionego pliku**: `BOUNDED` (omijane przy domyślnym `compact=True`, limitowane przez `max_items=30`).
- **Importy dodane/usunięte**: `BOUNDED` (lokalne dla pojedynczego pliku).
- **Dotknięte moduły**: `BOUNDED` (limitowane przez `max_items=30`).
- **Konsumenci artefaktów**: `NO` (nie są listowani na poziomie encji).
- **Diagnostyka składniowa**: `NO` (obsługiwana w strumieniu `get_live_events`).
- **Rozmiar repozytorium**: `NO`.
- **Historia zdarzeń LIVE**: `NO`.

---

## AGENT_SCOPE_CONTROLS
Narzędzie posiada wbudowane 3 mechanizmy kontroli zakresu po stronie wywołującego:
1. `compact: bool = True` (domyślnie pomija tablice elementów i zwraca wyłącznie agregaty liczbowe).
2. `max_items: int | None = 30` (jawny limit elementów per kolekcja przy `compact=False`).
3. `fields: list[str] | None = None` (projekcja wybranych kluczy najwyższego poziomu).

---

## PAYLOAD_GROWTH_DRIVER
Odpowiedź jest ściśle ograniczona zakresem pojedynczego pliku. Domyślny ładunek wynosi poniżej 1 KiB (~934 B). Nawet przy `compact=False` i `max_items=30` rozmiar wynosi ok. 1.4–3.0 KB.

---

## OUTPUT_GUARD_CANDIDATE
`NO`
Domyślna odpowiedź (`compact=True`) jest ultra-kompaktowa (< 1 KiB). Parametry `compact`, `max_items` i `fields` w pełni kontrolują rozmiar odpowiedzi bez konieczności narzucania zewnętrznej bramki preflight.

---

## PROGRESSIVE_DISCLOSURE_CANDIDATE
`NO`
Narzędzie fabrycznie implementuje progressive disclosure poprzez rozróżnienie `compact=True` (podsumowanie i metryki) oraz `compact=False` (szczegółowe wpisy różnic).

---

## REPRESENTATION_CANDIDATE
`NO`
Narzędzie zwraca lokalną deltę architektoniczną pojedynczego pliku, w której alternatywne reprezentacje indeksowane nie mają zastosowania.

---

## MEASURED_OPTIMIZATION_OPPORTUNITY
Brak przestrzeni optymalizacyjnej. Domyślna odpowiedź wynosi ok. 0.9–1.2 KB, a tryb rozszerzony ok. 1.4 KB.

---

## NON_TOKEN_CONTRACT_RISKS
`NONE`
Logika detekcji modyfikacji kodu serwera MCP (`runtime_restart_required`) oraz precyzyjne rozróżnienie workflow z watcherem i bez watchera działają w pełni poprawnie.

---

## FINAL_CLASSIFICATION
`A` (NO CHANGE)

---

## JUSTIFICATION
1. Domyślna odpowiedź w trybie `compact=True` generuje lekki ładunek poniżej 1 KiB (~934 B).
2. Wszystkie 6 kolekcji zagnieżdżonych jest fabrycznie ograniczonych przez `bounded_items` i `max_items`.
3. Wywołujący ma pełną kontrolę nad zakresem odpowiedzi za pomocą parametrów `compact`, `max_items` oraz `fields`.
4. Żadna refaktoryzacja tokenowa nie jest uzasadniona.

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
STEP A20 CLOSED — update_file is sufficiently token-efficient; no implementation justified.
