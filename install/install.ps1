<#
    Installation de GLM Code sur Windows.

    Installe le paquet avec pip, puis ajoute le dossier des scripts Python au
    PATH utilisateur pour que la commande `glm` soit disponible partout.

    Usage :
        powershell -ExecutionPolicy Bypass -File install\install.ps1

    Options :
        -Quiet     n'affiche que les erreurs
        -NoPath    installe sans toucher au PATH
        -Source    dossier du depot (par defaut : deduit de ce script)
#>

[CmdletBinding()]
param(
    [switch]$Quiet,
    [switch]$NoPath,
    [string]$Source
)

$ErrorActionPreference = 'Stop'
$LogFile = Join-Path $env:TEMP 'glm-install.log'

# --- Journalisation et affichage -------------------------------------------

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $LogFile -Value "[$stamp] [$Level] $Message" -Encoding utf8
}

function Say {
    param([string]$Message, [string]$Color = 'Gray')
    Write-Log $Message
    if (-not $Quiet) { Write-Host $Message -ForegroundColor $Color }
}

function Say-Step   { param([string]$m) Say "==> $m" 'Cyan' }
function Say-Ok     { param([string]$m) Say "    OK  $m" 'Green' }
function Say-Warn   { param([string]$m) Write-Log $m 'WARN'; Write-Host "    !   $m" -ForegroundColor Yellow }
function Say-Fail   { param([string]$m) Write-Log $m 'ERROR'; Write-Host "    X   $m" -ForegroundColor Red }

function Invoke-Native {
    <#
        Execute un binaire externe en journalisant sa sortie.

        PowerShell 5.1 emballe chaque ligne de stderr d'un exe dans un
        ErrorRecord (NativeCommandError) : avec $ErrorActionPreference = 'Stop',
        l'appel echouerait meme quand le code de retour vaut 0. On repasse donc
        temporairement en 'Continue' et on se fie au seul code de retour.
    #>
    param(
        [string]$Exe,
        [string[]]$Arguments,
        [string]$Show = '^(Successfully|ERROR|WARNING)'
    )
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

function Abort {
    param([string]$Message, [string]$Hint)
    Say-Fail $Message
    if ($Hint) { Write-Host "        $Hint" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Journal complet : $LogFile" -ForegroundColor DarkGray
    exit 1
}

# --- 1. Environnement -------------------------------------------------------

Set-Content -Path $LogFile -Value "" -Encoding utf8
Say ""
Say "  GLM Code - installation Windows" 'White'
Say "  --------------------------------" 'DarkGray'
Say ""

Say-Step "Verification de l'environnement"
Write-Log "OS      : $([Environment]::OSVersion.VersionString)"
Write-Log "64 bits : $([Environment]::Is64BitOperatingSystem)"

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Say-Ok "droits administrateur detectes (installation quand meme en mode utilisateur)"
} else {
    Say-Ok "mode utilisateur"
}

# --- 2. Python --------------------------------------------------------------

Say-Step "Recherche de Python 3.11 ou plus recent"

function Get-PythonCandidates {
    $found = @()
    # `py` (le lanceur Windows) expose les versions installees.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in @('3.14', '3.13', '3.12', '3.11', '3')) {
            $found += ,@('py', @("-$v"))
        }
    }
    foreach ($name in @('python', 'python3')) {
        if (Get-Command $name -ErrorAction SilentlyContinue) {
            $found += ,@($name, @())
        }
    }
    return $found
}

$python = $null
$pythonArgs = @()
$inVenv = $false

# Un environnement virtuel actif prime : `pip install --user` y est refuse, et
# l'utilisateur attend une installation dans son venv.
if ($env:VIRTUAL_ENV) {
    $venvPython = Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'
    if (Test-Path $venvPython) {
        $python = $venvPython
        $inVenv = $true
        $venvVersion = & $python -c "import sys; print('%d.%d' % sys.version_info[:2])"
        Say-Ok "environnement virtuel actif : $env:VIRTUAL_ENV (Python $venvVersion)"
    }
}

if (-not $python) {
foreach ($candidate in Get-PythonCandidates) {
    $exe = $candidate[0]
    $pre = $candidate[1]
    try {
        $version = & $exe @pre -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
    } catch { continue }
    if ($LASTEXITCODE -ne 0 -or -not $version) { continue }

    $parts = $version.Trim().Split('.')
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    Write-Log "candidat : $exe $pre -> $version"
    if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
        $python = $exe
        $pythonArgs = $pre
        Say-Ok "Python $version ($exe $pre)"
        break
    }
}
}

