# ============================================================
#  Installateur de glm (glmcode) - Version Avancée
#
#  Ce script télécharge et installe directement glm depuis GitHub avec des fonctionnalités avancées :
#    1. Détection automatique de l'environnement
#    2. Installation robuste avec gestion des erreurs
#    3. Gestion avancée de Python
#    4. Installation propre et organisation
#    5. Post-installation et vérification
#    6. Interface utilisateur améliorée
#
#  USAGE : 
#    irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.ps1" | iex
# ============================================================

param(
    [switch]$Silent,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ProgressPreference = if ($Silent) { "SilentlyContinue" } else { "Continue" }

# --- Configuration ---
$RepoUrl = "https://github.com/Marreouu/GLM-C0deur"
$AppName = "glm-code"
$TempDir = Join-Path $env:TEMP "glm-install"
$LogFile = Join-Path $env:TEMP "glm-install.log"
$StartTime = Get-Date

# --- Fonctions utilitaires ---
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $logEntry
    if ($Verbose -or $Level -ne "INFO") {
        Write-Host $logEntry
    }
}

function Write-Step { 
    param($m) 
    Write-Host "==> $m" -ForegroundColor Cyan
    Write-Log "Étape: $m"
}

function Write-Ok { 
    param($m) 
    Write-Host "    $m" -ForegroundColor Green
    Write-Log "OK: $m"
}

function Write-Warn { 
    param($m) 
    Write-Host "    $m" -ForegroundColor Yellow
    Write-Log "WARN: $m" "WARN"
}

function Write-Err { 
    param($m) 
    Write-Host "    $m" -ForegroundColor Red
    Write-Log "ERREUR: $m" "ERROR"
}

