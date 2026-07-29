@echo off
setlocal

echo ==========================================
echo     Contextor - GUI Launcher
echo ==========================================
echo.

cd /d "%~dp0"

set PYTHONPATH=%~dp0

:: 1. Detect Python interpreter
where python >nul 2>&1

if errorlevel 1 (
    where py >nul 2>&1

    if errorlevel 1 (
        echo [ERROR] Python was not found.
        echo Install Python 3.9+ and enable PATH support.
        pause
        exit /b 1
    )

    set PY=py
) else (
    set PY=python
)

echo [INFO] Using Python:
%PY% --version

echo.

:: 2. Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...

    %PY% -m venv venv

    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo [SUCCESS] Virtual environment created.
)

:: 3. Activate virtual environment
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: 4. Install dependencies once
if exist requirements.txt (

    if not exist "venv\.installed" (

        echo.
        echo [INFO] Installing dependencies...

        python -m pip install --upgrade pip

        if errorlevel 1 (
            echo [ERROR] Failed to upgrade pip.
            pause
            exit /b 1
        )

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

:: 5. Start Contextor GUI
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
