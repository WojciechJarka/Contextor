# Repo Guardian

Narzędzie do statycznej analizy architektury projektów Python: buduje graf
zależności między modułami, wykrywa cykle, kolizje nazw i "hotspoty", liczy
heurystyczny dług architektoniczny i zapisuje raporty JSON. Dostępne jako
GUI (Tkinter) albo CLI.

Pełna lista zmian wprowadzonych względem poprzedniej wersji: patrz
`CHANGELOG.md`.

## Wymagania

- Python 3.10 lub nowszy (testowane na 3.10).
- Pakiet `orjson`:

  ```
  python -m pip install orjson
  ```

  Jeśli masz kilka instalacji Pythona, wskaż jawnie właściwy interpreter,
  np.:

  ```
  C:\Users\<Ty>\AppData\Local\Programs\Python\Python310\python.exe -m pip install orjson
  ```

## Uruchomienie — GUI

1. Ustaw `PYTHONPATH` na katalog **nadrzędny** względem `repo_guardian`
   (import wewnątrz kodu odbywa się jako `repo_guardian.core...`,
   `repo_guardian.ui...`).
2. Uruchom:

   ```
   cd repo_guardian
   python main.py --gui
   ```

   albo po prostu uruchom `run_gui.bat` dwuklikiem — skrypt sam wykrywa
   dostępny interpreter Pythona (launcher `py` albo `python` z `PATH`), więc
   nie wymaga edycji.

## Uruchomienie — CLI

```
cd repo_guardian
set PYTHONPATH=<katalog nadrzędny>
python main.py <ścieżka do analizowanego repozytorium>
```

Raporty JSON (`summary`, `structure`, `artifacts`, opcjonalnie `layer_*`)
zapisują się w podkatalogu `output/` w bieżącym katalogu roboczym.

## Uwaga wydajnościowa

Dla bardzo dużych repozytoriów (rząd tysięcy plików `.py`) generowanie
raportu artefaktów może zająć kilka minut — to normalne (patrz `CHANGELOG.md`,
sekcja o cache'u AST). Indeksowanie samo w sobie powinno trwać sekundy.
