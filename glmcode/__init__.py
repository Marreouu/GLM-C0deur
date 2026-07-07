"""GLM Code — assistant de codage en terminal propulse par GLM-4.7 (API Z.ai)."""

__version__ = "0.1.0"

# Export du moniteur de performance
from .performance_monitor import performance_monitor, profile, record_metric, profile_context

# Export du gestionnaire de runtime
from .runtime import (
    RuntimeManager,
    ShellManager,
    ProcessManager,
    WatchManager,
    EventBus,
    BackgroundTasks,
    RuntimeCache,
    EventType,
    Event,
    get_runtime_manager,
    get_event_bus,
    get_process_manager,
    get_shell_manager,
    get_watch_manager,
    get_background_tasks,
    get_runtime_cache,
    shutdown_runtime,
    background_task
)
