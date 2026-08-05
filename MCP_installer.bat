@echo off
setlocal enabledelayedexpansion

title Contextor MCP Server Environment Installer

echo =======================================================
echo        Contextor MCP Server Environment Installer
echo =======================================================
echo.

set "TARGET_MCP=1.0.0"

cd /d "%~dp0"
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
    echo Please install Python 3.10+ or set up WinPython.
    pause
    exit /b 1
)

echo [INFO] Python interpreter found: "%PYTHON_EXE%"
echo.

:: =======================================================
:: 2/3: Checking mcp version
:: =======================================================
echo [2/3] Checking mcp version...

set "INSTALLED_VER="
"%PYTHON_EXE%" -c "import importlib.metadata; print(importlib.metadata.version('mcp'))" > "%TEMP%\mcp_ver.tmp" 2>nul

if exist "%TEMP%\mcp_ver.tmp" (
    set /p INSTALLED_VER=<"%TEMP%\mcp_ver.tmp"
    del "%TEMP%\mcp_ver.tmp" 2>nul
)

if "!INSTALLED_VER!"=="" (
    powershell -Command "Write-Host '[WARNING] mcp is NOT installed in this Python environment.' -ForegroundColor Red"
    echo mcp^>=%TARGET_MCP% is required for running the MCP Server.
    echo.
    set /p "install_choice=Do you want to install mcp now? (Y/N): "
    if /i "!install_choice!"=="Y" (
        echo [INFO] Installing mcp...
        "%PYTHON_EXE%" -m pip install mcp^>=%TARGET_MCP%
        if errorlevel 1 (
            echo [ERROR] Failed to install mcp.
            pause
            exit /b 1
        )
        echo [SUCCESS] mcp installed.
    ) else (
        echo [INFO] Skipping mcp installation.
    )
) else (
    powershell -Command "Write-Host '[INFO] Detected mcp version !INSTALLED_VER!.' -ForegroundColor Green"
    echo.
    set /p "downgrade_choice=Do you want to upgrade/reinstall mcp? (Y/N): "
    if /i "!downgrade_choice!"=="Y" (
        echo [INFO] Reinstalling mcp...
        "%PYTHON_EXE%" -m pip install mcp --upgrade
        if errorlevel 1 (
            echo [ERROR] Failed to reinstall mcp.
            pause
            exit /b 1
        )
        echo [SUCCESS] mcp reinstalled successfully.
    ) else (
        echo [INFO] Skipping mcp reinstallation.
    )
)
echo.

:: =======================================================
:: 3/3: Reinstalling Contextor in editable mode
:: =======================================================
echo [3/3] Linking contextor-mcp script...
echo.
set /p "link_choice=Do you want to run pip install -e . to link the new contextor-mcp script? (Y/N): "
if /i "!link_choice!"=="Y" (
    "%PYTHON_EXE%" -m pip install -e .
    echo [SUCCESS] Linked successfully.
) else (
    echo [INFO] Skipping linking.
)
echo.

echo =======================================================
echo        Installation Complete
echo =======================================================
pause
exit /b 0
