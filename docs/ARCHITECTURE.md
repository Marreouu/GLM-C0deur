# Architecture détaillée - GLM Code

Ce document décrit l'architecture interne de GLM Code, ses composants et leurs interactions.

## Vue d'ensemble

GLM Code est un assistant de codage en terminal basé sur une architecture modulaire avec séparation des responsabilités. L'application fonctionne selon le principe d'un agent conversationnel qui peut exécuter des outils pour interagir avec l'environnement.

### Flux de travail principal

```
Utilisateur → Interface (TUI/CLI) → Agent → LLM (GLM-4.7) → Outils → Fichiers/Commandes
```

## Composants principaux

### 1. Agent (`agent.py`)

L'agent est le cœur de l'application. Il orchestre l'interaction entre l'utilisateur, le LLM et les outils.

#### Responsabilités
- Gestion du contexte conversationnel
- Exécution des appels d'outils
- Gestion des modes de travail (normal/auto/plan)
- Implémentation du mode orchestrateur

#### Flux de travail

1. **Réception d'un message utilisateur** :
   ```python
   def send(self, user_input: str) -> None:
       self.messages.append({"role": "user", "content": user_input})
       self._run_turn()
   ```

2. **Exécution d'un tour** :
   - Choix des outils selon le mode
   - Appel au LLM avec streaming
   - Exécution des outils demandés
   - Mise à jour du contexte

3. **Exécution d'un outil** :
   - Validation des arguments
   - Confirmation pour les outils destructifs (sauf mode auto)
   - Exécution de la fonction
   - Gestion des erreurs

#### Modes de travail

- **Normal** : Demande confirmation avant chaque action destructrice
- **Auto** : Exécute les actions sans demander confirmation
- **Plan** : Mode lecture seule, propose un plan d'action

#### Mode orchestrateur

Lorsque activé, l'agent utilise deux modèles :
- **Cerveau** : GLM-4.7 via API Z.ai (dialogue, planification)
- **Codeur** : Modèle local (ex: qwen2.5-coder via Ollama) pour la génération de code

Le cerveau peut déléguer les tâches de codage complexes au codeur via l'outil `deleguer_codeur`.

### 2. Client HTTP (`client.py`)

Gère la communication avec l'API Z.ai avec support du streaming et gestion des erreurs.

#### Fonctionnalités

- Streaming des réponses en Server-Sent Events
- Gestion des erreurs transitoires (rate limit, surcharge)
- Bascule automatique vers un modèle de secours
- Support du tool-calling

#### Implémentation

```python
class LLMClient:
    def stream_chat(self, messages, tools=None, on_text=None, on_notice=None):
        # Préparation de la requête
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }
        
        # Ajout des outils si fournis
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        # Envoi de la requête
        resp = self._session.post(self._url(), headers=self._headers, json=payload, stream=True)
        
        # Traitement du streaming
        for line in resp.iter_lines():
            # Parsing et traitement des chunks
            pass
```

#### Gestion des erreurs

- **Codes retryables** : 1302 (rate limit), 1305 (surcharge), 429, 5xx
- **Bascule de modèle** : Si le modèle principal est indisponible
- **Retries automatiques** : Jusqu'à `max_retries` tentatives

### 3. Système d'outils (`tools.py`)

Implémentation des outils natifs que le LLM peut appeler.

#### Outils disponibles

| Outil | Description | Destructif | Requis |
|-------|-------------|------------|--------|
| `read_file` | Lecture de fichiers | Non | Oui |
| `write_file` | Écriture de fichiers | Oui | Oui |
| `edit_file` | Modification ciblée | Oui | Oui |
| `list_dir` | Listing de répertoires | Non | Non |
| `run_command` | Exécution de commandes | Oui | Oui |

#### Implémentation

Chaque outil expose :
- Un schéma JSON (format OpenAI)
- Une fonction d'implémentation

