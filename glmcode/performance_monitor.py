"""Système de profiling et de benchmarking pour mesurer les performances."""

from __future__ import annotations

import time
import functools
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
import json
import os
from pathlib import Path
from collections import defaultdict
import psutil
import os


@dataclass
class PerformanceMetric:
    """Métrique de performance mesurée."""
    name: str
    value: float
    unit: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class ProfileResult:
    """Résultat d'un profilage."""
    operation: str
    start_time: float
    end_time: float
    duration: float
    metrics: List[PerformanceMetric] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "timestamp": m.timestamp,
                    "metadata": m.metadata
                }
                for m in self.metrics
            ]
        }


class PerformanceMonitor:
    """Moniteur de performance global pour suivre les métriques du système."""

    _instance: Optional['PerformanceMonitor'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self._active_profiles: Dict[str, ProfileResult] = {}
        self._profile_history: List[ProfileResult] = []
        self._system_info = self._get_system_info()
        self._enabled = True
        self._initialized = True

    def _get_system_info(self) -> dict:
        """Récupère les informations système de base."""
        try:
            return {
                "cpu_count": os.cpu_count() or 1,
                "memory_total": psutil.virtual_memory().total,
                "platform": os.name,
                "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}"
            }
        except Exception:
            return {
                "cpu_count": 1,
                "memory_total": 0,
                "platform": "unknown",
                "python_version": "unknown"
            }

    def enable(self):
        """Active le profilage."""
        self._enabled = True

    def disable(self):
        """Désactive le profilage."""
        self._enabled = False

    @contextmanager
    def profile(self, operation_name: str):
        """Context manager pour profiler une opération."""
        if not self._enabled:
            yield
            return

        start_time = time.perf_counter()
        profile_id = f"{operation_name}_{start_time}_{threading.get_ident()}"

        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time

            result = ProfileResult(
                operation=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )

            self._profile_history.append(result)
            # Limiter l'historique pour éviter une consommation mémoire excessive
            if len(self._profile_history) > 1000:
                self._profile_history = self._profile_history[-500:]

    def record_metric(self, name: str, value: float, unit: str = "", metadata: Optional[dict] = None):
        """Enregistre une métrique de performance."""
        if not self._enabled:
            return

        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            metadata=metadata or {}
        )

        self._metrics[name].append(metric)
        # Limiter l'historique des métriques
        if len(self._metrics[name]) > 1000:
            self._metrics[name] = self._metrics[name][-500:]

    def time_function(self, operation_name: str = None):
        """
        Décorateur pour mesurer le temps d'exécution d'une fonction.

        Args:
            operation_name: Nom de l'opération (par défaut, nom de la fonction)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                with self.profile(op_name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_metrics_summary(self) -> dict:
        """Obtient un résumé des métriques collectées."""
        summary = {}
        for metric_name, metrics in self._metrics.items():
            if not metrics:
                continue

            values = [m.value for m in metrics]
            summary[metric_name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else 0,
                "unit": metrics[0].unit if metrics else ""
            }
        return summary

    def get_recent_profiles(self, limit: int = 10) -> List[dict]:
        """Obtient les profils récents."""
        recent = self._profile_history[-limit:] if self._profile_history else []
        return [p.to_dict() for p in reversed(recent)]

    def get_operation_stats(self, operation_name: str) -> dict:
        """Obtient les statistiques pour une opération spécifique."""
        durations = [
            p.duration for p in self._profile_history
            if p.operation == operation_name
        ]

        if not durations:
            return {"count": 0}

        return {
            "count": len(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
            "total": sum(durations)
        }

    def reset(self):
        """Réinitialise toutes les métriques et l'historique."""
        self._metrics.clear()
        self._profile_history.clear()

    def export_report(self, file_path: str = "performance_report.json"):
        """Exporte un rapport de performance détaillé."""
        report = {
            "timestamp": time.time(),
            "system_info": self._system_info,
            "metrics_summary": self.get_metrics_summary(),
            "recent_profiles": self.get_recent_profiles(50),
            "operation_stats": {
                op: self.get_operation_stats(op)
                for op in set(p.operation for p in self._profile_history)
            }
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return file_path


# Instance globale du moniteur de performance
performance_monitor = PerformanceMonitor()


# Fonctions d'aide pour faciliter l'utilisation
def profile(operation_name: str):
    """Décorateur pour profiler une fonction."""
    return performance_monitor.time_function(operation_name)


def record_metric(name: str, value: float, unit: str = "", metadata: Optional[dict] = None):
    """Enregistre une métrique de performance."""
    performance_monitor.record_metric(name, value, unit, metadata)


@contextmanager
def profile_context(operation_name: str):
    """Context manager pour profiler une section de code."""
    with performance_monitor.profile(operation_name):
        yield


def get_performance_summary() -> dict:
    """Obtient un résumé des performances."""
    return performance_monitor.get_metrics_summary()


def export_performance_report(file_path: str = "performance_report.json") -> str:
    """Exporte un rapport de performance."""
    return performance_monitor.export_report(file_path)


def reset_performance_data():
    """Réinitialise toutes les données de performance."""
    performance_monitor.reset()


# Décorateurs spécialisés pour différents types d'opérations
def profile_io(func: Callable) -> Callable:
    """Décorateur spécialisé pour les opérations d'entrée/sortie."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            record_metric(
                f"{func.__module__}.{func.__name__}_io_time",
                duration,
                "seconds",
                {"function": func.__name__, "module": func.__module__}
            )
    return wrapper


def profile_cpu(func: Callable) -> Callable:
    """Décorateur spécialisé pour les opérations CPU-intensives."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Mesurer l'utilisation CPU avant
        process = psutil.Process(os.getpid())
        cpu_before = process.cpu_percent()

        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            cpu_after = process.cpu_percent()
            duration = end_time - start_time

            record_metric(
                f"{func.__module__}.{func.__name__}_cpu_time",
                duration,
                "seconds",
                {"function": func.__name__, "module": func.__module__}
            )

            record_metric(
                f"{func.__module__}.{func.__name__}_cpu_usage",
                cpu_after - cpu_before,
                "percent",
                {"function": func.__name__, "module": func.__module__}
            )
    return wrapper


def profile_memory(func: Callable) -> Callable:
    """Décorateur spécialisé pour mesurer l'utilisation mémoire."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Mesurer l'utilisation mémoire avant
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Mesurer l'utilisation mémoire après
            memory_after = process.memory_info().rss
            memory_diff = memory_after - memory_before

            record_metric(
                f"{func.__module__}.{func.__name__}_memory",
                memory_diff,
                "bytes",
                {"function": func.__name__, "module": func.__module__}
            )
    return wrapper


# Décorateur combiné pour surveiller toutes les aspects
def profile_all(func: Callable) -> Callable:
    """Décorateur qui profile I/O, CPU et mémoire."""
    return profile_io(profile_cpu(profile_memory(func)))


if __name__ == "__main__":
    # Exemple d'utilisation
    import time

    @profile("exemple_operation")
    def exemple_fonction():
        time.sleep(0.1)
        return "resultat"

    # Utiliser le décorateur
    resultat = exemple_fonction()

    # Utiliser le context manager
    with profile_context("section_de_code"):
        time.sleep(0.05)

    # Enregistrer des métriques personnalisées
    record_metric("custom_metric", 42.5, "units", {"source": "exemple"})

    # Afficher le résumé
    print("Résumé des performances:")
    print(json.dumps(get_performance_summary(), indent=2))

    # Exporter un rapport
    report_file = export_performance_report("example_performance_report.json")
    print(f"\nRapport exporté vers: {report_file}")