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
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PY%" goto create_venv
goto check_deps


:create_venv
echo [INFO] Creating virtual environment ^(.venv^)...

set "PYTHON_EXE="

:: 1. Check embedded WinPython / SpiralProphet path
if exist "C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" (
    set "PYTHON_EXE=C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe"
    goto :PYTHON_FOUND
)

:: 2. Check system PATH
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

:: 3. Scan local directories (venv, .venv, WinPython)
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
    goto no_python
)

echo [INFO] Using python: "%PYTHON_EXE%"
"%PYTHON_EXE%" -m venv "%VENV_DIR%"
if errorlevel 1 goto venv_failed

if not exist "%VENV_PY%" goto venv_failed

echo [SUCCESS] Virtual environment created.
echo.


:check_deps
echo Checking dependencies...

"%VENV_PY%" -c "import orjson, watchdog, mcp, fastmcp" >nul 2>&1
if errorlevel 1 goto install_deps

echo [OK] Dependencies are already installed.
goto check_backend_autostart


:install_deps
echo [WARNING] Required dependencies are missing.
echo Installing project requirements...

"%VENV_PY%" -m pip install --upgrade pip >nul 2>&1

if not exist "%PROJECT_DIR%\requirements.txt" goto no_requirements

"%VENV_PY%" -m pip install -r "%PROJECT_DIR%\requirements.txt"
if errorlevel 1 goto install_failed

echo [SUCCESS] Dependencies installed.
echo.
goto check_backend_autostart


:check_backend_autostart
echo Checking MCP backend autostart...

"%VENV_PY%" -m contextor.mcp_backend_autostart status >nul 2>&1
if errorlevel 1 goto install_backend_autostart

echo [OK] MCP backend autostart is already configured.
goto check_backend


:install_backend_autostart
echo [INFO] Registering MCP backend autostart...

"%VENV_PY%" -m contextor.mcp_backend_autostart install >nul 2>&1
if errorlevel 1 goto backend_autostart_failed

echo [SUCCESS] MCP backend autostart registered.
goto check_backend


:check_backend
echo Checking MCP backend...

"%VENV_PY%" -m contextor backend status >nul 2>&1
if errorlevel 1 goto start_backend

echo [OK] MCP backend is already running.
goto start_gui


:start_backend
echo [INFO] Starting MCP backend...

"%VENV_PY%" -m contextor backend start >nul 2>&1
if errorlevel 1 goto backend_start_failed

echo [SUCCESS] MCP backend started.
goto start_gui


:start_gui
echo.
echo Starting Contextor GUI...
echo.

rem The virtual environment interpreter is invoked directly rather than
rem through activate.bat, so a failed activation can never silently fall
rem back to the system Python.
"%VENV_PY%" "%PROJECT_DIR%\main.py" --gui
if errorlevel 1 goto gui_failed

exit /b 0


:no_project_dir
echo [ERROR] Could not enter the project directory:
echo         %~dp0
pause
exit /b 1


:no_python
echo [ERROR] Python was not found.
echo Install Python 3.10+ and add it to your system PATH.
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