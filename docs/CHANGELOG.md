# Changelog - GLM Code

Tous les changements significatifs de GLM Code seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet suit la [sémantique des versions](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-XX

### Ajouté
- Version initiale de GLM Code
- Interface utilisateur TUI avec Rich et prompt_toolkit
- Interface utilisateur CLI simple
- Système de conversation avec LLM (GLM-4.7 via API Z.ai)
- Outils natifs (read_file, write_file, edit_file, list_dir, run_command)
- Système de skills basé sur des fichiers Markdown
- Mode orchestrateur avec délégation à un modèle local
- Gestion des sessions avec sauvegarde et reprise
- Configuration centralisée avec TOML
- Commandes slash (/help, /reset, /model, /mode, /skills, etc.)
- Trois modes de travail (normal, auto, plan)
- Intégration avec Git et Docker
- Documentation complète

### Modifié
- Aucun

### Supprimé
- Aucun

### Corrections
- Aucun

## [1.1.0] - 2024-12-XX

### Ajouté
- Fonctionnalité de sélection de fichiers avec @
- Autocompletion des fichiers dans l'interface TUI
- Support des mentions @fichier dans les messages
- Intégration avec le système de complétion existant
- Amélioration de l'expérience utilisateur pour la sélection de fichiers

### Modifié
- Amélioration de l'autocompletion dans l'interface CLI
- Optimisation de la recherche de fichiers dans les grands projets
- Mise à jour de la documentation pour inclure la nouvelle fonctionnalité

### Supprimé
- Aucun

### Corrections
- Correction des problèmes de performance dans la recherche de fichiers
- Amélioration de la gestion des erreurs pour les fichiers non trouvés
- Optimisation de l'affichage des mentions @fichier dans le transcript

---

## Format de version

- **Majeur** : Changements cassants ou nouvelles fonctionnalités majeures
- **Mineur** : Nouvelles fonctionnalités non cassantes
- **Patch** : Corrections de bugs et petites améliorations

## Prochaines versions

### [1.2.0] (Prochain)
- Support des skills externes (GitHub, GitLab)
- Amélioration du mode orchestrateur
- Support des modèles multimodaux
- Interface web expérimentale

### [2.0.0] (À venir)
- Refonte complète de l'architecture
- Support multi-LLM
- Plugin system
- Marketplace de skills

## Contribuer

Les contributions sont les bienvenues ! Veuillez consulter le [guide de contribution](contributing.md).

## Licence

Ce projet est sous licence [MIT](LICENSE).