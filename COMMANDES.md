# Commandes Internes de GLM Codeur

Une fois GLM Codeur installé, vous pouvez utiliser diverses commandes internes pour contrôler l'assistant. Ces commandes commencent par un slash `/`.

## 🚀 Commandes Principales

### `/help`
**Description:** Affiche l'aide complète avec toutes les commandes disponibles
**Usage:** `/help`
**Exemple:**
```
/help
```

### `/reset`
**Description:** Efface l'historique de la conversation actuelle
**Usage:** `/reset`
**Effet:** Démarre une nouvelle conversation fraîche

### `/exit` ou `/quit`
**Description:** Quitte GLM Codeur
**Usage:** `/exit` ou `/quit`
**Effet:** Ferme l'application proprement

---

## 🎯 Commandes de Modèle

### `/model <nom>`
**Description:** Change le modèle LLM courant
**Usage:** `/model gpt-4` ou `/model claude-3`
**Exemples:**
```
/model gpt-4                    # Affiche le modèle actuel
/model claude-3                 # Change pour Claude 3
/model                         # Affiche le modèle actuel
```

### `/mode [nom]` ou `/auto`
**Description:** Change le mode de fonctionnement
**Usage:** `/mode normal`, `/mode auto`, `/mode plan`
**Effet:**
- `normal`: Confirme chaque action (écriture/commande)
- `auto`: Exécute les actions sans demander
- `plan`: Lecture seule : propose un plan sans rien modifier
**Raccourci:** `Shift+Tab` pour basculer entre les modes

---

## 📚 Commandes de Skills

### `/skills`
**Description:** Liste tous les skills disponibles
**Usage:** `/skills`
**Exemple:**
```
/skills
```
**Résultat:** Affiche tous les skills avec leur description et source

### `/<skill> [texte]`
**Description:** Invoque un skill spécifique avec un argument optionnel
**Usage:** `/nom-du-skill [argument]`
**Exemples:**
```
/review-code mon_fichier.py      # Analyse le fichier Python
/generate-code "crée une fonction pour calculer la factorielle"  # Génère du code
/debug "mon code plante quand j'essaie de me connecter"  # Débogage
/explique "qu'est-ce que le machine learning"  # Explication
```

---

## 💾 Commandes de Session

### `/session`
**Description:** Affiche l'ID de la session courante
**Usage:** `/session`
**Exemple:**
```
/session
```
**Résultat:** `Session : abc123  (reprise : glmcode --resume abc123)`

### `/sessions`
**Description:** Liste toutes les sessions enregistrées
**Usage:** `/sessions`
**Exemple:**
```
/sessions
```
**Résultat:** Affiche toutes les sessions avec leur ID, date, nombre de tours et titre

### `/resume [id]`
**Description:** Reprend une session précédente
**Usage:** `/resume abc123` ou `/resume` (pour la dernière session)
**Exemples:**
```
/resume abc123                   # Reprend la session spécifique
/resume                         # Reprend la dernière session
```

---

## 🔧 Commandes Système

### `/ping`
**Description:** Teste la connexion au backend LLM
**Usage:** `/ping`
**Exemple:**
```
/ping
```
**Résultat:** `Connexion OK · Service opérationnel` ou `Échec : message d'erreur`

---

## 🎨 Skills Intégrés Disponibles

GLM Codeur inclut plusieurs prédéfinis que vous pouvez utiliser immédiatement :

### `/review-code`
**Description:** Analyse et critique de code
**Usage:** `/review-code nom_du_fichier.py`
**Fonctionnalités:**
- Résumé du code
- Points forts
- Points faibles et améliorations
- Bugs potentiels
- Suggestions de refactorisation

**Exemple:**
```
/review-code mon_app.py
```

### `/generate-code`
**Description:** Génère du code Python selon une description
**Usage:** `/generate-code "description de ce que vous voulez"`
**Fonctionnalités:**
- Code fonctionnel et testable
- Documentation avec docstrings
- Bonnes pratiques Python
- Gestion des erreurs
- Exemples d'utilisation

**Exemple:**
```
/generate-code "crée une classe pour gérer une liste de tâches avec méthodes ajouter, supprimer et lister"
```

