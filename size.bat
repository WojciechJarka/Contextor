@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Get-Location).Path; $files=Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.py' -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\\(\.contextor|\.git|\.pytest_cache|\.venv|tests|__pycache__)(\\|$)' }; $bytes=($files | Measure-Object -Property Length -Sum).Sum; if ($null -eq $bytes) { $bytes=0 }; Write-Host ('Python files: {0}' -f $files.Count); Write-Host ('Total size:   {0:N2} MB' -f ($bytes / 1MB))"

echo.
pause