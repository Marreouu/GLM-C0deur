"""Planner intelligent qui décide de la meilleure séquence d'actions pour résoudre une tâche."""

from __future__ import annotations

import asyncio
import enum
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any

from . import ui
from .tools import TOOL_IMPLS, read_file, grep, search_text, list_dir


class ActionType(enum.Enum):
    """Types d'actions que le planner peut planifier."""
    READ_FILE = "read_file"
    SEARCH_TEXT = "search_text"
    GREP = "grep"
    LIST_DIR = "list_dir"
    ANALYZE_CODE = "analyze_code"
    EXECUTE_COMMAND = "execute_command"
    NOOP = "noop"


@dataclass
class Action:
    """Une action à exécuter dans le plan."""
    type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)  # IDs d'actions qui doivent être exécutées avant celle-ci
    id: str = field(default_factory=lambda: str(time.time_ns()))
    result: Optional[Any] = None
    executed: bool = False
    error: Optional[str] = None


@dataclass
class PlanStep:
    """Étape d'un plan contenant une ou plusieurs actions pouvant être exécutées en parallèle."""
    actions: List[Action] = field(default_factory=list)
    description: str = ""

    def is_ready(self, completed_actions: Set[str]) -> bool:
        """Vérifie si toutes les dépendances de l'étape sont satisfaites."""
        for action in self.actions:
            if not action.dependencies.issubset(completed_actions):
                return False
        return True

    def can_execute_now(self, running_actions: Set[str]) -> List[Action]:
        """Retourne les actions qui peuvent être exécutées maintenant (dépendances satisfaites et pas encore en cours)."""
        ready_actions = []
        for action in self.actions:
            if action.id in running_actions:
                continue
            if action.dependencies.issubset(set(a.id for a in self.actions if a.executed)):
                ready_actions.append(action)
        return ready_actions


