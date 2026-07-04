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

## 🎮 Commandes Internes

Une fois installé, GLM Codeur offre de nombreuses commandes internes pour contrôler l'assistant. Consultez [COMMANDES.md](COMMANDES.md) pour la liste complète :

### Commandes principales :
- `/help` - Affiche l'aide complète
- `/reset` - Efface l'istorique de conversation
- `/model <nom>` - Change le modèle LLM
- `/mode [nom]` - Change le mode de fonctionnement (normal/auto/plan)

### Commandes de skills :
- `/skills` - Liste tous les skills disponibles
- `/review-code` - Analyse et critique de code
- `/generate-code` - Génère du code Python
- `/debug` - Aide au débogage
- `/explique` - Explication de concepts

### Commandes de session :
- `/session` - Affiche l'ID de la session courante
- `/sessions` - Liste toutes les sessions enregistrées
- `/resume [id]` - Reprend une session précédente

## ⚙️ Configuration

GLM Codeur utilise un fichier de configuration TOML. Consultez le dossier `config/` pour une documentation complète :

- [config/README.md](config/README.md) - Documentation complète de la configuration
- [config/QUICKSTART.md](config/QUICKSTART.md) - Guide de démarrage rapide
- [config/config.example.toml](config/config.example.toml) - Fichier d'exemple complet

### Configuration rapide :
```bash
# Copier le fichier d'exemple
cp config/config.example.toml ~/.glmcode/config.toml

# Configurer votre clé API
export GLM_API_KEY="votre_clé_api_ici"
```

## 🚀 Utilisation

Une fois installé et configuré, utilisez GLM Codeur simplement :

```bash
# Démarrer l'assistant
glm

# Dans l'interface, tapez votre demande :
"Bonjour, peux-tu m'aider avec mon projet Python ?"

# Ou utilisez les commandes internes :
/help
/review-code mon_fichier.py
/generate-code "crée une fonction pour calculer la factorielle"
```

## 📚 Skills Disponibles

GLM Codeur inclut plusieurs skills prédéfinis :

### Skills intégrés :
- **`/review-code`** - Analyse et critique de code
- **`/generate-code`** - Génère du code Python
- **`/refactor-code`** - Refactorise du code existant
- **`/debug`** - Aide au débogage
- **`/explique`** - Explication de concepts
- **`/tests`** - Génération de tests

### Créer vos propres skills :
Créez des fichiers Markdown dans `~/.glmcode/skills/` pour personnaliser les fonctionnalités.

## 🛠️ Scripts disponibles

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

## 💾 Commandes en Ligne de Commande

Les commandes suivantes sont utilisées au lancement de GLM Codeur :

### `glm --help`
Affiche l'aide complète des commandes en ligne de commande :
```bash
glm --help
```

**Résultat :**
```
usage: glmcode [-h] [--version] [--resume ID] [--continue] [--list-sessions]

Assistant de codage terminal (API Z.ai / GLM).

options:
  -h, --help       show this help message and exit
  --version        affiche la version
  --resume ID      reprend la session <ID>
  --continue       reprend la derniere session
  --list-sessions  liste les sessions enregistrees puis quitte
```

### `glm --version`
Affiche la version de GLM Codeur :
```bash
glm --version
```

### `glm --resume ID`
Reprend une session spécifique :
```bash
glm --resume abc123
```

### `glm --continue` ou `glm --cont`
Reprend la dernière session :
```bash
glm --continue
# ou
glm --cont
```

### `glm --list-sessions`
Liste toutes les sessions enregistrées :
```bash
glm --list-sessions
```

## 📖 Documentation Complète

- [COMMANDES.md](COMMANDES.md) - Toutes les commandes internes et skills
- [config/README.md](config/README.md) - Configuration détaillée
- [config/QUICKSTART.md](config/QUICKSTART.md) - Démarrage rapide
- [config/config.example.toml](config/config.example.toml) - Fichier de configuration exemple

## 🔧 Dépannage

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