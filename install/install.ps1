# ============================================================
#  Installateur de glm (glmcode)
#
#  A executer par la personne qui recoit le code source :
#    1. Verifie Python 3.11+
#    2. Installe les dependances (requirements.txt)
#    3. Cree un lanceur "glm" et l'ajoute au PATH utilisateur
#       -> la commande "glm" devient utilisable depuis n'importe ou
#
#  IMPORTANT : ne pas deplacer / supprimer le dossier du projet
#  apres l'installation (le lanceur pointe vers ce dossier).
# ============================================================

$ErrorActionPreference = "Stop"

function Write-Step { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "    $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "    $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "    $m" -ForegroundColor Red }

# --- Racine du projet (dossier parent de ce script) ---------
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host ""
Write-Host "  Installation de glm" -ForegroundColor Magenta
Write-Host "  Source : $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# --- 1. Verifier Python -------------------------------------
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

# --- 2. Installer les dependances ---------------------------
Write-Step "Installation des dependances (requirements.txt)"
& $python -m pip install --upgrade pip *> $null
& $python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Err "Echec de l'installation des dependances"
    exit 1
}
Write-Ok "Dependances installees"

# --- 3. Creer le lanceur "glm" ------------------------------
Write-Step "Creation de la commande glm"
$BinDir = Join-Path $ProjectRoot "bin"
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir | Out-Null }

# Chemin absolu de l'interpreteur Python (pour ne pas dependre d'un alias)
$pythonExe = (& $python -c "import sys; print(sys.executable)").Trim()

# Lanceur .cmd : ajoute la racine au PYTHONPATH puis lance le module glmcode
$launcher = @"
@echo off
set "PYTHONPATH=$ProjectRoot;%PYTHONPATH%"
"$pythonExe" -m glmcode %*
"@
$launcherPath = Join-Path $BinDir "glm.cmd"
Set-Content -Path $launcherPath -Value $launcher -Encoding ASCII
Write-Ok "Lanceur cree : $launcherPath"

# --- 4. Ajouter le dossier bin au PATH utilisateur ----------
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

# --- 4b. Installer la config globale (~/.glmcode/config.toml)
Write-Step "Installation de la configuration"
$cfgDir = Join-Path $env:USERPROFILE ".glmcode"
New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null
$cfgDst = Join-Path $cfgDir "config.toml"
$cfgSrc = Join-Path $ProjectRoot "config.toml"
if (-not (Test-Path $cfgSrc)) { $cfgSrc = Join-Path $ProjectRoot "config.example.toml" }
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

# --- 5. Verification ----------------------------------------
Write-Step "Verification"
try {
    & "$launcherPath" --version
    if ($LASTEXITCODE -eq 0) { Write-Ok "glm operationnel" } else { throw "code $LASTEXITCODE" }
} catch {
    Write-Warn "La verification n'a pas abouti dans cette session."
    Write-Warn "Ouvrez un NOUVEAU terminal puis tapez : glm --version"
}

Write-Host ""
Write-Host "  Installation terminee !" -ForegroundColor Green
Write-Host "  Ouvrez un NOUVEAU terminal et tapez : glm" -ForegroundColor Green
Write-Host "  (ne deplacez pas ce dossier, le lanceur pointe dessus)" -ForegroundColor DarkGray
Write-Host ""
