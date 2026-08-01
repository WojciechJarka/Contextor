@echo off
setlocal enabledelayedexpansion

title GUI Test Suite Environment Installer

echo =======================================================
echo        GUI Test Suite Environment Installer
echo =======================================================
echo.

set "TARGET_SETUPTOOLS=69.5.1"

echo [INFO] Working directory set to: %CD%
echo.

:: =======================================================
:: 1/3: Searching for Python interpreter
:: =======================================================
echo [1/3] Searching for Python interpreter...

set "PYTHON_EXE="

:: 1. Sprawdzanie wbudowanej ścieżki WinPython / SpiralProphet
if exist "C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" (
    set "PYTHON_EXE=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe"
    goto :PYTHON_FOUND
)

:: 2. Sprawdzanie zmiennej PATH
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

:: 3. Skanowanie lokalnych folderów (venv, .venv, WinPython)
for /d %%d in (venv .venv Python python WPy64*) do (
    if exist "%%d\Scripts\python.exe" (
        set "PYTHON_EXE=%%d\Scripts\python.exe"
        goto :PYTHON_FOUND
    )
    if exist "%%d\python.exe" (
        set "PYTHON_EXE=%%d\python.exe"
        goto :PYTHON_FOUND
    )
)

:PYTHON_FOUND
if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python interpreter not found in system PATH or standard directories.
    echo Please install Python 3.9+ or set up WinPython.
    pause
    exit /b 1
)

echo [INFO] Python interpreter found: "%PYTHON_EXE%"
echo.

:: =======================================================
:: 2/3: Checking setuptools version
:: =======================================================
echo [2/3] Checking setuptools version...

set "INSTALLED_VER="
"%PYTHON_EXE%" -c "import importlib.metadata; print(importlib.metadata.version('setuptools'))" > "%TEMP%\st_ver.tmp" 2>nul

if exist "%TEMP%\st_ver.tmp" (
    set /p INSTALLED_VER=<"%TEMP%\st_ver.tmp"
    del "%TEMP%\st_ver.tmp" 2>nul
)

if "!INSTALLED_VER!"=="" (
    powershell -Command "Write-Host '[WARNING] setuptools is NOT installed in this Python environment.' -ForegroundColor Red"
    echo setuptools==%TARGET_SETUPTOOLS% is required for running the full test suite in the main window.
    echo.
    set /p "install_choice=Do you want to install setuptools==%TARGET_SETUPTOOLS% now? (Y/N): "
    if /i "!install_choice!"=="Y" (
        echo [INFO] Installing setuptools==%TARGET_SETUPTOOLS%...
        "%PYTHON_EXE%" -m pip install setuptools==%TARGET_SETUPTOOLS%
        if errorlevel 1 (
            echo [ERROR] Failed to install setuptools.
            pause
            exit /b 1
        )
        echo [SUCCESS] setuptools==%TARGET_SETUPTOOLS% installed.
    ) else (
        echo [INFO] Skipping setuptools installation.
    )
) else if not "!INSTALLED_VER!"=="%TARGET_SETUPTOOLS%" (
    powershell -Command "Write-Host '[WARNING] Detected setuptools version !INSTALLED_VER!.' -ForegroundColor Red"
    powershell -Command "Write-Host 'Version %TARGET_SETUPTOOLS% is required for running the full test suite in the main window.' -ForegroundColor Red"
    echo.
    set /p "downgrade_choice=Do you want to downgrade/change setuptools from !INSTALLED_VER! to %TARGET_SETUPTOOLS%? (Y/N): "
    if /i "!downgrade_choice!"=="Y" (
        echo [INFO] Installing setuptools==%TARGET_SETUPTOOLS%...
        "%PYTHON_EXE%" -m pip install setuptools==%TARGET_SETUPTOOLS% --force-reinstall
        if errorlevel 1 (
            echo [ERROR] Failed to change setuptools version.
            pause
            exit /b 1
        )
        echo [SUCCESS] setuptools successfully set to %TARGET_SETUPTOOLS%.
    ) else (
        echo [INFO] Keeping current setuptools version !INSTALLED_VER!.
    )
) else (
    echo [OK] Correct setuptools version !INSTALLED_VER! is already installed.
)
echo.

:: =======================================================
:: 3/3: Checking dependencies (requirements.txt / orjson)
:: =======================================================
echo [3/3] Checking project dependencies...

if exist "Requirements.txt" set "REQ_FILE=Requirements.txt"
if exist "requirements.txt" set "REQ_FILE=requirements.txt"

if defined REQ_FILE (
    "%PYTHON_EXE%" -m pip show orjson >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Required dependencies may be missing.
        echo Installing project requirements from %REQ_FILE%...
        "%PYTHON_EXE%" -m pip install -r "%REQ_FILE%"
        if errorlevel 1 (
            echo [ERROR] Dependency installation failed.
            pause
            exit /b 1
        )
        echo [SUCCESS] Dependencies installed successfully.
    ) else (
        echo [OK] Dependencies are already satisfied.
    )
) else (
    echo [WARNING] No requirements.txt found. Skipping requirements check.
)

echo.
echo =======================================================
echo        Environment Check Completed Successfully
echo =======================================================
echo.

set /p "run_gui=Do you want to start the GUI application now? (Y/N): "
if /i "!run_gui!"=="Y" (
    echo.
    echo Starting GUI...
    if exist "main.py" (
        "%PYTHON_EXE%" main.py --gui
    ) else (
        echo [ERROR] main.py not found in working directory.
    )
)

pause