function Test-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    return (New-Object Security.Principal.WindowsPrincipal($currentUser)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-InternetConnection {
    try {
        $response = Invoke-WebRequest -Uri "https://www.google.com" -UseBasicParsing -TimeoutSec 10
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Show-Progress {
    param([int]$PercentComplete, [string]$Status)
    if (-not $Silent) {
        Write-Progress -Activity "Installation de $AppName" -Status $Status -PercentComplete $PercentComplete
    }
}

# --- Début de l'installation ---
Clear-Host
Write-Host ""
Write-Host "  Installation de $AppName" -ForegroundColor Magenta
Write-Host "  Source : $RepoUrl" -ForegroundColor DarkGray
Write-Host ""

Write-Log "Démarrage de l'installation de $AppName"
Write-Log "Mode silencieux: $($Silent.IsPresent)"
Write-Log "Mode verbeux: $($Verbose.IsPresent)"

# --- 1. Détection de l'environnement ---
Write-Step "Détection de l'environnement"
Show-Progress -PercentComplete 5 -Status "Détection de l'environnement"

# Vérifier les droits administratifs
$isAdmin = Test-Admin
Write-Ok "Mode administrateur: $($isAdmin)"

# Vérifier le système d'exploitation
$os = Get-CimInstance Win32_OperatingSystem
$osVersion = $os.Version
$osName = $os.Caption
Write-Ok "Système: $osName ($osVersion)"

# Vérifier la version .NET
$netVersion = Get-ItemProperty "HKLM:SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full\" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Release -ErrorAction SilentlyContinue
if ($netVersion) {
    if ($netVersion -ge 528040) {
        Write-Ok ".NET Framework 4.8 ou supérieur détecté"
    } else {
        Write-Warn ".NET Framework ancien détecté ($netVersion)"
    }
} else {
    Write-Warn ".NET Framework non détecté"
}

# Déterminer le dossier d'installation
if ($isAdmin) {
    $InstallDir = Join-Path $env:ProgramFiles $AppName
} else {
    $InstallDir = Join-Path $env:LOCALAPPDATA $AppName
}
Write-Ok "Dossier d'installation: $InstallDir"

# --- 2. Vérification de la connectivité Internet ---
Write-Step "Vérification de la connectivité Internet"
Show-Progress -PercentComplete 10 -Status "Vérification de la connectivité Internet"

if (-not (Test-InternetConnection)) {
    Write-Err "Aucune connexion Internet détectée. Veuillez vérifier votre connexion et réessayer."
    exit 1
}
Write-Ok "Connexion Internet active"

# --- 3. Téléchargement du dépôt GitHub ---
Write-Step "Téléchargement du dépôt GitHub"
Show-Progress -PercentComplete 20 -Status "Téléchargement du dépôt GitHub"

try {
    # Supprimer les anciens téléchargements
    if (Test-Path $TempDir) { 
        Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Log "Ancien dossier temporaire supprimé"
    }
    
    # Télécharger avec git
    Write-Log "Clonage du dépôt: $RepoUrl"
    & git clone $RepoUrl $TempDir 2>> $LogFile
    if ($LASTEXITCODE -ne 0) {
        throw "Échec du clonage du dépôt"
    }
    Write-Ok "Dépôt téléchargé avec succès"
} catch {
    Write-Err "Échec du téléchargement : $($_.Exception.Message)"
    Write-Err "Vérifiez votre connexion Internet et l'URL du dépôt"
    Write-Log "Erreur de téléchargement: $($_.Exception.Message)" "ERROR"
    exit 1
}

# --- 4. Vérification de Python ---
Write-Step "Vérification de Python"
Show-Progress -PercentComplete 30 -Status "Vérification de Python"

$pythonPaths = @()
$pythonVersions = @{}

# Rechercher toutes les installations de Python
$pythonCommands = @("python", "py", "python3")
foreach ($cmd in $pythonCommands) {
    try {
        $versionOutput = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $versionString = $versionOutput.ToString().Split(' ')[1]
            $pythonPaths += $cmd
            $pythonVersions[$cmd] = $versionString
            Write-Log "Python trouvé: $cmd ($versionString)"
        }
    } catch {
        # Commande non trouvée
    }
}

# Rechercher dans le registre
$pythonRegPaths = @(
    "HKLM:\SOFTWARE\Python\PythonCore",
    "HKCU:\SOFTWARE\Python\PythonCore"
)

foreach ($regPath in $pythonRegPaths) {
    if (Test-Path $regPath) {
        $versions = Get-ChildItem $regPath -ErrorAction SilentlyContinue
        foreach ($version in $versions) {
            $installPath = (Get-ItemProperty "$($version.PSPath)\InstallPath" -ErrorAction SilentlyContinue)."(default)"
            if ($installPath -and (Test-Path $installPath)) {
                $pythonExe = Join-Path $installPath "python.exe"
                if (Test-Path $pythonExe) {
                    $versionString = (& $pythonExe --version 2>&1).ToString().Split(' ')[1]
                    if ($pythonPaths -notcontains $pythonExe) {
                        $pythonPaths += $pythonExe
                        $pythonVersions[$pythonExe] = $versionString
                        Write-Log "Python trouvé dans le registre: $pythonExe ($versionString)"
                    }
                }
            }
        }
    }
}

if ($pythonPaths.Count -eq 0) {
    Write-Err "Python introuvable. Installez Python 3.11+ depuis https://python.org"
    Write-Err "(cochez 'Add Python to PATH' pendant l'installation)"
    exit 1
}

# Sélectionner la meilleure version de Python
$selectedPython = $null
$selectedVersion = $null
$bestVersion = [version]"0.0.0"

foreach ($path in $pythonPaths) {
    $versionString = $pythonVersions[$path]
    try {
        $version = [version]$versionString
        if ($version -ge [version]"3.11.0" -and $version -gt $bestVersion) {
            $bestVersion = $version
            $selectedPython = $path
            $selectedVersion = $versionString
        }
    } catch {
        # Version non valide
    }
}

if (-not $selectedPython) {
    Write-Err "Aucune version compatible de Python trouvée (3.11+ requis)"
    Write-Err "Versions détectées :"
    foreach ($path in $pythonPaths) {
        Write-Err "  - $path : $($pythonVersions[$path])"
    }
    exit 1
}

Write-Ok "Python sélectionné : $selectedPython ($selectedVersion)"

# --- 5. Installation des dépendances ---
Write-Step "Installation des dépendances"
Show-Progress -PercentComplete 50 -Status "Installation des dépendances"

try {
    Set-Location $TempDir
    Write-Log "Mise à jour de pip"
    & $selectedPython -m pip install --upgrade pip --quiet 2>> $LogFile
    if ($LASTEXITCODE -ne 0) {
        throw "Échec de la mise à jour de pip"
    }
    
    if (Test-Path "requirements.txt") {
        Write-Log "Installation des dépendances depuis requirements.txt"
        & $selectedPython -m pip install -r "requirements.txt" --quiet 2>> $LogFile
        if ($LASTEXITCODE -ne 0) {
            throw "Échec de l'installation des dépendances"
        }
        Write-Ok "Dépendances installées"
    } else {
        Write-Warn "Fichier requirements.txt non trouvé"
    }
} catch {
    Write-Err "Échec de l'installation des dépendances : $($_.Exception.Message)"
    Write-Log "Erreur d'installation des dépendances: $($_.Exception.Message)" "ERROR"
    exit 1
}

# --- 6. Déplacement vers le dossier d'installation final ---
Write-Step "Installation finale"
Show-Progress -PercentComplete 70 -Status "Installation finale"

try {
    # Créer le dossier d'installation si nécessaire
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        Write-Log "Dossier d'installation créé: $InstallDir"
    }
    
    # Copier les fichiers
    Copy-Item "$TempDir\*" $InstallDir -Recurse -Force
    Write-Ok "Fichiers copiés vers : $InstallDir"
} catch {
    Write-Err "Échec de l'installation finale : $($_.Exception.Message)"
    Write-Log "Erreur d'installation finale: $($_.Exception.Message)" "ERROR"
    exit 1
}

# --- 7. Création du lanceur "glm" ---
Write-Step "Création de la commande glm"
Show-Progress -PercentComplete 80 -Status "Création du lanceur"

try {
    $BinDir = Join-Path $InstallDir "bin"
    if (-not (Test-Path $BinDir)) { 
        New-Item -ItemType Directory -Path $BinDir | Out-Null
        Write-Log "Dossier bin créé: $BinDir"
    }

    # Chemin absolu de l'interpréteur Python
    $pythonExePath = (& $selectedPython -c "import sys; print(sys.executable)").Trim()
    Write-Log "Chemin de l'exécutable Python: $pythonExePath"

    # Lanceur .cmd
    $launcherCmd = @"
@echo off
set "PYTHONPATH=$InstallDir;%PYTHONPATH%"
"$pythonExePath" -m glmcode %*
"@
    $launcherCmdPath = Join-Path $BinDir "glm.cmd"
    Set-Content -Path $launcherCmdPath -Value $launcherCmd -Encoding ASCII
    Write-Ok "Lanceur CMD créé : $launcherCmdPath"

    # Lanceur PowerShell
    $launcherPs1 = @"
`$env:PYTHONPATH="$InstallDir;`$env:PYTHONPATH"
& "$pythonExePath" -m glmcode @args
"@
    $launcherPs1Path = Join-Path $BinDir "glm.ps1"
    Set-Content -Path $launcherPs1Path -Value $launcherPs1 -Encoding ASCII
    Write-Ok "Lanceur PS1 créé : $launcherPs1Path"
} catch {
    Write-Err "Échec de la création du lanceur : $($_.Exception.Message)"
    Write-Log "Erreur de création du lanceur: $($_.Exception.Message)" "ERROR"
    exit 1
}

# --- 8. Ajout au PATH ---
Write-Step "Ajout de glm au PATH"
Show-Progress -PercentComplete 85 -Status "Ajout au PATH"

try {
    $pathTarget = if ($isAdmin) { "Machine" } else { "User" }
    $currentPath = [Environment]::GetEnvironmentVariable("Path", $pathTarget)
    if (-not $currentPath) { $currentPath = "" }
    
    $alreadyInPath = ($currentPath -split ';') | Where-Object { $_.TrimEnd('\') -ieq $BinDir.TrimEnd('\') }
    if ($alreadyInPath) {
        Write-Ok "Déjà dans le PATH : $BinDir"
    } else {
        $newPath = if ($currentPath.TrimEnd(';')) { "$($currentPath.TrimEnd(';'));$BinDir" } else { $BinDir }
        [Environment]::SetEnvironmentVariable("Path", $newPath, $pathTarget)
        Write-Ok "Ajouté au PATH $pathTarget : $BinDir"
        Write-Log "Ajouté au PATH $pathTarget : $BinDir"
    }
    
    # Ajouter aussi à la session courante
    $env:Path = "$env:Path;$BinDir"
} catch {
    Write-Warn "Impossible d'ajouter au PATH : $($_.Exception.Message)"
    Write-Log "Avertissement PATH: $($_.Exception.Message)" "WARN"
}

# --- 9. Installation de la configuration ---
Write-Step "Installation de la configuration"
Show-Progress -PercentComplete 90 -Status "Installation de la configuration"

try {
    $cfgDir = Join-Path $env:USERPROFILE ".glmcode"
    if (-not (Test-Path $cfgDir)) {
        New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null
        Write-Log "Dossier de configuration créé: $cfgDir"
    }
    
    $cfgDst = Join-Path $cfgDir "config.toml"
    $cfgSrc = Join-Path $InstallDir "config.toml"
    if (-not (Test-Path $cfgSrc)) { 
        $cfgSrc = Join-Path $InstallDir "config.example.toml" 
    }
    
    if (Test-Path $cfgSrc) {
        if (Test-Path $cfgDst) {
            Write-Ok "Configuration déjà présente : $cfgDst (conservée)"
        } else {
            Copy-Item $cfgSrc $cfgDst -Force
            Write-Ok "Configuration installée : $cfgDst"
        }
    } else {
        Write-Warn "Aucun fichier de configuration à copier"
    }
} catch {
    Write-Warn "Impossible d'installer la configuration : $($_.Exception.Message)"
    Write-Log "Avertissement configuration: $($_.Exception.Message)" "WARN"
}

# --- 10. Création des raccourcis ---
Write-Step "Création des raccourcis"
Show-Progress -PercentComplete 95 -Status "Création des raccourcis"

if ($isAdmin) {
    try {
        # Créer un raccourci dans le menu Démarrer
        $startMenuPath = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs"
        $shortcutDir = Join-Path $startMenuPath $AppName
        if (-not (Test-Path $shortcutDir)) {
            New-Item -ItemType Directory -Path $shortcutDir | Out-Null
        }
        
        $shortcutPath = Join-Path $shortcutDir "$AppName.lnk"
        $WshShell = New-Object -ComObject WScript.Shell
        $shortcut = $WshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "cmd.exe"
        $shortcut.Arguments = "/k glm"
        $shortcut.WorkingDirectory = $env:USERPROFILE
        $shortcut.Description = "GLM Codeur"
        $shortcut.IconLocation = "cmd.exe,0"
        $shortcut.Save()
        Write-Ok "Raccourci créé : $shortcutPath"
    } catch {
        Write-Warn "Impossible de créer le raccourci : $($_.Exception.Message)"
    }
}

# --- 11. Vérification ---
Write-Step "Vérification"
Show-Progress -PercentComplete 98 -Status "Vérification finale"

try {
    $verificationResult = & "$launcherCmdPath" --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "glm opérationnel : $verificationResult"
    } else {
        throw "Code de retour : $LASTEXITCODE"
    }
} catch {
    Write-Warn "La vérification n'a pas abouti dans cette session."
    Write-Warn "Ouvrez un NOUVEAU terminal puis tapez : glm --version"
    Write-Log "Avertissement vérification: $($_.Exception.Message)" "WARN"
}

# --- 12. Nettoyage ---
Write-Step "Nettoyage"
Show-Progress -PercentComplete 100 -Status "Nettoyage"

try {
    if (Test-Path $TempDir) {
        Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Log "Dossier temporaire supprimé"
    }
    Write-Ok "Nettoyage terminé"
} catch {
    Write-Warn "Impossible de nettoyer les fichiers temporaires : $($_.Exception.Message)"
}

# --- Fin de l'installation ---
$endTime = Get-Date
$duration = $endTime - $StartTime
Write-Host ""
Write-Host "  Installation terminée !" -ForegroundColor Green
Write-Host "  Durée : $($duration.ToString("mm\:ss"))" -ForegroundColor Cyan
Write-Host "  Ouvrez un NOUVEAU terminal et tapez : glm" -ForegroundColor Green
Write-Host "  Installé dans : $InstallDir" -ForegroundColor DarkGray
Write-Host "  Journal : $LogFile" -ForegroundColor DarkGray
Write-Host ""

Write-Log "Installation terminée avec succès en $($duration.TotalSeconds) secondes"

# --- Proposition d'ouverture d'un terminal ---
if (-not $Silent) {
    $response = Read-Host "Voulez-vous ouvrir un nouveau terminal pour tester glm ? (O/n)"
    if ($response -ne "n" -and $response -ne "N") {
        Start-Process cmd.exe -ArgumentList "/k", "glm --version"
    }
}