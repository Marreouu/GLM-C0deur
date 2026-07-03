# Guide de développement - GLM Code

Ce guide explique comment développer, tester et contribuer au projet GLM Code.

## Environnement de développement

### Prérequis

- Python 3.11 ou supérieur
- Git
- Ollama (optionnel, pour le mode orchestrateur)
- Poetry ou pip (pour la gestion des dépendances)

### Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/votre-organisation/glm-code.git
cd glm-code
```

2. Créer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. (Optionnel) Installer en mode développement :
```bash
pip install -e .
```

### Configuration du développement

1. Créer un fichier de configuration pour le développement :
```bash
cp config.example.toml config.toml
```

2. Configurer votre clé API Z.ai dans `config.toml` :
```toml
[zai]
api_key = "votre-cle-api-zai"
```

3. Configurer le mode orchestrateur (optionnel) :
```toml
[coder]
enabled = true
base_url = "http://localhost:11434/v1"
model = "qwen2.5-coder:latest"
```

## Structure du projet

```
glm-code/
├── glmcode/                 # Package principal
│   ├── __init__.py
│   ├── __main__.py
│   ├── agent.py            # Agent conversationnel
│   ├── client.py           # Client HTTP
│   ├── config.py           # Configuration
│   ├── tools.py            # Outils natifs
│   ├── ui.py               # Interface utilisateur
│   ├── skills.py           # Système de skills
│   ├── coder.py            # Codeur délégué
│   ├── cli.py              # Interface CLI
│   ├── tui.py              # Interface TUI
│   └── builtin_skills/     # Skills intégrés
├── docs/                   # Documentation
├── tests/                  # Tests
├── config.example.toml     # Exemple de configuration
├── pyproject.toml         # Métadonnées du projet
├── requirements.txt        # Dépendances
└── README.md              # Documentation utilisateur
```

## Développement des modules

### 1. Agent (`agent.py`)

L'agent est le cœur de l'application. Pour le modifier :

```python
# Exemple : Ajouter un nouveau mode de travail
class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.client = LLMClient(config)
        self.mode = "normal"  # Ajouter un nouveau mode
    
    def cycle_mode(self) -> str:
        # Ajouter la logique pour le nouveau mode
        pass
```

### 2. Client HTTP (`client.py`)

Pour modifier la gestion des requêtes :

```python
# Exemple : Ajouter un nouveau type de gestion d'erreur
class LLMClient:
    def stream_chat(self, messages, tools=None, on_text=None, on_notice=None):
        # Ajouter la logique pour gérer un nouveau type d'erreur
        pass
```

### 3. Outils (`tools.py`

Pour ajouter un nouvel outil :

```python
# Exemple : Ajouter un outil git
def git_commit(message: str, **_) -> str:
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            timeout=30
        )
        return f"[code retour {result.returncode}]\n{result.stdout}"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande interrompue (timeout 30s)"
    except Exception as e:
        return f"[erreur] {str(e)}"

# Ajouter au schéma
TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "git_commit",
        "description": "Effectue un commit git avec le message fourni.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message du commit"}
            },
            "required": ["message"]
        }
    }
})

# Ajouter à l'implémentation
TOOL_IMPLS["git_commit"] = git_commit
```

### 4. Interface utilisateur (`ui.py`)

Pour modifier l'interface :

```python
# Exemple : Ajouter un nouveau type de message
def print_custom_message(message: str) -> None:
    console.print(f"[bold {PURPLE}]ℹ[/] [{FG}]{escape(message)}[/]")
```

### 5. Système de skills (`skills.py`)

Pour ajouter un nouveau skill intégré :

1. Créer le fichier skill dans `glmcode/builtin_skills/`
2. Le nom du fichier devient le nom du skill

Exemple : `glmcode/builtin_skills/debug.md`
```yaml
---
name: debug
description: Débogage de code
---

# Débogage de code

Analyse le code pour trouver les erreurs courantes :
- Syntax errors
- Logic errors
- Performance issues
- Security vulnerabilities
```

## Tests

### Structure des tests

```
tests/
├── __init__.py
├── test_agent.py
├── test_client.py
├── test_config.py
├── test_tools.py
├── test_ui.py
├── test_skills.py
└── test_coder.py
```

### Exemple de test

```python
# tests/test_agent.py
import pytest
from glmcode.agent import Agent
from glmcode.config import Config

def test_agent_initialization():
    config = Config()
    agent = Agent(config)
    assert agent.mode == "auto"  # Valeur par défaut si auto_approve=True
    assert agent.config == config

