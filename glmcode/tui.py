"""Interface plein ecran (barre epinglee en bas), inspiree de Claude Code.

Le transcript (banner, reponses de l'assistant, appels d'outils...) s'affiche
directement dans le terminal via la console rich habituelle (voir ui.py) ; ce
module se charge uniquement de la zone du bas, epinglee, qui reste visible :
la file d'attente des messages, la ligne de saisie et la barre de statut.
patch_stdout() permet aux impressions faites depuis le thread de l'agent de
s'inserer proprement au-dessus de cette zone pendant qu'une requete tourne.
"""

from __future__ import annotations

import os
import re
import threading
import time

from prompt_toolkit import Application
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.containers import Float, FloatContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from rich.markup import escape

from . import ui
from .cli import HELP_TEXT, _handle_slash  # reutilise la logique des commandes /
from .motd import get_motd_manager
from .runtime import runtime_manager, get_watch_manager
from .ui import BAR, BLUE, DIM, DIM2, FG, BG, FileMentionCompleter, _MODE_STYLE, _IGNORE_DIRS

# Commandes integrees proposees par l'autocompletion '/'.
_BUILTIN_COMMANDS = [
    ("/help", "Affiche l'aide"),
    ("/reset", "Efface l'historique de la conversation"),
    ("/model", "Change le modele courant"),
    ("/mode", "Change de mode (normal / auto / plan)"),
    ("/skills", "Liste les skills disponibles"),
    ("/session", "Affiche l'ID de la session courante"),
    ("/sessions", "Liste les sessions enregistrees"),
    ("/resume", "Reprend une session (derniere si aucun id)"),
    ("/ping", "Teste la connexion au backend"),
    ("/update", "Verifie et installe les mises a jour"),
    ("/check-update", "Verifie uniquement les mises a jour disponibles"),
    ("/version", "Affiche les informations de version"),
    ("/exit", "Quitte"),
]

_MAX_MENTION_CHARS = 20_000  # garde-fou : evite d'engloutir tout le contexte


class _MentionCompleter(Completer):
    """Combine l'autocompletion des commandes '/' et des fichiers '@'."""

    def __init__(self, commands: list[tuple[str, str]], base_dir: str = "."):
        self._commands = commands
        self._files = FileMentionCompleter(base_dir)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/") and " " not in text:
            needle = text[1:].lower()
            for name, desc in self._commands:
                if name[1:].lower().startswith(needle):
                    yield Completion(
                        name,
                        start_position=-len(text),
                        display=name,
                        display_meta=desc,
                    )
            return
        yield from self._files.get_completions(document, complete_event)


