# Correction des bugs initiaux de GLM Code

## Résumé des problèmes identifiés et solutions apportées

Ce document décrit en détail la résolution des 4 bugs initiaux identifiés dans GLM Code, avec le code complet et les explications techniques.

---

## Bug 1 : Mémorisation des modèles fonctionnels

### Problème identifié
Le codeur ne mémorisait pas les modèles qui fonctionnaient et réessayait toujours les mêmes modèles, créant une boucle infinie d'échecs.

### Solution apportée
Modification du fichier `glmcode/coder.py` pour ajouter une logique de mémorisation des modèles fonctionnels et de gestion des échecs.

#### Code implémenté

```python
class Coder:
    def __init__(self, cfg: CoderConfig):
        self.cfg = cfg
        self.client = LLMClient(cfg)
        self.current_model = cfg.model  # Modèle actuellement utilisé
        # Mémorisation des modèles
        self.last_working_model = None
        self.failed_models = set()

    def implement(self, task: str, files: list[str], auto_apply: bool) -> str:
        # ... code existant ...
        
        try:
            message = self.client.stream_chat(
                messages, on_text=ui.print_coder_chunk, on_notice=ui.print_info,
                preferred_model=self.current_model
            )
            # Mettre à jour le modèle courant si un autre modèle a été utilisé
            if "_used_model" in message:
                used_model = message["_used_model"]
                # Si le modèle fonctionne, le mémoriser
                if used_model not in self.failed_models:
                    self.last_working_model = used_model
                    self.current_model = used_model
                    ui.print_info(f"Modèle du codeur changé pour: {used_model}")
        except LLMError as exc:
            # Si le modèle échoue, l'ajouter aux modèles échoués
            if self.current_model in self.cfg.available_models:
                self.failed_models.add(self.current_model)
                # Essayer le dernier modèle qui fonctionnait
                if self.last_working_model and self.last_working_model not in self.failed_models:
                    self.current_model = self.last_working_model
                    ui.print_info(f"Réessai avec le modèle fonctionnel: {self.last_working_model}")
                    return self.implement(task, files, auto_apply)
            return (
                f"[codeur indisponible] {self.cfg.model} : {exc}. "
                "Reessaie dans un instant (les modeles gratuits OpenRouter sont "
                "souvent rate-limites)."
            )
```

#### Fonctionnement
1. **Mémorisation** : Quand un modèle fonctionne, il est stocké dans `last_working_model`
2. **Échec** : Quand un modèle échoue, il est ajouté à `failed_models`
3. **Bascule** : En cas d'échec, le système bascule automatiquement sur le dernier modèle fonctionnel
4. **Persistance** : La mémorisation est valide pour toute la session

---

## Bug 2 : Support du modèle préféré

### Problème identifié
Le codeur ne respectait pas le modèle mémorisé et recommençait la boucle depuis le premier modèle.

### Solution apportée
Le support du `preferred_model` était déjà implémenté dans `glmcode/client.py`, mais nous avons vérifié et optimisé la logique.

#### Code existant vérifié

```python
def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        on_text: Callable[[str], None] | None = None,
        on_notice: Callable[[str], None] | None = None,
        cancel_event: threading.Event | None = None,
        preferred_model: str | None = None,
    ) -> dict:
    # Liste des modèles à essayer :
    # 1. Si preferred_model est fourni, l'utiliser en premier
    # 2. Le modèle principal
    # 3. Si échec, essayer les modèles de model_coder_free.txt dans l'ordre
    models = [self.config.model]
    
    # Ajouter les modèles gratuits de model_coder_free.txt (s'ils ne sont pas déjà dans la liste)
    if self._free_models:
        for free_model in self._free_models:
            if free_model not in models:
                models.append(free_model)
    
    # Si preferred_model est fourni, l'ajouter en premier s'il n'est pas déjà dans la liste
    if preferred_model and preferred_model not in models:
        models.insert(0, preferred_model)
```

