@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo        Contextor Launcher
echo ==========================================
echo.

cd /d "%~dp0"
set PYTHONPATH=%~dp0

:: Detect Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found.
    echo Install Python 3.9+ and add it to your system PATH.
    pause
    exit /b 1
)

:: Virtual Environment setup
if not exist ".venv" (
    echo [INFO] Creating virtual environment ^(.venv^)...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
    echo.
)

:: Activate Virtual Environment
call ".venv\Scripts\activate.bat"

:: Detect and install requirements
if exist "Requirements.txt" set REQ_FILE=Requirements.txt
if exist "requirements.txt" set REQ_FILE=requirements.txt

if defined REQ_FILE (
    echo Checking dependencies...
    python -m pip show orjson >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Required dependencies may be missing.
        echo Installing project requirements from %REQ_FILE%...
        
        :: Optional: Upgrade pip silently
        python -m pip install --upgrade pip >nul 2>&1
        
        python -m pip install -r "%REQ_FILE%"
        if errorlevel 1 (
            echo.
            echo [ERROR] Dependency installation failed.
            pause
            exit /b 1
        )
        echo [SUCCESS] Dependencies installed.
    ) else (
        echo [OK] Dependencies are already installed.
    )
) else (
    echo [WARNING] No requirements.txt found. Skipping dependency installation.
)

echo.
echo Starting Contextor GUI...
echo.

python main.py --gui

pause
