# Skills intégrés

Ce dossier contient les skills intégrés à GLM Code.

## Structure

Chaque skill est défini dans un fichier Markdown avec la structure suivante:

```
# Nom du skill
- Description du skill

Prompt complet du skill...
```

## Skills disponibles

### review-code
- Analyse et critique de code

### generate-code
- Génération de code selon une description

### refactor-code
- Refactorisation de code existant

## Ajouter un nouveau skill

1. Créez un nouveau fichier Markdown dans ce dossier
2. Suivez la structure ci-dessus
3. Le sera automatiquement détecté et disponible via la commande `/nom-du-skill`

## Exemple

```markdown
# mon-skill
- Description de mon skill

Voici le prompt que je veux utiliser...
```