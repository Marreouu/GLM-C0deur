# Commandes Internes de GLM Codeur

GLM Codeur dispose d'un système de commandes internes accessibles via des commandes slash (`/`) dans l'interface. Ces commandes permettent de contrôler le comportement de l'assistant, gérer les sessions, et invoquer des compétences (skills).

## Commandes Slash Disponibles

### `/help`
Affiche l'aide avec la liste des commandes disponibles.

**Exemple :**
```
/help
```

### `/reset`
Efface l'historique de la conversation en cours.

**Exemple :**
```
/reset
```

### `/model <nom>`
Change le modèle de langage utilisé par l'assistant.

**Exemple :**
```
/model glm-4-plus
```

Si aucun nom n'est spécifié, affiche le modèle actuel :
```
/model
```

### `/mode [nom]`
Change le mode de fonctionnement de l'assistant.

**Modes disponibles :**
- `normal` : Confirme chaque action (écriture/commande)
- `auto` : Exécute les actions sans demander
- `plan` : Lecture seule - propose un plan sans rien modifier

**Exemple :**
```
/mode auto
```

Pour basculer entre les modes, vous pouvez également utiliser `Shift+Tab`.

### `/skills`
Liste tous les skills disponibles dans l'environnement actuel.

**Exemple :**
```
/skills
```

### `/session`
Affiche l'ID de la session courante.

**Exemple :**
```
/session
```

### `/sessions`
Liste toutes les sessions enregistrées.

**Exemple :**
```
/sessions
```

### `/resume [id]`
Reprend une session précédente. Si aucun ID n'est spécifié, reprend la dernière session.

**Exemple :**
```
/resume abc123
/resume
```

### `/ping`
Teste la connexion au backend.

**Exemple :**
```
/ping
```

### `/exit` ou `/quit`
Quitte l'application.

**Exemple :**
```
/exit
```

## 🎯 Système de Skills

Les skills sont des fichiers Markdown réutilisables qui peuvent être invoqués avec la syntaxe `/nom-skill [argument]`. Ils permettent d'automatiser des tâches répétitives et d'appliquer des méthodes de travail éprouvées.

### 📁 Structure d'un Skill

Un skill est un fichier `.md` avec un frontmatter optionnel :

```markdown
---
name: nom-du-skill
description: Description claire du skill
---

<instructions complètes injectées dans le contexte quand on invoque /nom-du-skill>
```

### 🗂️ Emplacements des Skills (par ordre de priorité)

1. **`./skills/`** - Skills du projet courant (priorité la plus haute)
2. **`~/.glmcode/skills/`** - Skills globaux de l'utilisateur
3. **Skills intégrés** - Livrés avec GLM Code
4. **Skills de Claude Code** - Intégration optionnelle

### 🔗 Intégration avec les Skills de Claude Code

GLM Codeur peut automatiquement détecter et utiliser les skills de Claude Code :

#### Skills "Superpowers" (workflows généraux)
- **Emplacement:** `~/.claude/plugins/cache/claude-plugins-official/superpowers/latest/skills/`
- **Contenu:** Workflows de développement généraux provenant de Claude Code
- **Activation:** Activé automatiquement si la configuration le permet

#### Skills personnels de Claude Code
- **Emplacement:** `~/.claude/skills/`
- **Contenu:** Skills personnalisés créés par l'utilisateur pour Claude Code
- **Activation:** Activé automatiquement si la configuration le permet

#### Structure des skills de Claude Code
GLM Codeur supporte deux formats :
1. **Fichiers plats:** `./skills/nom.md` (format GLM Codeur)
2. **Structure Claude:** `./skills/nom/SKILL.md` (format Claude Code)

### 🛠️ Skills Intégrés Disponibles

#### `/debug` - Débogage méthodique
**Description:** Debug methodique d'un bug ou d'une erreur
**Utilisation:** `/debug "mon code plante avec l'erreur X"`
**Fonctionnement:**
1. Reproduit le problème
2. Formule une hypothèse précise
3. Confirme la cause racine
4. Applique la correction minimale
5. Vérifie que c'est résolu

#### `/explique` - Explication pédagogique
**Description:** Explique clairement un fichier, une fonction ou un bout de code
**Utilisation:** `/explique "que fait cette fonction ?"` ou `/explique fichier.py`
**Fonctionnement:**
1. Analyse le code concerné
2. Donne une explication en une phrase
3. Détaille chaque partie importante
4. Signale les points subtils

