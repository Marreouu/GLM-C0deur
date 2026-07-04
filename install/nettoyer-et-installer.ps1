# ============================================================
#  Remise a zero + installation propre de glm
#
#  A EXECUTER SUR LA MACHINE OU glm EST CASSE.
#  Ce script :
#    1. Desinstalle glmcode de TOUS les Python trouves
#    2. Supprime tous les lanceurs glm residuels
#    3. Telecharge et reinstalle proprement glm depuis GitHub
#
#  USAGE :
#    irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.ps1" | iex
# ============================================================

# On continue meme si une etape de nettoyage echoue
$ErrorActionPreference = "Continue"

function Write-Step { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "    $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "    $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "    $m" -ForegroundColor Red }

# --- Configuration ---
$RepoUrl = "https://github.com/Marreouu/GLM-C0deur"
$InstallDir = Join-Path $env:LOCALAPPDATA "glm-code"
$TempDir = Join-Path $env:TEMP "glm-install"

Write-Host ""
Write-Host "  Remise a zero de glm" -ForegroundColor Magenta
Write-Host "  Source : $RepoUrl" -ForegroundColor DarkGray
Write-Host ""

# ------------------------------------------------------------
# 0. Recenser tous les interpreteurs Python de la machine
# ------------------------------------------------------------
Write-Step "Recherche des Python installes"
$pythons = New-Object System.Collections.Generic.List[string]

# via le lanceur "py -0p"
try {
    $lines = & py -0p 2>$null
    foreach ($l in $lines) {
        if ($l -match '([A-Za-z]:\\[^\r\n]*python\.exe)') { $pythons.Add($Matches[1]) }
    }
} catch { }

# via "where python"
try {
    & where.exe python 2>$null | ForEach-Object {
        if ($_ -match 'python\.exe$') { $pythons.Add($_.Trim()) }
    }
} catch { }

# le python courant
try {
    $cur = (& python -c "import sys;print(sys.executable)" 2>$null)
    if ($cur) { $pythons.Add($cur.Trim()) }
} catch { }

$pythons = $pythons | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique
if ($pythons.Count -eq 0) {
    Write-Err "Aucun Python trouve. Installez Python 3.11+ depuis https://python.org"
    exit 1
}
foreach ($p in $pythons) { Write-Ok $p }

# ------------------------------------------------------------
# 1. Desinstaller glmcode de chaque Python
# ------------------------------------------------------------
Write-Step "Desinstallation de glmcode (tous les Python)"
foreach ($py in $pythons) {
    & $py -m pip uninstall glmcode -y 2>$null | Out-Null
    & $py -m pip uninstall glm -y 2>$null | Out-Null
}
Write-Ok "Paquets glmcode/glm desinstalles"

# ------------------------------------------------------------
# 2. Supprimer tous les lanceurs glm residuels
# ------------------------------------------------------------
Write-Step "Suppression des lanceurs glm residuels"
$scriptDirs = New-Object System.Collections.Generic.List[string]
foreach ($py in $pythons) {
    foreach ($scheme in @("", "nt_user")) {
        try {
            $code = if ($scheme) { "import sysconfig;print(sysconfig.get_path('scripts','$scheme'))" }
                    else         { "import sysconfig;print(sysconfig.get_path('scripts'))" }
            $d = (& $py -c $code 2>$null)
            if ($d) { $scriptDirs.Add($d.Trim()) }
        } catch { }
    }
}
$scriptDirs = $scriptDirs | Where-Object { $_ } | Select-Object -Unique

# On balaie TOUS les dossiers du PATH (User + Machine) + les dossiers de
# scripts Python, et on supprime tout lanceur glm.*
$pathDirs = New-Object System.Collections.Generic.List[string]
foreach ($scope in @("User", "Machine")) {
    $pv = [Environment]::GetEnvironmentVariable("Path", $scope)
    if ($pv) { ($pv -split ';') | ForEach-Object { if ($_) { $pathDirs.Add($_.Trim()) } } }
}
foreach ($d in $scriptDirs) { $pathDirs.Add($d) }
$pathDirs = $pathDirs | Where-Object { $_ } | Select-Object -Unique

