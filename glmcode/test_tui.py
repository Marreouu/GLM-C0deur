#!/usr/bin/env python3
"""Test du TUI pour vérifier que l'interface fonctionne correctement."""

import sys
import os
import time
from unittest.mock import Mock

# Ajouter le répertoire courant au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glmcode.tui import TUI
from glmcode.ui import _MODE_STYLE


def test_tui_basic():
    """Test de base du TUI."""
    print("Test du TUI de base...")
    
    # Créer un agent mock
    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session-123"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None
    
    # Créer un TUI
    tui = TUI(agent, subtitle="Test subtitle")
    
    # Vérifier que le TUI est bien construit
    assert tui.agent == agent
    assert tui.subtitle == "Test subtitle"
    assert tui._queue == []
    assert tui._busy == False
    assert tui._req_count == 0
    assert tui._ctrl_c_pending == False
    assert tui._follow == True
    assert tui._exit_requested == False
    
    print("[OK] TUI de base cree avec succes")


def test_tui_layout():
    """Test du layout du TUI."""
    print("Test du layout du TUI...")
    
    # Créer un agent mock
    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session-123"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None
    
    # Créer un TUI
    tui = TUI(agent, subtitle="Test subtitle")
    
    # Vérifier que les éléments de base sont construits
    # (l'application peut être None dans certains environnements)
    assert tui.input is not None
    assert tui._root is not None
    assert tui._kb is not None
    
    print("[OK] Layout du TUI correct")


def test_tui_status():
    """Test de la fonction de statut."""
    print("Test de la fonction de statut...")

    # Créer un agent mock
    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session-123"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None

    # Créer un TUI
    tui = TUI(agent, subtitle="Test subtitle")

    # Tester la fonction de statut
    status = tui._status()
    assert len(status) > 0
    status_str = str(status)
    assert "NORMAL" in status_str  # Le mode normal doit être dans le statut

    print("[OK] Fonction de statut correcte")


def test_tui_queue():
    """Test de la file d'attente."""
    print("Test de la file d'attente...")

    # Créer un agent mock
    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session-123"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None

    # Créer un TUI
    tui = TUI(agent, subtitle="Test subtitle")

    # Tester la file d'attente vide
    queue_text = tui._queue_text()
    assert queue_text == ""

    # Ajouter un élément à la file d'attente
    tui._queue.append("Test message")
    queue_text = tui._queue_text()
    # Le texte de la file d'attente est maintenant une liste de tuples (style, texte)
    assert isinstance(queue_text, list)
    assert len(queue_text) == 1
    # Vérifier que le contenu contient notre message
    assert "Test message" in queue_text[0][1]

    print("[OK] File d'attente correcte")


def test_tui_completer():
    """Test du completer."""
    print("Test du completer...")

    # Créer un agent mock
    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session-123"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None

    # Créer un TUI
    tui = TUI(agent, subtitle="Test subtitle")

    # Tester le completer
    from prompt_toolkit.document import Document
    completer = tui.input.completer  # Accès direct au completer

    # Tester la complétion des commandes
    document = Document(text="/")
    completions = list(completer.get_completions(document, None))
    assert len(completions) > 0
    assert any(c.text.startswith("/") for c in completions)

    print("[OK] Completer correct")


def test_tui_queue_add_and_dispatch():
    """Test de l'ajout à la file d'attente et de la dispatch."""
    print("Test de l'ajout à la file d'attente et de la dispatch...")

    from glmcode.tui import TUI
    from unittest.mock import Mock
    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None
    tui = TUI(agent)
    # Simule que l'agent est occupe
    tui._busy = True
    mock_buf = Mock()
    mock_buf.text = "test command"
    tui._accept(mock_buf)
    assert tui._queue == ["test command"]
    # Lorsque pas occupe, le message doit etre envoye via _dispatch (on mocke)
    tui._busy = False
    dispatched = []
    original_dispatch = tui._dispatch
    def mock_dispatch(text):
        dispatched.append(text)
    tui._dispatch = mock_dispatch
    mock_buf2 = Mock()
    mock_buf2.text = "another"
    tui._accept(mock_buf2)
    assert dispatched == ["another"]
    tui._dispatch = original_dispatch

    print("[OK] File d'attente et dispatch corrects")


