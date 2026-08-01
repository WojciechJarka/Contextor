
echo =========================================
echo Force push to GitHub
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
