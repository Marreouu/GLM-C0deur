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

## Système de Skills

Les skills sont des fichiers Markdown réutilisables qui peuvent être invoqués avec la syntaxe `/nom-skill [argument]`.

### Structure d'un Skill

Un skill est un fichier `.md` avec un frontmatter optionnel :

```markdown
---
name: revue-code
description: Revue de code approfondie
---

<instructions injectées dans le contexte quand on invoque /revue-code>
```

### Emplacements des Skills

1. `./skills/` (dossier du projet courant)
2. `~/.glmcode/skills/` (skills globaux de l'utilisateur)
3. Le pack intégré livré avec GLM Code

### Exemples d'utilisation

```
/revue-code app.py
/test-unitaire fonction_calcul
```

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