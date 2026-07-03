"""Boucle agentique : dialogue + execution d'outils avec confirmation."""

from __future__ import annotations

import json
import threading
from typing import Any

from . import session as session_store
from . import ui
from .client import LLMCancelled, LLMClient, LLMError
from .coder import Coder
from .config import Config
from .tools import (
    DESTRUCTIVE_TOOLS,
    READONLY_TOOLS_SCHEMA,
    TOOL_IMPLS,
    TOOLS_SCHEMA,
)

# Outil expose au cerveau pour deleguer le code au modele codeur.
DELEGATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "deleguer_codeur",
        "description": (
            "Delegue une tache de codage (creation/modification de fichiers) au "
            "modele codeur specialise. Utilise-le pour tout travail de code un peu "
            "consequent : decris precisement ce qu'il faut coder et liste les "
            "fichiers existants pertinents a lui fournir en contexte."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tache": {
                    "type": "string",
                    "description": "Description detaillee et autonome du code a produire",
                },
                "fichiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Chemins des fichiers existants a donner en contexte (optionnel)",
                },
            },
            "required": ["tache"],
        },
    },
}

# Modes de travail cyclables avec Shift+Tab (comme Claude Code).
MODES = ("normal", "auto", "plan")
MODE_LABELS = {
    "normal": "normal · confirme les actions",
    "auto": "auto · execute sans confirmer",
    "plan": "plan · lecture seule, propose un plan",
}

PLAN_HINT = (
    "MODE PLAN ACTIF : tu ne disposes que des outils de lecture (read_file, list_dir). "
    "Tu ne dois RIEN modifier ni executer. Analyse la demande et presente un plan "
    "d'action clair, numerote, etape par etape. Termine en indiquant a l'utilisateur "
    "de passer en mode normal ou auto (Shift+Tab) pour lancer l'execution."
)

DEFAULT_SYSTEM_PROMPT = """Tu es GLM Code, un assistant de codage expert qui travaille dans le terminal de l'utilisateur.

Tu peux lire et modifier des fichiers et lancer des commandes via les outils fournis.
Regles :
- Sois concis et direct. Reponds en francais.
- Avant de modifier un fichier, lis-le si tu n'en connais pas le contenu.
- Utilise edit_file pour de petites modifications ciblees, write_file pour un fichier neuf ou une reecriture complete.
- Explique brievement ce que tu fais, puis agis via les outils.
- N'invente pas le contenu d'un fichier : lis-le d'abord.
"""

ORCHESTRATOR_EXTRA = """

MODE ORCHESTRATEUR : tu es le cerveau. Un modele codeur specialise est disponible
via l'outil `deleguer_codeur`. Pour tout travail de code un peu consequent
(creer/modifier des fichiers, implementer une fonctionnalite), DELEGUE-le au codeur
plutot que d'ecrire le code toi-meme : reflechis, decide de l'approche, puis appelle
`deleguer_codeur` avec une tache precise et les fichiers pertinents. Reserve
read_file/list_dir/run_command a l'analyse et a la verification. Apres delegation,
verifie le resultat (lis les fichiers, lance les tests) et fais la synthese."""


