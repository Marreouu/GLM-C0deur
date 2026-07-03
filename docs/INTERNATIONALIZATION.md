# Internationalisation - GLM Code

Ce document décrit l'approche internationalisation (i18n) et localisation (l10n) du projet GLM Code, y compris la structure des fichiers, les outils utilisés et les bonnes pratiques.

## Vue d'ensemble

GLM Code est conçu pour être accessible aux développeurs du monde entier. Nous soutenons actuellement le français et l'anglais, avec des plans pour ajouter d'autres langues à l'avenir.

## Structure des fichiers

### Fichiers de traduction

```
docs/
├── locales/
│   ├── fr/
│   │   ├── README.md
│   │   ├── development.md
│   │   ├── contributing.md
│   │   └── ...
│   ├── en/
│   │   ├── README.md
│   │   ├── development.md
│   │   ├── contributing.md
│   │   └── ...
│   └── es/
│       ├── README.md
│       ├── development.md
│       ├── contributing.md
│       └── ...
```

### Fichiers source

```
glmcode/
├── __init__.py
├── agent.py
├── client.py
├── config.py
├── tools.py
├── ui.py
├── skills.py
├── coder.py
├── cli.py
├── tui.py
└── ui.py
```

## Outils et technologies

### Bibliothèques utilisées

#### Babel

```python
# setup.py
from setuptools import setup

setup(
    # ...
    install_requires=[
        'Babel>=2.9.0',
    ],
)
```

#### gettext

```python
# glmcode/i18n.py
import gettext
import os

def setup_i18n():
    """Configure l'internationalisation."""
    localedir = os.path.join(os.path.dirname(__file__), 'locales')
    lang = os.environ.get('LANG', 'en').split('_')[0]
    
    try:
        translation = gettext.translation('glmcode', localedir, languages=[lang])
        translation.install()
        return translation.gettext
    except FileNotFoundError:
        return lambda x: x
```

### Configuration

#### pyproject.toml

```toml
[tool.babel]
extract_messages = [
    'glmcode/*.py',
    'docs/*.md',
]
output_file = 'glmcode/locales/messages.pot'
width = 80
```

#### .babel.ini

```ini
[python: **.py]
[jinja2: **/*.html]
[extractors]
custom = glmcode.i18n:extract_custom
```

## Processus de traduction

### Extraction des messages

```bash
# Extraire les messages des fichiers source
pybabel extract -F .babel.ini -o glmcode/locales/messages.pot glmcode/

# Mettre à jour les fichiers de traduction
pybabel update -i glmcode/locales/messages.pot -d glmcode/locales

# Compiler les fichiers de traduction
pybabel compile -i glmcode/locales/messages.pot -d glmcode/locales
```

### Workflow de traduction

1. **Extraction** : Extraire les messages des fichiers source
2. **Mise à jour** : Mettre à jour les fichiers de traduction existants
3. **Traduction** : Traduire les nouveaux messages
4. **Compilation** : Compiler les fichiers de traduction
5. **Intégration** : Intégrer les traductions dans le code

### Gestion des fichiers de traduction

#### Fichiers PO

```po
# glmcode/locales/fr/LC_MESSAGES/messages.po
msgid "Hello, World!"
msgstr "Bonjour le monde !"

msgid "File not found: %s"
msgstr "Fichier non trouvé : %s"
```

#### Fichiers MO

```bash
# Compiler les fichiers PO en MO
msgfmt glmcode/locales/fr/LC_MESSAGES/messages.po -o glmcode/locales/fr/LC_MESSAGES/messages.mo
```

## Implémentation dans le code

### Utilisation de gettext

```python
# glmcode/ui.py
import gettext
from .i18n import setup_i18n

_ = setup_i18n()

def print_message(message: str) -> None:
    """Affiche un message traduit."""
    print(_(message))

# Exemple d'utilisation
print_message("Hello, World!")
```

### Formatage des messages

```python
# Messages avec paramètres
msgid "File %s has been saved successfully."
msgstr "Le fichier %s a été enregistré avec succès."

# Messages pluriels
msgid "One file processed."
msgid_plural "%d files processed."
msgstr[0] "Un fichier traité."
msgstr[1] "%d fichiers traités."
```