class Planner:
    """
    Planner qui analyse une demande et crée un plan d'exécution optimal.

    Le planner suit cette architecture:
    Utilisateur → Compréhension → Planner → Sélection des outils → Exécution → Validation → LLM
    """

    def __init__(self):
        self._action_counter = 0

    def _generate_action_id(self) -> str:
        """Génère un ID unique pour une action."""
        self._action_counter += 1
        return f"action_{self._action_counter}_{int(time.time() * 1000)}"

    def create_plan(self, user_request: str, context: Dict[str, Any] = None) -> List[PlanStep]:
        """
        Crée un plan d'exécution pour répondre à la demande de l'utilisateur.

        Args:
            user_request: La demande de l'utilisateur
            context: Contexte supplémentaire (fichiers actuellement ouverts, etc.)

        Returns:
            Liste d'étapes de plan à exécuter en séquence
        """
        if context is None:
            context = {}

        # Étape 1: Comprendre la demande
        understanding_step = self._understand_request(user_request, context)

        # Étape 2: Planifier les actions basée sur la compréhension
        planning_step = self._plan_actions(understanding_step, user_request, context)

        # Étape 3: Optimiser le plan (regrouper les actions parallélisables)
        optimized_steps = self._optimize_plan([understanding_step, planning_step])

        return optimized_steps

    def _understand_request(self, user_request: str, context: Dict[str, Any]) -> PlanStep:
        """Analyse la demande de l'utilisateur pour en extraire l'intention et les entités."""
        actions = []

        # Analyse basique de la demande
        request_lower = user_request.lower()

        # Détecter les intentions principales
        intentions = []
        if any(word in request_lower for word in ["cherche", "trouve", "recherche", "search", "find"]):
            intentions.append("search")
        if any(word in request_lower for word in ["modifie", "change", "update", "edit", "modify"]):
            intentions.append("modify")
        if any(word in request_lower for word in ["crée", "ajoute", "create", "add", "new"]):
            intentions.append("create")
        if any(word in request_lower for word in ["supprime", "delete", "remove", "rm"]):
            intentions.append("delete")
        if any(word in request_lower for word in ["lis", "affiche", "show", "read", "view"]):
            intentions.append("read")
        if any(word in request_lower for word in ["exécute", "run", "execute", "lance", "run"]):
            intentions.append("execute")

        # Extraire les mentions de fichiers (@chemin/fichier)
        import re
        file_mentions = re.findall(r'@(\S+)', user_request)

        # Extraire les termes de recherche potentiels
        search_terms = []
        # Mots significatifs (plus de 3 caractères, pas des mots courants)
        stop_words = {"le", "la", "les", "un", "une", "des", "et", "ou", "mais", "donc",
                     "car", "puisque", "pour", "par", "avec", "sans", "sur", "sous",
                     "dans", "de", "du", "de la", "des", "au", "aux", "ce", "cet", "cette",
                     "ces", "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
                     "notre", "nos", "votre", "vos", "leur", "leurs", "y", "en", "a",
                     "est", "sont", "été", "être", "avoir", "avoir", "fait", "faire"}

        words = [word.strip(".,!?;:()[]{}'\"") for word in user_request.split()]
        significant_words = [w.lower() for w in words if len(w) > 3 and w.lower() not in stop_words]
        search_terms.extend(significant_words[:5])  # Limiter à 5 termes significatifs

        # Créer des actions d'analyse
        if file_mentions:
            for file_mention in file_mentions[:3]:  # Limiter à 3 fichiers
                actions.append(Action(
                    type=ActionType.READ_FILE,
                    params={"path": file_mention},
                    id=self._generate_action_id()
                ))

        if search_terms:
            # Décider où chercher : dans tout le projet ou dans des répertoires spécifiques
            search_path = context.get("current_dir", ".")
            actions.append(Action(
                type=ActionType.SEARCH_TEXT,
                params={"text": " ".join(search_terms), "path": search_path},
                id=self._generate_action_id()
            ))

            # Aussi faire une recherche regex pour plus de flexibilité
            actions.append(Action(
                type=ActionType.GREP,
                params={"pattern": " ".join(search_terms), "path": search_path},
                id=self._generate_action_id()
            ))

        # Toujours lister le répertoire courant pour avoir un contexte
        actions.append(Action(
            type=ActionType.LIST_DIR,
            params={"path": "."},
            id=self._generate_action_id()
        ))

        return PlanStep(
            actions=actions,
            description="Analyse de la demande utilisateur pour identifier les intentions et les entités"
        )

    def _plan_actions(self, understanding_step: PlanStep, user_request: str,
                     context: Dict[str, Any]) -> PlanStep:
        """Planifie les actions concrètes basée sur la compréhension de la demande."""
        actions = []

        # Extraire les informations utiles de l'étape de compréhension
        # (Dans une implémentation plus sophistiquée, on analyserait les résultats)

        # Pour l'instant, une approche simplifiée basée sur des mots-clés
        request_lower = user_request.lower()

        # Si la demande implique une modification de code
        if any(word in request_lower for word in ["modifie", "change", "update", "fix", "corrige"]):
            # Chercher d'abord les fichiers pertinents
            actions.append(Action(
                type=ActionType.GREP,
                params={"pattern": r"def\s+\w+|class\s+\w+", "path": "."},
                id=self._generate_action_id()
            ))

        # Si la demande implique de créer quelque chose
        if any(word in request_lower for word in ["crée", "ajoute", "create", "add", "nouveau"]):
            # Vérifier la structure du projet
            actions.append(Action(
                type=ActionType.LIST_DIR,
                params={"path": "src"},
                id=self._generate_action_id()
            ))
            actions.append(Action(
                type=ActionType.LIST_DIR,
                params={"path": "lib"},
                id=self._generate_action_id()
            ))

        # Si la demande implique de comprendre ou expliquer du code
        if any(word in request_lower for word in ["explique", "comprends", "understand", "explain", "comment"]):
            # Lire les fichiers principaux potentiels
            actions.append(Action(
                type=ActionType.READ_FILE,
                params={"path": "README.md"},
                id=self._generate_action_id()
            ))
            actions.append(Action(
                type=ActionType.READ_FILE,
                params={"path": "main.py"},
                id=self._generate_action_id()
            ))
            actions.append(Action(
                type=ActionType.READ_FILE,
                params={"path": "app.py"},
                id=self._generate_action_id()
            ))

        # Si aucune action spécifique n'a été ajoutée, tomber sur une recherche générale
        if not actions or len([a for a in actions if a.type != ActionType.LIST_DIR]) == 0:
            # Extraire des mots-clés pour une recherche générale
            import re
            words = [w.strip(".,!?;:()[]{}'\"") for w in user_request.split()]
            meaningful_words = [w for w in words if len(w) > 2 and w.lower() not in
                              {"le", "la", "les", "un", "une", "des", "et", "ou", "mais", "donc",
                               "car", "puisque", "pour", "par", "avec", "sans", "sur", "sous",
                               "dans", "de", "du", "de la", "des", "au", "aux", "ce", "cet", "cette",
                               "ces", "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses",
                               "notre", "nos", "votre", "vos", "leur", "leurs", "y", "en", "est",
                               "sont", "été", "être", "avoir", "fait", "faire", "the", "a", "an",
                               "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}]

            if meaningful_words:
                search_query = " ".join(meaningful_words[:4])
                actions.append(Action(
                    type=ActionType.SEARCH_TEXT,
                    params={"text": search_query, "path": "."},
                    id=self._generate_action_id()
                ))

        return PlanStep(
            actions=actions,
            description="Planification des actions spécifiques basée sur l'analyse de la demande"
        )

    def _optimize_plan(self, steps: List[PlanStep]) -> List[PlanStep]:
        """
        Optimise le plan en regroupant les actions qui peuvent être exécutées en parallèle
        et en éliminant les redondances.
        """
        if not steps:
            return steps

        # Pour l'instant, une optimisation simple : s'assurer qu'il n'y a pas de dépendances circulaires
        # et regrouper les actions indépendantes

        optimized_steps = []

        for step in steps:
            if not step.actions:
                continue

            # Séparer les actions par type pour voir ce qui peut être parallélisé
            read_actions = [a for a in step.actions if a.type == ActionType.READ_FILE]
            search_actions = [a for a in step.actions if a.type in (ActionType.SEARCH_TEXT, ActionType.GREP)]
            list_actions = [a for a in step.actions if a.type == ActionType.LIST_DIR]
            other_actions = [a for a in step.actions if a.type not in
                           (ActionType.READ_FILE, ActionType.SEARCH_TEXT, ActionType.GREP, ActionType.LIST_DIR)]

            # Créer des sous-étapes pour les opérations qui peuvent être parallélisées
            if read_actions:
                optimized_steps.append(PlanStep(
                    actions=read_actions,
                    description="Lecture de fichiers (peut être parallélisée)"
                ))

            if search_actions:
                optimized_steps.append(PlanStep(
                    actions=search_actions,
                    description="Recherche de texte (peut être parallélisée)"
                ))

            if list_actions:
                # Généralement, un seul ls suffit
                optimized_steps.append(PlanStep(
                    actions=list_actions[:1],
                    description="Listage de répertoire"
                ))

            if other_actions:
                optimized_steps.append(PlanStep(
                    actions=other_actions,
                    description="Autres opérations"
                ))

        return [step for step in optimized_steps if step.actions]

    async def execute_plan(self, plan: List[PlanStep]) -> List[PlanStep]:
        """
        Exécute un plan en respectant les dépendances et en parallélisant quand possible.

        Returns:
            Le plan avec les résultats remplis dans chaque action
        """
        completed_actions: Set[str] = set()
        failed_actions: Set[str] = set()

        for step_index, step in enumerate(plan):
            # Attendre que toutes les dépendances de l'étape soient satisfaites
            while not step.is_ready(completed_actions):
                # Vérifier si on est bloqué à cause d'échecs
                blocking_failed = False
                for action in step.actions:
                    if action.dependencies & failed_actions:
                        blocking_failed = True
                        break
                if blocking_failed:
                    # Marquer toutes les actions de cette étape comme échouées
                    for action in step.actions:
                        if action.id not in completed_actions and action.id not in failed_actions:
                            action.error = "Dépendance échouée"
                            action.executed = True
                            failed_actions.add(action.id)
                    break

                # Attendre un peu avant de revérifier
                await asyncio.sleep(0.1)

            if blocking_failed:
                continue

            # Exécuter les actions qui peuvent l'être maintenant
            ready_actions = step.can_execute_now(set())

            # Exécuter en parallèle les actions prêtes
            if ready_actions:
                tasks = []
                for action in ready_actions:
                    task = asyncio.create_task(self._execute_action(action))
                    tasks.append((action, task))

                # Attendre que toutes les tâches soient terminées
                for action, task in tasks:
                    try:
                        action.result = await task
                        action.executed = True
                        completed_actions.add(action.id)
                    except Exception as e:
                        action.error = str(e)
                        action.executed = True
                        failed_actions.add(action.id)

        return plan

    async def _execute_action(self, action: Action) -> Any:
        """Exécute une action individuelle et retourne son résultat."""
        try:
            if action.type == ActionType.READ_FILE:
                return read_file(path=action.params.get("path", "."))
            elif action.type == ActionType.SEARCH_TEXT:
                return search_text(text=action.params.get("text", ""), path=action.params.get("path", "."))
            elif action.type == ActionType.GREP:
                return grep(pattern=action.params.get("pattern", ""), path=action.params.get("path", "."))
            elif action.type == ActionType.LIST_DIR:
                return list_dir(path=action.params.get("path", "."))
            elif action.type == ActionType.EXECUTE_COMMAND:
                # Cette action nécessiterait l'accès à run_command depuis tools
                from .tools import run_command
                return run_command(command=action.params.get("command", ""))
            else:
                # Pour les autres types d'actions, retourner un placeholder
                return f"[action non implémentée: {action.type.value}]"
        except Exception as e:
            raise Exception(f"Échec de l'exécution de l'action {action.type.value}: {e}")


# Fonction d'aide pour faciliter l'utilisation
def create_plan(user_request: str, context: Dict[str, Any] = None) -> List[PlanStep]:
    """
    Fonction d'aide pour créer un plan d'exécution.

    Args:
        user_request: La demande de l'utilisateur
        context: Contexte supplémentaire

    Returns:
        Liste d'étapes de plan
    """
    planner = Planner()
    return planner.create_plan(user_request, context)


async def execute_plan(plan: List[PlanStep]) -> List[PlanStep]:
    """
    Fonction d'aide pour exécuter un plan.

    Args:
        Plan: Le plan à exécuter

    Returns:
        Le plan avec les résultats
    """
    planner = Planner()
    return await planner.execute_plan(plan)