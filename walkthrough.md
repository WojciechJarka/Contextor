# TASK: C16-P15-HCV-R2 — etap 1, autorytet źródeł

## PREFLIGHT_AND_AUTHORITY

- DIRECT_EVIDENCE: prompt R2 został oceniony według punktu 15 AGENTS.md. Żąda dowodów, nie narzuca wyniku semantycznego ani implementacji; na tym etapie nie wykryto przesłanki do `BLOCKED_SEMANTIC_INTEGRITY`. To nie zatwierdza żadnej reguły modelu.
- Contextor MCP użyty jako pierwsze narzędzie discovery: `get_project_architecture(fields=[])`. LIVE `canonical_revision=1155`, `canonical_state=fresh`, projektowy `workspace_sync=unverified`, graph/topology/cycles=fresh, `cycle_semantics=stale`, `resync_required=false`, syntax errors=0 fresh, 16 strukturalnych ścieżek DFS. Raport historyczny z 2026-11-08 nie jest świeżym dowodem semantyki.
- DIRECT_EVIDENCE: lokalny HEAD `563d2794a5ef81a6f7ca2ffd204c4d58e56f7673`; worktree przed raportem: wyłącznie `M walkthrough.md`; `.venv` CPython 3.15.2. Nie utożsamiono HEAD z LIVE.
- DIRECT_EVIDENCE: lokalne `engine_state.meta.json` w kanonicznym cache repozytorium: schema 1.4, `state_id=20261108_172727`, `revision=1155`, `repo_id=ctx_8efc50d8`, `root_path=C:\Temp\Contextor_Repo`, `writer=live-service`. Jest to zgodny identyfikator trwałej generacji; bieżąca odpowiedź MCP architektury nie eksponuje state_id/repo_id z RAM, więc ich tożsamość w samym LIVE pozostaje do potwierdzenia w etapie publikacji.
- `get_analysis_status` dla ostatniego ukończonego FULL potwierdza historyczną publikację `state_id=20261108_172727` przy rewizji 1128 i sukces mutacji; to nie jest dowód sukcesu semantyki przy obecnej rewizji 1155.
- `get_live_events(after_revision=1154)` potwierdza zdarzenie `desktop_watcher` dla testu pakietowego przy rewizji 1155; bieżący `cycle_warning_view` jest fresh, 16 ścieżek strukturalnych, `model_pass_count=0`, `active_warning_count=16`. Widok ostrzeżeń ma semantykę zainstalowanej akceptacji modelu statycznego, nie wykonania Pythonowego.
- Contextor `get_module_context` zwrócił `workspace_sync=verified`, rev 1155 dla `evidence.py`, `source_proof.py`, `generation_manifest.py`, `partial_scc_claims.py`, `cycle_warning_projection.py`. W poprzednim etapie R1 to samo potwierdzono dla `package_model.py` i `scenarios.py` przez `get_symbol_implementation(mode=preview)`; w tym etapie nie powtarzano bez potrzeby pełnych odczytów.
- Contextor `get_symbol_lineage(mode=preview)` rozwiązał dokładnie `generation_manifest::prepare_cycle_source_manifest`, `A7216/1`, świeże lineage/query-index przy rewizji 1155. W E2 pobrano wybrane sekcje `connections` i `calls_interfaces` dla tego symbolu oraz `seal_partial_scc_preparation`; liczne dynamiczne call sites pozostały unresolved, dlatego literalny kod uzupełnia dowód. `get_symbol_call_context` potwierdził m.in. wewnątrzmodułowe `verify_co_published_partial_scc_preparation -> seal_partial_scc_preparation`, lecz jego kontrakt nie obejmuje połączeń między modułami. `contextor_fact_lineage` v1 obsługuje tylko artifact_consumption, syntax_diagnostics, symbol_calls; nie jest bezpośrednim dowodem rodziny cycle semantics.

## REUSED_PRIOR_EVIDENCE

- Poprzedni HCV-R1 wykonał 28 syntetycznych przypadków B01–B06, K01–K10, D01–D12 w trybie produkcyjnym, prywatnym i warunkowym oraz 112 świeżych uruchomień CPython. Raport R1 miał werdykt `DISCOVERY_PARTIAL`; nie odtwarzano macierzy ani 120 commitów. Te wcześniejsze wyniki będą hipotezami do selektywnej weryfikacji, nie samodzielnym dowodem poprawności.

## COMPLETE_PUBLICATION_CALL_CHAIN

CODE_PATH_PROVED, aktualny HEAD: rzeczywista kolejność **nie** jest liniową listą z promptu. `prepare_original_worker_cycle_manifest(index, hard_edges, CycleSemanticsSnapshot)` w `original_worker_preparation.py:85-167` najpierw wymaga `SELECTED_CLOSURES_CONSISTENT_NON_ATOMIC`, parsuje zachowane bajty `SourceSnapshot`, wywołuje `build_source_bound_cycle_evidence`, potem `prepare_cycle_source_manifest`. Pierwsza funkcja wywołuje `analyze_cycle_scenarios` (`evidence.py:601-613` dla HARD_ONLY, `:674-681` dla opcjonalnego wyboru). Funkcja manifestu wywołuje `assess_scc_source_bytes` lub wariant opcjonalny (`generation_manifest.py:96-137`); source proof z kolei **odtwarza** `build_source_bound_cycle_evidence` i wymaga równości replay/source evidence (`source_proof.py:230,480,499-528`). Są to wywołania bezpośrednie, a nie kolejne niezależne publikacje.

`generation_manifest.py:152-219` dopuszcza tylko `BYTE_AST_CONSISTENT_NON_ATOMIC`, oczekiwany authority oraz dokładne klasyfikacje `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS` lub `MODEL_INTERNAL_EARLY_BINDING_HAZARD`; inaczej tworzy `INDETERMINATE/UNAVAILABLE`. Manifest niesie source/AST signatures i model evidence hash, ale pozostaje `PREPARED_UNPUBLISHED`.

`facade.py:1030-1055` dopuszcza przygotowanie dopiero po reindeksacji `REINDEX_COHERENT_SELECTED_BYTES_NON_ATOMIC`; błąd daje UNAVAILABLE. `facade.py:1497-1523` dla HARD_ONLY wymaga jawnego opt-in, świeżych rodzin semantyki/cykli, stabilnej nieatomowej coverage, braku source issues/resync, identycznego graph/state oraz zgodnych modułów; wywołuje `validate_partial_scc_claims` i przekazuje przygotowanie tylko gdy wynik nie jest `None`. `partial_scc_claims.py:68-213` sprawdza graph hash/topologię, fingerprinty cyklicznych modułów, tożsamość SCC/closure, status i model kind. Dopuszcza część SCC jako `UNAVAILABLE/INDETERMINATE`, ale tylko `PREPARED_UNPUBLISHED` z jedną z dwóch dokładnych klasyfikacji może później zyskać model-pass path. UNKNOWN nie jest zamieniany na PASS.

`facade.py:1593-1604` przekazuje `prepared_partial_scc_preparation` do `save_engine_state`; `state_manager.py:531-585` przekazuje je do `save_snapshot`. `store.py:1771-1809` kopiuje stan, wywołuje `seal_partial_scc_preparation` na tej kopii z metadata revision/state_id/repo_id/root_path i przypisuje `cycle_partial_source_publication`. `partial_scc_publication.py:50-97` wymaga świeżych rodzin, no-resync, graph SHA, state revision/state_id i ponownie waliduje claims; receipt zawiera digest z claims i preparation. Nieudane uszczelnienie rzuca wyjątek, więc meta commit nie następuje; `save_engine_state` łapie błąd i zwraca `None` (`state_manager.py:587-594`).

`store.py:1847-1965` zapisuje kopię z receipt do generation pickle, flush/fsync, następnie atomowo zastępuje wskaźnik `engine_state.meta.json` przez `os.replace` i zwraca metadata. To jest trwały commit generacji. W LIVE ścieżce committed-snapshot publish `ipc.py:1450-1567` sprawdza revision/state_id i monotoniczność, a przy trzymanych blokadach store/mutation przypisuje `self._state = committed_state`, `self._revision = committed_revision` (`:1555-1565`). Alternatywny publish w `ipc.py:1654-1693` ma odrębne sprawdzenie monotoniczności; jego dokładny admission contract nie został w pełni rozebrany.

