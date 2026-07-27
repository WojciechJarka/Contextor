# Changelog — sesja napraw i redesignu GUI

Dokument opisuje zmiany wprowadzone w kodzie `repo_guardian` w ramach tej sesji:
naprawę uruchamiania aplikacji, trzy błędy funkcjonalne/wydajnościowe w
pipeline'ie analizy oraz przebudowę wizualną całego GUI.

---

## 1. Naprawa uruchamiania GUI

**Plik:** `run_gui.bat`

**Problem:** skrypt wskazywał na interpreter Pythona pod ścieżką
`C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe`, która nie
istnieje na tym komputerze — i ogólniej, każda ścieżka wpisana na sztywno
działa tylko na maszynie, na której powstała.

**Zmiana (finalna, przenośna):** skrypt sam wykrywa dostępny interpreter,
niezależnie od maszyny — najpierw próbuje launchera `py` (`where py`,
standard przy instalacji z python.org), a gdy go nie ma, spada na `python`
z `PATH` (`where python`). Jeśli żadne z nich nie jest dostępne, wypisuje
czytelny komunikat z linkiem do instalatora zamiast cichego błędu. Dzięki
temu `run_gui.bat` działa bez edycji na dowolnym komputerze z zainstalowanym
Pythonem 3.10+.

---

## 2. Bug: `main.py` ignorował ścieżkę repozytorium przekazaną w CLI

**Plik:** `main.py`

**Problem:** `main()` wywoływał `cli_main()` bez żadnych argumentów, mimo że
`cli.py` przyjmuje `root_path`. W efekcie CLI zawsze analizowało bieżący
katalog (`.`), ignorując ścieżkę podaną w wierszu poleceń
(`python main.py <ścieżka>`).

**Zmiana:** `main()` odczytuje `sys.argv[1]` (domyślnie `"."`) i przekazuje go
do `cli_main(path)`.

---

## 3. Bug wydajnościowy: O(n²) logowanie w indekserze

**Plik:** `core/indexer.py`, funkcja `build_index()`

**Problem:** dla **każdego** nowo zaindeksowanego pliku funkcja wypisywała na
konsolę pełną, dotychczasową listę wszystkich zaindeksowanych modułów
(`for k, v in modules.items(): print(...)` wewnątrz głównej pętli po plikach).
Dla repozytorium z ~10 000 plików `.py` (np. Kronos) oznaczało to rząd
dziesiątków milionów linii printa — indeksowanie faktycznie nigdy się nie
kończyło w rozsądnym czasie.

**Zmiana:** usunięto trzy zbędne instrukcje debugowe (`print("BUILD_INDEX
ROOT:", ...)`, `print("RESOLVED ROOT:", ...)` oraz pętlę drukującą całą mapę
modułów po każdym pliku). Indeksowanie dużego repo skróciło się z
"nie kończy się" do kilku sekund.

---

## 4. Bug: `cli.py` — błędne wywołanie `generate_layer_report()`

**Plik:** `cli.py`

**Problem:** wywołanie
`generate_layer_report(graph, layer_path=layer, root_path=root_path)` nie
zgadzało się z sygnaturą funkcji
`generate_layer_report(layer_path, modules, graph, root_path)` — powodowało to
`TypeError: got multiple values for argument 'layer_path'` i przerywało CLI
zawsze na etapie generowania raportów per-warstwa (dla dowolnego repo).
Dodatkowo `layer_path` musi być pełną ścieżką do podkatalogu warstwy, a nie
samą nazwą.

**Zmiana:** wywołanie poprawione na pełną, nazwaną sygnaturę
(`layer_path=layer_full_path, modules=modules, graph=graph,
root_path=root_path`), gdzie `layer_full_path = os.path.join(root_path,
layer)`. Dodano też pominięcie warstw, których katalog nie istnieje w
analizowanym repo (`PROJECT_LAYERS = ["core", "ui", "cli", "domain",
"facts"]` to nazwy specyficzne dla samego repo_guardian i nie każde
analizowane repozytorium je ma).

