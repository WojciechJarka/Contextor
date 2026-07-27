# ==============================================================================
# FinalCleaner.ps1
# Wersja 17.1 - Ulepszona obsługa elementow python
# ==============================================================================

# --- KONFIGURACJA ---
$reposToClean = @(
    "C:\SpiralProphet",
    "C:\Users\DafoO\Desktop\SpiralProphet",
    "C:\AgentOrchestrator\project_repo",
    "C:\Temp\SpiralProphetRepo"
)

# --- FUNKCJE ---
function Clean-Repo {
    param(
        [string]$RepoPath
    )
    Write-Host "`nCzyszcze repozytorium: $RepoPath" -ForegroundColor Green
    
    if (-not (Test-Path $RepoPath)) {
        Write-Host "Sciezka '$RepoPath' nie istnieje. Pomijam." -ForegroundColor Red
        return
    }

    # --- ZMIANA: usuwamy sortowanie, żeby katalog .git był traktowany normalnie ---
    $items = @(Get-ChildItem -Path $RepoPath -Force -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)

    $itemsToDelete = $items | Where-Object {
        $fullPath = $_.FullName
        $name = $_.Name

        # --- Wyjatki ---
        # 1. Pomijanie wszystkiego, co zawiera 'python' w nazwie lub sciezce
        if ($fullPath -match "(?i)python" -or $name -match "(?i)python") {
            Write-Host "Pomijam: '$fullPath' - folder/plik python-related." -ForegroundColor Cyan
            return $false
        }

        # 2. Pomijanie 'spiralprophet.ico'
        if ($name -eq "spiralprophet.ico") {
            Write-Host "Pomijam: '$fullPath'." -ForegroundColor Cyan
            return $false
        }

        # Reszta zostaje usunieta (teraz również .git nie jest pomijany)
        return $true
    }

    if ($itemsToDelete.Count -gt 0) {
        $itemsToDelete | ForEach-Object {
            try {
                Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction Stop
                Write-Host "Usunieto: $_.FullName" -ForegroundColor Red
            }
            catch {
                Write-Host "Blad: Nie mozna usunac '$($_.FullName)'. Prawdopodobnie jest zablokowany." -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "Brak elementow do usuniecia." -ForegroundColor Green
    }
}

# --- WYKONANIE GLOWNEJ LOGIKI ---
Write-Host "=== Rozpoczynam czyszczenie lokalnych repozytoriow ===" -ForegroundColor Cyan
Write-Host "Prosze czekac cierpliwie na zakonczenie operacji..." -ForegroundColor Yellow

foreach ($repo in $reposToClean) {
    Clean-Repo -RepoPath $repo
}

Write-Host "`n=== Proces czyszczenia wszystkich repozytoriow zakonczony ===" -ForegroundColor Cyan
