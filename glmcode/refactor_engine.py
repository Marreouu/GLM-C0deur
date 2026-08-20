"""Moteur de refactoring pour renommer en toute sécurité des éléments de code."""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import shutil

from . import ui
from .knowledge_graph import KnowledgeGraph, NodeType


class RefactorType(Enum):
    """Types de refactoring supportés."""
    RENAME_VARIABLE = "rename_variable"
    RENAME_FUNCTION = "rename_function"
    RENAME_CLASS = "rename_class"


@dataclass
class RefactorResult:
    """Résultat d'une opération de refactoring."""
    success: bool
    message: str
    files_modified: List[str] = field(default_factory=list)
    changes_made: Dict[str, List[str]] = field(default_factory=dict)  # file -> list of changes
    errors: List[str] = field(default_factory=list)


class RefactorEngine:
    """
    Moteur de refactoring qui effectue des renommages sûrs en mettant à jour
    toutes les références dans le codebase.

    Supporte :
    - Renommage de classe
    - Renommage de fonction
    - Renommage de variable
    - Mise à jour automatique des imports, appels, tests, documentation
    """

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.kg = KnowledgeGraph(root_path)
        self.kg.build_from_path()

    def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        refactor_type: RefactorType,
        scope: str = "project"  # "file", "project"
    ) -> RefactorResult:
        """
        Renomme un symbole (variable, fonction, classe) dans tout le projet.

        Args:
            old_name: Nom actuel du symbole
            new_name: Nouveau nom du symbole
            refactor_type: Type de symbole à renommer
            scope: Portée du refactoring ("file" ou "project")

        Returns:
            Résultat de l'opération de refactoring
        """
        if not self._is_valid_identifier(new_name):
            return RefactorResult(
                success=False,
                message=f"'{new_name}' n'est pas un identificateur valide",
                errors=[f"Invalid identifier: {new_name}"]
            )

        if old_name == new_name:
            return RefactorResult(
                success=True,
                message="Aucun changement nécessaire (les noms sont identiques)",
                files_modified=[]
            )

        # Trouver toutes les occurrences du symbole
        occurrences = self._find_symbol_occurrences(old_name, refactor_type, scope)

        if not occurrences:
            return RefactorResult(
                success=False,
                message=f"Aucune occurrence de '{old_name}' trouvée en tant que {refactor_type.value}",
                errors=[f"No occurrences found for {old_name} as {refactor_type.value}"]
            )

        # Vérifier que le nouveau nom n'entre pas en conflit
        conflicts = self._check_name_conflicts(new_name, refactor_type, scope, exclude=[occ[0] for occ in occurrences])
        if conflicts:
            return RefactorResult(
                success=False,
                message=f"Le nom '{new_name}' entre en conflit avec des éléments existants",
                errors=[f"Name conflicts: {', '.join(conflicts)}"]
            )

        # Effectuer le refactoring
        result = RefactorResult(success=True, message="")
        files_to_process = set(file_path for file_path, _, _ in occurrences)

        for file_path in files_to_process:
            try:
                file_result = self._refactor_file(
                    file_path, old_name, new_name, refactor_type, occurrences
                )
                if file_result.success:
                    result.files_modified.append(file_path)
                    if file_result.changes_made:
                        result.changes_matched.update(file_result.changes_made)
                else:
                    result.errors.extend(file_result.errors)
            except Exception as e:
                result.errors.append(f"Error processing {file_path}: {str(e)}")

        # Mettre à jour le graphe de connaissances pour refléter les changements
        if result.files_modified:
            self.kg = KnowledgeGraph(self.root_path)
            self.kg.build_from_path()

        result.message = f"Renommage de {old_name} en {new_name} terminé. {len(result.files_modified)} fichier(s) modifié(s)."
        return result

    def _is_valid_identifier(self, name: str) -> bool:
        """Vérifie si un nom est un identificateur Python valide."""
        if not name:
            return False
        if not name[0].isalpha() and name[0] != '_':
            return False
        return all(c.isalnum() or c == '_' for c in name)

    def _find_symbol_occurrences(
        self,
        symbol_name: str,
        refactor_type: RefactorType,
        scope: str
    ) -> List[Tuple[str, int, str]]:
        """
        Trouve toutes les occurrences d'un symbole dans le codebase.

        Returns:
            Liste de tuples (file_path, line_number, context_line)
        """
        occurrences = []

        # Chercher dans le graphe de connaissances d'abord
        target_node_type = None
        if refactor_type == RefactorType.RENAME_VARIABLE:
            # Les variables sont plus dures à trouver dans le KG, on se base sur la recherche textuelle
            pass
        elif refactor_type == RefactorType.RENAME_FUNCTION:
            target_node_type = NodeType.FUNCTION
        elif refactor_type == RefactorType.RENAME_CLASS:
            target_node_type = NodeType.CLASS

        if target_node_type:
            for node in self.kg.get_nodes_by_type(target_node_type):
                if node.name == symbol_name:
                    occurrences.append((node.file_path, node.line_number, f"{node.type.value}: {node.name}"))

        # Recherche textuelle complémentaire pour attraper tout ce que le KG aurait manqué
        for file_path, content in self.kg._file_contents.items():
            # Limiter aux fichiers Python pour éviter les faux positifs
            if not file_path.endswith('.py'):
                continue

            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                # Rechercher des patterns selon le type de refactoring
                if refactor_type == FuncType.RENAME_VARIABLE:
                    # Chercher des utilisations de variable (plus complexe, approximation)
                    # Éviter les faux positifs dans les commentaires et chaînes
                    if self._is_variable_usage(line, symbol_name):
                        occurrences.append((file_path, line_num, line.strip()))
                elif refactor_type == RefactorType.RENAME_FUNCTION:
                    # Chercher des appels de fonction
                    if self._is_function_call(line, symbol_name):
                        occurrences.append((file_path, line_num, line.strip()))
                elif refactor_type == RefactorType.RENAME_CLASS:
                    # Chercher des instantiations ou références de classe
                    if self._is_class_reference(line, symbol_name):
                        occurrences.append((file_path, line_num, line.strip()))

        # Dédupliquer (même fichier, même ligne peut apparaître plusieurs fois)
        seen = set()
        unique_occurrences = []
        for file_path, line_num, context in occurrences:
            key = (file_path, line_num)
            if key not in seen:
                seen.add(key)
                unique_occurrences.append((file_path, line_num, context))

        return unique_occurrences

    def _is_variable_usage(self, line: str, var_name: str) -> bool:
        """Vérifie approximativement si une ligne contient une utilisation d'une variable."""
        # Éviter les commentaires et les chaînes de caractères
        # C'est une approximation simple
        if '#' in line:
            # Partie avant le premier # (si c'est pas dans une chaîne)
            comment_pos = line.find('#')
            # Vérifier si le # est dans une chaîne
            before_comment = line[:comment_pos]
            if '"' in before_comment or "'" in before_comment:
                # Trop complexe pour déterminer précisément, on simplifie
                check_part = line
            else:
                check_part = before_comment
        else:
            check_part = line

        # Rechercher le nom de variable comme mot isolé
        pattern = rf'\b{re.escape(var_name)}\b'
        return bool(re.search(pattern, check_part))

    def _is_function_call(self, line: str, func_name: str) -> bool:
        """Vérifie approximativement si une ligne contient un appel à une fonction."""
        # Éviter les commentaires et chaînes
        if '#' in line:
            comment_pos = line.find('#')
            before_comment = line[:comment_pos]
            if '"' in before_comment or "'" in before_comment:
                check_part = line
            else:
                check_part = before_comment
        else:
            check_part = line

        # Rechercher un appel de fonction: nom suivi de (
        pattern = rf'\b{re.escape(func_name)}\s*\('
        return bool(re.search(pattern, check_part))

    def _is_class_reference(self, line: str, class_name: str) -> bool:
        """Vérifie approximativement si une ligne contient une référence à une classe."""
        # Éviter les commentaires et chaînes
        if '#' in line:
            comment_pos = line.find('#')
            before_comment = line[:comment_pos]
            if '"' in before_comment or "'" in before_comment:
                check_part = line
            else:
                check_part = before_comment
        else:
            check_part = line

        # Rechercher diverses utilisations de classe:
        # 1. Instanciation: ClassName()
        # 2. Héritage: class ChildClass(ParentClass):
        # 3. Utilisation de type: isinstance(obj, ClassName)
        # 4. Attributs: instance.attribute
        patterns = [
            rf'\b{re.escape(class_name)}\s*\(',  # Instanciation
            rf'\b{re.escape(class_name)}\s*\)',  # Dans un appel (moins spécifique mais utile)
            rf'isinstance\s*\([^,]*,\s*{re.escape(class_name)}',  # isinstance
            r'\b' + re.escape(class_name) + r'\s*\.\s*\w+',  # attribute access
        ]

        for pattern in patterns:
            if re.search(pattern, check_part):
                return True

        # Vérifier l'héritage spécifiquement (devrait être en dehors des parenthèses de fonction généralement)
        inheritance_pattern = rf'^\s*class\s+\w+\s*\(\s*{re.escape(class_name)}\s*[,)]'
        if re.search(inheritance_pattern, check_part, re.MULTILINE):
            return True

        return False

    def _check_name_conflicts(
        self,
        new_name: str,
        refactor_type: RefactorType,
        scope: str,
        exclude: List[str] = None
    ) -> List[str]:
        """
        Vérifie si le nouveau nom crée des conflits avec des éléments existants.

        Returns:
            Liste des conflits trouvés (vide si aucun conflit)
        """
        if exclude is None:
            exclude = []

        conflicts = []
        target_node_type = None
        if refactor_type == RefactorType.RENAME_VARIABLE:
            # Les variables sont plus dures à vérifier depuis le KG, on s'appuie sur la recherche textuelle
            pass
        elif refactor_type == RefactorType.RENAME_FUNCTION:
            target_node_type = NodeType.FUNCTION
        elif refactor_type == RefactorType.RENAME_CLASS:
            target_node_type = NodeType.CLASS

        if target_node_type:
            for node in self.kg.get_nodes_by_type(target_node_type):
                if node.name == new_name and node.file_path not in exclude:
                    conflicts.append(f"{node.type.value} '{node.name}' in {node.file_path}:{node.line_number}")

        # Vérification textuelle supplémentaire pour éviter les faux négatifs du KG
        for file_path, content in self.kg._file_contents.items():
            if file_path in exclude:
                continue
            if not file_path.endswith('.py'):
                continue

            # Vérifier s'il y aurait une définition conflitante
            if refactor_type == RefactorType.RENAME_FUNCTION:
                pattern = rf'^\s*def\s+{re.escape(new_name)}\s*\('
                if re.search(pattern, content, re.MULTILINE):
                    conflicts.append(f"function '{new_name}' in {file_path}")
            elif refactor_type == ReFactorType.RENAME_CLASS:
                pattern = rf'^\s*class\s+{re.escape(new_name)}\s*[\(:]'
                if re.search(pattern, content, re.MULTILINE):
                    conflicts.append(f"class '{new_name}' in {file_path}")

        return conflicts

    def _refactor_file(
        self,
        file_path: str,
        old_name: str,
        new_name: str,
        refactor_type: RefactorType,
        all_occurrences: List[Tuple[str, int, str]]
    ) -> RefactorResult:
        """
        Effectue le refactoring dans un fichier spécifique.

        Returns:
            Résultat du refactoring pour ce fichier
        """
        full_path = self.root_path / file_path
        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception as e:
            return RefactorResult(
                success=False,
                message=f"Impossible de lire le fichier {file_path}",
                errors=[f"Read error: {e}"]
            )

        lines = content.split('\n')
        modified_lines = []
        changes_in_file = []

        for line_num, line in enumerate(lines, 1):
            original_line = line
            modified_line = line

            # Ignorer les lignes qui sont dans des commentaires ou des chaînes pour éviter les faux positifs
            # C'est une approximation - une vraie implémentation aurait besoin d'un parseur plus sophistiqué
            if self._is_in_comment_or_string(line, 0):  # Position approximative
                modified_lines.append(line)
                continue

            # Appliquer les remplacements selon le type de refactoring
            if refactor_type == RefactorType.RENAME_VARIABLE:
                modified_line = self._replace_variable_in_line(
                    line, old_name, new_name, line_num
                )
            elif refactor_type == RefactorType.RENAME_FUNCTION:
                modified_line = self._replace_function_in_line(
                    line, old_name, new_name, line_num
                )
            elif refactor_type == RefactorType.RENAME_CLASS:
                modified_line = self._replace_class_in_line(
                    line, old_name, new_name, line_num
                )

            if modified_line != original_line:
                changes_in_file.append(
                    f"Line {line_num}: {original_line} → {modified_line}"
                )

            modified_lines.append(modified_line)

        # Écrire le fichier modifié si des changements ont été faits
        if any(line != orig_line for line, orig_line in zip(modified_lines, lines)):
            try:
                # Créer une sauvegarde
                backup_path = full_path.with_suffix(f"{full_path.suffix}.bak")
                shutil.copy2(full_path, backup_path)

                # Écrire le nouveau contenu
                new_content = '\n'.join(modified_lines)
                full_path.write_text(new_content, encoding="utf-8")

                return RefactorResult(
                    success=True,
                    message=f"Fichier {file_path} modifié avec succès",
                    changes_made={file_path: changes_in_file}
                )
            except Exception as e:
                return RefactorResult(
                    success=False,
                    message=f"Erreur lors de l'écriture du fichier {file_path}",
                    errors=[f"Write error: {e}"]
                )
        else:
            return RefactorResult(
                success=True,
                message=f"Aucun changement nécessaire dans {file_path}",
                changes_made={}
            )

    def _is_in_comment_or_string(self, line: str, col_pos: int) -> bool:
        """
        Détermine si une position dans une ligne est dans un commentaire ou une chaîne de caractères.
        C'est une approximation simple basée sur le comptage des guillemets.
        """
        if col_pos < 0:
            return False

        # Compter les guillemets simples et doubles avant la position
        single_quotes = line[:col_pos].count("'")
        double_quotes = line[:col_pos].count('"')

        # Si un nombre impair de guillemets, on est à l'intérieur d'une chaîne
        in_string = (single_quotes % 2 == 1) or (double_quotes % 2 == 1)

        # Vérifier si on est dans un commentaire (tout ce qui suit un # non échappé)
        hash_pos = line.find('#')
        if hash_pos != -1 and hash_pos < col_pos:
            # Vérifier si le # est dans une chaîne
            hash_in_string = False
            temp_single = line[:hash_pos].count("'")
            temp_double = line[:hash_pos].count('"')
            if (temp_single % 2 == 1) or (temp_double % 2 == 1):
                hash_in_string = True

            if not hash_in_string:
                return True  # On est dans un commentaire

        return in_string

    def _replace_variable_in_line(
        self,
        line: str,
        old_name: str,
        new_name: str,
        line_num: int
    ) -> str:
        """Remplace les occurrences d'une variable dans une ligne de code."""
        # Éviter de remplacer dans les commentaires et chaînes
        if self._is_in_comment_or_string(line, 0):
            return line

        # Utiliser une expression régulière avec des limites de mot pour éviter les remplacer partiels
        # Mais il faut faire attention au contexte (pas dans les chaînes, etc.)
        # Pour simplifier, on fait un remplacement sûr en vérifiant le contexte autour

        # Pattern pour trouver le nom comme mot isolé
        pattern = rf'\b{re.escape(old_name)}\b'

        def replace_func(match):
            # Vérifier que la correspondance n'est pas dans une chaîne ou un commentaire
            match_start, match_end = match.span()
            if not self._is_in_comment_or_string(line, match_start):
                return new_name
            else:
                return match.group(0)  # Laisser tel quel si dans une chaîne/commentaire

        return re.sub(pattern, replace_func, line)

    def _replace_function_in_line(
        self,
        line: str,
        old_name: str,
        new_name: str,
        line_num: int
    ) -> str:
        """Remplace les occurrences d'un nom de fonction dans une ligne de code."""
        if self._is_in_comment_or_string(line, 0):
            return line

        # Remplacer les appels de fonction: nom suivi de (
        pattern = rf'\b{re.escape(old_name)}\s*\('

        def replace_func(match):
            match_start, match_end = match.span()
            if not self._is_in_comment_or_string(line, match_start):
                return f"{new_name}{match.group(0)[len(old_name):]}"  # Garder le parenthèse
            else:
                return match.group(0)

        return re.sub(pattern, replace_func, line)

    def _replace_class_in_line(
        self,
        line: str,
        old_name: str,
        new_name: str,
        line_num: int
    ) -> str:
        """Remplace les occurrences d'un nom de classe dans une ligne de code."""
        if self._is_in_comment_or_string(line, 0):
            return line

        # Plusieurs patterns pour les références de classe
        patterns = [
            # Instanciation: ClassName()
            (rf'\b{re.escape(old_name)}\s*\(', f'{new_name}( '),
            # Héritage: class Child(Parent):
            (rf'\b{re.escape(old_name)}\s*\)', f'{new_name} )'),
            # isinstance: isinstance(obj, ClassName)
            (rf'isinstance\s*\([^,]*,\s*{re.escape(old_name)}', f'isinstance($1, {new_name}'),
            # Accès d'attribut: instance.attribute
            (rf'\b{re.escape(old_name)}\s*\.\s*\w+', lambda m: m.group(0).replace(old_name, new_name)),
            # Référence isolée (fait attention aux faux positifs)
            (rf'\b{re.escape(old_name)}\b', lambda m: self._safe_replace_class(m, line, new_name))
        ]

        result = line
        for pattern, replacement in patterns:
            if callable(replacement):
                # Pour les fonctions de remplacement personnalisées
                def make_replacer(rep_func):
                    def replacer(match):
                        match_start, match_end = match.span()
                        if not self._is_in_comment_or_string(line, match_start):
                            return rep_func(match)
                        else:
                            return match.group(0)
                    return replacer
                result = re.sub(pattern, make_replacer(replacement), result)
            else:
                # Remplacement simple avec vérification de contexte
                def make_simple_replacer(rep_string):
                    def replacer(match):
                        match_start, match_end = match.span()
                        if not self._is_in_comment_or_string(line, match_start):
                            return rep_string
                        else:
                            return match.group(0)
                    return replacer
                result = re.sub(pattern, make_simple_replacer(replacement), result)

        return result

    def _safe_replace_class(self, match: re.Match, original_line: str, new_name: str) -> str:
        """Remplacement sécurisé pour les références de classe isolées."""
        match_start, match_end = match.span()
        # Éviter de remplacer si c'est dans une chaîne ou un commentaire
        if self._is_in_comment_or_string(original_line, match_start):
            return match.group(0)

        # Vérifications contextuelles supplémentaires pour éviter les faux positifs
        # Par exemple, ne pas remplacer dans des commentaires de type "# TODO: refactoriser OldClassName"
        # Déjà géré par _is_in_comment_or_string ci-dessus

        # Éviter de remplacer si ça ressemble à un mot-clé ou à une partie d'un mot plus grand dans certains contextes
        # Cette vérification est basique - une vraie implémentation aurait besoin d'analyser le contexte syntaxique

        before = max(0, match_start - 10)
        after = min(len(original_line), match_end + 10)
        context = original_line[before:after].lower()

        # Éviter les faux positifs évidents
        false_positive_indicators = ['#', '//', '/*', '"""', "'''", 'import ', 'from ']
        if any(indicator in context for indicator in false_positive_indicators):
            # Si on est proche d'un indicateur de faux positif, vérifier si c'est vraiment sûr
            # Pour simplifier ici, on fait confiance au contrôle de commentaire/chaîne ci-dessus
            pass

        return new_name