def test_mode_styles():
    """Test des styles de mode."""
    print("Test des styles de mode...")

    # Vérifier que tous les modes ont des styles définis
    assert "normal" in _MODE_STYLE
    assert "auto" in _MODE_STYLE
    assert "plan" in _MODE_STYLE

    # Vérifier que chaque mode a une couleur et un label
    for mode, (color, label) in _MODE_STYLE.items():
        assert isinstance(color, str)
        assert isinstance(label, str)
        assert len(color) > 0
        assert len(label) > 0

    print("[OK] Styles de mode corrects")


def test_tui_instantiation():
    """Test d'instantiation de base du TUI."""
    print("Test d'instantiation du TUI...")

    from glmcode.tui import TUI
    from unittest.mock import Mock
    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None
    tui = TUI(agent, subtitle="Test")
    assert tui.agent == agent
    assert tui.subtitle == "Test"
    assert tui._queue == []
    assert tui._busy == False
    assert tui._req_count == 0

    print("[OK] TUI de base crée avec succes")


def test_stdout_est_patche_pendant_app_run(monkeypatch):
    """Le transcript doit s'inserer AU-DESSUS de la zone epinglee.

    Les ecritures rich faites depuis le thread de l'agent pendant que l'app
    tourne doivent passer par le StdoutProxy de prompt_toolkit. Sans lui,
    elles vont directement dans le terminal a la position courante du
    curseur : le renderer ne sait pas que le curseur a bouge, redessine plus
    bas, et la barre de statut se fait recouvrir.
    """
    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput
    from prompt_toolkit.patch_stdout import StdoutProxy

    from glmcode import tui as tui_module

    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None

    tui = TUI(agent)
    captured = {}

    class _FakeApp:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            captured["stdout"] = sys.stdout

        def invalidate(self):
            pass

        def exit(self):
            pass

    monkeypatch.setattr(tui_module, "Application", _FakeApp)
    monkeypatch.setattr(tui, "_start_watch", lambda: None)
    monkeypatch.setattr(tui, "_stop_watch", lambda: None)
    monkeypatch.setattr(tui_module.ui, "print_banner", lambda cfg: None)

    # Console factice : sous pytest, stdout est un fichier temporaire et
    # prompt_toolkit ne peut pas ouvrir de vrai buffer console.
    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            tui.run()

    assert isinstance(captured.get("stdout"), StdoutProxy), (
        "app.run() doit tourner dans patch_stdout() sinon le transcript "
        "ecrase la barre epinglee"
    )


def test_confirmation_repond_via_la_barre_de_saisie():
    """Les confirmations doivent passer par la ligne de saisie du TUI.

    L'agent tourne dans un thread pendant que prompt_toolkit tient stdin en
    mode raw : un console.input() depuis ce thread se bat avec l'app pour les
    touches, et l'utilisateur ne peut plus repondre.
    """
    import threading
    import time

    from glmcode import ui as ui_module

    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None

    tui = TUI(agent)
    tui.app = Mock()
    try:
        resultat = {}

        def worker():
            resultat["ok"] = ui_module.confirm("Autoriser test ?")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        # Le worker doit se mettre en attente, pas lire stdin.
        deadline = time.time() + 2.0
        while not tui._awaiting_confirm and time.time() < deadline:
            time.sleep(0.01)
        assert tui._awaiting_confirm, (
            "ui.confirm() doit passer par le handler du TUI, pas par console.input()"
        )
        assert thread.is_alive(), "le thread agent doit attendre la reponse"

        # L'utilisateur tape "o" puis Entree dans la barre du bas.
        buf = Mock()
        buf.text = "o"
        tui._accept(buf)

        thread.join(timeout=2.0)
        assert not thread.is_alive(), "la reponse doit debloquer le thread agent"
        assert resultat.get("ok") is True
        assert tui._awaiting_confirm is False
    finally:
        ui_module.set_confirm_handler(None)


