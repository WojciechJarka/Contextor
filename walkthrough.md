# SP-R5 — kontrakt walidacji kompilacji i korekta issues

## PREFLIGHT

Contextor MCP FIRST: `get_project_architecture(fields=[])` wskazuje `C:/Temp/Spiral-Prophet_Repo`, LIVE revision 8, provenance=live, module_count=1065, resync_required=false, parse_stale_modules={}. Aggregate canonical_state=stale, workspace_sync=unverified; rodziny module=stale, graph=fresh, topology=fresh, artifact_consumption=fresh, cycles=fresh, cycle_semantics=stale, collisions=fresh, lineage=stale. syntax_errors=6, availability=fresh. Bieżący overlay nie wystawia repo_id; wcześniejszy odczyt `ctx_2611e91a` nie jest ponownym potwierdzeniem.

Odczyt Git: Spiral Prophet HEAD `694ffbe211aa6132dcfd6ea3504e334ea59dc41f`; przed audytem: M `core/contracts/event/__init__.py`, D `core/contracts/event/event_core_manifest_contract.py`, trzy nieśledzone pliki manifestów event/transport. Contextor HEAD `a141388f4bc4b2b4a5037fa91e218310cce5d924`; przed audytem czysty status. Nie przełączano LIVE. `contextor_fact_lineage(family=syntax_diagnostics)` zwróciło snapshot Contextora revision 1402 i potwierdzone ścieżki od indeksu i incremental do kanonicznej diagnostyki oraz projekcji `get_file_edit_context`; ta projekcja ma własną świeżość i nie dowodzi kompilowalności.

## PARSER / AST / COMPILE

DIRECT_EVIDENCE — CPython 3.15.2, trzy izolowane źródła pod tymczasowym `C:/Temp/sp_r5_*`, bajty UTF-8. `compile` wywołano z `dont_inherit=True`; żadnego obiektu kodu nie uruchomiono. Parser Contextora: `parse_source_snapshot(SourceSnapshot(raw, sha256(raw)), path)`.

| Przypadek | Źródło | ast.parse | compile(AST, ..., dont_inherit=True) | compile(source, ..., dont_inherit=True) | parse_source_snapshot |
|---|---|---|---|---|---|
| A | `from __future__ import annotations; x: list[int] = []` | OK | OK | OK | OK |
| B | `import os; from __future__ import annotations; x = 1` | OK | SyntaxError, future import poza początkiem, linia 2 | ten sam SyntaxError, linia 2 | OK |
| C | `return 1` na poziomie modułu | OK | SyntaxError: 'return' outside function, linia 1 | ten sam SyntaxError, linia 1 | OK |

Hash SHA-256 bajtów: A `8e08b431e65913c51d5dd1f6a9d410ecd16dcaf1dbaa4fd9dc45fc0e305cecee`; B `c737b106b3f6f83fae1d4c4a9395853cc3b705b01caa1e2811c33d42dfaaa110`; C `0805bfdc02e872ed322a4a4e440ae985f3a4335f4dd59f3d373dfaf2a68a4a3c`. `contextor/core/source.py:58-71` oblicza fingerprint SHA-256 surowych bajtów, `:74-108` dekoduje je i używa `ast.parse`; nie wywołuje `compile`. `parse_source_with_fingerprint` (`:111-118`) deleguje do tej samej funkcji.

## COLD INDEX

CODE_PATH_PROVED — `contextor/core/symbol_engine/indexer.py:881-949`: worker czyta jeden `SourceSnapshot` i pyta `CacheManager.get` z jego bajtami. Gdy nie ma kompletnego cache, `:1096-1133` wywołuje `parse_source_snapshot` na tym samym snapshotcie. `indexer.py:2751-2767,2903-2920`: wynik z `error` trafia do `skipped`, bez błędu do `modules`. Nie jest prawdą, że każdy odczyt `index_repository` bezwarunkowo parsuje; zimny odczyt z brakiem kompletnego cache tak.

DIRECT_EVIDENCE — w izolowanym jedno plikowym repo dla B, `CONTEXTOR_DISABLE_PROCESS_POOL=1`, świeży cache poza repo: pierwszy `index_repository` wywołał `parse_source_snapshot` dokładnie raz, zaakceptował moduł `B`, `skipped=[]`, fingerprint modułu `c737b106b3f6f83fae1d4c4a9395853cc3b705b01caa1e2811c33d42dfaaa110`. Cache zawierał `error=null`, importy, symbol/reference/collision/lineage facts, trzy pola typing-guard i `import_classification_semantics_version=10`. W syntetycznym źródle nie było zmian bajtów między odczytami.

## WARM CACHE