Exemple pour `read_file` :
```python
def read_file(path: str, **_) -> str:
    p = _safe_path(path)
    if not p.is_file():
        return f"[erreur] Fichier introuvable : {path}"
    data = p.read_bytes()[:MAX_READ_BYTES]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return f"[erreur] Fichier binaire ou encodage non-UTF8 : {path}"
    return text
```

#### Gestion des permissions

- **Outils destructifs** : Nécessitent confirmation en mode normal
- **Mode plan** : Accès uniquement aux outils en lecture seule
- **Validation des chemins** : Empêche l'accès à des fichiers sensibles

### 4. Interface utilisateur (`ui.py`)

Gère l'affichage et l'interaction avec l'utilisateur.

#### Composants

- **Console Rich** : Affichage coloré et formaté
- **Session prompt_toolkit** : Saisie avec complétion et historique
- **Gestion des modes** : Affichage visuel du mode courant
- **Prévisualisation** : Affichage des modifications avant application

#### Implémentation

```python
def print_stream_chunk(text: str) -> None:
    console.print(text, end="", highlight=False, soft_wrap=True)

def print_diff_preview(path: str, content: str, lang: str = "text") -> None:
    console.print(
        Panel(
            Syntax(content[:2000], lang, theme="monokai", word_wrap=True),
            title=f"[bold]{escape(path)}[/]",
            title_align="left",
            border_style=CYAN,
            padding=(0, 1),
        )
    )
```

#### Modes d'interface

- **TUI (Terminal User Interface)** : Interface plein écran avec barre d'état
- **CLI (Command Line Interface)** : Interface ligne par ligne (fallback)

### 5. Système de configuration (`config.py`)

Gestion centralisée de la configuration avec priorité multiple.

#### Priorité

1. Variables d'environnement `GLMCODE_*`
2. Fichier `config.toml` dans le dossier courant
3. Fichier `~/.glmcode/config.toml`
4. Valeurs par défaut

#### Structure

```python
@dataclass
class Config:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    fallback_model: str = "glm-4.5-flash"
    max_retries: int = 3
    temperature: float = 0.3
    max_tokens: int = 8192
    auto_approve: bool = False
    system_prompt: str = ""
    coder: CoderConfig = field(default_factory=CoderConfig)
    skills_dirs: list = field(default_factory=list)
    include_claude_skills: bool = False
```

#### Chargement

```python
def load_config() -> Config:
    data: dict = {}
    for path in _config_search_paths():
        found = _load_toml(path)
        if found:
            data = found
            break
    
    # Application de la priorité environnement
    return Config(
        api_key=pick("GLMCODE_API_KEY", "api_key", ""),
        # ... autres paramètres
    )
```

### 6. Système de skills (`skills.py`)

Système d'extension basé sur des fichiers Markdown.

#### Structure d'un skill

```yaml
---
name: nom-du-skill
description: Description du skill
---

Instructions du skill...
```

#### Chemin de recherche

1. `./skills/` (projet courant)
2. `~/.glmcode/skills/` (global)
3. `glmcode/builtin_skills/` (intégré)
4. Skills Claude (optionnel)

#### Implémentation

```python
def load_skills(extra_dirs: list[str] | None = None, include_claude: bool = False) -> dict[str, Skill]:
    dirs: list[tuple[Path, str]] = [
        (Path.cwd() / "skills", "projet"),
        (Path.home() / ".glmcode" / "skills", "global"),
        (Path(__file__).parent / "builtin_skills", "integre"),
    ]
    
    skills: dict[str, Skill] = {}
    for directory, source in dirs:
        if directory.is_dir():
            _scan_dir(directory, source, skills)
    return skills
```

### 7. Codeur délégué (`coder.py`)

Pour le mode orchestrateur, permet de déléguer les tâches de codage à un modèle spécialisé.

#### Flux de travail

1. Le cerveau analyse la demande
2. Pour les tâches complexes, il délègue au codeur
3. Le codeur génère le code dans un format structuré
4. Le cerveau vérifie et applique les résultats

#### Format de sortie

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

#### Implémentation

