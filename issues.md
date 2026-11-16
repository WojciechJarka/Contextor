### Legacy summary — diagnozowanie cykli strukturalnych
Generator podsumowania przypisuje wykrytemu cyklowi
strukturalnemu poziom CRITICAL i zalecenie jego
eliminacji bez dowodu zagrożenia wykonania.
Dodatkowo len(worst) uwzględnia powtórzony moduł
zamykający ścieżkę, zawyżając liczbę unikalnych
modułów. Oba zachowania wymagają osobnej oceny
i korekty kontraktu raportowania. Nie przesądzono
jeszcze rozwiązania implementacyjnego.

### TYPE_CHECKING — ImportFrom i klasyfikacja zależności

W audycie Spiral Prophet potwierdzono, że importy
ast.ImportFrom umieszczone pod rozpoznanym strażnikiem
TYPE_CHECKING mogą otrzymać type_only=false i utworzyć
hard dependency. AdvancedImportVisitor.visit_ImportFrom
nie przenosi obecnie informacji type_only, podczas gdy
wybrane przypadki ast.Import są obsługiwane. Mechanizm
może generować fałszywe strukturalne cykle wykonania
w projekcji hard graph. Przyszła korekta musi zachować
bezpieczne rozpoznawanie pochodzenia strażnika oraz
konserwatywną granicę dla niepewnych przypadków.
Nie zatwierdzono jeszcze implementacji.

### Walidacja AST a kompilowalność CPython

Audyt Spiral Prophet ujawnił moduł
core.validators.event.event_actor_validator,
który pozostaje w kanonicznym indeksie,
mimo że CPython compile odrzuca jego źródło
z powodu nieprawidłowego położenia instrukcji
from __future__ import annotations.
Dotychczasowa diagnostyka oparta na ast.parse
nie wykrywa tego przypadku, a plik nie wystąpił
wśród zgłoszonych skipped_files.
Należy osobno zweryfikować kontrakt diagnostyki
składni, zakres kontroli kompilowalności oraz
spójność faktów FULL i LIVE.
Nie zatwierdzono jeszcze implementacji.

### Wywołania metod przez pola instancji

Audyt Spiral Prophet wykazał niepełne przypisywanie
wywołań metod przez pola instancji, w tym delegowanie
DualPipeline do SystemOrchestrator oraz wywołania
GUI przez self.pipeline. Część rzeczywistych wywołań
nie występuje w artifact consumers i symbol call
context. Nie wykazano fałszywego przypisania
właściciela w sprawdzonych przypadkach. Wymaga
późniejszej weryfikacji zakresu modelowania,
tożsamości obiektów i kontraktu kompletności wyników.
Nie zatwierdzono jeszcze implementacji.
