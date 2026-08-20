"""Gestion intelligente du contexte pour réduire le nombre de tokens envoyés au LLM."""

from __future__ import annotations

import ast
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Union
from .performance_monitor import profile, record_metric

from . import ui


class ContextType(Enum):
    """Types de contexte pouvant être envoyés au LLM."""
    FULL_FILE = "full_file"
    FUNCTION = "function"
    CLASS = "class"
    AST_SUMMARY = "ast_summary"
    GIT_DIFF = "git_diff"


@dataclass
class ContextDecision:
    """Décision sur quel type de contexte envoyer."""
    type: ContextType
    content: str
    reason: str
    estimated_tokens: int


class ContextManager:
    """Gestionnaire qui décide automatiquement quoi envoyer au LLM pour minimiser les tokens."""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self._git_root: Optional[Path] = None
        self._is_git_repo = False
        self._detect_git_repository()

    def _detect_git_repository(self) -> None:
        """Détecte si le répertoire racine est un dépôt Git."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.root_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            self._is_git_repo = result.returncode == 0
            if self._is_git_repo:
                git_dir_result = subprocess.run(
                    ["git", "rev-parse", "--git-dir"],
                    cwd=self.root_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if git_dir_result.returncode == 0:
                    git_dir = git_dir_result.stdout.strip()
                    if git_dir == ".git":
                        self._git_root = self.root_path
                    else:
                        self._git_root = self.root_path / git_dir
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._is_git_repo = False
            self._git_root = None

    @profile("get_context_for_file")
    def get_context_for_file(self, file_path: str, query: str = "") -> ContextDecision:
        """
        Détermine le meilleur type de contexte à envoyer pour un fichier donné.

        Args:
            file_path: Chemin relatif vers le fichier depuis la racine du projet
            query: Requête de l'utilisateur (pour contextualiser la décision)

        Returns:
            ContextDecision avec le type de contexte choisi et son contenu
        """
        import time

        start_time = time.perf_counter()
        full_path = self.root_path / file_path

        # Vérifier que le fichier existe
        if not full_path.is_file():
            record_metric("context_file_not_found", 1, "count", {"file_path": file_path})
            duration = time.perf_counter() - start_time
            record_metric("context_decision_time", duration, "seconds", {
                "file_path": file_path,
                "decision_type": "ERROR",
                "reason": "Fichier non trouvé",
                "token_count": 0
            })
            return ContextDecision(
                type=ContextType.FULL_FILE,
                content=f"[erreur] Fichier introuvable : {file_path}",
                reason="Fichier non trouvé",
                estimated_tokens=0,
            )

        # Lire le contenu du fichier
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            record_metric("context_file_read_error", 1, "count", {"file_path": file_path, "error": str(e)})
            duration = time.perf_counter() - start_time
            record_metric("context_decision_time", duration, "seconds", {
                "file_path": file_path,
                "decision_type": "ERROR",
                "reason": f"Erreur de lecture: {e}",
                "token_count": 0
            })
            return ContextDecision(
                type=ContextType.FULL_FILE,
                content=f"[erreur] Impossible de lire le fichier {file_path}: {e}",
                reason="Erreur de lecture",
                estimated_tokens=0,
            )

        # Estimer le nombre de tokens (approximation simple : 1 token ≈ 4 caracteres)
        estimated_tokens = len(content) // 4
        record_metric("context_file_read", 1, "count", {"file_path": file_path, "size": len(content)})

        # Si le fichier est petit, envoyer le contenu complet
        if estimated_tokens < 500:  # Seuil arbitraire pour les petits fichiers
            duration = time.perf_counter() - start_time
            record_metric("context_decision_time", duration, "seconds", {
                "file_path": file_path,
                "decision_type": "FULL_FILE",
                "reason": "Fichier petit (< 500 tokens estimés)",
                "token_count": estimated_tokens
            })
            return ContextDecision(
                type=ContextType.FULL_FILE,
                content=content,
                reason="Fichier petit (< 500 tokens estimés)",
                estimated_tokens=estimated_tokens,
            )

        # Analyser le contenu pour décider quoi envoyer
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Si ce n'est pas du Python valable, revenir au contenu complet
            duration = time.perf_counter() - start_time
            record_metric("context_decision_time", duration, "seconds", {
                "file_path": file_path,
                "decision_type": "FULL_FILE",
                "reason": "Fichier non-Python ou syntaxe invalide",
                "token_count": estimated_tokens
            })
            return ContextDecision(
                type=ContextType.FULL_FILE,
                content=content,
                reason="Fichier non-Python ou syntaxe invalide",
                estimated_tokens=estimated_tokens,
            )

        # Chercher des fonctions ou classes pertinentes par rapport à la requête
        if query:
            relevant_symbols = self._find_relevant_symbols(tree, query, content)
            if relevant_symbols:
                # Retourner le symbole le plus pertinent
                symbol_type, symbol_name, symbol_code = relevant_symbols[0]
                duration = time.perf_counter() - start_time
                record_metric("context_decision_time", duration, "seconds", {
                    "file_path": file_path,
                    "decision_type": "FUNCTION" if symbol_type == "function" else "CLASS",
                    "reason": f"{'Fonction' if symbol_type == 'function' else 'Classe'} pertinente trouvée : {symbol_name}",
                    "token_count": len(symbol_code) // 4
                })
                return ContextDecision(
                    type=ContextType.FUNCTION if symbol_type == "function" else ContextType.CLASS,
                    content=symbol_code,
                    reason=f"{'Fonction' if symbol_type == 'function' else 'Classe'} pertinente trouvée : {symbol_name}",
                    estimated_tokens=len(symbol_code) // 4,
                )

        # Essayer de générer un résumé AST
        ast_summary = self._generate_ast_summary(tree)
        if ast_summary:
            ast_tokens = len(ast_summary) // 4
            if ast_tokens < estimated_tokens * 0.5:  # Au moins 50% d'économie
                duration = time.perf_counter() - start_time
                record_metric("context_decision_time", duration, "seconds", {
                    "file_path": file_path,
                    "decision_type": "AST_SUMMARY",
                    "reason": "Résumé AST généré (économie significative de tokens)",
                    "token_count": ast_tokens
                })
                return ContextDecision(
                    type=ContextType.AST_SUMMARY,
                    content=ast_summary,
                    reason="Résumé AST généré (économie significative de tokens)",
                    estimated_tokens=ast_tokens,
                )

        # Vérifier si nous sommes dans un dépôt Git et si le fichier a été modifié
        if self._is_git_repo:
            git_diff = self._get_git_diff_for_file(file_path)
            if git_diff and "diff --git" in git_diff:
                diff_tokens = len(git_diff) // 4
                if diff_tokens < estimated_tokens * 0.3:  # Au moins 70% d'économie
                    duration = time.perf_counter() - start_time
                    record_metric("context_decision_time", duration, "seconds", {
                        "file_path": file_path,
                        "decision_type": "GIT_DIFF",
                        "reason": "Diff Git montrant uniquement les changements récents",
                        "token_count": diff_tokens
                    })
                    return ContextDecision(
                        type=ContextType.GIT_DIFF,
                        content=git_diff,
                        reason="Diff Git montrant uniquement les changements récents",
                        estimated_tokens=diff_tokens,
                    )

        # Par défaut, retourner le contenu complet (mais on pourrait aussi essayer de
        # envoyer seulement les parties modifiées ou pertinentes)
        duration = time.perf_counter() - start_time
        record_metric("context_decision_time", duration, "seconds", {
            "file_path": file_path,
            "decision_type": "FULL_FILE",
            "reason": "Aucune optimisation applicable détectée",
            "token_count": estimated_tokens
        })
        return ContextDecision(
            type=ContextType.FULL_FILE,
            content=content,
            reason="Aucune optimisation applicable détectée",
            estimated_tokens=estimated_tokens,
        )

    def _find_relevant_symbols(
        self, tree: ast.AST, query: str, content: str
    ) -> List[tuple[str, str, str]]:
        """
        Trouve les fonctions/classes dans l'AST qui semblent pertinentes par rapport à la requête.

        Returns:
            Liste de tuples (type, nom, code) triés par pertinence
        """
        query_lower = query.lower()
        relevant = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                # Vérifier si le nom de la fonction contient des mots de la requête
                if any(word in func_name.lower() for word in query_lower.split()):
                    try:
                        # Extraire le code de la fonction
                        lines = content.split('\n')
                        start_line = node.lineno - 1
                        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
                        func_code = '\n'.join(lines[start_line:end_line])
                        relevant.append(("function", func_name, func_code))
                    except (AttributeError, IndexError):
                        # Fallback : utiliser une approximation simple
                        func_code = f"def {func_name}(...):\n    # Corps de la fonction"
                        relevant.append(("function", func_name, func_code))
            elif isinstance(node, ast.ClassDef):
                class_name = node.name
                if any(word in class_name.lower() for word in query_lower.split()):
                    try:
                        lines = content.split('\n')
                        start_line = node.lineno - 1
                        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
                        class_code = '\n'.join(lines[start_line:end_line])
                        relevant.append(("class", class_name, class_code))
                    except (AttributeError, IndexError):
                        class_code = f"class {class_name}:\n    pass"
                        relevant.append(("class", class_name, class_code))

        # Trier par pertinence (simple : ceux qui correspondent exactement d'abord)
        def relevance_score(item):
            _, name, _ = item
            name_lower = name.lower()
            query_words = query_lower.split()
            exact_matches = sum(1 for word in query_words if word in name_lower)
            return (-exact_matches, len(name))  # Plus de correspondances exactes = mieux, puis nom plus court

        relevant.sort(key=relevance_score)
        return relevant

    def _generate_ast_summary(self, tree: ast.AST) -> str:
        """Génère un résumé de la structure AST du fichier."""
        lines = []

        # Compter les différents types de nœuds
        function_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        import_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))

        lines.append(f"# Résumé AST du fichier")
        lines.append(f"- Fonctions : {function_count}")
        lines.append(f"- Classes : {class_count}")
        lines.append(f"- Importations : {import_count}")

        # Lister les fonctions et classes avec leurs signatures
        if function_count > 0:
            lines.append("\n## Fonctions")
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = [arg.arg for arg in node.args.args]
                    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                    args_str = ", ".join(args)
                    lines.append(f"- def {node.name}({args_str}){returns}")

        if class_count > 0:
            lines.append("\n## Classes")
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    bases = [ast.unparse(base) for base in node.bases] if node.bases else []
                    bases_str = f"({', '.join(bases)})" if bases else ""
                    lines.append(f"- class {node.name}{bases_str}")
                    # Méthodes de la classe
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            args = [arg.arg for arg in item.args.args]
                            args_str = ", ".join(args)
                            lines.append(f"  - def {item.name}({args_str})")

        if import_count > 0:
            lines.append("\n## Importations")
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        lines.append(f"- import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    names = [alias.name for alias in node.names]
                    lines.append(f"- from {module} import {', '.join(names)}")

        return "\n".join(lines)

    def _get_git_diff_for_file(self, file_path: str) -> Optional[str]:
        """Obtient le diff Git pour un fichier spécifique."""
        if not self._is_git_repo or not self._git_root:
            return None

        try:
            # Obtenir le diff entre l'index et le working tree pour ce fichier
            result = subprocess.run(
                ["git", "diff", "HEAD", "--", file_path],
                cwd=self._git_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                diff_output = result.stdout.strip()
                if diff_output:
                    return diff_output

            # Si pas de différences avec HEAD, vérifier les changements non stagés
            result = subprocess.run(
                ["git", "diff", "--", file_path],
                cwd=self._git_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    def get_context_for_multiple_files(
        self, file_paths: List[str], query: str = ""
    ) -> List[ContextDecision]:
        """
        Obtient le contexte pour plusieurs fichiers.

        Returns:
            Liste de ContextDecision pour chaque fichier
        """
        return [self.get_context_for_file(fp, query) for fp in file_paths]


# Fonction d'aide pour faciliter l'utilisation
def get_optimal_context(file_path: str, query: str = "", root_path: str = ".") -> ContextDecision:
    """
    Fonction d'aide pour obtenir le contexte optimal pour un fichier.

    Args:
        file_path: Chemin relatif vers le fichier
        query: Requête de l'utilisateur
        root_path: Racine du projet (défaut : répertoire courant)

    Returns:
        ContextDecision avec le contexte recommandé
    """
    manager = ContextManager(root_path)
    return manager.get_context_for_file(file_path, query)