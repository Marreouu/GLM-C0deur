# FAQ - GLM Code

## Questions générales

### Qu'est-ce que GLM Code ?

GLM Code est un assistant de codage en terminal inspiré de Claude Code, utilisant GLM-4.7 via l'API Z.ai. Il permet de lire et modifier des fichiers, lancer des commandes, et gérer des projets de développement directement depuis votre terminal.

### Quels sont les systèmes d'exploitation supportés ?

GLM Code supporte :
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu, Debian, Fedora, etc.)

### Quelles sont les dépendances requises ?

- Python 3.11 ou supérieur
- Une clé API Z.ai (gratuite)
- Optionnel : Ollama pour le mode orchestrateur

### Est-ce gratuit ?

Oui, GLM Code est open source sous licence MIT. L'utilisation de l'API Z.ai est gratuite avec le modèle glm-4.5-flash. Les modèles payants (glm-4.7, glm-5) sont optionnels.

## Installation et configuration

### Comment installer GLM Code ?

```bash
# Cloner le dépôt
git clone https://github.com/votre-organisation/glm-code.git
cd glm-code

# Installer les dépendances
pip install -r requirements.txt

# Installer en mode global (optionnel)
pip install -e .
```

### Comment configurer l'API Z.ai ?

1. Créez un fichier `config.toml` :
```bash
cp config.example.toml config.toml
```

2. Ajoutez votre clé API :
```toml
[zai]
api_key = "votre-cle-api-zai"
```

3. Ou utilisez une variable d'environnement :
```bash
export GLMCODE_API_KEY="votre-cle-api-zai"
```

### Comment activer le mode orchestrateur ?

Ajoutez cette configuration à `config.toml` :
```toml
[coder]
enabled = true
base_url = "http://localhost:11434/v1"
model = "qwen2.5-coder:latest"
```

Assurez-vous d'avoir Ollama installé et le modèle téléchargé :
```bash
ollama pull qwen2.5-coder
```

## Utilisation

### Comment lancer GLM Code ?

```bash
# Depuis le dossier du projet
python -m glmcode

# Ou si installé globalement
glm

# Ou avec PowerShell
.\glm.ps1
```

### Quels sont les modes de travail disponibles ?

- **Normal** : Demande confirmation avant chaque action destructrice
- **Auto** : Exécute les actions sans demander confirmation
- **Plan** : Mode lecture seule, propose un plan d'action

### Comment changer de mode ?

- **Shift+Tab** : Bascule entre les modes
- **`/mode`** : Commande pour changer de mode
- **`/mode normal/auto/plan`** : Spécifier le mode

### Comment utiliser les commandes slash ?

- **`/help`** : Affiche l'aide
- **`/reset`** : Efface l'historique
- **`/model <nom>`** : Change le modèle
- **`/mode [nom]`** : Change le mode
- **`/skills`** : Liste les skills disponibles
- **`/<skill> [texte]`** : Invoque un skill
- **`/ping`** : Teste la connexion
- **`/exit`** : Quitte

### Comment utiliser les skills ?

Les skills sont des fichiers Markdown qui étendent les fonctionnalités de GLM Code :

```bash
# Lister les skills disponibles
/skills

# Invoquer un skill
/revue-code

# Invoquer avec un argument
/revue-code app.py
```

## Développement

### Comment contribuer au projet ?

1. Fork le dépôt
2. Créez une branche de fonctionnalité
3. Développez et testez
4. Créez une Pull Request

Voir [contributing.md](contributing.md) pour plus de détails.

### Comment exécuter les tests ?

```bash
# Exécuter tous les tests
pytest

# Avec coverage
pytest --cov=glmcode

# Test spécifique
pytest tests/test_agent.py
```

### Comment ajouter un nouvel outil ?

1. Définissez le schéma dans `tools.py`
2. Implémentez la fonction
3. Ajoutez à `TOOL_IMPLS`
4. Ajoutez des tests

Exemple :
```python
def git_commit(message: str, **_) -> str:
    # Implémentation
    pass

# Ajouter au schéma
TOOLS_SCHEMA.append({...})

# Ajouter à l'implémentation
TOOL_IMPLS["git_commit"] = git_commit
```

## Problèmes courants

### J'ai une erreur "No API key found"

Vérifiez que :
- Vous avez configuré `config.toml` avec votre clé API
- Ou que la variable d'environnement `GLMCODE_API_KEY` est définie
- La clé est valide et non expirée

### Le mode plein écran ne fonctionne pas

Essayez :
```bash
GLMCODE_SIMPLE=1 glm
```

Ou installez les dépendances manquantes :
```bash
pip install rich prompt_toolkit
```

### Les commandes shell ne fonctionnent pas

Vérifiez :
- La syntaxe de votre commande
- Les permissions d'exécution
- Le timeout (120s par défaut)

