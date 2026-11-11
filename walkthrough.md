# P5-M08-I8-I2 — BLOCKED_SEMANTIC_INTEGRITY

## PREFLIGHT

Zaakceptowany w poprzednim etapie. HEAD `6a12ab6f276a1e0ebd417a6f69e353c66399cca6`; aktywny CPython 3.15.2; przed próbą implementacji drzewo czyste poza `walkthrough.md`; canonical LIVE revision 1337, source sync `verified`, cycle semantics `stale`.

## BLOCKING_CONDITION

Specyfikacja przypadków G, H i I zawiera sprzeczne wymagania. Każe utworzyć moduły `pkg.a`, `pkg.b`, `pkg.c`, a zarazem definiuje w `pkg.__init__` funkcje `a`, `b`, `c` oraz wymaga `MODEL_PASS` dla G/H. Oba istniejące guardy kolizji nazw potomnych modułów w `contextor/core/cycle_semantics/package_model.py` (oryginalnie linie 1573–1584 i 1674–1685) zwracają `UNKNOWN`, gdy definicja funkcji ma nazwę identyczną z bezpośrednim dzieckiem pakietu. Punkt 7 specyfikacji nakazuje dodać do tych guardów `DEFINE_STACKED_FUNCTION` i zachować pozostałe warunki. Spełnienie tego punktu gwarantuje `UNKNOWN` dla G/H/I przed aplikacją dekoratorów. Wymagane jednocześnie `MODEL_PASS` i sekwencje `CALL_FUNCTION`/`START_IMPORT` są więc niemożliwe.

DIRECT_EVIDENCE: source guard opiera się na zbiorze dzieci wyprowadzonym z `programs`; test ma tworzyć syntetyczne `pkg.a`, `pkg.b`, `pkg.c`. `DEFINE_FUNCTION` dla `a`, `b`, `c` jest już w guardzie. Powód ograniczenia jest opisany w komentarzu źródła: definicja funkcji i bezpośrednie dziecko o tej samej nazwie wymagają bogatszej semantyki shadowing/import-binding. Nowe zachowanie dekoratorów tego konfliktu nie rozwiązuje.

CODE_PATH_PROVED: guard przed wykonaniem modułu występuje przy `not _compile_on_first_import`; drugi guard występuje przy kompilacji programu na pierwszym imporcie. Oba są przed `DEFINE_STACKED_FUNCTION` execution. Brak uzasadnienia do usunięcia/obejścia tego guardu w zadanym scope.

CONTRACT_PROVED: wymaganie zachowania obu guardów i oczekiwanie `MODEL_PASS` dla G/H nie mogą współistnieć przy zadanych nazwach. To jest konflikt specyfikacji, nie regresja implementacji.

INFERENCE: CPython może wykonać podane przykłady dzięki wcześniejszemu uchwyceniu obiektów dekoratorów i późniejszemu nadpisywaniu atrybutów pakietu przez import. Nie przedstawiam tego jako wykonanego porównania CPython; w tym etapie nie uruchomiono referencji.

UNKNOWN: zachowanie po ewentualnej zmianie fixture na nazwy dekoratorów różne od nazw modułów dzieci oraz pełne wyniki targeted tests. Nie wykonano tych testów po wykryciu blokady.

## ACTIONS

Rozpoczęto literalną implementację w czterech plikach produkcyjnych. Po wykryciu sprzeczności cofnięto wszystkie te lokalne zmiany narzędziem `apply_patch`. Nie zmieniono production/tests/docs; zachowano jedynie ten raport. Nie wykonano FULL, SCC02, update_file, restartu ani operacji Git zmieniających indeks/historię.

## TEST/RESULT

Targeted pytest: NOT RUN — STOP zgodnie z failure contract. `git diff --check`: PASS dla bieżącego drzewa; ostrzeżenia Git dotyczą jedynie konwersji LF/CRLF. Brak traceback i event sequence, ponieważ testy/ewaluacja nie zostały uruchomione.

## FILES_CHANGED

NONE (source/test/docs). `walkthrough.md` jest jedyną zmianą w drzewie.

## ACTUAL_DIFF/FULL_DIFF

DIFFS=NONE

## NEXT STEP

Potrzebna poprawiona specyfikacja przypadków G/H/I, np. rozdzielenie nazw funkcji dekoratorów od nazw bezpośrednich modułów potomnych, albo osobna analiza semantyki kolizji i autoryzowany zakres jej modelowania. Nie zmieniać oczekiwań na `MODEL_PASS` bez uzasadnienia kontraktu.

## FINAL_VERDICT

BLOCKED_SEMANTIC_INTEGRITY. FINAL PASS niedopuszczalny.
