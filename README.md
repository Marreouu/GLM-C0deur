# GLM Codeur

Un assistant de codage intelligent basé sur GLM, conçu pour vous aider dans vos projets de développement.

## Installation

### 🚀 Installation avancée (recommandée)

**Installation directe depuis GitHub avec fonctionnalités avancées :**

**Windows:**
```bash
# Installation complète avec détection d'environnement, gestion des erreurs et journalisation
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.ps1" | iex
```

**Linux/macOS:**
```bash
# Installation complète avec détection d'environnement, gestion des erreurs et rollback
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.sh | bash
```

### 🔧 Options d'installation avancée

**Installation avec nettoyage complet (si vous avez des problèmes existants):**

**Windows:**
```bash
# Désinstallation complète + réinstallation propre
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.ps1" | iex
```

**Linux/macOS:**
```bash
# Désinstallation complète + réinstallation propre avec rollback
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.sh" | bash
```

### 🗑️ Désinstallation complète

**Windows:**
```bash
# Désinstallation complète avec suppression de tous les traces
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/uninstall.ps1" | iex
```

**Linux/macOS:**
```bash
# Désinstallation complète avec rollback et nettoyage
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/uninstall.sh" | bash
```

### 📦 Méthode manuelle (si vous avez déjà cloné le dépôt)

1. **Clonez le dépôt :**
   ```bash
   git clone https://github.com/Marreouu/GLM-C0deur.git
   cd GLM-C0deur
   ```

2. **Installez GLM Codeur :**

   **Windows:**
   ```bash
   # Double-cliquez sur install/install.bat
   # Ou exécutez en PowerShell :
   powershell -ExecutionPolicy Bypass -File install/install.ps1
   ```

   **Linux/macOS:**
   ```bash
   # Exécutez le script d'installation :
   chmod +x install/install.sh
   ./install/install.sh
   ```

3. **Vérifiez l'installation :**
   ```bash
   glm --version
   ```

## ⚙️ Fonctionnalités avancées de l'installation

### 🖥️ Détection automatique de l'environnement
- **Windows:** Détection des droits administratifs, version .NET, système d'exploitation
- **Linux/macOS:** Détection de la distribution, version bash, paquets système requis

### 🛡️ Installation robuste avec gestion des erreurs
- Vérification de la connectivité Internet
- Gestion des timeouts et des erreurs réseau
- Journalisation détaillée de toutes les opérations
- Points de restauration automatiques (rollback)

### 🐍 Gestion avancée de Python
- Détection automatique de toutes les installations Python
- Proposition de choix si plusieurs versions disponibles
- Vérification automatique des dépendances manquantes
- Installation de pip si nécessaire

### 📁 Installation propre et organisation
- **Windows:** Installation dans Program Files (si admin) ou AppData (utilisateur)
- **Linux/macOS:** Installation dans /usr/local (si sudo) ou ~/.glm-code (utilisateur)
- Création de raccourcis dans le menu Démarrer (Windows)
- Ajout au PATH système ou utilisateur

### 🔍 Post-installation et vérification
- Tests automatiques de l'installation
- Configuration des variables d'environment
- Création d'un fichier de log complet
- Proposition d'ouverture d'un terminal pour test

### 🎨 Interface utilisateur améliorée
- Barre de progression pour les opérations longues
- Couleurs et formatage pour une meilleure lisibilité
- Messages d'erreur clairs avec solutions proposées
- Mode silencieux/verbose optionnel

## 📋 Explication détaillée des commandes des scripts

### Commandes d'installation directe

#### Windows (`install.ps1`)

```powershell
# Commande principale d'installation
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.ps1" | iex
```

**Explication:**
- `irm`: Invoke-RWebCommand - Télécharge le script depuis GitHub
- `| iex`: Invoke-Expression - Exécute le script téléchargé
- **Fonction:** Télécharge et exécute directement l'installateur depuis le dépôt GitHub

#### Linux/macOS (`install.sh`)

```bash
# Commande principale d'installation
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.sh | bash
```

**Explication:**
- `curl`: Outil de transfert de données URL
- `-s`: Silent mode (pas de statistiques)
- `-S`: Show errors (affiche les erreurs même en mode silencieux)
- `-L`: Follow redirects (suit les redirections HTTP)
- `| bash`: Pipe le contenu du script à bash pour exécution
- **Fonction:** Télécharge et exécute directement l'installateur depuis le dépôt GitHub

### Commandes de nettoyage + réinstallation

#### Windows (`nettoyer-et-installer.ps1`)

```powershell
# Commande de nettoyage + réinstallation
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.ps1" | iex
```

**Explication:**
- **Fonction:** Désinstalle toutes les versions existantes de GLM, supprime tous les lanceurs résiduels, puis réinstalle proprement depuis GitHub
- **Utilisation:** Idéal pour corriger les installations corrompues ou les conflits

#### Linux/macOS (`nettoyer-et-installer.sh`)

```bash
# Commande de nettoyage + réinstallation
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.sh" | bash
```

**Explication:**
- **Fonction:** Désinstalle toutes les versions existantes de GLM, supprime tous les lanceurs résiduels, puis réinstalle proprement depuis GitHub
- **Fonction supplémentaire:** Effectue un rollback automatique en cas d'erreur pendant l'installation

### Commandes de désinstallation

#### Windows (`uninstall.ps1`)

```powershell
# Commande de désinstallation complète
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/uninstall.ps1" | iex
```

**Explication:**
- **Fonction:** Supprime complètement GLM Codeur du système
- **Actions:** Désinstalle les paquets Python, supprime les lanceurs, supprime le dossier d'installation, supprime la configuration
- **Log:** Crée un fichier de log pour le suivi des opérations