CODE_PATH_PROVED — `contextor/core/analysis/cache_manager.py:120-158` porównuje BLAKE2b-16 bajtów źródła i rozwiązaną ścieżkę z wrapperem cache. `indexer.py:951-982` sprawdza wersję klasyfikacji importów 10, kształt importów i trzy pola typing-guard; `:1002-1046` waliduje lineage oraz schematy symbol/reference/collision/test facts. Kompletny wpis zwraca wynik w `:1047-1094` przed parserem, z `source_parse_called=False`, `cache_hit=True` i `CACHE_SHA256_EQUIVALENT`.

Wersje sterujące ponowną ekstrakcją: `SYMBOL_FACTS_SCHEMA_VERSION=2`, `REFERENCE_FACTS_SCHEMA_VERSION=1`, `COLLISION_FACTS_SCHEMA_VERSION=1`, `TEST_FACTS_SCHEMA_VERSION=1`, `IMPORT_CLASSIFICATION_SEMANTICS_VERSION=10` (`indexer.py:74-81,117-181,951-1046`). Deserializacja lineage wymaga `LINEAGE_EXTRACTION_CACHE_SCHEMA_VERSION=1` oraz zgodnych `source_key` i SHA-256 (`analysis/lineage_extraction.py:79,283-304`); odrębny `LINEAGE_FACTS_SEMANTIC_VERSION="1"` jest w `domain/lineage_facts.py:17`. `ENGINE_CACHE_SCHEMA_VERSION="1.1"` (`analysis/state_manager.py:529`) dotyczy osobnej serializacji stanu silnika, nie wrappera per-file `CacheManager`.

DIRECT_EVIDENCE — drugi `index_repository` na identycznych bajtach B: `parse_source_snapshot` wywołany zero razy, moduł `B` nadal przyjęty, `skipped=[]`, ten sam SHA-256, cache obecny z `error=null` i wersją importów 10. Tym samym pełny cache omija nie tylko `compile`, lecz także `ast.parse`. Katalog tymczasowego repo i cache syntetycznego usunięto po próbie; oba repozytoria audytu pozostały nietknięte.

## INCREMENTAL / LIVE

CODE_PATH_PROVED — `contextor/core/analysis/incremental/preparation.py:147-184`: `prepare_source_update` używa `parse_source_with_fingerprint`, więc dalej `parse_source_snapshot`; `SourceError` wypełnia `error_status`, message, line i column. Aktualizacja istniejącego/nowego pliku przez incremental nie idzie przez warm cache `index_repository`. `analysis/incremental/engine.py:699-746`: wynik błędu SYNTAX_ERROR tworzy `checked_with_errors`; `:754-835`: poprawne AST tworzy `checked_and_none`. `_commit_syntax_candidate` (`:240-315`) aktualizuje rodzinę diagnostyk i świeżość modułu. Usunięcie pliku usuwa fakt diagnostyczny.

FULL: `analysis/state_manager.py:210-249` buduje `checked_and_none` dla indeksowanych modułów, `checked_with_errors` dla składniowych `skipped`, a dla pominięć innych niż składniowe odracza rodzinę. `contextor_fact_lineage` potwierdza wejście index parse results do buildera i niezależną gałąź incremental do stanu oraz projekcji. Wskazane ścieżki akceptacji omijające bezpośrednie wywołanie `parse_source_snapshot`: kompletny warm cache indeksatora; wrapper `parse_source_with_fingerprint` nie omija funkcji, tylko do niej deleguje. Nie dowodzono braku wszystkich innych ścieżek w całym kodzie Contextora.

## ISTNIEJĄCE KONTRAKTY TESTÓW

Odczytano wskazane przypadki; nie uruchamiano pytest i nie dopisywano testów.

- `tests/test_syntax_diagnostics_full_analysis.py:29-86,122-171`: FULL mapuje indeksowany plik do `checked_and_none`, parserowo pominięty do `checked_with_errors`, nieczytelny do deferred; rzeczywisty indeks/facade utrwala te fakty. `:204-262`: LIVE aktualizuje diagnostykę i revision dla valid→syntax error→recovered, dodania i usunięcia.
- `tests/test_no_double_parse.py:20-47`: przygotowanie incremental czyta jeden raw snapshot i wywołuje ast.parse raz. `:50-105`: MODIFY/ADD mają `reparse_modules=()`; `:108-134`: DELETE nie parsuje.
- `tests/test_index_fusion.py:131-169`: kompletny warm cache nie parsuje i nie wyciąga ponownie symboli. `:171-203`: zmiana bajtów wymusza parse i odświeżenie faktów, kolejny warm hit już nie parsuje. `:275-324`: stary symbol schema version odświeża symbole. Te testy nie sprawdzają `compile(AST)` ani `compile(source)` dla B/C.

## POTWIERDZONE FAKTY