### Gestion des langues

```python
# glmcode/config.py
from dataclasses import dataclass

@dataclass
class Config:
    language: str = "en"
    
    def get_language(self) -> str:
        """Récupère la langue configurée."""
        return self.language
    
    def set_language(self, language: str) -> None:
        """Définit la langue."""
        self.language = language
```

## Documentation

### Structure multilingue

```
docs/
├── README.md                    # Documentation principale (fr)
├── development.md              # Guide de développement (fr)
├── contributing.md             # Guide de contribution (fr)
├── locales/
│   ├── en/
│   │   ├── README.md          # Documentation principale (en)
│   │   ├── development.md    # Guide de développement (en)
│   │   └── contributing.md   # Guide de contribution (en)
│   ├── es/
│   │   ├── README.md          # Documentation principale (es)
│   │   ├── development.md    # Guide de développement (es)
│   │   └── contributing.md   # Guide de contribution (es)
│   └── zh/
│       ├── README.md          # Documentation principale (zh)
│       ├── development.md    # Guide de développement (zh)
│       └── contributing.md   # Guide de contribution (zh)
```

### Gestion des liens

```markdown
<!-- docs/README.md -->
## Documentation

- [English](locales/en/README.md)
- [Français](README.md)
- [Español](locales/es/README.md)
- [中文](locales/zh/README.md)
```

### Traduction de la documentation

#### Utilisation de Sphinx

```python
# conf.py
extensions = [
    'sphinxcontrib.babel',
    'sphinx_intl',
]

html_context = {
    'current_language': 'fr',
}
```

#### Gestion des traductions

```bash
# Générer les fichiers de traduction
sphinx-intl update -l fr

# Compiler la documentation
sphinx-build -b html . _build/html
```

## Bonnes pratiques

### Guidelines de traduction

1. **Consistance** : Utiliser les mêmes termes pour les mêmes concepts
2. **Clarté** : Les traductions doivent être claires et concises
3. **Contexte** : Tenir compte du contexte technique
4. **Culturalisation** : Adapter aux cultures locales
5. **Mise à jour** : Garder les traductions à jour avec le code

### Qualité des traductions

#### Vérification automatique

```bash
# Vérifier la qualité des traductions
pybabel check -i glmcode/locales/messages.pot -d glmcode/locales
```

#### Relecture humaine

1. **Native speakers** : Faire relire par des locuteurs natifs
2. **Experts techniques** : Faire relire par des experts du domaine
3. **Utilisateurs finaux** : Recueillir le feedback des utilisateurs

### Gestion des variations

#### Régionalisations

```python
# glmcode/i18n.py
import locale

def setup_regional():
    """Configure la régionalisation."""
    try:
        locale.setlocale(locale.LC_ALL, '')
        locale_format = locale.format_string
    except locale.Error:
        locale_format = lambda x, y: x
    
    return locale_format
```

#### Formats de date et heure

```python
from datetime import datetime

def format_date(date: datetime) -> str:
    """Formate une date selon la locale."""
    return date.strftime('%x')  # Format local
```

#### Formats de nombre

```python
import locale

def format_number(number: float) -> str:
    """Formate un nombre selon la locale."""
    locale.setlocale(locale.LC_ALL, '')
    return locale.format_string("%d", number, grouping=True)
```

## Support des langues

### Langues supportées

| Langue | Code | Statut |
|--------|------|--------|
| Français | fr | ✅ Complet |
| Anglais | en | ✅ Complet |
| Espagnol | es | 🚧 En cours |
| Allemand | de | 🚧 En cours |
| Chinois | zh | 🚧 En cours |
| Japonais | ja | 📝 Planifié |
| Portugais | pt | 📝 Planifié |
| Russe | ru | 📝 Planifié |

### Priorisation des langues

1. **Anglais** : Langue par défaut
2. **Français** : Langue principale du projet
3. **Espagnol** : Demande élevée de la communauté
4. **Allemand** : Demande modérée
5. **Chinois** : Marché important
6. **Autres** : Selon la demande

