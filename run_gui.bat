@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo     Contextor - GUI Launcher
echo ==========================================
echo.

cd /d "%~dp0"
set PYTHONPATH=%~dp0

:: 1. Detect Python interpreter
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not recognized as an internal or external command.
    echo Make sure Python is installed and added to your system PATH.
    pause
    exit /b 1
)

:: 2. Install requirements
if exist requirements.txt (
    echo.
    echo Checking and installing dependencies...
    
    python -m pip install -r requirements.txt

    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install dependencies.
        echo Please check your pip configuration or internet connection.
        pause
        exit /b 1
    )

    echo [SUCCESS] Dependencies are ready.
) else (
    echo.
    echo [WARNING] requirements.txt not found.
    echo Continuing without dependency installation...
)

:: 3. Start Contextor GUI
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