def test_confirmation_refus_par_entree_vide():
    """Entree seule = reponse par defaut (non), conformement a l'invite [o/N]."""
    import threading
    import time

    from glmcode import ui as ui_module

    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None

    tui = TUI(agent)
    tui.app = Mock()
    try:
        resultat = {}

        def worker():
            resultat["ok"] = ui_module.confirm("Autoriser test ?")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        deadline = time.time() + 2.0
        while not tui._awaiting_confirm and time.time() < deadline:
            time.sleep(0.01)
        assert tui._awaiting_confirm

        buf = Mock()
        buf.text = ""
        tui._accept(buf)

        thread.join(timeout=2.0)
        assert resultat.get("ok") is False
    finally:
        ui_module.set_confirm_handler(None)


def test_sortie_bufferisee_par_ligne():
    """Aucun fragment sans fin de ligne ne doit atteindre le terminal.

    prompt_toolkit redessine la barre epinglee apres chaque ecriture et, sur
    Windows, ne sait pas relire la colonne du curseur (responds_to_cpr est
    False) : il la suppose a 0. Un fragment laisse en milieu de ligne decale
    donc tout le rendu suivant, d'ou l'affichage en escalier.
    """
    from io import StringIO

    from glmcode.tui import _LineBufferedStdout

    cible = StringIO()
    out = _LineBufferedStdout(lambda: cible)

    # Le streaming ecrit par fragments, avec un flush apres chacun (rich).
    out.write("Bonjour ")
    out.flush()
    assert cible.getvalue() == "", "un fragment partiel ne doit pas sortir"

    out.write("le monde\n")
    assert cible.getvalue() == "Bonjour le monde\n"

    # Plusieurs lignes d'un coup : tout sort sauf le reste partiel.
    out.write("une\ndeux\ntrois")
    out.flush()
    assert cible.getvalue() == "Bonjour le monde\nune\ndeux\n"

    # Fin du tour : le reste est emis avec une fin de ligne propre.
    out.close_line()
    assert cible.getvalue() == "Bonjour le monde\nune\ndeux\ntrois\n"

    # Et rien de plus si le tampon est vide.
    out.close_line()
    assert cible.getvalue() == "Bonjour le monde\nune\ndeux\ntrois\n"


def test_console_du_tui_ne_laisse_pas_de_ligne_partielle(monkeypatch):
    """La Console installee par run() doit passer par le tampon de lignes."""
    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from glmcode import tui as tui_module
    from glmcode import ui as ui_module

    agent = Mock()
    agent.mode = "normal"
    agent.cycle_mode = Mock()
    agent.cancel_event = Mock()
    agent.session_id = "test-session"
    agent.config = Mock()
    agent.config.model = "test-model"
    agent.config.coder = None

    tui = TUI(agent)
    vue = {}

    class _FakeApp:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            vue["console"] = ui_module.console

        def invalidate(self):
            pass

        def exit(self):
            pass

    monkeypatch.setattr(tui_module, "Application", _FakeApp)
    monkeypatch.setattr(tui, "_start_watch", lambda: None)
    monkeypatch.setattr(tui, "_stop_watch", lambda: None)
    monkeypatch.setattr(tui_module.ui, "print_banner", lambda cfg: None)

    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            tui.run()

    assert isinstance(vue["console"].file, tui_module._LineBufferedStdout)


def run_all_tests():
    """Exécuter tous les tests."""
    print("=== Tests du TUI ===")
    
    try:
        test_tui_basic()
        test_tui_layout()
        test_tui_status()
        test_tui_queue()
        test_tui_completer()
        test_mode_styles()
        
        print("\n[SUCCESS] Tous les tests ont réussi !")
        print("Le TUI est prêt à être utilisé.")
        
    except Exception as e:
        print(f"\n[ERROR] Test echec : {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)