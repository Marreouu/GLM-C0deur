"""Interface terminal soignee (rich + prompt_toolkit), inspiree de Claude Code."""

from __future__ import annotations

from prompt_toolkit import PromptSession
from . import __version__
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
        rows = Text.assemble(
            ("cerveau  ", f"bold {BLUE}"),
            (f"{cfg.model}", FG),
            ("  ·  API Z.ai\n", DIM),
            ("codeur   ", f"bold {CYAN}"),
            (f"{cfg.coder.model}", FG),
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


# ─── Saisie ─────────────────────────────────────────────────────────────
def build_session(get_mode, cycle_mode, subtitle: str = "") -> PromptSession | None:
    """Session de saisie avec Shift+Tab (changement de mode).

    Le mode s'affiche a droite de la saisie (rprompt) et se met a jour en direct.
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
        hint = f"   <style fg='{DIM2}'>⇧⇥ mode · /help</style>"
        return HTML(chip + mid + hint)

    try:
        return PromptSession(
            key_bindings=kb, bottom_toolbar=bottom_toolbar, style=_PT_STYLE
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
