# P10-R4-I1 — audyt przed implementacją

## PREFLIGHT

- DIRECT_EVIDENCE: Contextor MCP `get_project_architecture(repo_path="C:\\Temp\\Contextor_Repo", fields=[])`: LIVE revision **1510**, `canonical_state=fresh`, `resync_required=false`, `cycle_semantics=fresh`, globalne `workspace_sync=unverified`.
- DIRECT_EVIDENCE: `get_module_context(..., compact=true)` dla `package_model`, `execution.definition_checks`, `execution.steps`, `execution.state`: per-file `workspace_sync=verified` przy revision 1510.
- DIRECT_EVIDENCE: `get_symbol_lineage(..., symbol="contextor.core.cycle_semantics.package_model::evaluate_package_import_order", mode="preview")`: rozstrzygnięty `A6428/1`, `metadata_consistent=true`, `scope_state=available`; pełna odpowiedź wymagałaby ~1,62 MB. Dokładne gałęzie poniżej sprawdzono w źródle.
- Git HEAD `4c0a37f1e134314dffbe75eb61666ae087667393`. Zastane modyfikacje `audyt.txt`, `issues.md`, `walkthrough.md` występowały przed zadaniem. Anchory wskazane w promptcie I1 (`annotation_builtin_names`, `_restricted_dataclass_field_annotation`, `_DefinitionState`) pasują do bieżącego źródła; to nie jest SOURCE_DRIFT.

## NIEZALEŻNY AUDYT SEMANTYCZNY

- CODE_PATH_PROVED: obecny `_restricted_dataclass_field_annotation` w `execution/definition_checks.py:62–122` dopuszcza m.in. `ast.Subscript`, ograniczone `BitOr None` oraz dokładnie `ast.AST`. `package_model.py:421–425` stosuje ten warunek, a `:2592–2632` weryfikuje symboliczne wiązania przed założoną dekoracją. Zakres jest warunkowy (`package_model.py:1498–1505`), nie poświadcza runtime.
- DIRECT_EVIDENCE: eksperyment odczytowy poza repo `C:\Temp\p10_i1_preflight.py`, uruchomiony przez `.venv\Scripts\python.exe` z `PYTHONPATH=C:\Temp\Contextor_Repo`: trzy odrębne próbki `@dataclass(frozen=True) class C: x: list[int]`, `x: ast.AST` (z `import ast`) oraz `x: int | None` dały w aktualnym warunkowym modelu `MODEL_PASS`, `ASSUMED_FROZEN_DATACLASS_DECORATION`, `READY`, przy `evidence_scope=CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`. Każda miała flagi `_compile_on_first_import=True`, `_assume_passive_external_imports=True`, `_assume_frozen_dataclass_decoration=True` i `annotation_semantics="DEFERRED"`.
- CONTRACT_PROVED dla literalnie podanego algorytmu I1: w nowym `_annotation_value`, `list[int]` trafia do `ast.Subscript`; receiver `list` jest `_OpaqueValue(("assumed_builtin", "list"))`, podczas gdy gałąź Subscript przyjmuje tylko `_ConstructedSequence`. Zwraca `None`, zatem część G nakazuje `UNKNOWN` przed dekoracją. `int | None` trafia do `ast.BinOp`, ale gałąź akceptuje tylko Add/Sub/Mult na dwóch dokładnych int, więc także `UNKNOWN`. `ast.AST` trafia do `ast.Attribute`: importowane `ast` jest sentinelowym stringiem `\x00ASSUMED_EXTERNAL:ast` (`package_model.py:2040–2066`), a proponowana gałąź szuka receiver.origin jako klucza `module_namespaces`; nie jest nim logiczna nazwa indeksowanego modułu. Również zwraca `None`. Te trzy utraty dotychczasowych ścieżek wynikają bezpośrednio z proponowanego kodu, bez potrzeby wdrożenia.
- CODE_PATH_PROVED: istniejący model klasy nie ma pełnego namespace ciała klasy; class-local BIND emituje event bez zapisu do `namespaces[module]` (`package_model.py:3054–3063`), a class-local FROM nie zapisuje wiązania modułowego (`execution/imports.py:235–259`). Proponowany scope jest nową semantyką, która wymaga sprawdzenia jej relacji z istniejącymi krokami. W I1 `class_scope_id` trafia tylko do BIND z AnnAssign z wartością i do metody; szersze skutki dla istniejących dopuszczeń nie zostały udowodnione.
- INFERENCE podparta podaną implementacją: przy literalnym I1 trzy weryfikowane powyżej przypadki przechodzą z warunkowego `MODEL_PASS` do `UNKNOWN`. Sam `UNKNOWN` jest konserwatywny, ale propozycja usuwa już działające mechanizmy bez wykazania ich wadliwości i bez jawnego kontraktu dopuszczającego tę regresję. Nie należy zmieniać oczekiwań testów tylko po to, aby ją zaakceptować. To jest warunek przerwania z punktu 15 AGENTS.md.
- Dodatkowa granica: `if node.id in vars(builtins)` w podanym I1 czyta aktualne builtins procesu modelu. `package_model.py:1472–1475` mówi wprost, że evaluator nie poświadcza builtins ani import environment analizowanego procesu. Sam odczyt hostowego zbioru nazw nie dowodzi wiązania w docelowym CPython; bez doprecyzowania kontraktu nie wolno z tego robić autorytetu semantycznego. Nie twierdzę na tej podstawie, że konkretny import jest FALSE_PASS.

