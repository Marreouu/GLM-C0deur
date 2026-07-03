# Changelog

All notable changes to GLM Code will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nouveau système de skills basé sur des fichiers Markdown
- Support des skills Claude Code
- Interface utilisateur améliorée avec Rich
- Mode orchestrateur avec codeur délégué
- Gestion des erreurs transitoires avec retries automatiques
- Bascule automatique vers un modèle de secours

### Changed
- Refactorisation complète de l'architecture
- Migration vers GLM-4.7 via API Z.ai
- Amélioration de l'interface TUI
- Optimisation du streaming des réponses

### Fixed
- Problèmes d'encodage avec les fichiers binaires
- Gestion des chemins de fichiers sous Windows
- Erreurs de timeout sur les commandes longues

## [0.1.0] - 2024-07-03

### Added
- Version initiale de GLM Code
- Interface CLI de base
- Support des outils natifs (read_file, write_file, edit_file, list_dir, run_command)
- Configuration via fichier TOML
- Modes de travail : normal, auto, plan
- Commandes slash (/help, /reset, /model, /mode, /skills, /ping, /exit)
- Support de l'API Z.ai
- Documentation utilisateur complète

### Technical
- Architecture modulaire avec séparation des responsabilités
- Client HTTP avec streaming et gestion des erreurs
- Système de configuration flexible
- Interface utilisateur avec Rich et prompt_toolkit
- Support des variables d'environnement
- Package Python installable

## [0.0.1] - 2024-06-15

### Added
- Proof of concept
- Interface de base en ligne de commande
- Support minimal des outils de fichiers
- Configuration simple via variables d'environnement

---

## Prochaines versions

### [0.2.0] - Prochainement

#### Ajouté
- [ ] Support de Git (git_commit, git_push, etc.)
- [ ] Intégration avec les éditeurs de code (VS Code, Sublime Text)
- [ ] Système de plugins
- [ ] Support des modèles locaux (via Hugging Face)
- [ ] Interface web
- [ ] Tests unitaires complets
- [ ] Documentation API
- [ ] Internationalisation (anglais, espagnol, allemand)

#### Changé
- [ ] Optimisation des performances
- [ ] Amélioration de la gestion des erreurs
- [ ] Refactorisation du codeur délégué
- [ ] Support des workspaces multi-projets

#### Corrigé
- [ ] Gestion des fichiers volumineux
- [ ] Problèmes de compatibilité avec les anciens systèmes
- [ ] Erreurs de parsing des skills
- [ ] Problèmes d'encodage Unicode

### [0.3.0] - Prochainement

#### Ajouté
- [ ] Support des tests automatisés
- [ ] Intégration CI/CD
- [ ] Système de mise à jour automatique
- [ ] Support des profils de configuration
- [ ] Historique des conversations
- [ ] Export des conversations
- [ ] Support des modèles multimodaux
- [ ] Interface mobile

#### Changé
- [ ] Refactorisation complète de l'architecture
- [ ] Migration vers Python 3.12
- [ ] Amélioration de la sécurité
- [ ] Support des conteneurs Docker

#### Corrigé
- [ ] Tous les bugs connus
- [ ] Problèmes de performance
- [ ] Problèmes de compatibilité
- [ ] Problèmes de documentation

---

## Format de version

- **Major (X)**: Changements cassants ou nouvelles fonctionnalités majeures
- **Minor (Y)**: Nouvelles fonctionnalités non cassantes
- **Patch (Z)**: Corrections de bugs et petites améliorations

## Comment contribuer

Pour suggérer des changements ou rapporter des bugs :
1. Créez un issue sur GitHub
2. Utilisez les labels appropriés
3. Suivez le guide de contribution

## Remerciements

Merci à tous les contributeurs qui ont rendu ce projet possible !