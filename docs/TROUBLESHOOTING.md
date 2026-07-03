# Dépannage - GLM Code

Ce guide aide à résoudre les problèmes courants rencontrés avec GLM Code.

## Problèmes d'installation

### Erreur "ModuleNotFoundError"

**Symptôme** : `ModuleNotFoundError: No module named 'glmcode'`

**Solutions** :
```bash
# Vérifier l'installation
pip list | grep glmcode

# Réinstaller
pip install -r requirements.txt
pip install -e .

# Vérifier le Python PATH
echo $PYTHONPATH  # Linux/macOS
echo %PYTHONPATH%  # Windows
```

### Erreur "Permission denied"

**Symptôme** : `Permission denied: '/usr/local/bin/glm'`

**Solutions** :
```bash
# Installer pour l'utilisateur courant
pip install --user -e .

# Ou utiliser un virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -e .
```

### Problèmes avec les dépendances

**Symptôme** : Erreurs d'importation des dépendances

**Solutions** :
```bash
# Mettre à jour pip
pip install --upgrade pip

# Réinstaller les dépendances
pip install -r requirements.txt

# Vérifier les versions
pip list
```

## Problèmes de configuration

### Clé API manquante

**Symptôme** : `No API key found`

**Solutions** :
```bash
# Vérifier la configuration
cat config.toml

# Définir la variable d'environnement
export GLMCODE_API_KEY="votre-cle-api"

# Tester la connexion
glm /ping
```

### Fichier de configuration incorrect

**Symptôme** : Configuration invalide

**Solutions** :
```bash
# Valider le TOML
python -c "import tomllib; tomllib.load(open('config.toml', 'rb'))"

# Revenir au fichier exemple
cp config.example.toml config.toml
# Modifier avec vos paramètres
```

### Problèmes avec le mode orchestrateur

**Symptôme** : Le codeur ne répond pas

**Solutions** :
```bash
# Vérifier Ollama
ollama --version

# Lister les modèles
ollama list

# Télécharger le modèle
ollama pull qwen2.5-coder

# Tester Ollama
curl http://localhost:11434/api/tags

# Vérifier la configuration
cat config.toml | grep -A 10 \[coder\]
```

## Problèmes d'exécution

### Interface TUI non fonctionnelle

**Symptôme** : Erreurs avec l'interface plein écran

**Solutions** :
```bash
# Passer en mode simple
GLMCODE_SIMPLE=1 glm

# Vérifier les dépendances
pip install rich prompt_toolkit

# Tester avec un terminal différent
# Ex: utiliser xterm, gnome-terminal, etc.
```

### Problèmes d'encodage

**Symptôme** : Erreurs Unicode, caractères illisibles

**Solutions** :
```bash
# Vérifier l'encodage du terminal
echo $LANG  # Linux/macOS
echo %LANG%  # Windows

# Forcer l'UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Vérifier les fichiers
file fichier.txt
```

### Problèmes de performance

**Symptôme** : GLM Code est lent

**Solutions** :
```bash
# Vérifier la charge système
top  # Linux/macOS
Task Manager  # Windows

# Réduire la taille des fichiers
# Limitez les fichiers à <100Ko

# Utiliser le mode auto
glm --mode auto

# Optimiser Python
# Utiliser Python 3.11+ avec PyPy si possible
```

## Problèmes réseau

### Erreurs de connexion API

**Symptôme** : `Connection error`, `Timeout`

**Solutions** :
```bash
# Tester la connexion
curl -I https://api.z.ai/api/paas/v4

# Vérifier le proxy
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Tester sans proxy
unset HTTP_PROXY HTTPS_PROXY
glm /ping

# Vérifier le pare-feu
sudo ufw status  # Linux
```

### Rate limit

**Symptôme** : `429 Too Many Requests`

**Solutions** :
```bash
# Attendre avant de réessayer
# GLM Code gère automatiquement les retries

# Changer de modèle
glm /model glm-4.5-flash

# Réduire la fréquence des requêtes
# Utiliser des messages plus courts
```

## Problèmes de fichiers

### Erreurs de permission

**Symptôme** : `Permission denied` lors de l'écriture de fichiers

**Solutions** :
```bash
# Vérifier les permissions
ls -la fichier.txt

# Changer les permissions
chmod 644 fichier.txt

# Changer le propriétaire
sudo chown $USER:$USER fichier.txt

# Écrire dans un autre dossier
mkdir -p ~/glm-workspace
cd ~/glm-workspace
```

### Fichiers non trouvés

**Symptôme** : `File not found`

**Solutions** :
```bash
# Vérifier le chemin absolu
pwd
realpath fichier.txt

# Vérifier l'existence du fichier
ls -la fichier.txt

# Utiliser des chemins relatifs
# Toujours partir du dossier courant
```

### Problèmes d'encodage de fichiers

**Symptôme** : Erreurs lors de la lecture de fichiers

**Solutions** :
```bash
# Vérifier l'encodage
file -i fichier.txt

# Convertir en UTF-8
iconv -f original_encoding -t utf-8 fichier.txt > fichier_utf8.txt

# Utiliser des fichiers texte simples
# Éviter les fichiers binaires
```