class Agent:
    def __init__(self, config: Config, session_id: str | None = None):
        self.config = config
        self.client = LLMClient(config)
        # Identifiant de session + drapeau d'interruption (Ctrl+C).
        self.session_id = session_id or session_store.new_session_id()
        self.cancel_event = threading.Event()
        system = config.system_prompt.strip() or DEFAULT_SYSTEM_PROMPT
        # Orchestrateur : active le codeur delegue si configure.
        self.coder = Coder(config.coder) if config.coder.enabled else None
        if self.coder is not None:
            system += ORCHESTRATOR_EXTRA
            self.brain_tools = TOOLS_SCHEMA + [DELEGATE_SCHEMA]
        else:
            self.brain_tools = TOOLS_SCHEMA
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        self.mode = "auto" if config.auto_approve else "normal"

    def cycle_mode(self) -> str:
        idx = MODES.index(self.mode)
        self.mode = MODES[(idx + 1) % len(MODES)]
        return self.mode

    def reset(self) -> None:
        system = self.messages[0]
        self.messages = [system]
        self._save()

    def load_history(self, messages: list[dict[str, Any]]) -> None:
        """Remplace l'historique par une session reprise (garde un system en tete)."""
        if messages and messages[0].get("role") == "system":
            self.messages = list(messages)
        else:
            self.messages = [self.messages[0]] + list(messages)

    def _save(self) -> None:
        try:
            session_store.save_session(self.session_id, self.messages, self.config.model)
        except Exception:  # noqa: BLE001 — la persistance ne doit jamais crasher
            pass

    def send(self, user_input: str) -> None:
        # Nouvelle requete : on repart d'un drapeau d'interruption propre.
        self.cancel_event.clear()
        self.messages.append({"role": "user", "content": user_input})
        try:
            self._run_turn()
        finally:
            self._save()

    def _run_turn(self) -> None:
        # Boucle tant que le modele demande des outils.
        while True:
            if self.cancel_event.is_set():
                ui.print_info("(interrompu)")
                return
            # Choix des outils selon le mode courant.
            if self.mode == "plan":
                tools = READONLY_TOOLS_SCHEMA
                req_messages = self.messages + [{"role": "system", "content": PLAN_HINT}]
            else:
                tools = self.brain_tools
                req_messages = self.messages

            ui.assistant_prefix()
            printed_any = {"v": False}

            def on_text(chunk: str) -> None:
                printed_any["v"] = True
                ui.print_stream_chunk(chunk)

            try:
                message = self.client.stream_chat(
                    req_messages,
                    tools=tools,
                    on_text=on_text,
                    on_notice=ui.print_info,
                    cancel_event=self.cancel_event,
                )
            except LLMCancelled:
                ui.console.print()
                ui.print_info("(interrompu)")
                return
            except LLMError as exc:
                ui.console.print()
                ui.print_error(str(exc))
                return

            if printed_any["v"]:
                ui.console.print()  # retour a la ligne apres le stream

            self.messages.append(message)

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                return  # Reponse finale, on rend la main a l'utilisateur.

            for call in tool_calls:
                if self.cancel_event.is_set():
                    ui.print_info("(interrompu)")
                    return
                self._execute_tool(call)

    def _execute_tool(self, call: dict[str, Any]) -> None:
        fn = call.get("function", {})
        name = fn.get("name", "")
        raw_args = fn.get("arguments", "") or "{}"
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            args = {}

        ui.print_tool_call(name, args)

        # Delegation au codeur (orchestrateur).
        if name == "deleguer_codeur":
            if self.coder is None:
                self._append_tool_result(call, "[erreur] Codeur non configure.")
                return
            if self.mode == "plan":
                self._append_tool_result(
                    call,
                    "[mode plan] Delegation desactivee. Presente ton plan ; "
                    "l'utilisateur passera en mode normal/auto pour l'executer.",
                )
                return
            task = args.get("tache", "")
            files = args.get("fichiers", []) or []
            result = self.coder.implement(task, files, auto_apply=(self.mode == "auto"))
            ui.print_tool_result("deleguer_codeur", result)
            self._append_tool_result(call, result)
            return

        impl = TOOL_IMPLS.get(name)
        if impl is None:
            result = f"[erreur] Outil inconnu : {name}"
            self._append_tool_result(call, result)
            return

        # Mode plan : aucune action destructive autorisee.
        if name in DESTRUCTIVE_TOOLS and self.mode == "plan":
            self._append_tool_result(
                call,
                "[mode plan] Action bloquee. Presente d'abord ton plan ; "
                "l'utilisateur passera en mode normal/auto pour l'executer.",
            )
            return

        # Confirmation pour les actions sensibles (sauf mode auto).
        if name in DESTRUCTIVE_TOOLS and self.mode != "auto":
            if not ui.confirm(f"Autoriser {name} ?"):
                self._append_tool_result(call, "[refuse] L'utilisateur a refuse cette action.")
                return

        try:
            result = impl(**args)
        except Exception as exc:  # noqa: BLE001 — on renvoie l'erreur au modele
            result = f"[erreur] {type(exc).__name__}: {exc}"

        ui.print_tool_result(name, result)
        self._append_tool_result(call, result)

    def _append_tool_result(self, call: dict[str, Any], result: str) -> None:
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": result,
            }
        )
