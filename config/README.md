# Configuration de GLM Codeur

Ce dossier contient les fichiers de configuration pour GLM Codeur. La configuration utilise le format TOML, qui est lisible par l'homme et facile à modifier.

## Fichiers disponibles

- `config.toml` - Fichier de configuration principal (si vous voulez personnaliser)
- `config.example.toml` - Fichier de configuration avec tous les paramètres disponibles et leurs valeurs par défaut

## Structure du fichier de configuration

Le fichier de configuration TOML est organisé en sections. Voici un exemple complet avec explications :

```toml
# =====================================================================
# Configuration de GLM Codeur
# =====================================================================

# Section principale du modèle de langage
[llm]
# Modèle à utiliser (par exemple: "gpt-4", "claude-3", "gemini-pro")
model = "gpt-4"

# Clé API pour accéder au service LLM
# Ne mettez jamais votre clé en clair dans ce fichier !
# Utilisez des variables d'environnement à la place.
api_key = "${GLM_API_KEY}"

# URL de base de l'API (si vous utilisez un service personnalisé)
api_base = "https://api.openai.com/v1"

# Température pour la génération de texte (0.0 à 1.0)
# Plus la température est élevée, plus les réponses seront créatives
temperature = 0.7

# Nombre maximum de tokens dans la réponse
max_tokens = 2000

# Timeout en secondes pour les requêtes API
timeout = 30

# =====================================================================
# Configuration des assistants
# =====================================================================

[assistants]
# Assistant par défaut pour le codage
default = "coding"

# Liste des assistants disponibles
[[assistants.profiles]]
name = "coding"
description = "Assistant spécialisé en développement logiciel"
system_prompt = """
Tu es un assistant de codage expert. Tu aides à écrire, refactorer, déboguer et optimiser du code.
- Donne des réponses concises et précises
- Propose des solutions pratiques
- Explique les concepts clés
- Suit les meilleures pratiques du langage utilisé
"""

[[assistants.profiles]]
name = "debug"
description = "Assistant spécialisé dans le débogage"
system_prompt = """
Tu es un expert en débogage. Tu aides à identifier et corriger les erreurs dans le code.
- Analyse les erreurs systématiquement
- Propose des solutions testées
- Explique la cause racine des problèmes
- Donne des conseils pour éviter les erreurs similaires
"""

[[assistants.profiles]]
name = "review"
description = "Assistant pour la revue de code"
system_prompt = """
Tu es un expert en revue de code. Tu analyses la qualité, la sécurité et les performances du code.
- Vérifie la conformité aux bonnes pratiques
- Identifie les vulnérabilités potentielles
- Suggère des améliorations de performance
- Propose des refactorisations pour une meilleure lisibilité
"""

# =====================================================================
# Configuration des outils
# =====================================================================

[tools]
# Activer/désactiver certains outils
enable_file_operations = true
enable_web_search = false
enable_code_execution = false

# Configuration des outils de fichier
[tools.file]
# Extensions de fichiers à ignorer
ignored_extensions = [".tmp", ".log", ".bak", ".swp"]
# Taille maximale des fichiers à lire (en Mo)
max_file_size = 10
# Dossiers à exclure de l'analyse
excluded_directories = ["node_modules", ".git", "__pycache__", "venv"]

# Configuration des outils web
[tools.web]
# User agent personnalisé pour les requêtes HTTP
user_agent = "GLM-Codeur/1.0"
# Timeout pour les requêtes web (en secondes)
timeout = 10
# Nombre maximum de résultats de recherche
max_results = 5

# =====================================================================
# Configuration de l'interface
# =====================================================================

[ui]
# Thème de couleur (dark, light, auto)
theme = "dark"
# Format de sortie des réponses (markdown, plain_text)
output_format = "markdown"
# Afficher les numéros de ligne dans les extraits de code
show_line_numbers = true
# Couleur syntaxique activée
syntax_highlighting = true

# =====================================================================
# Configuration avancée
# =====================================================================

[advanced]
# Journalisation (off, info, debug, verbose)
log_level = "info"
# Chemin du fichier de log (laisser vide pour désactiver)
log_file = ""
# Activer le mode développeur (pour le débogage)
developer_mode = false
# Nombre maximum de tokens dans le contexte
context_window = 4000
# Nombre de conversations à conserver dans l'historique
max_history = 50

# =====================================================================
# Configuration des raccourcis clavier
# =====================================================================

[shortcuts]
# Raccourcis pour les actions courantes
save = "Ctrl+S"
new_conversation = "Ctrl+N"
clear_screen = "Ctrl+L"
help = "F1"
settings = "Ctrl+,"
```