`store.py:2421-2433,2572-2584` podczas hydracji weryfikuje receipt względem metadata i usuwa nieważny. `partial_scc_publication.py:100-128` przelicza seal z obecnym stanem i wymaga równości receipt. `lifecycle.py:118-120` unieważnia wszystkie trzy receipt na określonej ścieżce życia stanu; pełny zbiór jej callerów nie był audytowany. Jeśli kopia stanu jest tworzona z receipt, lecz nowe preparation nie zostało dostarczone, `store.py:1808-1809` usuwa partial receipt.

## LIVE_RECEIPT_INSTALLATION

CODE_PATH_PROVED dla implementacji: receipt jest przypisany wyłącznie do `state_to_persist`, nie do wejściowego `state` (`store.py:1757-1809`), potem zapisany w pickle i zainstalowany przez committed-snapshot publish (`ipc.py:1563`). `assess_live_installed_partial_claims` jest wywoływany bezpośrednio przez `partial_warning_eligibility.py:37-50` pod blokadą LIVE oraz przez IPC generation check (`ipc.py:2543-2564`). `live_installed_partial_claims.py:53-156` sprawdza service/process/repo/root, `state.revision/state_id`, świeżość cykli i semantyki, no-resync, dokładny typ receipt, `verify_co_published_partial_scc_preparation`, claims SHA i graph SHA; brak któregokolwiek daje `unavailable` z powodem. Aktualna rewizja 1155 ma `cycle_semantics=stale`, więc ta bramka nie może potwierdzić partial receipt jako model-pass. Nie odczytano samych bajtów obecnego pickle ani nie potwierdzono obecności receipt w RAM: UNKNOWN.

## WARNING_CONSUMERS

`partial_warning_eligibility.py:19-127` wywołuje installed assessor; wymaga exact binding/status/revision/state_id/graph SHA/claims SHA/activity epoch, SCC membership i `PREPARED_UNPUBLISHED` + dokładnie `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`. Inny status, w tym stale/UNKNOWN/PARTIAL, zwraca pusty zbiór. `cycle_warning_projection.py:24-127` waliduje strukturalne ścieżki i dzieli je na `model_pass_paths` i `active_warning_paths`; pusta eligibility pozostawia wszystkie jako aktywne. `live_cycle_warning_query.py:27-129` pod blokadą LIVE pobiera authority/state identity, wywołuje projekcję i fail-closed zwraca `unavailable` przy złej partycji. `ipc.py:2416-2442` udostępnia `get_installed_cycle_warning_projection` tylko gotowemu ownerowi.

Desktop FULL `gui.py:1308-1325` włącza partial opt-in i następnie wywołuje `filter_installed_desktop_cycle_errors`; `ui/cycle_warning_presentation.py:170-224` filtruje tylko dokładne `ArchitectureCycle` odpowiadające zaakceptowanej ścieżce z aktualnej, zgodnej odpowiedzi LIVE, inaczej zachowuje błędy. Desktop watcher `watcher.py:1109-1182` czyta tę samą projekcję i sprawdza revision, epoch, repo/root/process/instance, graph hash i partycję. MCP `get_live_events.py:5-78,285-308` pobiera tę samą projekcję, wymaga zgodnego revision/epoch oraz poprawnej partycji. DIRECT_EVIDENCE z etapu 1: bieżący publiczny widok 16 structural, 0 model-pass, 16 active.

Alternatywne ścieżki: `publication_binding.py` ma legacy/pełny `cycle_source_publication` i `warning_eligibility.py:_verified_model_pass_cycle_paths`, lecz literalny przegląd bieżących wywołań w `contextor/**/*.py` nie znalazł callerów tej funkcji. `optional_scc_publication.py` publikuje oddzielny receipt; aktualna `cycle_warning_projection.py` czyta wyłącznie partial eligibility. `namespace_bound_model.py:217-235` zachowuje `CONDITIONAL_MODEL_PASS`; `package_model.py:2871-2881` mapuje wewnętrzny MODEL_PASS na tę etykietę. `scenarios.py:331-358` wywołuje package evaluator bez assumption flags, a partial claims przyjmują tylko dokładną zwykłą klasyfikację. Z tych sprawdzonych połączeń nie wynika ścieżka warunkowego PASS do wyciszenia. Dynamiczna modyfikacja stanu/nieprzejrzyste alternatywne entry pointy nie zostały dowiedzione jako niemożliwe: globalna nieosiągalność NOT_VERIFIED.

## INDEPENDENT_SEMANTIC_CONTRACT_AUDIT

