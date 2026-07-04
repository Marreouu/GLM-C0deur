# Guide de démarrage rapide - Configuration de GLM Codeur

## 1. Configuration de base

### Étape 1: Obtenir votre clé API
Avant de configurer GLM Codeur, vous avez besoin d'une clé API pour un service LLM:

- **OpenAI (GPT-4):** https://platform.openai.com/api-keys
- **Anthropic (Claude):** https://console.anthropic.com/
- **Google (Gemini):** https://makersuite.google.com/app/apikey

### Étape 2: Configurer votre clé API

**Méthode recommandée: Variables d'environnement**

**Windows (PowerShell):**
```powershell
# Définir pour la session courante
$env:GLM_API_KEY="votre_clé_api_ici"

# Ajouter au profil pour une persistance
Add-Content $PROFILE "`n`n# GLM Codeur`n`$env:GLM_API_KEY='votre_clé_api_ici'"
```

**Linux/macOS:**
```bash
# Définir pour la session courante
export GLM_API_KEY="votre_clé_api_ici"

# Ajouter au fichier de configuration (bashrc ou zshrc)
echo 'export GLM_API_KEY="votre_clé_api_ici"' >> ~/.bashrc
# Ou pour zsh:
echo 'export GLM_API_KEY="votre_clé_api_ieu"' >> ~/.zshrc
```

### Étape 3: Créer votre fichier de configuration
```bash
# Copier le fichier d'exemple
cp config.example.toml config.toml
```

### Étape 4: Configurer le modèle
Ouvrez `config.toml` et modifiez la section LLM:

```toml
[llm]
model = "gpt-4"  # Ou "claude-3", "gemini-pro", etc.
api_key = "${GLM_API_KEY}"  # Utilise la variable d'environnement
temperature = 0.7
max_tokens = 2000
```

## 2. Configuration rapide par scénario

### Scénario 1: Développement web moderne
```toml
[llm]
model = "gpt-4"
api_key = "${GLM_API_KEY}"
temperature = 0.3  # Plus précis pour le code

[assistants]
default = "coding"

[tools]
enable_file_operations = true
enable_web_search = true
enable_code_execution = false

[ui]
theme = "dark"
output_format = "markdown"
```

### Scénario 2: Débogage et analyse de code
```toml
[llm]
model = "claude-3"
api_key = "${GLM_API_KEY}"
temperature = 0.2  # Très précis pour l'analyse

[assistants]
default = "debug"

[tools]
enable_file_operations = true
enable_web_search = false
enable_code_execution = false

[ui]
theme = "light"
show_line_numbers = true
```

### Scénario 3: Recherche et documentation
```toml
[llm]
model = "gemini-pro"
api_key = "${GLM_API_KEY}"
temperature = 0.8  # Plus créatif

[assistants]
default = "explain"

[tools]
enable_file_operations = true
enable_web_search = true
enable_code_execution = false

[ui]
theme = "dark"
output_format = "markdown"
```

## 3. Vérifier la configuration

### Tester l'installation
```bash
# Après installation, vérifiez que tout fonctionne
glm --version
```

### Tester la configuration
```bash
# Démarrer GLM Codeur
glm

# Dans l'interface, tapez:
# "Bonjour, peux-tu m'aider avec mon projet ?"
```

## 4. Problèmes courants

### Problème: "Clé API non trouvée"
**Solution:** Vérifiez que la variable d'environnement est bien définie:
```bash
# Linux/macOS
echo $GLM_API_KEY

# Windows (PowerShell)
$env:GLM_API_KEY
```

### Problème: "Modèle non supporté"
**Solution:** Vérifiez le nom du modèle et votre accès à l'API:
```toml
[llm]
model = "gpt-4"  # Vérifiez que vous avez accès à ce modèle
```

### Problème: "Fichier de configuration introuvable"
**Solution:** Assurez-vous que le fichier s'appelle `config.toml` et est dans `~/.glmcode/`:
```bash
# Vérifier l'emplacement
ls -la ~/.glmcode/

# Recréer si nécessaire
cp config.example.toml ~/.glmcode/config.toml
```

## 5. Prochaines étapes

1. **Explorez les assistants:** Essayez différents assistants avec `/debug`, `/review`, etc.
2. **Personnalisez les prompts:** Modifiez les `system_prompt` dans `config.toml`
3. **Activez les outils:** Essayez `enable_file_operations = true` pour travailler sur vos fichiers
4. **Consultez la documentation:** Voir `config/README.md` pour plus d'options

## 6. Support

Si vous avez des problèmes:
- Vérifiez les logs: `~/.glmcode/logs/`
- Consultez la documentation complète dans `config/README.md`
- Ouvrez un issue sur GitHub: https://github.com/Marreouu/GLM-C0deur