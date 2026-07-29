@echo off
setlocal

echo ==========================================
echo     Contextor - GUI Launcher
echo ==========================================
echo.

cd /d "%~dp0"
set PYTHONPATH=%~dp0

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not available in PATH.
    pause
    exit /b 1
)

:: Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...

    python -m venv venv

    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

:: Install dependencies once
if exist requirements.txt (
    if not exist "venv\.installed" (
        echo [INFO] Installing dependencies...

        python -m pip install --upgrade pip
        python -m pip install -r requirements.txt

        if errorlevel 1 (
            echo [ERROR] Failed to install dependencies.
            pause
            exit /b 1
        )

        type nul > "venv\.installed"

        echo [SUCCESS] Dependencies installed.
    )
)

:: Start application
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
