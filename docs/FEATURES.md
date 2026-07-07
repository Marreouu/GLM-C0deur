# Fonctionnalités - GLM Code

Ce document présente les fonctionnalités principales de GLM Code, avec des exemples concrets d'utilisation.

## Fonctionnalités principales

### 1. Interface utilisateur

#### TUI (Terminal User Interface)
- Interface plein écran avec Rich et prompt_toolkit
- Navigation au clavier et à la souris
- Historique des conversations scrollable
- Modes visuels (normal/auto/plan)

#### CLI (Command Line Interface)
- Interface simple pour les environnements limités
- Support des pipes et redirections

### 2. Système de conversation

#### Modes de travail
- **Normal** : Demande confirmation avant chaque action
- **Auto** : Exécute les actions sans demander confirmation
- **Plan** : Mode lecture seule, propose un plan d'action

#### Commandes slash
- `/help` : Affiche l'aide
- `/reset` : Efface l'historique
- `/model <nom>` : Change le modèle
- `/mode [nom]` : Change de mode
- `/skills` : Liste les skills
- `/session` : Affiche l'ID de session
- `/sessions` : Liste les sessions
- `/resume <id>` : Reprend une session
- `/exit` : Quitter

### 3. Système de sélection de fichiers

#### Mentions @fichier
GLM Code supporte les mentions `@fichier` pour joindre automatiquement le contenu des fichiers à vos messages. Cette fonctionnalité similaire à Claude Code permet de sélectionner facilement des fichiers du projet.

##### Utilisation
```bash
# Taper @ pour voir la liste des fichiers disponibles
@main.py

# Le contenu du fichier sera automatiquement joint à votre message
Analyse ce fichier @src/app.py et identifie les problèmes potentiels

# Comparer plusieurs fichiers
Compare ces fichiers @main.py @app.py et explique les différences
```

##### Fonctionnalités
- **Autocompletion** : Taper `@` déclenche la liste des fichiers du projet
- **Recherche intelligente** : Les fichiers sont triés par pertinence
- **Limites de sécurité** : Seuls les fichiers existants et lisibles sont joints
- **Taille maximale** : Les fichiers de plus de 20Ko sont tronqués

##### Configuration
La fonctionnalité utilise les paramètres suivants :

```toml
# Ignorer certains répertoires lors de la recherche de fichiers
ignore_dirs = [".git", "__pycache__", "node_modules", ".venv", "venv"]
```

### 4. Outils natifs

#### Outils de fichiers
- `read_file` : Lecture de fichiers
- `write_file` : Écriture de fichiers
- `edit_file` : Modification ciblée de fichiers
- `list_dir` : Listing de répertoires

#### Outils de commandes
- `run_command` : Exécution de commandes shell

### 5. Système de skills

#### Skills intégrés
- `revue-code` : Revue de code approfondie
- `debug` : Débogage d'erreurs
- `tests` : Génération de tests
- `generate-code` : Génération de code
- `refactor` : Refactoring de code

#### Skills personnalisés
- Création de skills via des fichiers Markdown
- Support des entêtes YAML
- Intégration avec le système de commandes

### 6. Mode orchestrateur

#### Architecture
- **Cerveau** : GLM-4.7 via API Z.ai (dialogue, planification)
- **Codeur** : Modèle local (ex: qwen2.5-coder via Ollama) pour la génération de code

#### Configuration
```toml
[coder]
enabled = true
base_url = "http://localhost:11434/v1"
model = "qwen2.5-coder:latest"
```

### 7. Architecture Runtime (Niveau Système)

#### Composants principaux
- **RuntimeManager** : Coordinateur principal de tous les composants système
- **EventBus** : Bus d'événements central pour la communication inter-composants
- **ShellManager** : Gestionnaire de shells persistants (PowerShell, CMD, Bash, WSL)
- **ProcessManager** : Gestionnaire de processus système avec suivi PID et logs
- **WatchManager** : Surveillance en temps réel des fichiers, dossiers et dépôts Git
- **BackgroundTasks** : Pool de workers pour l'exécution de tâches en arrière-plan
- **RuntimeCache** : Cache en mémoire avec expiration et politique LRU

#### Fonctionnalités clés
- **Shells persistants** : Les shells ne sont pas recréés à chaque commande, réduisant considérablement l'overhead
- **Surveillance en temps réel** : Détection immédiate des changements de fichiers, dossiers et Git
- **Architecture événementielle** : Toute la communication se fait via des événements, pas de polling inutile
- **Traitement en arrière-plan** : Indexation, calcul d'embeddings et autres tâches lourdes exécutés sans bloquer l'utilisateur
- **Gestion de processus** : Suivi complet du cycle de vie des processus (démarrage, arrêt, redémarrage, logs)
- **Cache intelligent** : Mise en cache efficace des résultats coûteux avec expiration automatique

