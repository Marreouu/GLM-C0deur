"""Boucle interactive (REPL) et commandes slash."""

from __future__ import annotations

import os
import sys

from . import __version__, ui
from .agent import MODE_LABELS, MODES, Agent
from .client import LLMClient
from .config import Config, load_config
from .skills import compose_prompt, load_skills

HELP_TEXT = """[bold]Commandes[/]
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
et lancer des commandes (selon le mode)."""


def _handle_slash(cmd: str, agent: Agent, skills: dict) -> bool:
    """Retourne True s'il faut continuer la boucle, False pour quitter."""
    parts = cmd.strip().split(maxsplit=1)
    name = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if name in ("/exit", "/quit"):
        return False
    if name == "/help":
        ui.console.print(HELP_TEXT)
    elif name == "/skills":
        if not skills:
            ui.print_info("Aucun skill. Ajoute des .md dans ./skills/")
        else:
            for s in skills.values():
                ui.console.print(f"  [bold]/{s.name}[/]  {s.description}  ({s.source})")
    elif name[1:] in skills:
        agent.send(compose_prompt(skills[name[1:]], arg))
    elif name == "/reset":
        agent.reset()
        ui.print_info("Historique efface.")
    elif name == "/session":
        ui.print_info(
            f"Session : {agent.session_id}  (reprise : glmcode --resume {agent.session_id})"
        )
    elif name == "/sessions":
        _print_sessions()
    elif name == "/resume":
        from . import session as sess

        target = arg.strip() or (sess.latest_session_id() or "")
        data = sess.load_session(target) if target else None
        if data is None:
            ui.print_error(f"Session introuvable : {arg or '(aucune)'}")
        else:
            agent.session_id = data.get("id", target)
            agent.load_history(data.get("messages", []))
            ui.print_info(f"Session {agent.session_id} reprise.")
    elif name == "/model":
        if arg:
            agent.config.model = arg.strip()
            ui.print_info(f"Modele : {agent.config.model}")
        else:
            ui.print_info(f"Modele actuel : {agent.config.model}")
    elif name in ("/mode", "/auto"):
        if arg and arg.strip() in MODES:
            agent.mode = arg.strip()
        else:
            agent.cycle_mode()
        ui.print_info(f"Mode : {MODE_LABELS[agent.mode]}")
    elif name == "/ping":
        ok, msg = LLMClient(agent.config).ping()
        (ui.print_info if ok else ui.print_error)(
            f"Connexion OK · {msg}" if ok else f"Echec : {msg}"
        )
    else:
        ui.print_error(f"Commande inconnue : {name} (voir /help)")
    return True


def run(resume: str | None = None) -> int:
    try:
        cfg: Config = load_config()
    except Exception as exc:  # noqa: BLE001
        ui.print_error(f"Config invalide : {exc}")
        return 1

    if not cfg.api_key:
        ui.print_error(
            "Aucune cle API Z.ai trouvee.\n"
            "Cree un fichier config.toml (voir config.example.toml) ou definis "
            "la variable d'environnement GLMCODE_API_KEY."
        )
        return 1

    # Reprise eventuelle d'une session enregistree.
    history = None
    session_id = None
    if resume:
        from . import session as sess

        target = sess.latest_session_id() if resume == "__LATEST__" else resume
        data = sess.load_session(target) if target else None
        if data is None:
            ui.print_error(f"Session introuvable : {resume}")
            return 1
        history = data.get("messages")
        session_id = data.get("id", target)

    agent = Agent(cfg, session_id=session_id)
    if history:
        agent.load_history(history)
    skills = load_skills(cfg.skills_dirs, cfg.include_claude_skills)
    if cfg.coder.enabled:
        subtitle = f"{cfg.model} + {cfg.coder.model}"
    else:
        subtitle = cfg.model

    # Interface plein ecran (barre epinglee en bas) par defaut ; repli sur la
    # boucle ligne-a-ligne si le terminal ne la supporte pas.
    if os.environ.get("GLMCODE_SIMPLE") not in ("1", "true"):
        try:
            from .tui import TUI

            TUI(agent, subtitle, skills).run()
            return 0
        except Exception as exc:  # noqa: BLE001
            ui.reset_console()
            ui.set_confirm_handler(None)
            ui.print_info(f"(mode plein ecran indisponible : {exc} — mode simple)")

    ui.print_banner(cfg)
    session = ui.build_session(lambda: agent.mode, agent.cycle_mode, subtitle)

    while True:
        try:
            user_input = ui.prompt_user(session)
        except (EOFError, KeyboardInterrupt):
            ui.console.print()
            ui.print_info("A bientot.")
            return 0

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            if not _handle_slash(user_input, agent, skills):
                ui.print_info("A bientot.")
                return 0
            continue

        try:
            agent.send(user_input)
        except KeyboardInterrupt:
            ui.console.print()
            ui.print_info("(interrompu)")


def _print_sessions() -> None:
    from datetime import datetime

    from . import session as sess

    rows = sess.list_sessions()
    if not rows:
        ui.print_info("Aucune session enregistree.")
        return
    ui.console.print("[bold]Sessions enregistrees[/] (reprends avec --resume <id>)")
    for r in rows:
        when = datetime.fromtimestamp(r["updated"]).strftime("%Y-%m-%d %H:%M")
        ui.console.print(
            f"  [cyan]{r['id']}[/]  [dim]{when}[/]  {r['turns']} tours  {r['title']}"
        )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="glmcode", description="Assistant de codage terminal (API Z.ai / GLM)."
    )
    parser.add_argument("--version", action="store_true", help="affiche la version")
    parser.add_argument("--resume", metavar="ID", help="reprend la session <ID>")
    parser.add_argument(
        "--continue", dest="cont", action="store_true",
        help="reprend la derniere session",
    )
    parser.add_argument(
        "--list-sessions", dest="list_sessions", action="store_true",
        help="liste les sessions enregistrees puis quitte",
    )
    args = parser.parse_args()

    if args.version:
        print(f"glmcode {__version__}")
        return
    if args.list_sessions:
        _print_sessions()
        return

    resume = "__LATEST__" if args.cont else args.resume
    sys.exit(run(resume))
