"""Knowledge Graph pour représenter les relations entre les éléments du code."""

from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import hashlib

from . import ui


class NodeType(Enum):
    """Types de nœuds dans le graphe de connaissances."""
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    IMPORT = "import"
    VARIABLE = "variable"


@dataclass
class Node:
    """Nœud dans le graphe de connaissances."""
    id: str
    type: NodeType
    name: str
    file_path: str
    line_number: int
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)  # IDs des nœuds enfants


@dataclass
class Edge:
    """Arête dans le graphe de connaissances."""
    source: str
    target: str
    type: str  # "import", "inheritance", "call", "containment", etc.
    properties: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """
    Graphe de connaissances représentant la structure du code et les dépendances.

    Contient :
    - classes
    - fonctions
    - imports
    - héritage
    - appels de fonctions
    - dépendances
    - modules utilisés
    """

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._file_contents: Dict[str, str] = {}
        self._node_id_counter = 0

    def _generate_node_id(self) -> str:
        """Génère un ID unique pour un nœud."""
        self._node_id_counter += 1
        return f"node_{self._node_id_counter}_{int(time.time() * 1000)}"

    def build_from_path(self, path: str = None) -> None:
        """
        Construit le graphe de connaissances à partir des fichiers Python dans le chemin spécifié.

        Args:
            path: Chemin relatif depuis la racine du projet (None = racine complète)
        """
        if path is None:
            search_path = self.root_path
        else:
            search_path = self.root_path / path

        if not search_path.exists():
            return

        # Parcourir récursivement les fichiers Python
        for root, dirs, files in os.walk(search_path):
            # Ignorer les répertoires de cache et virtuels
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                '__pycache__', '.git', 'node_modules', '.venv', 'venv',
                '.idea', '.mypy_cache', '.pytest_cache', '.ruff_cache',
                'dist', 'build', '.eggs'
            }]

            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.root_path)
                    self._parse_python_file(str(relative_path))

    def _parse_python_file(self, file_path: str) -> None:
        """Analyse un fichier Python et extrait sa structure pour le graphe."""
        full_path = self.root_path / file_path

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return  # Ignorer les fichiers qui ne peuvent pas être lus

        self._file_contents[file_path] = content

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return  # Ignorer les fichiers avec des erreurs de syntaxe

        # Créer un nœud pour le fichier
        file_node_id = self._create_file_node(file_path, content)

        # Parcourir l'arbre AST pour extraire les éléments
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._process_class(node, file_path, file_node_id, content)
            elif isinstance(node, ast.FunctionDef):
                # Vérifier si c'est une méthode (à l'intérieur d'une classe) ou une fonction globale
                if self._is_method_in_class(node, tree):
                    self._process_method(node, file_path, content)
                else:
                    self._process_function(node, file_path, file_node_id, content)
            elif isinstance(node, ast.Import):
                self._process_import(node, file_path, file_node_id)
            elif isinstance(node, ast.ImportFrom):
                self._import_from_node(node, file_path, file_node_id)

    def _create_file_node(self, file_path: str, content: str) -> str:
        """Crée un nœud représentant un fichier."""
        node_id = self._generate_node_id()
        node = Node(
            id=node_id,
            type=NodeType.FILE,
            name=os.path.basename(file_path),
            file_path=file_path,
            line_number=1,
            properties={
                "size": len(content),
                "lines": len(content.splitlines()),
                "language": "python" if file_path.endswith('.py') else "unknown"
            }
        )
        self.nodes[node_id] = node
        return node_id

    def _is_method_in_class(self, func_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Vérifie si une fonction est une méthode définie à l'intérieur d'une classe."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Vérifier si la fonction est dans le corps de cette classe
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item is func_node:
                        return True
        return False

    def _process_class(self, node: ast.ClassDef, file_path: str,
                      file_node_id: str, content: str) -> None:
        """Traite une définition de classe."""
        class_node_id = self._generate_node_id()
        class_node = Node(
            id=class_node_id,
            type=NodeType.CLASS,
            name=node.name,
            file_path=file_path,
            line_number=node.lineno,
            properties={
                "docstring": ast.get_docstring(node),
                "base_classes": [base.id if isinstance(base, ast.Name)
                               else ast.dump(base) for base in node.bases]
            }
        )
        self.nodes[class_node_id] = class_node

        # Lien de containment avec le fichier
        self.edges.append(Edge(
            source=file_node_id,
            target=class_node_id,
            type="contains"
        ))

        # Traiter les méthodes de la classe
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_node_id = self._process_method(item, file_path, content, class_node_id)
                # Lien d'héritage ou de containment
                self.edges.append(Edge(
                    source=class_node_id,
                    target=method_node_id,
                    type="contains"
                ))

        # Gérer l'héritage
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                # Chercher une classe avec ce nom (dans le même fichier ou importée)
                # Pour simplifier, on crée une arête vers un nœud représentant la classe de base
                # Dans une implémentation complète, on ferait une résolution de noms plus sophistiquée
                pass

    def _process_method(self, node: ast.FunctionDef, file_path: str,
                       content: str, class_node_id: str = None) -> str:
        """Traite une définition de méthode (ou de fonction si class_node_id est None)."""
        method_node_id = self._generate_node_id()
        node_type = NodeType.METHOD if class_node_id else NodeType.FUNCTION

        # Extraire les paramètres
        args = [arg.arg for arg in node.args.args]
        defaults = [None] * (len(args) - len(node.args.defaults)) + [
            ast.dump(default) for default in node.args.defaults
        ]

        method_node = Node(
            id=method_node_id,
            type=node_type,
            name=node.name,
            file_path=file_path,
            line_number=node.lineno,
            properties={
                "docstring": ast.get_docstring(node),
                "args": args,
                "defaults": defaults,
                "returns": ast.dump(node.returns) if node.returns else None
            }
        )
        self.nodes[method_node_id] = method_node

        # Lier au conteneur (classe ou fichier)
        if class_node_id:
            self.edges.append(Edge(
                source=class_node_id,
                target=method_node_id,
                type="contains"
            ))
        else:
            # Trouver le nœud fichier correspondant
            file_node_id = self._find_file_node(file_path)
            if file_node_id:
                self.edges.append(Edge(
                    source=file_node_id,
                    target=method_node_id,
                    type="contains"
                ))

        return method_node_id

    def _process_function(self, node: ast.FunctionDef, file_path: str,
                         file_node_id: str, content: str) -> str:
        """Traite une définition de fonction."""
        return self._process_method(node, file_path, content, None)

    def _process_import(self, node: ast.Import, file_path: str,
                       file_node_id: str) -> None:
        """Traite une déclaration d'import."""
        for alias in node.names:
            import_name = alias.name
            if alias.asname:
                import_name = f"{alias.name} as {alias.asname}"

            import_node_id = self._generate_node_id()
            import_node = Node(
                id=import_node_id,
                type=NodeType.IMPORT,
                name=alias.name,
                file_path=file_path,
                line_number=node.lineno,
                properties={
                    "alias": alias.asname,
                    "is_from": False
                }
            )
            self.nodes[import_node_id] = import_node

            # Lien d'import depuis le fichier
            self.edges.append(Edge(
                source=file_node_id,
                target=import_node_id,
                type="imports"
            ))

    def _import_from_node(self, node: ast.ImportFrom, file_path: str,
                         file_node_id: str) -> None:
        """Traite une déclaration d'import desde."""
        module = node.module or ""
        for alias in node.names:
            name = alias.name
            if alias.asname:
                name = f"{alias.name} as {alias.asname}"

            import_node_id = self._generate_node_id()
            import_node = Node(
                id=import_node_id,
                type=NodeType.IMPORT,
                name=name,
                file_path=file_path,
                line_number=node.lineno,
                properties={
                    "module": module,
                    "alias": alias.asname,
                    "is_from": True
                }
            )
            self.nodes[import_node_id] = import_node

            # Lien d'import depuis le fichier
            self.edges.append(Edge(
                source=file_node_id,
                target=import_node_id,
                type="imports"
            ))

    def _find_file_node(self, file_path: str) -> Optional[str]:
        """Trouve l'ID du nœud correspondant à un fichier."""
        for node_id, node in self.nodes.items():
            if node.type == NodeType.FILE and node.file_path == file_path:
                return node_id
        return None

    def get_node(self, node_id: str) -> Optional[Node]:
        """Récupère un nœud par son ID."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        """Récupère tous les nœuds d'un type donné."""
        return [node for node in self.nodes.values() if node.type == node_type]

    def get_nodes_by_file(self, file_path: str) -> List[Node]:
        """Récupère tous les nœuds associés à un fichier donné."""
        return [node for node in self.nodes.values() if node.file_path == file_path]

    def get_edges_from(self, node_id: str) -> List[Edge]:
        """Récupère toutes les arêtes sortant d'un nœud."""
        return [edge for edge in self.edges if edge.source == node_id]

    def get_edges_to(self, node_id: str) -> List[Edge]:
        """Récupère toutes les arêtes entrant dans un nœud."""
        return [edge for edge in self.edges if edge.target == node_id]

    def find_path(self, start_node_id: str, end_node_id: str,
                  max_depth: int = 10) -> Optional[List[str]]:
        """
        Trouve un chemin entre deux nœuds en utilisant une recherche en largeur.

        Returns:
            Liste d'IDs de nœuds formant le chemin, ou None si pas de chemin
        """
        if start_node_id not in self.nodes or end_node_id not in self.nodes:
            return None

        if start_node_id == end_node_id:
            return [start_node_id]

        from collections import deque

        queue = deque([(start_node_id, [start_node_id])])
        visited = {start_node_id}

        while queue:
            current, path = queue.popleft()

            if len(path) > max_depth:
                continue

            for edge in self.get_edges_from(current):
                neighbor = edge.target
                if neighbor == end_node_id:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def get_dependencies(self, file_path: str) -> Set[str]:
        """
        Trouve tous les fichiers dont dépend le fichier spécifié.

        Returns:
            Ensemble des chemins de fichiers de dépendance
        """
        file_node_id = self._find_file_node(file_path)
        if not file_node_id:
            return set()

        dependencies = set()
        visited = set()
        to_visit = [file_node_id]

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)

            # Chercher les imports qui mènent à d'autres fichiers
            for edge in self.get_edges_from(current):
                if edge.type == "imports":
                    target_node = self.nodes.get(edge.target)
                    if target_node and target_node.type == NodeType.IMPORT:
                        # Résoudre le module importé en fichier
                        # Ceci est une simplification - une vraie implementation ferait une résolution de module
                        pass

            # Pour les fichiers, chercher les contenus qui pourraient être des imports
            node = self.nodes.get(current)
            if node and node.type == NodeType.FILE:
                # En pratique, on devrait avoir des arêtes "imports" du fichier vers les modules
                # Pour simplifier ici, on regarde les nœuds de type IMPORT liés à ce fichier
                for edge in self.get_edges_to(current):
                    if edge.type == "imports":
                        source_node = self.nodes.get(edge.source)
                        if source_node and source_node.type == NodeType.FILE:
                            dependencies.add(source_node.file_path)

        return dependencies

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le graphe en dictionnaire pour sérialisation."""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type.value,
                    "name": node.name,
                    "file_path": node.file_path,
                    "line_number": node.line_number,
                    "properties": node.properties
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "properties": edge.properties
                }
                for edge in self.edges
            ]
        }

    def save_to_file(self, file_path: str) -> None:
        """Sauvegarde le graphe dans un fichier JSON."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: str, root_path: str = ".") -> 'KnowledgeGraph':
        """Charge un graphe depuis un fichier JSON."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        kg = cls(root_path)
        kg.nodes = {}
        kg.edges = []

        for node_data in data["nodes"]:
            node = Node(
                id=node_data["id"],
                type=NodeType(node_data["type"]),
                name=node_data["name"],
                file_path=node_data["file_path"],
                line_number=node_data["line_number"],
                properties=node_data.get("properties", {})
            )
            kg.nodes[node["id"]] = node

        for edge_data in data["edges"]:
            edge = Edge(
                source=edge_data["source"],
                target=edge_data["target"],
                type=edge_data["type"],
                properties=edge_data.get("properties", {})
            )
            kg.edges.append(edge)

        return kg


# Instance globale du graphe de connaissances (singleton simple)
_knowledge_graph_instance: Optional[KnowledgeGraph] = None

def get_knowledge_graph(root_path: str = ".") -> KnowledgeGraph:
    """
    Retourne l'instance singleton du graphe de connaissances.

    Args:
        root_path: Racine du projet à analyser

    Returns:
        Instance de KnowledgeGraph
    """
    global _knowledge_graph_instance
    if _knowledge_graph_instance is None or _knowledge_graph_instance.root_path != Path(root_path).resolve():
        _knowledge_graph_instance = KnowledgeGraph(root_path)
        _knowledge_graph_instance.build_from_path()
    return _knowledge_graph_instance

def build_knowledge_graph(path: str = None) -> KnowledgeGraph:
    """
    Construit et retourne un graphe de connaissances pour le chemin spécifié.

    Args:
        path: Chemin relatif depuis la racine du projet (None = construire à partir de la racine configurée)

    Returns:
        Instance de KnowledgeGraph construite
    """
    kg = get_knowledge_graph()
    if path is not None:
        kg.build_from_path(path)
    return kg