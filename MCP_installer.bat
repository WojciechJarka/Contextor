@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 1
if exist "%CD%\.contextor_py315_cutover.guard" (
    echo CONTEXTOR_CUTOVER_ACTIVE
    exit /b 86
)
endlocal
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
:: 1/2: Selecting the project-local interpreter
:: =======================================================
echo [1/2] Selecting the project-local interpreter...

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

:PYTHON_FOUND
if not exist "%PYTHON_EXE%" (
    echo [ERROR] The local Contextor .venv must be created explicitly before running this installer.
    pause
    exit /b 1
)

echo [INFO] Python interpreter found: "%PYTHON_EXE%"
echo.

:: =======================================================
:: 2/2: Checking mcp version
:: =======================================================
echo [2/2] Checking mcp version...

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

echo =======================================================
echo        Installation Complete
echo =======================================================
pause
exit /b 0
