# GLM Codeur

Un assistant de codage intelligent basé sur GLM, conçu pour vous aider dans vos projets de développement.

## Installation

### Méthode recommandée (Windows/Linux/macOS)

1. **Clonez le dépôt :**
   ```bash
   git clone https://github.com/Marreouu/GLM-C0deur.git
   cd GLM-C0deur
   ```

2. **Installez GLM Codeur :**

   **Windows :**
   ```bash
   # Double-cliquez sur install/install.bat
   # Ou exécutez en PowerShell :
   powershell -ExecutionPolicy Bypass -File install/install.ps1
   ```

   **Linux/macOS :**
   ```bash
   # Exécutez le script d'installation :
   chmod +x install/install.sh
   ./install/install.sh
   ```

3. **Vérifiez l'installation :**
   ```bash
   glm --version
   ```

### Méthode alternative (nettoyage + installation)

Si vous avez des problèmes d'installation ou si vous voulez une installation propre :

**Windows :**
```bash
# Double-cliquez sur install/nettoyer-et-installer.bat
# Ou exécutez en PowerShell :
powershell -ExecutionPolicy Bypass -File install/nettoyer-et-installer.ps1
```

**Linux/macOS :**
```bash
# Exécutez le script de nettoyage + installation :
chmod +x install/nettoyer-et-installer.sh
./install/nettoyer-et-installer.sh
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

### `install/install.bat` / `install/install.ps1`
- Vérifie Python 3.11+
- Installe les dépendances
- Crée un lanceur `glm` et l'ajoute au PATH
- Installe la configuration globale

### `install/nettoyer-et-installer.bat` / `install/nettoyer-et-installer.ps1`
- Désinstalle GLM Codeur de tous les Python trouvés
- Supprime tous les lanceurs résiduels
- Réinstalle proprement GLM Codeur

## Dépannage

Si vous rencontrez des problèmes :

1. Essayez la méthode de nettoyage + installation
2. Vérifiez que Python 3.11+ est installé et dans votre PATH
3. Redémarrez votre terminal après l'installation

## Contribuer

Les contributions sont les bienvenues ! Veuillez consulter le dossier `docs/` pour plus d'informations sur la contribution.

## Licence

Ce projet est sous licence MIT.