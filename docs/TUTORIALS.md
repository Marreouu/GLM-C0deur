# Tutoriels - GLM Code

Ce document fournit une série de tutoriels pour vous aider à démarrer avec GLM Code, couvrant les bases, les fonctionnalités avancées et les cas d'usage spécifiques.

## Tutoriel 1 : Installation et configuration

### Objectif
Installer et configurer GLM Code pour commencer à l'utiliser.

### Prérequis
- Python 3.11 ou supérieur
- Une clé API Z.ai (gratuite)

### Étapes

#### 1. Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-organisation/glm-code.git
cd glm-code

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Installer en mode développement (optionnel)
pip install -e .
```

#### 2. Configuration

```bash
# Copier le fichier de configuration
cp config.example.toml config.toml

# Éditer le fichier de configuration
nano config.toml
```

Ajoutez votre clé API :

```toml
[zai]
api_key = "votre-cle-api-zai"
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
enabled = false
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
dirs = []
```

#### 3. Lancement

```bash
# Lancer GLM Code
python -m glmcode

# Ou si installé globalement
glm

# Avec PowerShell
.\glm.ps1
```

### Vérification

```bash
# Tester la connexion
glm /ping

# Vérifier la version
glm --version
```

## Tutoriel 2 : Premiers pas avec GLM Code

### Objectif
Apprendre les bases de l'utilisation de GLM Code.

### Étapes

#### 1. Interface utilisateur

GLM Code offre deux modes d'interface :
- **TUI (Terminal User Interface)** : Interface plein écran
- **CLI (Command Line Interface)** : Interface ligne par ligne

```bash
# Lancer en mode TUI (par défaut)
glm

# Lancer en mode CLI
GLMCODE_SIMPLE=1 glm
```

#### 2. Modes de travail

GLM Code propose trois modes de travail :
- **Normal** : Demande confirmation avant chaque action
- **Auto** : Exécute les actions sans demander confirmation
- **Plan** : Mode lecture seule, propose un plan d'action

```bash
# Changer de mode avec Shift+Tab
# Ou avec la commande
glm /mode auto
```

#### 3. Commandes slash

Les commandes slash permettent de contrôler GLM Code :

```bash
# Aide
/help

# Changer de modèle
glm /model glm-4.5-flash

# Changer de mode
glm /mode normal

# Lister les skills
/skills

# Tester la connexion
/ping

# Quitter
/exit
```

#### 3. Utilisation des mentions @fichier

```bash
# Lancer GLM Code
glm

# Analyser un fichier existant
Analyse ce fichier @src/app.py et identifie les problèmes potentiels

# Modifier un fichier spécifique
Modifie ce fichier @utils.py pour optimiser la fonction calculate

# Comparer plusieurs fichiers
Compare ces fichiers @main.py @app.py et explique les différences
```

#### 4. Conversation avec GLM Code

```bash
# Démarrer une conversation
glm

# Demander de créer un fichier
Crée un fichier hello.py avec le code suivant:
def hello():
    print("Hello, World!")

# Demander de modifier un fichier
Modifie le fichier hello.py pour ajouter une fonction goodbye

# Demander d'exécuter du code
Exécute le fichier hello.py
```

### Exemple complet

```bash
# Lancer GLM Code
glm

# Créer un projet simple
Crée un projet Python simple avec un fichier main.py qui affiche "Hello World"

# GLM Code va :
# 1. Créer le fichier main.py
# 2. Demander confirmation
# 3. Écrire le fichier
# 4. Vous informer du résultat

# Exécuter le projet
Exécute le fichier main.py

# Analyser le projet
Analyse le projet pour suggérer des améliorations

# Créer des tests
Crée des tests unitaires pour le projet

# Documenter le projet
Crée une documentation simple pour le projet
```

## Tutoriel 3 : Utilisation des outils natifs

### Objectif
Apprendre à utiliser les outils natifs de GLM Code.

### Étapes

#### 1. Outils de fichiers

```bash
# Lire un fichier
read_file fichier.txt

