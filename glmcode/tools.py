"""Outils que le modele peut appeler (function calling).

Chaque outil expose :
- un schema JSON (format OpenAI) declare dans TOOLS_SCHEMA
- une fonction Python d'execution dans TOOL_IMPLS

Les actions qui modifient le disque ou lancent une commande passent par une
demande de confirmation geree dans agent.py (sauf mode auto_approve).
"""

from __future__ import annotations

import subprocess
import functools
import shutil
import glob as glob_module
import os
import socket
import urllib.request
import urllib.parse
import urllib.error
import re
from pathlib import Path
from typing import List
from .performance_monitor import profile, record_metric

# Taille max de lecture pour eviter de saturer le contexte.
MAX_READ_BYTES = 100_000


def _safe_path(path: str) -> Path:
    return Path(path).expanduser()


def _ensure_parent_exists(path: Path) -> None:
    """Cree le repertoire parent si necessaire."""
    path.parent.mkdir(parents=True, exist_ok=True)


@profile("read_file")
def read_file(path: str, **_) -> str:
    p = _safe_path(path)
    if not p.is_file():
        record_metric("file_not_found", 1, "count", {"path": path})
        return f"[erreur] Fichier introuvable : {path}"
    data = p.read_bytes()[:MAX_READ_BYTES]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        record_metric("file_encoding_error", 1, "count", {"path": path})
        return f"[erreur] Fichier binaire ou encodage non-UTF8 : {path}"

    record_metric("file_read", 1, "count", {"path": path, "size": len(text)})
    return text


@profile("write_file")
def write_file(path: str, content: str, **_) -> str:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    record_metric("file_written", 1, "count", {"path": path, "size": len(content)})
    return f"[ok] Ecrit {len(content)} caracteres dans {path}"


@profile("edit_file")
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


@profile("list_dir")
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


# ─── Activite shell (lue par la barre de statut du TUI) ─────────────────
# Renseignee pendant qu'une commande tourne, remise a None ensuite. Ecrite
# depuis le thread de l'agent, lue depuis le thread d'affichage : une simple
# reference suffit, aucune section critique n'est necessaire.
_active_shell: tuple[str, str] | None = None


def active_shell() -> tuple[str, str] | None:
    """Renvoie (nom du shell, commande) si une commande tourne, sinon None."""
    return _active_shell


def _shell_tool(shell_name: str):
    """Signale a l'interface qu'un shell tourne pendant l'appel."""
    def decorateur(fn):
        @functools.wraps(fn)
        def enveloppe(command: str = "", *args, **kwargs):
            global _active_shell
            _active_shell = (shell_name, command)
            try:
                return fn(command, *args, **kwargs)
            finally:
                _active_shell = None
        return enveloppe
    return decorateur


@profile("run_command")
@_shell_tool("shell")
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
        record_metric("command_timeout", 1, "count", {"command": command})
        return "[erreur] Commande interrompue (timeout 120s)"
    out = (_decode(result.stdout) + _decode(result.stderr)).strip() or "(aucune sortie)"

    # Record metrics
    record_metric("command_execution", 1, "count", {
        "command": command,
        "return_code": result.returncode,
        "output_length": len(out)
    })

    return f"[code retour {result.returncode}]\n{out[:MAX_READ_BYTES]}"


@profile("append_file")
def append_file(path: str, content: str, **_) -> str:
    """Ajoute du contenu a la fin d'un fichier existant."""
    p = _safe_path(path)
    if not p.is_file():
        return f"[erreur] Fichier introuvable : {path}"
    p.write_text(p.read_text(encoding="utf-8") + content, encoding="utf-8")
    record_metric("file_appended", 1, "count", {
        "path": path,
        "size": len(content)
    })
    return f"[ok] Ajoute {len(content)} caracteres a {path}"


@profile("copy_file")
def copy_file(src: str, dst: str, **_) -> str:
    """Copie un fichier de src vers dst."""
    src_path = _safe_path(src)
    dst_path = _safe_path(dst)
    if not src_path.is_file():
        return f"[erreur] Fichier source introuvable : {src}"
    _ensure_parent_exists(dst_path)
    shutil.copy2(src_path, dst_path)
    record_metric("file_copied", 1, "count", {
        "source": src,
        "destination": dst
    })
    return f"[ok] Copie de {src} vers {dst}"


@profile("move_file")
def move_file(src: str, dst: str, **_) -> str:
    """Deplace un fichier de src vers dst."""
    src_path = _safe_path(src)
    dst_path = _safe_path(dst)
    if not src_path.is_file():
        return f"[erreur] Fichier source introuvable : {src}"
    _ensure_parent_exists(dst_path)
    shutil.move(str(src_path), str(dst_path))
    record_metric("file_moved", 1, "count", {
        "source": src,
        "destination": dst
    })
    return f"[ok] Deplace de {src} vers {dst}"


@profile("rename_file")
def rename_file(src: str, new_name: str, **_) -> str:
    """Renomme un fichier."""
    src_path = _safe_path(src)
    if not src_path.is_file():
        return f"[erreur] Fichier introuvable : {src}"
    dst_path = src_path.parent / new_name
    if dst_path.exists():
        return f"[erreur] Un fichier nommé {new_name} existe déja dans {src_path.parent}"
    src_path.rename(dst_path)
    record_metric("file_renamed", 1, "count", {
        "source": src,
        "new_name": new_name
    })
    return f"[ok] Renomme {src} en {new_name}"


@profile("create_file")
def create_file(path: str, content: str = "", **_) -> str:
    """Cree un nouveau fichier avec le contenu optionnel."""
    p = _safe_path(path)
    if p.exists():
        return f"[erreur] Le fichier {path} existe deja"
    _ensure_parent_exists(p)
    p.write_text(content, encoding="utf-8")
    record_metric("file_created", 1, "count", {
        "path": path,
        "size": len(content)
    })
    return f"[ok] Cree le fichier {path} avec {len(content)} caracteres"


@profile("create_dir")
def create_dir(path: str, **_) -> str:
    """Cree un nouveau repertoire."""
    p = _safe_path(path)
    if p.exists():
        return f"[erreur] Le chemin {path} existe deja"
    p.mkdir(parents=True, exist_ok=True)
    record_metric("directory_created", 1, "count", {
        "path": path
    })
    return f"[ok] Cree le repertoire {path}"


@profile("delete_dir")
def delete_dir(path: str, **_) -> str:
    """Supprime un repertoire et tout son contenu."""
    p = _safe_path(path)
    if not p.exists():
        return f"[erreur] Le repertoire {path} n'existe pas"
    if not p.is_dir():
        return f"[erreur] {path} n'est pas un repertoire"
    shutil.rmtree(p)
    record_metric("directory_deleted", 1, "count", {
        "path": path
    })
    return f"[ok] Supprime le repertoire {path} et tout son contenu"


@profile("find_files")
def find_files(pattern: str, path: str = ".", **_) -> str:
    """Trouve des fichiers correspondant a un motif dans un repertoire et ses sous-repertoires."""
    search_path = _safe_path(path)
    if not search_path.is_dir():
        return f"[erreur] Repertoire introuvable : {path}"

    matches = []
    files_searched = 0
    try:
        for root, dirs, files in os.walk(search_path):
            files_searched += len(files)
            for file in files:
                if glob_module.fnmatch.fnmatch(file, pattern):
                    rel_path = os.path.relpath(os.path.join(root, file), search_path)
                    matches.append(rel_path)

        record_metric("files_found", len(matches), "count", {
            "pattern": pattern,
            "path": path,
            "files_searched": files_searched
        })

        return "\n".join(matches) if matches else "(aucun fichier trouvé)"
    except Exception as e:
        return f"[erreur] Erreur lors de la recherche: {e}"


@profile("glob")
def glob(pattern: str, path: str = ".", **_) -> str:
    """Trouve des fichiers correspondant a un motif glob dans un repertoire."""
    search_path = _safe_path(path)
    if not search_path.is_dir():
        return f"[erreur] Repertoire introuvable : {path}"

    # Change directory temporairement pour que glob fonctionne correctement
    old_cwd = os.getcwd()
    try:
        os.chdir(search_path)
        matches = glob_module.glob(pattern, recursive=True)
    finally:
        os.chdir(old_cwd)

    record_metric("glob_matches_found", len(matches), "count", {
        "pattern": pattern,
        "path": path
    })

    return "\n".join(matches) if matches else "(aucun fichier trouvé)"


