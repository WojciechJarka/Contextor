@echo off
setlocal

echo =========================================
echo 1/3: Cleaning __pycache__ directories...
echo =========================================
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        echo Removing: %%d
        rd /s /q "%%d"
    )
)
echo Done.
echo.

echo =========================================
echo 2/4: Cleaning repo_generator OUTPUT...
echo =========================================
if exist "repo_generator\OUTPUT" (
    echo Removing repo_generator\OUTPUT...
    rd /s /q "repo_generator\OUTPUT"
    echo Done.
) else (
    echo OUTPUT folder not found, skipping.
)
echo.

echo =========================================
echo 3/4: Delete JSON files prompt
echo =========================================
set /p del_json="Do you want to delete all .json files in the project? (Y/N): "
if /i "%del_json%"=="Y" (
    echo Deleting .json files...
    del /s /q *.json 2>nul
    echo Done.
) else (
    echo Skipping .json deletion.
)
echo.

echo =========================================
echo 4/4: Force push to GitHub
echo =========================================
echo Staging all files...
git -c core.safecrlf=false add .

echo Committing changes...
git commit -m "Auto-commit: Cleanup and update"

echo Force pushing to remote repository...
git push -f

echo.
echo All operations completed!
pause