```python
class Coder:
    def implement(self, task: str, files: list[str], auto_apply: bool) -> str:
        # Préparation du contexte
        context = ""
        for path in files or []:
            content = read_file(path)
            context += f"\n----- {path} -----\n{content}\n"
        
        # Appel au codeur
        messages = [
            {"role": "system", "content": CODER_SYSTEM},
            {"role": "user", "content": user},
        ]
        
        # Traitement de la réponse
        message = self.client.stream_chat(messages, on_text=ui.print_coder_chunk)
        
        # Application des résultats
        blocks = _BLOCK_RE.findall(message.get("content", ""))
        for path, body in blocks:
            if not auto_apply:
                ui.print_diff_preview(path, body, _lang_for(path))
                if not ui.confirm(f"Appliquer le fichier {path} ?"):
                    continue
            write_file(path, body)
```

## Flux de données

### Contexte conversationnel

Le contexte est stocké dans une liste de messages :

```python
self.messages: list[dict[str, Any]] = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_input},
    {"role": "assistant", "content": response},
    {"role": "tool", "content": tool_result},
]
```

### Exécution d'un outil

1. **Appel du LLM** : Le LLM demande d'exécuter un outil
2. **Validation** : Vérification des arguments et permissions
3. **Confirmation** : Demande à l'utilisateur si nécessaire
4. **Exécution** : Appel de la fonction d'implémentation
5. **Résultat** : Retour du résultat au LLM
6. **Mise à jour** : Ajout du résultat au contexte

### Gestion des erreurs

1. **Erreurs LLM** : Retries automatiques, bascule de modèle
2. **Erreurs outils** : Messages d'erreur formatés
3. **Erreurs système** : Logging et gestion gracieuse

## Performance et optimisation

### Streaming

- Réponses en temps réel avec Server-Sent Events
- Affichage progressif du contenu
- Gestion des interruptions

### Gestion mémoire

- Limite de lecture des fichiers (100Ko max)
- Contexte conversationnel géré
- Cache des configurations lourdes

### Réseau

- Retries intelligents
- Bascule de modèle
- Timeout adaptatifs

## Sécurité

### Validation des entrées

- Validation des chemins de fichiers
- Échappement des sorties utilisateur
- Limite des commandes shell

### Protection contre les abus

- Timeout sur les commandes longues
- Limite des ressources système
- Pas d'exécution de code arbitraire

### Configuration sécurisée

- Clés API non stockées en clair
- Support des variables d'environnement
- Fichiers de configuration ignorés par git

## Tests

### Unitaires

- Test de chaque composant isolément
- Mock des dépendances externes
- Couverture de 80% minimum

### Intégration

- Test du flux complet
- Simulation des interactions utilisateur
- Test des erreurs système

### E2E

- Test sur différents environnements
- Test des cas limites
- Performance under load

## Extension et personnalisation

### Ajout d'outils

```python
# Définition du schéma
TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "nouvel_outil",
        "description": "Description de l'outil",
        "parameters": {...}
    }
})

# Implémentation
TOOL_IMPLS["nouvel_outil"] = nouvel_outil
```

### Ajout de skills

1. Créer un fichier Markdown
2. Ajouter l'entête YAML
3. Placer dans le bon dossier
4. Tester l'invocation

### Personnalisation de l'interface

- Modifier les couleurs dans `ui.py`
- Ajouter de nouveaux types de messages
- Personnaliser le prompt

## Déploiement et distribution

### Package Python

- Métadonnées dans `pyproject.toml`
- Script d'installation
- Dépendances gérées

### Docker

- Image légère
- Multi-stage build
- Optimisation pour la production

### Documentation

- Documentation utilisateur
- Documentation technique
- Exemples et tutoriels

## Conclusion

L'architecture de GLM Code est conçue pour être :
- **Modulaire** : Composants indépendants
- **Extensible** : Facile d'ajouter de nouvelles fonctionnalités
- **Robuste** : Gestion d'erreurs complète
- **Performante** : Optimisation pour l'usage en terminal
- **Sécurisée** : Protection contre les abus

Cette architecture permet de maintenir et faire évoluer l'application facilement tout en garantissant la qualité et la stabilité.