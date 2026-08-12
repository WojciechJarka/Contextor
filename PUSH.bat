@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo =========================================
echo Commit and force push to GitHub
echo =========================================

for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if not defined BRANCH (
    echo ERROR: Git is in detached HEAD state.
    goto :failed
)

echo Staging all tracked, new, and deleted files...
git -c core.safecrlf=false add -A
if errorlevel 1 goto :failed

git diff --cached --quiet
if errorlevel 1 (
    set "COMMIT_MESSAGE=Auto-commit: Cleanup and update"
    if not "%~1"=="" set "COMMIT_MESSAGE=%~1"
    echo Committing changes on %BRANCH%...
    git commit -m "!COMMIT_MESSAGE!"
    if errorlevel 1 goto :failed
) else (
    echo No staged changes to commit.
)

echo.
echo Remote branch: origin/%BRANCH%
echo This will overwrite the remote branch with the local %BRANCH% history.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto :cancelled

git push --force origin "HEAD:%BRANCH%"
if errorlevel 1 goto :failed

echo.
echo Commit and push completed successfully.
pause
exit /b 0

:cancelled
echo Push cancelled. The local commit, if created, was kept.
pause
exit /b 2

:failed
echo.
echo ERROR: Operation failed. Push was not reported as successful.
pause
exit /b 1
