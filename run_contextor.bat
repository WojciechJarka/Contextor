@echo off
setlocal

rem Delayed expansion is deliberately NOT enabled.
rem
rem It would treat "!" as a variable delimiter and silently strip it from
rem every path, so a project stored under e.g. C:\!Projects\... became
rem C:\Projects\... - the directory change failed, the virtual
rem environment was never activated, and Contextor ran on whatever Python
rem happened to be on PATH instead.

echo ==========================================
echo        Contextor Launcher
echo ==========================================
echo.

cd /d "%~dp0"
if errorlevel 1 goto no_project_dir

set "PROJECT_DIR=%CD%"
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PY%" goto create_venv
goto check_deps


:create_venv
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo [INFO] Creating virtual environment ^(.venv^)...

set "PYTHON_EXE="

:: 1. Check the explicit CPython 3.15 installation.
if exist "C:\Python315\python.exe" (
    "C:\Python315\python.exe" -I -B -c "import sys; sys.exit(0 if sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=C:\Python315\python.exe"
        goto :PYTHON_FOUND
    )
)

:: 2. Accept PATH Python only after the same interpreter validation.
python -I -B -c "import sys; sys.exit(0 if sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

:PYTHON_FOUND
if "%PYTHON_EXE%"=="" (
    goto no_python
)

echo [INFO] Using python: "%PYTHON_EXE%"
"%PYTHON_EXE%" -m venv "%VENV_DIR%"
if errorlevel 1 goto venv_failed

if not exist "%VENV_PY%" goto venv_failed

echo [SUCCESS] Virtual environment created.
echo.


:check_deps
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo Checking dependencies...

"%VENV_PY%" -c "import orjson, watchdog, mcp, fastmcp" >nul 2>&1
if errorlevel 1 goto install_deps

echo [OK] Dependencies are already installed.
goto check_ruff


:install_deps
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo [WARNING] Required dependencies are missing.
echo Installing project requirements...

"%VENV_PY%" -m pip install --upgrade pip >nul 2>&1

if not exist "%PROJECT_DIR%\requirements.txt" goto no_requirements

"%VENV_PY%" -m pip install -r "%PROJECT_DIR%\requirements.txt"
if errorlevel 1 goto install_failed

echo [SUCCESS] Dependencies installed.
echo.
goto check_ruff


:check_ruff
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo Checking Ruff development tool...

"%VENV_PY%" -c "import importlib.metadata as m, re, sys; v=m.version('ruff'); p=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)',v); sys.exit(0 if p and tuple(map(int,p.groups())) >= (0,17,0) else 1)" >nul 2>&1
if errorlevel 1 goto install_ruff

if not exist "%VENV_DIR%\Scripts\ruff.exe" goto install_ruff

"%VENV_DIR%\Scripts\ruff.exe" --version >nul 2>&1
if errorlevel 1 goto install_ruff

echo [OK] Ruff >=0.17.0 is available.
goto check_backend_autostart


:install_ruff
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo [INFO] Installing Ruff into the project virtual environment...

"%VENV_PY%" -m pip install "ruff>=0.17.0"
if errorlevel 1 goto ruff_unavailable

if not exist "%VENV_DIR%\Scripts\ruff.exe" goto ruff_unavailable

"%VENV_DIR%\Scripts\ruff.exe" --version >nul 2>&1
if errorlevel 1 goto ruff_unavailable

echo [SUCCESS] Ruff installed and verified.
goto check_backend_autostart


:ruff_unavailable
echo [WARNING] Ruff is unavailable. Continuing without optional lint tooling.
goto check_backend_autostart


:check_backend_autostart
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo Checking MCP backend autostart...

"%VENV_PY%" -m contextor.mcp_backend_autostart status >nul 2>&1
if errorlevel 1 goto install_backend_autostart

echo [OK] MCP backend autostart is already configured.
goto check_backend


:install_backend_autostart
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo [INFO] Registering MCP backend autostart...

"%VENV_PY%" -m contextor.mcp_backend_autostart install >nul 2>&1
if errorlevel 1 goto backend_autostart_failed

echo [SUCCESS] MCP backend autostart registered.
goto check_backend


:check_backend
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo Checking MCP backend...

"%VENV_PY%" -m contextor backend status >nul 2>&1
if errorlevel 1 goto start_backend

echo [OK] MCP backend is already running.
goto start_gui


:start_backend
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo [INFO] Starting MCP backend...

"%VENV_PY%" -m contextor backend start >nul 2>&1
if errorlevel 1 goto backend_start_failed

echo [SUCCESS] MCP backend started.
goto start_gui


:start_gui
if exist "%PROJECT_DIR%\.contextor_py315_cutover.guard" goto cutover_blocked
echo.
echo Starting Contextor GUI...
echo.

rem The virtual environment interpreter is invoked directly rather than
rem through activate.bat, so a failed activation can never silently fall
rem back to the system Python.
"%VENV_PY%" "%PROJECT_DIR%\main.py" --gui
if errorlevel 1 goto gui_failed

exit /b 0


:cutover_blocked
echo CONTEXTOR_CUTOVER_ACTIVE
exit /b 86


:no_project_dir
echo [ERROR] Could not enter the project directory:
echo         %~dp0
pause
exit /b 1


:no_python
echo [ERROR] CPython 3.15 was not found or did not pass validation.
pause
exit /b 1


:venv_failed
echo [ERROR] Failed to create the virtual environment at:
echo         %VENV_DIR%
pause
exit /b 1


:no_requirements
echo [ERROR] requirements.txt not found in:
echo         %PROJECT_DIR%
pause
exit /b 1


:install_failed
echo.
echo [ERROR] Dependency installation failed.
pause
exit /b 1


:backend_autostart_failed
echo.
echo [ERROR] Failed to register the Contextor MCP backend autostart.
pause
exit /b 1


:backend_start_failed
echo.
echo [ERROR] Failed to start the Contextor MCP backend.
pause
exit /b 1


:gui_failed
echo.
echo [ERROR] Contextor exited with an error.
pause
exit /b 1