#### Configuration
```toml
[runtime]
enabled = true
shell_history_size = 1000
file_watch_delay = 1.0
git_watch_delay = 5.0
background_workers = 4
cache_max_size = 1000
cache_default_ttl = 3600  # 1 heure en secondes
```

#### Utilisation programmatique
```python
from glmcode.runtime import (
    initialize_runtime, 
    get_shell_manager,
    get_watch_manager,
    get_background_tasks,
    background_task
)

# Initialiser le runtime au démarrage de l'application
initialize_runtime()

# Obtenir un shell persistant
shell = get_shell_manager().get_or_create_shell("powershell")
output = shell.execute_command("Get-Process | Select-Object -First 5")

# Surveiller un fichier pour les changements
def on_file_changed(file_path):
    print(f"Fichier modifié: {file_path}")
    # Déclencher une reanalyse ou d'autres actions

get_watch_manager().watch_file("src/config.py", on_file_changed)

# Exécuter une tâche en arrière-plan
@background_task("data_processing")
def process_large_dataset(data):
    # Traitement long qui ne bloque pas l'interface utilisateur
    result = expensive_computation(data)
    return result

# Utiliser le task handler pour suivre la progression
task_handle = process_large_dataset(large_data)
if task_handle.status()["status"] == "completed":
    result = task_handle.result()
    print(f"Résultat: {result}")
```

### 7. Gestion des sessions

#### Sauvegarde automatique
- Historique des conversations sauvegardé
- Reprise des sessions précédentes
- ID de session unique

#### Commandes de session
- `/session` : Affiche l'ID de session
- `/sessions` : Liste les sessions
- `/resume <id>` : Reprend une session

### 8. Configuration

#### Fichier config.toml
```toml
[zai]
api_key = "votre-cle-api"
model = "glm-4.5-flash"
temperature = 0.3

[coder]
enabled = false
model = "qwen2.5-coder"

[skills]
include_claude = false
dirs = []
```

#### Variables d'environnement
- `GLMCODE_API_KEY` : Clé API Z.ai
- `GLMCODE_MODEL` : Modèle principal
- `GLMCODE_AUTO_APPROVE` : Auto-approbation
- `GLMCODE_CODER_ENABLED` : Activation du codeur

## Exemples d'utilisation

### 1. Analyse de code
```bash
glm
Analyse ce fichier @src/app.py et identifie les problèmes potentiels
```

### 2. Création de projet
```bash
glm
Crée un projet Python avec un fichier main.py qui affiche "Hello World"
```

### 3. Utilisation des skills
```bash
glm
/revue-code src/app.py
```

### 4. Mode orchestrateur
```bash
glm
/coder enable
Crée une application web Flask complète avec authentification et base de données
```

### 5. Comparaison de fichiers
```bash
glm
Compare ces fichiers @v1/app.py @v2/app.py et explique les différences
```

## Bonnes pratiques

### 1. Sécurité
- Ne jamais joindre des fichiers sensibles
- Valider les chemins de fichiers
- Limiter la taille des fichiers joints

### 2. Performance
- Utiliser le mode auto pour les tâches répétitives
- Sauvegarder les sessions importantes
- Utiliser les skills pour les tâches spécifiques

### 3. Qualité
- Documenter les skills personnalisés
- Tester le code généré
- Utiliser le mode plan pour les revues de code

## Dépannage

### Problèmes courants
1. **Autocompletion non fonctionnelle** : Vérifier les permissions du projet
2. **Fichiers non joints** : Vérifier l'existence et la lisibilité des fichiers
3. **Mode orchestrateur non fonctionnel** : Vérifier Ollama et le modèle

### Solutions
1. `GLMCODE_SIMPLE=1 glm` : Mode simple sans TUI
2. `/reset` : Réinitialiser la conversation
3. `/ping` : Tester la connexion

## Conclusion

GLM Code offre une suite complète d'outils pour le développement logiciel, de l'analyse de code à la génération de projets complets. La fonctionnalité de sélection de fichiers avec @ améliore considérablement l'expérience utilisateur en permettant de joindre facilement des fichiers aux conversations.

Pour plus d'informations, consultez la [documentation complète](README.md) et les [tutoriels](TUTORIALS.md).