# Écrire un fichier
write_file nouveau.txt "Contenu du fichier"

# Modifier un fichier
edit_file fichier.txt "ancien texte" "nouveau texte"

# Lister un répertoire
list_dir

# Lister un répertoire spécifique
list_dir src/
```

#### 2. Outils de commandes

```bash
# Exécuter une commande
run_command ls -la

# Exécuter une commande avec timeout
run_command "sleep 10"  # Timeout après 120s
```

#### 3. Utilisation dans une conversation

```bash
# Demander de lire un fichier
Peux-tu lire le fichier src/app.py et me dire ce qu'il fait ?

# Demander de créer un fichier
Crée un fichier requirements.txt avec les dépendances suivantes:
requests>=2.31.0
rich>=13.7.0

# Demander d'exécuter une commande
Exécute la commande git status pour voir l'état du dépôt
```

### Exemple complet

```bash
# Lancer GLM Code
glm

# Créer un projet
Crée un projet Python avec les fichiers suivants:
- main.py
- requirements.txt
- tests/test_main.py

# GLM Code va créer les fichiers avec le contenu approprié

# Lire les fichiers créés
read_file main.py
read_file requirements.txt
read_file tests/test_main.py

# Exécuter les tests
run_command python -m pytest tests/

# Modifier un fichier
edit_file main.py "print('Hello')" "print('Hello, World!')"

# Exécuter le projet
run_command python main.py
```

## Tutoriel 4 : Utilisation des skills

### Objectif
Apprendre à utiliser et créer des skills.

### Étapes

#### 1. Skills intégrés

GLM Code inclut plusieurs skills intégrés :

```bash
# Lister les skills disponibles
/skills

# Utiliser un skill
/revue-code src/app.py

# Utiliser un skill avec un argument
/debug src/app.py --error "division by zero"

/tests src/utils.py --unit --integration
```

#### 2. Créer un skill personnalisé

Créez un fichier `skills/react.md` :

```yaml
---
name: react
description: Développement React
---

# Développement React

Aide au développement d'applications React avec:
- Création de composants
- Gestion d'état
- Routing
- Tests

## Exemples

### Créer un composant
Pour créer un composant React, utilisez la syntaxe suivante:
```jsx
function MonComposant(props) {
  return <div>{props.children}</div>;
}
```

### Gestion d'état
Pour gérer l'état local, utilisez useState:
```jsx
import { useState } from 'react';

function Compteur() {
  const [count, setCount] = useState(0);
  return (
    <div>
      <p>Compteur: {count}</p>
      <button onClick={() => setCount(count + 1)}>Incrémenter</button>
    </div>
  );
}
```
```

#### 3. Utiliser un skill personnalisé

```bash
# Utiliser le skill React
/react Crée un composant React pour un formulaire de contact

# Utiliser le skill avec des arguments
/react Crée un composant React pour un formulaire de contact avec validation
```

### Exemple complet

```bash
# Créer un skill personnalisé
mkdir -p skills
cat > skills/python.md << 'EOF'
---
name: python
description: Développement Python
---

# Développement Python

Aide au développement Python avec:
- Création de scripts
- Gestion de packages
- Tests
- Documentation

## Exemples

### Créer un script
Pour créer un script Python, utilisez la syntaxe suivante:
```python
#!/usr/bin/env python3
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
```

### Gestion de packages
Pour gérer les dépendances, utilisez requirements.txt:
```
requests>=2.31.0
rich>=13.7.0
```
EOF

# Utiliser le skill
/python Crée un script Python pour analyser un fichier CSV

