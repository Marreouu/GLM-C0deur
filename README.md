![Logo](https://image.noelshack.com/fichiers/2026/28/2/1783430000-image.png)

# GLM Code

Assistant de codage en terminal, propulsé par l'API Z.ai (GLM). Il lit et écrit
des fichiers, lance des commandes shell et garde le contexte de la session, dans
une interface inspirée de Claude Code.

> **v0.1.0 — version de test, en cours d'amélioration.**

## Fonctionnalités

- **Architecture cerveau / codeur** — la conversation et la génération de code
  sont confiées à deux modèles distincts.
- **Édition de fichiers et exécution de commandes**, avec confirmation selon le
  mode choisi.
- **Skills personnalisables** — des fichiers Markdown invocables par `/<nom>`.
- **Sessions persistantes** — reprise du travail avec `--continue` ou `--resume`.
- **Interface épinglée** — le transcript défile au-dessus d'une barre de saisie
  et de statut qui reste visible.
- **Compteur de tokens** en direct dans la barre de statut.
- **Surveillance de fichiers** — l'agent est réveillé quand un fichier change en
  dehors de l'assistant.
- **Multiplateforme** — Windows, Linux et macOS.

## Architecture cerveau / codeur

| Rôle | Modèle par défaut | Fournisseur | Coût |
|------|-------------------|-------------|------|
| **Cerveau** — conversation, décisions, appels d'outils | `glm-4.5-flash` | API Z.ai | gratuit |
| **Codeur** — génération de code déléguée | `qwen/qwen3-coder:free` | OpenRouter | gratuit |

Le cerveau analyse la demande et garde le contrôle des actions sensibles.
Lorsqu'une tâche demande d'écrire du code conséquent, il la délègue au codeur
via l'outil `deleguer_codeur`, applique le résultat, puis vérifie. Si un modèle
est indisponible, le client bascule automatiquement sur les modèles gratuits
listés dans `model/model_coder_free.txt`.

Le codeur est optionnel : mets `enabled = false` dans `[coder]` pour que le
cerveau fasse tout.

## Installation

Prérequis : **Python 3.11 ou plus récent**. Les scripts installent le paquet
puis ajoutent la commande `glm` à ton PATH.

### Windows

```powershell
git clone https://github.com/Marreouu/GLM-C0deur.git
cd GLM-C0deur
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

Ou double-clique sur `install\install.bat`.

### Linux / macOS

```bash
git clone https://github.com/Marreouu/GLM-C0deur.git
cd GLM-C0deur
chmod +x install/install.sh
./install/install.sh
```

Ouvre ensuite un **nouveau terminal** (le PATH n'est relu qu'au démarrage du
shell), puis vérifie :

```bash
glm --version
```

> Le dépôt étant privé, l'installation en une ligne (`irm … | iex` ou
> `curl … | bash`) ne fonctionne pas : `raw.githubusercontent.com` refuse les
> dépôts privés sans jeton. Passe par le clone ci-dessus.

### Installation manuelle

Si tu préfères te passer des scripts :

```bash
pip install -e .          # installe le paquet et la commande glm
pip install -r requirements.txt   # dépendances seules
```

## Ce que font les scripts d'installation

`install/install.ps1` (Windows) et `install/install.sh` (Linux/macOS) suivent
les mêmes six étapes, et journalisent tout dans `glm-install.log`
(`%TEMP%` sous Windows, `/tmp` ailleurs) :

1. **Environnement** — relève le système, la distribution et, sous Windows, la
   présence de droits administrateur. L'installation reste en mode utilisateur
   dans tous les cas.
2. **Python** — teste les interpréteurs disponibles (`py -3.14` … `python3`) et
   retient le premier en 3.11 ou plus. Installe `pip` via `ensurepip` s'il
   manque. Si un environnement virtuel est actif, il est utilisé en priorité.
3. **Sources** — utilise le dépôt cloné. À défaut, tente un `git clone`.
4. **Installation** — `pip install --user --editable .`, en s'adaptant aux
   environnements Python gérés par la distribution (PEP 668).
5. **PATH** — ajoute le dossier des scripts Python au PATH utilisateur : dans le
   registre sous Windows, dans `~/.bashrc`, `~/.zshrc` ou `~/.profile` ailleurs.
   L'entrée n'est jamais ajoutée deux fois.
6. **Vérification** — exécute `glm --version` et signale tout problème.

Options communes :

| Option | Effet |
|--------|-------|
| `-Quiet` / `--quiet` | n'affiche que les erreurs |
| `-NoPath` / `--no-path` | installe sans toucher au PATH |
| `-Source` / `--source` | force le dossier des sources |

### Désinstallation

```powershell
powershell -ExecutionPolicy Bypass -File install\uninstall.ps1    # Windows
```

```bash
./install/uninstall.sh                                            # Linux/macOS
```

Le script retire le paquet, l'entrée ajoutée au PATH et les lanceurs résiduels.
La configuration (`~/.glmcode`) est **conservée** par défaut ; ajoute `-Purge`
(Windows) ou `--purge` (Linux/macOS) pour l'effacer aussi. Les fichiers de shell
modifiés sont sauvegardés avant toute réécriture.

## Configuration

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

`config.toml` est exclu par `.gitignore` — ta clé API ne part jamais sur GitHub.

## Utilisation

```bash
glm                      # démarre l'assistant dans le dossier courant
glm --continue           # reprend la dernière session
glm --resume <ID>        # reprend une session précise
glm --list-sessions      # liste les sessions enregistrées
glm --version
glm --help
```

### Modes

On bascule avec <kbd>Shift</kbd>+<kbd>Tab</kbd> ou `/mode <nom>`.

| Mode | Comportement |
|------|--------------|
| `normal` | demande confirmation avant chaque écriture ou commande |
| `auto` | exécute les actions sans demander |
| `plan` | lecture seule : propose un plan sans rien modifier |

En mode `normal`, réponds aux demandes d'autorisation directement dans la barre
du bas : `o` pour accepter, <kbd>Entrée</kbd> ou `n` pour refuser.

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
| <kbd>Ctrl</kbd>+<kbd>C</kbd> | interrompt la requête (deux fois pour quitter) |
| <kbd>Ctrl</kbd>+<kbd>D</kbd> | quitte |
| <kbd>PgUp</kbd> / <kbd>PgDn</kbd> | défile le transcript |

Si le mode plein écran pose problème sur ton terminal, `GLMCODE_SIMPLE=1 glm`
force une boucle ligne à ligne.

## Skills

Un skill est un fichier Markdown décrivant une tâche répétitive, invocable par
`/<nom>`. Les skills fournis sont dans `glmcode/builtin_skills/` :
`/debug`, `/explique`, `/revue-code`, `/review-code`, `/generate-code`,
`/refactor`, `/refactor-code`, `/tests`.

Pour ajouter les tiens, dépose des `.md` dans un dossier et déclare-le :

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
  client.py      client HTTP de l'API Z.ai (streaming, usage, bascule modèle)
  coder.py       délégation au modèle codeur
  tools.py       outils : lecture/écriture de fichiers, shell
  config.py      chargement de la configuration
  session.py     persistance des sessions
  runtime.py     surveillance de fichiers, services de fond
  updater.py     vérification des mises à jour
  builtin_skills/  skills fournis
install/         scripts d'installation et de désinstallation
model/           listes de modèles de repli
```

## Dépannage

| Symptôme | Piste |
|----------|-------|
| `glm` introuvable après installation | ouvre un nouveau terminal ; le PATH n'est relu qu'au démarrage du shell |
| l'installation échoue | consulte le journal : `%TEMP%\glm-install.log` ou `/tmp/glm-install.log` |
| `externally-managed-environment` | le script réessaie seul avec `--break-system-packages` ; sinon, utilise un venv |
| affichage cassé dans le terminal | lance `GLMCODE_SIMPLE=1 glm` |
| erreur d'authentification | vérifie `[zai].api_key` dans `config.toml` |

## Tests

```bash
python -m pytest glmcode/test_tui.py glmcode/test_cli.py
```

## Licence

Projet personnel, sans licence explicite pour le moment.
