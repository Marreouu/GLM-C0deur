"""Outils que le modele peut appeler (function calling).

Chaque outil expose :
- un schema JSON (format OpenAI) declare dans TOOLS_SCHEMA
- une fonction Python d'execution dans TOOL_IMPLS

Les actions qui modifient le disque ou lancent une commande passent par une
demande de confirmation geree dans agent.py (sauf mode auto_approve).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Taille max de lecture pour eviter de saturer le contexte.
MAX_READ_BYTES = 100_000


def _safe_path(path: str) -> Path:
    return Path(path).expanduser()


def read_file(path: str, **_) -> str:
    p = _safe_path(path)
    if not p.is_file():
        return f"[erreur] Fichier introuvable : {path}"
    data = p.read_bytes()[:MAX_READ_BYTES]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return f"[erreur] Fichier binaire ou encodage non-UTF8 : {path}"
    return text


def write_file(path: str, content: str, **_) -> str:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"[ok] Ecrit {len(content)} caracteres dans {path}"


def edit_file(path: str, old: str, new: str, **_) -> str:
    p = _safe_path(path)
    if not p.is_file():
        return f"[erreur] Fichier introuvable : {path}"
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        return f"[erreur] Texte a remplacer introuvable dans {path}"
    if count > 1:
        return (
            f"[erreur] Le texte apparait {count} fois dans {path} ; "
            "rends-le plus specifique pour un remplacement unique."
        )
    p.write_text(text.replace(old, new), encoding="utf-8")
    return f"[ok] Modifie {path}"


def list_dir(path: str = ".", **_) -> str:
    p = _safe_path(path)
    if not p.is_dir():
        return f"[erreur] Dossier introuvable : {path}"
    entries = []
    for child in sorted(p.iterdir()):
        suffix = "/" if child.is_dir() else ""
        entries.append(child.name + suffix)
    return "\n".join(entries) if entries else "(dossier vide)"


def _decode(raw: bytes) -> str:
    """Decode une sortie shell en essayant plusieurs encodages (Windows inclus)."""
    if not raw:
        return ""
    for enc in ("utf-8", "cp1252", "cp850"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def run_command(command: str, **_) -> str:
    # On capture des octets bruts (pas de text=True) pour eviter les crashs de
    # decodage : la sortie Windows n'est pas toujours de l'UTF-8.
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return "[erreur] Commande interrompue (timeout 120s)"
    out = (_decode(result.stdout) + _decode(result.stderr)).strip() or "(aucune sortie)"
    return f"[code retour {result.returncode}]\n{out[:MAX_READ_BYTES]}"


TOOL_IMPLS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_dir": list_dir,
    "run_command": run_command,
}

# Outils qui necessitent une confirmation utilisateur.
DESTRUCTIVE_TOOLS = {"write_file", "edit_file", "run_command"}

# Outils lecture-seule, autorises en mode plan.
READONLY_TOOLS = {"read_file", "list_dir"}


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lit et renvoie le contenu texte d'un fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier a lire"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Cree ou remplace entierement un fichier avec le contenu fourni.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier"},
                    "content": {"type": "string", "description": "Contenu complet du fichier"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Remplace une occurrence unique de texte dans un fichier existant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier"},
                    "old": {"type": "string", "description": "Texte exact a remplacer (unique)"},
                    "new": {"type": "string", "description": "Nouveau texte"},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Liste les fichiers et dossiers d'un repertoire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du dossier (defaut : .)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute une commande shell et renvoie sa sortie. A utiliser avec prudence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Commande a executer"},
                },
                "required": ["command"],
            },
        },
    },
]

# Sous-ensemble expose en mode plan (aucune action destructive).
READONLY_TOOLS_SCHEMA = [
    t for t in TOOLS_SCHEMA if t["function"]["name"] in READONLY_TOOLS
]
