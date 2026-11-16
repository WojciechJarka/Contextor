# SP-R4 — walidacja kompilacji i granicy type_only

## PREFLIGHT

Contextor MCP `get_project_architecture(fields=[])`: LIVE dotyczy `C:/Temp/Spiral-Prophet_Repo`, revision 8, activity_epoch `7a9d2291ba26492e9732e8aa93544fd3`, module_count 1065, resync_required=false. repo_id `ctx_2611e91a` pochodzi z wcześniejszego preflightu; bieżące użyte projekcje nie udostępniły repo_id, zatem ponowne potwierdzenie jest NIEUSTALONE. Aggregate canonical_state=stale, workspace_sync=unverified; rodziny: module=stale, graph=fresh, topology=fresh, artifact_consumption=fresh, cycles=fresh, cycle_semantics=stale, collisions=fresh, lineage=stale. syntax_errors=6, availability=fresh. `get_live_events(after_revision=7)` zwróciło jedynie revision 8: desktop_watcher, `agents/app.py:66`, SYNTAX_ERROR.

Ukończony raport `summary` (2026-11-16T08:37:07, historyczny względem overlay LIVE) wymienia skipped_files: `agents/app.py:66`; `data_preprocessing/core/contracts/contracts_manifest_contract.py:23776`; `data_preprocessing/core/contracts/registry/registry_aggregate_snapshot_contract.py:71`; `data_preprocessing/core/contracts/registry/registry_manifest_contract.py:98`; `data_preprocessing/core/fingerprint/fingerprint_sha256.py:36`; `data_preprocessing/core/performance/date_perf.py:250`. Liczba zgadza się z bieżącym LIVE, lecz bieżąca pełna lista skipped_files nie jest wystawiana przez użyte projekcje, więc jej identyczność pozostaje NIEUSTALONA. Badany plik nie jest na liście raportu.

Odczyt Git: Spiral Prophet HEAD `694ffbe211aa6132dcfd6ea3504e334ea59dc41f`; wcześniejsze zmiany w `core/contracts/event/__init__.py`, usunięcie `event_core_manifest_contract.py` i trzy nieśledzone pliki manifestów pozostawiono. Contextor HEAD `7641d85ab66dfdbc546a8f230fa5cf602a0546f3`. `audyt.txt` nie edytowano.

## DOWODY CPYTHON I MCP

DIRECT_EVIDENCE — `C:/Temp/Spiral-Prophet_Repo/core/validators/event/event_actor_validator.py`: 986 bajtów, SHA-256 `40d91e6feeeecc792c08af3b7eb7436c20cd45d7a043312385cf7d940aa6ef60`. Linia 1: `from core.errors.contracts.event.event_contract_errors import EventActorContractError`; linia 5: `from __future__ import annotations`. CPython 3.15.2 na tych samych bajtach: `ast.parse(source, filename)` — OK; `compile(source, path, "exec")` — `SyntaxError: from __future__ imports must occur at the beginning of the file`, linia 5. Kod nie został wykonany.

MCP `query_canonical_projection(root=modules, module_name eq core.validators.event.event_actor_validator)`: jeden rekord modułu, path `core/validators/event/event_actor_validator.py`, sześć ImportRef, w tym `__future__(annotations)`. `get_module_context` zwróciło revision 8, canonical_state=fresh, workspace_sync=verified dla pliku. Według kontraktu oznacza to zgodność dysku z kanonicznym snapshotem SHA-256; projekcja nie ujawniła osobnego kanonicznego hasha. `get_file_edit_context` zwróciło `syntax_diagnostics={status:checked_and_none,availability:fresh,materialized:true,errors:[],total:0}`.

## ŚCIEŻKA WYKONANIA CONTEXTORA

CODE_PATH_PROVED — `C:/Temp/Contextor_Repo/contextor/core/source.py:85-108`: `parse_source_snapshot` dekoduje bajty i wywołuje `ast.parse`; brak `compile`. `contextor/core/symbol_engine/indexer.py:1096-1133`: `_process_single_file` przyjmuje AST lub zwraca błąd `SourceError`. `indexer.py:2751-2767,2903-2920`: wynik z `error` trafia do `skipped`, pozostały staje się `Module`. `contextor/core/analysis/state_manager.py:210-249`: `build_syntax_diagnostics_from_index` wpisuje indeksowane moduły jako `checked_and_none`; błędy pochodzą ze `skipped`; bez ponownej kompilacji. `contextor_fact_lineage(family=syntax_diagnostics)` potwierdza index parse results → builder → stan kanoniczny → `get_file_edit_context`, a także osobną gałąź incremental `_commit_syntax_candidate`. Narzędzie projekcyjne nie parsuje źródła przy odczycie.

Werdykt hipotezy kompilacji: POTWIERDZONE — ten plik jest zaakceptowany w modelu AST i ma pustą diagnostykę LIVE, choć CPython compile odrzuca go na linii 5. To jest granica aktualnego kontraktu AST, nie dowód, że samo użycie AST jest przypadkową usterką. Globalne twierdzenie o kompilowalności wszystkich modułów pozostaje NIEUSTALONE.

## TYPE_CHECKING — PONOWNA OCENA SP-R2

