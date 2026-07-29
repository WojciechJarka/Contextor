@echo off
setlocal

echo ==========================================
echo     Contextor - GUI Launcher
echo ==========================================
echo.

cd /d "%~dp0"

set PYTHONPATH=%~dp0

:: Detect Python interpreter
set PY=

where python >nul 2>&1
if not errorlevel 1 (
    set PY=python
)

if "%PY%"=="" (
    where py >nul 2>&1
    if not errorlevel 1 (
        set PY=py
    )
)

:: Check common local Python locations
if "%PY%"=="" (
    if exist "%~dp0python.exe" (
        set PY=%~dp0python.exe
    )
)

if "%PY%"=="" (
    echo [ERROR] Python was not found.
    echo Install Python 3.9+ or add Python to PATH.
    pause
    exit /b 1
)

echo [INFO] Using:
%PY% --version

echo.

:: Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...

    %PY% -m venv venv

    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

:: Install dependencies
if exist requirements.txt (
    if not exist "venv\.installed" (

        echo [INFO] Installing dependencies...

        python -m pip install --upgrade pip
        python -m pip install -r requirements.txt

        if errorlevel 1 (
            echo [ERROR] Dependency installation failed.
            pause
            exit /b 1
        )

        type nul > "venv\.installed"

        echo [SUCCESS] Dependencies installed.
    )
)

echo.
echo Starting Contextor GUI...
echo.

python main.py --gui

if errorlevel 1 (
    echo.
    echo [ERROR] Contextor failed to start.
    pause
    exit /b 1
)

pause
