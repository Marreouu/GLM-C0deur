# Exemples d'utilisation - GLM Code

Ce document présente des exemples concrets d'utilisation de GLM Code dans différents scénarios de développement.

## Exemples de base

### 1. Utilisation des mentions @fichier

```bash
# Lancer GLM Code
glm

# Analyser un fichier existant
Analyse ce fichier @src/app.py et identifie les problèmes potentiels
```

GLM Code va :
1. Lire automatiquement le fichier `src/app.py`
2. Analyser le code pour les problèmes courants
3. Proposer des améliorations basées sur le contenu

### 2. Création d'un projet Python

```bash
# Lancer GLM Code
glm

# Demander la création d'un projet
Crée un projet Python simple avec un fichier main.py qui affiche "Hello World"
```

GLM Code va :
1. Créer le fichier `main.py` avec le contenu approprié
2. Vous demander confirmation avant d'écrire les fichiers
3. Créer un fichier `requirements.txt` avec les dépendances

### 2. Analyse de code

```bash
# Analyser un fichier existant
Analyse le fichier src/app.py et identifie les problèmes potentiels
```

GLM Code va :
1. Lire le fichier `src/app.py`
2. Analyser le code pour les problèmes courants
3. Proposer des améliorations

### 3. Refactoring

```bash
# Refactoriser une fonction
Refactorise la fonction calculate_total dans src/utils.py pour qu'elle soit plus efficace
```

GLM Code va :
1. Lire le fichier `src/utils.py`
2. Identifier la fonction `calculate_total`
3. Proposer une version refactorisée
4. Appliquer les modifications après confirmation

## Exemples avancés

### 4. Création d'une API REST

```bash
# Créer une API Flask
Crée une API REST avec Flask qui expose les endpoints suivants :
- GET /api/users - Liste tous les utilisateurs
- POST /api/users - Crée un nouvel utilisateur
- GET /api/users/<id> - Récupère un utilisateur par ID
```

GLM Code va :
1. Créer les fichiers nécessaires (`app.py`, `models.py`, `requirements.txt`)
2. Implémenter les endpoints avec validation
3. Ajouter des tests unitaires
4. Documenter l'API

### 5. Migration de code

```bash
# Migrer de Python 2 à Python 3
Migre le code du dossier legacy/ de Python 2 à Python 3. Gère les imports, les print statements, et les divisions.
```

GLM Code va :
1. Analyser tous les fichiers Python dans `legacy/`
2. Identifier les éléments à migrer
3. Appliquer les modifications nécessaires
4. Vérifier la syntaxe

### 6. Optimisation de performance

```bash
# Optimiser les performances
Analyse le dossier src/ pour identifier les problèmes de performance et propose des optimisations.
```

GLM Code va :
1. Analyser le code pour les boucles inefficaces
2. Identifier les opérations coûteuses
3. Proposer des optimisations
4. Appliquer les modifications après confirmation

## Exemples avec le mode orchestrateur

### 7. Création d'une application web complète

```bash
# Activer le mode orchestrateur
/coder enable

# Créer une application web complète
Crée une application web Django avec les fonctionnalités suivantes :
- Système d'authentification
- Blog avec CRUD
- Panier d'achat
- Dashboard administratif
```

GLM Code va :
1. Le cerveau analysera la demande globale
2. Déléguera la création de l'application au codeur
3. Le codeur générera tous les fichiers nécessaires
4. Le cerveau vérifiera et appliquera les résultats

### 8. Génération de tests automatisés

```bash
# Générer des tests pour un projet existant
Génère des tests unitaires et d'intégration complets pour le projet existant. Couvre tous les modules et les cas limites.
```

GLM Code va :
1. Analyser la structure du projet
2. Générer des tests pour chaque module
3. Créer des fixtures si nécessaire
4. Configurer le framework de test

## Exemples avec les skills

### 9. Utilisation des skills intégrés

```bash
# Utiliser le skill de revue de code
/revue-code src/main.py

# Utiliser le skill de débogage
/debug src/app.py --error "division by zero"

# Utiliser le skill de tests
/tests src/utils.py --unit --integration
```

### 10. Création de skills personnalisés

Créez un fichier `skills/react.md` :

```yaml
---
name: react
description: Développement React
---

# Développement React

Aide au développement d'applications React avec :
- Création de composants
- Gestion d'état
- Routing
- Tests
```

Utilisez-le ensuite :

```bash
/react Crée un composant React pour un formulaire de contact avec validation
```

## Exemples automatisés

### 11. Scripts de build

```bash
# Automatiser le processus de build
Crée un script build.sh qui :
- Installe les dépendances
- Lance les tests
- Build le projet
- Déploie sur le serveur
```

### 12. Configuration CI/CD

```bash
# Configurer GitHub Actions
Configure GitHub Actions pour le projet avec :
- Tests sur Python 3.9, 3.10, 3.11
- Build du package
- Déploiement sur PyPI
- Notifications Slack
```

