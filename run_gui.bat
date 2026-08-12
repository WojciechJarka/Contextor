@echo off
setlocal
set "VENV_PYW=%~dp0.venv\Scripts\pythonw.exe"

if not exist "%VENV_PYW%" (
    echo [INFO] Project virtual environment is missing. Starting setup launcher...
    call "%~dp0run_contextor.bat"
    exit /b %errorlevel%
)

start "" /d "%~dp0" "%VENV_PYW%" "%~dp0main.py" --gui
