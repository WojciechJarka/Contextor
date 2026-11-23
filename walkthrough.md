# DEPENDENCY-MATRIX-R1 — audyt kompletności i wierności danych

Tryb: discovery only. Nie zmieniono kodu ani testów; nie uruchomiono pytest ani FULL. Lokalny HEAD: `a22dd19b157cc6fc981c83d1fd7b164c97d6ee5e`.

## A. DIRECT_EVIDENCE

- Contextor MCP `get_project_architecture(fields=[])`: LIVE revision 1554, `provenance=live`, `resync_required=false`; `graph`, `artifact_consumption` i `lineage` są `fresh`, `workspace_sync=unverified`. Odpowiedź nie podaje osobnego stanu `dependency_matrix`. Raport `graph_analytics` jest historycznym raportem FULL z 2026-11-21; ostatni odczytany status FULL wskazuje publikację w revision 1510. Nie utożsamiać raportu z LIVE 1554.
- `contextor/core/analysis/state_manager.py:630-638`: siedem dozwolonych kanałów kanonicznej konsumpcji. `:654-711` definiuje `artifact_consumption[target]` jako listę konsumentów i `channels[consumer]`; `:833-911` buduje tę strukturę z surowych faktów. Fakty bez konsumentów pozostają kanonicznymi celami z pustymi polami.
- `contextor/core/reporting_engine/graph_analytics.py:2190-2291`: projekcja bierze `state.artifacts` i `state.artifact_consumption`; zachowuje artefakt tylko przy zewnętrznym konsumencie. Odwraca `channels[consumer]` do `_usage_sidecar[artifact][channel] = [consumers]`.
- `graph_analytics.py:325-355`: `_usage_dependency_types` mapuje niepuste kanały na `call`, `import`, `inheritance`; nie filtruje ich według aktualnego konsumenta. `:450-469`: builder wylicza typy jeden raz dla artefaktu, następnie przypisuje cały zbiór każdemu jego zewnętrznemu konsumentowi. `weight` rośnie raz na relację konsument–artefakt.
- `graph_analytics.py:378-408,471-509`: `hard_edges` dodają typ `import`; import-only edge ma wagę zero. Builder nie przyjmuje `soft_edges`, lineage ani `symbol_calls`. Lokalne `consumer == definer` pomija.
- `state_manager.py:809-830`: warunek świeżości wejść wymaga braku `resync_required`, świeżej kompletnej konsumpcji i grafu z mapą `hard_edges`. `contextor/core/api/facade.py:1356-1367`: FULL oblicza macierz z kanonicznego stanu. `contextor/core/analysis/incremental/plan_executor.py:1703-1733`: incremental używa tej samej funkcji buildera na projekcji i `hard_edges`; przy niespełnionych warunkach oznacza stan `stale`.
- `graph_analytics.py:1323-1361,1640-1644,1932-1939,1995-2011`: raport filtruje relacje do zakresu, używa tego samego buildera, zapisuje kompaktową macierz. Publiczny `get_project_architecture` zwraca raport historyczny, nie aktualne `state.dependency_matrix`.
- `tests/test_graph_analytics_regressions.py:27-59` sprawdza fallback `import` i jawne `inheritance`. `tests/test_matrix_clusters_ram_parity.py:220-235` porównuje kanały per consumer i końcowe macierze FULL/projekcja, ale nie sprawdza, czy `dep_types` komórki są ograniczone do kanałów danego konsumenta. Testów nie uruchamiano.
- MCP `contextor_fact_lineage(artifact_consumption)` potwierdził właściciela stanu, producenta FULL, aktualizację incremental, snapshot oraz publiczne projekcje blast radius. Dokumentacja `query_canonical_projection` v1.1 wystawia konsumentów i twarde/miękkie zależności, ale nie pole kanonicznych `channels[consumer]`.

## B. MACIERZ POKRYCIA

