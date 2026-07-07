"""Interface terminal soignee (rich + prompt_toolkit), inspiree de Claude Code."""

from __future__ import annotations

import os

from prompt_toolkit import PromptSession
from . import __version__
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

console = Console()

# ─── Palette (Tokyo Night) ──────────────────────────────────────────────
BG = "#1a1b26"
FG = "#c0caf5"
BLUE = "#7aa2f7"
PURPLE = "#bb9af7"
CYAN = "#7dcfff"
GREEN = "#9ece6a"
YELLOW = "#e0af68"
RED = "#f7768e"
DIM = "#565f89"
DIM2 = "#414868"
BAR = "#24283b"

# Style prompt_toolkit (barre de statut sombre facon IDE).
_PT_STYLE = Style.from_dict(
    {
        "bottom-toolbar": f"noreverse bg:{BAR} fg:{DIM}",
        "completion-menu": f"bg:{BAR} fg:{FG}",
        "completion-menu.completion": f"bg:{BAR} fg:{FG}",
        "completion-menu.completion.current": f"bg:{BLUE} fg:{BG} bold",
        "completion-menu.meta.completion": f"bg:{BAR} fg:{DIM}",
        "completion-menu.meta.completion.current": f"bg:{BLUE} fg:{BG}",
        "motd": f"bg:{BAR} fg:{FG}",
    }
)

# (couleur pastille, libelle) par mode.
_MODE_STYLE = {
    "normal": (GREEN, "NORMAL"),
    "auto": (YELLOW, "AUTO"),
    "plan": (BLUE, "PLAN"),
}

BANNER_LINES = [
    r"  ____ _     __  __    ____          _      ",
    r" / ___| |   |  \/  |  / ___|___   __| | ___ ",
    r"| |  _| |   | |\/| | | |   / _ \ / _` |/ _ \ ",
    r"| |_| | |___| |  | | | |__| (_) | (_| |  __/ ",
    r" \____|_____|_|  |_|  \____\___/ \__,_|\___| ",
]
_BANNER_SHADES = [PURPLE, PURPLE, BLUE, CYAN, CYAN]


def print_banner(cfg) -> None:
    console.print()
    banner = Text()
    for line, shade in zip(BANNER_LINES, _BANNER_SHADES):
        banner.append(line + "\n", style=f"bold {shade}")
    console.print(banner)

    if getattr(cfg, "coder", None) is not None and cfg.coder.enabled:
        # Récupérer le modèle courant du codeur s'il est disponible
        coder_model = getattr(cfg.coder, 'current_model', cfg.coder.model)
        rows = Text.assemble(
            ("cerveau  ", f"bold {BLUE}"),
            (f"{cfg.model}", FG),
            ("  ·  API Z.ai\n", DIM),
            ("codeur   ", f"bold {CYAN}"),
            (f"{coder_model}", FG),
            ("  ·  API Openrouteur\n", DIM),
        )
    else:
        rows = Text.assemble(
            ("modele   ", f"bold {BLUE}"),
            (f"{cfg.model}", FG),
            ("  ·  API Z.ai\n", DIM),
        )
    rows.append_text(
        Text.assemble(
            ("\n", ""),
            ("/help", PURPLE),
            (" aide   ", DIM),
            ("@fichier", PURPLE),
            (" joindre   ", DIM),
            ("⇧⇥", PURPLE),
            (" changer de mode   ", DIM),
            ("/exit", PURPLE),
            (" quitter", DIM),
        )
    )
    console.print(
        Panel(
            rows,
            title=f"[bold]GLM Code - Version: {__version__}[/]",
            title_align="left",
            border_style=BLUE,
            padding=(1, 2),
            expand=False,
        )
    )


# ─── Fichiers du projet (pour l'autocompletion '@fichier') ──────────────
# Dossiers ignores lors du parcours (bruit habituel des projets Python/JS).
_IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".idea",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", ".eggs",
}


def list_files(base: str = ".", limit: int = 5000) -> list[str]:
    """Liste les fichiers sous `base`, pour l'autocompletion des mentions '@'.

    Ignore les dossiers caches et les repertoires habituels (venv, node_modules,
    .git...) afin de rester rapide meme sur de gros projets.
    """
    out: list[str] = []
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in _IGNORE_DIRS and not d.startswith("."))
        for f in sorted(files):
            if f.startswith("."):
                continue
            rel = os.path.relpath(os.path.join(root, f), base)
            out.append(rel.replace(os.sep, "/"))
            if len(out) >= limit:
                return out
    return out


class FileMentionCompleter(Completer):
    """Autocompletion des fichiers du projet quand l'utilisateur tape '@'.

    Facon Claude Code : '@' declenche la liste des fichiers ; en choisir un
    insere '@chemin/du/fichier' dans la ligne de saisie.
    """

    def __init__(self, base_dir: str = ".", cache_ttl: float = 5.0):
        self.base_dir = base_dir
        self.cache_ttl = cache_ttl
        self._cache: list[str] | None = None
        self._cache_time = 0.0

    def _files(self) -> list[str]:
        import time

        now = time.time()
        if self._cache is None or now - self._cache_time > self.cache_ttl:
            self._cache = list_files(self.base_dir)
            self._cache_time = now
        return self._cache

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        at_pos = text.rfind("@")
        if at_pos == -1:
            return
        # Le '@' doit demarrer un "mot" (debut de ligne ou precede d'un espace).
        if at_pos > 0 and not text[at_pos - 1].isspace():
            return
        partial = text[at_pos + 1:]
        if " " in partial:
            return  # la phrase continue apres le chemin : plus de completion

        needle = partial.lower()
        matches = [p for p in self._files() if needle in p.lower()]
        matches.sort(key=lambda p: (not p.lower().startswith(needle), len(p)))
        for path in matches[:30]:
            yield Completion(
                f"@{path}",
                start_position=-(len(text) - at_pos),
                display=f"@{path}",
                display_meta="fichier",
            )