# Fonctions d'aide pour faciliter l'utilisation
def rename_symbol(
    old_name: str,
    new_name: str,
    refactor_type: str,
    scope: str = "project",
    root_path: str = "."
) -> dict:
    """
    Fonction d'aide pour renommer un symbole.

    Args:
        old_name: Nom actuel du symbole
        new_name: Nouveau nom du symbole
        refactor_type: Type de réflexse ("variable", "function", "class")
        scope: Portée du refactoring ("file" ou "project")
        root_path: Racine du projet

    Returns:
        Dictionnaire avec le résultat de l'opération
    """
    try:
        refactor_type_enum = RefactorType(refactor_type)
    except ValueError:
        return {
            "success": False,
            "message": f"Type de refactoring invalide: {refactor_type}",
            "errors": [f"Invalid refactor type: {refactor_type}"]
        }

    engine = RefactorEngine(root_path)
    result = engine.rename_symbol(old_name, new_name, refactor_type_enum, scope)

    return {
        "success": result.success,
        "message": result.message,
        "files_modified": result.files_modified,
        "changes_made": result.changes_made,
        "errors": result.errors
    }


def rename_variable(old_name: str, new_name: str, scope: str = "project", root_path: str = ".") -> dict:
    """Fonction d'aide pour renommer une variable."""
    return rename_symbol(old_name, new_name, "variable", scope, root_path)


def rename_function(old_name: str, new_name: str, scope: str = "project", root_path: str = ".") -> dict:
    """Fonction d'aide pour renommer une fonction."""
    return rename_symbol(old_name, new_name, "function", scope, root_path)


def rename_class(old_name: str, new_name: str, scope: str = "project", root_path: str = ".") -> dict:
    """Fonction d'aide pour renommer une classe."""
    return rename_symbol(old_name, new_name, "class", scope, root_path)