DIRECT_EVIDENCE — `C:/Temp/Spiral-Prophet_Repo/agents/data_processing_states.py:21`: `from typing import Any, Dict, TYPE_CHECKING, Union`; linie 29-31: `if TYPE_CHECKING: from .data_agent import DataAgent; from .processing_context import ProcessingContext`. MCP `query_canonical_projection`: `ImportRef(module=data_agent,level=1,names=[DataAgent],is_from_import=true,type_only=false)`. `get_module_context`, revision 8, workspace_sync=verified: `agents.data_processing_states → agents.data_agent` jako `hard_dependency`. `get_live_events` pokazuje dwumodułowy cykl strukturalny.

A. Źródłowy AST zawiera strażnika, ale `recognize_typing_guard` w `contextor/core/cycle_semantics/typing_guard.py:46-66` wymaga pojedynczej nazwy w markerze `from typing import TYPE_CHECKING`. Tutaj są cztery nazwy. Funkcja nie rozpoznaje więc tego strażnika. Sam zapis `if TYPE_CHECKING` nie spełnia jej kontraktu.

B. `type_only_candidate_statement_ids` (`typing_guard.py:401-485`) zwraca pusty zbiór bez rozpoznanego markera. Ponadto wybiera tylko `ast.Import`, nigdy `ast.ImportFrom`. `AdvancedImportVisitor.visit_Import` (`indexer.py:264-293`) może oznaczyć wybrane importy type_only; `visit_ImportFrom` (`:296-315`) nie przekazuje tego pola. Badany ImportRef jest false już przy tworzeniu. Zachowany literalnie wcześniejszy wpis w issues.md mówi o rozpoznanym strażniku; dla tego konkretnego pliku aktualny kod tego nie potwierdza.

C. `_finalize_type_only_imports` (`indexer.py:2618-2736`) może cofnąć wyłącznie istniejące true; badanego false nie zmienia. `project_marker_safe` (`:2623-2649`) i `project_effects_closed` (`:2650-2681`) wymagają `not skipped`. Raport wykazuje sześć pominiętych plików, więc hipotetyczne true w takim przebiegu zostałoby cofnięte. Pozostałe warunki: brak shadowing `typing`, pasywność inicjalizatorów rodziców, zgodność fingerprintów markerów i efektów, brak nieindeksowanych źródeł/artefaktów oraz zamknięcie importów; ich wszystkich wartości dla aktualnego przebiegu nie ustalono.

D. `contextor/core/graph/graph.py:52-66,185-230`: `_is_type_only_import` odczytuje flagę; false z rozstrzygnięciem MODULE daje hard edge. Wynik hard potwierdza MCP. Konkretny wewnętrzny wynik `resolve_internal` jest wnioskowany z tej ścieżki, nie zaobserwowany osobno.

E. Hard oznacza klasyfikację grafu strukturalnego. Przy standardowym `typing.TYPE_CHECKING=False` import w ciele `if` nie wykonuje się; hard nie dowodzi runtime dependency ani błędu wykonania. Werdykt: POTWIERDZONE są false i hard; FAŁSZYWE jako wyjaśnienie tego konkretnego przypadku jest twierdzenie, że true zostało dopiero cofnięte przez finalizer. NIEUSTALONE pozostają inne warunki bezpieczeństwa oraz rzeczywisty przebieg runtime.

## FILES_CHANGED

- `C:/Temp/Contextor_Repo/issues.md`: jeden dosłowny wpis SP-R4; trzy wcześniejsze zachowane.
- `C:/Temp/Contextor_Repo/walkthrough.md`: bieżący raport.
- Produkcja i testy obu repozytoriów: NONE. Nie wykonano pytest, FULL, SCC02, restartu ani operacji Git zapisującej.

## FULL_DIFFS

Pełny rzeczywisty diff `issues.md` względem HEAD:

```diff
diff --git a/issues.md b/issues.md
index a12faa8..a904320 100644
--- a/issues.md
+++ b/issues.md
@@ -22,6 +22,22 @@ bezpieczne rozpoznawanie pochodzenia strażnika oraz
 konserwatywną granicę dla niepewnych przypadków.
 Nie zatwierdzono jeszcze implementacji.
 
+### Walidacja AST a kompilowalność CPython
+
+Audyt Spiral Prophet ujawnił moduł
+core.validators.event.event_actor_validator,
+który pozostaje w kanonicznym indeksie,
+mimo że CPython compile odrzuca jego źródło
+z powodu nieprawidłowego położenia instrukcji
+from __future__ import annotations.
+Dotychczasowa diagnostyka oparta na ast.parse
+nie wykrywa tego przypadku, a plik nie wystąpił
+wśród zgłoszonych skipped_files.
+Należy osobno zweryfikować kontrakt diagnostyki
+składni, zakres kontroli kompilowalności oraz
+spójność faktów FULL i LIVE.
+Nie zatwierdzono jeszcze implementacji.
+
 ### Wywołania metod przez pola instancji
 
 Audyt Spiral Prophet wykazał niepełne przypisywanie
```

ACTUAL_DIFF produkcji/testów: NONE. `walkthrough.md` jest niniejszym raportem; jego własny diff nie jest dublowany.
