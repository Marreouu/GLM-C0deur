# Documentation technique - GLM Code

## Table des matières
- [Architecture](#architecture)
- [Modules principaux](#modules-principaux)
- [Système de configuration](#système-de-configuration)
- [Outils natifs](#outils-natifs)
- [Système de skills](#système-de-skills)
- [Mode orchestrateur](#mode-orchestrateur)
- [Système de sélection de fichiers](#système-de-sélection-de-fichiers)
- [Guide de développement](development.md)
- [Guide de contribution](contributing.md)
- [Fonctionnalités](FEATURES.md)
- [Exemples d'utilisation](examples.md)
- [Tutoriels](TUTORIALS.md)

## Architecture

GLM Code est un assistant de codage en terminal basé sur une architecture modulaire avec séparation des responsabilités. L'application fonctionne selon le principe d'un agent conversationnel qui peut exécuter des outils pour interagir avec l'environnement.

### Flux de travail principal

```
Utilisateur → Interface (TUI/CLI) → Agent → LLM (GLM-4.7) → Outils → Fichiers/Commandes
```

### Composants architecturaux

1. **Agent** : Cœur de l'application, gère la conversation et l'exécution d'outils
2. **Client LLM** : Gère la communication avec l'API Z.ai
3. **Système d'outils** : Fonctionnalités de base (lecture/écriture fichiers, exécution commandes)
4. **Interface utilisateur** : Couche présentation avec Rich et prompt_toolkit
5. **Système de configuration** : Gestion centralisée des paramètres
6. **Système de skills** : Extension via des fichiers Markdown
7. **Codeur délégué** : Pour le mode orchestrateur

## Modules principaux

### `agent.py` - Agent conversationnel

L'agent est le composant central qui orchestre l'interaction entre l'utilisateur, le LLM et les outils.

**Responsabilités :**
- Gestion du contexte conversationnel
- Exécution des appels d'outils
- Gestion des modes de travail (normal/auto/plan)
- Implémentation du mode orchestrateur

**Classe principale :** `Agent`
- Méthodes clés : `send()`, `_run_turn()`, `_execute_tool()`

### `client.py` - Client HTTP

Gère la communication avec l'API Z.ai avec support du streaming et gestion des erreurs.

**Fonctionnalités :**
- Streaming des réponses en Server-Sent Events
- Gestion des erreurs transitoires (rate limit, surcharge)
- Bascule automatique vers un modèle de secours
- Support du tool-calling

**Classe principale :** `LLMClient`
- Méthodes clés : `stream_chat()`, `ping()`

### `tools.py` - Système d'outils

Implémentation des outils natifs que le LLM peut appeler.

**Outs disponibles :**
- `read_file` : Lecture de fichiers
- `write_file` : Écriture de fichiers
- `edit_file` : Modification ciblée de fichiers
- `list_dir` : Listing de répertoires
- `run_command` : Exécution de commandes shell

**Gestion des permissions :**
- Outils destructifs (`write_file`, `edit_file`, `run_command`) nécessitent confirmation en mode normal
- Mode plan : accès uniquement aux outils en lecture seule

### `ui.py` - Interface utilisateur

Gère l'affichage et l'interaction avec l'utilisateur.

**Composants :**
- Console Rich pour l'affichage coloré
- Session prompt_toolkit pour la saisie
- Gestion des modes visuels
- Prévisualisation des modifications

### `config.py` - Système de configuration

Gestion centralisée de la configuration avec priorité multiple.

**Priorité :**
1. Variables d'environnement `GLMCODE_*`
2. Fichier `config.toml` dans le dossier courant
3. Fichier `~/.glmcode/config.toml`
4. Valeurs par défaut

**Sections :**
- `[zai]` : Configuration API Z.ai
- `[coder]` : Configuration du codeur délégué
- `[skills]` : Configuration des skills

### `skills.py` - Système de skills

Système d'extension basé sur des fichiers Markdown.

**Structure d'un skill :**
```yaml
---
name: nom-du-skill
description: Description du skill
---

Instructions du skill...
```

**Chemin de recherche :**
1. `./skills/` (projet courant)
2. `~/.glmcode/skills/` (global)
3. `glmcode/builtin_skills/` (intégré)

### `coder.py` - Codeur délégué

Pour le mode orchestrateur, permet de déléguer les tâches de codage à un modèle spécialisé.

**Format de sortie :**
```
=== FICHIER: chemin/du/fichier ===
contenu complet du fichier
=== FIN ===
```

## Système de configuration

### Structure du fichier config.toml

```toml
# Configuration API Z.ai
[zai]
api_key = "ta-cle-api"
base_url = "https://api.z.ai/api/paas/v4"
model = "glm-4.5-flash"
fallback_model = "glm-4.5-flash"
max_retries = 3
temperature = 0.3
max_tokens = 8192

# Configuration générale
auto_approve = false

# Configuration du codeur (orchestrateur)
[coder]
enabled = true
base_url = "http://localhost:11434/v1"
model = "qwen2.5-coder:latest"
api_key = ""
fallback_model = ""
max_retries = 3
temperature = 0.2
max_tokens = 8192

# Configuration des skills
[skills]
include_claude = false
dirs = ["/chemin/vers/skills/personnels"]
```

### Variables d'environnement supportées

| Variable | Description |
|----------|-------------|
| `GLMCODE_API_KEY` | Clé API Z.ai |
| `GLMCODE_MODEL` | Modèle principal |
| `GLMCODE_BASE_URL` | URL de l'endpoint |
| `GLMCODE_FALLBACK_MODEL` | Modèle de secours |
| `GLMCODE_MAX_RETRIES` | Nombre de tentatives |
| `GLMCODE_TEMPERATURE` | Température du LLM |
| `GLMCODE_MAX_TOKENS` | Tokens max |
| `GLMCODE_AUTO_APPROVE` | Auto-approbation |
| `GLMCODE_CODER_ENABLED` | Activation du codeur |
| `GLMCODE_CODER_MODEL` | Modèle du codeur |
| `GLMCODE_CODER_BASE_URL` | URL du codeur |
| `GLMCODE_CLAUDE_SKILLS` | Intégration skills Claude |

## Outils natifs

### Schéma des outils

Chaque outil expose :
- Un schéma JSON (format OpenAI)
- Une fonction d'implémentation

#### read_file
```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Lit et renvoie le contenu texte d'un fichier.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Chemin du fichier à lire"}
      },
      "required": ["path"]
    }
  }
}
```

#### write_file
```json
{
  "type": "function",
  "function": {
    "name": "write_file",
    "description": "Crée ou remplace entièrement un fichier avec le contenu fourni.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Chemin du fichier"},
        "content": {"type": "string", "description": "Contenu complet du fichier"}
      },
      "required": ["path", "content"]
    }
  }
}
```

#### edit_file
```json
{
  "type": "function",
  "function": {
    "name": "edit_file",
    "description": "Remplace une occurrence unique de texte dans un fichier existant.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Chemin du fichier"},
        "old": {"type": "string", "description": "Texte exact à remplacer (unique)"},
        "new": {"type": "string", "description": "Nouveau texte"}
      },
      "required": ["path", "old", "new"]
    }
  }
}
```

#### list_dir
```json
{
  "type": "function",
  "function": {
    "name": "list_dir",
    "description": "Liste les fichiers et dossiers d'un répertoire.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Chemin du dossier (défaut: .)"}
      }
    }
  }
}
```

#### run_command
```json
{
  "type": "function",
  "function": {
    "name": "run_command",
    "description": "Exécute une commande shell et renvoie sa sortie. À utiliser avec prudence.",
    "parameters": {
      "type": "object",
      "properties": {
        "command": {"type": "string", "description": "Commande à exécuter"}
      },
      "required": ["command"]
    }
  }
}
```

## Système de sélection de fichiers

### Mentions @fichier

GLM Code supporte les mentions `@fichier` pour joindre automatiquement le contenu des fichiers à vos messages. Cette fonctionnalité similaire à Claude Code permet de sélectionner facilement des fichiers du projet.

#### Utilisation

```bash
# Taper @ pour voir la liste des fichiers disponibles
@main.py

# Le contenu du fichier sera automatiquement joint à votre message
Analyse ce fichier @src/app.py et identifie les problèmes potentiels
```

#### Fonctionnalités

- **Autocompletion** : Taper `@` déclenche la liste des fichiers du projet
- **Recherche intelligente** : Les fichiers sont triés par pertinence
- **Limites de sécurité** : Seuls les fichiers existants et lisibles sont joints
- **Taille maximale** : Les fichiers de plus de 20Ko sont tronqués

#### Configuration

La fonctionnalité utilise les paramètres suivants :

```toml
# Ignorer certains répertoires lors de la recherche de fichiers
ignore_dirs = [".git", "__pycache__", "node_modules", ".venv", "venv"]
```

## Système de skills

### Format des skills

Les skills sont des fichiers Markdown avec un entête YAML optionnel :

```yaml
---
name: revue-code
description: Revue de code approfondie
---

# Revue de code

Analyse le code fourni selon les critères suivants :
1. Qualité du code
2. Performance
3. Sécurité
4. Maintenabilité

Pour chaque fichier, fournis :
- Un résumé des points forts
- Les axes d'amélioration
- Les suggestions de refactoring
```

### Types de skills

1. **Skills intégrés** : Dans `glmcode/builtin_skills/`
2. **Skills globaux** : Dans `~/.glmcode/skills/`
3. **Skills de projet** : Dans `./skills/`
4. **Skills Claude** : Intégration avec les skills de Claude Code

### Invocation des skills

```bash
/skills                    # Liste tous les skills disponibles
/revue-code               # Invoque le skill revue-code
/revue-code app.py        # Invoque le skill avec un argument
```

## Mode orchestrateur

### Architecture

Le mode orchestrateur utilise deux modèles :
- **Cerveau** : GLM-4.7 via API Z.ai (dialogue, planification)
- **Codeur** : Modèle local (ex: qwen2.5-coder via Ollama) pour la génération de code

### Flux de travail

1. Le cerveau analyse la demande
2. Pour les tâches complexes, il délègue au codeur via `deleguer_codeur`
3. Le codeur génère le code dans un format structuré
4. Le cerveau vérifie et applique les résultats

### Configuration requise

```toml
[coder]
enabled = true
base_url = "http://localhost:11434/v1"
model = "qwen2.5-coder:latest"
```

### Prérequis

- Ollama installé
- Modèle téléchargé : `ollama pull qwen2.5-coder`

### Format de sortie du codeur

```
=== FICHIER: src/main.py ===
import sys

def main():
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
=== FIN ===
```

## Bonnes pratiques

### Développement

1. Utiliser les types hints partout
2. Gérer les exceptions avec précision
3. Documenter les fonctions et classes
4. Tester les cas limites

### Performance

1. Limiter la taille des fichiers lus (100Ko max)
2. Utiliser le streaming pour les réponses longues
3. Mettre en cache les configurations lourdes
4. Optimiser les appels réseau

### Sécurité

1. Valider tous les chemins de fichiers
2. Échapper les sorties utilisateur
3. Limiter le temps d'exécution des commandes
4. Ne jamais logger les clés API

### Maintenance

1. Maintenir la compatibilité ascendante
2. Documenter les changements majeurs
3. Utiliser des versions sémantiques
4. Tenir à jour les dépendances