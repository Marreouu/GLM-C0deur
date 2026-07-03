# Script de désinstallation pour glm
# Ce script désinstalle glm et nettoie le PATH

Write-Host "Désinstallation de glm..." -ForegroundColor Green

# Désinstaller le package
Write-Host "Désinstallation du package glm..." -ForegroundColor Yellow
try {
    pip uninstall glm -y
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Avertissement : Le package n'a pas pu être désinstallé" -ForegroundColor Yellow
    }
    else {
        Write-Host "Package désinstallé avec succès" -ForegroundColor Green
    }
}
catch {
    Write-Host "Avertissement : Le package n'a pas pu être désinstallé" -ForegroundColor Yellow
}

# Vérifier si glm est encore accessible
Write-Host "Vérification de la désinstallation..." -ForegroundColor Yellow
try {
    $glmVersion = glm --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Avertissement : glm est encore accessible. Vérifiez votre PATH" -ForegroundColor Yellow
    }
    else {
        Write-Host "glm a été correctement désinstallé" -ForegroundColor Green
    }
}
catch {
    Write-Host "glm a été correctement désinstallé" -ForegroundColor Green
}

Write-Host ""
Write-Host "Désinstallation terminée !" -ForegroundColor Green
Write-Host "Si vous souhaitez réinstaller glm, utilisez : git clone https://github.com/Marreou/glm-coder-v1 && cd glm-coder-v1 && pip install -r requirements.txt && pip install ." -ForegroundColor Cyan