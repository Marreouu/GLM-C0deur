# ============================================================
#  Désinstallateur de glm (glmcode)
#
#  Ce script désinstalle complètement glm :
#    1. Désinstalle glmcode de TOUS les Python trouvés
#    2. Supprime tous les lanceurs glm résiduels
#    3. Supprime le dossier d'installation
#    4. Supprime la configuration
#
#  USAGE :
#    irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/uninstall.ps1" | iex
# ============================================================

$ErrorActionPreference = "Stop"

function Write-Step { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "    $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "    $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "    $m" -ForegroundColor Red }

# --- Configuration ---
$InstallDir = Join-Path $env:LOCALAPPDATA "glm-code"
$ConfigDir = Join-Path $env:USERPROFILE ".glmcode"

Write-Host ""
Write-Host "  Désinstallation de glm" -ForegroundColor Magenta
Write-Host ""

# ------------------------------------------------------------
# 1. Recenser tous les interpreteurs Python de la machine
# ------------------------------------------------------------
Write-Step "Recherche des Python installés"
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
    Write-Warn "Aucun Python trouvé. Aucune désinstallation de paquets nécessaire."
} else {
    foreach ($p in $pythons) { Write-Ok $p }
}

# ------------------------------------------------------------
# 2. Désinstaller glmcode de chaque Python
# ------------------------------------------------------------
Write-Step "Désinstallation de glmcode (tous les Python)"
foreach ($py in $pythons) {
    & $py -m pip uninstall glmcode -y 2>$null | Out-Null
    & $py -m pip uninstall glm -y 2>$null | Out-Null
}
Write-Ok "Paquets glmcode/glm désinstalllés"

# ------------------------------------------------------------
# 3. Supprimer tous les lanceurs glm résiduels
# ------------------------------------------------------------
Write-Step "Suppression des lanceurs glm résiduels"
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
if ($removed -eq 0) { Write-Ok "aucun lanceur résiduel" }

# ------------------------------------------------------------
# 4. Supprimer le dossier d'installation
# ------------------------------------------------------------
Write-Step "Suppression du dossier d'installation"
if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $InstallDir)) {
        Write-Ok "Dossier d'installation supprimé : $InstallDir"
    } else {
        Write-Warn "Impossible de supprimer le dossier : $InstallDir"
    }
} else {
    Write-Ok "Aucun dossier d'installation trouvé"
}

# ------------------------------------------------------------
# 5. Supprimer la configuration
# ------------------------------------------------------------
Write-Step "Suppression de la configuration"
if (Test-Path $ConfigDir) {
    Remove-Item $ConfigDir -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $ConfigDir)) {
        Write-Ok "Configuration supprimée : $ConfigDir"
    } else {
        Write-Warn "Impossible de supprimer la configuration : $ConfigDir"
    }
} else {
    Write-Ok "Aucune configuration trouvée"
}

# ------------------------------------------------------------
# 6. Vérifier si glm est encore accessible
# ------------------------------------------------------------
Write-Step "Vérification finale"
try {
    $glmVersion = glm --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Warn "Attention : glm est encore accessible. Vérifiez votre PATH"
        Write-Warn "Redémarrez votre terminal pour être sûr"
    } else {
        Write-Ok "glm a été complètement désinstallé"
    }
} catch {
    Write-Ok "glm a été complètement désinstallé"
}

Write-Host ""
Write-Host "  Désinstallation terminée !" -ForegroundColor Green
Write-Host ""