@profile("file_exists")
def file_exists(path: str, **_) -> str:
    """Verifie si un fichier ou repertoire existe."""
    p = _safe_path(path)
    exists = p.exists()
    record_metric("file_exists_check", 1, "count", {
        "path": path,
        "exists": exists
    })
    return "[ok] true" if exists else "[ok] false"


@profile("read_multiple_files")
def read_multiple_files(paths: str, **_) -> str:
    """Lit plusieurs fichiers et retourne leur contenu concatené.

    Args:
        paths: Liste de chemins separes par des virgules
    """
    path_list = [p.strip() for p in paths.split(",") if p.strip()]
    if not path_list:
        return "[erreur] Aucune chemin fourni"

    results = []
    errors = []

    for path in path_list:
        p = _safe_path(path)
        if not p.is_file():
            errors.append(f"[erreur] Fichier introuvable : {path}")
            continue

        try:
            data = p.read_bytes()[:MAX_READ_BYTES]
            text = data.decode("utf-8")
            results.append(f"=== {path} ===\n{text}")
        except UnicodeDecodeError:
            errors.append(f"[erreur] Fichier binaire ou encodage non-UTF8 : {path}")
        except Exception as e:
            errors.append(f"[erreur] Impossible de lire {path}: {e}")

    output = []
    if results:
        output.append("\n\n---\n\n".join(results))
    if errors:
        output.extend(errors)

    record_metric("read_multiple_files_operation", 1, "count", {
        "files_requested": len(path_list),
        "files_success": len(results),
        "files_failed": len(errors)
    })

    return "\n\n".join(output) if output else "(aucun contenu)"


@profile("write_multiple_files")
def write_multiple_files(file_map: str, **_) -> str:
    """Ecrit plusieurs fichiers a partir d'une correspondance fichier->contenu.

    Args:
        file_map: Chaîne au format "chemin1:contenu1,chemin2:contenu2,..."
    """
    if not file_map.strip():
        return "[erreur] Aucune correspondance fichier-contenu fournie"

    pairs = file_map.split(",")
    results = []
    errors = []

    for pair in pairs:
        if ":" not in pair:
            errors.append(f"[erreur] Format invalide (attendu 'chemin:contenu') : {pair}")
            continue

        path, content = pair.split(":", 1)
        path = path.strip()
        content = content.strip()

        if not path:
            errors.append("[erreur] Chemin vide")
            continue

        try:
            p = _safe_path(path)
            _ensure_parent_exists(p)
            p.write_text(content, encoding="utf-8")
            results.append(f"[ok] Ecrit {len(content)} caracteres dans {path}")
        except Exception as e:
            errors.append(f"[erreur] Impossible d'ecrire {path}: {e}")

    output = []
    if results:
        output.extend(results)
    if errors:
        output.extend(errors)

    record_metric("write_multiple_files_operation", 1, "count", {
        "files_requested": len(pairs),
        "files_success": len(results),
        "files_failed": len(errors)
    })

    return "\n".join(output) if output else "(aucune opération effectuée)"


@profile("replace_text")
def replace_text(path: str, old: str, new: str, **_) -> str:
    """Remplace toutes les occurrences d'un texte dans un fichier."""
    p = _safe_path(path)
    if not p.is_file():
        return f"[erreur] Fichier introuvable : {path}"

    text = p.read_text(encoding="utf-8")
    if old not in text:
        return f"[erreur] Texte a remplacer introuvable dans {path}"

    new_text = text.replace(old, new)
    count = text.count(old)
    p.write_text(new_text, encoding="utf-8")

    record_metric("text_replaced", count, "count", {
        "path": path,
        "old_length": len(old),
        "new_length": len(new)
    })

    return f"[ok] Remplace {count} occurrence(s) de '{old}' par '{new}' dans {path}"


@profile("replace_regex")
def replace_regex(path: str, pattern: str, replacement: str, **_) -> str:
    """Remplace toutes les occurrences correspondant a une expression reguliere."""
    import re

    p = _safe_path(path)
    if not p.is_file():
        return f"[erreur] Fichier introuvable : {path}"

    text = p.read_text(encoding="utf-8")
    try:
        new_text, count = re.subn(pattern, replacement, text)
        if count == 0:
            return f"[erreur] Aucun motif correspondant trouve dans {path}"
        p.write_text(new_text, encoding="utf-8")

        record_metric("regex_replacements", count, "matches", {
            "path": path,
            "pattern": pattern,
            "replacement_length": len(replacement)
        })

        return f"[ok] Remplace {count} occurrence(s) du motif par '{replacement}' dans {path}"
    except re.error as e:
        return f"[erreur] Expression reguliere invalide: {e}"


