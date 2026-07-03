"""Persistance des sessions : sauvegarde/reprise de l'historique de conversation.

Chaque session est un fichier JSON dans ~/.glmcode/sessions/<id>.json contenant
les messages (system/user/assistant/tool) plus des metadonnees (date, modele,
titre derive du premier message). Cela permet de fermer le script puis de
reprendre exactement ou on en etait via `glmcode --resume <id>`.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def sessions_dir() -> Path:
    d = Path.home() / ".glmcode" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_session_id() -> str:
    """ID court et lisible : AAAAMMJJ-hhmmss-xxxx."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid4().hex[:4]}"


def _path(session_id: str) -> Path:
    return sessions_dir() / f"{session_id}.json"


def _title_from(messages: list[dict[str, Any]]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            text = (msg.get("content") or "").strip().replace("\n", " ")
            return text[:60] if text else "(vide)"
    return "(nouvelle session)"


def save_session(
    session_id: str, messages: list[dict[str, Any]], model: str = ""
) -> None:
    """Ecrit la session sur disque (ecrase la version precedente)."""
    path = _path(session_id)
    created = time.time()
    if path.is_file():
        try:
            created = json.loads(path.read_text(encoding="utf-8")).get("created", created)
        except Exception:
            pass
    data = {
        "id": session_id,
        "created": created,
        "updated": time.time(),
        "model": model,
        "title": _title_from(messages),
        "messages": messages,
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_session(session_id: str) -> dict[str, Any] | None:
    """Charge une session par ID. Renvoie None si introuvable/illisible."""
    path = _path(session_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_sessions() -> list[dict[str, Any]]:
    """Liste les sessions, de la plus recente a la plus ancienne."""
    out: list[dict[str, Any]] = []
    for path in sessions_dir().glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        msgs = data.get("messages", [])
        turns = sum(1 for m in msgs if m.get("role") == "user")
        out.append(
            {
                "id": data.get("id", path.stem),
                "updated": data.get("updated", 0),
                "title": data.get("title", ""),
                "model": data.get("model", ""),
                "turns": turns,
            }
        )
    out.sort(key=lambda s: s.get("updated", 0), reverse=True)
    return out


def latest_session_id() -> str | None:
    sessions = list_sessions()
    return sessions[0]["id"] if sessions else None