| Rodzina | Źródło → transformacja | Macierz | Publiczne MCP |
|---|---|---|---|
| Potwierdzeni konsumenci artefaktów | Fakty ekstraktora → `state.artifacts` → `artifact_consumption` → projekcja | Zagregowani do `weight` pary modułów; brak tożsamości artefaktu w komórce | Konsumenci i blast radius dostępni osobno; kanoniczne query daje listę konsumentów |
| Kanały użycia | `channels[consumer]` → `_usage_sidecar` → trzy typy | Zagregowane; możliwe przypisanie kanału innego konsumenta | Surowe `channels[consumer]` nie są polem sprawdzonego publicznego query ani kontraktu blast radius |
| Twarde importy | `dependency_graph.hard_edges` → builder | Para modułów i `import`; import-only ma wagę 0, brak miejsca importu | Query zależności `hard` |
| Miękkie importy | `dependency_graph.soft_edges` | Nieuwzględnione; poza wejściami buildera | Query zależności `soft` |
| Lineage, `symbol_calls` | Odrębny stan kanoniczny | Nie są bezpośrednimi wejściami i nie zachowują swojej semantyki w macierzy | Osobne `get_symbol_lineage` i `get_symbol_call_context` |
| Reeksporty, aliasy, nierozstrzygnięte zależności | Rozwiązywanie przed konsumpcją | Tylko rozstrzygnięte relacje docierające do konsumpcji lub `hard_edges`; brak łańcucha i przyczyny braku rozwiązania | Pełnego pokrycia osobnymi MCP nie ustalono |
| Artefakty bez konsumentów zewnętrznych, relacje lokalne | Kanoniczna konsumpcja i projekcja | Brak komórki między modułami; świadomy filtr | Artefakty dostępne osobnymi zapytaniami |

## C. POTWIERDZONE NIEZGODNOŚCI

**CODE_PATH_PROVED:** Jeśli ten sam artefakt ma konsumenta A z `direct_calls` i B z `inheritance`, `_usage_dependency_types` zwraca oba typy dla artefaktu. `build_module_dependency_matrix` przypisuje oba A i B, mimo że stan kanoniczny rozróżnia ich kanały. To kontrprzykład wynikający z kodu, nie zaobserwowana jeszcze komórka LIVE. `hard_edges` może niezależnie dodać `import` konkretnej parze.

**UNKNOWN LIVE WITNESS:** sprawdzone publiczne projekcje nie udostępniają `artifact_consumption[target]["channels"]`, więc nie potwierdzono rzeczywistego świadka w faktach LIVE 1554. Nie kwalifikuję konkretnej komórki LIVE jako błędnej.

## D. ŚWIADOME OGRANICZENIA KONTRAKTU

Macierz zawiera `consumer → definer`, `weight` i zbiór trzech typów. Pomija nazwy artefaktów, miejsca i liczbę użyć, siedem oryginalnych kanałów, relacje lokalne i szczegóły importu. Import-only edges są jawnie uwzględnione. Brak `soft_edges`, lineage i `symbol_calls` nie jest sam w sobie defektem kontraktu: nie są bezpośrednimi wejściami buildera. Raport warstwowy filtruje relacje do zakresu; raport globalny może być starszy od LIVE.

## E. UNKNOWN

Nie potwierdzono osobnej świeżości zmaterializowanej `dependency_matrix` w LIVE 1554, jej równości z bieżącymi wejściami ani kompletności publicznego udostępnienia wszystkich nierozstrzygniętych faktów. `workspace_sync=unverified` ogranicza wnioskowanie o zgodności źródeł na dysku ze stanem LIVE. Nie uruchamiano testów.

## WERDYKT

1. **Czy macierz wiernie realizuje kontrakt?** Nie w pełni: realizuje format i agregację modułową, ale typy zależności mogą pochodzić z użycia innego konsumenta tego samego artefaktu. Dowód dotyczy ścieżki kodu; rzeczywistego świadka LIVE nie potwierdzono.
2. **Czy wykorzystuje wszystkie fakty przeznaczone do budowy?** Tak dla zadeklarowanych wejść buildera: konsumpcji artefaktów i `hard_edges`. Kanały są wykorzystane niewiernie względem konsumenta.
3. **Czy istnieją fakty silnika niedostępne przez macierz lub inne publiczne MCP?** Surowe `channels[consumer]` są w stanie kanonicznym, ale nie w macierzy ani w sprawdzonym schemacie publicznych zapytań. `soft_edges`, lineage i `symbol_calls` mają osobne odczyty. Negatywnej tezy o każdym istniejącym publicznym narzędziu nie dowiedziono.

## FILES_CHANGED

NONE — nie zmieniono source, tests ani docs. Zmieniono wyłącznie `walkthrough.md` jako raport, na żądanie użytkownika.

ACTUAL_DIFF=DIFFS=NONE
