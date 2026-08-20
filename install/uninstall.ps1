<#
    Desinstallation de GLM Code sur Windows.

    Retire le paquet, l'entree ajoutee au PATH utilisateur et, sur demande,
    la configuration et les sessions enregistrees.

    Usage :
        powershell -ExecutionPolicy Bypass -File install\uninstall.ps1
        powershell -ExecutionPolicy Bypass -File install\uninstall.ps1 -Purge
#>

[CmdletBinding()]
param(
    [switch]$Purge,   # supprime aussi ~\.glmcode (config, sessions)
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$LogFile = Join-Path $env:TEMP 'glm-uninstall.log'

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    Add-Content -Path $LogFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$Level] $Message" -Encoding utf8
}
function Say      { param([string]$m, [string]$c = 'Gray') Write-Log $m; if (-not $Quiet) { Write-Host $m -ForegroundColor $c } }
function Say-Step { param([string]$m) Say "==> $m" 'Cyan' }
function Say-Ok   { param([string]$m) Say "    OK  $m" 'Green' }
function Say-Warn { param([string]$m) Write-Log $m 'WARN'; Write-Host "    !   $m" -ForegroundColor Yellow }

function Invoke-Native {
    <#
        Execute un binaire externe en journalisant sa sortie.

        PowerShell 5.1 emballe chaque ligne de stderr d'un exe dans un
        ErrorRecord (NativeCommandError) : avec $ErrorActionPreference = 'Stop',
        l'appel echouerait meme quand le code de retour vaut 0.
    #>
    param([string]$Exe, [string[]]$Arguments, [string]$Show = '^(Successfully|WARNING|ERROR)')
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object {
            $line = "$_"
            Write-Log $line
            if (-not $Quiet -and $line -match $Show) {
                Write-Host "    $line" -ForegroundColor DarkGray
            }
        }
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
}

Set-Content -Path $LogFile -Value "" -Encoding utf8
Say ""
Say "  GLM Code - desinstallation" 'White'
Say ""

# --- 1. Python ---------------------------------------------------------------

$python = $null
$inVenv = $false

# Un venv actif prime : sinon on desinstallerait le paquet global alors que
# l'utilisateur visait son environnement virtuel.
if ($env:VIRTUAL_ENV) {
    $venvPython = Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'
    if (Test-Path $venvPython) {
        $python = $venvPython
        $inVenv = $true
        Say-Ok "environnement virtuel actif : $env:VIRTUAL_ENV"
    }
}
if (-not $python) {
    foreach ($name in @('py', 'python', 'python3')) {
        if (Get-Command $name -ErrorAction SilentlyContinue) { $python = $name; break }
    }
}
if (-not $python) {
    Say-Warn "Python introuvable : le paquet ne peut pas etre desinstalle par pip"
} else {
    Say-Step "Suppression du paquet"
    $code = Invoke-Native -Exe $python -Arguments @('-m', 'pip', 'uninstall', '-y', 'glmcode')
    if ($code -eq 0) { Say-Ok "paquet supprime" } else { Say-Warn "pip n'a rien supprime (deja absent ?)" }
}

# --- 2. PATH -----------------------------------------------------------------

Say-Step "Nettoyage du PATH utilisateur"

$scriptsDir = $null
if ($python) {
    try {
        $scheme = if ($inVenv) { 'nt' } else { 'nt_user' }
        $scriptsDir = (& $python -c "import sysconfig; print(sysconfig.get_path('scripts', '$scheme'))").Trim()
    } catch { }
}

if ($inVenv) {
    Say-Ok "venv : PATH utilisateur inchange"
} elseif ($scriptsDir) {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath) {
        $kept = $userPath.Split(';') | Where-Object {
            $_ -and ($_.TrimEnd('\') -ine $scriptsDir.TrimEnd('\'))
        }
        $newPath = ($kept -join ';')
        if ($newPath -ne $userPath) {
            [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
            Say-Ok "entree retiree : $scriptsDir"
        } else {
            Say-Ok "aucune entree a retirer"
        }
    }
} else {
    Say-Warn "dossier des scripts inconnu, PATH inchange"
}

# --- 3. Lanceurs residuels ---------------------------------------------------

Say-Step "Recherche de lanceurs residuels"
$leftovers = @()
foreach ($dir in @($scriptsDir, "$env:LOCALAPPDATA\Programs\glm", "$env:APPDATA\glm")) {
    if ($dir -and (Test-Path $dir)) {
        $leftovers += Get-ChildItem -Path $dir -Filter 'glm.*' -ErrorAction SilentlyContinue
    }
}
if ($leftovers) {
    foreach ($f in $leftovers) {
        Remove-Item -Force $f.FullName -ErrorAction SilentlyContinue
        Say-Ok "supprime : $($f.FullName)"
    }
} else {
    Say-Ok "aucun lanceur residuel"
}

# --- 4. Configuration --------------------------------------------------------

$configDir = Join-Path $env:USERPROFILE '.glmcode'
if ($Purge) {
    Say-Step "Suppression de la configuration"
    if (Test-Path $configDir) {
        Remove-Item -Recurse -Force $configDir
        Say-Ok "supprime : $configDir"
    } else {
        Say-Ok "rien a supprimer"
    }
    $src = Join-Path $env:LOCALAPPDATA 'GLM-Code-src'
    if (Test-Path $src) { Remove-Item -Recurse -Force $src; Say-Ok "supprime : $src" }
} elseif (Test-Path $configDir) {
    Say-Warn "configuration conservee : $configDir (relance avec -Purge pour l'effacer)"
}

Say ""
Say "  Desinstallation terminee." 'Green'
Say "  Ouvre un nouveau terminal pour que le PATH soit rafraichi." 'DarkGray'
Say ""