$removed = 0
$launcherNames = @("glm.ps1", "glm.cmd", "glm.bat", "glm.exe", "glm-script.py")
foreach ($d in $pathDirs) {
    # On ne supprime pas notre futur lanceur
    if ($d.TrimEnd('\') -ieq $InstallDir.TrimEnd('\')) { continue }
    
    foreach ($name in $launcherNames) {
        $f = Join-Path $d $name
        if (Test-Path $f) {
            Remove-Item $f -Force -ErrorAction SilentlyContinue
            if (-not (Test-Path $f)) { 
                $removed++; 
                Write-Ok "supprime : $f" 
            } else { 
                Write-Warn "impossible de supprimer : $f" 
            }
        }
    }
}
if ($removed -eq 0) { Write-Ok "aucun lanceur residuel" }

# supprimer l'ancien dossier d'installation s'il existe
if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host ""
Write-Host "  Nettoyage termine. Installation propre..." -ForegroundColor Magenta
Write-Host ""

# ------------------------------------------------------------
# 3. Telecharger le depot GitHub
# ------------------------------------------------------------
Write-Step "Telechargement du depot GitHub"
try {
    # Supprimer les anciens telechargements
    if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue }
    
    # Telecharger avec git
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

# ------------------------------------------------------------
# 4. Choisir un Python 3.11+ pour l'installation propre
# ------------------------------------------------------------
$ErrorActionPreference = "Stop"
Write-Step "Selection d'un Python 3.11+"
$python = $null
foreach ($py in $pythons) {
    try {
        $v = (& $py -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null).Trim()
        $mj = [int]$v.Split('.')[0]; $mn = [int]$v.Split('.')[1]
        if ($mj -gt 3 -or ($mj -eq 3 -and $mn -ge 11)) { $python = $py; break }
    } catch { }
}
if (-not $python) {
    Write-Err "Aucun Python 3.11+ trouve. Installez-le depuis https://python.org"
    exit 1
}
Write-Ok "Python retenu : $python ($($python --version 2>&1))"

# ------------------------------------------------------------
# 5. Installer les dependances
# ------------------------------------------------------------
Write-Step "Installation des dependances"
Set-Location $TempDir
& $python -m pip install --upgrade pip *> $null
& $python -m pip install -r "requirements.txt"
if ($LASTEXITCODE -ne 0) { Write-Err "Echec de l'installation des dependances"; exit 1 }
Write-Ok "Dependances installees"

# ------------------------------------------------------------
# 6. Deplacer vers le dossier d'installation final
# ------------------------------------------------------------
Write-Step "Installation finale"
Move-Item $TempDir $InstallDir -Force
Write-Ok "Installe dans : $InstallDir"

# ------------------------------------------------------------
# 7. Creer le lanceur glm unique
# ------------------------------------------------------------
Write-Step "Creation de la commande glm"
$BinDir = Join-Path $InstallDir "bin"
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

# Chemin absolu de l'interpreteur Python
$pythonExe = (& $python -c "import sys; print(sys.executable)").Trim()

$launcher = @"
@echo off
set "PYTHONPATH=$InstallDir;%PYTHONPATH%"
"$pythonExe" -m glmcode %*
"@
$launcherPath = Join-Path $BinDir "glm.cmd"
Set-Content -Path $launcherPath -Value $launcher -Encoding ASCII
Write-Ok "Lanceur cree : $launcherPath"

# ------------------------------------------------------------
# 8. Ajouter bin au PATH utilisateur (une seule fois)
# ------------------------------------------------------------
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
$env:Path = "$env:Path;$BinDir"

# ------------------------------------------------------------
# 9. Installer la config globale (~/.glmcode/config.toml)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# 10. Verification
# ------------------------------------------------------------
Write-Step "Verification"
try {
    & "$launcherPath" --version
    if ($LASTEXITCODE -eq 0) { Write-Ok "glm operationnel" } else { throw "code $LASTEXITCODE" }
} catch {
    Write-Warn "Verification non aboutie dans cette session."
    Write-Warn "Ouvrez un NOUVEAU terminal puis tapez : glm --version"
}

# Nettoyer les fichiers temporaires
Write-Step "Nettoyage"
Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "  Termine ! Une seule commande glm est maintenant installee." -ForegroundColor Green
Write-Host "  Ouvrez un NOUVEAU terminal et tapez : glm" -ForegroundColor Green
Write-Host "  Installe dans : $InstallDir" -ForegroundColor DarkGray
Write-Host ""