## Comment personnaliser votre configuration

### 1. Copier le fichier d'exemple

```bash
# Copiez le fichier d'exemple pour le modifier
cp config.example.toml config.toml
```

### 2. Modifier les valeurs

Éditez le fichier `config.toml` avec vos préférences :

```toml
# Changer le modèle LLM
[llm]
model = "claude-3"
temperature = 0.5

# Personnaliser l'assistant par défaut
[assistants]
default = "debug"
```

### 3. Utiliser des variables d'environnement

Pour les informations sensibles comme les clés API, utilisez des variables d'environnement :

```toml
[llm]
api_key = "${GLM_API_KEY}"  # Sera remplacé par la valeur de la variable d'environnement
```

Définissez la variable dans votre terminal :

**Windows (PowerShell) :**
```powershell
$env:GLM_API_KEY="votre_clé_api_ici"
```

**Linux/macOS :**
```bash
export GLM_API_KEY="votre_clé_api_ici"
```

Ou ajoutez-la à votre fichier de configuration shell :

```bash
# ~/.bashrc ou ~/.zshrc
export GLM_API_KEY="votre_clé_api_ici"
```

## Paramètres importants

### Modèle LLM
- `model`: Choisissez le modèle qui correspond à vos besoins
- `temperature`: Contrôle la créativité (0.0 = très précis, 1.0 = très créatif)
- `max_tokens`: Limite la longueur des réponses

### Assistants
- `default`: Assistant utilisé par défaut
- `profiles`: Définissez vos propres assistants avec des prompts personnalisés

### Outils
- `enable_file_operations`: Permet la lecture et modification de fichiers
- `enable_web_search`: Active la recherche d'informations en ligne
- `enable_code_execution`: Permet l'exécution de code (attention aux risques de sécurité)

### Interface
- `theme`: Apparence de l'interface
- `output_format`: Format des réponses
- `syntax_highlighting`: Coloration syntaxique du code

## Bonnes pratiques

1. **Ne mettez jamais de clés API en clair** - Utilisez toujours des variables d'environnement
2. **Sauvegardez votre configuration** - Faites une copie de votre fichier `config.toml`
3. **Testez après modification** - Redémarrez GLM Codeur après avoir changé la configuration
4. **Consultez les logs** - Si quelque chose ne fonctionne pas, vérifiez les logs pour plus de détails

## Problèmes courants

### Le fichier n'est pas reconnu
- Assurez-vous que le fichier s'appelle `config.toml` (pas `config.example.toml`)
- Vérifiez qu'il est dans le bon dossier (`~/.glmcode/`)

### Les changements ne sont pas appliqués
- Redémarrez GLM Codeur après avoir modifié la configuration
- Vérifiez qu'il n'y a pas d'erreur de syntaxe dans le fichier TOML

### Variables d'environnement non reconnues
- Vérifiez que les variables sont bien définies avant de lancer GLM Codeur
- Utilisez la commande `echo $GLM_API_KEY` (Linux/macOS) ou `$env:GLM_API_KEY` (Windows) pour vérifier

## Support

Si vous avez des questions sur la configuration :
- Consultez la documentation dans le dossier `docs/`
- Ouvrez un issue sur GitHub
- Contactez l'équipe de développement