if (-not $python) {
    Abort "aucun Python 3.11+ trouve." `
          "Installe-le depuis https://www.python.org/downloads/ en cochant 'Add Python to PATH'."
}

& $python @pythonArgs -m pip --version *>$null
if ($LASTEXITCODE -ne 0) {
    Say-Warn "pip absent, tentative d'installation via ensurepip"
    $code = Invoke-Native -Exe $python -Arguments ($pythonArgs + @('-m', 'ensurepip', '--upgrade'))
    if ($code -ne 0) { Abort "impossible d'installer pip." }
}
Say-Ok "pip disponible"

# --- 3. Sources -------------------------------------------------------------

Say-Step "Localisation des sources"

if (-not $Source) {
    # Ce script vit dans install\, le depot est le dossier parent.
    $Source = Split-Path -Parent $PSScriptRoot
}

$downloaded = $false
if (-not (Test-Path (Join-Path $Source 'pyproject.toml'))) {
    # Execution hors du depot (par exemple via `irm ... | iex`) : on clone.
    Say-Warn "sources introuvables dans $Source"
    $repo = 'https://github.com/Marreouu/GLM-C0deur.git'
    $Source = Join-Path $env:LOCALAPPDATA 'GLM-Code-src'
    Say "    telechargement depuis $repo"

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Abort "git est introuvable et les sources ne sont pas locales." `
              "Installe git, ou clone le depot puis relance install\install.ps1."
    }
    if (Test-Path $Source) { Remove-Item -Recurse -Force $Source }
    $code = Invoke-Native -Exe 'git' -Arguments @('clone', '--depth', '1', $repo, $Source) -Show 'zzz'
    if ($code -ne 0) {
        Abort "le clone a echoue (depot prive ou reseau indisponible)." `
              "Clone le depot manuellement, puis relance install\install.ps1."
    }
    $downloaded = $true
}
Say-Ok "sources : $Source"

# --- 4. Installation --------------------------------------------------------

Say-Step "Installation du paquet"

$pipArgs = @('-m', 'pip', 'install', '--upgrade')
if (-not $inVenv) { $pipArgs += '--user' }   # refuse a l'interieur d'un venv
if (-not $downloaded) { $pipArgs += '--editable' }
$pipArgs += $Source

Write-Log "commande : $python $pythonArgs $pipArgs"
$code = Invoke-Native -Exe $python -Arguments ($pythonArgs + $pipArgs)
if ($code -ne 0) {
    Abort "l'installation pip a echoue (code $code)." "Details dans $LogFile"
}
Say-Ok "paquet installe"

# --- 5. PATH ----------------------------------------------------------------

$scheme = if ($inVenv) { 'nt' } else { 'nt_user' }
$scriptsDir = & $python @pythonArgs -c "import sysconfig; print(sysconfig.get_path('scripts', '$scheme'))"
$scriptsDir = $scriptsDir.Trim()
Write-Log "dossier des scripts : $scriptsDir"

if (-not (Test-Path (Join-Path $scriptsDir 'glm.exe'))) {
    Say-Warn "glm.exe absent de $scriptsDir"
}

if ($NoPath) {
    Say-Step "PATH inchange (-NoPath)"
    Say "    ajoute ce dossier toi-meme : $scriptsDir"
} else {
    Say-Step "Configuration du PATH utilisateur"
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if (-not $userPath) { $userPath = '' }

    $already = $userPath.Split(';') | Where-Object { $_.TrimEnd('\') -ieq $scriptsDir.TrimEnd('\') }
    if ($already) {
        Say-Ok "deja present dans le PATH"
    } else {
        $newPath = if ($userPath.TrimEnd(';')) { $userPath.TrimEnd(';') + ';' + $scriptsDir } else { $scriptsDir }
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        Say-Ok "ajoute au PATH : $scriptsDir"
        Say-Warn "ouvre un nouveau terminal pour que le PATH soit pris en compte"
    }
    # Rend `glm` utilisable immediatement dans cette session.
    $env:Path = "$env:Path;$scriptsDir"
}

# --- 6. Verification --------------------------------------------------------

Say-Step "Verification"
$glm = Join-Path $scriptsDir 'glm.exe'
if (Test-Path $glm) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $v = (& $glm --version) 2>$null
    $ErrorActionPreference = $previous
    if ($v) { Say-Ok "$v" } else { Say-Warn "glm n'a pas repondu a --version" }
} else {
    Say-Warn "commande glm introuvable, essaie : $python -m glmcode"
}

Say ""
Say "  Installation terminee." 'Green'
Say ""
Say "  Etapes suivantes :" 'White'
Say "    1. copie config.example.toml vers config.toml" 'Gray'
Say "    2. renseigne ta cle API Z.ai dans [zai].api_key" 'Gray'
Say "    3. lance : glm" 'Gray'
Say ""
Say "  Journal : $LogFile" 'DarkGray'
Say ""
