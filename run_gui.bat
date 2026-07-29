@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo     Contextor - GUI Launcher
echo ==========================================
echo.

cd /d "%~dp0"
set PYTHONPATH=%~dp0..

:: 1. Detect Python interpreter
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not recognized as an internal or external command.
    echo Make sure Python is installed and added to your system PATH.
    pause
    exit /b 1
)

:: 2. Detect if orjson is installed
python -c "import orjson" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] The required Python package 'orjson' is not installed.
    echo This package is strictly necessary for Contextor to operate.
    echo.
    set /p choice="Would you like to install 'orjson' now using pip? (Y/N): "
    if /i "!choice!"=="Y" (
        echo.
        echo Installing orjson...
        python -m pip install orjson
        if errorlevel 1 (
            echo.
            echo [ERROR] Failed to install orjson. Please check your internet connection or pip configuration.
            pause
            exit /b 1
        )
        echo [SUCCESS] orjson installed successfully!
    ) else (
        echo.
        echo [ABORT] Cannot proceed without orjson. Exiting...
        pause
        exit /b 1
    )
)

echo.
echo Starting Contextor GUI...
python main.py --gui

pause