def test_agent_cycle_mode():
    config = Config()
    agent = Agent(config)
    initial_mode = agent.mode
    agent.cycle_mode()
    assert agent.mode != initial_mode
```

### Exécution des tests

```bash
# Exécuter tous les tests
pytest

# Exécuter avec coverage
pytest --cov=glmcode

# Exécuter un test spécifique
pytest tests/test_agent.py

# Exécuter en mode verbos
pytest -v
```

### Tests d'intégration

Pour tester l'application complète :

```python
# tests/test_integration.py
def test_full_workflow():
    # Configurer l'agent
    config = Config()
    agent = Agent(config)
    
    # Simuler une conversation
    agent.send("Crée un fichier test.txt avec 'Hello World'")
    
    # Vérifier que le fichier a été créé
    assert Path("test.txt").exists()
    assert Path("test.txt").read_text() == "Hello World"
```

## Débogage

### Debuggage avec pdb

```python
# Insérer un point d'arrêt
import pdb; pdb.set_trace()

# Ou utiliser la commande pdb
python -m pdb -m glmcode
```

### Debuggage avec VS Code

1. Créer un fichier `.vscode/launch.json` :
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

2. Définir des points d'arrêt dans le code

### Logging

Activer le logging pour le débogage :

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance

### Optimisation

1. **Lecture de fichiers** : Limiter à 100Ko max
2. **Streaming** : Utiliser le streaming pour les réponses longues
3. **Cache** : Mettre en cache les configurations lourdes
4. **Réseau** : Optimiser les appels HTTP

### Profilage

```python
# Exemple de profilage
import cProfile
import pstats

def profile_agent():
    config = Config()
    agent = Agent(config)
    cProfile.run('agent.send("Hello")', 'profile_stats')
    
    stats = pstats.Stats('profile_stats')
    stats.sort_stats('cumulative')
    stats.print_stats()

profile_agent()
```

## Documentation

### Documentation du code

Utiliser des docstrings conformes à PEP 257 :

```python
def read_file(path: str, **_) -> str:
    """
    Lit et renvoie le contenu texte d'un fichier.
    
    Args:
        path: Chemin du fichier à lire
        
    Returns:
        Contenu du fichier ou message d'erreur
        
    Raises:
        FileNotFoundError: Si le fichier n'existe pas
    """
    pass
```

### Génération de documentation

Utiliser Sphinx pour générer la documentation :

```bash
# Installer Sphinx
pip install sphinx sphinx-rtd-theme

# Créer la documentation
sphinx-quickstart docs/source
```

## Bonnes pratiques

### Code style

1. **PEP 8** : Respecter le style Python
2. **Black** : Formatter le code automatiquement
3. **Flake8** : Vérifier la qualité du code
4. **MyPy** : Vérifier les types

### Exemple de configuration .pre-commit

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
```

### Git workflow

1. **Branches** : Utiliser des branches fonctionnelles
2. **Commits** : Commits atomiques et descriptifs
3. **Pull Requests** : PR détaillées avec tests
4. **Reviews** : Code review obligatoire

### Exemple de commit

```bash
git checkout -b feature/nouvel-outil
# Modifier le code
git add .
git commit -m "feat: ajouter l'outil git_commit"
git push origin feature/nouvel-outil
# Créer une PR
```

## Déploiement

### Création d'une release

1. Mettre à jour la version dans `pyproject.toml`
2. Créer un tag
3. Publier sur PyPI

```bash
# Mettre à jour la version
sed -i 's/version = ".*"/version = "0.2.0"/' pyproject.toml

# Créer un tag
git tag -a v0.2.0 -m "Version 0.2.0"

# Pousser le tag
git push origin v0.2.0

# Publier sur PyPI
python -m build
twine upload dist/*
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

CMD ["glm"]
```

## Dépannage courant

### Problèmes courants

1. **API Key manquante** : Vérifier `config.toml` ou la variable d'environnement
2. **Module non trouvé** : Vérifier l'installation avec `pip install -e .`
3. **Ollama non démarré** : Démarrer Ollama pour le mode orchestrateur
4. **Terminal non supporté** : Utiliser `GLMCODE_SIMPLE=1` pour le mode simple

### Debuggage des erreurs

1. Activer le logging :
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. Tester la connexion API :
```bash
glm /ping
```

3. Vérifier la configuration :
```bash
glm --version
```

## Contribuer

Voir [contributing.md](contributing.md) pour les instructions de contribution.