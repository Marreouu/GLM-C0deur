# ============================================================
#  Installateur de glm (glmcode)
#
#  Ce script telecharge et installe directement glm depuis GitHub :
#    1. Telecharge le depot depuis GitHub
#    2. Verifie Python 3.11+
#    3. Installe les dependances (requirements.txt)
#    4. Cree un lanceur "glm" et l'ajoute au PATH utilisateur
#       -> la commande "glm" devient utilisable depuis n'importe ou
#
#  USAGE : 
#    irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.ps1" | iex
# ============================================================

$ErrorActionPreference = "Stop"

function Write-Step { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "    $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "    $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "    $m" -ForegroundColor Red }

# --- Configuration ---
$RepoUrl = "https://github.com/Marreouu/GLM-C0deur"
$InstallDir = Join-Path $env:LOCALAPPDATA "glm-code"
$TempDir = Join-Path $env:TEMP "glm-install"

Write-Host ""
Write-Host "  Installation de glm" -ForegroundColor Magenta
Write-Host "  Source : $RepoUrl" -ForegroundColor DarkGray
Write-Host ""

# --- 1. Telecharger le depot GitHub -------------------------
Write-Step "Telechargement du depot GitHub"
try {
    # Supprimer les anciens telechargements
    if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue }
    
    # Telecharger avec git (plus rapide)
    & git clone $RepoUrl $TempDir
    if ($LASTEXITCODE -ne 0) {
        throw "Echec du clonage du depot"
    }
    Write-Ok "Depot telecharge avec succes"
}
catch {
    Write-Err "Echec du telechargement : $($_.Exception.Message)"
    Write-Err "Verifiez votre connexion Internet et l'URL du depot"
    exit 1
}

# --- 2. Verifier Python -------------------------------------
Write-Step "Verification de Python"
$python = $null
foreach ($cmd in @("python", "py")) {
    try {
        & $cmd --version *> $null
        if ($LASTEXITCODE -eq 0) { $python = $cmd; break }
    } catch { }
}
if (-not $python) {
    Write-Err "Python introuvable. Installez Python 3.11+ depuis https://python.org"
    Write-Err "(cochez 'Add Python to PATH' pendant l'installation)"
    exit 1
}

$verString = (& $python --version 2>&1).ToString().Split(' ')[1]
$major = [int]$verString.Split('.')[0]
$minor = [int]$verString.Split('.')[1]
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
    Write-Err "Python 3.11+ requis (version detectee : $verString)"
    exit 1
}
Write-Ok "Python $verString ($python)"

# --- 3. Installer les dependances ---------------------------
Write-Step "Installation des dependances"
Set-Location $TempDir
& $python -m pip install --upgrade pip *> $null
& $python -m pip install -r "requirements.txt"
if ($LASTEXITCODE -ne 0) {
    Write-Err "Echec de l'installation des dependances"
    exit 1
}
Write-Ok "Dependances installees"

# --- 4. Deplacer vers le dossier d'installation final --------
Write-Step "Installation finale"
Move-Item $TempDir $InstallDir -Force
Write-Ok "Installe dans : $InstallDir"

# --- 5. Creer le lanceur "glm" ------------------------------
Write-Step "Creation de la commande glm"
$BinDir = Join-Path $InstallDir "bin"
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir | Out-Null }

# Chemin absolu de l'interpreteur Python (pour ne pas dependre d'un alias)
$pythonExe = (& $python -c "import sys; print(sys.executable)").Trim()

# Lanceur .cmd : ajoute la racine au PYTHONPATH puis lance le module glmcode
$launcher = @"
@echo off
set "PYTHONPATH=$InstallDir;%PYTHONPATH%"
"$pythonExe" -m glmcode %*
"@
$launcherPath = Join-Path $BinDir "glm.cmd"
Set-Content -Path $launcherPath -Value $launcher -Encoding ASCII
Write-Ok "Lanceur cree : $launcherPath"

# --- 6. Ajouter le dossier bin au PATH utilisateur ----------
Write-Step "Ajout de glm au PATH"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
$already = ($userPath -split ';') | Where-Object { $_.TrimEnd('\') -ieq $BinDir.TrimEnd('\') }
if ($already) {
    Write-Ok "Deja dans le PATH : $BinDir"
} else {
    $newPath = if ($userPath.TrimEnd(';')) { "$($userPath.TrimEnd(';'));$BinDir" } else { $BinDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Ok "Ajoute au PATH : $BinDir"
}
# Disponible aussi dans la session courante
$env:Path = "$env:Path;$BinDir"

# --- 7. Installer la config globale (~/.glmcode/config.toml)
Write-Step "Installation de la configuration"
$cfgDir = Join-Path $env:USERPROFILE ".glmcode"
New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null
$cfgDst = Join-Path $cfgDir "config.toml"
$cfgSrc = Join-Path $InstallDir "config.toml"
if (-not (Test-Path $cfgSrc)) { $cfgSrc = Join-Path $InstallDir "config.example.toml" }
if (Test-Path $cfgSrc) {
    if (Test-Path $cfgDst) {
        Write-Ok "Config deja presente : $cfgDst (conservee)"
    } else {
        Copy-Item $cfgSrc $cfgDst -Force
        Write-Ok "Config installee : $cfgDst"
    }
} else {
    Write-Warn "Aucun config.toml/config.example.toml a copier"
}

# --- 8. Verification ----------------------------------------
Write-Step "Verification"
try {
    & "$launcherPath" --version
    if ($LASTEXITCODE -eq 0) { Write-Ok "glm operationnel" } else { throw "code $LASTEXITCODE" }
} catch {
    Write-Warn "La verification n'a pas abouti dans cette session."
    Write-Warn "Ouvrez un NOUVEAU terminal puis tapez : glm --version"
}

# --- 9. Nettoyer les fichiers temporaires -------------------
Write-Step "Nettoyage"
Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "  Installation terminee !" -ForegroundColor Green
Write-Host "  Ouvrez un NOUVEAU terminal et tapez : glm" -ForegroundColor Green
Write-Host "  Installe dans : $InstallDir" -ForegroundColor DarkGray
Write-Host ""