## Exemples multi-fichiers

### 13. Création d'un microservice

```bash
# Créer un microservice Python
Crée un microservice Python avec :
- API REST avec FastAPI
- Base de données PostgreSQL
- Docker configuration
- Tests unitaires
- Documentation OpenAPI
```

GLM Code va créer :
- `main.py` - Application FastAPI
- `models.py` - Modèles SQLAlchemy
- `database.py` - Configuration de la base
- `tests/` - Tests unitaires
- `Dockerfile` - Configuration Docker
- `requirements.txt` - Dépendances

### 14. Migration de monolithique à microservices

```bash
# Migrer une application monolithique
Transforme l'application monolithique actuelle en architecture microservices. Identifie les modules qui peuvent être extraits et crée des services séparés.
```

GLM Code va :
1. Analyser l'architecture actuelle
2. Identifier les modules candidates
3. Créer des services séparés
4. Mettre à jour la configuration
5. Gérer les communications inter-services

## Exemples de débogage

### 15. Diagnostic de problèmes

```bash
# Diagnostiquer un problème de performance
Le site est lent. Diagnostique les problèmes de performance et propose des solutions.
```

GLM Code va :
1. Analyser le code pour les goulets d'étranglement
2. Vérifier les requêtes SQL
3. Identifier les opérations coûteuses
4. Proposer des optimisations

### 16. Debug d'erreurs

```bash
# Debuguer une erreur spécifique
L'application plante avec l'erreur "AttributeError: 'NoneType' object has no attribute 'user'". Trouve la cause et propose une solution.
```

GLM Code va :
1. Analyser les logs d'erreur
2. Identifier la ligne de code problématique
3. Proposer une solution
4. Appliquer le fix

## Exemples de documentation

### 17. Génération de documentation

```bash
# Générer la documentation du projet
Génère la documentation complète du projet avec :
- Documentation API
- Guide d'installation
- Tutoriels
- FAQ
```

### 18. Mise à jour de la documentation

```bash
# Mettre à jour la documentation
Met à jour la documentation pour refléter les changements récents dans le code. Ajoute des exemples et clarifie les concepts complexes.
```

## Exemples DevOps

### 19. Configuration Kubernetes

```bash
# Configurer Kubernetes
Crée les manifests Kubernetes pour déployer l'application en production avec :
- Deployment
- Service
- Ingress
- ConfigMap
- Secrets
```

### 20. Monitoring et logging

```bash
# Configurer le monitoring
Configure le monitoring avec Prometheus et Grafana. Inclut des dashboards pour :
- Métriques d'application
- Performance
- Erreurs
- Usage des ressources
```

## Exemples de sécurité

### 21. Audit de sécurité

```bash
# Auditer la sécurité
Audite la sécurité de l'application et identifie les vulnérabilités courantes. Propose des solutions pour chaque problème trouvé.
```

### 22. Configuration de la sécurité

```bash
# Configurer la sécurité
Configure la sécurité de l'application avec :
- Authentification JWT
- Autorisation basée sur les rôles
- Validation des entrées
- Protection contre les injections SQL
- HTTPS
```

## Exemples de tests

### 23. Tests unitaires

```bash
# Générer des tests unitaires
Génère des tests unitaires complets pour le projet. Couvre toutes les fonctions et méthodes avec des cas positifs et négatifs.
```

### 24. Tests d'intégration

```bash
# Générer des tests d'intégration
Génère des tests d'intégration qui testent l'interaction entre les différents modules du projet.
```

## Exemples de performance

### 25. Optimisation de la base de données

```bash
# Optimiser la base de données
Analyse les requêtes SQL et optimise la base de données pour améliorer les performances.
```

### 26. Cache et performance

```bash
# Implémenter le caching
Implémente un système de caching pour améliorer les performances de l'application. Utilise Redis pour le caching.
```

## Bonnes pratiques

### 27. Code review automatisé

```bash
# Faire un code review
Fais un code review complet du projet. Vérifie la qualité du code, les bonnes pratiques, et les potentiels bugs.
```

### 28. Refactoring continu

```bash
# Refactoriser le code
Refactorise le code pour améliorer sa lisibilité, sa maintenabilité et sa performance. Applique les principes SOLID et DRY.
```

## Exemples avancés

### 29. Machine learning

```bash
# Créer un modèle ML
Crée un modèle de machine learning pour prédire les ventes basé sur les données historiques. Inclut :
- Prétraitement des données
- Entraînement du modèle
- Évaluation
- Déploiement
```

### 30. Big data

```bash
# Traiter des données big data
Crée un pipeline de traitement de données big data avec Spark pour analyser de grands volumes de données.
```

## Conclusion

Ces exemples montrent la polyvalence de GLM Code pour divers scénarios de développement. Que vous soyez débutant ou expert, GLM Code peut vous aider à accélérer votre développement et à améliorer la qualité de votre code.

Pour plus d'exemples, consultez le [README principal](../README.md) et la [documentation](./README.md).