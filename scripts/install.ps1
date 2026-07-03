# Script d'installation pour glm
# Ce script installe glm dans le PATH et configure les dépendances

Write-Host "Installation de glm..." -ForegroundColor Green

# Vérifier si Python est installé
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python n'est pas pas installé ou n'est pas dans le PATH"
    }
    Write-Host "Python trouvé : $pythonVersion" -ForegroundColor Yellow
}
catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Veuillez installer Python 3.11 ou supérieur depuis https://python.org" -ForegroundColor Yellow
    exit 1
}

# Vérifier la version de Python
try {
    $majorVersion = [int]($pythonVersion -split ' ')[1].Split('.')[0]
    $minorVersion = [int]($pythonVersion -split ' ')[1].Split('.')[1]
    
    if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 11)) {
        throw "Python 3.11 ou supérieur est requis. Version actuelle : $pythonVersion"
    }
}
catch {
    Write-Host "Erreur : Impossible de vérifier la version Python" -ForegroundColor Red
    exit 1
}

# Cloner le dépôt GitHub
Write-Host "Clonage du dépôt GitHub..." -ForegroundColor Yellow
try {
    $repoUrl = "https://github.com/Marreou/glm-coder-v1"
    $clonePath = Join-Path $env:TEMP "glm-code"
    
    if (Test-Path $clonePath) {
        Remove-Item $clonePath -Recurse -Force
    }
    
    git clone $repoUrl $clonePath
    if ($LASTEXITCODE -ne 0) {
        throw "Le clonage du dépôt a échoué"
    }
    Write-Host "Dépôt cloné avec succès" -ForegroundColor Green
}
catch {
    Write-Host "Erreur lors du clonage : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Installer les dépendances
Write-Host "Installation des dépendances..." -ForegroundColor Yellow
try {
    Set-Location $clonePath
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "L'installation des dépendances a échoué"
    }
    Write-Host "Dépendances installées avec succès" -ForegroundColor Green
}
catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Installer le package
Write-Host "Installation du package glm..." -ForegroundColor Yellow
try {
    pip install .
    if ($LASTEXITCODE -ne 0) {
        throw "L'installation du package a échoué"
    }
    Write-Host "Package installé avec succès" -ForegroundColor Green
}
catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Vérifier si glm est accessible
Write-Host "Vérification de l'installation..." -ForegroundColor Yellow
try {
    $glmVersion = glm --version
    if ($LASTEXITCODE -ne 0) {
        throw "glm n'est pas accessible après l'installation"
    }
    Write-Host "glm est accessible : $glmVersion" -ForegroundColor Green
}
catch {
    Write-Host "Erreur : $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Veuillez vérifier votre configuration PATH" -ForegroundColor Yellow
    exit 1
}

# Nettoyer le répertoire temporaire
Write-Host "Nettoyage..." -ForegroundColor Yellow
try {
    Set-Location $env:TEMP
    Remove-Item "glm-code" -Recurse -Force
    Write-Host "Nettoyage terminé" -ForegroundColor Green
}
catch {
    Write-Host "Avertissement : Impossible de nettoyer le répertoire temporaire" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Installation terminée !" -ForegroundColor Green
Write-Host "Vous pouvez maintenant utiliser la commande 'glm' dans votre terminal" -ForegroundColor Yellow