@profile("grep_operation")
def grep(pattern: str, path: str = ".", **_) -> str:
    """Recherche un motif dans les fichiers d'un repertoire (comme la commande grep)."""
    search_path = _safe_path(path)
    if not search_path.is_dir():
        return f"[erreur] Repertoire introuvable : {path}"

    matches = []
    try:
        # Utiliser grep via subprocess pour de meilleures performances
        cmd = f'grep -r "{pattern}" "{search_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.stdout:
            matches.append(result.stdout.strip())
        if result.stderr and "No such file or directory" not in result.stderr:
            # Ignorer l'erreur "No such file or directory" qui est normale quand aucun fichier ne correspond
            if "No such file or directory" not in result.stderr:
                matches.append(f"[avertissement] {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        return "[erreur] Recherche interrompue (timeout 30s)"
    except Exception as e:
        # Fallback sur une implementation en Python
        matches = []
        try:
            pattern_re = re.compile(pattern)
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if pattern_re.search(line):
                                    rel_path = os.path.relpath(file_path, search_path)
                                    matches.append(f"{rel_path}:{i}:{line.rstrip()}")
                    except (OSError, UnicodeDecodeError):
                        # Ignorer les fichiers binaires ou inaccessibles
                        continue
        except re.error as e:
            return f"[erreur] Expression reguliere invalide: {e}"

    # Mesurer le nombre de correspondances et d'articles pesquisés pour des métriques supplémentaires
    files_searched = 0
    try:
        for root, dirs, files in os.walk(search_path):
            files_searched += len(files)
    except Exception:
        pass  # Ignorer les erreurs de comptage

    record_metric("grep_matches_found", len(matches), "matches", {
        "pattern": pattern,
        "path": path,
        "files_searched": files_searched
    })

    return "\n".join(matches) if matches else "(aucun résultat trouvé)"


@profile("search_text")
def search_text(text: str, path: str = ".", **_) -> str:
    """Recherche du texte litteral dans les fichiers d'un repertoire."""
    search_path = _safe_path(path)
    if not search_path.is_dir():
        return f"[erreur] Repertoire introuvable : {path}"

    matches = []
    files_searched = 0
    try:
        for root, dirs, files in os.walk(search_path):
            files_searched += len(files)
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if text in content:
                            # Trouver toutes les lignes contenant le texte
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if text in line:
                                    rel_path = os.path.relpath(file_path, search_path)
                                    matches.append(f"{rel_path}:{i}:{line.rstrip()}")
                except (OSError, UnicodeDecodeError):
                    # Ignorer les fichiers binaires ou inaccessibles
                    continue
    except Exception as e:
        return f"[erreur] Erreur lors de la recherche: {e}"

    record_metric("search_text_operation", 1, "count", {
        "text": text,
        "path": path,
        "matches": len(matches),
        "files_searched": files_searched
    })

    return "\n".join(matches) if matches else "(aucun résultat trouvé)"


@profile("search_regex")
def search_regex(pattern: str, path: str = ".", **_) -> str:
    """Recherche une expression reguliere dans les fichiers d'un repertoire."""
    search_path = _safe_path(path)
    if not search_path.is_dir():
        return f"[erreur] Repertoire introuvable : {path}"

    matches = []
    files_searched = 0
    try:
        regex = re.compile(pattern)
        for root, dirs, files in os.walk(search_path):
            files_searched += len(files)
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        for match in regex.finditer(content):
                            # Trouver la ligne contenant la correspondance
                            lines = content[:match.start()].count('\n')
                            line_content = content.split('\n')[lines] if lines < len(content.split('\n')) else ""
                            relative_path = os.path.relpath(file_path, search_path)
                            matches.append(f"{relative_path}:{lines+1}:{line_content.strip()}")
                except Exception:
                    # Ignorer les fichiers qui ne peuvent pas être lus
                    continue
    except re.error as e:
        return f"[erreur] Expression reguliere invalide: {e}"
    except Exception as e:
        return f"[erreur] Erreur lors de la recherche: {e}"

    record_metric("search_regex_operation", 1, "count", {
        "pattern": pattern,
        "path": path,
        "matches": len(matches),
        "files_searched": files_searched
    })

    return "\n".join(matches) if matches else "(aucun résultat trouvé)"


@profile("find_symbol")
def find_symbol(symbol: str, path: str = ".", **_) -> str:
    """Trouve un symbole (fonction, classe, etc.) dans les fichiers source."""
    search_path = _safe_path(path)
    if not search_path.is_dir():
        return f"[erreur] Repertoire introuvable : {path}"

    # Patterns pour differents types de symboles dans differents langages
    patterns = [
        rf'\b{re.escape(symbol)}\s*\([^)]*\)\s*{{?',  # Fonctions
        rf'\bclass\s+{re.escape(symbol)}\b',          # Classes
        rf'\bdef\s+{re.escape(symbol)}\b',            # Fonctions Python
        rf'\bfunction\s+{re.escape(symbol)}\b',       # Fonctions JS/PHP
        rf'\bvoid\s+{re.escape(symbol)}\s*\(',       # Fonctions C/C++/Java
        rf'\b{re.escape(symbol)}\s*[:=]',             # Variables
    ]

    combined_pattern = '|'.join(f'({p})' for p in patterns)
    try:
        pattern_re = re.compile(combined_pattern, re.IGNORECASE)
    except re.error:
        # Fallback simple si la regex complexe echoue
        pattern_re = re.compile(re.escape(symbol), re.IGNORECASE)

    matches = []
    try:
        for root, dirs, files in os.walk(search_path):
            for file in files:
                # Limiter aux fichiers source courants
                if any(file.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs']):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if pattern_re.search(line):
                                    rel_path = os.path.relpath(file_path, search_path)
                                    matches.append(f"{rel_path}:{i}:{line.rstrip()}")
                    except (OSError, UnicodeDecodeError):
                        # Ignorer les fichiers binaires ou inaccessibles
                        continue
    except Exception as e:
        return f"[erreur] Erreur lors de la recherche: {e}"

    # Supprimer les doublons tout en préservant l'ordre
    seen = set()
    unique_matches = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            unique_matches.append(match)

    record_metric("symbols_found", len(unique_matches), "count", {
        "symbol": symbol,
        "path": path
    })

    return "\n".join(unique_matches) if unique_matches else "(aucun symbole trouvé)"


@profile("pwd")
def pwd(**_) -> str:
    """Retourne le repertoire de travail courant."""
    result = f"[ok] {os.getcwd()}"
    record_metric("current_directory_check", 1, "count", {})
    return result


@profile("tree")
def tree(path: str = ".", **_) -> str:
    """Affiche l'arborescence d'un repertoire sous forme texte."""
    search_path = _safe_path(path)
    if not search_path.is_dir():
        record_metric("tree_error", 1, "count", {"path": path, "error": "not_a_directory"})
        return f"[erreur] Repertoire introuvable : {path}"

    dir_count = 0
    file_count = 0
    try:
        result = []
        for root, dirs, files in os.walk(search_path):
            dir_count += len(dirs)
            file_count += len(files)
            level = root.replace(str(search_path), '').count(os.sep)
            indent = ' ' * 2 * level
            rel_root = os.path.relpath(root, search_path)
            if rel_root == '.':
                result.append(f"{os.path.basename(search_path)}/")
            else:
                result.append(f"{indent}{os.path.basename(root)}/")

            subindent = ' ' * 2 * (level + 1)
            for file in files:
                result.append(f"{subindent}{file}")

        output = "\n".join(result) if result else "(repertoire vide)"
        record_metric("tree_success", 1, "count", {
            "path": path,
            "directories": dir_count,
            "files": file_count
        })
        return output
    except Exception as e:
        record_metric("tree_error", 1, "count", {"path": path, "error": str(e)})
        return f"[erreur] Erreur lors de la generation de l'arborescence: {e}"


@profile("cd")
def cd(path: str, **_) -> str:
    """Change le repertoire de travail courant."""
    target_path = _safe_path(path)
    if not target_path.exists():
        record_metric("cd_error", 1, "count", {"path": path, "error": "not_found"})
        return f"[erreur] Repertoire introuvable : {path}"
    if not target_path.is_dir():
        record_metric("cd_error", 1, "count", {"path": path, "error": "not_a_directory"})
        return f"[erreur] {path} n'est pas un repertoire"

    try:
        os.chdir(target_path)
        record_metric("cd_success", 1, "count", {"path": path, "new_cwd": os.getcwd()})
        return f"[ok] Repertoire de travail change vers : {os.getcwd()}"
    except Exception as e:
        record_metric("cd_error", 1, "count", {"path": path, "error": str(e)})
        return f"[erreur] Impossible de changer de repertoire: {e}"


@profile("project_info")
def project_info(**_) -> str:
    """Fournit des informations sur le projet actuel."""
    try:
        cwd = os.getcwd()
        info = []
        info.append(f"Repertoire de travail: {cwd}")

        # Verifier si c'est un depot Git
        git_dir = os.path.join(cwd, '.git')
        if os.path.exists(git_dir):
            info.append("Depot Git detecte: Oui")
            try:
                # Obtenir la branche actuelle
                result = subprocess.run(['git', 'branch', '--show-current'],
                                      capture_output=True, text=True, cwd=cwd, timeout=5)
                if result.returncode == 0:
                    branch = result.stdout.strip()
                    if branch:
                        info.append(f"Branche Git actuelle: {branch}")
            except:
                pass
        else:
            info.append("Depot Git detecte: Non")

        # Compter les fichiers et dossiers
        file_count = 0
        dir_count = 0
        try:
            for root, dirs, files in os.walk(cwd):
                # Ignorer le dossier .git pour le comptage
                if '.git' in root.split(os.sep):
                    continue
                dir_count += len(dirs)
                file_count += len(files)
        except:
            pass

        info.append(f"Nombre de dossiers: {dir_count}")
        info.append(f"Nombre de fichiers: {file_count}")

        # Verifier la presence de fichiers courants
        common_files = ['README.md', 'README.txt', 'README', 'requirements.txt', 'setup.py', 'package.json', 'Cargo.toml']
        found_files = [f for f in common_files if os.path.exists(os.path.join(cwd, f))]
        if found_files:
            info.append(f"Fichiers importants detectes: {', '.join(found_files)}")

        record_metric("project_info_success", 1, "count", {"cwd": cwd})
        return "[info] " + "\n[info] ".join(info)
    except Exception as e:
        record_metric("project_info_error", 1, "count", {"error": str(e)})
        return f"[erreur] Erreur lors de la recuperation des informations du projet: {e}"


@profile("run_background")
@_shell_tool("shell (fond)")
def run_background(command: str, **_) -> str:
    """Lance une commande en arriere-plan et retourne immédiatement le PID."""
    try:
        # Utiliser START /B pour lancer en arriere-plan sur Windows
        # Ou nohup & sur Unix
        if os.name == 'nt':  # Windows
            full_command = f'start /b "" {command}'
        else:  # Unix/Linux/MacOS
            full_command = f"{command} &"

        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        record_metric("run_background_success", 1, "count", {"command": command})
        return f"[ok] Commande lancee en arriere-plan\n{result.stdout}"
    except subprocess.TimeoutExpired:
        record_metric("run_background_timeout", 1, "count", {"command": command, "timeout": 5})
        return "[erreur] Commande interrompue (timeout 5s)"
    except Exception as e:
        record_metric("run_background_error", 1, "count", {"command": command, "error": str(e)})
        return f"[erreur] Impossible de lancer la commande en arriere-plan: {e}"


@profile("kill_process")
def kill_process(pid: str, **_) -> str:
    """Tue un processus par son PID."""
    try:
        pid_int = int(pid)
        if os.name == 'nt':  # Windows
            result = subprocess.run(
                f"taskkill /PID {pid_int} /F",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
        else:  # Unix/Linux/MacOS
            result = subprocess.run(
                f"kill -9 {pid_int}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

        if result.returncode == 0:
            record_metric("kill_process_success", 1, "count", {"pid": pid})
            return f"[ok] Processus {pid} termine"
        else:
            record_metric("kill_process_failed", 1, "count", {"pid": pid, "returncode": result.returncode, "stderr": result.stderr})
            return f"[erreur] Impossible de tuer le processus {pid}: {result.stderr}"
    except ValueError:
        record_metric("kill_process_value_error", 1, "count", {"pid": pid, "error": "invalid"})
        return f"[erreur] PID invalide: {pid}"
    except subprocess.TimeoutExpired:
        record_metric("kill_process_timeout", 1, "count", {"pid": pid, "timeout": 10})
        return "[erreur] Commande interrompue (timeout 10s)"
    except Exception as e:
        record_metric("kill_process_error", 1, "count", {"pid": pid, "error": str(e)})
        return f"[erreur] Erreur lors de la termination du processus: {e}"


@profile("run_powershell")
@_shell_tool("powershell")
def run_powershell(command: str, **_) -> str:
    """Execute une commande PowerShell."""
    if os.name != 'nt':
        record_metric("run_powershell_skipped", 1, "count", {"reason": "not_windows", "os": os.name})
        return "[erreur] PowerShell n'est disponible que sur Windows"

    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = (result.stdout + result.stderr).strip()
        record_metric("run_powershell_success", 1, "count", {"command": command, "returncode": result.returncode})
        return f"[code retour {result.returncode}]\n{output}"
    except subprocess.TimeoutExpired:
        record_metric("run_powershell_timeout", 1, "count", {"command": command, "timeout": 30})
        return "[erreur] Commande PowerShell interrompue (timeout 30s)"
    except Exception as e:
        record_metric("run_powershell_error", 1, "count", {"command": command, "error": str(e)})
        return f"[erreur] Impossible d'executer la commande PowerShell: {e}"


@profile("run_cmd")
@_shell_tool("cmd")
def run_cmd(command: str, **_) -> str:
    """Execute une commande CMD Windows."""
    if os.name != 'nt':
        record_metric("run_cmd_skipped", 1, "count", {"reason": "not_windows", "os": os.name})
        return "[erreur] CMD n'est disponible que sur Windows"

    try:
        result = subprocess.run(
            ["cmd", "/c", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        output = (result.stdout + result.stderr).strip()
        record_metric("run_cmd_success", 1, "count", {"command": command, "returncode": result.returncode})
        return f"[code retour {result.returncode}]\n{output}"
    except subprocess.TimeoutExpired:
        record_metric("run_cmd_timeout", 1, "count", {"command": command, "timeout": 30})
        return "[erreur] Commande CMD interrompue (timeout 30s)"
    except Exception as e:
        record_metric("run_cmd_error", 1, "count", {"command": command, "error": str(e)})
        return f"[erreur] Impossible d'executer la commande CMD: {e}"


def _bash_argv(command: str) -> list[str] | None:
    """Trouve un bash utilisable, y compris sous Windows.

    Git Bash installe `bash.exe` dans le PATH ; a defaut, WSL peut en fournir
    un. Renvoie None si aucun n'est disponible.
    """
    bash = shutil.which("bash")
    if bash:
        return [bash, "-c", command]
    if os.name == "nt" and shutil.which("wsl"):
        return ["wsl", "bash", "-c", command]
    return None


@profile("run_bash")
@_shell_tool("bash")
def run_bash(command: str, **_) -> str:
    """Execute une commande Bash."""
    argv = _bash_argv(command)
    if argv is None:
        record_metric("run_bash_skipped", 1, "count", {"reason": "no_bash", "os": os.name})
        return ("[erreur] Aucun bash trouve. Sous Windows, installe Git Bash "
                "ou WSL ; sinon utilise run_powershell ou run_cmd.")

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = (result.stdout + result.stderr).strip()
        record_metric("run_bash_success", 1, "count", {"command": command, "returncode": result.returncode})
        return f"[code retour {result.returncode}]\n{output}"
    except subprocess.TimeoutExpired:
        record_metric("run_bash_timeout", 1, "count", {"command": command, "timeout": 30})
        return "[erreur] Commande Bash interrompue (timeout 30s)"
    except Exception as e:
        record_metric("run_bash_error", 1, "count", {"command": command, "error": str(e)})
        return f"[erreur] Impossible d'executer la commande Bash: {e}"


@profile("start_process")
def start_process(command: str, **_) -> str:
    """Demarre un nouveau processus et retourne ses informations."""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        record_metric("start_process_success", 1, "count", {"command": command, "pid": process.pid})
        return f"[ok] Processus demarre avec PID: {process.pid}"
    except Exception as e:
        record_metric("start_process_error", 1, "count", {"command": command, "error": str(e)})
        return f"[erreur] Impossible de demarrer le processus: {e}"


@profile("stop_process")
def stop_process(pid: str, **_) -> str:
    """Arrete un processus par son PID."""
    record_metric("stop_process_call", 1, "count", {"pid": pid})
    return kill_process(pid)  # Reutiliser la fonction kill_process


@profile("list_processes")
def list_processes(**_) -> str:
    """Liste les processus en cours d'exécution."""
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:  # Unix/Linux/MacOS
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=10
            )

        if result.returncode == 0:
            record_metric("list_processes_success", 1, "count", {"os": os.name if os.name == 'nt' else 'unix', "output_length": len(result.stdout)})
            return f"[ok] Liste des processus:\n{result.stdout}"
        else:
            record_metric("list_processes_error", 1, "count", {"os": os.name if os.name == 'nt' else 'unix', "returncode": result.returncode, "stderr": result.stderr})
            return f"[erreur] Impossible de lister les processus: {result.stderr}"
    except subprocess.TimeoutExpired:
        record_metric("list_processes_timeout", 1, "count", {})
        return "[erreur] Commande interrompue (timeout 10s)"
    except Exception as e:
        record_metric("list_processes_error", 1, "count", {"error": str(e)})
        return f"[erreur] Erreur lors de la liste des processus: {e}"


@profile("get_process")
def get_process(pid: str, **_) -> str:
    """Obtient les informations d'un processus spécifique."""
    try:
        pid_int = int(pid)
        if os.name == 'nt':  # Windows
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid_int}"],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:  # Unix/Linux/MacOS
            result = subprocess.run(
                ["ps", "-p", str(pid_int), "-o", "pid,ppid,cmd,%mem,%cpu"],
                capture_output=True,
                text=True,
                timeout=10
            )

        if result.returncode == 0:
            output = result.stdout.strip()
            if "INFO:" in output or not output or "No tasks are running" in output:
                record_metric("get_process_not_found", 1, "count", {"pid": pid})
                return f"[erreur] Aucun processus trouve avec PID {pid}"
            else:
                record_metric("get_process_success", 1, "count", {"pid": pid, "os": os.name if os.name == 'nt' else 'unix', "output_length": len(output)})
                return f"[ok] Informations sur le processus {pid}:\n{output}"
        else:
            record_metric("get_process_error", 1, "count", {"pid": pid, "os": os.name if os.name == 'nt' else 'unix', "returncode": result.returncode, "stderr": result.stderr})
            return f"[erreur] Impossible d'obtenir les informations du processus {pid}: {result.stderr}"
    except ValueError:
        record_metric("get_process_value_error", 1, "count", {"pid": pid, "error": "invalid"})
        return f"[erreur] PID invalide: {pid}"
    except subprocess.TimeoutExpired:
        record_metric("get_process_timeout", 1, "count", {"pid": pid, "timeout": 10})
        return "[erreur] Commande interrompue (timeout 10s)"
    except Exception as e:
        record_metric("get_process_exception", 1, "count", {"pid": pid, "error": str(e)})
        return f"[erreur] Erreur lors de la recuperation des informations du processus: {e}"


@profile("get_services")
def get_services(**_) -> str:
    """Liste les services du système."""
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(
                ["wmic", "service", "get", "name,state,startmode"],
                capture_output=True,
                text=True,
                timeout=15
            )
        else:  # Unus/Linux/MacOS
            # Essayer systemctl d'abord (systemd), puis service
            result = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--state=running"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode != 0:
                # Fallback sur service --status-all
                result = subprocess.run(
                    ["service", "--status-all"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                record_metric("get_services_not_found", 1, "count", {"os": os.name if os.name == 'nt' else 'unix'})
                return f"[info] Aucun service trouvé"
            else:
                record_metric("get_services_success", 1, "count", {"os": os.name if os.name == 'nt' else 'unix', "output_length": len(output)})
                return f"[ok] Liste des services:\n{output}"
        else:
            record_metric("get_services_error", 1, "count", {"os": os.name if os.name == 'nt' else 'unix', "returncode": result.returncode, "stderr": result.stderr})
            return f"[erreur] Impossible de lister les services: {result.stderr}"
    except subprocess.TimeoutExpired:
        record_metric("get_services_timeout", 1, "count", {"timeout": 15})
        return "[erreur] Commande interrompue (timeout 15s)"
    except Exception as e:
        record_metric("get_services_exception", 1, "count", {"error": str(e)})
        return f"[erreur] Erreur lors de la liste des services: {e}"


def get_environment(**_) -> str:
    """Retourne les variables d'environnement."""
    try:
        env_vars = []
        for key, value in sorted(os.environ.items()):
            # Masquer les valeurs sensibles
            if any(sensitive in key.lower() for sensitive in ['key', 'token', 'secret', 'password', 'pass']):
                display_value = "***MASQUE***"
            else:
                display_value = value
            env_vars.append(f"{key}={display_value}")

        return f"[ok] Variables d'environnement:\n" + "\n".join(env_vars)
    except Exception as e:
        return f"[erreur] Erreur lors de la recuperation des variables d'environnement: {e}"


def set_environment(variable: str, value: str, **_) -> str:
    """Définit une variable d'environnement (pour la session courante uniquement)."""
    try:
        if "=" not in variable:
            # Si c'est juste le nom de la variable
            os.environ[variable] = value
        else:
            # Si c'est au format VAR=value
            var, val = variable.split("=", 1)
            os.environ[var] = val

        return f"[ok] Variable d'environnement definie: {variable}={value if '=' not in variable else variable.split('=',1)[1]}"
    except Exception as e:
        return f"[erreur] Impossible de definir la variable d'environnement: {e}"


def current_directory(**_) -> str:
    """Retourne le répertoire de travail courant."""
    try:
        cwd = os.getcwd()
        return f"[ok] Répertoire courant: {cwd}"
    except Exception as e:
        return f"[erreur] Impossible d'obtenir le répertoire courant: {e}"


def change_directory(path: str, **_) -> str:
    """Change le répertoire de travail courant."""
    try:
        p = _safe_path(path)
        if not p.exists():
            return f"[erreur] Le chemin n'existe pas: {path}"
        if not p.is_dir():
            return f"[erreur] Le chemin n'est pas un répertoire: {path}"

        os.chdir(p)
        return f"[ok] Répertoire changé pour: {p}"
    except Exception as e:
        return f"[erreur] Impossible de changer de répertoire: {e}"


def git_status(**_) -> str:
    """Affiche l'état du dépôt Git actuel."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return "[ok] Dépôt Git propre - aucun changement"
            return f"[ok] État du dépôt Git:\n{output}"
        else:
            return f"[erreur] Impossible d'obtenir l'état du dépôt Git: {result.stderr}"
    except FileNotFoundError:
        return "[erreur] Git n'est pas installé ou pas dans le PATH"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande Git interrompue (timeout 10s)"
    except Exception as e:
        return f"[erreur] Erreur lors de la vérification de l'état Git: {e}"


def git_diff(file_path: str = "", **_) -> str:
    """Affiche les différences dans le dépôt Git ou dans un fichier spécifique."""
    try:
        cmd = ["git", "diff"]
        if file_path:
            cmd.append(file_path)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return "[ok] Aucune différence détectée"
            return f"[ok] Différences Git:\n{output}"
        else:
            return f"[erreur] Impossible de récupérer les différences Git: {result.stderr}"
    except FileNotFoundError:
        return "[erreur] Git n'est pas installé ou pas dans le PATH"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande Git interrompue (timeout 15s)"
    except Exception as e:
        return f"[erreur] Erreur lors de la comparaison Git: {e}"


def git_add(files: str = ".", **_) -> str:
    """Ajoute des fichiers à l'index Git."""
    try:
        file_list = [f.strip() for f in files.split(",")] if files else ["."]
        cmd = ["git", "add"] + file_list

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            return f"[ok] Fichiers ajoutés à l'index Git: {', '.join(file_list)}"
        else:
            return f"[erreur] Échec de l'ajout aux fichiers Git: {result.stderr}"
    except FileNotFoundError:
        return "[erreur] Git n'est pas installé ou pas dans le PATH"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande Git interrompue (timeout 15s)"
    except Exception as e:
        return f"[erreur] Erreur lors de l'ajout aux fichiers Git: {e}"


def git_commit(message: str, **_) -> str:
    """Enregistre les changements dans le dépôt Git avec un message."""
    if not message.strip():
        return "[erreur] Le message de commit ne peut pas être vide"

    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            return f"[ok] Commit effectué avec succès:\n{output}"
        else:
            # Vérifier si c'est juste parce qu'il n'y a rien à committer
            if "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
                return "[ok] Aucun changement à commiter"
            return f"[erreur] Échec du commit Git: {result.stderr}"
    except FileNotFoundError:
        return "[erreur] Git n'est pas installé ou pas dans le PATH"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande Git interrompue (timeout 15s)"
    except Exception as e:
        return f"[erreur] Erreur lors du commit Git: {e}"


def git_log(limit: str = "10", **_) -> str:
    """Affiche l'historique des commits du dépôt Git."""
    try:
        limit_int = int(limit) if limit.isdigit() else 10
        result = subprocess.run(
            ["git", "log", f"-{limit_int}", "--oneline"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return "[ok] Aucun commit dans l'historique"
            return f"[ok] Historique des commits Git:\n{output}"
        else:
            return f"[erreur] Impossible de récupérer l'historique Git: {result.stderr}"
    except ValueError:
        return "[erreur] Limite invalide pour l'historique Git"
    except FileNotFoundError:
        return "[erreur] Git n'est pas installé ou pas dans le PATH"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande Git interrompue (timeout 10s)"
    except Exception as e:
        return f"[erreur] Erreur lors de la récupération de l'historique Git: {e}"


def git_branch(**_) -> str:
    """Liste les branches du dépôt Git."""
    try:
        result = subprocess.run(
            ["git", "branch"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return "[ok] Aucune branche trouvée"
            return f"[ok] Branches Git:\n{output}"
        else:
            return f"[erreur] Impossible de lister les branches Git: {result.stderr}"
    except FileNotFoundError:
        return "[erreur] Git n'est pas installé ou pas dans le PATH"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande Git interrompue (timeout 10s)"
    except Exception as e:
        return f"[erreur] Erreur lors de la liste des branches Git: {e}"


def git_checkout(branch: str, **_) -> str:
    """Change de branche ou restaure des fichiers dans le dépôt Git."""
    if not branch.strip():
        return "[erreur] Le nom de branche ne peut pas être vide"

    try:
        result = subprocess.run(
            ["git", "checkout", branch],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            return f"[ok] Changement de branche effectué avec succès vers: {branch}"
        else:
            return f"[erreur] Échec du changement de branche: {result.stderr}"
    except FileNotFoundError:
        return "[erreur] Git n'est pas installé ou pas dans le PATH"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande Git interrompue (timeout 15s)"
    except Exception as e:
        return f"[erreur] Erreur lors du changement de branche Git: {e}"


def run_tests(test_cmd: str = "", **_) -> str:
    """Exécute les tests du projet."""
    try:
        if not test_cmd.strip():
            # Essayer quelques commandes de test courantes
            test_commands = [
                ["python", "-m", "pytest"],
                ["python", "-m", "unittest", "discover"],
                ["npm", "test"],
                ["yarn", "test"],
                ["cargo", "test"],
                ["mvn", "test"]
            ]

            for cmd in test_commands:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        return f"[ok] Tests exécutés avec succès avec {' '.join(cmd)}:\n{result.stdout}"
                    # Continuer à essayer d'autres commandes même si celle-ci échoue
                except FileNotFoundError:
                    continue  # Essayer la prochaine commande
                except subprocess.TimeoutExpired:
                    return f"[erreur] Timeout lors de l'exécution des tests avec {' '.join(cmd)} (30s)"

            return "[info] Aucune commande de test reconnue trouvée ou tous les tests ont échoué"
        else:
            # Utiliser la commande spécifiée
            result = subprocess.run(
                test_cmd.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return f"[ok] Tests exécutés avec succès:\n{result.stdout}"
            else:
                return f"[erreur] Échec des tests:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande de test interrompue (timeout 30s)"
    except Exception as e:
        return f"[erreur] Erreur lors de l'exécution des tests: {e}"


def lint(file_path: str = "", **_) -> str:
    """Exécute l'analyse statique du code (linting) sur un fichier ou un projet."""
    try:
        if not file_path.strip():
            # Essayer quelques linters courants
            linters = [
                (["flake8", "."], "flake8"),
                (["pylint", "."], "pylint"),
                (["eslint", "."], "eslint"),
                (["jshint", "."], "jshint"),
                (["rustc", "+clippy"], "clippy")
            ]

            for cmd, name in linters:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    # Pour certains linters, un code de sortie != 0 ne signifie pas forcément une erreur
                    # mais juste qu'il y a des problèmes détectés
                    if result.returncode in [0, 1]:  # 0 = succès, 1 = problèmes trouvés
                        output = result.stdout.strip()
                        if not output and result.stderr:
                            output = result.stderr.strip()
                        if output:
                            return f"[ok] Analyse {name} terminée:\n{output}"
                        else:
                            return f"[ok] Analyse {name} terminée - aucun problème détecté"
                except FileNotFoundError:
                    continue  # Essayer le prochain linter
                except subprocess.TimeoutExpired:
                    return f"[erreur] Timeout lors de l'analyse avec {name} (30s)"

            return "[info] Aucun linter reconnu trouvé"
        else:
            # Linter sur un fichier spécifique
            result = subprocess.run(
                ["flake8", file_path],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode in [0, 1]:
                output = result.stdout.strip()
                if not output and result.stderr:
                    output = result.stderr.strip()
                if output:
                    return f"[ok] Analyse flake8 de {file_path}:\n{output}"
                else:
                    return f"[ok] Analyse flake8 de {file_path} terminée - aucun problème détecté"
            else:
                return f"[erreur] Échec de l'analyse de {file_path}: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande de linting interrompue (timeout 30s)"
    except Exception as e:
        return f"[erreur] Erreur lors de l'analyse statique du code: {e}"


def format_code(file_path: str = "", **_) -> str:
    """Formate le code selon les conventions du projet."""
    try:
        if not file_path.strip():
            # Essayer quelques formateurs courants
            formatters = [
                (["black", "."], "black"),
                (["autopep8", "-r", "."], "autopep8"),
                (["prettier", "--write", "."], "prettier"),
                (["gofmt", "-w", "."], "gofmt"),
                (["rustfmt"], "rustfmt")
            ]

            for cmd, name in formatters:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        output = result.stdout.strip()
                        if not output and result.stderr:
                            output = result.stderr.strip()
                        if output:
                            return f"[ok] Formatage {name} terminé:\n{output}"
                        else:
                            return f"[ok] Formatage {name} terminé avec succès"
                    else:
                        # Certains formateurs retournent un code != 0 même en cas de succès
                        # Si stdout/stderr sont vides, considérer comme succès
                        if not result.stdout.strip() and not result.stderr.strip():
                            return f"[ok] Formatage {name} terminé avec succès"
                except FileNotFoundError:
                    continue  # Essayer le prochain formateur
                except subprocess.TimeoutExpired:
                    return f"[erreur] Timeout lors du formatage avec {name} (30s)"

            return "[info] Aucun formateur reconnu trouvé"
        else:
            # Formater un fichier spécifique
            result = subprocess.run(
                ["black", file_path],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if not output and result.stderr:
                    output = result.stderr.strip()
                if output:
                    return f"[ok] Formatage black de {file_path}:\n{output}"
                else:
                    return f"[ok] Formatage black de {file_path} terminé avec succès"
            else:
                return f"[erreur] Échec du formatage de {file_path}: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande de formatage interrompue (timeout 30s)"
    except Exception as e:
        return f"[erreur] Erreur lors du formatage du code: {e}"


def install_dependencies(package_manager: str = "", **_) -> str:
    """Installe les dépendances du projet."""
    try:
        if not package_manager.strip():
            # Détecter automatiquement le gestionnaire de paquets
            cwd = os.getcwd()
            managers = [
                (["pip", "install", "-r", "requirements.txt"], "pip", "requirements.txt"),
                (["pip", "install", "-r", "requirements.pip"], "pip", "requirements.pip"),
                (["npm", "install"], "npm", "package.json"),
                (["yarn", "install"], "yarn", "package.json"),
                (["pipenv", "install", "--dev"], "pipenv", "Pipfile"),
                (["poetry", "install"], "poetry", "pyproject.toml"),
                (["conda", "install", "--file", "requirements.txt"], "conda", "requirements.txt"),
                (["cargo", "fetch"], "cargo", "Cargo.toml")
            ]

            for cmd, name, marker in managers:
                marker_path = os.path.join(cwd, marker)
                if os.path.exists(marker_path):
                    try:
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=60  # Plus long pour l'installation
                        )
                        if result.returncode == 0:
                            output = result.stdout.strip()
                            if not output and result.stderr:
                                output = result.stderr.strip()
                            if output:
                                return f"[ok] Installation des dépendances avec {name} terminée:\n{output}"
                            else:
                                return f"[ok] Installation des dépendances avec {name} terminée avec succès"
                        else:
                            return f"[erreur] Échec de l'installation avec {name}: {result.stderr}"
                    except FileNotFoundError:
                        continue  # Essayer le prochain gestionnaire
                    except subprocess.TimeoutExpired:
                        return f"[erreur] Timeout lors de l'installation avec {name} (60s)"

            return "[info] Aucun fichier de dépendances reconnu trouvé"
        else:
            # Utiliser le gestionnaire spécifié
            result = subprocess.run(
                package_manager.split(),
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return f"[ok] Installation des dépendances terminée:\n{result.stdout}"
            else:
                return f"[erreur] Échec de l'installation des dépendances:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "[erreur] Commande d'installation interrompue (timeout 60s)"
    except Exception as e:
        return f"[erreur] Erreur lors de l'installation des dépendances: {e}"


def ping(host: str, count: str = "4", **_) -> str:
    """Envoie des requêtes ICMP Echo Request vers un hôte."""
    try:
        count_int = int(count) if count.isdigit() else 4
        if count_int < 1 or count_int > 20:
            return "[erreur] Le nombre de paquets doit être entre 1 et 20"

        if os.name == 'nt':  # Windows
            cmd = ["ping", "-n", str(count_int), host]
        else:  # Unix/Linux/MacOS
            cmd = ["ping", "-c", str(count_int), host]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10 + count_int * 2  # Timeout basé sur le nombre de paquets
        )

        if result.returncode == 0:
            return f"[ok] Ping vers {host} réussi:\n{result.stdout}"
        else:
            # Même si ping échoue, on peut avoir reçu une réponse partielle
            output = result.stdout.strip()
            if not output:
                output = result.stderr.strip()
            if output:
                return f"[info] Ping vers {host} terminé avec des erreurs:\n{output}"
            else:
                return f"[erreur] Ping vers {host} échoué: {result.stderr}"
    except ValueError:
        return "[erreur] Nombre de paquets invalide"
    except subprocess.TimeoutExpired:
        return f"[erreur] Timeout du ping vers {host} (dépassé {10 + count_int * 2}s)"
    except Exception as e:
        return f"[erreur] Erreur lors du ping vers {host}: {e}"


def dns_lookup(hostname: str, **_) -> str:
    """Effectue une recherche DNS pour résoudre un nom d'hôte en adresse IP."""
    try:
        # Supprimer le protocole si présent
        hostname = hostname.replace("http://", "").replace("https://", "")
        # Supprimer le chemin si présent
        hostname = hostname.split("/")[0]

        if not hostname:
            return "[erreur] Nom d'hôte vide"

        # Résoudre l'adresse IP
        ip_address = socket.gethostbyname(hostname)
        return f"[ok] Résolution DNS de {hostname}: {ip_address}"
    except socket.gaierror as e:
        return f"[erreur] Impossible de résoudre le nom d'hôte '{hostname}': {e}"
    except Exception as e:
        return f"[erreur] Erreur lors de la résolution DNS: {e}"


def curl(url: str, method: str = "GET", headers: str = "", data: str = "", **_) -> str:
    """Effectue une requête HTTP simile à la commande curl."""
    try:
        # Validation de l'URL
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        # Préparer la requête
        req = urllib.request.Request(url)

        # Méthode HTTP
        req.method = method.upper()

        # En-têtes personnalisés
        if headers:
            try:
                for line in headers.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        req.add_header(key.strip(), value.strip())
            except Exception:
                return "[erreur] Format d'en-tête invalide (attendu: 'Clé: Valeur')"

        # Données pour POST/PUT
        data_bytes = None
        if data and method.upper() in ["POST", "PUT", "PATCH"]:
            data_bytes = data.encode('utf-8')
            req.data = data_bytes

        # Effectuer la requête
        response = urllib.request.urlopen(req, timeout=30)
        content = response.read().decode('utf-8', errors='replace')
        status_code = response.getcode()
        headers_info = dict(response.headers)

        result = f"[ok] Statut HTTP: {status_code}\n"
        result += f"URL: {url}\n"
        if headers_info:
            result += "En-têtes de réponse:\n"
            for key, value in headers_info.items():
                result += f"  {key}: {value}\n"
        result += f"\nContenu ({len(content)} caractères):\n{content[:500]}"
        if len(content) > 500:
            result += "\n... (contenu tronqué)"

        return result
    except urllib.error.HTTPError as e:
        return f"[erreur] Erreur HTTP {e.code}: {e.reason}\n{ e.read().decode('utf-8', errors='replace') if e.read() else '' }"
    except urllib.error.URLError as e:
        return f"[erreur] Erreur d'URL: {e.reason}"
    except Exception as e:
        return f"[erreur] Erreur lors de la requête HTTP: {e}"


def download(url: str, filename: str = "", **_) -> str:
    """Télécharge un fichier depuis une URL."""
    try:
        import urllib.request

        # Validation de l'URL
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        # Déterminer le nom de fichier
        if not filename:
            # Essayer d'extraire le nom de fichier de l'URL
            parsed = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename or "." not in filename:
                filename = "downloaded_file"

        # Chemin complet du fichier
        filepath = _safe_path(filename)
        _ensure_parent_exists(filepath)

        # Télécharger le fichier
        def progress_hook(count, block_size, total_size):
            pass  # On pourrait afficher la progression ici, mais on garde simple

        urllib.request.urlretrieve(url, str(filepath))

        # Vérifier la taille du fichier téléchargé
        file_size = os.path.getsize(filepath)
        return f"[ok] Téléchargement terminé: {url}\nFichier sauvegardé: {filepath}\nTaille: {file_size} octets"
    except Exception as e:
        return f"[erreur] Échec du téléchargement depuis {url}: {e}"


def upload(file_path: str, url: str, **_) -> str:
    """Télécharge un fichier vers une URL (simplifié - nécessite un endpoint compatible)."""
    try:
        import urllib.request
        import urllib.error

        # Vérifier que le fichier existe
        filepath = _safe_path(file_path)
        if not filepath.is_file():
            return f"[erreur] Fichier introuvable: {file_path}"

        # Validation de l'URL
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        # Lire le fichier
        with open(filepath, 'rb') as f:
            file_data = f.read()

        # Préparer la requête POST
        req = urllib.request.Request(url, data=file_data)
        req.add_header('Content-Type', 'application/octet-stream')
        req.add_header('Content-Length', str(len(file_data)))
        # Quelques en-têtes utiles
        req.add_header('User-Agent', 'GLM-Code-Upload-Agent/1.0')

        # Effectuer l'upload
        response = urllib.request.urlopen(req, timeout=30)
        content = response.read().decode('utf-8', errors='replace')
        status_code = response.getcode()

        return f"[ok] Upload réussi vers {url}\nStatut HTTP: {status_code}\nRéponse: {content[:200]}{'...' if len(content) > 200 else ''}"
    except urllib.error.HTTPError as e:
        return f"[erreur] Erreur HTTP {e.code} lors de l'upload: {e.reason}"
    except Exception as e:
        return f"[erreur] Échec de l'upload vers {url}: {e}"


# Fonctions Internet (aliases pour des noms plus intuitifs)
def fetch_url(url: str, **_) -> str:
    """Récupère le contenu d'une URL (équivalent à curl avec méthode GET)."""
    return curl(url, method="GET", **_)


def download_file(url: str, filename: str = "", **_) -> str:
    """Télécharge un fichier (alias pour download)."""
    return download(url, filename, **_)


def web_search(query: str, **_) -> str:
    """Effectue une recherche web (simulée - nécessite une API externe pour être réellement utile)."""
    return f"[info] Fonction de recherche web non implémentée dans cette version. Pour une recherche réelle, vous auriez besoin d'intégrer une API de recherche comme Google Custom Search, Bing Search API, etc.\n\nQuery: {query}\n\nSuggestion: Utilisez plutôt la fonction 'curl' pour interroger directement une API de recherche si vous en avez accès."


TOOL_IMPLS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_dir": list_dir,
    "run_command": run_command,
    "append_file": append_file,
    "copy_file": copy_file,
    "move_file": move_file,
    "rename_file": rename_file,
    "create_file": create_file,
    "create_dir": create_dir,
    "delete_dir": delete_dir,
    "find_files": find_files,
    "glob": glob,
    "file_exists": file_exists,
    "read_multiple_files": read_multiple_files,
    "write_multiple_files": write_multiple_files,
    "replace_text": replace_text,
    "replace_regex": replace_regex,
    "grep": grep,
    "search_text": search_text,
    "search_regex": search_regex,
    "find_symbol": find_symbol,
    # Project
    "pwd": pwd,
    "tree": tree,
    "cd": cd,
    "project_info": project_info,
    # Terminal
    "run_background": run_background,
    "kill_process": kill_process,
    # PowerShell
    "run_powershell": run_powershell,
    "run_cmd": run_cmd,
    "run_bash": run_bash,
    "start_process": start_process,
    "stop_process": stop_process,
    "list_processes": list_processes,
    "get_process": get_process,
    "get_services": get_services,
    "get_environment": get_environment,
    "set_environment": set_environment,
    "current_directory": current_directory,
    "change_directory": change_directory,
    # Development
    "git_status": git_status,
    "git_diff": git_diff,
    "git_add": git_add,
    "git_commit": git_commit,
    "git_log": git_log,
    "git_branch": git_branch,
    "git_checkout": git_checkout,
    "run_tests": run_tests,
    "lint": lint,
    "format_code": format_code,
    "install_dependencies": install_dependencies,
    # Network
    "ping": ping,
    "dns_lookup": dns_lookup,
    "curl": curl,
    "download": download,
    "upload": upload,
    # Internet
    "fetch_url": fetch_url,
    "download_file": download_file,
    "web_search": web_search,
}

# Outils qui nécessitent une confirmation utilisateur.
DESTRUCTIVE_TOOLS = {
    "write_file",
    "edit_file",
    "run_command",
    "append_file",
    "copy_file",
    "move_file",
    "rename_file",
    "create_file",
    "create_dir",
    "delete_dir",
    "write_multiple_files",
    "replace_text",
    "replace_regex",
    "run_background",
    "kill_process",
    "start_process",
    "stop_process",
    "set_environment",
    "git_add",
    "git_commit",
    "install_dependencies",
    "download",
    "upload",
    "download_file",
    "curl",
}

# Outils lecture-seule, autorisés en mode plan.
READONLY_TOOLS = {
    "read_file",
    "list_dir",
    "find_files",
    "glob",
    "file_exists",
    "read_multiple_files",
    "grep",
    "search_text",
    "search_regex",
    "find_symbol",
    "pwd",
    "tree",
    "project_info",
    "list_processes",
    "get_process",
    "get_services",
    "get_environment",
    "current_directory",
    "git_status",
    "git_diff",
    "git_log",
    "git_branch",
    "ping",
    "dns_lookup",
    "fetch_url",
    "web_search",
}


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lit et renvoie le contenu texte d'un fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier à lire"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Crée ou remplace entièrement un fichier avec le contenu fourni.",
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
                    "old": {"type": "string", "description": "Texte exact à remplacer (unique)"},
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
            "description": "Liste les fichiers et dossiers d'un répertoire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du répertoire (défaut : .)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Exécute une commande shell et renvoie sa sortie. À utiliser avec prudence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Commande à exécuter"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_file",
            "description": "Ajoute du contenu à la fin d'un fichier existant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier"},
                    "content": {"type": "string", "description": "Contenu à ajouter"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "copy_file",
            "description": "Copie un fichier vers une nouvelle destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Chemin du fichier source"},
                    "destination": {"type": "string", "description": "Chemin de destination"},
                },
                "required": ["source", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Déplace un fichier vers une nouvelle destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Chemin du fichier source"},
                    "destination": {"type": "string", "description": "Chemin de destination"},
                },
                "required": ["source", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rename_file",
            "description": "Renomme un fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier à renommer"},
                    "new_name": {"type": "string", "description": "Nouveau nom du fichier"},
                },
                "required": ["path", "new_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Crée un nouveau fichier vide.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier à créer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_dir",
            "description": "Crée un nouveau répertoire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du répertoire à créer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_dir",
            "description": "Supprime un répertoire et tout son contenu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du répertoire à supprimer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Trouve des fichiers correspondant à un motif dans un répertoire et ses sous-répertoires.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Motif de recherche (ex: *.py)"},
                    "path": {"type": "string", "description": "Chemin du répertoire de recherche (défaut : .)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Trouve des fichiers correspondant à un motif glob dans un répertoire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Motif glob (ex: **/*.py)"},
                    "path": {"type": "string", "description": "Chemin du répertoire de recherche (défaut : .)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_exists",
            "description": "Vérifie si un fichier ou répertoire existe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier ou répertoire à vérifier"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_multiple_files",
            "description": "Lit plusieurs fichiers et retourne leur contenu concaténé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {"type": "string", "description": "Liste de chemins séparés par des virgules"},
                },
                "required": ["paths"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_multiple_files",
            "description": "Écrit plusieurs fichiers à partir d'une correspondance fichier→contenu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_map": {"type": "string", "description": "Correspondance au format 'chemin1:contenu1,chemin2:contenu2,...'"},
                },
                "required": ["file_map"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_text",
            "description": "Remplace toutes les occurrences d'un texte dans un fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier"},
                    "old": {"type": "string", "description": "Texte à remplacer"},
                    "new": {"type": "string", "description": "Nouveau texte"},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_regex",
            "description": "Remplace toutes les occurrences correspondant à une expression régulière.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier"},
                    "pattern": {"type": "string", "description": "Expression régulière"},
                    "replacement": {"type": "string", "description": "Texte de remplacement"},
                },
                "required": ["path", "pattern", "replacement"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Recherche un motif dans les fichiers d'un répertoire (comme la commande grep).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Motif à rechercher"},
                    "path": {"type": "string", "description": "Chemin du répertoire de recherche (défaut : .)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "Recherche du texte littéral dans les fichiers d'un répertoire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Texte à rechercher"},
                    "path": {"type": "string", "description": "Chemin du répertoire de recherche (défaut : .)"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_regex",
            "description": "Recherche une expression régulière dans les fichiers d'un répertoire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Expression régulière à rechercher"},
                    "path": {"type": "string", "description": "Chemin du répertoire de recherche (défaut : .)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_symbol",
            "description": "Trouve un symbole (fonction, classe, etc.) dans les fichiers source.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbole à rechercher (nom de fonction, classe, etc.)"},
                    "path": {"type": "string", "description": "Chemin du répertoire de recherche (défaut : .)"},
                },
                "required": ["symbol"],
            },
        },
    },
    # Project
    {
        "type": "function",
        "function": {
            "name": "pwd",
            "description": "Retourne le répertoire de travail courant.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tree",
            "description": "Affiche l'arborescence d'un répertoire sous forme texte.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du répertoire à afficher (défaut : .)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cd",
            "description": "Change le répertoire de travail courant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du répertoire cible"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "project_info",
            "description": "Fournit des informations sur le projet actuel.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    # Terminal
    {
        "type": "function",
        "function": {
            "name": "run_background",
            "description": "Exécute une commande en arrière-plan et retourne immédiatement le PID du processus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Commande à exécuter en arrière-plan"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kill_process",
            "description": "Tue un processus par son PID ou son nom.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "PID ou nom du processus à tuer"},
                },
                "required": ["identifier"],
            },
        },
    },
    # PowerShell
    {
        "type": "function",
        "function": {
            "name": "run_powershell",
            "description": "Exécute une commande PowerShell et renvoie sa sortie.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Commande PowerShell à exécuter"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_cmd",
            "description": "Exécute une commande Windows CMD et renvoie sa sortie.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Commande CMD à exécuter"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Exécute une commande Bash et renvoie sa sortie (disponible sur WSL ou environnements Unix-like).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Commande Bash à exécuter"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_process",
            "description": "Démarre un processus et retourne ses informations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Commande à exécuter"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_process",
            "description": "Arrête un processus en cours d'exécution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {"type": "string", "description": "ID du processus à arrêter"},
                },
                "required": ["pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_processes",
            "description": "Liste tous les processus en cours d'exécution.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_process",
            "description": "Récupère les informations sur un processus spécifique.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pid": {"type": "string", "description": "ID du processus à interroger"},
                },
                "required": ["pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_services",
            "description": "Liste les services du système (Windows uniquement).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_environment",
            "description": "Récupère les variables d'environnement du processus actuel.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_environment",
            "description": "Définit une variable d'environnement pour la session courante.",
            "parameters": {
                "type": "object",
                "properties": {
                    "variable": {"type": "string", "description": "Nom de la variable d'environnement (ex: PATH ou VAR=value)"},
                    "value": {"type": "string", "description": "Valeur à attribuer (ignorée si variable contient '=')"},
                },
                "required": ["variable"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "current_directory",
            "description": "Retourne le répertoire de travail courant.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "change_directory",
            "description": "Change le répertoire de travail courant (alias pour cd).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du répertoire cible"},
                },
                "required": ["path"],
            },
        },
    },
    # Development
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Affiche l'état du dépôt Git actuel.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Affiche les différences dans le dépôt Git ou dans un fichier spécifique.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Chemin du fichier à comparer (optionnel)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_add",
            "description": "Ajoute des fichiers à l'index Git.",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {"type": "string", "description": "Liste de fichiers séparés par des virgules (défaut: .)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Enregistre les changements dans le dépôt Git avec un message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message de commit"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Affiche l'historique des commits du dépôt Git.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "string", "description": "Nombre de commits à afficher (défaut: 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_branch",
            "description": "Liste les branches du dépôt Git.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_checkout",
            "description": "Change de branche ou restaure des fichiers dans le dépôt Git.",
            "parameters": {
                "type": "object",
                "properties": {
                    "branch": {"type": "string", "description": "Nom de la branche cible"},
                },
                "required": ["branch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Exécute les tests du projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_cmd": {"type": "string", "description": "Commande de test à exécuter (optionnel)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lint",
            "description": "Exécute l'analyse statique du code (linting) sur un fichier ou un projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Chemin du fichier à analyser (optionnel)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "format_code",
            "description": "Formate le code selon les conventions du projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Chemin du fichier à formater (optionnel)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_dependencies",
            "description": "Installe les dépendances du projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_manager": {"type": "string", "description": "Gestionnaire de paquets à utiliser (optionnel)"},
                },
                "required": [],
            },
        },
    },
    # Network
    {
        "type": "function",
        "function": {
            "name": "ping",
            "description": "Teste la connectivité réseau vers un hôte.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Adresse IP ou nom d'hôte à pinger"},
                    "count": {"type": "string", "description": "Nombre de paquets à envoyer (défaut: 4)"},
                },
                "required": ["host"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dns_lookup",
            "description": "Effectue une recherche DNS pour un nom d'hôte.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Nom d'hôte à résoudre"},
                },
                "required": ["hostname"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "curl",
            "description": "Effectue une requête HTTP(S) avec diverses méthodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL cible"},
                    "method": {"type": "string", "description": "Méthode HTTP (GET, POST, PUT, DELETE, etc.)", "default": "GET"},
                    "data": {"type": "string", "description": "Données à envoyer (pour POST/PUT)"},
                    "headers": {"type": "string", "description": "En-têtes HTTP au format 'Clé:Valeur,Clé2:Valeur2'"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "download",
            "description": "Télécharge un fichier depuis une URL vers le système de fichiers local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL du fichier à télécharger"},
                    "filename": {"type": "string", "description": "Nom du fichier local (optionnel)"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "upload",
            "description": "Télécharge un fichier vers un serveur distant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL de destination pour l'upload"},
                    "file_path": {"type": "string", "description": "Chemin du fichier à uploader"},
                },
                "required": ["url", "file_path"],
            },
        },
    },
    # Internet
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Récupère le contenu d'une URL (équivalent à curl avec méthode GET).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL à récupérer"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "download_file",
            "description": "Télécharge un fichier depuis une URL (alias pour download).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL du fichier à télécharger"},
                    "filename": {"type": "string", "description": "Nom du fichier local (optionnel)"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Effectue une recherche web (simulée - retourne des informations sur la façon d'implémenter une recherche réelle).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Terme de recherche"},
                },
                "required": ["query"],
            },
        },
    },
]

# Sous-ensemble exposé en mode plan (aucune action destructive).
READONLY_TOOLS_SCHEMA = [
    t for t in TOOLS_SCHEMA if t["function"]["name"] in READONLY_TOOLS
]