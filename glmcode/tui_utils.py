"""Utilitaires pour le TUI - gestion du patching stdout et affichage."""

from __future__ import annotations
import sys
import threading
from contextlib import contextmanager
from io import StringIO
from typing import Optional, Generator
import time

from rich.console import Console
from rich.markup import escape


class TUIBuffer:
    """Gère un buffer pour capturer les sorties et les afficher dans le TUI."""
    
    def __init__(self, max_lines: int = 1000):
        self.max_lines = max_lines
        self.buffer: list[str] = []
        self.lock = threading.Lock()
        self._last_update = 0
        
    def write(self, text: str) -> None:
        """Écrire dans le buffer."""
        with self.lock:
            timestamp = time.time()
            self.buffer.append(f"[{timestamp:.3f}] {text}")
            # Garder seulement les max_lines dernières entrées
            if len(self.buffer) > self.max_lines:
                self.buffer = self.buffer[-self.max_lines:]
            self._last_update = timestamp
    
    def flush(self) -> None:
        """Vider le buffer (implémentation de l'interface file-like)."""
        pass
    
    def get_content(self) -> str:
        """Récupérer le contenu complet du buffer."""
        with self.lock:
            return "\n".join(self.buffer)
    
    def clear(self) -> None:
        """Vider le buffer."""
        with self.lock:
            self.buffer.clear()
            self._last_update = 0


# Global buffer pour le TUI
_tui_buffer: Optional[TUIBuffer] = None
_original_stdout: Optional[object] = None
_original_stderr: Optional[object] = None


def get_tui_buffer() -> TUIBuffer:
    """Obtenir le buffer global du TUI."""
    global _tui_buffer
    if _tui_buffer is None:
        _tui_buffer = TUIBuffer()
    return _tui_buffer


@contextmanager
def patch_stdout_tui() -> Generator[StringIO, None, None]:
    """Rediriger stdout et stderr vers le buffer du TUI."""
    global _tui_buffer, _original_stdout, _original_stderr
    
    # Sauvegarder les originaux
    if _original_stdout is None:
        _original_stdout = sys.stdout
    if _original_stderr is None:
        _original_stderr = sys.stderr
    
    # Créer un buffer pour cette session
    buffer = StringIO()
    tui_buffer = get_tui_buffer()
    
    # Créer un wrapper qui écrit à la fois dans le buffer et dans le TUI
    class TUIWriter:
        def write(self, text: str) -> None:
            buffer.write(text)
            tui_buffer.write(text)
            
        def flush(self) -> None:
            buffer.flush()
            tui_buffer.flush()
    
    # Rediriger stdout et stderr
    sys.stdout = TUIWriter()
    sys.stderr = TUIWriter()
    
    try:
        yield buffer
    finally:
        # Restaurer les originaux
        sys.stdout = _original_stdout
        sys.stderr = _original_stderr


def clear_tui_buffer() -> None:
    """Vider le buffer du TUI."""
    buffer = get_tui_buffer()
    buffer.clear()


def print_tui_content(console: Console, max_display_lines: int = 50) -> None:
    """Afficher le contenu du buffer TUI dans la console."""
    buffer = get_tui_buffer()
    content = buffer.get_content()
    
    if not content:
        return
    
    # Diviser en lignes et prendre les dernières lignes
    lines = content.split('\n')
    if len(lines) > max_display_lines:
        lines = lines[-max_display_lines:]
    
    # Afficher avec le style approprié
    console.print()
    console.print(f"[bold {PURPLE}]⏺[/]  ", end="")
    for line in lines:
        if line.strip():
            console.print(line, highlight=False, soft_wrap=True)


# Importer les couleurs depuis ui
try:
    from .ui import PURPLE, DIM
except ImportError:
    # Fallback si ui n'est pas disponible
    PURPLE = "#bb9af7"
    DIM = "#565f89"