#### `/review-code` - Revue de code approfondie
**Description:** Analyse et critique de code
**Utilisation:** `/review-code mon_fichier.py`
**Fonctionnement:**
- Résumé du code
- Points forts
- Points faibles et améliorations
- Bugs potentiels
- Suggestions de refactorisation

#### `/generate-code` - Génération de code
**Description:** Génère du code Python selon une description
**Utilisation:** `/generate-code "crée une fonction pour calculer la factorielle"`
**Fonctionnement:**
- Code fonctionnel et testable
- Documentation avec docstrings
- Bonnes pratiques Python
- Gestion des erreurs

#### `/refactor` - Refactorisation contrôlée
**Description:** Refactorise du code sans changer son comportement
**Utilisation:** `/ refactor vieux_code.py`
**Fonctionnement:**
1. Analyse le code existant
2. Identifie les problèmes
3. Applique des refactorisations petites et sûres
4. Vérifie que rien n'est cassé

#### `/tests` - Génération de tests
**Description:** Génère des tests pour le code existant
**Utilisation:** `/tests ma_fonction.py`
**Fonctionnement:**
- Génération de tests unitaires
- Couverture des cas d'usage
- Assertions appropriées

### 🚀 Création de Skills Personnalisés

#### 1. Créer un skill simple

```markdown
---
name: mon-skill
description: Description de mon skill personnalisé
---

Tu es un expert dans [domaine]. Quand on invoque ce skill, tu dois :

1. Analyser la demande : {input}
2. Appliquer une méthode spécifique
3. Fournir un résultat structuré

Exemple de réponse :
- Analyse : ...
- Solution : ...
- Résultat : ...
```

#### 2. Créer un skill complexe avec plusieurs étapes

```markdown
---
name: analyse-securite
description: Analyse de sécurité complète du code
---

Tu es un expert en sécurité applicative. Procède ainsi :

1. **Lecture du code** : Lis le fichier fourni et comprends son fonctionnement
2. **Analyse des vulnérabilités** : Recherche les problèmes de sécurité courants
3. **Évaluation des risques** : Classe les problèmes par criticité
4. **Recommandations** : Propose des solutions concrètes

Code à analyser :
```python
{input}
```

Format de réponse attendu :
## Vulnérabilités détectées
- [Problème] : Description et risque associé
- [Problème] : Description et risque associé

## Recommandations
- [Solution] : Description de la solution
- [Solution] : Description de la solution
```

#### 3. Emplacement des skills personnalisés

**Skills du projet courant :**
```bash
mkdir -p ./skills
# Créer ./skills/mon-skill.md
```

**Skills globaux :**
```bash
mkdir -p ~/.glmcode/skills
# Créer ~/.glmcode/skills/mon-skill.md
```

### 📝 Exemples de Skills Personnalisés

#### Skill d'analyse de performance
```markdown
---
name: analyse-performance
description: Analyse les performances du code et propose des optimisations
---

Tu es un expert en optimisation de code. Analyse le code fourni :

1. Identifie les boucles inefficaces
2. Repère les allocations mémoire inutiles
3. Cherche les algorithmes sous-optimaux
4. Propose des solutions concrètes

Code :
```python
{input}
```

Rapport d'analyse :
## Problèmes de performance
- [Problème] : Ligne et impact
- [Problème] : Ligne et impact

## Optimisations recommandées
- [Optimisation] : Description et gain attendu
```

#### Skill de documentation
```markdown
---
name: documenter
description: Génère une documentation complète pour un projet
---

Tu es un expert en documentation technique. Génère une documentation complète pour le projet.

Procède ainsi :
1. Analyse la structure du projet
2. Documente chaque module/fichier
3. Crée des exemples d'utilisation
4. Génère un README complet

Projet : {input}

Documentation :
```

### 🔧 Gestion des Skills

#### Lister tous les skills disponibles
```bash
/skills
```

#### Utiliser un skill
```bash
/mon-skill argument
/revue-code fichier.py
/generate-code "crée une classe pour gérer une todo list"
```

#### Priorité des skills
1. Skills du projet courant (`./skills/`)
2. Skills globaux (`~/.glmcode/skills/`)
3. Skills intégrés
4. Skills de Claude Code (si activé)

Les skills avec le même nom : celui du projet courant écrase les autres.

### 💡 Bonnes Pratiques pour les Skills