# GLM Code va utiliser le skill pour créer le script approprié
```

## Tutoriel 5 : Mode orchestrateur

### Objectif
Apprendre à utiliser le mode orchestrateur pour des tâches complexes.

### Prérequis
- Ollama installé
- Modèle qwen2.5-coder téléchargé

### Étapes

#### 1. Configuration du mode orchestrateur

```bash
# Éditer le fichier de configuration
nano config.toml

# Ajouter la configuration du codeur
[coder]
enabled = true
base_url = "http://localhost:11434/v1"
model = "qwen2.5-coder:latest"
api_key = ""
fallback_model = ""
max_retries = 3
temperature = 0.2
max_tokens = 8192
```

#### 2. Activer le mode orchestrateur

```bash
# Activer le codeur
/coder enable

# Vérifier que le codeur est activé
/coder status
```

#### 3. Utiliser le mode orchestrateur

```bash
# Créer une application complexe
Crée une application web Django avec les fonctionnalités suivantes:
- Système d'authentification
- Blog avec CRUD
- Panier d'achat
- Dashboard administratif

# GLM Code va:
# 1. Le cerveau analysera la demande globale
# 2. Déléguera la création de l'application au codeur
# 3. Le codeur générera tous les fichiers nécessaires
# 4. Le cerveau vérifiera et appliquera les résultats
```

### Exemple complet

```bash
# Configurer le mode orchestrateur
# (voir étapes ci-dessus)

# Créer une application complète
Crée une application Flask avec:
- Modèle SQLAlchemy
- API REST
- Frontend React
- Tests unitaires
- Documentation

# Le codeur va générer tous les fichiers nécessaires:
# - app.py (Flask application)
# - models.py (SQLAlchemy models)
# - api.py (REST API)
# - frontend/ (React application)
# - tests/ (unit tests)
# - requirements.txt
# - README.md

# Vérifier les fichiers créés
list_dir

# Exécuter l'application
run_command python app.py
```

## Tutoriel 6 : Intégration avec des outils externes

### Objectif
Apprendre à intégrer GLM Code avec des outils externes.

### Étapes

#### 1. Intégration avec Git

```bash
# Créer un dépôt Git
git init

# Ajouter des fichiers
git add .

# Faire un commit
git commit -m "Initial commit"

# Pousser sur GitHub
git remote add origin https://github.com/votre-username/projet.git
git push -u origin main
```

#### 2. Intégration avec Docker

```bash
# Créer un Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "app.py"]
EOF

# Construire l'image Docker
docker build -t glm-code-app .

# Exécuter le conteneur
docker run -p 5000:5000 glm-code-app
```

#### 3. Intégration avec des éditeurs de code

```bash
# VS Code
code .

# Sublime Text
subl .

# Vim
vim .
```

### Exemple complet

```bash
# Créer un projet complet
glm

# Crée une application Flask avec Docker

# GLM Code va:
# 1. Créer l'application Flask
# 2. Créer un Dockerfile
# 3. Créer un docker-compose.yml
# 4. Créer des tests
# 5. Créer une documentation

# Initialiser Git
git init
git add .
git commit -m "Initial commit"

# Construire et exécuter Docker
docker build -t glm-app .
docker run -p 5000:5000 glm-app

# Ouvrir dans VS Code
code .
```

## Tutoriel 7 : Dépannage et bonnes pratiques

### Objectif
Apprendre à dépanner GLM Code et suivre les bonnes pratiques.

### Étapes

#### 1. Dépannage

```bash
# Problème: Clé API manquante
# Solution: Vérifier la configuration
cat config.toml

# Problème: Mode plein écran non fonctionnel
# Solution: Utiliser le mode simple
GLMCODE_SIMPLE=1 glm

# Problème: Commandes shell qui ne fonctionnent pas
# Solution: Vérifier la syntaxe et les permissions
which commande
ls -la $(which commande)

# Problème: Mode orchestrateur non fonctionnel
# Solution: Vérifier Ollama
ollama --version
ollama list
```

#### 2. Bonnes pratiques

```bash
# 1. Utiliser des versions virtuelles
python -m venv venv
source venv/bin/activate