### Le mode orchestrateur ne fonctionne pas

Assurez-vous que :
- Ollama est installé et démarré
- Le modèle est téléchargé (`ollama pull qwen2.5-coder`)
- La configuration `[coder]` est correcte

### Les skills ne sont pas reconnus

Vérifiez :
- Le format du fichier (Markdown avec entête YAML)
- Le chemin du fichier (dans `skills/`, `~/.glmcode/skills/`, ou intégré)
- Les permissions de lecture

## Performance

### GLM Code est lent, que faire ?

1. **Réduisez la taille des fichiers** : Limitez les fichiers à <100Ko
2. **Utilisez le mode auto** : Évitez les confirmations inutiles
3. **Optimisez les commandes** : Évitez les commandes longues
4. **Mettez à jour Python** : Utilisez Python 3.11+

### Comment optimiser l'utilisation de la mémoire ?

- Fermez les conversations longues
- Utilisez `/reset` régulièrement
- Évitez de lire de très gros fichiers

### Comment gérer les timeouts ?

- Les commandes shell ont un timeout de 120s
- Les requêtes API ont un timeout de 300s
- Vous pouvez ajuster ces valeurs dans `config.toml`

## Sécurité

### GLM Code est-il sécurisé ?

Oui, GLM Code inclut plusieurs mesures de sécurité :
- Validation des chemins de fichiers
- Échappement des sorties utilisateur
- Pas d'exécution de code arbitraire
- Gestion sécurisée des clés API

### Mes clés API sont-elles stockées en clair ?

Non, les clés API sont :
- Stockées dans des fichiers ignorés par git
- Accessibles uniquement par l'utilisateur
- Chiffrées si stockées dans un trousseau système

### Est-ce que GLM Code envoie mes données à des tiers ?

Non, GLM Code communique uniquement avec :
- L'API Z.ai pour les requêtes LLM
- Votre machine locale pour les fichiers et commandes

## Comparaison avec d'autres outils

### GLM Code vs Claude Code

| Caractéristique | GLM Code | Claude Code |
|----------------|----------|-------------|
| Modèle | GLM-4.7 (Z.ai) | Claude (Anthropic) |
| Open source | Oui | Non |
| Mode orchestrateur | Oui | Oui |
| Skills | Oui | Oui |
| Interface riche | Oui | Oui |
| Gratuit | Oui | Non |

### GLM Code vs GitHub Copilot

| Caractéristique | GLM Code | GitHub Copilot |
|----------------|----------|----------------|
| Contexte | Complet | Limité |
| Exécution | Oui | Non |
| Personnalisation | Oui | Limitée |
| Open source | Oui | Non |
| Gratuit | Oui | Non |

## Fonctionnalités avancées

### Comment personnaliser le prompt système ?

Ajoutez ceci à `config.toml` :
```toml
system_prompt = """
Votre prompt personnalisé ici...
"""
```

### Comment ajouter des skills personnalisés ?

1. Créez un dossier `skills/` dans votre projet
2. Ajoutez des fichiers Markdown avec entête YAML
3. Ou ajoutez le chemin dans `config.toml` :
```toml
[skills]
dirs = ["/chemin/vers/vos/skills"]
```

### Comment intégrer avec d'autres outils ?

Vous pouvez créer des skills pour intégrer avec :
- Système de build (npm, pip, etc.)
- Outils de test (pytest, Jest, etc.)
- Outils de déploiement
- VCS (git, etc.)

## Support

### Où trouver de l'aide ?

1. Documentation : [docs/](docs/)
2. Issues GitHub : [Problèmes](https://github.com/votre-organisation/glm-code/issues)
3. Discussions GitHub : [Discussions](https://github.com/votre-organisation/glm-code/discussions)
4. Discord/Slack : [Communauté](lien-ici)

### Comment signaler un bug ?

1. Vérifiez si le bug n'existe pas déjà
2. Créez un issue détaillé avec :
   - Description du problème
   - Étapes pour reproduire
   - Comportement attendu
   - Environnement (OS, Python, version)

### Comment proposer une nouvelle fonctionnalité ?

1. Créez un issue avec l'étiquette "enhancement"
2. Décrivez votre idée en détail
3. Discutez de la proposition avec la communauté

## Licence

GLM Code est sous licence [MIT License](LICENSE). Vous êtes libre de :
- Utiliser le logiciel
- Modifier le code source
- Distribuer des copies
- Utiliser commercialement

Sous les conditions :
- Inclusion de la licence et de l'avis de copyright
- Pas de responsabilité des auteurs

## Remerciements

Merci à :
- L'équipe de Z.ai pour GLM-4.7
- La communauté open source
- Tous les contributeurs du projet

---

*Pour plus d'informations, consultez le [README principal](../README.md).*