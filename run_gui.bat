@echo off
REM ==========================================
REM Repo Guardian - GUI launcher
REM ==========================================

cd /d %~dp0

REM Dodajemy katalog nadrzędny do PYTHONPATH, aby importy typu "from repo_guardian..." działały
set PYTHONPATH=%~dp0..

REM Uruchamiamy plik main.py bezpośrednio przy użyciu Twojego interpretera
"C:\SpiralProphet\python\WPy64-31090\python-3.10.9.amd64\python.exe" "main.py" --gui

pause