# 2. Gérer les dépendances
pip freeze > requirements.txt

# 3. Écrire des tests
pytest tests/

# 4. Documenter le code
# Utiliser des docstrings
def fonction():
    """Documentation de la fonction."""
    pass

# 5. Versionner le code
git add .
git commit -m "Message descriptif"
```

### Exemple complet

```bash
# Créer un projet avec bonnes pratiques
glm

# Crée un projet Python avec:
# - Structure de projet standard
# - Tests unitaires
# - Documentation
# - Gestion des dépendances
# - Configuration Git

# GLM Code va créer une structure de projet propre:
# projet/
# ├── src/
# │   └── main.py
# ├── tests/
# │   └── test_main.py
# ├── requirements.txt
# ├── README.md
# └── .gitignore

# Tester le projet
pytest tests/

# Documenter le projet
# GLM Code va générer une documentation complète

# Versionner le projet
git init
git add .
git commit -m "Initial commit"
```

## Tutoriel 8 : Cas d'usage avancés

### Objectif
Explorer des cas d'usage avancés de GLM Code.

### Étapes

#### 1. Migration de code

```bash
# Migrer de Python 2 à Python 3
Migre le code du dossier legacy/ de Python 2 à Python 3

# GLM Code va:
# 1. Analyser tous les fichiers Python
# 2. Identifier les éléments à migrer
# 3. Appliquer les modifications nécessaires
# 4. Vérifier la syntaxe
```

#### 2. Refactoring

```bash
# Refactoriser une base de code
Refactorise le projet pour améliorer:
- La structure du code
- La performance
- La maintenabilité
- Les tests

# GLM Code va:
# 1. Analyser le code existant
# 2. Identifier les problèmes
# 3. Proposer des améliorations
# 4. Appliquer les modifications
```

#### 3. Création d'une API REST

```bash
# Créer une API REST complète
Crée une API REST avec:
- FastAPI
- SQLAlchemy
- Authentification JWT
- Tests
- Documentation

# GLM Code va créer:
# - main.py (FastAPI application)
# - models.py (SQLAlchemy models)
# - auth.py (JWT authentication)
# - tests/ (test suite)
# - docs/ (documentation)
```

### Exemple complet

```bash
# Créer une application complète
glm

# Crée une application web complète avec:
# - Backend Flask
# - Frontend React
# - Base de données PostgreSQL
# - Tests unitaires et d'intégration
# - Documentation
# - Configuration Docker

# GLM Code va générer une structure complète:
# backend/
# ├── app.py
# ├── models.py
# ├── database.py
# ├── tests/
# frontend/
# ├── src/
# ├── public/
# ├── tests/
# docker-compose.yml
# README.md

# Déployer l'application
docker-compose up -d

# Tester l'application
curl http://localhost:5000/api/health
```

## Conclusion

Ces tutoriels vous ont montré comment utiliser GLM Code pour diverses tâches de développement. De l'installation de base aux cas d'usage avancés, GLM Code peut vous aider à accélérer votre développement et à améliorer la qualité de votre code.

### Prochaines étapes

1. **Explorer la documentation** : Consultez la documentation complète pour plus de détails
2. **Créer vos propres skills** : Développez des skills personnalisés pour vos besoins spécifiques
3. **Contribuer au projet** : Aidez à améliorer GLM Code en contribuant au code ou à la documentation
4. **Rejoindre la communauté** : Participez aux discussions et partagez votre expérience

### Ressources supplémentaires

- [Documentation complète](README.md)
- [Guide de développement](development.md)
- [Guide de contribution](contributing.md)
- [Exemples d'utilisation](examples.md)
- [Forum de discussion](lien-du-forum)

---

*Bonne utilisation de GLM Code ! N'hésitez pas à explorer et à expérimenter avec les différentes fonctionnalités.*