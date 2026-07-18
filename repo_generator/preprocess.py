import sys
import re
import os

def preprocess_file(file_path):
    try:
        # Pobranie rozszerzenia pliku
        file_ext = os.path.splitext(file_path)[1].lower()

        # Odczyt z ignorowaniem błędów kodowania (kluczowe na Windows)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        processed_lines = []
        
        # 1. WZORCE TEKSTOWE / AI (Usuwamy z każdego rodzaju pliku)
        general_trash = [
            re.compile(r".*ZACHOWAJ HISTORIĘ.*", re.IGNORECASE),
            re.compile(r".*UTRZYMUJ DOKUMENTACJĘ.*", re.IGNORECASE),
            re.compile(r".*KOMENTUJ KOD.*", re.IGNORECASE),
            re.compile(r".*NIE USUWAJ FUNKCJI.*", re.IGNORECASE),
            re.compile(r".*ZACHOWAJ SZCZEGÓŁOWE LOGOWANIE.*", re.IGNORECASE),
            re.compile(r".*OZNACZAJ ZMIANY W KODZIE.*", re.IGNORECASE),
            re.compile(r".*ZACHOWAJ FORMĘ I ROZBUDUJ.*", re.IGNORECASE),
            re.compile(r".*PRECYZUJ HISTORIĘ.*", re.IGNORECASE),
            re.compile(r".*Plik:.*", re.IGNORECASE),
            re.compile(r".*Autor:.*", re.IGNORECASE),
            re.compile(r".*Data:.*", re.IGNORECASE),
            re.compile(r".*Opis:.*", re.IGNORECASE),
            re.compile(r".*Wersja:.*", re.IGNORECASE),
            re.compile(r".*HISTORIA ZMIAN:.*", re.IGNORECASE),
            re.compile(r".*KANON NAJLEPSZYCH PRAKTYK.*", re.IGNORECASE),
            re.compile(r".*OBOWIĄZUJE DLA WSZYSTKICH PLIKÓW.*", re.IGNORECASE),
            re.compile(r".*HOLISTYCZNEJ ANALIZIE.*", re.IGNORECASE),
            re.compile(r".*DOKŁADNIEJSZY OPIS:.*", re.IGNORECASE),
            re.compile(r".*INTERFEJSY I ZALEŻNOŚCI.*", re.IGNORECASE),
            re.compile(r".*== WEJŚCIA.*", re.IGNORECASE),
            re.compile(r".*== WYJŚCIA.*", re.IGNORECASE),
            re.compile(r".*START ZMIANY.*", re.IGNORECASE),
            re.compile(r".*KONIEC ZMIANY.*", re.IGNORECASE),
            re.compile(r".*Pełna Forma Pliku.*", re.IGNORECASE),
            re.compile(r".*Nie zgaduj!!!.*", re.IGNORECASE),
            re.compile(r".*Nigdy nie usuwaj istniejących wpisów.*", re.IGNORECASE),
            re.compile(r".*publicznych metod.*", re.IGNORECASE),
            re.compile(r".*rozbudowuj je.*", re.IGNORECASE),
            re.compile(r".*egzekutywnego oznaczaj.*", re.IGNORECASE),
            re.compile(r".*szczegółowo opisz.*", re.IGNORECASE),
            re.compile(r".*i treści instrukcji.*", re.IGNORECASE),
            re.compile(r".*zawierać dokładny czas modyfikacji.*", re.IGNORECASE),
            re.compile(r".*nowej zawartośći pliku.*", re.IGNORECASE),
            re.compile(r".*próbuj je złożyć.*", re.IGNORECASE),
            re.compile(r".*\(Sekcja zgodna ze standardem P\.F\.P\.\).*"),
            re.compile(r".*WERSJA POPRAWIONA.*", re.IGNORECASE),
            re.compile(r".*\(standardowy nagłówek\).*"),
            re.compile(r".*numer wersji.*", re.IGNORECASE),
            re.compile(r".*inne moduły.*", re.IGNORECASE),
            re.compile(r".*sekcje informacyjne.*", re.IGNORECASE),
            re.compile(r".*ewolucji kodu.*", re.IGNORECASE),
            re.compile(r".*konfigurację logowania.*", re.IGNORECASE),
            re.compile(r".*tworzy i konfiguruje.*", re.IGNORECASE),
            re.compile(r".*zapisywania logów.*", re.IGNORECASE),
            re.compile(r".*wyświetlania ich.*", re.IGNORECASE),
            re.compile(r".*różnych poziomów.*", re.IGNORECASE),
            re.compile(r".*zawsze DEBUG.*", re.IGNORECASE),
            re.compile(r".*bibliotek zewnętrznych.*", re.IGNORECASE),
            re.compile(r".*Główne skrypty.*", re.IGNORECASE),
            re.compile(r".*skonfigurować logowanie.*", re.IGNORECASE),
            re.compile(r".*tworzenia loggerów.*", re.IGNORECASE),
            re.compile(r".*ustawiania poziomów.*", re.IGNORECASE),
            re.compile(r".*Poziom logowania.*", re.IGNORECASE),
            re.compile(r".*nadmierną ilość.*", re.IGNORECASE),
            re.compile(r".*została zaimputowana.*", re.IGNORECASE),
            re.compile(r".*do przetworzenia.*", re.IGNORECASE),
            re.compile(r".*moduły \(WEJŚCIA.*", re.IGNORECASE),
            re.compile(r".*ten moduł \(WYJŚCIA\).*", re.IGNORECASE),
            re.compile(r".*informacyjne/plik, rób.*", re.IGNORECASE),
            re.compile(r".*rozbudowy lub.*", re.IGNORECASE),
            re.compile(r".*lub uaktualnienia.*", re.IGNORECASE),
            re.compile(r".*precyzyjne śledzenie.*", re.IGNORECASE),
            re.compile(r".*=======.*", re.IGNORECASE),
            re.compile(r".*poproś o.*", re.IGNORECASE) ,
            re.compile(r".*pliku, lub.*", re.IGNORECASE) ,
            re.compile(r".*11. Zamiast.*", re.IGNORECASE) ,
            re.compile(r".*niniejszym czacie.*", re.IGNORECASE) ,
            re.compile(r".*Wersja\s*\|\s*Data\s*.*"),
            re.compile(r".*\|\s*2025.*"),
            re.compile(r".*\|\s*v1\.0.*", re.IGNORECASE),
            re.compile(r".*`Użycie:.*"),
            re.compile(r".*`Opis:.*"),
            re.compile(r".*`Wywoływana przez:.*"),
            re.compile(r".*sers\\DafoO.*"),
            re.compile(r"^#~+\[START PLIKU:.*"),
            re.compile(r"^#~+\[KONIEC PLIKU:.*"),
            re.compile(r"^\s*#\s*$"),
            re.compile(r"^\s*\n$"),
            re.compile(r"^\s*(\.|\.{3})\s*$"),
        ]

        # 2. WZORCE SYSTEMOWE / BATCH (Usuwamy TYLKO z plików .bat)
        # Te wzorce niszczyły kod Pythona (np. setattr, print, separatory ---)
        batch_trash = [
            re.compile(r".*@echo\s*off.*", re.IGNORECASE),
            re.compile(r".*setlocal.*", re.IGNORECASE),
            re.compile(r".*cls.*", re.IGNORECASE),
            re.compile(r".*echo\s*=.*", re.IGNORECASE),
            re.compile(r".*::.*"),
            re.compile(r".*rem.*", re.IGNORECASE),
            re.compile(r".*if\s*not\s*exist.*", re.IGNORECASE),
            re.compile(r".*set\s*.*", re.IGNORECASE),
            re.compile(r".*pause.*", re.IGNORECASE),
            re.compile(r".*exit\s*/b.*", re.IGNORECASE),
            re.compile(r".*xcopy.*", re.IGNORECASE),
            re.compile(r".*for\s*/f.*", re.IGNORECASE),
            re.compile(r".*powershell\.exe.*", re.IGNORECASE),
            re.compile(r".*---+.*"),
            re.compile(r".*- .*", re.IGNORECASE),
            re.compile(r".*#      .*", re.IGNORECASE),
            re.compile(r".*# ....*", re.IGNORECASE),
        ]
        
        artifact_pattern = re.compile(r"^\s*[\.\,\-_~]+\s*$")

        for line in lines:
            # Filtr 1: Ogólne śmieci (zawsze)
            if any(pattern.search(line) for pattern in general_trash):
                continue
            
            # Filtr 2: Śmieci Batchowe (TYLKO jeśli to nie jest plik .py)
            if file_ext != ".py":
                if any(pattern.search(line) for pattern in batch_trash):
                    continue
            
            processed_lines.append(line)

        # Czyszczenie góra/dół
        while processed_lines and not processed_lines[0].strip():
            processed_lines.pop(0)
        while processed_lines and not processed_lines[-1].strip():
            processed_lines.pop()
        if processed_lines and artifact_pattern.search(processed_lines[-1]):
            processed_lines.pop()
        
        # WYJŚCIE BINARNE
        if processed_lines:
            output_content = "".join(processed_lines)
            sys.stdout.buffer.write(output_content.encode('utf-8'))
            sys.stdout.buffer.flush()

    except Exception as e:
        sys.stderr.write(f"Error processing {file_path}: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        preprocess_file(sys.argv[1])