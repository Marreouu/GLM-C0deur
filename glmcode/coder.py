"""Sous-agent 'codeur' delegue par l'orchestrateur.

Le cerveau (modele principal) delegue une tache de codage precise ; le codeur
(ex. qwen2.5-coder via Ollama) genere le contenu complet des fichiers dans un
format simple et robuste (blocs === FICHIER === ... === FIN ===), qui ne depend
pas du tool-calling natif — souvent mal gere par les modeles locaux.
"""

from __future__ import annotations

import re

from . import ui
from .client import LLMClient, LLMError
from .config import CoderConfig
from .tools import read_file, write_file

CODER_SYSTEM = """Tu es un codeur expert. On te confie une tache de programmation precise.

Pour CHAQUE fichier a creer ou modifier, produis un bloc EXACTEMENT dans ce format :
=== FICHIER: chemin/relatif/du/fichier ===
<contenu COMPLET du fichier, du debut a la fin>
=== FIN ===

Regles strictes :
- Donne toujours le contenu COMPLET du fichier, jamais un extrait ni un diff.
- N'ecris aucun texte en dehors des blocs (pas d'explication, pas de ```).
- Si tu modifies un fichier existant fourni, reprends tout son contenu avec tes changements.
- Un bloc par fichier."""

# Capture les blocs de fichiers produits par le codeur.
_BLOCK_RE = re.compile(
    r"===\s*FICHIER\s*:\s*(?P<path>.+?)\s*===\n(?P<body>.*?)\n===\s*FIN\s*===",
    re.DOTALL,
)


class Coder:
    def __init__(self, cfg: CoderConfig):
        self.cfg = cfg
        self.client = LLMClient(cfg)
        self.current_model = cfg.model  # Modèle actuellement utilisé
        self.last_working_model = None  # Dernier modèle qui a fonctionné
        self.failed_models = set()  # Modèles qui ont échoué

    def implement(self, task: str, files: list[str], auto_apply: bool) -> str:
        """Genere et applique le code pour `task`. Renvoie un resume pour le cerveau."""
        context = ""
        for path in files or []:
            content = read_file(path)
            context += f"\n----- {path} -----\n{content}\n"

        user = (
            f"Tache a coder :\n{task}\n\n"
            f"Fichiers existants pertinents :{context or ' (aucun)'}"
        )
        messages = [
            {"role": "system", "content": CODER_SYSTEM},
            {"role": "user", "content": user},
        ]

        # Utiliser le dernier modèle qui a fonctionné s'il existe
        if self.last_working_model:
            self.current_model = self.last_working_model
            ui.print_info(f"Utilisation du modèle qui a fonctionné précédemment: {self.current_model}")

        ui.print_coder_header(self.current_model)
        try:
            message = self.client.stream_chat(
                messages, on_text=ui.print_coder_chunk, on_notice=ui.print_info,
                preferred_model=self.current_model
            )
            # Mettre à jour le modèle courant si un autre modèle a été utilisé
            if "_used_model" in message:
                used_model = message["_used_model"]
                # Si le modèle a changé, mettre à jour le dernier modèle fonctionnel
                if used_model != self.current_model:
                    self.last_working_model = used_model
                    self.current_model = used_model
                    # Afficher un message pour indiquer le changement de modèle
                    ui.print_info(f"Modèle du codeur changé pour: {self.current_model}")
            else:
                # Si aucun modèle n'est indiqué, considérer que le modèle actuel a fonctionné
                self.last_working_model = self.current_model
        except LLMError as exc:
            # Ajouter le modèle actuel à la liste des modèles échoués
            self.failed_models.add(self.current_model)
            # Essayer le dernier modèle qui a fonctionné s'il existe
            if self.last_working_model and self.last_working_model not in self.failed_models:
                self.current_model = self.last_working_model
                ui.print_info(f"Réessai avec le modèle fonctionnel: {self.last_working_model}")
                return self.implement(task, files, auto_apply)
            return (
                f"[codeur indisponible] {self.cfg.model} : {exc}. "
                "Reessaie dans un instant (les modeles gratuits OpenRouter sont "
                "souvent rate-limites)."
            )
        ui.console.print()

        text = message.get("content", "")
        blocks = _BLOCK_RE.findall(text)
        if not blocks:
            return (
                "[codeur] Aucun bloc de fichier detecte dans la reponse. "
                "La tache etait peut-etre trop vague, ou le modele n'a pas suivi le format."
            )

        applied: list[str] = []
        for path, body in blocks:
            path = path.strip()
            body = _strip_fences(body)
            if not auto_apply:
                ui.print_diff_preview(path, body, _lang_for(path))
                if not ui.confirm(f"Appliquer le fichier {path} ?"):
                    applied.append(f"{path} (refuse)")
                    continue
            result = write_file(path, body)
            applied.append(path if result.startswith("[ok]") else f"{path} ({result})")

        return "[codeur] Fichiers traites : " + ", ".join(applied)


def _strip_fences(body: str) -> str:
    """Retire une eventuelle cloture Markdown ```lang ... ``` autour du contenu."""
    lines = body.split("\n")
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
        # Retire la derniere ligne de fence correspondante.
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith("```"):
                lines = lines[:i]
                break
    return "\n".join(lines)


def _lang_for(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "html": "html",
        "css": "css",
        "json": "json",
        "md": "markdown",
        "sh": "bash",
    }.get(ext, "text")
