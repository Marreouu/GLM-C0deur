"""Recherche sémantique qui trouve du code basé sur la signification plutôt que sur les mots exacts."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
import string

from . import ui
from .knowledge_graph import KnowledgeGraph, NodeType


@dataclass
class SearchResult:
    """Résultat d'une recherche sémantique."""
    file_path: str
    line_number: int
    content: str
    score: float
    match_type: str  # "exact", "semantic", "fuzzy"
    metadata: dict = field(default_factory=dict)


class SimpleEmbedding:
    """
    Implémentation simple d'embeddings basée sur TF-IDF pour la similarité sémantique de base.
    Dans une implémentation production, on utiliserait des modèles comme Sentence-BERT.
    """

    def __init__(self):
        self.vocabulary: dict[str, int] = {}
        self.idf_values: dict[str, float] = {}
        self._is_fitted = False

    def _tokenize(self, text: str) -> list[str]:
        """Tokenise un texte en mots simples."""
        # Convertir en minuscules et supprimer la ponctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        # Filtrer les mots très communs (stop words basiques)
        stop_words = {
            'le', 'la', 'les', 'un', 'une', 'des', 'et', 'ou', 'mais', 'donc',
            'car', 'puisque', 'pour', 'par', 'avec', 'sans', 'sur', 'sous',
            'dans', 'de', 'du', 'de la', 'des', 'au', 'aux', 'ce', 'cet', 'cette',
            'ces', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
            'notre', 'nos', 'votre', 'vos', 'leur', 'leurs', 'y', 'en', 'a',
            'est', 'sont', 'été', 'être', 'avoir', 'fait', 'faire', 'the', 'a',
            'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
            'must', 'shall', 'can', 'of', 'in', 'is', 'it', 'to', 'for', 'as',
            'on', 'at', 'by', 'this', 'that', 'these', 'those', 'am', 'is', 'are'
        }
        return [token for token in tokens if token not in stop_words and len(token) > 2]

    def fit(self, documents: list[str]) -> None:
        """Entraîne le modèle sur une liste de documents."""
        # Construire le vocabulaire
        word_counts = Counter()
        doc_count = len(documents)

        for doc in documents:
            words = set(self._tokenize(doc))
            word_counts.update(words)

        # Créer le vocabulaire (mots qui apparaissent dans au moins 2 documents)
        self.vocabulary = {
            word: idx for idx, (word, count) in enumerate(
                word for word, count in word_counts.items() if count >= 2
            )
        }

        # Calculer IDF (Inverse Document Frequency)
        self.idf_values = {}
        for word, word_idx in self.vocabulary.items():
            # Compter dans combien de documents ce mot apparaît
            doc_freq = sum(1 for doc in documents if word in self._tokenize(doc))
            self.idf_values[word] = math.log((doc_count + 1) / (doc_freq + 1)) + 1

        self._is_fitted = True

    def transform(self, text: str) -> list[float]:
        """Transforme un texte en vecteur TF-IDF."""
        if not self._is_fitted:
            # Retourner un vecteur zéro si non entraîné
            return [0.0] * max(1, len(self.vocabulary))

        words = self._tokenize(text)
        word_counts = Counter(words)
        total_words = len(words)

        # Calculer TF-IDF
        tfidf_vector = [0.0] * len(self.vocabulary)
        for word, count in word_counts.items():
            if word in self.vocabulary:
                tf = count / max(1, total_words)
                idf = self.idf_values.get(word, 0.0)
                tfidf_vector[self.vocabulary[word]] = tf * idf

        # Normaliser le vecteur
        norm = math.sqrt(sum(x * x for x in tfidf_vector))
        if norm > 0:
            tfidf_vector = [x / norm for x in tfidf_vector]

        return tfidf_vector

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calcule la similarité cosinus entre deux vecteurs."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or n2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