---

## 5. Bug wydajnościowy: brak cache'a AST przy generowaniu raportu artefaktów

**Pliki:** `core/symbol_reference.py`, `core/artifact_usage_report.py`

**Problem:** `collect_module_artifacts()` wywołuje `build_symbol_references()`
osobno dla **każdego** modułu posiadającego własne symbole (definer module).
Wewnątrz `build_symbol_references()` funkcja `_load_tree()` za każdym razem
**od nowa czytała z dysku i parsowała AST wszystkich modułów w projekcie** —
bez żadnego współdzielonego cache'a. Dla repozytorium z setkami modułów
definiujących symbole i tysiącami plików łącznie dawało to rząd
dziesiątek–setek tysięcy pełnych re-parsowań AST (dla Kronosa krok ten nie
kończył się nawet po kilku minutach).

**Zmiana:**
- `_load_tree(root_path, module, tree_cache=None)` — dodano opcjonalny
  słownik cache (klucz: `module_id`), zwracający już sparsowane drzewo
  zamiast parsować plik ponownie.
- `build_symbol_references(..., tree_cache=None)` — przyjmuje i przekazuje
  dalej cache do `_load_tree`.
- `collect_module_artifacts()` — tworzy jeden słownik `tree_cache = {}` przed
  pętlą i przekazuje go do każdego wywołania `build_symbol_references()`, dzięki
  czemu każdy plik jest parsowany co najwyżej raz na całe wywołanie raportu.

Efekt: generowanie `Kronos_artifacts.json` (551 modułów w grafie, ~10 000
plików `.py` łącznie) skróciło się z "nie kończy się" do ok. 5 minut.

---

## 6. Redesign GUI — nowy wspólny system stylu

**Nowy plik:** `ui/theme.py`

Bez dodatkowych zależności (czysty `ttk.Style`, motyw bazowy `clam`):

- **Paleta:** neutralne tło (`#f5f6fa`), biała "karta" na pola (`#ffffff`),
  jeden kolor akcentu — niebieski `#2f6fed` — dla akcji głównej, czerwień
  tylko dla akcji destrukcyjnych.
- **Typografia:** Segoe UI z jasną hierarchią (nagłówek / sekcja / etykieta
  pola / tekst pomocniczy).