1. **Nommage clair** : Utilisez des noms descriptifs et courts
2. **Description précise** : Expliquez ce que fait le skill en une phrase
3. **Instructions complètes** : Donnez toutes les étapes nécessaires
4. **Utilisation de `{input}`** : Permet de personnaliser le skill
5. **Formatage cohérent** : Utilisez un format de sortie standard
6. **Testez vos skills** : Vérifiez qu'ils fonctionnent correctement
7. **Documentez vos skills** : Créez un README pour vos skills personnalisés

### 🔄 Intégration avec Claude Code

Pour activer l'intégration avec les skills de Claude Code :

1. **Vérifiez l'installation de Claude Code** :
   ```bash
   # Si Claude Code est installé, les dossiers suivants existent :
   ls -la ~/.claude/skills/
   ls -la ~/.claude/plugins/cache/claude-plugins-official/superpowers/
   ```

2. **Les skills seront automatiquement détectés** et disponibles via `/skills`

3. **Conflits de noms** : Les skills de GLM Codeur ont priorité sur ceux de Claude Code

4. **Structure compatible** : GLM Codeur peut utiliser les skills au format de Claude Code

## Modes de Fonctionnement

### Mode Normal
- Confirmation requise pour chaque action
- Idéal pour un contrôle précis

### Mode Auto
- Exécution automatique des actions
- Plus rapide mais nécessite confiance dans l'assistant

### Mode Plan
- Lecture seule
- Propose un plan sans exécuter d'actions
- Utile pour la planification

## Contrôles Clavier

- `Shift+Tab` : Basculer entre les modes
- `Ctrl+C` : Interrompre une opération en cours
- `Enter` : Envoyer un message
- `Flèche haut/bas` : Navigation dans l'historique

## Dépannage

### Problèmes de connexion
Utilisez `/ping` pour tester la connexion au backend.

### Skills non trouvés
Vérifiez que vos fichiers `.md` sont dans les bons répertoires :
- `./skills/` pour les skills du projet
- `~/.glmcode/skills/` pour les skills globaux

### Sessions
Si une session ne se charge pas correctement :
1. Vérifiez l'ID avec `/sessions`
2. Utilisez `/resume <id>` pour reprendre la session

## Commandes en Ligne de Commande (glm --*)

Les commandes suivantes sont utilisées au lancement de GLM Codeur, avant d'entrer dans l'interface interactive.

### Affichage de l'aide complète
Pour voir toutes les options disponibles en ligne de commande :
```bash
glm --help
```

**Résultat :**
```
usage: glmcode [-h] [--version] [--resume ID] [--continue] [--list-sessions]

Assistant de codage terminal (API Z.ai / GLM).

options:
  -h, --help       show this help message and exit
  --version        affiche la version
  --resume ID      reprend la session <ID>
  --continue       reprend la derniere session
  --list-sessions  liste les sessions enregistrees puis quitte
```

### `glm --resume ID`
**Description:** Lance GLM et reprend une session spécifique
**Usage:** `glm --resume <ID>`
**Exemple:**
```bash
glm --resume abc123                    # Reprend la session avec l'ID abc123
glm --resume session-2024-01-15_14-30-00  # Reprend une session précise
```

### `glm --continue` ou `glm --cont`
**Description:** Lance GLM et reprend la dernière session
**Usage:** `glm --continue` ou `glm --cont`
**Exemple:**
```bash
glm --continue                         # Reprend la dernière session
glm --cont                            # Abréviation de --continue
```

### `glm --list-sessions`
**Description:** Liste toutes les sessions enregistrées puis quitte
**Usage:** `glm --list-sessions`
**Exemple:**
```bash
glm --list-sessions                    # Affiche toutes les sessions disponibles
```

### `glm --version`
**Description:** Affiche la version de GLM Codeur
**Usage:** `glm --version`
**Exemple:**
```bash
glm --version                          # Affiche: glmcode 1.2.3
```

### `glm --help`
**Description:** Affiche l'aide des commandes en ligne de commande
**Usage:** `glm --help`
**Exemple:**
```bash
glm --help                            # Affiche toutes les options de ligne de commande
```

### 📋 Résumé des commandes en ligne de commande

| Commande | Description | Abréviation | Exemple |
|----------|-------------|-------------|---------|
| `glm --help` | Affiche l'aide | | `glm --help` |
| `glm --version` | Affiche la version | | `glm --version` |
| `glm --resume ID` | Reprend une session spécifique | | `glm --resume abc123` |
| `glm --continue` | Reprend la dernière session | `glm --cont` | `glm --continue` |
| `glm --list-sessions` | Liste toutes les sessions | | `glm --list-sessions` |

