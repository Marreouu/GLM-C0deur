"""Interface plein ecran facon Claude Code.

Le transcript (reponses de l'IA, appels d'outils) defile en haut ; la barre de
saisie et la ligne de mode restent epinglees en bas. La sortie riche (couleurs)
est rendue par rich dans un buffer, puis affichee en ANSI dans une fenetre
scrollable de prompt_toolkit.
"""

from __future__ import annotations

import io
import random
import shutil
import threading
import time

# Frames du spinner d'activite.
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
# Scintillement de l'icone (facon Claude Code).
_SPARKLES = "✳✢✶✻✽✻✶✢"
# Verbes rigolos affiches pendant le traitement (un tire au sort par requete).
_WORK_VERBS = [
    "Cogitation", "Mijotage", "Concoction", "Gribouillage", "Tricotage",
    "Ratatouillage", "Elucubration", "Bidouillage", "Petrissage", "Maciration",
    "Reflexion", "Tambouille", "Ruminations", "Popotage", "Fricotage",
]
# Phrases d'etat selon le temps ecoule.
_WORK_PHRASES = [
    (0, "reflechit"),
    (8, "reflechit encore"),
    (20, "y travaille"),
    (40, "presque fini"),
]

from prompt_toolkit.application import Application
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import ANSI, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from rich.console import Console

from . import session as session_store
from . import ui
from .agent import MODE_LABELS
from .client import LLMClient
from .skills import Skill, compose_prompt