| Mechanizm i kod | Niezależna podstawa, testy, werdykt ograniczony |
|---|---|
| Pasywna funkcja `package_model.py:99-186` | [Python function definitions](https://docs.python.org/3/reference/compound_stmts.html#function-definitions): ciało jest odroczone, dekoratory/defaults mogą być oceniane przy definicji. Odmowa dekoratorów i nieliteralnych defaults to `CONSERVATIVE_LIMITATION`; przyjęcie literalnych defaults jest `SEMANTICALLY_JUSTIFIED` w granicach zwykłego środowiska. Testy passive_functions i R1 D01/D03/D04 dają przykłady, nie pełny dowód. |
| Pasywna klasa, baza i import w ciele `package_model.py:289-500,1010-1135,2221-2246` | [Python class definitions](https://docs.python.org/3/reference/compound_stmts.html#class-definitions): baza oceniana przed ciałem, ciało wykonane przed związaniem nazwy klasy. CPython K08/K09 i nowy ślad potwierdzają kolejność. Bare `ValueError` zaakceptowany, `Exception/object` odrzucone mimo sukcesu CPython K03/K04: `PROJECT_SPECIFIC_SELECTION` + `CONSERVATIVE_LIMITATION`, nie potwierdzony fałszywy PASS. Modułowe przesłonięcie ValueError jest sprawdzane, pełne środowisko builtins nie. |
| Importy/wiązanie w cyklu `package_model.py:756-869,988-1002,1837-2048` | Python import może udostępnić częściowo zainicjalizowany moduł. R1 B02/K09 oraz nowy ślad klasy pokazują hazard zależny od entry/order. Wybrane reguły `SEMANTICALLY_JUSTIFIED` w badanych źródłach; kompletność obsługi wszystkich form importu `UNVERIFIED`. B03 nie jest fałszywym hazardem; model odmawia nieobsługiwanej zagnieżdżonej ekspresji. |
| Guardy `package_model.py:872-935`, odroczony import funkcji | Literalne `if True/False` odpowiada semantyce [if statement](https://docs.python.org/3/reference/compound_stmts.html#if); B04–B06 zgodne w próbkach. Inne testy guardów i dynamiczne warunki nieprzejrzane w pełni: `UNVERIFIED`. |
| Adnotacje `package_model.py:226-286,2390-2437` | [Python 3.15 annotations](https://docs.python.org/3/reference/datamodel.html#annotations): odroczona ewaluacja może uruchomić kod przy odczycie. Bez dekoratora późniejsze przesłonięcie `ast` zmienia wynik; `@dataclass` może wymusić odczyt przy dekoracji. R10 `ast.AST` wobec równie poprawnego `pathlib.Path` D12 jest `PROJECT_SPECIFIC_SELECTION` i `CONSERVATIVE_LIMITATION`; uniwersalna soundness `UNVERIFIED`. |
| Warunkowe importy zewnętrzne i dataclass/field/property `package_model.py:189-223,304-419,1843-1868,2132-2219` | [dataclasses API](https://docs.python.org/3/library/dataclasses.html) uzasadnia znaczenie `frozen` i `field(hash=False)`, ale nie dowodzi pasywności każdego zewnętrznego importu ani niezmienności builtins. R1 D06/D07/D09/D11 są wyłącznie `CONDITIONAL_MODEL_PASS`; nowy kontrprzykład z zewnętrznym modułem przesłaniającym `builtins.property` daje `CONDITIONAL_ASSUMPTION_MISMATCH`. `field(compare=False)` i `pathlib.Path` UNKNOWN to `CONSERVATIVE_LIMITATION`; wybór exact `field(hash=False)` i `@property` to `PROJECT_SPECIFIC_SELECTION`. Brak dowodu `CONFIRMED_FALSE_MODEL_PASS` dla zwykłej produkcji. |

Wszystkie werdykty są ograniczone do odczytanych branchy i wybranych fixture. Nie twierdzę, że żaden poprawny mechanizm Pythona nie jest odrzucony ani że dowolny import/model PASS oznacza runtime safety.

## TEST_CONTRACT_INDEPENDENCE

Odczytane rzeczywiste asercje, bez pytest: `tests/test_cycle_semantics_package_model.py:318-365` przyjmuje Contextor-shaped `SourceError(ValueError)` oraz syntetyczny `CustomError(ValueError)` jako MODEL_PASS; `:368-429` odrzuca inne bazy, metaclass, dekorator i przesłonięty ValueError jako UNKNOWN. To sprawdza granicę implementacji, lecz nie dowodzi, że wyłącznie ValueError jest semantycznie pasywne. R1 K03/K04 pokazują bezpieczne w tych fixture bazy Exception/object z UNKNOWN.

`tests/test_cycle_semantics_package_model.py:760-835` używa `Module`, `ImportRef`, `field(hash=False)`, property i asercji o kolejności zdarzeń; jest szczególnie związany ze źródłem Contextora. Negatywy `:920-1033` sprawdzają field binding, inne keywordy, metody i lokalny shadow property; nie badają zewnętrznego modułu zmieniającego `builtins.property`. `:1115-1169` poprawnie rozróżnia ordinary UNKNOWN od bezpośredniego `MODEL_PASS` ze scope warunkowym. Te testy nie są niezależnym dowodem pasywności importów zewnętrznych. Pozostałe powiązane testy source proof/receipt/consumerów i pełna macierz testów semantycznych: NOT_VERIFIED. Brak testów wykonanych w tym etapie.

## TARGETED_DIFFERENTIAL_EVIDENCE

CPython 3.15.2 `-I`, świeży proces na próbę, syntetyczne pliki poza repo. Sterownik i źródła `C:\Temp\hcv_r2_probe.py` (nie plik repo). Próby mają jawne teksty źródła i stdout/stderr w wyniku wykonania; poniżej decisive evidence.

- **B03 dokładny model bez print:** `a.py="from .b import other\nvalue = 1\n"`; `b.py="import p.a\nother = p.a.value\n"`; `__init__.py` pusty. `_compile(b)` zwrócił `None`, a `evaluate_package_import_order(...,_compile_on_first_import=True)` `UNKNOWN`, target=`p.b`, events `START_IMPORT, READY, START_IMPORT, START_IMPORT, IMPORT`. Pierwsza odmowa to `package_model.py:988-1002`: `other=p.a.value` ma zagnieżdżony `ast.Attribute`, a przyjmowana jest tylko ekspresja `Name.attr`. Osobny instrumentowany wariant z `print` w a/b pokazał `a:start`, `b:start`, `b:bound False`, po czym CPython `AttributeError: cannot access submodule 'a' ... due to a circular import`. Print sam jest poza ograniczonym modelem, dlatego powód odmowy ustalono na **oryginalnym** źródle bez instrumentacji.
- **Porządek klasy:** `a.py="value=1\nprint('a:before-class')\nclass C:\n print('class:before-import')\n from .b import other\n print('class:after-import',other)\nprint('a:class-bound',C.__name__)\n"`; `b.py="other=2\nprint('b:before-read')\nfrom .a import value\nprint('b:read-value',value)\n"` (w pliku rzeczywiste wcięcia czterospacjowe). Ślad CPython: `a:before-class -> class:before-import -> b:before-read -> b:read-value 1 -> class:after-import 2 -> a:class-bound C`. Potwierdza kolejność i binding w tym przykładzie. Instrumentacja `print` sprawia, że nie jest to fixture akceptowane przez model; odwołanie do modelowych K08/K09 pochodzi z R1.
- **Adnotacja po definicji:** plain `class C: x: ast.AST` po `ast=None` tworzy klasę, lecz `C.__annotations__` zgłasza `AttributeError` w `__annotate__`. Natomiast `@dataclass(frozen=True)` z `x: ast.AST`, `y: pathlib.Path` po przesłonięciu obu nazw zwróciło wcześniej rozstrzygnięte klasy w `C.__annotations__`; dekorator odczytał adnotacje przy tworzeniu. D06–D12 wymagają rozróżnienia opóźnionej semantyki języka od faktycznej konsumpcji przez dataclass. Pojedyncza próba nie obejmuje wszystkich odmian dekoratora/field.
- **Założenie zewnętrzne:** namespace `p.a`: `from dataclasses import dataclass; value=1; from .b import other; @dataclass(frozen=True) class C: x:int; @property def y(self): return self.x`; `p.b`: `other=2; import evil_hcv_r2; from .a import value`; zewnętrzne `evil_hcv_r2.py`: `import builtins; builtins.property=1; print('evil:property-rebound')`. Warunkowy evaluator z `assume_passive_external_imports=True`, `assume_frozen_dataclass_decoration=True`, target 3.15 i dokładnym SearchPortion zwrócił `CONDITIONAL_MODEL_PASS`, scope `CONDITIONAL_EXTERNAL_AND_FROZEN_DATACLASS_ASSUMPTIONS_NOT_RUNTIME_PROOF`, records `dataclasses`, `evil_hcv_r2`, jedna dekoracja. CPython wypisał `evil:property-rebound`, potem `TypeError: 'int' object is not callable` przy `@property`. Pierwsza rozbieżność to fałszywe **jawne założenie pasywności** zewnętrznego importu, nie dowód błędu ordinary produkcyjnego PASS ani samego stdlib property.

Dokładne źródła śladów (pusty `__init__.py` dla B03 i klasy; brak `__init__.py` dla namespace):

```text
B03 instrumented a.py:
print("a:start")
from .b import other
value = 1

B03 instrumented b.py:
print("b:start")
import hcv_r2_b03.a
print("b:bound", hasattr(hcv_r2_b03, "a"))
other = hcv_r2_b03.a.value

class_order a.py:
value = 1
print("a:before-class")
class C:
    print("class:before-import")
    from .b import other
    print("class:after-import", other)
print("a:class-bound", C.__name__)

class_order b.py:
other = 2
print("b:before-read")
from .a import value
print("b:read-value", value)

annotation_later_read a.py:
from dataclasses import dataclass
import ast
import pathlib
@dataclass(frozen=True)
class C:
    x: ast.AST
    y: pathlib.Path
print("created", C.__name__)
ast = None
pathlib = None
print("rebound")
try:
    print("annotations", C.__annotations__)
except Exception as exc:
    print("annotation_error", type(exc).__name__, str(exc))

conditional_external_effect a.py:
from dataclasses import dataclass
value = 1
from .b import other
@dataclass(frozen=True)
class C:
    x: int
    @property
    def y(self): return self.x

conditional_external_effect b.py:
other = 2
import evil_hcv_r2
from .a import value

external evil_hcv_r2.py:
import builtins
builtins.property = 1
print("evil:property-rebound")
```

Plain-class deferred-annotation microprobe source was `import ast; exec('class C:\\n    x: ast.AST\\n'); print('created'); ast=None; print(C.__annotations__)` in a fresh `-I` subprocess; stdout `created`, then `AttributeError: 'NoneType' object has no attribute 'AST'` in `__annotate__`. The semicolon here is exact microprobe source, not the file-based fixture.

## CONFIRMED_DEFECTS

`CONFIRMED_FALSE_MODEL_PASS` dla ścieżki produkcyjnej: brak potwierdzonego przykładu. `CONFIRMED_FALSE_HAZARD`: brak potwierdzonego przykładu. Potwierdzono wąski `CONDITIONAL_ASSUMPTION_MISMATCH` dla zewnętrznego importu zmieniającego builtin property; taki wynik ma jawnie warunkowy scope i etykietę oraz nie przeszedł sprawdzonej ścieżki publikacji ostrzeżeń.

## CONSERVATIVE_LIMITATIONS

R1 K03–K05 (`Exception`, `object`, user base), D02–D05 (dekoratory/default), D08 (`field(compare=False)`), D12 (`pathlib.Path`) dają runtime sukces w wybranych fixture przy modelowym UNKNOWN. To ograniczenia obsługi; samo UNKNOWN nie jest błędnym stwierdzeniem hazardu. B03 też UNKNOWN, lecz CPython w tym układzie rzeczywiście zawodzi. Nie ma podstawy do automatycznego rozszerzenia PASS na te konstrukcje.

## PROJECT_SPECIFIC_SELECTIONS

`package_model.py:316-323` dopuszcza bare ValueError, lecz odrzuca Exception/object; `:226-241` dopuszcza `ast.AST`, lecz odrzuca inne kwalifikowane adnotacje; `:210-223` dopuszcza exact `field(hash=False)`; `:118-127` dopuszcza bare `@property` tylko w warunkowej dataclass. To `PROJECT_SPECIFIC_SELECTION`, oparte na aktualnym kodzie i Contextor-shaped pozytywnym R11 teście. Żaden z tych wyborów sam w sobie nie dowodzi fałszywego ordinary PASS. Wpływ: głównie UNKNOWN/niekompletna coverage; warunkowa akceptacja zależy od niezweryfikowanych zewnętrznych efektów.

## UNVERIFIED

- Obecność receipt w bieżącym LIVE RAM i jego dokładna tożsamość; stan LIVE ma cycle_semantics=stale, więc nie wydaje modelowego potwierdzenia. Tożsamość `state_id/repo_id` w RAM wobec zgodnych metadanych dyskowych nie była odczytana bezpośrednio.
- Wszystkie warianty optional/legacy publication, bezpośredni publish admission, każdy caller unieważniania w `lifecycle.py` i dynamiczne wpisy stanu nie zostały zamknięte pełnym dowodem nieosiągalności warunkowego PASS. Literalny przegląd bieżących callerów wskazuje brak przejścia, lecz globalny dowód pozostaje NOT_VERIFIED.
- Pełna ocena `evaluate_flat_import_order`, wszystkich import hooks/metaclass/builtins environment, 3.15 dataclass annotation edge cases i wszystkich powiązanych testów. Selektywne subprocessy nie certyfikują ogólnej semantyki Pythona.
- Eksperyment z zewnętrznym modułem pokazuje rozbieżność z **założeniem**, nie realizuje `CONFIRMED_FALSE_MODEL_PASS` zwykłej ścieżki. Brak niezależnego kontrprzykładu dla ordinary zaakceptowanej reguły pozostaje otwartym wynikiem poszukiwania, nie dowodem soundness.

## FILES_CHANGED

`walkthrough.md` wyłącznie. Brak zmian production/test/docs.

## FULL_DIFFS

ACTUAL_DIFF=DIFFS=NONE dla production/test/docs. Sam raport nie jest własnym diffem.

## FINAL_VERDICT

`DISCOVERY_PARTIAL` dla pełnego R2: wykonano etapy E2–E4 w ograniczonym zakresie opisanym powyżej; pozostałe dokładne luki wymieniono w UNVERIFIED. Nie ma podstawy do FINAL PASS ani do modyfikacji kodu. Punkt 15 AGENTS.md nie wymusił `BLOCKED_SEMANTIC_INTEGRITY`, gdyż prompt nie narzuca wadliwej implementacji ani spreparowanego wyniku; potencjalne założenie pasywności zewnętrznego importu zostało jawnie zakwestionowane dowodem CPython. STOP.

# C16-P15-HCV-R3 — PUBLICATION BOUNDARY CLOSURE

Stan odniesienia: HEAD `563d2794a5ef81a6f7ca2ffd204c4d58e56f7673`, Contextor MCP canonical revision 1155, `resync_required=False`, graph/cycles fresh, cycle_semantics stale. R2 powyżej zachowany. Discovery rozpoczęto przez Contextor MCP (`get_project_architecture`, `get_module_context`, `get_symbol_lineage`), następnie sprawdzono aktualne źródła i istniejące testy. To analiza statyczna, bez mutacji LIVE i bez testów.

## ALTERNATIVE_LIVE_PUBLISH

- `contextor/core/live_state/runtime.py:1613-1631` inicjuje jedyny znaleziony produkcyjny `CanonicalLiveServer` i przekazuje `committed_snapshot_reader=lambda: locked_committed_snapshot(...)` z oczekiwanym repo/root. `ipc.py:800-855` dopuszcza `None` jako domyślną wartość konstruktora, lecz w sprawdzonej konfiguracji runtime reader jest ustawiony. Fallback z `ipc.py:1635-1693` jest więc `UNREACHABLE_IN_VERIFIED_CONFIGURATION` startu przez `runtime.py`; to nie dowód globalnej nieosiągalności dla zewnętrznego konstruktora lub izolowanych testów.
- `ipc.py:2350-2377` dispatchuje operację `publish` do `_execute_publish`; `ui/gui.py:1810-1830` wywołuje `client.publish` przy startup pod lease pełnej analizy. `ipc.py:1991-2000` kieruje także zakolejkowany `submit_committed_publish` do tej metody z `SimpleNamespace(state_id, revision)`, a `:2000-2020` odmawia tej operacji bez readera. `ipc.py:1621-1636` blokuje publikację podczas recovery i bierze `_mutation_execution_lock`. Dla skonfigurowanego readera `ipc.py:1392-1567` ładuje committed snapshot, porównuje identyfikator i rewizję z żądaniem, a instaluje załadowany committed state pod blokadą. `PATH_PROVED_SAFE_WITHIN_CONTRACT` dla sprawdzonej ścieżki committed snapshot; nie jest to certyfikacja dowolnego klienta IPC.
- Fallback `ipc.py:1637-1693` sprawdza tylko ciągłość rewizji, po czym instaluje `request.state`; nie weryfikuje tam receipt, state_id ani repo_id. `request.state` technicznie może mieć pola receipt. `CONFIRMED_PUBLICATION_DEFECT` jako naruszenie lokalnego kontraktu autoryzacji fallbacku nie jest dowiedziony, ponieważ normalny start ustawia reader, a testy tworzą serwer izolowany. Gdyby fallback został użyty, `live_installed_partial_claims.py:102-174` i `partial_warning_eligibility.py:35-88` nadal niezależnie wymagają zgodności typu stanu, rewizji, state_id, repo/root, świeżości, graph/claims hash i ważnego receipt; brak tych warunków daje pustą eligibility. Werdykt dla hipotetycznej ścieżki zewnętrznej: `NOT_VERIFIED`.

## RECEIPT_INVALIDATION_COVERAGE

- `lifecycle.py:95-120` czyści trzy receipt dla `SOURCE_CHANGED`, `SOURCE_DELETED`, `SOURCE_PARSE_FAILED`, `CANONICAL_RESYNC_REQUIRED`. Callerzy znalezieni w `analysis/incremental/engine.py:309,592,988`. `:592` obsługuje resync przed no-op, `:722-735` błąd parsowania, `:774-782` pusty refresh plan, `:973-990` zmianę/usunięcie źródła i resync. `state_manager.py:147-171` inicjuje i klonuje receipt jako None. `live_state/store.py:1782-1828` nadaje nowe receipty tylko przy przygotowaniu publikacji i czyści w przeciwnym razie; `:2409-2451,2560-2602` weryfikuje je podczas obu ścieżek hydracji i usuwa niezgodne. `ipc.py:1555-1567` zastępuje LIVE state stanem committed; `:1686-1689` fallback zastępuje go stanem requestu. To ostatnie ogranicza się do konfiguracji bez readera.
- Potwierdzony lokalny defekt: `_commit_syntax_candidate` w `engine.py:240-337` wywołuje `invalidate_cycle_semantics(candidate, reason)` na kopii, lecz kopiuje z powrotem wyłącznie snapshot/status/reason i pola syntax/lineage; nie kopiuje `candidate.cycle_source_publication`, `candidate.cycle_partial_source_publication`, `candidate.cycle_optional_source_publication`. Przy parse failure (`:722-735`) lub pustym planie (`:774-782`) stare receipty na `self.state` pozostają. To `CONFIRMED_PUBLICATION_DEFECT` w utrzymaniu stanu po invalidation. Istniejące `tests/test_cycle_semantics_invalidation.py:144-181` sprawdzają stale status/evidence, nie retencję receipt. Nie wykazano wyciszenia ostrzeżeń: `live_installed_partial_claims.py:102-174` odmawia przy `cycle_semantics_state != fresh`, a weryfikacja receipt i generacji następuje ponownie. Skutek po późniejszej reindeksacji lub innej mutacji stanu: `NOT_VERIFIED`.

## OPTIONAL_AND_LEGACY_REACHABILITY

- `publication_binding.py:303` weryfikuje kompletny receipt; konsumenci obejmują `live_installed_claims.py:171`, `worker_claim_binding.py:155`, hydrację w `store.py:2409,2560` i historyczny `warning_eligibility.py:43`. `warning_eligibility.py:20` definiuje `_verified_model_pass_cycle_paths`; w bieżącym produkcyjnym drzewie nie znaleziono callera, a projekcja `cycle_warning_projection.py:10,87` używa wyłącznie partial eligibility. Werdykt o wpływie tej funkcji na sprawdzoną projekcję: `PATH_PROVED_FAIL_CLOSED`; globalna nieosiągalność dynamicznych wywołań: `NOT_VERIFIED`.
- Optional receipt z `optional_scc_publication.py:162` ma osobny seal/verify, hydrację `store.py:2441-2451,2592-2602` i właścicielski query `ipc.py:2447-2500` przez `live_installed_optional_claims.py:36-210`. Opcja przygotowania jest dostępna w `api/facade.py:659-678,1526`; nie jest to martwy kod. Optional query nie jest używany przez `cycle_warning_projection.py:87`, więc nie przenosi bezpośrednio akceptacji do aktualnej partycji ostrzeżeń. Testy `test_cycle_semantics_live_installed_optional_claims.py` i `test_cycle_semantics_optional_child_full_preview.py` potwierdzają zamierzony osobny kontrakt, nie dowodzą semantycznej poprawności wszystkich modeli optional. Werdykt: `PATH_PROVED_SAFE_WITHIN_CONTRACT` dla izolacji projekcji, szersza semantyka `NOT_VERIFIED`.

## CONDITIONAL_PASS_ISOLATION

- `namespace_bound_model.py:217-235` pozostawia `CONDITIONAL_MODEL_PASS` w osobnym wyniku. `source_proof.py:55-90,215-258` w zwykłej ścieżce wymaga modelu związanego z indeksem, porównuje hashe bytes/AST, odtwarza `build_source_bound_cycle_evidence` i porównuje scenariusz oraz token z dostarczonymi wartościami. Tylko klasyfikacje `MODEL_ALL_FRESH_MEMBER_ENTRIES_PASS`/hazard przechodzą przez `generation_manifest.py:150-175` i `partial_scc_claims.py:155-180`. Stąd ręczne podmienienie samego wyniku lub `evidence_scope` bez zgodnego replay daje odmowę. Optional replay `source_proof.py:475-520` również wymaga równości całego evidence. Werdykt: `PATH_PROVED_FAIL_CLOSED` dla bezpośredniego przeniesienia conditional result do zwykłego partial receipt. Nie jest to dowód prawdziwości ordinary MODEL_PASS przy wszystkich efektach importu; R2 dokumentuje kontrprzykład warunkowego założenia.

## DESKTOP_MCP_EVENTS_CONSUMERS

- Właściciel LIVE `ipc.py:2416-2442` czyta projekcję pod `_lock` przez `live_cycle_warning_query.py:27-129`. `cycle_warning_projection.py:40-127` oblicza świeżą partycję structural/model_pass/active z partial eligibility i odmawia dla niepoprawnego inwentarza lub braku fresh state. `ui/gui.py:1308-1325` włącza filtrowanie po FULL; `ui/cycle_warning_presentation.py:152-224` wymaga success publikacji, odczytu LIVE oraz dokładnej zgodności `ArchitectureCycle` path/message. `watcher.py:1109-1182` sprawdza rewizję, epoch, endpoint identity i partycję. `mcp/tools/get_live_events.py:285-308` dołącza bieżący widok do historii, jawnie rozdzielając historyczne zmiany strukturalne od aktywnych ostrzeżeń. W sprawdzonych połączeniach żaden z tych konsumentów nie używa optional/legacy jako świeżego model-pass: `PATH_PROVED_SAFE_WITHIN_CONTRACT`. Pełna inwentaryzacja wszystkich potencjalnych zewnętrznych klientów IPC pozostaje `NOT_VERIFIED`.

## PUBLICATION_TEST_CONTRACTS

Odczytane powiązania testowe: `tests/test_cycle_semantics_publication_live_integration.py` (committed snapshot, receipt/hydration), `tests/test_cycle_semantics_invalidation.py` (source/parse/resync status), `tests/test_cycle_semantics_live_installed_partial_claims.py`, `tests/test_cycle_semantics_live_installed_optional_claims.py`, `tests/test_cycle_semantics_cycle_warning_projection.py`, `tests/test_cycle_semantics_live_cycle_warning_query.py`, `tests/test_cycle_semantics_live_warning_transition_checkpoint.py`, `tests/test_cycle_semantics_desktop_full_partial_activation.py`, `tests/test_cycle_semantics_optional_child_full_preview.py`. Fallback jest testowany przez izolowane serwery z reader=None (`test_cycle_semantics_live_warning_transition_checkpoint.py:27,105`; `test_cycle_semantics_cycle_warning_projection.py:184`). Ich oczekiwania obejmują identyfikatory, odmowy i partycję, ale nie stanowią niezależnego dowodu semantyki CPython ani gwarancji rzeczywistej konfiguracji Desktop. Nie uruchomiono testów: etap jest read-only i nie wymaga mutacji kanonicznej.

## CONFIRMED_PUBLICATION_DEFECTS

`CONFIRMED_PUBLICATION_DEFECT`: `analysis/incremental/engine.py:309-337` — wynik czyszczenia trzech receipt na candidate ginie podczas `_commit_syntax_candidate`; osiągalne z `:722` (parse failure) i `:774` (empty refresh plan). Bezpośrednio udowodniony skutek to zachowanie starych pól receipt w `self.state` po source invalidation. Nie wykazano, by stare receipt uzyskały świeżą eligibility, gdy status semantyki jest stale.

## REMAINING_UNVERIFIED_LINKS

1. Pełny audyt bram własności/uwierzytelnienia w wejściu IPC `publish` oraz wszystkich możliwych konstruktorów spoza produkcyjnego `runtime.py`; sam brak dodatkowego callera w repo nie dowodzi niemożliwości klienta zewnętrznego.
2. Zachowanie zachowanych starych receipt po późniejszym powrocie `cycle_semantics_state` do fresh lub zmianie rewizji bez nowego seal; aktualny fail-closed przy stale jest udowodniony, ale pełny łańcuch po reindeksacji nie.
3. Kompletny wpływ optional/legacy query na wszystkie interfejsy diagnostyczne i dynamicznych klientów; izolacja bieżącej projekcji jest wykazana.
4. Niezależne, negatywne testy receiptu po parse failure i empty refresh plan oraz reprodukcja defektu w izolowanym fixture; obecny werdykt wynika z prostego przepływu przypisań, nie z wykonania testu.
5. Runtime freshness aktualnie załadowanego Desktop/MCP i dokładny LIVE RAM receipt wobec dysku; analiza dotyczy HEAD i statycznej konfiguracji, nie certyfikuje uruchomionego procesu.

## FILES_CHANGED

`walkthrough.md` wyłącznie. Production/test/docs: NONE.

## FULL_DIFFS

ACTUAL_DIFF=DIFFS=NONE dla production/test/docs. Raport nie zawiera własnego diffu.

## FINAL_VERDICT

`PUBLICATION_BOUNDARY_PARTIAL`. Potwierdzono defekt retencji receipt w inkrementalnej ścieżce syntax candidate i niezależne fail-closed aktualnej partial warning eligibility przy stale. Pozostałe konkretne luki są wymienione powyżej. Brak podstaw do `PUBLICATION_BOUNDARY_VERIFIED` lub FINAL PASS całej semantyki. Brak podstaw do `BLOCKED_SEMANTIC_INTEGRITY` dla samego promptu R3. STOP — bez implementacji; czekam na `proceduj`.

# C16-P15-HCV-R4 — RECEIPT INVALIDATION REPRODUCTION

R2/R3 powyżej pozostają historycznym zapisem. R4 koryguje zakres R3: retencja występuje również przy niepustym planie. Eksperymenty poniżej dotyczyły wyłącznie syntetycznych repozytoriów w `tempfile.TemporaryDirectory` poza projektem. Żadna operacja nie dotknęła kanonicznego LIVE.

## R4_SOURCE_AUTHORITY

HEAD `563d2794a5ef81a6f7ca2ffd204c4d58e56f7673`; w worktree przed R4 zmieniony wyłącznie `walkthrough.md`. Contextor MCP `get_project_architecture(fields=[])`: LIVE revision 1155, resync false, cycle_semantics stale, graph/cycles fresh. MCP `get_symbol_implementation(mode=preview)` potwierdził `workspace_sync=verified` dla `IncrementalAnalysisEngine._commit_syntax_candidate` (`engine.py:240-335`) i `invalidate_cycle_semantics` (`lifecycle.py:95-156`). `_prepare_candidate_state` jest w `plan_executor.py:688`, więc pierwsza próba nazwania go symbolem z `engine.py` dała `not_found`, bez podstaw do wniosku o braku funkcji. Dokładne implementacje i miejsca wywołań odczytano ze źródeł po discovery MCP.

`plan_executor.py:688` tworzy COW `CandidateState`; `engine.py:240-335` i `:970-1155` unieważniają candidate. Oba commit paths kopiują z candidate semantyczny snapshot/status/reason, lecz pomijają trzy pola receipt. `_failed_commit_guard` w `engine.py:173-220` zapisuje `vars(state).copy()` i przy wyjątku przywraca ten sam obiekt oraz FileState tracking. `lifecycle.py:95-120` czyści receipty na przekazanym obiekcie. `store.py:1760-1828` kopiuje stan z receipt input i bez nowego preparation czyści je na kopii przed persist; `:2060+` ładuje snapshot z kontrolą tożsamości. Istniejące testy COW/rollback/parse/empty plan w `tests/test_cycle_semantics_invalidation.py:75-245` sprawdzają semantyczny status, ale nie wszystkie trzy receipty na engine.state. Testy publikacji/hydracji wymieniono w R3.

## ISOLATED_REPRODUCTION

Uruchomiono `& .\.venv\Scripts\python.exe -B -` z kodem przez stdin i `PYTHONDONTWRITEBYTECODE=1`. Każdy scenariusz miał oddzielny `TemporaryDirectory`, dwa cyklicznie importujące się pliki `pkg/a.py` i `pkg/b.py`, `IncrementalAnalysisEngine` z własnym registry/cache oraz rzeczywisty `CycleSemanticsSnapshot` z pomocniczego fixture `tests/test_cycle_semantics_invalidation.py:_snapshot`. Po bazowej indeksacji ustawiono `cycle_semantics_state=fresh`, reason=None i trzy różne `object()` jako znaczniki pól receipt. To nie są poprawne receipty. `revision` i `state_id` na bezpośrednim engine.state były `None` przed i po; to nie jest generacja LIVE.

| Scenariusz | Operacja / wynik | Przed: status, reason, znaczniki | Po: status, reason, znaczniki | Werdykt |
|---|---|---|---|---|
| A | Istniejący `a.py` -> `def broken(:`; `SYNTAX_ERROR` | fresh, None, (1,1,1) | stale, SOURCE_PARSE_FAILED, (1,1,1) | REPRODUCED_STATE_RETENTION |
| B | Dopisanie komentarza, `shadow_plan.is_empty=True`; `UNCHANGED` | fresh, None, (1,1,1) | stale, SOURCE_CHANGED, (1,1,1) | REPRODUCED_STATE_RETENTION |
| C | Usunięcie importu, `shadow_plan.is_empty=False`; `UPDATED` | fresh, None, (1,1,1) | stale, SOURCE_CHANGED, (1,1,1) | REPRODUCED_STATE_RETENTION |
| D | Brak zmiany pliku, `UNCHANGED` | fresh, None, (1,1,1) | fresh, None, (1,1,1) | zachowanie receipt bez invalidation zgodne z kontraktem |

W każdym przypadku zachowana była tożsamość `engine.state`. Powtórzenie z rzeczywistym snapshotem było istotne: próba bez niego dawała `deferred`, zatem nie stanowiłaby poprawnego dowodu przejścia `fresh -> stale`. W scenariuszu C przyczyną jest również brak kopiowania pól w `engine.py:1125-1155`, nie tylko metoda `_commit_syntax_candidate` wskazana w R3.

## RECEIPT_STATE_TRANSITIONS

Bezpośrednio zaobserwowane `IN_MEMORY_RETENTION`: A/B/C dla każdego z trzech pól. D zachowuje pola i status fresh, gdy faktycznie brak source invalidation. Znaczniki dowodzą przepływu przypisań, nie potwierdzają ważności ani eligibility receipt. Nie stwierdzono `CONFIRMED_FALSE_ELIGIBILITY`.

## ROLLBACK_AND_COW_CONTRACT

W osobnym izolowanym scenariuszu B `state_manager.update_state` zastąpiono funkcją rzucającą `RuntimeError('controlled acknowledgement failure')`. Po wyjątku identyczny obiekt `engine.state` miał ponownie `fresh`, reason=None i wszystkie trzy pierwotne znaczniki. `engine.py:173-220` wyjaśnia to przywróceniem `vars(state)` i tracking map. Ewentualne przyszłe przenoszenie pól z candidate musi pozostać w tym samym chronionym logicznym commit; wykonanie go przed guard lub osobno od syntax/lineage mogłoby naruszyć rollback/atomowość. W niepustym planie analogiczny transfer musi objąć drugi commit path `engine.py:1125-1155`; zmiana samego `_commit_syntax_candidate` nie zamknęłaby C. To analiza wpływu, bez projektu poprawki i bez zmian kodu.

## PERSISTENCE_AND_HYDRATION

W izolowanym scenariuszu B powtórzono przebieg z trzema picklowalnymi stringami `MARKER_*`. Po `UNCHANGED`, `stale` i retencji w RAM użyto `save_snapshot` z lokalnym cache, `FileStateManager.build_payload('r4-state',1)`, repo/root identity i `exact_revision=1`; następnie `load_snapshot` z tymi samymi oczekiwanymi identyfikatorami. Zapis zwrócił revision 1, load sukces, wszystkie trzy pola w odczytanym stanie `None`, podczas gdy RAM zachował trzy znaczniki. Pierwsza próba zapisu bez wymaganego `_meta` w file_state_payload została odrzucona przez kontrakt `store.py:1870-1890`; skorygowana próba zakończyła się sukcesem. `PERSISTED_RETENTION`: `NOT_REPRODUCED` w tej ścieżce bez nowego preparation. To nie jest eksperyment z autentycznie zapieczętowanym receiptem ani dowód wszystkich wariantów hydracji.

## POST_REFRESH_ELIGIBILITY

`STALE_ELIGIBILITY_REJECTION`: `PATH_PROVED_FAIL_CLOSED` na podstawie `live_installed_partial_claims.py:102-150` — sprawdzenie `cycle_semantics_state == fresh` poprzedza walidację receipt. Eksperymentalne znaczniki nie miały typu `CanonicalPartialSCCReceipt`, więc nie użyto ich jako testu eligibility. `POST_REFRESH_REACCEPTANCE`: `NOT_VERIFIED`. Nie odtworzono autentycznego receiptu, jego późniejszego `fresh` ani poprawnej tożsamości generacji; nie ma dowodu realnej drogi do fałszywego model-pass.

## INDEPENDENT_REGRESSION_CONTRACTS

Najmniejszy sensowny zestaw przyszłych testów: (1) trzy rozłączne pola receipt na stanie przed A/B/C, po rzeczywistym invalidation każde ma być None, a snapshot ma stale z właściwym reason; (2) D zachowuje te pola i fresh, gdy brak invalidation; (3) kontrolowana awaria commitu przywraca trzy pola, status, syntax/lineage i identyczny obiekt; (4) persist bez nowego preparation i ponowna hydracja nie przywracają starych receipt; (5) po prawidłowym ponownym przygotowaniu fresh tylko nowy receipt zgodnej generacji może uzyskać eligibility, stale lub mismatch revision/state_id/repo/root muszą odmówić. Oczekiwania wynikają z `lifecycle.py:95-120`, COW/rollback `engine.py:173-220`, store `:1760-1828` i installed generation gate, nie z obecnego pominięcia pól. Pozytywny test autentycznego receipt wymaga istniejącego seal contract, nie znaczników.

## CONFIRMED_EFFECTS

`REPRODUCED_STATE_RETENTION` dla A/B/C, wszystkich trzech pól. `NOT_REPRODUCED` dla D jako brak invalidation. `REPRODUCED_PERSISTENCE_DEFECT`: nie; izolowany save/load usunął znaczniki. `CONFIRMED_FALSE_ELIGIBILITY`: nie. `PATH_PROVED_FAIL_CLOSED` dla stale partial warning eligibility w sprawdzonym code path. Nie ekstrapolowano do runtime safety.

## REMAINING_UNVERIFIED

1. Autentyczny sealed receipt w pamięci po A/B/C oraz jego walidacja przy zmianie generacji; znaczniki dowodzą retencji pola, nie poprawności receipt.
2. Ponowny `fresh` po późniejszej reindeksacji i ewentualna re-akceptacja starego receipt; wymaga kontrolowanej ścieżki z prawidłowym przygotowaniem i tożsamością, nie ręcznego ustawienia flagi.
3. Odmowa eligibility wykonawczo na rzeczywistym stanie LIVE lub z autentycznym receipt; obecnie udowodniona code path, nie runtime.
4. Obie ścieżki hydracji z autentycznym, lecz niezgodnym receipt oraz rollback niepustego planu z receipt; nie były przedmiotem izolowanego wykonania.
5. Pozostałe luki R3 w autoryzacji alternatywnego IPC publish i dynamicznych klientach; R4 ich nie badał.

## FILES_CHANGED

`walkthrough.md` wyłącznie. Production/test/docs: NONE.

## FULL_DIFFS

ACTUAL_DIFF=DIFFS=NONE dla production/test/docs. Raport nie zawiera własnego diffu.

## FINAL_VERDICT

`REPRODUCTION_PARTIAL`: wykonawczo zamknięto retencję w RAM dla A/B/C, negatywny D, rollback pustego planu oraz brak persisted retention w sprawdzonym save/load. Pozostałe wymienione kwestie są `NOT_VERIFIED`. Nie deklaruje się `PUBLICATION_BOUNDARY_VERIFIED` ani FINAL PASS. Prompt R4 nie wymusił `BLOCKED_SEMANTIC_INTEGRITY`. STOP — bez implementacji; czekam na `proceduj`.

# C16-P15-HCV-R4-F1 — EXACT RECEIPT INVALIDATION FIX

## PREFLIGHT

HEAD `563d2794a5ef81a6f7ca2ffd204c4d58e56f7673`; przed edycją worktree zawierał wyłącznie zmodyfikowany `walkthrough.md`. Contextor MCP first: LIVE revision 1155, graph/cycles fresh, cycle_semantics stale, resync false; `get_symbol_implementation` potwierdził `workspace_sync=verified` dla `_commit_syntax_candidate` i `invalidate_cycle_semantics`. Źródła `plan_executor.py:46-85,688-800`, `engine.py:173-220,240-335,970-990,1125-1155`, `lifecycle.py:95-120` potwierdziły R4. Istotne call sites: parse failure `engine.py:722`, pusty plan `:774`, niepusty plan `:988`; prawdziwy no-op omija invalidation. Brak materialnego source drift.

## INDEPENDENT_PROMPT_CHECK

Kontrakt `invalidate_cycle_semantics` czyści trzy pola na candidate. `CandidateState` początkowo ich nie deklaruje, lecz mutowalny dataclass przyjmuje je podczas invalidation. Poprzedni commit przenosił status stale, a pozostawiał stare receipt na state, co R4 odtworzył dla trzech ścieżek. Wymagane przypisania wynikają z tego kontraktu, a nie z oczekiwanego zielonego testu. Warunkowe kopiowanie w syntax path chroni prawdziwy no-op. `_failed_commit_guard` obejmuje przypisania i przywraca snapshot pól przy awarii. Brak przesłanki do `BLOCKED_SEMANTIC_INTEGRITY`.

## EXACT_CHANGE_CONTRACT

Wyłącznie `contextor/core/analysis/incremental/engine.py`: po zatwierdzeniu semantycznego statusu w `_commit_syntax_candidate` trzy pola są kopiowane tylko gdy `invalidate_cycle_semantics_reason is not None`; w głównym commit path trzy pola są kopiowane po obowiązkowym invalidation. Bez zmian `CandidateState`, lifecycle, store, IPC, source proof, modelu i eligibility. Zmiana testowa wyłącznie w `tests/test_cycle_semantics_invalidation.py`: A/B/C czyszczenie, D no-op, E/F rollback. Znaczniki `object()` badają transfer, nie stanowią receipt.

## FILES_CHANGED

- `contextor/core/analysis/incremental/engine.py`
- `tests/test_cycle_semantics_invalidation.py`

`walkthrough.md` jest raportem i nie jest liczony jako source/test diff.

## BEFORE_AFTER_RECEIPT_BEHAVIOR

Przed: A/B/C zostawiały wszystkie trzy stare pola; RED 3 FAIL. Po: A parse failure, B pusty refresh plan i C niepusty plan zerują `cycle_source_publication`, `cycle_partial_source_publication`, `cycle_optional_source_publication` na tym samym obiekcie `engine.state`, z odpowiednim stale reason. D prawdziwy no-op zachowuje trzy znaczniki i fresh. To kontrakt lokalnego stanu, bez deklaracji ważności receiptu i bez twierdzenia o runtime safety.

## REGRESSION_TESTS

RED przed patchem produkcyjnym: `python -B -m pytest -q -rs tests/test_cycle_semantics_invalidation.py -k 'incremental_invalidation_clears_all_receipts or true_noop_preserves_all_receipts or failed_incremental_commit_restores_all_receipts'` -> 3 failed (A/B/C), 3 passed (D/E/F), 14 deselected. GREEN po patchem: cały `tests/test_cycle_semantics_invalidation.py` -> 20 passed in 10.67s. Po usunięciu nieużytego parametru z E/F uruchomiono tylko te dwa przypadki -> 2 passed, 18 deselected. Nie uruchomiono pełnego pytest.

## ROLLBACK_VERIFICATION

E/F wymuszają wyjątek `state_manager.update_state` po ścieżce commit; ten sam obiekt stanu zachowuje pierwotne trzy znaczniki, fresh, reason=None oraz początkowe syntax/lineage maps. Istniejący `_failed_commit_guard` przywraca `vars(state)` i tracking map. Nie dodano osobnego zapisu ani mutacji poza ochroną guard.

## POST_CHANGE_MCP_AUDIT

Contextor MCP `get_module_context`: `engine.py` i `tests/test_cycle_semantics_invalidation.py` przy LIVE revision 1158 mają `workspace_sync=verified`, canonical_state fresh, advisory null. W trakcie propagacji watcher widziano przejściowo engine `unverified` przy 1156 i test `out_of_sync` przy 1157; późniejsze wspólne 1158 zamknęło ten drift. `get_project_architecture(fields=[])` przy 1158: graph/cycles fresh, 16 strukturalnych ścieżek jak przed zmianą, resync false; cycle_semantics stale jak przed zmianą. Diff dodaje przypisania i testy, bez importów/zależności, więc brak nowej krawędzi źródłowej; nie jest to certyfikacja pełnej semantyki ani uruchomionego kodu MCP po restarcie.

## REGRESSION_RISK

Ryzyko ogranicza się do transferu trzech pól na główny state. Syntax path ma jawny warunek invalidation, główny path invaliduje zawsze. Testy obejmują no-op, oba typy planu, parse failure i rollback obu planów. Testy ze znacznikami nie certyfikują seal ani eligibility autentycznych receipt. Brak zmiany API i kontraktu store.

## UNVERIFIED_PUBLICATION_PATHS

Pozostają luki R3/R4: alternatywna publikacja IPC poza zweryfikowaną konfiguracją, dynamiczni klienci, autentyczny sealed receipt po późniejszym fresh/reindex oraz pełna certyfikacja hydracji i rzeczywistego procesu LIVE. R4-F1 nie rości `PUBLICATION_BOUNDARY_VERIFIED`.

## FULL_DIFFS

```diff
diff --git a/contextor/core/analysis/incremental/engine.py b/contextor/core/analysis/incremental/engine.py
index 2abf579..2992e32 100644
--- a/contextor/core/analysis/incremental/engine.py
+++ b/contextor/core/analysis/incremental/engine.py
@@ -333,6 +333,10 @@ class IncrementalAnalysisEngine:
         self.state.cycle_semantics_invalidation_reason = (
             candidate.cycle_semantics_invalidation_reason
         )
+        if invalidate_cycle_semantics_reason is not None:
+            self.state.cycle_source_publication = candidate.cycle_source_publication
+            self.state.cycle_partial_source_publication = candidate.cycle_partial_source_publication
+            self.state.cycle_optional_source_publication = candidate.cycle_optional_source_publication
 
     def _update_candidate_lineage_slice(
         self,
@@ -1152,6 +1156,9 @@ class IncrementalAnalysisEngine:
         self.state.cycle_semantics_invalidation_reason = (
             candidate.cycle_semantics_invalidation_reason
         )
+        self.state.cycle_source_publication = candidate.cycle_source_publication
+        self.state.cycle_partial_source_publication = candidate.cycle_partial_source_publication
+        self.state.cycle_optional_source_publication = candidate.cycle_optional_source_publication
         self.state.collision_facts = candidate.collision_facts
         self.state.collisions = candidate.collisions
         self.state.collisions_state = candidate.collisions_state
diff --git a/tests/test_cycle_semantics_invalidation.py b/tests/test_cycle_semantics_invalidation.py
index 5c1ffd1..e8616cd 100644
--- a/tests/test_cycle_semantics_invalidation.py
+++ b/tests/test_cycle_semantics_invalidation.py
@@ -102,6 +102,100 @@ def _assert_stale(engine: IncrementalAnalysisEngine, evidence: CycleSemanticsSna
     assert engine.state.cycle_semantics_invalidation_reason == reason
 
 
+_RECEIPT_FIELDS = (
+    "cycle_source_publication",
+    "cycle_partial_source_publication",
+    "cycle_optional_source_publication",
+)
+
+
+def _seed_receipt_markers(engine: IncrementalAnalysisEngine) -> tuple[object, ...]:
+    markers = tuple(object() for _ in _RECEIPT_FIELDS)
+    for name, marker in zip(_RECEIPT_FIELDS, markers):
+        setattr(engine.state, name, marker)
+    return markers
+
+
+@pytest.mark.parametrize(
+    ("changed_source", "expected_status", "expected_reason", "plan_empty"),
+    (
+        ("def broken(:\n", "SYNTAX_ERROR", "SOURCE_PARSE_FAILED", None),
+        ("import pkg.b\ndef fa():\n    return 1\n# changed\n", "UNCHANGED", "SOURCE_CHANGED", True),
+        ("def fa():\n    return 1\n", "UPDATED", "SOURCE_CHANGED", False),
+    ),
+)
+def test_incremental_invalidation_clears_all_receipts(
+    cyclic_engine, changed_source, expected_status, expected_reason, plan_empty,
+) -> None:
+    engine, a, _ = cyclic_engine
+    _seed_receipt_markers(engine)
+    state = engine.state
+    a.write_text(changed_source, encoding="utf-8")
+
+    result = engine.update_file(str(a))
+
+    assert result.status == expected_status
+    if plan_empty is not None:
+        assert result.shadow_plan is not None
+        assert result.shadow_plan.is_empty is plan_empty
+    assert engine.state is state
+    assert engine.state.cycle_semantics_state == "stale"
+    assert engine.state.cycle_semantics_invalidation_reason == expected_reason
+    assert all(getattr(engine.state, name) is None for name in _RECEIPT_FIELDS)
+
+
+def test_true_noop_preserves_all_receipts(cyclic_engine) -> None:
+    engine, a, _ = cyclic_engine
+    markers = _seed_receipt_markers(engine)
+    state = engine.state
+
+    result = engine.update_file(str(a))
+
+    assert result.status == "UNCHANGED"
+    assert engine.state is state
+    assert engine.state.cycle_semantics_state == "fresh"
+    assert engine.state.cycle_semantics_invalidation_reason is None
+    assert all(
+        getattr(engine.state, name) is marker
+        for name, marker in zip(_RECEIPT_FIELDS, markers)
+    )
+
+
+@pytest.mark.parametrize(
+    "changed_source",
+    (
+        "import pkg.b\ndef fa():\n    return 1\n# changed\n",
+        "def fa():\n    return 1\n",
+    ),
+)
+def test_failed_incremental_commit_restores_all_receipts(
+    cyclic_engine, monkeypatch, changed_source,
+) -> None:
+    engine, a, _ = cyclic_engine
+    markers = _seed_receipt_markers(engine)
+    state = engine.state
+    syntax_before = engine.state.syntax_diagnostics_by_path.copy()
+    lineage_before = engine.state.lineage_facts_by_source.copy()
+    a.write_text(changed_source, encoding="utf-8")
+
+    def fail(*args, **kwargs):
+        raise RuntimeError("controlled acknowledgement failure")
+
+    monkeypatch.setattr(engine.state_manager, "update_state", fail)
+    with pytest.raises(RuntimeError, match="controlled acknowledgement failure"):
+        engine.update_file(str(a))
+
+    assert engine.state is state
+    assert engine.state.cycle_semantics_state == "fresh"
+    assert engine.state.cycle_semantics_invalidation_reason is None
+    assert engine.state.syntax_diagnostics_by_path == syntax_before
+    assert engine.state.lineage_facts_by_source == lineage_before
+    assert all(
+        getattr(engine.state, name) is marker
+        for name, marker in zip(_RECEIPT_FIELDS, markers)
+    )
+
+
 def test_d2_invalidation_preserves_evidence_identity(cyclic_engine) -> None:
     engine, _, _ = cyclic_engine
     evidence = engine.state.cycle_semantics
```

## FINAL_VERDICT

`R4_F1_PASS` dla dokładnego kontraktu lokalnej retencji receipt: dwie ścieżki commitu poprawione, RED/GREEN i focused tests zaliczone, MCP potwierdził zgodność źródeł po zmianie, bez nowych krawędzi importu. Nie oznacza `PUBLICATION_BOUNDARY_VERIFIED`, pełnej poprawności semantycznej ani certyfikacji runtime. STOP — oczekuję na `proceduj`.