class TUI:
    """Interface plein ecran avec barre epinglee (saisie + statut) en bas."""

    def __init__(self, agent, subtitle: str = "", skills: dict | None = None) -> None:
        self.agent = agent
        self.subtitle = subtitle
        self.skills = skills or {}

        self._queue: list[str] = []
        self._busy = False
        self._req_count = 0
        self._ctrl_c_pending = False
        self._follow = True
        self._exit_requested = False

        # Surveillance de fichiers en arriere-plan : reveille l'agent quand un
        # fichier change en dehors de l'assistant (edition manuelle, outil
        # externe, etc.). `_watch_mute_until` empeche que les propres ecritures
        # de l'agent ne se re-declenchent elles-memes juste apres un tour.
        self._watch_id: str | None = None
        self._watch_mute_until = 0.0
        self._watch_mute_seconds = 3.0
        self._motd_manager = None

        self.input: TextArea
        self.app: Application | None = None
        self._build_app()

    # ─── Construction de l'app ──────────────────────────────────────────
    def _build_app(self) -> None:
        completer = _MentionCompleter(
            _BUILTIN_COMMANDS + [(f"/{s.name}", s.description) for s in self.skills.values()]
        )
        self.input = TextArea(
            height=1,
            multiline=False,
            wrap_lines=False,
            prompt=[("class:prompt", "> ")],
            accept_handler=self._accept,
            completer=completer,
            complete_while_typing=True,
        )

        status = Window(content=FormattedTextControl(self._status), height=1)

        # Zone epinglee des messages en attente (hauteur 0 si file vide).
        queue_win = Window(
            content=FormattedTextControl(self._queue_text),
            height=lambda: min(len(self._queue), 7),
            style="class:queued",
        )

        # Zone principale (colonne unique) : queue, input, status.
        main_column = HSplit(
            [
                queue_win,
                Window(height=1, char="─", style="class:sep"),
                self.input,
                Window(height=1, char="─", style="class:sep"),
                status,
            ]
        )

        self._root = FloatContainer(
            content=main_column,
            floats=[
                # Menu d'autocompletion (au-dessus de la saisie).
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=12, scroll_offset=1),
                )
            ],
        )

        self._kb = KeyBindings()

        @self._kb.add("s-tab")
        def _(event):
            self.agent.cycle_mode()
            event.app.invalidate()

        @self._kb.add("c-c")
        def _(event):
            self._on_ctrl_c(event)

        @self._kb.add("c-d")
        def _(event):
            event.app.exit()

        # Defilement de l'historique (eager = prioritaire sur la zone de saisie).
        # Le transcript vit desormais dans le scrollback natif du terminal ; ces
        # raccourcis sont conserves pour compatibilite mais n'agissent plus sur
        # un buffer interne.
        @self._kb.add("pageup", eager=True)
        @self._kb.add("c-up", eager=True)
        def _(event):
            self._scroll_by(-1)

        @self._kb.add("pagedown", eager=True)
        @self._kb.add("c-down", eager=True)
        def _(event):
            self._scroll_by(1)

        @self._kb.add("c-end", eager=True)
        def _(event):
            self._follow = True
            event.app.invalidate()

        self.app = None  # cree dans run() : Application() exige une vraie console.

    # ─── Contenu dynamique ──────────────────────────────────────────────
    def _status(self):
        color, label = _MODE_STYLE.get(self.agent.mode, (FG, self.agent.mode.upper()))
        return [
            (f"bg:{color} fg:{BG} bold", f" {label} "),
            ("", "  "),
            (f"fg:{FG}", self.subtitle),
            ("", "   "),
            (f"fg:{DIM}", f"⇅{self._req_count} req"),
            ("", "   "),
            (
                f"fg:{DIM2}",
                "shift+tab mode · @ fichier · molette/pgup defiler · ctrl+c annule",
            ),
        ]

    def _queue_text(self):
        if not self._queue:
            return ""
        lines: list[tuple[str, str]] = []
        for i, item in enumerate(self._queue, 1):
            preview = item if len(item) <= 80 else item[:77] + "…"
            lines.append((f"fg:{DIM}", f"  {i}. {preview}\n"))
        return lines

    def _scroll_by(self, direction: int) -> None:
        self._follow = direction >= 0

    # ─── Style prompt_toolkit ───────────────────────────────────────────
    @staticmethod
    def _style() -> Style:
        return Style.from_dict(
            {
                "prompt": f"bold {BLUE}",
                "sep": DIM2,
                "queued": DIM,
                "completion-menu": f"bg:{BAR} fg:{FG}",
                "completion-menu.completion": f"bg:{BAR} fg:{FG}",
                "completion-menu.completion.current": f"bg:{BLUE} fg:{BG} bold",
                "completion-menu.meta.completion": f"bg:{BAR} fg:{DIM}",
                "completion-menu.meta.completion.current": f"bg:{BLUE} fg:{BG}",
            }
        )

    # ─── Saisie / envoi ─────────────────────────────────────────────────
    def _accept(self, buf) -> bool:
        text = buf.text.strip()
        if not text:
            return False
        if self._busy:
            self._queue.append(text)
        else:
            self._dispatch(text)
        return False  # vide la ligne de saisie

    def _dispatch(self, text: str) -> None:
        self._busy = True
        if self.app is not None:
            self.app.invalidate()
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, text: str) -> None:
        try:
            self._run_one(text)
        except Exception as exc:  # noqa: BLE001 — ne jamais planter l'app pour une erreur agent
            ui.print_error(f"Erreur : {exc}")
        finally:
            self._req_count += 1
            self._busy = False
            # Les ecritures que ce tour vient de faire ne doivent pas se
            # re-declencher elles-memes via la surveillance de fichiers.
            self._watch_mute_until = time.monotonic() + self._watch_mute_seconds
            if self._exit_requested:
                if self.app is not None:
                    self.app.exit()
            if self._queue:
                nxt = self._queue.pop(0)
                self._dispatch(nxt)
            elif self.app is not None:
                self.app.invalidate()

    def _run_one(self, text: str) -> None:
        ui.console.print()
        ui.console.print(f"[bold {BLUE}]❯[/] {escape(text)}")
        if text.startswith("/"):
            cont = _handle_slash(text, self.agent, self.skills)
            if not cont:
                self._exit_requested = True
        else:
            self.agent.send(self._expand_mentions(text))

    def _expand_mentions(self, text: str) -> str:
        """Joint le contenu des fichiers references par '@chemin' au message envoye."""
        extras = []
        for match in re.finditer(r"(?<!\S)@(\S+)", text):
            path = match.group(1)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError:
                continue
            if len(content) > _MAX_MENTION_CHARS:
                content = content[:_MAX_MENTION_CHARS] + "\n... (tronque)"
            extras.append(f"\n\n--- Fichier joint : {path} ---\n{content}")
        return text + "".join(extras) if extras else text

    def _on_ctrl_c(self, event) -> None:
        if self._busy:
            self.agent.cancel_event.set()
            ui.print_info("Interruption demandee (Ctrl+C)...")
            return
        if self._ctrl_c_pending:
            event.app.exit()
            return
        self._ctrl_c_pending = True
        ui.print_info("Ctrl+C a nouveau pour quitter.")

        def _reset() -> None:
            self._ctrl_c_pending = False

        threading.Timer(2.0, _reset).start()

    # ─── Surveillance de fichiers (reveil automatique de l'agent) ───────
    def _start_watch(self) -> None:
        cfg = getattr(self.agent, "config", None)
        runtime_cfg = getattr(cfg, "runtime", None)
        if runtime_cfg is not None and not runtime_cfg.enabled:
            return
        delay = getattr(runtime_cfg, "file_watch_delay", 2.0)
        try:
            runtime_manager.initialize()
            ok = get_watch_manager().watch_directory(
                ".",
                callback=self._on_fs_change,
                ignore_dirs=_IGNORE_DIRS,
                poll_delay=delay,
            )
            if ok:
                self._watch_id = "dir:."
        except Exception as exc:  # noqa: BLE001 — la surveillance ne doit jamais bloquer le demarrage
            ui.print_info(f"(surveillance fichiers indisponible : {exc})")

    def _stop_watch(self) -> None:
        if self._watch_id is None:
            return
        try:
            get_watch_manager().unwatch(self._watch_id)
        except Exception:  # noqa: BLE001
            pass
        try:
            runtime_manager.shutdown()
        except Exception:  # noqa: BLE001
            pass

    def _on_fs_change(self, info: dict) -> None:
        # Appele depuis le thread de surveillance : jamais pendant un tour
        # de l'agent (evite de reagir a ses propres ecritures en cours), et
        # pas juste apres non plus (fenetre de mute).
        if self._busy or time.monotonic() < self._watch_mute_until:
            return
        changed = list(info.get("modified", [])) + list(info.get("added", []))
        if not changed:
            return
        preview = ", ".join(changed[:5])
        if len(changed) > 5:
            preview += f", … (+{len(changed) - 5})"
        prompt = (
            "[surveillance fichiers] Modification detectee en dehors de "
            f"l'assistant : {preview}. Verifie ce qui a change et agis si necessaire."
        )
        # A ce stade self._busy est deja False (verifie plus haut) : on peut
        # declencher directement un nouveau tour.
        self._dispatch(prompt)

    # ─── Lancement ───────────────────────────────────────────────────────
    def run(self) -> None:
        self._motd_manager = get_motd_manager()
        self._motd_manager.start_background_updates()
        ui.print_banner(self.agent.config, motd_panel=self._motd_manager.render_motd())
        ui.console.print(
            f"[{DIM}]session {self.agent.session_id} · reprise possible avec "
            f"/resume ou glmcode --resume {self.agent.session_id}[/]"
        )

        self.app = Application(
            layout=Layout(self._root, focused_element=self.input),
            key_bindings=self._kb,
            style=self._style(),
            full_screen=False,
            mouse_support=False,
        )

        from rich.console import Console

        ui.set_console(
            Console(
                force_terminal=True,
                legacy_windows=False
            )
        )

        self._start_watch()

        try:
            self.app.run()
        finally:
            ui.reset_console()
            self._stop_watch()

        if self._motd_manager is not None:
            self._motd_manager.stop_background_updates()