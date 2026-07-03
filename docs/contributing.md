# Guide de contribution - GLM Code

Merci d'intéresser à contribuer à GLM Code ! Ce guide explique comment participer au développement du projet.

## Code de conduite

- Soyez respectueux et constructif
- Adhésion aux principes de [Contributor Covenant](https://www.contributor-covenant.org/)
- Focalisez-vous sur ce qui est meilleur pour la communauté

## Processus de contribution

### 1. Fork et clone

1. Fork le dépôt sur GitHub
2. Clonez votre fork localement :
```bash
git clone https://github.com/votre-username/glm-code.git
cd glm-code
```

3. Ajoutez le dépôt original en upstream :
```bash
git remote add upstream https://github.com/organisation-originale/glm-code.git
```

### 2. Créez une branche de fonctionnalité

```bash
git checkout -b feature/nouvelle-fonctionnalite
```

### 3. Développez

Suivez les bonnes pratiques décrites dans [development.md](development.md).

### 4. Testez

Assurez-vous que tous les tests passent :
```bash
pytest
```

### 5. Commitez

Utilisez des commits atomiques et descriptifs :
```bash
git add .
git commit -m "feat: ajouter l'outil git_commit"
```

### 6. Poussez

```bash
git push origin feature/nouvelle-fonctionnalite
```

### 7. Créez une Pull Request

1. Allez sur GitHub et créez une PR depuis votre branche
2. Remplissez le template de PR
3. Attendez les reviews

## Types de contributions

### Rapports de bugs

1. Vérifiez si le bug n'a pas déjà été rapporté
2. Créez un issue avec :
   - Titre descriptif
   - Description détaillée
   - Étapes pour reproduire
   - Comportement attendu
   - Comportement actuel
   - Environnement (OS, Python, version de GLM Code)

### Nouvelles fonctionnalités

1. Discutez d'abord dans un issue
2. Proposez une solution
3. Implémentez avec tests
4. Mettez à jour la documentation

### Documentation

- Améliorez la documentation existante
- Ajoutez des exemples
- Corrigez les erreurs
- traduisez dans d'autres langues

### Traductions

Le projet est actuellement en français. Pour ajouter d'autres langues :

1. Créez un fichier `docs/<lang>/README.md`
2. Traduisez la documentation
3. Mettez à jour l'interface utilisateur

## Standards de code

### Style de code

- Respectez PEP 8
- Utilisez Black pour le formatage
- Utilisez des types hints partout
- Documentez avec des docstrings

### Exemple de docstring

```python
def read_file(path: str, **_) -> str:
    """
    Lit et renvoie le contenu texte d'un fichier.
    
    Args:
        path: Chemin du fichier à lire
        
    Returns:
        Contenu du fichier ou message d'erreur
        
    Raises:
        FileNotFoundError: Si le fichier n'existe pas
    """
    pass
```

### Tests

- Écrivez des tests pour tout nouveau code
- Utilisez pytest
- Maintenez un coverage de 80% minimum
- Testez les cas limites

### Exemple de test

```python
def test_read_file():
    # Créer un fichier test
    test_file = "test.txt"
    with open(test_file, "w") as f:
        f.write("Hello World")
    
    # Tester la fonction
    result = read_file(test_file)
    assert result == "Hello World"
    
    # Nettoyer
    os.remove(test_file)
```

## Structure des Pull Requests

### Template de PR

```markdown
## Description
Courte description des changements

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Documentation
- [ ] Refactoring
- [ ] Performance
- [ ] Autre

## Checklist
- [ ] Les tests passent
- [ ] La documentation est mise à jour
- [ ] Le code respecte les standards
- [ ] Les changements sont testés

## Questions
Posez des questions si nécessaire
```

### Review de PR

Lorsque vous reviewez une PR :

1. Vérifiez que tous les tests passent
2. Lisez le code pour les problèmes évidents
3. Testez fonctionnellement si possible
4. Soyez constructif dans les commentaires
5. Approvez ou demandez des modifications

## Dépannage

### Problèmes courants

1. **Conflits de merge** :
```bash
git fetch upstream
git merge upstream/main
git push origin votre-branche
```

2. **Tests qui échouent** :
```bash
pytest --tb=short
```

3. **Problème de dépendances** :
```bash
pip install -r requirements.txt
```

### Obtenir de l'aide

1. Consultez la [documentation](README.md)
2. Cherchez dans les issues existantes
3. Créez un nouveau issue si nécessaire
4. Rejoignez notre Discord/Slack

## Reconnaissance

Les contributeurs seront reconnus dans :
- Le fichier `CONTRIBUTORS.md`
- Les releases
- Les commits

### Format des contributeurs

```markdown
- [Nom d'utilisateur](lien-github) - Description des contributions
```

## Licence

En contribuant à GLM Code, vous acceptez que vos contributions soient sous licence [MIT License](LICENSE).

## Remerciements

Merci de contribuer à GLM Code ! 🎉