## Problèmes de commandes

### Commandes shell qui ne fonctionnent pas

**Symptôme** : Les commandes shell échouent

**Solutions** :
```bash
# Vérifier la syntaxe
# Les commandes shell doivent être valides

# Tester manuellement
ls -la

# Vérifier les permissions
which commande
ls -la $(which commande)

# Vérifier le PATH
echo $PATH
```

### Timeouts

**Symptôme** : `Command timeout`

**Solutions** :
```bash
# Vérifier la durée des commandes
# Les commandes ont un timeout de 120s

# Optimiser les commandes
# Utiliser des options plus rapides

# Augmenter le timeout (dans config.toml)
max_tokens = 8192
```

## Problèmes de skills

### Skills non reconnus

**Symptôme** : `/skills` ne montre aucun skill

**Solutions** :
```bash
# Vérifier les chemins
ls -la skills/
ls -la ~/.glmcode/skills/

# Vérifier le format des fichiers
head -n 10 skill.md

# Vérifier les permissions
ls -la ~/.glmcode/skills/skill.md
```

### Problèmes avec les skills personnalisés

**Symptôme** : Les personnalisés ne fonctionnent pas

**Solutions** :
```bash
# Vérifier la syntaxe YAML
python -c "import yaml; yaml.safe_load(open('skill.md'))"

# Vérifier le contenu
cat skill.md

# Tester avec un skill simple
echo "---\nname: test\ndescription: Test\n---\n# Test" > test.md
```

## Problèmes de mémoire

### Erreurs de mémoire

**Symptôme** : `MemoryError`, `OutOfMemoryError`

**Solutions** :
```bash
# Vérifier l'utilisation mémoire
free -h  # Linux
Activity Monitor  # macOS

# Réduire la taille du contexte
# Utiliser des messages plus courts

# Fermer d'autres applications
# Libérer de la RAM
```

### Fichiers trop volumineux

**Symptôme** : Problèmes avec les gros fichiers

**Solutions** :
```bash
# Diviser les fichiers
# Utiliser split pour les gros fichiers

# Utiliser git pour les gros fichiers
# Git LFS

# Compresser les fichiers
# gzip, zip
```

## Problèmes de compatibilité

### Version Python

**Symptôme** : Erreurs avec certaines versions de Python

**Solutions** :
```bash
# Vérifier la version
python --version

# Utiliser Python 3.11+
# Recommandé pour GLM Code

# Créer un virtual environment
python -m venv venv
source venv/bin/activate
```

### Système d'exploitation

**Symptôme** : Problèmes spécifiques à un OS

**Solutions** :
```bash
# Windows
# Utiliser PowerShell ou Git Bash
# Vérifier l'encodage

# macOS
# Vérifier les permissions
# Utiliser Homebrew pour les dépendances

# Linux
# Vérifier les dépendances système
# Utiliser le package manager
```

## Problèmes de logs

### Activer les logs

**Solution** :
```bash
# Créer un fichier de logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    filename='glm.log',
    filemode='w'
)

# Ou utiliser la variable d'environnement
export GLMCODE_LOG_LEVEL=DEBUG
```

### Analyser les logs

**Commandes** :
```bash
# Voir les erreurs
grep ERROR glm.log

# Voir les requêtes API
grep "API request" glm.log

# Voir les outils appelés
grep "tool_call" glm.log
```

## Problèmes avancés

### Problèmes de concurrence

**Symptôme** : Problèmes avec plusieurs instances

**Solutions** :
```bash
# Utiliser des dossiers de travail séparés
mkdir -p workspace1 workspace2
cd workspace1
glm

# Vérifier les verrous de fichiers
lsof | grep glmcode
```

### Problèmes de persistance

**Symptôme** : Perte de contexte entre les sessions

**Solutions** :
```bash
# Vérifier le fichier d'historique
ls -la ~/.glmcode/

# Exporter l'historique
cat ~/.glmcode/history.json

# Réinitialiser
rm ~/.glmcode/history.json
glm /reset
```

## Obtenir de l'aide

### Commandes intégrées

```bash
# Aide intégrée
glm /help

# Tester la connexion
glm /ping

# Vérifier la version
glm --version
```

### GitHub Issues

1. Créez un issue détaillé
2. Incluez :
   - Votre système d'exploitation
   - Version de Python
   - Version de GLM Code
   - Les étapes pour reproduire
   - Les messages d'erreur complets
   - Les logs si disponibles

### Communauté

- Discord/Slack : [Lien de la communauté]
- Discussions GitHub : [Lien des discussions]
- Email : [Email de support]

## Checklist de dépannage

1. [ ] Vérifier l'installation
2. [ ] Vérifier la configuration
3. [ ] Vérifier la connexion réseau
4. [ ] Vérifier les permissions
5. [ ] Vérifier les dépendances
6. [ ] Activer les logs
7. [ ] Tester avec un simple cas
8. [ ] Rechercher dans les issues existantes
9. [ ] Créer un nouveau issue si nécessaire

---

*Pour plus d'informations, consultez le [README principal](../README.md) et la [FAQ](FAQ.md).*