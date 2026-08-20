"""Boucle interactive (REPL) et commandes slash."""

from __future__ import annotations

import os
import sys
import threading
import time

from . import __version__, ui
from .agent import MODE_LABELS, MODES, Agent
from .client import LLMClient
from .config import Config, load_config
from .skills import compose_prompt, load_skills
from .updater import UpdateManager
from .version import Version

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
  /update          Verifie et installe les mises a jour
  /check-update    Verifie uniquement les mises a jour disponibles
  /version         Affiche les informations de version
  /exit, /quit     Quitte

[bold]Modes[/] (bascule aussi avec [magenta]Shift+Tab[/])
  normal   confirme chaque action (ecriture / commande)
  auto     execute les actions sans demander
  plan     lecture seule : propose un plan sans rien modifier

[bold]Mention de fichier[/]
  @chemin/fichier  Autocompletion + jonction du contenu au message envoye
                   (tape '@' pour voir la liste des fichiers du projet)

Sinon, ecris simplement ta demande. L'assistant peut lire/ecrire des fichiers
et lancer des commandes (selon le mode)."""


# Instance globale du gestionnaire de mises a jour
_updater: Optional[UpdateManager] = None
_update_check_thread: Optional[threading.Thread] = None
_stop_update_check = threading.Event()


def _initialize_update_system(config: Config) -> None:
    """Initialise le systeme de mise a jour automatique."""
    global _updater, _update_check_thread

    # Initialiser l'uploader
    auto_update_config = getattr(config, 'auto_update', None)
    if auto_update_config is None:
        # Configuration par defaut si pas presente
        auto_update_config = type('AutoUpdateConfig', (), {
            'enabled': True,
            'check_on_start': True,
            'interval': 24,  # heures
            'channel': 'stable'
        })()

    _updater = UpdateManager()
    _updater.update_channel = getattr(auto_update_config, 'channel', 'stable')

    # Demarrer la verificaton periodique si activee
    if getattr(auto_update_config, 'enabled', True) and getattr(auto_update_config, 'check_on_start', True):
        _start_periodic_update_check(getattr(auto_update_config, 'interval', 24) * 3600)  # Convertir heures en secondes


def _start_periodic_update_check(interval_seconds: int) -> None:
    """Demarre la verificaton periodique des mises a jour en arriere-plan."""
    global _update_check_thread, _stop_update_check

    def update_check_loop():
        while not _stop_update_check.is_set():
            try:
                if _updater is not None:
                    _updater.check_for_updates()
                # Attendre l'intervalle spécifié ou jusqu'à l'arrêt
                _stop_update_check.wait(interval_seconds)
            except Exception:
                # En cas d'erreur silencieux pour ne pas interrompre l'utilisateur
                _stop_update_check.wait(60)  # Réessayer après 1 minute en cas d'erreur

    _stop_update_check.clear()
    _update_check_thread = threading.Thread(target=update_check_loop, daemon=True)
    _update_check_thread.start()


def _stop_update_system() -> None:
    """Arrete le systeme de mise a jour."""
    global _update_check_thread, _stop_update_check
    _stop_update_check.set()
    if _update_check_thread and _update_check_thread.is_alive():
        _update_check_thread.join(timeout=5.0)


def _handle_slash(cmd: str, agent: Agent, skills: dict) -> bool:
    """Retourne True s'il faut continuer la boucle, False pour quitter."""
    global _updater

    parts = cmd.strip().split(maxsplit=1)
    name = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if name in ("/exit", "/quit"):
        _stop_update_system()
        return False
    elif name == "/help":
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
    elif name == "/update":
        _handle_update_command(agent)
    elif name == "/check-update":
        _handle_check_update_command(agent)
    elif name == "/version":
        _handle_version_command(agent)
    else:
        ui.print_error(f"Commande inconnue : {name} (voir /help)")
    return True


