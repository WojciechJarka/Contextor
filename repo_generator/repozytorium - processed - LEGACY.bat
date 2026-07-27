@echo off
setlocal EnableDelayedExpansion

REM Ustawienie kodowania UTF-8 dla konsoli Windows
chcp 65001 >nul

REM ============================================================================
REM == SKRYPT GENERUJACY REPOZYTORIUM Z FILTROWANIEM ARTEFAKTOW (COMPLETO) ==
REM ============================================================================

set "REPO_FOLDER=C:\Users\DafoO\Desktop\SpiralProphet"
set "SCRIPT_DIR=C:\Users\DafoO\Desktop"
set "PYTHON_EXE=C:\WPy64-31090\python-3.10.9.amd64\python.exe"
set "OUTPUT_FILE=%SCRIPT_DIR%\repozytorium.txt"
set "ERROR_LOG_FILE=%SCRIPT_DIR%\log_bledow.txt"
set "PREPROCESS_SCRIPT=%SCRIPT_DIR%\preprocess.py"
set "FILE_EXTENSIONS=*.py *.bat *.vbs *.js *.sh *.md *.txt *.json"

REM Domyślnie filtracja włączona
set "DO_FILTER=T"

REM === WALIDACJA ŚRODOWISKA ===

if not exist "%PREPROCESS_SCRIPT%" (
    echo [WARNING] Preprocessing script not found: "%PREPROCESS_SCRIPT%"
    echo Filtering will be disabled.
    set "DO_FILTER=N"
)

if "%DO_FILTER%"=="T" (
    if not exist "%PYTHON_EXE%" (
        echo [WARNING] Python interpreter not found at: "%PYTHON_EXE%"
        echo Filtering will be disabled.
        set "DO_FILTER=N"
    )
)

:ASK_FILTER
echo.
echo Do you want to filter the repository using preprocess.py?
echo Type T (Yes) or N (No) and press ENTER.
set /p "USER_INPUT=Selection [T/N]: "

if /I "%USER_INPUT%"=="T" (
    set "DO_FILTER=T"
    echo Log rozpoczecia: %date% %time% > "%ERROR_LOG_FILE%"
) else if /I "%USER_INPUT%"=="N" (
    set "DO_FILTER=N"
    del "%ERROR_LOG_FILE%" 2>nul
) else (
    echo Invalid selection. Try again.
    goto :ASK_FILTER
)

REM Czyszczenie pliku wynikowego
del "%OUTPUT_FILE%" 2>nul

echo.
echo Starting file processing in folder: "%REPO_FOLDER%"

for /R "%REPO_FOLDER%" %%F in (%FILE_EXTENSIONS%) do (
    set "RELATIVE_PATH=%%F"
    call set "RELATIVE_PATH=%%RELATIVE_PATH:!REPO_FOLDER!\=%%"
    
    set "SKIP="
    REM Twoja lista wykluczeń
    if /I "%%~nxF"=="repozytorium.txt" set "SKIP=1"
    if /I "%%~nxF"=="preprocess.py" set "SKIP=1"
    if /I "%%~nxF"=="log_bledow.txt" set "SKIP=1"
    if /I "%%~nxF"=="spiralprophet.ico" set "SKIP=1"
    if /I "%%~nxF"=="chat_history.json" set "SKIP=1"
    
    REM Wykluczenie folderów ukrytych/venv (dodatkowe zabezpieczenie)
    echo %%F | findstr /i "\\.git\\ \\venv\\ \\__pycache__\\" >nul && set "SKIP=1"

    if not defined SKIP (
        echo Processing: "!RELATIVE_PATH!"
        echo #~~~~~~[START PLIKU: "!RELATIVE_PATH!" ]~~~~~~# >> "%OUTPUT_FILE%"

        if "%DO_FILTER%"=="T" (
            "%PYTHON_EXE%" "%PREPROCESS_SCRIPT%" "%%F" 2>>"%ERROR_LOG_FILE%" >> "%OUTPUT_FILE%"
        ) else (
            REM Używamy Pythona do zrzutu całości (bezpieczniejsze niż 'type' dla UTF-8)
            "%PYTHON_EXE%" -c "import sys; data = open(sys.argv[1], 'r', encoding='utf-8', errors='ignore').read(); sys.stdout.buffer.write(data.encode('utf-8'))" "%%F" >> "%OUTPUT_FILE%"
        )
        
        echo. >> "%OUTPUT_FILE%"
        echo #~~~~~~[KONIEC PLIKU: "!RELATIVE_PATH!" ]~~~~~~# >> "%OUTPUT_FILE%"
        echo. >> "%OUTPUT_FILE%"
    )
)

echo.
echo =========================================
echo Processing finished. Result: "%OUTPUT_FILE%"
if "%DO_FILTER%"=="T" echo Check logs: "%ERROR_LOG_FILE%"
echo =========================================
pause
