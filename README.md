# GLM Code

Assistant de codage en terminal, propulsé par l'API Z.ai (GLM). Il lit et écrit
des fichiers, lance des commandes shell et garde le contexte de la session, dans
une interface inspirée de Claude Code.

> Version 0.1.0 — projet personnel en cours de développement.

## Architecture cerveau / codeur

Deux modèles se répartissent le travail :

| Rôle | Modèle par défaut | Fournisseur | Coût |
|------|-------------------|-------------|------|
| **Cerveau** — conversation, décisions, appels d'outils | `glm-4.5-flash` | API Z.ai | gratuit |
| **Codeur** — génération de code déléguée | `qwen/qwen3-coder:free` | OpenRouter | gratuit |

Le codeur est optionnel : désactive la section `[coder]` pour tout faire passer
par le cerveau.

## Installation

Python 3.11 ou plus récent est requis.

```bash
git clone https://github.com/<utilisateur>/<depot>.git
cd <depot>
pip install -e .
```

Cela installe les dépendances et expose la commande `glm`.

Pour installer seulement les dépendances, sans le point d'entrée :

```bash
pip install -r requirements.txt
```

## Configuration

Copie le modèle de configuration et renseigne ta clé API :

```bash
cp config.example.toml config.toml
```

```toml
[zai]
api_key = "ta-cle-zai"
model = "glm-4.5-flash"

[coder]
enabled = true
api_key = "ta-cle-openrouter"
model = "qwen/qwen3-coder:free"
```

Les fichiers de configuration sont cherchés dans cet ordre :

1. les variables d'environnement `GLMCODE_*` (et `ZAI_API_KEY`) ;
2. `./config.toml` dans le dossier courant ;
3. `~/.glmcode/config.toml`.

`config.toml` est exclu du dépôt par `.gitignore` — ta clé API ne part jamais
sur GitHub.

## Utilisation

```bash
glm                      # démarre l'assistant dans le dossier courant
glm --continue           # reprend la dernière session
glm --resume <ID>        # reprend une session précise
glm --list-sessions      # liste les sessions enregistrées
glm --version
```

### Modes

On bascule d'un mode à l'autre avec <kbd>Shift</kbd>+<kbd>Tab</kbd>, ou avec
`/mode <nom>`.

| Mode | Comportement |
|------|--------------|
| `normal` | demande confirmation avant chaque écriture ou commande |
| `auto` | exécute les actions sans demander |
| `plan` | lecture seule : propose un plan sans rien modifier |

### Commandes

| Commande | Effet |
|----------|-------|
| `/help` | affiche l'aide |
| `/reset` | efface l'historique de la conversation |
| `/model <nom>` | change le modèle courant |
| `/mode [nom]` | change de mode |
| `/skills` | liste les skills disponibles |
| `/<skill> [texte]` | invoque un skill (ex. `/revue-code app.py`) |
| `/session`, `/sessions`, `/resume [id]` | gestion des sessions |
| `/ping` | teste la connexion au backend |
| `/update`, `/check-update`, `/version` | mises à jour |
| `/exit`, `/quit` | quitte |

### Joindre un fichier

Tape `@` pour ouvrir l'autocomplétion des fichiers du projet. Le contenu du
fichier mentionné est joint au message envoyé :

```
> corrige le bug de scroll dans @glmcode/tui.py
```

### Raccourcis

| Touche | Effet |
|--------|-------|
| <kbd>Shift</kbd>+<kbd>Tab</kbd> | change de mode |
| <kbd>Ctrl</kbd>+<kbd>C</kbd> | interrompt la requête en cours (deux fois pour quitter) |
| <kbd>Ctrl</kbd>+<kbd>D</kbd> | quitte |
| <kbd>PgUp</kbd> / <kbd>PgDn</kbd> | défile le transcript |

Si le mode plein écran pose problème sur ton terminal, `GLMCODE_SIMPLE=1 glm`
force une boucle ligne à ligne.

## Skills

Un skill est un fichier Markdown décrivant une tâche répétitive, invocable par
`/<nom>`. Les skills fournis (`/debug`, `/explique`, `/revue-code`, `/tests`,
`/refactor`…) sont dans `glmcode/builtin_skills/`.

Pour en ajouter, dépose tes `.md` dans un dossier et déclare-le :

```toml
[skills]
include_claude = true   # charge aussi les skills Claude Code s'ils sont présents
dirs = ["./mes-skills"]
```

## Structure

```
glmcode/
  cli.py         boucle REPL et commandes slash
  tui.py         interface terminal (barre épinglée, autocomplétion)
  ui.py          rendu du transcript et thème
  agent.py       orchestration du dialogue et des outils
  client.py      client HTTP de l'API Z.ai (streaming)
  coder.py       délégation au modèle codeur
  tools.py       outils : lecture/écriture de fichiers, shell
  config.py      chargement de la configuration
  session.py     persistance des sessions
  runtime.py     surveillance de fichiers, services de fond
  builtin_skills/  skills fournis
```

## Tests

```bash
python -m pytest glmcode/test_tui.py glmcode/test_cli.py
```

## Licence

Projet personnel, sans licence explicite pour le moment.
