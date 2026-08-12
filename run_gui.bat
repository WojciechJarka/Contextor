@echo off
REM ==========================================
REM Repo Guardian - GUI launcher
REM ==========================================

cd /d "%~dp0"

echo ==========================================
echo Repo Guardian - GUI launcher
echo ==========================================
echo.
echo BAT STARTED
echo Working directory:
cd
echo.
echo Python:
"C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" --version
echo.

set "PYTHONPATH=%~dp0.."

echo PYTHONPATH=%PYTHONPATH%
echo.
echo Press any key to START GUI...
pause

echo.
echo Starting Python...
echo.

"C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" -u "main.py" --gui > "%~dp0gui_debug.txt" 2>&1

echo.
echo PYTHON EXIT CODE: %ERRORLEVEL%
echo.
echo ==========================================
echo Contents of gui_debug.txt:
echo ==========================================
type "%~dp0gui_debug.txt"
echo.
echo ==========================================
echo END
echo ==========================================
pause