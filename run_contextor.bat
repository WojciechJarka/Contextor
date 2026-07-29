@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo        Contextor Launcher
echo ==========================================
echo.

cd /d "%~dp0"
set PYTHONPATH=%~dp0

:: ==========================================
:: Detect Python interpreter
:: ==========================================

set PYTHON_CMD=

python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
)

if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=py
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python was not found.
    echo Install Python 3.9+ and enable PATH support.
    echo.
    pause
    exit /b 1
)

echo [OK] Python detected: %PYTHON_CMD%
echo.


:: ==========================================
:: Create virtual environment
:: ==========================================

if not exist ".venv" (
    echo [INFO] Creating virtual environment...

    %PYTHON_CMD% -m venv .venv

    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo [SUCCESS] Virtual environment created.
    echo.
)


:: ==========================================
:: Activate environment
:: ==========================================

call ".venv\Scripts\activate.bat"


:: ==========================================
:: Install dependencies
:: ==========================================

if exist "requirements.txt" (

    if not exist ".venv\.installed" (

        echo [INFO] Installing dependencies...

        python -m pip install --upgrade pip

        python -m pip install -r requirements.txt

        if errorlevel 1 (
            echo.
            echo [ERROR] Dependency installation failed.
            pause
            exit /b 1
        )

        type nul > ".venv\.installed"

        echo [SUCCESS] Dependencies installed.
        echo.

    ) else (

        echo [OK] Dependencies already installed.

    )

) else (

    echo [WARNING] requirements.txt not found.
    echo Skipping dependency installation.

)


:: ==========================================
:: Start Contextor
:: ==========================================

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