- **Style przycisków:**
  - `Primary.TButton` — jedyna akcja wyróżniona kolorem (np. "Analyze
    Repository", "Generuj repozytorium").
  - `Secondary.TButton` — przyciski z obrysem, dla pozostałych akcji.
  - `Ghost.TButton` / `Danger.Ghost.TButton` — subtelne przyciski narzędziowe
    (toolbar), przy czym akcje destrukcyjne (np. "Empty Output", "Przywróć
    wszystko") są wyraźnie oznaczone kolorem czerwonym.
- **`Tooltip`** — lekka klasa dymka (Toplevel bez ramki, pokazywany po
  zatrzymaniu kursora), zastępująca wcześniejszy hack z podmienianiem tytułu
  okna na czas hovera.

`apply_theme(root)` wywołane raz na oknie głównym obowiązuje też we
wszystkich `Toplevel`-ach otwieranych z tego samego roota (współdzielony
interpreter Tcl). Dla `repo_generator/repo_gui.py`, które tworzy **własny**
`tk.Tk()`, motyw jest aplikowany osobno w `run_repo_generator()`.

---

## 7. Redesign GUI — `ui/gui.py` (okno główne)

- Layout przepisany z chaotycznego `pack()` na `grid()` — pola wyrównują się
  i skalują z oknem; okno jest teraz `resizable` z `minsize(680, 560)` i
  startowym rozmiarem 760×640 (wcześniej sztywne 600×440).
- Każde pole ma opisową etykietę: "Repository root", "Layer — optional
  subdirectory of the root", "Single file — optional .py file to analyze"
  (wcześniej trzeba było się domyślać z kolejności pól).
- Sekcje pogrupowane wizualnie: nagłówek aplikacji (tytuł + podtytuł), karta
  "Project" (3 ścieżki + separatory), rząd trzech akcji analizy, konsola
  logów/progress bar, dolny toolbar.
- Prawdziwe tooltips (`Tooltip` z `ui/theme.py`) zamiast podmiany tytułu okna.
- **Usunięto zduplikowany przycisk "Parsuj JSON"** — w oryginalnym kodzie był
  wstawiony do dolnego paska dwukrotnie (kopiuj-wklej).

---

## 8. Redesign GUI — `ui/exclude_gui.py` (Exclude Manager)

- Nagłówek + podtytuł okna.
- `Listbox` przekolorowany pod jasny motyw (tło białe, zaznaczenie w kolorze
  akcentu).
- Przyciski przeniesione na `ttk` z hierarchią stylów; "Przywróć wszystko"
  oznaczone jako akcja destrukcyjna (`Danger.Ghost.TButton`).
- Przycisk "Usuń zaznaczone / Przywróć" przemianowany na "Przywróć
  zaznaczone" — nazwa dokładniej opisuje faktyczne działanie (`restore_selected`).

---

## 9. Redesign GUI — `ui/gui_parser.py` (Parsuj JSON)

- Dodane etykiety pól ("Plik JSON", "Nazwa pliku lub symbolu…").
- Layout pola ścieżki + przycisku "Browse…" przeniesiony na `grid` w obrębie
  jednego wiersza.
- Główny przycisk akcji w stylu `Primary.TButton`.

---

## 10. Redesign GUI + bugfix — `repo_generator/repo_gui.py` (Repo Builder)

**Bug:** metoda `RepoGenerator.build_gui()` była zdefiniowana **dwukrotnie**
w tej samej klasie (linie ~253 i ~357). Druga definicja cicho nadpisywała
pierwszą (standardowe zachowanie Pythona przy duplikacie metody), więc
pierwsza, uboższa wersja (bez przycisków "zaznacz/odznacz wszystkie", bez
dolnego panelu i przycisku generowania) była martwym kodem. Usunięto
duplikat.

**Redesign:**
- Nagłówek + podtytuł okna.
- Pasek ikon (`create_icon_button`) przeniesiony na `ttk.Button` w stylu
  `Secondary.TButton`, tło `Canvas` z ikoną dopasowane do tła aplikacji.
- Lista plików i scrollbar przestylowane pod jasny motyw (jak w Exclude
  Manager).
- Przyciski pogrupowane: kontrolki listy (zaznacz/odznacz — `Ghost.TButton`),
  dolny pasek (Filtry / Output Folder — `Secondary.TButton`, Opróżnij output —
  `Danger.Ghost.TButton`).
- Główny CTA **"Generuj repozytorium"** — wcześniej `tk.Button` z twardo
  wpisanym `bg="green", fg="white"`; teraz `Primary.TButton`, spójny z resztą
  aplikacji.
- Okno "Filtry plików" — nagłówki sekcji, `ttk.Checkbutton`, separator przed
  rzędem przycisków, "Zapisz" wyróżnione jako `Primary.TButton`.

---

## Weryfikacja

- Wszystkie zmienione moduły przechodzą parsowanie AST (`ast.parse`) bez
  błędów składniowych.
- Smoke test programowy: zbudowano wszystkie cztery okna (`gui.py` root,
  Exclude Manager, Parsuj JSON, Repo Builder + okno Filtrów) w jednym procesie
  Tk bez wyjątków.
- Naprawiony pipeline CLI uruchomiony end-to-end na zewnętrznym repozytorium
  (Kronos, ~10 000 plików `.py`) — `summary`, `structure` i `artifacts`
  generują się poprawnie.
