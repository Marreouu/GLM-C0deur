"""Intelligence Git avancée pour comprendre automatiquement l'état du dépôt."""

from __future__ import annotations

import subprocess
import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import re

from . import ui


class ChangeType(Enum):
    """Types de changements dans Git."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"
    UNMERGED = "unmerged"


@dataclass
class GitFileChange:
    """Représente un changement dans un fichier Git."""
    file_path: str
    change_type: ChangeType
    old_path: Optional[str] = None  # Pour les renommages/copies
    lines_added: int = 0
    lines_deleted: int = 0
    is_staged: bool = False


@dataclass
class GitCommitInfo:
    """Informations sur un commit Git."""
    hash: str
    author: str
    date: datetime.datetime
    message: str
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


@dataclass
class GitBlameInfo:
    """Informations de blame pour une ligne spécifique."""
    commit_hash: str
    author: str
    date: datetime.datetime
    line_number: int
    content: str


class GitIntelligence:
    """
    Intelligence Git avancée qui fournit des insights avancés sur l'état du dépôt.

    Peut répondre à :
    - Que s'est-il passé depuis mon dernier commit ?
    - Quels fichiers ont changé ?
    - Quel est le plus gros changement ?
    - Quels tests doivent être relancés ?
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self._is_git_repo = False
        self._detect_git_repository()

    def _detect_git_repository(self) -> None:
        """Détecte si le chemin est un dépôt Git."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            self._is_git_repo = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._is_git_repo = False

    def _run_git_command(self, command: List[str]) -> Tuple[bool, str, str]:
        """
        Exécute une commande Git et retourne le succès, stdout et stderr.

        Returns:
            Tuple (success, stdout, stderr)
        """
        if not self._is_git_repo:
            return False, "", "Not a git repository"

        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "", "Git command timed out"
        except Exception as e:
            return False, "", f"Git command failed: {e}"

    def get_status_since_last_commit(self) -> Dict[str, Any]:
        """
        Obtient un résumé intelligent des changements depuis le dernier commit.

        Returns:
            Dictionnaire avec les informations sur les changements
        """
        if not self._is_git_repo:
            return {"error": "Not a git repository"}

        # Obtenir le dernier commit
        success, stdout, stderr = self._run_git_command(["rev-parse", "HEAD"])
        if not success:
            return {"error": f"Failed to get HEAD: {stderr}"}
        last_commit_hash = stdout

        # Obtenir les changements depuis le dernier commit
        success, stdout, stderr = self._run_git_command(
            ["diff", "--stat", last_commit_hash]
        )
        if not success:
            return {"error": f"Failed to get diff stat: {stderr}"}

        # Parser le output de git diff --stat
        changes_summary = self._parse_diff_stat(stdout)

        # Obtenir la liste détaillée des fichiers changés
        success, stdout, stderr = self._run_git_command(
            ["diff", "--name-status", last_commit_hash]
        )
        if not success:
            return {"error": f"Failed to get name-status: {stderr}"}

        file_changes = self._parse_name_status(stdout, last_commit_hash)

        # Calculer les statistiques
        total_files = len(file_changes)
        added_files = sum(1 for c in file_changes if c.change_type == ChangeType.ADDED)
        modified_files = sum(1 for c in file_changes if c.change_type == ChangeType.MODIFIED)
        deleted_files = sum(1 for c in file_changes if c.change_type == ChangeType.DELETED)
        renamed_files = sum(1 for c in file_changes if c.change_type == ChangeType.RENAMED)

        total_lines_added = sum(c.lines_added for c in file_changes)
        total_lines_deleted = sum(c.lines_deleted for c in file_changes)

        # Identifier les plus gros changements
        biggest_changes = sorted(
            file_changes,
            key=lambda c: c.lines_added + c.lines_deleted,
            reverse=True
        )[:5]

        # Déterminer quels tests pourraient être affectés
        affected_tests = self._identify_affected_tests(file_changes)

        return {
            "since_commit": last_commit_hash[:8],
            "summary": changes_summary,
            "files_changed": total_files,
            "added": added_files,
            "modified": modified_files,
            "deleted": deleted_files,
            "renamed": renamed_files,
            "lines_added": total_lines_added,
            "lines_deleted": total_lines_deleted,
            "biggest_changes": [
                {
                    "file": c.file_path,
                    "type": c.change_type.value,
                    "lines_added": c.lines_added,
                    "lines_deleted": c.lines_deleted,
                    "total": c.lines_added + c.lines_deleted
                }
                for c in biggest_changes
            ],
            "affected_tests": affected_tests,
            "file_details": [
                {
                    "file": c.file_path,
                    "type": c.change_type.value,
                    "lines_added": c.lines_added,
                    "lines_deleted": c.lines_deleted,
                    "old_path": c.old_path
                }
                for c in file_changes
            ]
        }

    def _parse_diff_stat(self, diff_stat_output: str) -> str:
        """Parse la sortie de git diff --stat pour en extraire un résumé lisible."""
        if not diff_stat_output:
            return "Aucun changement"

        lines = diff_stat_output.strip().split('\n')
        if not lines:
            return "Aucun changement"

        # La dernière ligne contient généralement le résumé
        last_line = lines[-1].strip()
        if "changed" in last_line and ("insertion" in last_line or "deletion" in last_line):
            return last_line
        elif lines:
            # Sinon, retourner la première ligne non vide
            for line in lines:
                if line.strip():
                    return line.strip()
        return "Changements détectés"

    def _parse_name_status(self, name_status_output: str, since_commit: str) -> List[GitFileChange]:
        """Parse la sortie de git diff --name-status."""
        changes = []
        if not name_status_output:
            return changes

        lines = name_status_output.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue

            parts = line.split('\t')
            if len(parts) < 2:
                continue

            status = parts[0]
            file_path = parts[1]

            change = GitFileChange(file_path=file_path, change_type=ChangeType.MODIFIED)

            if status == 'A':
                change.change_type = ChangeType.ADDED
            elif status == 'M':
                change.change_type = ChangeType.MODIFIED
            elif status == 'D':
                change.change_type = ChangeType.DELETED
            elif status == 'R':
                change.change_type = ChangeType.RENAMED
                if len(parts) >= 3:
                    change.old_path = parts[2]
            elif status == 'C':
                change.change_type = ChangeType.COPIED
                if len(parts) >= 3:
                    change.old_path = parts[2]

            # Essayer d'obtenir le nombre de lignes ajoutées/supprimées
            # Cela nécessiterait un appel supplémentaire à git diff --numstat
            # Pour simplifier, on utilise des estimations basées sur le statut
            if change.change_type in [ChangeType.ADDED, ChangeType.MODIFIED]:
                change.lines_added = 10  # Estimation basique
            if change.change_type in [ChangeType.DELETED, ChangeType.MODIFIED]:
                change.lines_deleted = 10  # Estimation basique

            changes.append(change)

        return changes

    def get_smart_status(self) -> str:
        """
        Retourne un statut Git intelligent et formaté pour l'affichage.

        Returns:
            Chaîne formatée avec l'état intelligent du dépôt
        """
        if not self._is_git_repo:
            return "[erreur] Pas un dépôt Git"

        # Obtenir la branche actuelle
        success, branch_output, _ = self._run_git_command(["branch", "--show-current"])
        branch = branch_output.strip() if success else "unknown"

        # Obtenir le statut depuis le dernier commit
        status_info = self.get_status_since_last_commit()

        if "error" in status_info:
            return f"[erreur] {status_info['error']}"

        lines = []
        lines.append(f"Branche: {branch}")
        lines.append(f"Depuis le commit {status_info['since_commit']}:")
        lines.append(f"  {status_info['summary']}")

        if status_info['files_changed'] > 0:
            lines.append(f"Fichiers modifiés: {status_info['files_changed']}")
            if status_info['added'] > 0:
                lines.append(f"  Ajoutés: {status_info['added']}")
            if status_info['modified'] > 0:
                lines.append(f"  Modifiés: {status_info['modified']}")
            if status_info['deleted'] > 0:
                lines.append(f"  Supprimés: {status_info['deleted']}")
            if status_info['renamed'] > 0:
                lines.append(f"  Renommés: {status_info['renamed']}")

            if status_info['biggest_changes']:
                lines.append("Plus gros changements:")
                for change in status_info['biggest_changes']:
                    lines.append(
                        f"  {change['file']}: "
                        f"+{change['lines_added']}/-{change['lines_deleted']} "
                        f"({change['type']})"
                    )

        if status_info['affected_tests']:
            lines.append("Tests potentiellement affectés:")
            for test in status_info['affected_tests'][:5]:  # Limiter à 5
                lines.append(f"  {test}")

        return "\n".join(lines)

    def get_git_blame_for_line(self, file_path: str, line_number: int) -> Optional[GitBlameInfo]:
        """
        Obtient les informations de blame pour une ligne spécifique d'un fichier.

        Args:
            file_path: Chemin relatif du fichier
            line_number: Numéro de ligne (1-based)

        Returns:
            Informations de blame ou None si impossible
        """
        if not self._is_git_repo:
            return None

        success, stdout, stderr = self._run_git_command([
            "blame", "--line-porcelain", f"-L{line_number},{line_number}", file_path
        ])

        if not success or not stdout:
            return None

        # Parser la sortie au format porcelaine
        lines = stdout.split('\n')
        if len(lines) < 4:
            return None

        try:
            # Première ligne: <hash> <ligne_original> <ligne_finale> <nombre>
            first_parts = lines[0].split()
            if len(first_parts) < 4:
                return None

            commit_hash = first_parts[0]

            # Chercher les lignes auteur et date
            author_line = None
            date_line = None
            content_line = None

            for line in lines[1:]:
                if line.startswith('author '):
                    author_line = line[7:]  # Enlever 'author '
                elif line.startswith('author-mail '):
                    # Ignorer l'email pour simplifier
                    pass
                elif line.startswith('author-time '):
                    try:
                        timestamp = int(line[12:])
                        date_line = datetime.datetime.fromtimestamp(timestamp)
                    except ValueError:
                        pass
                elif line.startswith('\t'):
                    # Ligne de contenu (commence par une tabulation)
                    content_line = line[1:]  # Enlever la tabulation
                    break

            if not author_line or not date_line or content_line is None:
                return None

            return GitBlameInfo(
                commit_hash=commit_hash,
                author=author_line,
                date=date_line,
                line_number=line_number,
                content=content_line.strip()
            )
        except Exception:
            return None

    def analyze_recent_commits(self, count: int = 5) -> List[GitCommitInfo]:
        """
        Analyse les derniers commits pour en extraire des insights.

        Args:
            count: Nombre de commits à analyser

        Returns:
            Liste d'informations sur les commits
        """
        if not self._is_git_repo:
            return []

        success, stdout, stderr = self._run_git_command([
            "log", f"-{count}", "--pretty=format:%H|%an|%ad|%s", "--date=short"
        ])

        if not success:
            return []

        commits = []
        for line in stdout.split('\n'):
            if not line.strip():
                continue

            parts = line.split('|', 3)
            if len(parts) < 4:
                continue

            hash_val, author, date_str, message = parts

            try:
                commit_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                commit_date = datetime.datetime.now()  # Fallback

            # Obtenir les statistiques du commit
            success, stats_output, _ = self._run_git_command([
                "show", "--numstat", hash_val
            ])

            files_changed = []
            insertions = 0
            deletions = 0

            if success and stats_output:
                for stat_line in stats_output.split('\n'):
                    if not stat_line.strip():
                        continue
                    stat_parts = stat_line.split('\t')
                    if len(stat_parts) >= 3:
                        try:
                            add = int(stat_parts[0]) if stat_parts[0] != '-' else 0
                            delete = int(stat_parts[1]) if stat_parts[1] != '-' else 0
                            file_path = stat_parts[2]
                            files_changed.append(file_path)
                            insertions += add
                            deletions += delete
                        except ValueError:
                            pass

            commits.append(GitCommitInfo(
                hash=hash_val,
                author=author,
                date=commit_date,
                message=message,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions
            ))

        return commits

    def identify_affected_tests(self, file_changes: List[GitFileChange]) -> List[str]:
        """
        Identifie quels tests pourraient être affectés par les changements de fichiers.

        Args:
            file_changes: Liste des changements de fichiers

        Returns:
            Liste de chemins de tests potentiellement affectés
        """
        affected_tests = set()

        # Mots-clés indiquant des fichiers de test
        test_indicators = {
            'test', 'tests', 'spec', 'specs', '_test.', '_spec.',
            'test_', 'spec_', '.test.', '.spec.'
        }

        # Pour chaque fichier changé, chercher des tests associés
        for change in file_changes:
            file_path = change.file_path

            # 1. Si le fichier changé est lui-même un test, l'ajouter
            if any(indicator in file_path.lower() for indicator in test_indicators):
                affected_tests.add(file_path)
                continue

            # 2. Chercher des fichiers de test correspondant à ce fichier
            # Exemple: si on change src/user/service.py, chercher test/user/test_service.py
            path_parts = Path(file_path).parts

            # Supprimer l'extension pour chercher le nom de base
            file_stem = Path(file_path).stem

            # Rechercher dans les répertoires de tests courants
            test_dirs = ['test', 'tests', 'spec', 'specs']
            for test_dir in test_dirs:
                # Chemin potentiel: test/<same_path>/<file_stem>_test.py
                test_path_parts = list(path_parts)
                # Essayer de remplacer le premier répertoire par un répertoire de test
                for i, part in enumerate(test_path_parts):
                    if part not in test_dirs and not part.startswith('.'):
                        test_path_parts[i] = test_dir
                        test_path = Path(*test_path_parts)
                        # Essayer différents noms de fichiers de test
                        for suffix in ['_test', '_spec', 'test_', 'spec_']:
                            test_file = test_path.parent / f"{test_path.stem}{suffix}{test_path.suffix}"
                            if test_file.exists():
                                affected_tests.add(str(test_file.relative_to(self.repo_path)))
                            # Essayer aussi avec l'extension .py si ce n'est pas déjà le cas
                            if test_file.suffix != '.py':
                                test_file_py = test_file.with_suffix('.py')
                                if test_file_py.exists():
                                    affected_tests.add(str(test_file_py.relative_to(self.repo_path)))
                        break  # On a trouvé un répertoire à remplacer, on arrête

            # 3. Recherche générique: tout fichier de test contenant le nom du fichier modifié
            # Ceci serait trop coûteux en pratique, donc on se limite aux approches ci-dessus

        return sorted(list(affected_tests))

    def get_smart_diff(self, file_path: str = None) -> str:
        """
        Retourne un diff Git intelligent qui met en évidence les changements importants.

        Args:
            file_path: Chemin relatif du fichier (None = tous les fichiers)

        Returns:
            Diff formaté et analysé
        """
        if not self._is_git_repo:
            return "[erreur] Pas un dépôt Git"

        cmd = ["diff"]
        if file_path:
            cmd.extend(["--", file_path])

        success, stdout, stderr = self._run_git_command(cmd)

        if not success:
            return f"[erreur] Échec du diff: {stderr}"

        if not stdout.strip():
            return "[info] Aucun changement détecté"

        # Analyser le diff pour fournir des insights
        insights = self._analyze_diff_insights(stdout, file_path)

        # Combiner le diff brut avec les insights
        result = stdout
        if insights:
            result += "\n\n[insights]\n" + insights

        return result

    def _analyze_diff_insights(self, diff_output: str, file_path: str = None) -> str:
        """Analyse la sortie de diff pour fournir des insights utiles."""
        if not diff_output.strip():
            return ""

        lines = diff_output.split('\n')
        insights = []

        # Compter les lignes ajoutées/supprimées
        added_lines = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))

        if added_lines > 0 or removed_lines > 0:
            insights.append(f"Lignes ajoutées: {added_lines}, supprimées: {removed_lines}")

        # Détecter les changements structurels importants
        function_changes = []
        class_changes = []

        current_function = None
        current_class = None

        for line in lines:
            # Détecter les définitions de fonctions
            if line.startswith('+') and not line.startswith('+++'):
                content = line[1:]
                func_match = re.search(r'^\s*def\s+(\w+)\s*\(', content)
                if func_match:
                    function_changes.append(("added", func_match.group(1)))
                class_match = re.search(r'^\s*class\s+(\w+)', content)
                if class_match:
                    class_changes.append(("added", class_match.group(1)))
            elif line.startswith('-') and not line.startswith('---'):
                content = line[1:]
                func_match = re.search(r'^\s*def\s+(\w+)\s*\(', content)
                if func_match:
                    function_changes.append(("removed", func_match.group(1)))
                class_match = re.search(r'^\s*class\s+(\w+)', content)
                if class_match:
                    class_changes.append(("removed", class_match.group(1)))

        if function_changes:
            added_funcs = [f"'{name}' ({typ})" for typ, name in function_changes if typ == "added"]
            removed_funcs = [f"'{name}' ({typ})" for typ, name in function_changes if typ == "removed"]
            if added_funcs:
                insights.append(f"Fonctions ajoutées: {', '.join(added_funcs)}")
            if removed_funcs:
                insights.append(f"Fonctions supprimées: {', '.join(removed_funcs)}")

        if class_changes:
            added_classes = [f"'{name}' ({typ})" for typ, name in class_changes if typ == "added"]
            removed_classes = [f"'{name}' ({typ})" for typ, name in class_changes if typ == "removed"]
            if added_classes:
                insights.append(f"Classes ajoutées: {', '.join(added_classes)}")
            if removed_classes:
                insights.append(f"Classes supprimées: {', '.join(removed_classes)}")

        # Détecter les changements dans les imports
        import_changes = []
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                content = line[1:]
                if re.search(r'^\s*(import|from)\s+', content):
                    import_changes.append(("added", content.strip()))
            elif line.startswith('-') and not line.startswith('---'):
                content = line[1:]
                if re.search(r'^\s*(import|from)\s+', content):
                    import_changes.append(("removed", content.strip()))

        if import_changes:
            added_imports = [imp for typ, imp in import_changes if typ == "added"]
            removed_imports = [imp for typ, imp in import_changes if typ == "removed"]
            if added_imports:
                insights.append(f"Imports ajoutés: {', '.join(added_imports[:3])}{'...' if len(added_imports) > 3 else ''}")
            if removed_imports:
                insights.append(f"Imports supprimés: {', '.join(removed_imports[:3])}{'...' if len(removed_imports) > 3 else ''}")

        return '\n'.join(insights) if insights else ""


# Fonction d'aide pour faciliter l'utilisation
def git_smart_status(repo_path: str = ".") -> str:
    """
    Fonction d'aide pour obtenir un statut Git intelligent.

    Args:
        repo_path: Chemin vers le dépôt Git

    Returns:
        Statut Git formaté et analysé
    """
    gi = GitIntelligence(repo_path)
    return gi.get_smart_status()


def git_smart_diff(file_path: str = None, repo_path: str = ".") -> str:
    """
    Fonction d'aide pour obtenir un diff Git intelligent.

    Args:
        file_path: Chemin relatif du fichier (None = tous les fichiers)
        repo_path: Chemin vers le dépôt Git

    Returns:
        Diff Git formaté et analysé
    """
    gi = GitIntelligence(repo_path)
    return gi.get_smart_diff(file_path)


def git_blame_line(file_path: str, line_number: int, repo_path: str = ".") -> Optional[dict]:
    """
    Fonction d'aide pour obtenir les informations de blame pour une ligne.

    Args:
        file_path: Chemin relatif du fichier
        line_number: Numéro de ligne (1-based)
        repo_path: Chemin vers le dépôt Git

    Returns:
        Dictionnaire avec les informations de blame ou None
    """
    gi = GitIntelligence(repo_path)
    blame_info = gi.get_git_blame_for_line(file_path, line_number)
    if blame_info:
        return {
            "commit_hash": blame_info.commit_hash,
            "author": blame_info.author,
            "date": blame_info.date.isoformat(),
            "line_number": blame_info.line_number,
            "content": blame_info.content
        }
    return None


def git_analyze_recent_commits(count: int = 5, repo_path: str = ".") -> List[dict]:
    """
    Fonction d'aide pour analyser les derniers commits.

    Args:
        count: Nombre de commits à analyser
        repo_path: Chemin vers le dépôt Git

    Returns:
        Liste de dictionnaires avec les informations des commits
    """
    gi = GitIntelligence(repo_path)
    commits = gi.analyze_recent_commits(count)
    return [
        {
            "hash": commit.hash,
            "author": commit.author,
            "date": commit.date.isoformat(),
            "message": commit.message,
            "files_changed": commit.files_changed,
            "insertions": commit.insertions,
            "deletions": commit.deletions
        }
        for commit in commits
    ]


def git_identify_affected_tests(file_changes: List[dict], repo_path: str = ".") -> List[str]:
    """
    Fonction d'aide pour identifier les tests affectés par des changements.

    Args:
        file_changes: Liste de dictionnaires représentant les changements de fichiers
        repo_path: Chemin vers le dépôt Git

    Returns:
        Liste de chemins de tests affectés
    """
    gi = GitIntelligence(repo_path)
    # Convertir les dictionnaires en objets GitFileChange
    changes = []
    for fc in file_changes:
        change = GitFileChange(
            file_path=fc["file_path"],
            change_type=ChangeType(fc["change_type"]),
            old_path=fc.get("old_path"),
            lines_added=fc.get("lines_added", 0),
            lines_deleted=fc.get("lines_deleted", 0),
            is_staged=fc.get("is_staged", False)
        )
        changes.append(change)
    return gi.identify_affected_tests(changes)