## Outils et ressources

### Outils de traduction

#### Poedit

```bash
# Éditeur de fichiers PO
poedit glmcode/locales/fr/LC_MESSAGES/messages.po
```

#### Weblate

```python
# Configuration Weblate
# weblate.cfg
[weblate]
url = https://hosted.weblate.org/api/
```

### Ressources

#### Glossaires

- [Glossaire technique fr-en](glossary/fr-en.txt)
- [Glossaire technique es-en](glossary/es-en.txt)
- [Glossaire technique de-en](glossary/de-en.txt)

#### Style guides

- [Style guide français](style-guide/fr.md)
- [Style guide anglais](style-guide/en.md)
- [Style guide espagnol](style-guide/es.md)

## Tests

### Tests d'internationalisation

```python
# tests/test_i18n.py
import pytest
from glmcode.i18n import setup_i18n

def test_french_translation():
    """Test la traduction française."""
    _ = setup_i18n()
    assert _("Hello, World!") == "Bonjour le monde !"

def test_english_translation():
    """Test la traduction anglaise."""
    os.environ['LANG'] = 'en_US.UTF-8'
    _ = setup_i18n()
    assert _("Hello, World!") == "Hello, World!"
```

### Tests de localisation

```python
# tests/test_l10n.py
import pytest
from glmcode.i18n import setup_regional

def test_date_format():
    """Test le formatage des dates."""
    format_date = setup_regional()
    assert format_date(2024, 1, 1) == "01/01/2024"

def test_number_format():
    """Test le formatage des nombres."""
    format_number = setup_regional()
    assert format_number(1000.0) == "1,000"
```

## Déploiement

### Gestion des traductions

#### Mise à jour automatique

```yaml
# .github/workflows/i18n.yml
name: Internationalization
on:
  push:
    paths:
      - 'glmcode/**/*.py'
      - 'docs/**/*.md'

jobs:
  update-translations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Update translations
        run: |
          pybabel extract -F .babel.ini -o glmcode/locales/messages.pot glmcode/
          pybabel update -i glmcode/locales/messages.pot -d glmcode/locales
```

#### Déploiement des traductions

```bash
# Déployer les traductions
pybabel compile -i glmcode/locales/messages.pot -d glmcode/locales
```

### Documentation multilingue

#### Génération automatique

```python
# scripts/generate_docs.py
import os
import shutil

def generate_multilingual_docs():
    """Génère la documentation multilingue."""
    languages = ['en', 'fr', 'es', 'de']
    
    for lang in languages:
        src_dir = f'docs/locales/{lang}'
        dst_dir = f'docs/{lang}'
        
        if os.path.exists(src_dir):
            shutil.copytree(src_dir, dst_dir)
```

## Contribuer aux traductions

### Processus de contribution

1. **Choisir une langue** : Sélectionner une langue à traduire
2. **Extraire les messages** : `pybabel extract`
3. **Mettre à jour les fichiers** : `pybabel update`
4. **Traduire les messages** : Éditer les fichiers PO
5. **Compiler les traductions** : `pybabel compile`
6. **Créer une PR** : Proposer les traductions

### Guidelines pour les contributeurs

1. **Respecter le style** : Suivre le style guide existant
2. **Tenir compte du contexte** : Comprendre le code avant de traduire
3. **Tester les traductions** : Vérifier que les traductions fonctionnent
4. **Mettre à jour régulièrement** : Garder les traductions à jour

## Contact

### Équipe d'internationalisation

- **Coordinateur i18n** : [Email]
- **Traducteurs** : [Email]
- **Relecteurs** : [Email]

### Ressources

- [Documentation i18n](https://docs.python.org/3/library/gettext.html)
- [Guide de traduction](https://www.gnu.org/software/gettext/manual/)
- [Outils de traduction](https://weblate.org/)

---

*Cette documentation d'internationalisation est régulièrement mise à jour pour refléter l'évolution du projet. Pour plus d'informations, consultez le [README principal](../README.md) et la [documentation](./README.md).*