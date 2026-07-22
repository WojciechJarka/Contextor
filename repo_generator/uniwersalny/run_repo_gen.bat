@echo off
setlocal

:: Ustawienie kodowania na UTF-8 dla poprawnych polskich znaków
chcp 65001 >nul

:: Przejście do katalogu, w którym znajduje się ten plik .bat
cd /d "%~dp0"

:: Ścieżka do Twojego interpretera Python
set PYTHON_CMD=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe

:: Sprawdzenie czy interpreter istnieje pod wskazaną ścieżką
if not exist "%PYTHON_CMD%" (
    echo [BŁĄD] Nie znaleziono interpretera Python pod ścieżką:
    echo %PYTHON_CMD%
    pause
    exit /b 1
)

echo Uruchamianie Repo Guardian przy użyciu WinPython...
"%PYTHON_CMD%" repo_gui.py

pause