class SemanticSearch:
    """
    Moteur de recherche sémantique qui trouve du code basé sur la signification.

    Combine plusieurs techniques:
    - Recherche textuelle exacte
    - Similarité sémantique (TF-IDF simplifié)
    - Correspondance de noms de fonctions/classes
    - Analyse de contexte
    """

    def __init__(self, knowledge_graph: KnowledgeGraph = None):
        self.kg = knowledge_graph or KnowledgeGraph()
        self.embedder = SimpleEmbedding()
        self._document_vectors: dict[str, list[float]] = {}
        self._is_indexed = False

    def index_codebase(self, root_path: str = ".") -> None:
        """
        Indexe toute la base de code pour la recherche sémantique.

        Args:
            root_path: Racine du projet à indexer
        """
        self.kg = KnowledgeGraph(root_path)
        self.kg.build_from_path()

        # Préparer les documents pour l'entraînement de l'embedding
        documents = []
        file_paths = []

        for file_path, content in self.kg._file_contents.items():
            documents.append(content)
            file_paths.append(file_path)

        # Entraîner l'embedding sur tout le codebase
        if documents:
            self.embedder.fit(documents)

            # Créer les vecteurs pour chaque document
            for file_path, content in self.kg._file_contents.items():
                self._document_vectors[file_path] = self.embedder.transform(content)

        self._is_indexed = True

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Effectue une recherche sémantique pour la requête donnée.

        Args:
            query: Requête de recherche (ex: "fonction qui sauvegarde")
            top_k: Nombre maximum de résultats à retourner

        Returns:
            Liste de résultats de recherche triés par score décroissant
        """
        if not self._is_indexed:
            # Indexer par défaut sur le répertoire courant si pas encore fait
            self.index_codebase()

        results = []

        # 1. Recherche textuelle exacte (comme fallback)
        exact_results = self._exact_text_search(query)
        results.extend(exact_results)

        # 2. Recherche sémantique basée sur l'embedding
        semantic_results = self._semantic_search(query)
        results.extend(semantic_results)

        # 3. Recherche par noms de fonctions/classes
        name_results = self._name_based_search(query)
        results.extend(name_results)

        # Dédupliquer et scorer les résultats
        seen = set()
        unique_results = []
        for result in results:
            # Créer une clé unique pour éviter les doublons
            key = (result.file_path, result.line_number, result.content[:50])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)

        # Trier par score décroissant
        unique_results.sort(key=lambda x: x.score, reverse=True)

        # Retourner les top_k résultats
        return unique_results[:top_k]

    def _exact_text_search(self, query: str) -> List[SearchResult]:
        """Recherche textuelle exacte (comme grep mais optimisée)."""
        results = []
        query_lower = query.lower()

        for file_path, content in self.kg._file_contents.items():
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if query_lower in line.lower():
                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=line_num,
                        content=line.strip(),
                        score=0.8,  # Score fixe pour les correspondances exactes
                        match_type="exact"
                    ))

        return results

    def _semantic_search(self, query: str) -> List[SearchResult]:
        """Recherche basée sur la similarité sémantique (TF-IDF + cosinus)."""
        if not self._is_indexed:
            return []

        query_vector = self.embedder.transform(query)
        results = []

        for file_path, doc_vector in self._document_vectors.items():
            similarity = self.embedder.cosine_similarity(query_vector, doc_vector)
            if similarity > 0.1:  # Seuil de similarité minimal
                # Trouver la ligne la plus pertinente dans le fichier
                content = self.kg._file_contents.get(file_path, "")
                if content:
                    lines = content.split('\n')
                    best_line = ""
                    best_line_num = 1
                    best_line_score = 0.0

                    # Chercher la ligne qui contient le plus de mots de la requête
                    query_words = set(self._tokenize(query))
                    for line_num, line in enumerate(lines, 1):
                        line_words = set(self._tokenize(line))
                        overlap = len(query_words.intersection(line_words))
                        if overlap > best_line_score:
                            best_line_score = overlap
                            best_line = line.strip()
                            best_line_num = line_num

                    # Si aucune bonne ligne trouvée, prendre la première ligne
                    if not best_line and lines:
                        best_line = lines[0].strip()
                        best_line_num = 1

                    results.append(SearchResult(
                        file_path=file_path,
                        line_number=best_line_num,
                        content=best_line,
                        score=similarity * 0.7,  # Pondérer le score
                        match_type="semantic"
                    ))

        return results

    def _name_based_search(self, query: str) -> List[SearchResult]:
        """Recherche basée sur les noms de fonctions, classes, etc."""
        results = []
        query_lower = query.lower()
        query_words = set(self._tokenize(query))

        # Chercher dans les nœuds de fonctions et classes
        for node in self.kg.get_nodes_by_type(NodeType.FUNCTION):
            if self._name_matches_query(node.name, query_lower, query_words):
                # Trouver le contenu de la fonction
                content = self._get_node_content(node)
                if content:
                    lines = content.split('\n')
                    first_line = lines[0].strip() if lines else ""
                    results.append(SearchResult(
                        file_path=node.file_path,
                        line_number=node.line_number,
                        content=first_line,
                        score=0.9,  # Score élevé pour les correspondances de nom
                        match_type="name"
                    ))

        for node in self.kg.get_nodes_by_type(NodeType.CLASS):
            if self._name_matches_query(node.name, query_lower, query_words):
                content = self._get_node_content(node)
                if content:
                    lines = content.split('\n')
                    first_line = lines[0].strip() if lines else ""
                    results.append(SearchResult(
                        file_path=node.file_path,
                        line_number=node.line_number,
                        content=first_line,
                        score=0.9,
                        match_type="name"
                    ))

        return results

    def _name_matches_query(self, name: str, query_lower: str, query_words: set[str]) -> bool:
        """Vérifie si un nom correspond à la requête."""
        name_lower = name.lower()

        # Correspondance exacte du nom
        if query_lower in name_lower:
            return True

        # Correspondance par mots
        name_words = set(self._tokenize(name))
        if query_words.intersection(name_words):
            return True

        # Correspondance partielle (pour les noms composés comme snake_case)
        name_parts = re.split(r'[_\-]', name_lower)
        for part in name_parts:
            if any(query_word in part for query_word in query_words):
                return True

        return False

    def _get_node_content(self, node: Node) -> str:
        """Récupère le contenu approximatif d'un nœud à partir du fichier source."""
        try:
            full_content = self.kg._file_contents.get(node.file_path, "")
            if not full_content:
                return ""

            lines = full_content.split('\n')
            start_line = max(0, node.line_number - 1)

            # Essayer de déterminer la fin du bloc
            end_line = len(lines)
            if node.type == NodeType.FUNCTION:
                # Pour une fonction, prendre jusqu'à la prochaine définition de fonction ou classe de même niveau
                # Ou un nombre fixe de lignes
                end_line = min(len(lines), start_line + 20)
            elif node.type == NodeType.CLASS:
                # Pour une classe, prendre un nombre raisonnable de lignes
                end_line = min(len(lines), start_line + 30)

            return '\n'.join(lines[start_line:end_line])
        except Exception:
            return f"// Contenu de {node.name} non disponible"

    def search_by_example(self, example_code: str, top_k: int = 5) -> List[SearchResult]:
        """
        Recherche du code similaire à un exemple donné.

        Args:
            example_code: Extrait de code à utiliser comme exemple
            top_k: Nombre de résultats à retourner

        Returns:
            Résultats de recherche sémantique basés sur l'exemple
        """
        return self.search(example_code, top_k=top_k)

    def find_similar_functions(self, function_name: str, file_path: str = None,
                              top_k: int = 5) -> List[SearchResult]:
        """
        Trouve des fonctions similaires à une fonction donnée.

        Args:
            function_name: Nom de la fonction de référence
            file_path: Fichier où chercher (None = partout)
            top_k: Nombre de résultats

        Returns:
            Fonctions similaires
        """
        # Construire une requête basée sur le nom et la signature potentielle
        query = f"function {function_name}"
        if file_path:
            query += f" in {file_path}"

        results = self.search(query, top_k=top_k)
        # Filtrer pour ne garder que les fonctions
        return [r for r in results if "def " in r.content or "function" in r.content.lower()]

    def find_related_classes(self, class_name: str, top_k: int = 5) -> List[SearchResult]:
        """
        Trouve des classes liées à une classe donnée (par héritage, utilisation, etc.).

        Args:
            class_name: Nom de la classe de référence
            top_k: Nombre de résultats

        Returns:
            Classes liées
        """
        query = f"class {class_name}"
        results = self.search(query, top_k=top_k)
        # Filtrer pour ne garder que les classes
        return [r for r in results if "class " in r.content]


# Fonction d'aide pour faciliter l'utilisation
def semantic_search(query: str, root_path: str = ".", top_k: int = 10) -> List[SearchResult]:
    """
    Fonction d'aide pour effectuer une recherche sémantique.

    Args:
        query: Requête de recherche
        root_path: Racine du projet à chercher
        top_k: Nombre de résultats à retourner

    Returns:
        Liste de résultats de recherche
    """
    searcher = SemanticSearch()
    searcher.index_codebase(root_path)
    return searcher.search(query, top_k=top_k)


def search_by_example(example_code: str, root_path: str = ".", top_k: int = 5) -> List[SearchResult]:
    """
    Recherche du code similaire à un exemple donné.

    Args:
        example_code: Extrait de code à utiliser comme exemple
        root_path: Racine du projet
        top_k: Nombre de résultats

    Returns:
        Résultats de recherche
    """
    searcher = SemanticSearch()
    searcher.index_codebase(root_path)
    return searcher.search_by_example(example_code, top_k=top_k)