POTWIERDZONE: AST parser dopuszcza B/C, oba tryby compile je odrzucają na wskazanych liniach; obecny parser Contextora przyjmuje oba. POTWIERDZONE: zimny indeks B wykonuje parser i przyjmuje moduł; kompletny cache po niezmienionych bajtach przyjmuje moduł bez parsera. POTWIERDZONE: FULL i incremental korzystają z tej samej podstawowej funkcji AST przez różne wejścia; SourceError propaguje do skipped lub diagnostyki incremental. POTWIERDZONE: wcześniejszy opis TYPE_CHECKING wymagał literalnej korekty, wykonanej w issues.md bez zmiany pozostałych sekcji.

## NIEUSTALONE

NIEUSTALONE: ogólna kompilowalność wszystkich modułów Spiral Prophet, pełna aktualna lista skipped_files niezależna od historycznego raportu, oraz brak jakichkolwiek innych prywatnych ścieżek akceptacji źródła w całym projekcie Contextor. Snapshot Contextora revision 1402 z lineage nie jest dowodem bieżącego załadowania kodu przez proces serwera. Izolowana próba używała aktualnego kodu repo przez lokalny Python 3.15.2.

## WERDYKT

Obecny kontrakt przyjęcia źródła w zbadanych ścieżkach to skuteczny `ast.parse` lub kompletny cache związany z niezmienionymi bajtami i zgodnymi faktami. Nie jest on kontraktem kompilowalności CPython. Przypadki B i C są konkretnymi kontrprzykładami; semantyka FULL i LIVE na tej granicy jest opisana przez źródło i istniejące testy, bez wykonywania pełnej analizy Spiral Prophet.

## FILES_CHANGED

- `C:/Temp/Contextor_Repo/issues.md` — wyłącznie literalna wymiana opisu sekcji TYPE_CHECKING.
- `C:/Temp/Contextor_Repo/walkthrough.md` — raport SP-R5.
- Pliki produkcyjne i testowe obu repozytoriów: NONE. `audyt.txt` i Spiral Prophet nie były edytowane. Nie wykonano FULL, SCC02, restartu, pytest ani zapisującej operacji Git.

## FULL_DIFFS

Pełny rzeczywisty diff `issues.md` względem HEAD:

```diff
diff --git a/issues.md b/issues.md
index a904320..2b03e30 100644
--- a/issues.md
+++ b/issues.md
@@ -10,17 +10,35 @@ jeszcze rozwiązania implementacyjnego.
 
 ### TYPE_CHECKING — ImportFrom i klasyfikacja zależności
 
-W audycie Spiral Prophet potwierdzono, że importy
-ast.ImportFrom umieszczone pod rozpoznanym strażnikiem
-TYPE_CHECKING mogą otrzymać type_only=false i utworzyć
-hard dependency. AdvancedImportVisitor.visit_ImportFrom
-nie przenosi obecnie informacji type_only, podczas gdy
-wybrane przypadki ast.Import są obsługiwane. Mechanizm
-może generować fałszywe strukturalne cykle wykonania
-w projekcji hard graph. Przyszła korekta musi zachować
-bezpieczne rozpoznawanie pochodzenia strażnika oraz
-konserwatywną granicę dla niepewnych przypadków.
-Nie zatwierdzono jeszcze implementacji.
+Audyt Spiral Prophet wykazał, że import DataAgent
+w agents/data_processing_states.py znajduje się
+pod if TYPE_CHECKING, jednak marker importujący
+TYPE_CHECKING wraz z trzema innymi nazwami
+nie spełnia ograniczonego kontraktu
+recognize_typing_guard.
+
+Dodatkowo type_only_candidate_statement_ids
+wybiera wybrane ast.Import, ale nie ast.ImportFrom,
+a AdvancedImportVisitor.visit_ImportFrom
+pozostawia type_only=false.
+
+W tym konkretnym przypadku flaga jest false
+już przy ekstrakcji. Nie została cofnięta
+z true przez _finalize_type_only_imports.
+
+Finalizacja ma także odrębną konserwatywną
+granicę: wymaga między innymi not skipped
+i może cofać istniejące type_only=true
+przy niekompletnym obrazie projektu.
+
+Krawędź hard jest faktem grafu strukturalnego,
+ale sama nie dowodzi wykonania importu
+podczas inicjalizacji modułu.
+
+Należy osobno rozstrzygnąć kontrakt
+rozpoznawania strażnika, zakres ImportFrom
+i warunki bezpieczeństwa całego projektu.
+Nie zatwierdzono implementacji.
 
 ### Walidacja AST a kompilowalność CPython
 
```

ACTUAL_DIFF produkcji/testów: NONE. `walkthrough.md` jest niniejszym raportem; jego własny diff nie jest dublowany.