#### Linux/macOS (`uninstall.sh`)

```bash
# Commande de désinstallation complète
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/uninstall.sh" | bash
```

**Explication:**
- **Fonction:** Supprime complètement GLM Codeur du système
- **Actions:** Désinstalle les paquets Python, supprime les lanceurs, supprime le dossier d'installation, supprime la configuration
- **Log:** Crée un fichier de log pour le suivi des opérations

### Options avancées des scripts

#### Windows - Options PowerShell

```powershell
# Installation avec mode silencieux
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.ps1" | iex -Silent

# Installation avec mode verbeux
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.ps1" | iex -Verbose
```

**Explication:**
- `-Silent`: Exécute le script sans afficher les détails des opérations
- `-Verbose`: Affiche toutes les informations détaillées du processus d'installation

#### Linux/macOS - Options bash

```bash
# Installation avec sortie verbeuse
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.sh | bash -x

# Exécution avec un shell spécifique
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.sh | bash -x -v
```

**Explication:**
- `-x`: Mode debug (affiche chaque commande exécutée)
- `-v`: Mode verbose (affiche les détails d'exécution)

### Commandes internes des scripts

#### Détection de l'environnement

**Windows:**
```powershell
# Vérification des droits administratifs
$isAdmin = [Security.Principal.WindowsIdentity]::GetCurrent() | 
    New-Object Security.Principal.WindowsPrincipal | 
    Where-Object { $_.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) }

# Vérification de la version .NET
$netVersion = Get-ItemProperty "HKLM:SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full\" | 
    Select-Object -ExpandProperty Release
```

**Linux/macOS:**
```bash
# Détection du système d'exploitation
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    DISTRO=$(lsb_release -d | cut -f2)
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    DISTRO=$(sw_vers -productVersion)
fi

# Vérification de la version de bash
BASH_VERSION=$(bash --version | head -n1 | cut -d' ' -f4 | cut -d'(' -f1)
```

#### Gestion de Python

**Windows:**
```powershell
# Recherche de toutes les installations Python
$pythonCommands = @("python", "py", "python3")
foreach ($cmd in $pythonCommands) {
    try {
        $versionOutput = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            # Python trouvé
        }
    } catch {
        # Commande non trouvée
    }
}
```

**Linux/macOS:**
```bash
# Recherche et sélection de Python
python_commands=("python3" "python")
for cmd in "${python_commands[@]}"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        # Python trouvé
    fi
done

# Proposition de choix si plusieurs versions
if [ ${#available_pythons[@]} -gt 1 ]; then
    echo "Plusieurs versions de Python détectées :"
    for i in "${!available_pythons[@]}"; do
        echo "$((i+1)). $(${available_pythons[$i]} --version)"
    done
    read -p "Choisissez une version : " choice
fi
```

#### Installation et configuration

**Windows:**
```powershell
# Création du lanceur
$launcher = @"
@echo off
set "PYTHONPATH=$InstallDir;%PYTHONPATH%"
"$pythonExe" -m glmcode %*
"@
Set-Content -Path "$BinDir\glm.cmd" -Value $launcher -Encoding ASCII

# Ajout au PATH
[Environment]::SetEnvironmentVariable("Path", "$newPath", "Machine")
```

**Linux/macOS:**
```bash
# Création du lanceur
cat > "$BIN_DIR/glm" << 'EOF'
#!/bin/bash
export PYTHONPATH="$(dirname "$(dirname "$(realpath "$0")")"):$PYTHONPATH"
exec python3 -m glmcode "$@"
EOF
chmod +x "$BIN_DIR/glm"

# Ajout au PATH
echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$HOME/.bashrc"
```

## Prérequis

- Python 3.11 ou supérieur
- pip (gestionnaire de paquets Python)
- Git (pour le clonage du dépôt)
- (Windows) .NET Framework 4.8+ (recommandé)

## Configuration

GLM Codeur utilise un fichier de configuration situé à `~/.glmcode/config.toml`. Si ce fichier n'existe pas, il sera créé automatiquement à partir de `config.example.toml`.

## Utilisation

Une fois installé, utilisez GLM Codeur simplement avec :

```bash
glm
```

## Scripts disponibles

### `install/install.ps1` / `install/install.sh`
- Installation avancée avec détection d'environnement
- Téléchargement direct du dépôt GitHub
- Gestion robuste des erreurs et rollback
- Configuration automatique du PATH
- Création de raccourcis et lanceurs

### `install/nettoyer-et-installer.ps1` / `install/nettoyer-et-installer.sh`
- Désinstallation complète de toutes les versions existantes
- Suppression de tous les lanceurs résiduels
- Téléchargement et réinstallation propre depuis GitHub
- Restauration automatique en cas d'erreur

### `install/uninstall.ps1` / `install/uninstall.sh`
- Désinstallation complète de GLM Codeur
- Suppression de tous les lanceurs résiduels
- Suppression du dossier d'installation
- Suppression de la configuration
- Vérification finale

## Dépannage

Si vous rencontrez des problèmes :

1. **Essayez la méthode de nettoyage + installation:**
   ```bash
   # Windows
   irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.ps1" | iex
   
   # Linux/macOS
   curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.sh" | bash
   ```

2. **Vérifiez que Python 3.11+ est installé et dans votre PATH**
3. **Redémarrez votre terminal après l'installation**
4. **Consultez les fichiers de log pour plus de détails:**
   - Windows: `%TEMP%\glm-install.log`
   - Linux/macOS: `/tmp/glm-install.log`

## Contribuer

Les contributions sont les bienvenues ! Veuillez consulter le dossier `docs/` pour plus d'informations sur la contribution.

## Licence

Ce projet est sous licence MIT.