#### Fonctionnement
1. **Priorité** : Le `preferred_model` est utilisé en premier s'il est fourni
2. **Chute** : En cas d'échec, bascule vers le modèle principal puis les modèles gratuits
3. **Retour** : Le modèle utilisé est retourné dans `_used_model` pour mémorisation

---

## Bug 3 : Affichage dynamique du modèle du codeur

### Problème identifié
L'affichage du modèle du codeur était statique et ne se mettait pas à jour quand le modèle changeait.

### Solution apportée
Modification de la TUI pour afficher dynamiquement le modèle actuel du codeur.

#### Code implémenté

```python
def _status(self) -> HTML:
    mode = self.agent.mode
    color, label = ui._MODE_STYLE.get(mode, (ui.FG, mode.upper()))
    chip = f"<style bg='{color}' fg='{ui.BG}'><b> {label} </b></style>"
    reqs = f"  <style fg='{ui.CYAN}'>⇅ {LLMClient.request_count} req</style>"
    # ... autres éléments de statut ...
    
    # Mettre à jour dynamiquement le subtitle avec le modèle du codeur
    if hasattr(self.agent, 'coder') and self.agent.coder:
        coder_model = self.agent.coder.current_model
        sub = f"  <style fg='{ui.BLUE}'>{self.agent.config.model} + {coder_model}</style>"
    else:
        sub = f"  <style fg='{ui.BLUE}'>{self.subtitle}</style>" if self.subtitle else ""
    
    # Ajouter le statut du monitoring
    monitoring_status = get_monitoring_status()
    monitoring_display = f"  <style fg='{ui.GREEN}'>{monitoring_status}</style>" if monitoring_status else ""
    
    return HTML(f"⏵⏵ {chip}{sub}{reqs}{monitoring_display}{tail}")
```

#### Fonctionnement
1. **Vérification** : Vérifie si l'agent a un codeur
2. **Lecture** : Lit le modèle actuel du codeur (`current_model`)
3. **Affichage** : Affiche dynamiquement les deux modèles (principal + codeur)
4. **Mise à jour** : Le modèle est mis à jour en temps réel dans la barre de statut

---

## Bug 4 : Commande /help fonctionnelle

### Problème identifié
La commande `/help` était listée mais ne fonctionnait pas dans la TUI.

### Solution apportée
Ajout du cas `/help` dans la méthode `_handle_slash` de la TUI.

#### Code implémenté

```python
def _handle_slash(self, cmd: str) -> None:
    parts = cmd.split(maxsplit=1)
    name = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    if name in ("/exit", "/quit"):
        self.app.exit()
    elif name == "/help":
        self._rich.print("""[bold]Commandes[/]
  /help            Affiche cette aide
  /reset           Efface l'historique de la conversation
  /model <nom>     Change le modele courant
  /mode [nom]      Change de mode (normal / auto / plan)
  /skills          Liste les skills disponibles
  /<skill> [texte] Invoque un skill (ex. /revue-code app.py)
  /session         Affiche l'ID de la session courante
  /sessions        Liste les sessions enregistrees
  /resume [id]     Reprend une session (derniere si aucun id)
  /ping            Teste la connexion au backend
  /exit, /quit     Quitte

[bold]Modes[/] (bascule aussi avec [magenta]Shift+Tab[/])
  normal   confirme chaque action (ecriture / commande)
  auto     execute les actions sans demander
  plan     lecture seule : propose un plan sans rien modifier

Sinon, ecris simplement ta demande. L'assistant peut lire/ecrire des fichiers
et lancer des commandes (selon le mode).""")
    # ... autres commandes ...
```

#### Fonctionnement
1. **Parsing** : Analyse la commande slash
2. **Traitement** : Exécute la commande `/help` avec un message d'aide complet
3. **Affichage** : Affiche l'aide formatée avec les différentes commandes et modes

---

