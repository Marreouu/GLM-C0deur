# GLM Codeur

Un assistant de codage intelligent basé sur GLM, conçu pour vous aider dans vos projets de développement.

## Installation

### Méthode recommandée (Windows/Linux/macOS)

**Installation directe depuis GitHub :**

**Windows:**
```bash
# Exécutez directement depuis PowerShell :
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.ps1" | iex
```

**Linux/macOS:**
```bash
# Exécutez directement depuis votre terminal :
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.sh | bash
```

### Méthode alternative (nettoyage + installation)

Si vous avez des problèmes d'installation ou si vous voulez une installation propre :

**Windows:**
```bash
# Exécutez directement depuis PowerShell :
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.ps1" | iex
```

**Linux/macOS:**
```bash
# Exécutez directement depuis votre terminal :
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.sh | bash
```

## Désinstallation

Si vous souhaitez désinstaller complètement GLM Codeur :

**Windows:**
```bash
# Exécutez directement depuis PowerShell :
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/uninstall.ps1" | iex
```

**Linux/macOS:**
```bash
# Exécutez directement depuis votre terminal :
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/uninstall.sh | bash
```

### Méthode manuelle (si vous avez déjà cloné le dépôt)

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

## Prérequis

- Python 3.11 ou supérieur
- pip (gestionnaire de paquets Python)
- Git (pour le clonage du dépôt)

## Configuration

GLM Codeur utilise un fichier de configuration situé à `~/.glmcode/config.toml`. Si ce fichier n'existe pas, il sera créé automatiquement à partir de `config.example.toml`.

## Utilisation

Une fois installé, utilisez GLM Codeur simplement avec :

```bash
glm
```

## Scripts disponibles

### `install/install.ps1` / `install/install.sh`
- Télécharge directement le dépôt GitHub
- Vérifie Python 3.11+
- Installe les dépendances
- Crée un lanceur `glm` et l'ajoute au PATH
- Installe la configuration globale

### `install/nettoyer-et-installer.ps1` / `install/nettoyer-et-installer.sh`
- Désinstalle GLM Codeur de tous les Python trouvés
- Supprime tous les lanceurs résiduels
- Télécharge et réinstalle proprement GLM Codeur depuis GitHub

### `install/uninstall.ps1` / `install/uninstall.sh`
- Désinstalle GLM Codeur de tous les Python trouvés
- Supprime tous les lanceurs résiduels
- Supprime le dossier d'installation
- Supprime la configuration

## Dépannage

Si vous rencontrez des problèmes :

1. Essayez la méthode de nettoyage + installation
2. Vérifiez que Python 3.11+ est installé et dans votre PATH
3. Redémarrez votre terminal après l'installation

## Contribuer

Les contributions sont les bienvenues ! Veuillez consulter le dossier `docs/` pour plus d'informations sur la contribution.

## Licence

Ce projet est sous licence MIT.