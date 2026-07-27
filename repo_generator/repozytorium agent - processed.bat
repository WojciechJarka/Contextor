@echo off
pause REM <--- DODAJ TĘ LINIĘ
setlocal EnableDelayedExpansion

REM ============================================================================
REM == KONFIGURACJA SKRYPTU ==
REM ============================================================================

REM Sciezka do glownego folderu repozytorium (na pulpicie)
set "REPO_FOLDER=C:\Users\DafoO\Desktop\Agent-Installer"

REM Sciezka do folderu, w ktorym znajduja sie skrypty (na pulpicie)
set "SCRIPT_DIR=C:\Users\DafoO\Desktop"

REM Sciezka do pliku python.exe
set "PYTHON_EXE=C:\WPy64-31090\python-3.10.9.amd64\python.exe"

REM Nazwa pliku wyjsciowego (na pulpicie)
set "OUTPUT_FILE=%SCRIPT_DIR%\repozytorium-agent.txt"

REM Nazwa pliku z logami bledow (na pulpicie)
set "ERROR_LOG_FILE=%SCRIPT_DIR%\log_bledow.txt"

REM Nazwa skryptu do preprocessingu (na pulpicie)
set "PREPROCESS_SCRIPT=%SCRIPT_DIR%\preprocess.py"

REM ============================================================================
REM == GLÓWNA LOGIKA ==
REM ============================================================================

REM Sprawdz, czy skrypt preprocessingu istnieje
if not exist "%PREPROCESS_SCRIPT%" (
    echo [ERROR] Preprocessing script not found: "%PREPROCESS_SCRIPT%"
    goto :end
)

REM Sprawdz, czy sciezka do Pythona jest poprawna
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python interpreter not found at: "%PYTHON_EXE%"
    echo Please update the path to python.exe in this script.
    goto :end
)

REM Petla po wszystkich plikach w folderach (bez pomijania rozszerzen)
for /R "%REPO_FOLDER%" %%F in (*) do (
    echo ZNALAZLEM PLIK: %%F
    if /I not "%%~nxF"=="repozytorium-agent.txt" (
        if /I not "%%~nxF"=="preprocess.py" (
            if /I not "%%~nxF"=="log_bledow.txt" (
                if /I not "%%~nxF"=="spiralprophet.ico" (
                    if /I not "%%~nxF"=="run_agent_debug.bat" (
                        if /I not "%%~xF"==".ico" (
                            if /I not "%%~xF"==".pyc" (
                                if /I not "%%~nxF"=="projects_config.json" (
                                    REM Komunikat o przetwarzaniu pliku
                                    echo Przetwarzam: "%%~nxF"
                                    
                                    REM Przetwarzaj plik i dodaj go do pliku wyjsciowego
                                    echo #~~~~~~[START PLIKU: "%%~nxF" ]~~~~~~#>>"%OUTPUT_FILE%"
                                    "%PYTHON_EXE%" "%PREPROCESS_SCRIPT%" "%%F" 2>>"%ERROR_LOG_FILE%" >>"%OUTPUT_FILE%"
                                    echo.>>"%OUTPUT_FILE%"
                                    echo #~~~~~~[KONIEC PLIKU: "%%~nxF" ]~~~~~~#>>"%OUTPUT_FILE%"
                                    echo.>>"%OUTPUT_FILE%"
                                )
                            )
                        )
                    )
                )
            )
        )
    )
)

echo.
echo =========================================
echo Przetwarzanie zakonczone.
echo Pliki zostaly skonsolidowane w: "%OUTPUT_FILE%"
echo Log bledow znajduje sie w: "%ERROR_LOG_FILE%"
echo =========================================

:end
pause