# ─── Saisie ─────────────────────────────────────────────────────────────
def build_session(
    get_mode, cycle_mode, subtitle: str = "", base_dir: str = "."
) -> PromptSession | None:
    """Session de saisie avec Shift+Tab (changement de mode) et '@fichier'.

    Le mode s'affiche a droite de la saisie (rprompt) et se met a jour en direct.
    Taper '@' propose une autocompletion des fichiers du projet courant.
    Renvoie None si le terminal ne supporte pas prompt_toolkit (git bash, pipe).
    """
    kb = KeyBindings()

    @kb.add("s-tab")
    def _(event):
        cycle_mode()
        event.app.invalidate()

    def bottom_toolbar():
        mode = get_mode()
        color, label = _MODE_STYLE.get(mode, (FG, mode.upper()))
        chip = f"<style bg='{color}' fg='{BG}'><b>  {label}  </b></style>"
        mid = f"  <style fg='{BLUE}'>{subtitle}</style>" if subtitle else ""
        hint = f"   <style fg='{DIM2}'>⇧⇥ mode · @ fichier · /help</style>"
        return HTML(chip + mid + hint)

    try:
        return PromptSession(
            key_bindings=kb,
            bottom_toolbar=bottom_toolbar,
            style=_PT_STYLE,
            completer=FileMentionCompleter(base_dir),
            complete_while_typing=True,
        )
    except Exception:
        return None


def _rule() -> None:
    """Trait horizontal pleine largeur, discret."""
    console.print(f"[{DIM2}]" + "─" * console.width + "[/]")


def prompt_user(session: PromptSession | None = None) -> str:
    console.print()
    _rule()
    if session is None:
        return console.input(f"[bold {BLUE}]❯[/] ")
    return session.prompt(HTML(f"<style fg='{BLUE}'><b>❯</b></style> "))


# ─── Sortie assistant ───────────────────────────────────────────────────
def assistant_prefix() -> None:
    # Deux espaces : le glyphe ⏺ est rendu "large" par certains terminaux et se
    # collerait sinon au premier caractere du texte.
    console.print(f"[bold {PURPLE}]⏺[/]  ", end="")


def print_stream_chunk(text: str) -> None:
    console.print(text, end="", highlight=False, soft_wrap=True)


def print_coder_header(model: str) -> None:
    console.print(f"  [{DIM2}]⎿[/] [bold {CYAN}]codeur[/] [{DIM}]{escape(model)}[/]")


def print_coder_chunk(text: str) -> None:
    console.print(escape(text), end="", style=CYAN, highlight=False, soft_wrap=True)


# ─── Outils ─────────────────────────────────────────────────────────────
def print_tool_call(name: str, args: dict) -> None:
    detail = ", ".join(f"{k}={_short(v)}" for k, v in args.items())
    console.print(
        f"[bold {GREEN}]●[/] [bold {FG}]{escape(name)}[/][{DIM}]({escape(detail)})[/]"
    )


def print_tool_result(name: str, result: str) -> None:
    lines = result.splitlines() or ["(vide)"]
    shown = lines[:14]
    console.print(f"  [{DIM2}]⎿[/]  [{DIM}]{escape(shown[0])}[/]")
    for ln in shown[1:]:
        console.print(f"     [{DIM}]{escape(ln)}[/]")
    if len(lines) > 14:
        console.print(f"     [{DIM2}]… +{len(lines) - 14} lignes[/]")


def print_diff_preview(path: str, content: str, lang: str = "text") -> None:
    console.print(
        Panel(
            Syntax(content[:2000], lang, theme="monokai", word_wrap=True),
            title=f"[bold]{escape(path)}[/]",
            title_align="left",
            border_style=CYAN,
            padding=(0, 1),
        )
    )


# ─── Divers ─────────────────────────────────────────────────────────────
def print_error(msg: str) -> None:
    console.print(f"[bold {RED}]✗[/] [{RED}]{escape(msg)}[/]")


def print_info(msg: str) -> None:
    console.print(f"[{DIM}]{escape(msg)}[/]")


# Point d'accroche : en mode plein ecran (TUI), les confirmations passent par
# un gestionnaire dedie plutot que par console.input().
_confirm_handler = None


def set_confirm_handler(fn) -> None:
    global _confirm_handler
    _confirm_handler = fn


def confirm(question: str) -> bool:
    if _confirm_handler is not None:
        console.print(f"[bold {YELLOW}]?[/] [{FG}]{escape(question)}[/] [{DIM}][o/N][/]")
        return _confirm_handler(question)
    answer = console.input(f"[bold {YELLOW}]?[/] [{FG}]{escape(question)}[/] [{DIM}][o/N][/] ")
    return answer.strip().lower() in ("o", "oui", "y", "yes")


def set_console(new_console) -> None:
    """Redirige toute la sortie vers une autre Console (ex. buffer du TUI)."""
    global console
    console = new_console


def reset_console() -> None:
    """Restaure une Console standard (sortie terminal normale)."""
    global console
    console = Console()


def _short(value, limit: int = 60) -> str:
    text = str(value).replace("\n", "⏎")
    return text if len(text) <= limit else text[:limit] + "…"