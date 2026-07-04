# GLM Codeur - CLI d'Assistant de Codage

GLM Codeur est un **CLI d'assistant de codage** similaire à Claude Code, conçu pour vous aider dans vos projets de développement grâce à l'intelligence artificielle.

## 🚀 Installation en 1 commande

**Windows:**
```bash
irm "https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.ps1" | iex
```

**Linux/macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.sh | bash
```

## 🎯 Pourquoi GLM Codeur ?

GLM Codeur est un **terminal intelligent** qui combine :
- **Un orchestrateur (cerveau)** : Comprend vos demandes et coordonne le travail
- **Un codeur spécialisé** : Génère et modifie du code technique avec précision
- **Un système de skills** : Automatise les tâches répétitives
- **Gestion de sessions** : Reprenez votre travail là où vous l'avez laissé

## 🛠️ Fonctionnalités Principales

### Architecture à deux niveaux
- **🧠 Cerveau (Orchestrateur)** : Gère la conversation et délègue les tâches complexes
- **💻 Codeur (Spécialisé)** : Génère du code technique structuré

### Commandes internes
- `/help` - Aide complète
- `/review-code` - Analyse de code
- `/generate-code` - Génération de code
- `/debug` - Débogage méthodique
- `/explique` - Explications pédagogiques
- `/skills` - Liste des skills disponibles

### Gestion de sessions
- `glm --continue` - Reprend la dernière session
- `glm --resume ID` - Reprend une session spécifique
- `glm --list-sessions` - Liste toutes les sessions

### Skills personnalisables
Créez vos propres workflows avec des fichiers Markdown :
```markdown
---
name: mon-skill
description: Description de mon workflow
---

Instructions complètes pour le skill...
```

## 🎮 Utilisation

### Démarrer simplement
```bash
glm
# Puis tapez votre demande :
"Crée-moi une application Flask avec authentification JWT"
```

### Utiliser les commandes
```bash
glm --continue                    # Reprendre la dernière session
glm --resume session-123         # Reprendre une session spécifique
glm --list-sessions              # Voir toutes les sessions
```

### Dans l'interface
```bash
/help                           # Voir toutes les commandes internes
/review-code mon_fichier.py     # Analyser un fichier
/generate-code "crée une fonction"  # Générer du code
/debug "mon code plante"        # Débogage
/explique "que fait ce code ?"  # Explication
```

## 🔧 Configuration

GLM Codeur utilise un fichier de configuration TOML :
```bash
cp config/config.example.toml ~/.glmcode/config.toml
export GLM_API_KEY="votre_clé_api_ici"
```

## 📚 Skills Intégrés

- **`/review-code`** - Analyse et critique de code
- **`/generate-code`** - Génère du code Python
- **`/refactor-code`** - Refactorisation contrôlée
- **`/debug`** - Débogage méthodique
- **`/explique`** - Explications pédagogiques
- **`/tests`** - Génération de tests

## 🔄 Intégration Claude Code

GLM Codeur détecte automatiquement et utilise les skills de Claude Code :
- Skills "Superpowers" (workflows généraux)
- Skills personnels de l'utilisateur
- Structure compatible avec les deux formats

## 🎯 Cas d'usage

- **Développement web** - Créez des applications complètes
- **Débogage** - Identifiez et corrigez les erreurs
- **Code review** - Améliorez la qualité de votre code
- **Documentation** - Générez automatiquement la doc
- **Tests** - Créez des tests unitaires
- **Refactoring** - Améliorez la structure de votre code

## 📊 Comparaison avec Claude Code

| Caractéristique | GLM Codeur | Claude Code |
|----------------|------------|-------------|
| Architecture | Cerveau + Codeur | Mono-modèle |
| Skills | Personnalisables + Intégration Claude | Personnalisables |
| Installation | 1 commande | 1 commande |
| Configuration | TOML avancée | JSON simple |
| Gestion sessions | Complète | Basique |
| Multiplateforme | Windows/Linux/macOS | macOS/Linux |

## 🤝 Contribuer

Les contributions sont les bienvenues ! Voir le dossier `docs/` pour plus d'informations.

## 📄 Licence

MIT License - voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

**GLM Codeur** - L'assistant de codage qui comprend vraiment vos besoins.