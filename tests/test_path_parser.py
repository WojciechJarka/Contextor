import os
import contextor.ui
from unittest.mock import patch
from contextor.repo_generator.path_parser import parse_paths_from_text

def test_parse_paths_from_text():
    # Definiujemy wirtualną listę plików, które "istnieją"
    existing_files = {
        os.path.abspath("C:\\real_file.txt"),
        os.path.abspath("C:\\Program Files\\app.exe"),
        os.path.abspath("src/main.py"),
        os.path.abspath("src/utils.py")
    }

    # Ta funkcja zastąpi prawdziwe sprawdzanie dysku
    def mock_isfile(path):
        return os.path.abspath(path) in existing_files

    # Używamy patch, aby "oszukać" funkcję os.path.isfile na czas testu
    with patch("os.path.isfile", side_effect=mock_isfile):
        
        # 1. Prosty test - jedna poprawna ścieżka
        text1 = "C:\\real_file.txt"
        parsed1 = parse_paths_from_text(text1)
        assert os.path.abspath("C:\\real_file.txt") in parsed1

        # 2. Test ignorowania nieistniejących plików
        text2 = "C:\\fake_file.txt"
        parsed2 = parse_paths_from_text(text2)
        assert len(parsed2) == 0

        # 3. Test list numerowanych i punktowanych
        text3 = "1. C:\\real_file.txt\n* src/main.py"
        parsed3 = parse_paths_from_text(text3)
        assert len(parsed3) == 2
        assert os.path.abspath("C:\\real_file.txt") in parsed3
        assert os.path.abspath("src/main.py") in parsed3

        # 4. Test ścieżek ze spacjami wplecionych w zdania (z komentarzem)
        text4 = "Sprawdź plik C:\\Program Files\\app.exe - to on odpowiada za błąd."
        parsed4 = parse_paths_from_text(text4)
        assert len(parsed4) == 1
        assert os.path.abspath("C:\\Program Files\\app.exe") in parsed4

        # 5. Test ścieżek oddzielonych przecinkami (w tym jednej fałszywej)
        text5 = "Pliki: src/main.py, src/utils.py, C:\\fake_file.txt"
        parsed5 = parse_paths_from_text(text5)
        assert len(parsed5) == 2
        assert os.path.abspath("src/main.py") in parsed5
        assert os.path.abspath("src/utils.py") in parsed5

        # 6. Test braku duplikatów
        text6 = "src/main.py i jeszcze raz src/main.py"
        parsed6 = parse_paths_from_text(text6)
        assert len(parsed6) == 1
        assert os.path.abspath("src/main.py") in parsed6
