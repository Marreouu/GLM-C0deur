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
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.sh | bash
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
   curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.sh | bash
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