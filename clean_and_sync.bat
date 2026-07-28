@echo off
echo ========================================================
echo     Repo Guardian - Clean and Sync Script
echo ========================================================
echo.

echo [1/3] Deleting ALL .json files across the repository...
del /s /q *.json

echo.
echo [2/3] Deleting ALL __pycache__ directories...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo.
echo [3/3] Committing changes and forcing sync to GitHub...
git -c core.safecrlf=false add -A
git commit -m "Auto-clean: Removed JSONs and pycache, forced sync"
git push --force

echo.
echo ========================================================
echo     DONE. Repository cleaned and forcibly pushed.
echo ========================================================
pause
