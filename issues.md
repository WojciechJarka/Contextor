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

Audyt Spiral Prophet wykazał, że import DataAgent
w agents/data_processing_states.py znajduje się
pod if TYPE_CHECKING, jednak marker importujący
TYPE_CHECKING wraz z trzema innymi nazwami
nie spełnia ograniczonego kontraktu
recognize_typing_guard.

Dodatkowo type_only_candidate_statement_ids
wybiera wybrane ast.Import, ale nie ast.ImportFrom,
a AdvancedImportVisitor.visit_ImportFrom
pozostawia type_only=false.

W tym konkretnym przypadku flaga jest false
już przy ekstrakcji. Nie została cofnięta
z true przez _finalize_type_only_imports.

Finalizacja ma także odrębną konserwatywną
granicę: wymaga między innymi not skipped
i może cofać istniejące type_only=true
przy niekompletnym obrazie projektu.

Krawędź hard jest faktem grafu strukturalnego,
ale sama nie dowodzi wykonania importu
podczas inicjalizacji modułu.

Należy osobno rozstrzygnąć kontrakt
rozpoznawania strażnika, zakres ImportFrom
i warunki bezpieczeństwa całego projektu.
Nie zatwierdzono implementacji.

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