def _handle_update_command(agent: Agent) -> None:
    """Ger la commande /update."""
    global _updater

    if _updater is None:
        ui.print_error("Systeme de mise a jour non initialise")
        return

    ui.print_info("Verification des mises a jour en cours...")
    update_available = _updater.check_for_update()

    if update_available:
        update_info = _updater.get_update_info()
        if update_info:
            current_ver = _updater.get_current_version()
            latest_ver = _updater.get_latest_version()

            ui.print_info(f"Version actuelle : {current_ver}")
            ui.print_info(f"Nouvelle version disponible : {latest_ver}")

            if hasattr(update_info, 'get') and update_info.get('critical', False):
                ui.print_warning("MISE A JOUR CRITIQUE DISPONIBLE")
            else:
                ui.print_info("Nouvelle version disponible")

            ui.print_info("Telechargement et installation de la mise a jour...")
            if _updater.apply_update():
                ui.print_info("Mise a jour terminee avec succès. Redemarrage de l'application...")
                # Noter que l'application va redémarrer, donc on sort
                # Le redémarrage réel sera géré par l'updater lui-même
                ui.print_info("Redemarrage en cours...")
                # Donner un peu de temps pour que le message s'affiche
                time.sleep(1)
                # L'updater devrait gérer le redémarrage
            else:
                ui.print_error("Echec de la mise a jour. Voir les logs pour plus de details.")
        else:
            ui.print_info("Mise a jour disponible mais informations indisponibles")
            if _updater.apply_update():
                ui.print_info("Mise a jour terminee. Redemarrage en cours...")
            else:
                ui.print_error("Echec de la mise a jour")
    else:
        ui.print_info("Vous utilisez deja la derniere version disponible.")


def _handle_check_update_command(agent: Agent) -> None:
    """Ger la commande /check-update."""
    global _updater

    if _updater is None:
        ui.print_error("Systeme de mise a jour non initialise")
        return

    ui.print_info("Verification des mises a jour...")
    update_available = _updater.check_for_updates()

    if update_available:
        update_info = _updater.get_update_info()
        if update_info:
            current_ver = _updater.get_current_version()
            latest_ver = _updater.get_latest_version()

            ui.print_info(f"Version actuelle : {current_ver}")
            ui.print_info(f"Nouvelle version disponible : {latest_ver}")

            if hasattr(update_info, 'get') and update_info.get('critical', False):
                ui.print_warning("MISE A JOUR CRITIQUE DISPONIBLE")
            else:
                ui.print_info("Nouvelle version disponible")

            # Afficher le message de mise a jour si disponible
            message = update_info.get('message', '')
            if message:
                ui.print_info(f"Message : {message}")

            # Afficher les instructions pour mettre a jour
            ui.print_info("Tapez /update pour telecharger et installer la mise a jour.")
        else:
            ui.print_info("Mise a jour disponible mais informations indisponibles")
    else:
        ui.print_info("Vous utilisez deja la derniere version disponible.")


def _handle_version_command(agent: Agent) -> None:
    """Ger la commande /version."""
    global _updater

    current_ver = Version.parse(__version__)
    ui.print_info(f"Version locale : {current_ver}")

    if _updater is not None:
        latest_ver = _updater.get_latest_version()
        if latest_ver is not None:
            ui.print_info(f"Version distante : {latest_ver}")

            # Comparer les versions
            comparison = current_ver.compare(latest_ver) if hasattr(current_ver, 'compare') else \
                        (1 if str(current_ver) > str(latest_ver) else
                         -1 if str(current_ver) < str(latest_ver) else 0)

            if comparison < 0:
                ui.print_info("Une mise a jour est disponible")
            elif comparison > 0:
                ui.print_info("Vous avez une version plus recente que celle du depot")
            else:
                ui.print_info("Vous avez la derniere version")
        else:
            ui.print_info("Impossible de verifier la version distante")
    else:
        # Essayer de verifier quand même une fois
        try:
            temp_updater = UpdateManager()
            if temp_updater.check_for_updates():
                latest_ver = temp_updater.get_latest_version()
                if latest_ver is not None:
                    ui.print_info(f"Version distante : {latest_ver}")
                    comparison = current_ver.compare(latest_ver) if hasattr(current_ver, 'compare') else \
                                (1 if str(current_ver) > str(latest_ver) else
                                 -1 if str(current_ver) < str(latest_ver) else 0)
                    if comparison < 0:
                        ui.print_info("Une mise a jour est disponible")
                    elif comparison > 0:
                        ui.print_info("Vous avez une version plus recente que celle du depot")
                    else:
                        ui.print_info("Vous avez la derniere version")
                else:
                    ui.print_info("Aucune information de version distante disponible")
            else:
                ui.print_info("Vous utilisez deja la derniere version disponible")
        except Exception:
            ui.print_info("Impossible de verifier les mises a jour pour le moment")


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

    # Initialiser le systeme de mise a jour
    _initialize_update_system(cfg)

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
            _stop_update_system()
            ui.console.print()
            ui.print_info("A bientot.")
            return 0

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            if not _handle_slash(user_input, agent, skills):
                _stop_update_system()
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
    ui.console.print("[bold]Sessions enregistrees[/] (reprens avec --resume <id>)")
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