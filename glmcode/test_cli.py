"""Tests pour l'interface en ligne de commande (CLI)."""

import os
from unittest.mock import Mock

import glmcode.cli as cli


def test_cli_uses_tui_when_not_simple(monkeypatch):
    """Vérifie que le CLI utilise TUI lorsque GLMCODE_SIMPLE n'est pas défini."""
    # Simule que GLMCODE_SIMPLE n'est pas défini
    monkeypatch.delenv("GLMCODE_SIMPLE", raising=False)

    # Crée un mock pour l'agent
    mock_agent = Mock()
    mock_agent.config = Mock()
    mock_agent.config.model = "test-model"

    # Mock TUI pour vérifier qu'il est appelé correctement
    mock_tui_instance = Mock()
    mock_tui_instance.run = Mock()

    def mock_tui_constructor(agent, subtitle="", skills=None):
        assert agent == mock_agent
        assert subtitle == ""
        assert skills is None or isinstance(skills, dict)
        return mock_tui_instance

    monkeypatch.setattr(cli, "TUI", mock_tui_constructor)

    # Mock les autres dépendances
    monkeypatch.setattr(cli, "LLMClient", Mock())
    monkeypatch.setattr(cli, "_stop_update_system", Mock())
    monkeypatch.setattr(cli.ui, "print_info", Mock())
    monkeypatch.setattr(cli.ui, "print_error", Mock())
    monkeypatch.setattr(cli.ui, "reset_console", Mock())
    monkeypatch.setattr(cli.ui, "set_confirm_handler", Mock())

    # Mock sys.exit pour empêcher la sortie réelle du programme
    mock_exit = Mock(side_effect=SystemExit(0))
    monkeypatch.setattr("sys.exit", mock_exit)

    try:
        cli.main()
    except SystemExit:
        pass  # Attendu lorsque sys.exit est appelé

    # Vérifier que le constructeur TUI a été appelé
    mock_tui_constructor.assert_called_once()
    # Vérifier que la méthode run de l'instance TUI a été appelée
    mock_tui_instance.run.assert_called_once()


def test_cli_uses_simple_when_env_set(monkeypatch):
    """Vérifie que le CLI utilise le mode simple lorsque GLMCODE_SIMPLE est défini."""
    # Définit GLMCODE_SIMPLE pour forcer le mode simple
    monkeypatch.setenv("GLMCODE_SIMPLE", "1")

    # Mock la fonction de boucle simple
    mock_simple_loop = Mock()
    monkeypatch.setattr(cli, "simple_loop", mock_simple_loop)

    # Mock les autres dépendances
    monkeypatch.setattr(cli, "LLMClient", Mock())
    monkeypatch.setattr(cli, "_stop_update_system", Mock())
    monkeypatch.setattr(cli.ui, "print_info", Mock())
    monkeypatch.setattr(cli.ui, "print_error", Mock())
    monkeypatch.setattr(cli.ui, "reset_console", Mock())
    monkeypatch.setattr(cli.ui, "set_confirm_handler", Mock())

    # Mock sys.exit pour empêcher la sortie réelle du programme
    mock_exit = Mock(side_effect=SystemExit(0))
    monkeypatch.setattr("sys.exit", mock_exit)

    try:
        cli.main()
    except SystemExit:
        pass  # Attendu lorsque sys.exit est appelé

    # Vérifier que la boucle simple a été appelée
    mock_simple_loop.assert_called_once()

    # Vérifier que TUI n'a pas été importé (ou du moins pas utilisé)
    # Note: Comme l'import est à l'intérieur du bloc conditionnel,
    # il ne devrait pas être exécuté lorsque GLMCODE_SIMPLE est défini