class _ScrollWindow(Window):
    """Fenetre du transcript qui reagit a la molette de la souris.

    prompt_toolkit route les evenements souris vers cette fenetre ; on capte
    SCROLL_UP/SCROLL_DOWN pour deleguer au callback (qui coupe aussi le suivi
    automatique du bas, sinon le rendu suivant recolle le defilement en bas).
    """

    def __init__(self, *args, on_scroll=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_scroll = on_scroll

    def _mouse_handler(self, mouse_event):
        if self._on_scroll is not None:
            if mouse_event.event_type == MouseEventType.SCROLL_UP:
                self._on_scroll(-1)
                return None
            if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self._on_scroll(1)
                return None
        return super()._mouse_handler(mouse_event)

# Commandes integrees (nom, description) pour l'autocompletion.
_BUILTIN_COMMANDS = [
    ("help", "affiche l'aide"),
    ("skills", "liste les skills disponibles"),
    ("mode", "change de mode (normal/auto/plan)"),
    ("model", "change le modele"),
    ("reset", "efface l'historique"),
    ("clear", "efface l'ecran"),
    ("session", "affiche l'ID de session (pour la reprise)"),
    ("sessions", "liste les sessions enregistrees"),
    ("resume", "reprend une session : /resume <id>"),
    ("exit", "quitter"),
]


class _SlashCompleter(Completer):
    """Autocompletion des commandes et skills quand la ligne commence par '/'."""

    def __init__(self, entries):
        # entries : liste de (nom, description)
        self.entries = entries

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/") or " " in text:
            return
        word = text[1:].lower()
        for name, desc in self.entries:
            if name.lower().startswith(word):
                yield Completion(
                    f"/{name}",
                    start_position=-len(text),
                    display=f"/{name}",
                    display_meta=desc,
                )

_STYLE = Style.from_dict(
    {
        "sep": ui.DIM2,
        "prompt": f"{ui.BLUE} bold",
        "status": ui.DIM,
        "status.mode": f"{ui.BG}",
        "queued": f"bg:{ui.BAR} {ui.YELLOW}",
        # Menu d'autocompletion (facon Claude Code).
        "completion-menu": f"bg:{ui.BAR} {ui.FG}",
        "completion-menu.completion": f"bg:{ui.BAR} {ui.FG}",
        "completion-menu.completion.current": f"bg:{ui.BLUE} {ui.BG} bold",
        "completion-menu.meta.completion": f"bg:{ui.BAR} {ui.DIM}",
        "completion-menu.meta.completion.current": f"bg:{ui.BLUE} {ui.BG}",
        "scrollbar.background": f"bg:{ui.BAR}",
        "scrollbar.button": f"bg:{ui.DIM2}",
    }
)


class TUI:
    def __init__(self, agent, subtitle: str = "", skills: dict[str, Skill] | None = None):
        self.agent = agent
        self.subtitle = subtitle
        self.skills = skills or {}

        # Buffer de sortie : rich ecrit dedans, la fenetre du haut l'affiche.
        cols = shutil.get_terminal_size((100, 30)).columns
        self.buffer_io = io.StringIO()
        self._rich = Console(
            file=self.buffer_io,
            force_terminal=True,
            color_system="truecolor",
            width=max(40, cols - 1),
            soft_wrap=False,
        )
        ui.set_console(self._rich)
        ui.set_confirm_handler(self._confirm)

        self._busy = False
        self._lock = threading.Lock()
        # File : chaque element = (prompt_a_envoyer, markup_a_afficher, label_court)
        self._queue: list[tuple[str, str, str]] = []
        self._work_start = 0.0        # debut du traitement courant
        self._work_verb = ""          # verbe rigolo courant
        self._awaiting_confirm = False
        self._confirm_event = threading.Event()
        self._confirm_result = False
        self._last_ctrl_c = 0.0     # horodatage du dernier Ctrl+C (double = quitter)

        # Etat du defilement du transcript.
        self._last_text = ""      # derniere version affichee (evite la race)
        self._follow = True       # True = colle en bas ; False = defilement manuel
        self._transcript_window = None

        self._build_app()

    # ─── Rendu du transcript ────────────────────────────────────────────
    def _transcript(self) -> ANSI:
        # On memorise le texte affiche pour un calcul de curseur coherent.
        self._last_text = self.buffer_io.getvalue()
        w = self._transcript_window
        # En mode suivi : on colle le defilement tout en bas a chaque rendu.
        if self._follow and w is not None and w.render_info is not None:
            total_rows = self._last_text.count("\n") + 1
            w.vertical_scroll = max(0, total_rows - w.render_info.window_height)
        return ANSI(self._last_text)

    def _cursor(self) -> Point:
        # Curseur sur la premiere ligne visible : n'impose aucun re-defilement,
        # ce qui laisse notre `vertical_scroll` manuel tel quel.
        w = self._transcript_window
        if w is not None and w.render_info is not None:
            y = w.vertical_scroll
        else:
            y = self._last_text.count("\n")
        return Point(x=0, y=y)

    def _scroll_lines(self, direction: int, step: int) -> None:
        """Defile de `step` lignes (direction -1 = haut, +1 = bas)."""
        w = self._transcript_window
        if w is None or w.render_info is None:
            return
        height = w.render_info.window_height
        total_rows = self._last_text.count("\n") + 1
        max_scroll = max(0, total_rows - height)
        new = max(0, min(w.vertical_scroll + direction * step, max_scroll))
        w.vertical_scroll = new
        self._follow = new >= max_scroll  # revenu tout en bas -> reprend le suivi
        if self.app:
            self.app.invalidate()

    def _scroll_by(self, direction: int) -> None:
        """Defile d'une page (direction -1 = haut, +1 = bas)."""
        w = self._transcript_window
        if w is None or w.render_info is None:
            return
        self._scroll_lines(direction, max(1, w.render_info.window_height - 2))

    def _status(self) -> HTML:
        mode = self.agent.mode
        color, label = ui._MODE_STYLE.get(mode, (ui.FG, mode.upper()))
        chip = f"<style bg='{color}' fg='{ui.BG}'><b> {label} </b></style>"
        reqs = f"  <style fg='{ui.CYAN}'>⇅ {LLMClient.request_count} req</style>"
        if self._awaiting_confirm:
            tail = f"  <style fg='{ui.YELLOW}'>o/N puis Entree</style>"
        elif self._busy:
            spark = _SPARKLES[int(time.time() * 6) % len(_SPARKLES)]
            elapsed = int(time.time() - self._work_start)
            mm, ss = divmod(elapsed, 60)
            tstr = f"{mm}m {ss:02d}s" if mm else f"{ss}s"
            phrase = _WORK_PHRASES[0][1]
            for sec, ph in _WORK_PHRASES:
                if elapsed >= sec:
                    phrase = ph
            queued = f" · +{len(self._queue)} en file" if self._queue else ""
            tail = (
                f"  <style fg='{ui.YELLOW}'>{spark} {self._work_verb}… "
                f"({tstr} · {phrase}{queued})</style>"
                f"  <style fg='{ui.DIM2}'>ctrl+c interrompt</style>"
            )
        elif not self._follow:
            tail = f"  <style fg='{ui.YELLOW}'>defilement · ctrl+fin pour revenir en bas</style>"
        else:
            tail = (
                f"  <style fg='{ui.DIM2}'>shift+tab mode · molette/pgup defiler · "
                f"ctrl+c annule</style>"
            )
        # Mettre à jour dynamiquement le subtitle avec le modèle du codeur
        if hasattr(self.agent, 'coder') and self.agent.coder:
            coder_model = self.agent.coder.current_model
            sub = f"  <style fg='{ui.BLUE}'>{self.agent.config.model} + {coder_model}</style>"
        else:
            sub = f"  <style fg='{ui.BLUE}'>{self.subtitle}</style>" if self.subtitle else ""
        return HTML(f"⏵⏵ {chip}{sub}{reqs}{tail}")

    def _queue_text(self):
        # Messages en attente, epingles au-dessus de la saisie.
        out = []
        for _, _, label in self._queue[:6]:
            out.append(("class:queued", f"⏳ {label}\n"))
        if len(self._queue) > 6:
            out.append(("class:queued", f"   … +{len(self._queue) - 6} autres\n"))
        return out

    # ─── Construction de l'app ──────────────────────────────────────────
    def _build_app(self) -> None:
        # wrap_lines=False : rich a deja replie le texte a la largeur, donc
        # 1 ligne de contenu = 1 ligne d'ecran -> defilement exact.
        self._transcript_window = _ScrollWindow(
            content=FormattedTextControl(
                text=self._transcript,
                get_cursor_position=self._cursor,
                focusable=False,
                show_cursor=False,
            ),
            wrap_lines=False,
            on_scroll=lambda direction: self._scroll_lines(direction, 3),
        )
        transcript = self._transcript_window

        completer = _SlashCompleter(
            _BUILTIN_COMMANDS + [(s.name, s.description) for s in self.skills.values()]
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

        self._root = FloatContainer(
            content=HSplit(
                [
                    transcript,
                    queue_win,
                    Window(height=1, char="─", style="class:sep"),
                    self.input,
                    Window(height=1, char="─", style="class:sep"),
                    status,
                ]
            ),
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

    def _create_app(self) -> None:
        self.app = Application(
            layout=Layout(self._root, focused_element=self.input),
            key_bindings=self._kb,
            style=_STYLE,
            full_screen=True,
            mouse_support=True,
            refresh_interval=0.1,
        )

    def _on_ctrl_c(self, event) -> None:
        """Ctrl+C annule l'action courante ; ne quitte qu'au 2e appui a vide."""
        # 1. Confirmation en attente -> equivaut a repondre "non".
        if self._awaiting_confirm:
            self._confirm_result = False
            self._awaiting_confirm = False
            self._confirm_event.set()
            self._rich.print(f"[{ui.DIM}](action annulee)[/]")
            event.app.invalidate()
            return
        # 2. Requete en cours ou file d'attente -> on interrompt tout.
        if self._busy or self._queue:
            with self._lock:
                self._queue.clear()
            self.agent.cancel_event.set()
            self._rich.print(f"[{ui.YELLOW}](interruption…)[/]")
            event.app.invalidate()
            return
        # 3. Au repos avec du texte saisi -> on vide simplement la ligne.
        if self.input.text:
            self.input.text = ""
            event.app.invalidate()
            return
        # 4. Au repos, ligne vide -> double Ctrl+C rapproche pour quitter.
        now = time.time()
        if now - self._last_ctrl_c < 2:
            event.app.exit()
            return
        self._last_ctrl_c = now
        self._rich.print(
            f"[{ui.DIM2}](appuie encore sur Ctrl+C pour quitter, ou Ctrl+D)[/]"
        )
        event.app.invalidate()

    # ─── Entrees utilisateur ────────────────────────────────────────────
    def _accept(self, buff) -> bool:
        text = buff.text.strip()
        if not text:
            return False

        # Reponse a une demande de confirmation en attente.
        if self._awaiting_confirm:
            self._confirm_result = text.lower() in ("o", "oui", "y", "yes")
            self._awaiting_confirm = False
            self._confirm_event.set()
            return False

        # Les commandes slash s'executent tout de suite (sauf si occupe : file).
        if text.startswith("/") and not self._busy:
            self._handle_slash(text)
            return False

        self._submit(text, f"\n[bold {ui.BLUE}]>[/] {text}", text)
        return False

    def _submit(self, prompt_text: str, display: str, label: str) -> None:
        """Empile un message ; demarre le consommateur s'il ne tourne pas.

        Le message n'est affiche dans le transcript qu'au moment ou il est
        reellement traite. En attendant, il reste visible dans la zone epinglee.
        """
        start = False
        with self._lock:
            self._queue.append((prompt_text, display, label))
            if not self._busy:
                self._busy = True
                start = True
        if start:
            threading.Thread(target=self._worker, daemon=True).start()
        if self.app:
            self.app.invalidate()

    def _worker(self) -> None:
        while True:
            with self._lock:
                if self._queue:
                    prompt_text, display, _ = self._queue.pop(0)
                else:
                    self._busy = False
                    prompt_text = None
            if prompt_text is None:
                break
            self._work_start = time.time()
            self._work_verb = random.choice(_WORK_VERBS)
            self._rich.print(display)  # apparait quand le traitement demarre
            if self.app:
                self.app.invalidate()
            try:
                self.agent.send(prompt_text)
            except Exception as exc:  # noqa: BLE001
                self._rich.print(f"[bold {ui.RED}]Erreur : {exc}[/]")
        if self.app:
            self.app.invalidate()

    def _confirm(self, question: str) -> bool:
        self._confirm_result = False
        self._confirm_event.clear()
        self._awaiting_confirm = True
        self.app.invalidate()
        self._confirm_event.wait()
        return self._confirm_result

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
        elif name == "/reset":
            self.agent.reset()
            self._rich.print(f"[{ui.DIM}]Historique efface.[/]")
        elif name == "/clear":
            self.buffer_io.seek(0)
            self.buffer_io.truncate(0)
        elif name == "/skills":
            self._list_skills()
        elif name == "/session":
            self._rich.print(
                f"[{ui.DIM}]Session courante :[/] [bold {ui.CYAN}]{self.agent.session_id}[/]"
                f"  [{ui.DIM2}](reprise : glm --resume {self.agent.session_id})[/]"
            )
        elif name == "/sessions":
            self._list_sessions()
        elif name == "/resume":
            self._resume_session(arg)
        elif name == "/mode":
            from .agent import MODES

            if arg in MODES:
                self.agent.mode = arg
            else:
                self.agent.cycle_mode()
            self._rich.print(f"[{ui.DIM}]Mode : {MODE_LABELS[self.agent.mode]}[/]")
        elif name[1:] in self.skills:
            self._run_skill(self.skills[name[1:]], arg)
        else:
            self._rich.print(f"[{ui.DIM2}]Commande inconnue : {name} (voir /skills)[/]")

    def _list_skills(self) -> None:
        if not self.skills:
            self._rich.print(f"[{ui.DIM}]Aucun skill. Ajoute des .md dans ./skills/[/]")
            return
        self._rich.print(f"\n[bold {ui.PURPLE}]✦ Skills disponibles[/]")
        for skill in self.skills.values():
            self._rich.print(
                f"  [bold {ui.CYAN}]/{skill.name}[/]  [{ui.DIM}]{skill.description}[/]"
                f"  [{ui.DIM2}]({skill.source})[/]"
            )

    def _list_sessions(self) -> None:
        from datetime import datetime

        rows = session_store.list_sessions()
        if not rows:
            self._rich.print(f"[{ui.DIM}]Aucune session enregistree.[/]")
            return
        self._rich.print(f"\n[bold {ui.PURPLE}]✦ Sessions enregistrees[/]")
        for r in rows[:20]:
            when = datetime.fromtimestamp(r["updated"]).strftime("%d/%m %H:%M")
            here = "  ← courante" if r["id"] == self.agent.session_id else ""
            self._rich.print(
                f"  [bold {ui.CYAN}]{r['id']}[/]  [{ui.DIM}]{when}[/]  "
                f"[{ui.DIM2}]{r['turns']} tours[/]  {r['title']}"
                f"[{ui.GREEN}]{here}[/]"
            )
        self._rich.print(f"[{ui.DIM2}]Reprends avec /resume <id>[/]")

    def _resume_session(self, arg: str) -> None:
        target = arg.strip() or (session_store.latest_session_id() or "")
        data = session_store.load_session(target) if target else None
        if data is None:
            self._rich.print(f"[{ui.RED}]Session introuvable : {arg or '(aucune)'}[/]")
            return
        self.agent.session_id = data.get("id", target)
        self.agent.load_history(data.get("messages", []))
        # On repart d'un transcript propre puis on rejoue l'echange.
        self.buffer_io.seek(0)
        self.buffer_io.truncate(0)
        self._replay_history()

    def _replay_history(self) -> None:
        """Reaffiche les tours user/assistant d'une session reprise."""
        msgs = self.agent.messages
        turns = sum(1 for m in msgs if m.get("role") == "user")
        self._rich.print(
            f"[{ui.DIM}]— session [bold {ui.CYAN}]{self.agent.session_id}[/] "
            f"reprise · {turns} tours —[/]"
        )
        for m in msgs[1:]:
            role = m.get("role")
            content = (m.get("content") or "").strip()
            if role == "user":
                self._rich.print(f"\n[bold {ui.BLUE}]>[/] {content}")
            elif role == "assistant" and content:
                self._rich.print(content)
        self._rich.print(f"[{ui.DIM2}]— fin de la reprise —[/]\n")

    def _run_skill(self, skill: Skill, arg: str) -> None:
        display = (
            f"\n[bold {ui.PURPLE}]✦ skill /{skill.name}[/] "
            f"[{ui.DIM}]{skill.description}[/]"
        )
        label = f"/{skill.name} {arg}".strip()
        self._submit(compose_prompt(skill, arg), display, label)

    def run(self) -> None:
        self._create_app()
        ui.print_banner(self.agent.config)
        # Reprise : si l'historique contient deja des echanges, on les rejoue.
        if len(self.agent.messages) > 1:
            self._replay_history()
        else:
            self._rich.print(
                f"[{ui.DIM2}]session [bold {ui.CYAN}]{self.agent.session_id}[/] "
                f"· reprise possible avec /resume ou glmcode --resume {self.agent.session_id}[/]"
            )
        self.app.run()