### `/refactor-code`
**Description:** Refactorise du code existant
**Usage:** `/refactor-code nom_du_fichier.py`
**Fonctionnalités:**
- Amélioration de la lisibilité
- Optimisation des performances
- Correction des mauvaises pratiques
- Simplification du code

**Exemple:**
```
/refactor-code code_vieux.py
```

### `/debug`
**Description:** Aide au débogage de code
**Usage:** `/debug "description du problème"`
**Fonctionnalités:**
- Analyse des erreurs
- Identification des causes racines
- Propositions de solutions
- Conseils pour éviter les récidives

**Exemple:**
```
/debug "mon code Python plante avec une erreur de type 'list index out of range'"
```

### `/explique`
**Description:** Explication de concepts ou de code
**Usage:** `/explique "question ou concept"`
**Fonctionnalités:**
- Explications claires et pédagogiques
- Analogies pour les concepts complexes
- Exemples concrets
- Adaptation au niveau de l'utilisateur

**Exemple:**
```
/explique "qu'est-ce que le machine learning et comment ça marche"
```

### `/tests`
**Description:** Génération de tests pour le code
**Usage:** `/tests nom_du_fichier.py`
**Fonctionnalités:**
- Génération de tests unitaires
- Couverture des cas d'usage
- Assertions appropriées
- Documentation des tests

**Exemple:**
```
/tests ma_fonction.py
```

---

## 📁 Personnalisation des Skills

### Créer un skill personnalisé
1. Créez un fichier Markdown dans `./skills/` ou `~/.glmcode/skills/`
2. Nommez-le avec le nom de votre skill (ex: `mon-skill.md`)
3. Ajoutez un entête avec métadonnées :

```markdown
---
name: mon-skill
description: Description de mon skill
---

Instructions complètes pour mon skill...
{input}  # L'argument utilisateur sera inséré ici
```

### Exemple de skill personnalisé
```markdown
---
name: analyse-securite
description: Analyse de sécurité du code
---

Analyse le code suivant pour détecter les problèmes de sécurité:

Code:
```python
{input}
```

Fournis un rapport de sécurité avec:
1. Vulnérabilités détectées
2. Risques associés
3. Solutions recommandées
4. Bonnes pratiques à appliquer
```

### Utiliser le skill
```
/analyse-securite mon_script.py
```

---

## 🎮 Contrôles Clavier

### Dans l'interface en mode plein écran
- `Shift+Tab`: Bascule entre les modes (normal/auto/plan)
- `Ctrl+S`: Sauvegarde la conversation
- `Ctrl+N`: Nouvelle conversation
- `Ctrl+L`: Efface l'écran
- `F1`: Affiche l'aide
- `Ctrl+,`: Ouvre les paramètres

### Dans l'interface en mode ligne à ligne
- Les commandes slash comme décrit ci-dessus
- `Ctrl+C`: Interrompt l'exécution
- `Ctrl+D`: Quitte

---

## 🚦 Modes de Fonctionnement

### Mode Normal (`normal`)
- **Comportement:** Confirme chaque action avant de l'exécuter
- **Usage:** Idéal pour les débutants ou le travail critique
- **Commande:** `/mode normal`

### Mode Auto (`auto`)
- **Comportement:** Exécute les actions sans demander confirmation
- **Usage:** Pour les workflows rapides et les tâches répétitives
- **Commande:** `/mode auto` ou simplement `/auto`

### Mode Plan (`plan`)
- **Comportement:** Lecture seule : propose un plan sans rien modifier
- **Usage:** Pour l'analyse et la planification sans risque
- **Commande:** `/mode plan`

---

## 💡 Conseils d'Utilisation

1. **Commencez avec `/help`** pour toujours avoir la liste des commandes
2. **Utilisez `/skills`** pour découvrir tous les skills disponibles
3. **Combinez les modes** selon votre besoin (normal pour le code critique, auto pour les tâches simples)
4. **Créez vos propres skills** pour automatiser vos tâches répétitives
5. **Sauvegardez vos sessions** importantes avec `/session` et reprenez-les plus tard

---

## 🔍 Dépannage

### Commande inconnue
```
/help  # Vérifiez la liste des commandes disponibles
```

### Problème de skill
```
/skills  # Vérifiez que votre skill est bien chargé
```

### Connexion LLM
```
/ping  # Testez la connexion au backend
```

### Session corrompue
```
/reset  # Effacez l'historique et recommencez
```