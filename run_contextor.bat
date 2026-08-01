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

python --version >nul 2>&1
if errorlevel 1 goto no_python

python -m venv "%VENV_DIR%"
if errorlevel 1 goto venv_failed

if not exist "%VENV_PY%" goto venv_failed

echo [SUCCESS] Virtual environment created.
echo.


:check_deps
echo Checking dependencies...

"%VENV_PY%" -c "import orjson" >nul 2>&1
if errorlevel 1 goto install_deps

echo [OK] Dependencies are already installed.
goto start_gui


:install_deps
echo [WARNING] Required dependencies are missing.
echo Installing project requirements...

"%VENV_PY%" -m pip install --upgrade pip >nul 2>&1

if not exist "%PROJECT_DIR%\requirements.txt" goto no_requirements

"%VENV_PY%" -m pip install -r "%PROJECT_DIR%\requirements.txt"
if errorlevel 1 goto install_failed

echo [SUCCESS] Dependencies installed.


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

:gui_failed
echo.
echo [ERROR] Contextor exited with an error.
pause
exit /b 1