## Exemples d'Utilisation Combinée

### Flux de travail typique :
```bash
# 1. Voir les sessions disponibles
glm --list-sessions

# 2. Reprendre la dernière session
glm --continue

# 3. Une fois dans GLM, voir la session actuelle
/session

# 4. Lister toutes les sessions internes
/sessions

# 5. Reprendre une autre session depuis l'interface interne
/resume session-2024-01-14_10-15-00

# 6. Changer de modèle ou de mode
/model gpt-4
/mode auto

# 7. Utiliser un skill
/review-code mon_projet/app.py

# 8. Quitter et reprendre plus tard
/exit

# 9. Reprendre la session plus tard
glm --resume session-2024-01-15_14-30-00
```

### Gestion des sessions :
```bash
# Créer une nouvelle session
glm

# Voir l'ID de la session courante
/session

# Quitter sans sauvegarder explicitement
/exit

# Reprendre la session plus tard
glm --continue  # ou glm --resume <ID>
```

## Architecture GLM Codeur : Cerveau et Codeur

GLM Codeur utilise une architecture à deux niveaux intelligente pour séparer les responsabilités :

### 🧠 Le Cerveau (Orchestrateur)
- **Rôle:** Modèle principal qui gère la conversation globale
- **Fonctions:** 
  - Comprend la demande utilisateur
  - Décide de l'approche à adopter
  - Utilise des outils pour lire des fichiers, exécuter des commandes
  - Délègue les tâches de codage complexes au codeur
- **Modèles utilisés:** GPT-4, Claude, etc. (modèles conversationnels)

### 💻 Le Codeur (Spécialisé)
- **Rôle:** Modèle dédié exclusivement au codage technique
- **Fonctions:**
  - Génère du code complet et structuré
  - Modifie des fichiers avec précision
  - Suit un formatage strict pour les réponses
  - Optimisé pour les tâches de programmation
- **Modèles utilisés:** Qwen2.5-Coder, CodeLlama, etc. (modèles codeurs)

### 🔄 Comment ça fonctionne ensemble

1. **Le cerveau analyse la demande** et décide s'il faut déléguer
2. **Si c'est une tâche complexe** (création/modification de fichiers), le cerveau utilise l'outil `deleguer_codeur`
3. **Le codeur génère** le code complet dans un format structuré
4. **Le cerveau applique** les modifications ou demande confirmation
5. **Le cerveau vérifie** le résultat et fait la synthèse

### Exemple de workflow

```bash
# Demande complexe qui active les deux niveaux
"Crée-moi une application web Flask avec authentification JWT et une base de données SQLite"

# Le cerveau comprend la demande et délègue au codeur
# Le codeur génère les fichiers : app.py, models.py, config.py, etc.
# Le cerveau applique les modifications et vérifie que tout fonctionne
```

### Avantages de cette architecture

- **Efficacité:** Le codeur est optimisé pour le codage technique
- **Sécurité:** Le cerveau garde le contrôle sur les actions sensibles
- **Flexibilité:** Peut fonctionner avec un seul modèle ou les deux
- **Qualité:** Le codeur génère du code complet et bien structuré

## Bonnes Pratiques

1. **Utilisez le mode `plan`** pour les tâches complexes avant de passer en mode `auto`
2. **Nommez vos skills de manière descriptive**
3. **Documentez vos skills** avec des descriptions claires
4. **Testez vos skills** dans des environnements de développement avant de les utiliser en production
5. **Sauvegardez vos sessions** importantes avec `/session` et reprenez-les plus tard
6. **Utilisez `glm --list-sessions`** pour voir toutes vos sessions disponibles
7. **Comprenez la séparation cerveau/codeur** pour mieux utiliser les fonctionnalités

## Création de Skills Personnalisés

Pour créer un skill personnalisé :

1. Créez un fichier `.md` dans `./skills/` ou `~/.glmcode/skills/`
2. Ajoutez un frontmatter avec `name` et `description`
3. Écrivez les instructions dans le corps du fichier

Exemple (`./skills/mon-skill.md`) :
```markdown
---
name: mon-skill
description: Un skill personnalisé
---

Vous êtes un expert en Python. Répondez à la demande suivante avec du code bien documenté.
```

Utilisation :
```
/mon-skill Créer une fonction pour trier une liste
```