## WERDYKT I BLOKADA

**BLOCKED_SEMANTIC_INTEGRITY.** Nie wykonano literalnej implementacji I1. Punkt 15 aktualnego AGENTS.md wymaga przerwania, gdy instrukcja usuwa poprawne mechanizmy bez dowodu wadliwości albo nie ma wystarczających dowodów skutków zmiany. Tu takie skutki są konkretne: `list[int]` i `int | None` przy konwencjonalnych builtins oraz istniejąca warunkowa ścieżka `ast.AST` zostają odrzucone przez nowy algorytm. Nie projektowano poprawki ani listy wyjątków.

Minimalny brakujący dowód/rozstrzygnięcie przed implementacją: czy celowo wycofać każde z trzech obecnych warunkowych dopuszczeń na podstawie niezależnego kontraktu i porównań CPython, czy przedstawić poprawiony projekt zachowujący semantycznie uzasadnione przypadki. Potrzebne jest też określenie, dlaczego hostowe `vars(builtins)` może być traktowane jako fakt o analizowanym środowisku. Bez tego nie ma podstaw do modyfikacji production/tests.

## ACTIONS / TEST_RESULT / NEXT_STEP

- Wykonano odczyt MCP, źródeł i niewykonujący analizowanych modułów eksperyment aktualnego modelu poza repo. Nie uruchomiono pytest, FULL, restartu ani operacji Git zmieniających repo.
- Wynik: obecny warunkowy model przyjął trzy wskazane próbki. Proponowany evaluator został oceniony literalnie z kodu promptu; nie został uruchomiony ani wstawiony do repo. Nie przypisano mu wyniku testu runtime.
- Następny krok wymaga poprawionego, semantycznie uzasadnionego kontraktu lub dowodu świadomie dopuszczającego powyższe regresje. Zgodnie ze STOP czekam na „proceduj”.

## FILES_CHANGED

- `walkthrough.md` — wyłącznie raport. `audyt.txt` i `issues.md` pozostają zastanymi zmianami, nieedytowanymi w tym zadaniu.

## ACTUAL_DIFF=DIFFS=NONE

Nie zmieniono plików source/tests/docs poza raportem.

## FULL_DIFFS=NONE

Source/tests: brak zmian.
