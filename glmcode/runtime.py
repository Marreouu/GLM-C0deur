"""Gestionnaire d'exécution pour maintenir des états persistants pendant la session."""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from queue import Queue
from threading import Thread, Event as ThreadEvent
from typing import Dict, List, Optional, Set, Callable, Any
import subprocess
import sys
import os

try:
    import psutil
except ImportError:
    psutil = None

from . import ui
from .performance_monitor import profile, record_metric


class EventType(Enum):
    """Types d'événements dans le système."""
    FILE_CHANGED = "file_changed"
    DIRECTORY_CHANGED = "directory_changed"
    GIT_CHANGE = "git_change"
    PROCESS_STARTED = "process_started"
    PROCESS_STOPPED = "process_stopped"
    COMMAND_EXECUTED = "command_executed"
    ERROR_OCCURRED = "error_occurred"
    HEARTBEAT = "heartbeat"


@dataclass
class Event:
    """Événement transmis par le EventBus."""
    type: EventType
    data: dict
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class EventBus:
    """Bus d'événements central pour la communication entre composants."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self._event_queue: Queue = Queue()
        self._running = False
        self._thread: Optional[Thread] = None

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """S'abonner à un type d'événement spécifique."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Se désabonner d'un type d'événement."""
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> None:
        """Publier un événement sur le bus."""
        self._event_queue.put(event)

    def start(self) -> None:
        """Démarrer le traitement des événements en arrière-plan."""
        if self._running:
            return

        self._running = True
        self._thread = Thread(target=self._process_events, daemon=True)
        self._thread.start()
        record_metric("event_bus_started", 1, "count")

    def stop(self) -> None:
        """Arrêter le traitement des événements."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        record_metric("event_bus_stopped", 1, "count")

    def _process_events(self) -> None:
        """Boucle de traitement des événements (exécutée dans un thread séparé)."""
        while self._running:
            try:
                # Attendre un événement avec timeout pour permettre de vérifier _running
                try:
                    event = self._event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Traiter l'événement
                if event.type in self._subscribers:
                    for callback in self._subscribers[event.type]:
                        try:
                            callback(event)
                        except Exception as e:
                            # Publier l'erreur plutôt que de laisser le thread mourir
                            error_event = Event(
                                type=EventType.ERROR_OCCURRED,
                                data={"error": str(e), "original_event": event.__dict__},
                                source="EventBus"
                            )
                            self._event_queue.put(error_event)

                self._event_queue.task_done()

            except Exception as e:
                # Erreur dans la boucle principale de traitement
                print(f"[erreur] EventBus processing error: {e}")


@dataclass
class ProcessInfo:
    """Informations sur un processus en cours d'exécution."""
    pid: int
    name: str
    command: List[str]
    start_time: float
    status: str = "running"
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class ProcessManager:
    """Gestionnaire de processus pour suivre et contrôler les processus système."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._processes: Dict[int, ProcessInfo] = {}
        self._lock = threading.RLock()

    @profile("process_start")
    def start_process(self, name: str, command: List[str]) -> Optional[ProcessInfo]:
        """Démarrer un nouveau processus et le suivre."""
        try:
            # Démarrer le processus
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Créer les informations de suivi
            proc_info = ProcessInfo(
                pid=process.pid,
                name=name,
                command=command.copy(),
                start_time=time.time(),
                status="running"
            )

            # Stocker les informations
            with self._lock:
                self._processes[process.pid] = proc_info

            # Publier l'événement
            event = Event(
                type=EventType.PROCESS_STARTED,
                data={
                    "pid": process.pid,
                    "name": name,
                    "command": command
                },
                source="ProcessManager"
            )
            self.event_bus.publish(event)

            # Démarrer un thread pour surveiller la sortie du processus
            Thread(target=self._monitor_process_output,
                   args=(process, process.pid),
                   daemon=True).start()

            record_metric("process_started", 1, "count", {"process_name": name})
            return proc_info

        except Exception as e:
            error_msg = f"Failed to start process {name}: {e}"
            print(f"[erreur] {error_msg}")

            # Publier l'erreur
            error_event = Event(
                type=EventType.ERROR_OCCURRED,
                data={"error": error_msg, "process_name": name},
                source="ProcessManager"
            )
            self.event_bus.publish(error_event)

            return None

    def stop_process(self, pid: int) -> bool:
        """Arrêter un processus en cours d'exécution."""
        with self._lock:
            if pid not in self._processes:
                return False

            proc_info = self._processes[pid]

        try:
            # Essayer d'arrêter proprement d'abord
            proc = subprocess.Popen(
                ["taskkill" if sys.platform == "win32" else "kill",
                 "/PID" if sys.platform == "win32" else str(pid), str(pid)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            proc.wait(timeout=5)

            # Si toujours en vie, forcer l'arrêt
            if psutil is not None and psutil.pid_exists(pid):
                proc = subprocess.Popen(
                    ["taskkill" if sys.platform == "win32" else "kill",
                     "/F" if sys.platform == "win32" else "-9",
                     "/PID" if sys.platform == "win32" else str(pid), str(pid)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                proc.wait(timeout=5)

            # Mettre à jour le statut
            with self._lock:
                if pid in self._processes:
                    self._processes[pid].status = "stopped"
                    # Nettoyer après un délai
                    threading.Timer(30.0, self._cleanup_process, args=[pid]).start()

            # Publier l'événement
            event = Event(
                type=EventType.PROCESS_STOPPED,
                data={"pid": pid, "name": proc_info.name},
                source="ProcessManager"
            )
            self.event_bus.publish(event)

            record_metric("process_stopped", 1, "count", {"process_name": proc_info.name})
            return True

        except Exception as e:
            error_msg = f"Failed to stop process {pid}: {e}"
            print(f"[erreur] {error_msg}")

            # Publier l'erreur
            error_event = Event(
                type=EventType.ERROR_OCCURRED,
                data={"error": error_msg, "pid": pid},
                source="ProcessManager"
            )
            self.event_bus.publish(error_event)

            return False

    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """Obtenir les informations sur un processus spécifique."""
        with self._lock:
            return self._processes.get(pid)

    def list_processes(self) -> List[ProcessInfo]:
        """Lister tous les processus suivis."""
        with self._lock:
            return list(self._processes.values())

    def _monitor_process_output(self, process: subprocess.Popen, pid: int) -> None:
        """Surveiller la sortie d'un processus en arrière-plan."""
        try:
            # Lire stdout et stderr en temps réel
            stdout_lines = []
            stderr_lines = []

            # Fonction pour lire un flux en arrière-plan
            def read_stream(stream, lines_list):
                try:
                    for line in iter(stream.readline, ''):
                        lines_list.append(line)
                        if not line:  # Fin du flux
                            break
                except Exception:
                    pass  # Ignorer les erreurs de lecture
                finally:
                    stream.close()

            # Démarrer les threads de lecture
            stdout_thread = Thread(target=read_stream, args=(process.stdout, stdout_lines), daemon=True)
            stderr_thread = Thread(target=read_stream, args=(process.stderr, stderr_lines), daemon=True)

            stdout_thread.start()
            stderr_thread.start()

            # Attendre la fin du processus
            return_code = process.wait()

            # Attendre que les threads de lecture se terminent
            stdout_thread.join(timeout=1.0)
            stderr_thread.join(timeout=1.0)

            # Mettre à jour les informations du processus
            stdout_content = ''.join(stdout_lines)
            stderr_content = ''.join(stderr_lines)

            with self._lock:
                if pid in self._processes:
                    self._processes[pid].stdout = stdout_content
                    self._processes[pid].stderr = stderr_content
                    self._processes[pid].status = f"finished_{return_code}"

            # Publier l'événement de fin
            event = Event(
                type=EventType.PROCESS_STOPPED,
                data={
                    "pid": pid,
                    "return_code": return_code,
                    "stdout_length": len(stdout_content),
                    "stderr_length": len(stderr_content)
                },
                source="ProcessManager"
            )
            self.event_bus.publish(event)

        except Exception as e:
            error_msg = f"Error monitoring process {pid}: {e}"
            print(f"[erreur] {error_msg}")

            # Publier l'erreur
            error_event = Event(
                type=EventType.ERROR_OCCURRED,
                data={"error": error_msg, "pid": pid},
                source="ProcessManager"
            )
            self.event_bus.publish(error_event)

    def _cleanup_process(self, pid: int) -> None:
        """Nettoyer les informations d'un processus après un délai."""
        with self._lock:
            if pid in self._processes:
                del self._processes[pid]


class ShellManager:
    """Gestionnaire de shell persistant pour différentes interfaces (PowerShell, CMD, Bash, WSL)."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._shells: Dict[str, subprocess.Popen] = {}
        self._shell_queues: Dict[str, Queue] = {}
        self._shell_threads: Dict[str, Thread] = {}
        self._shell_outputs: Dict[str, List[str]] = {}

    def get_or_create_shell(self, shell_type: str) -> Optional[subprocess.Popen]:
        """Obtenir ou créer un shell du type spécifié."""
        if shell_type in self._shells:
            # Vérifier si le shell est toujours actif
            if self._shells[shell_type].poll() is None:
                return self._shells[shell_type]
            else:
                # Le shell s'est terminé, le nettoyer
                self._cleanup_shell(shell_type)

        # Créer un nouveau shell
        shell_process = self._create_shell(shell_type)
        if shell_process:
            self._shells[shell_type] = shell_process
            self._shell_queues[shell_type] = Queue()
            self._shell_outputs[shell_type] = []

            # Démarrer le thread de lecture de sortie
            thread = Thread(target=self._monitor_shell_output,
                          args=(shell_type, shell_process),
                          daemon=True)
            self._shell_threads[shell_type] = thread
            thread.start()

            # Publier l'événement
            event = Event(
                type=EventType.COMMAND_EXECUTED,
                data={"shell_type": shell_type, "action": "created"},
                source="ShellManager"
            )
            self.event_bus.publish(event)

        return shell_process

    def _create_shell(self, shell_type: str) -> Optional[subprocess.Popen]:
        """Créer une nouvelle instance de shell."""
        try:
            if shell_type.lower() == "powershell" and sys.platform == "win32":
                cmd = ["powershell.exe", "-NoLogo", "-NoExit"]
            elif shell_type.lower() == "cmd" and sys.platform == "win32":
                cmd = ["cmd.exe"]
            elif shell_type.lower() == "bash":
                if sys.platform == "win32":
                    # Essayer WSL d'abord
                    try:
                        subprocess.run(["wsl", "--status"],
                                     capture_output=True, check=True)
                        cmd = ["wsl", "bash"]
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        # Fallback sur Git bash ou similaire
                        cmd = ["bash"]
                else:
                    cmd = ["bash"]
            elif shell_type.lower() == "wsl" and sys.platform == "win32":
                cmd = ["wsl"]
            else:
                # Shell par défaut du système
                cmd = [os.environ.get("SHELL", "sh")]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            return process

        except Exception as e:
            print(f"[erreur] Failed to create {shell_type} shell: {e}")
            return None

    def execute_command(self, shell_type: str, command: str) -> Optional[str]:
        """Exécuter une commande dans un shell spécifique."""
        shell = self.get_or_create_shell(shell_type)
        if not shell or not shell.stdin:
            return None

        try:
            # Envoyer la commande
            shell.stdin.write(command + '\n')
            shell.stdin.flush()

            # Attendre un court moment pour que la commande s'exécute
            time.sleep(0.1)

            # Récupérer la sortie depuis notre buffer
            output_lines = []
            start_time = time.time()
            while time.time() - start_time < 2.0:  # Timeout de 2 secondes
                try:
                    line = self._shell_queues[shell_type].get_nowait()
                    if line == "__END_OF_COMMAND__":
                        break
                    output_lines.append(line)
                except queue.Empty:
                    if self._shells[shell_type].poll() is not None:
                        break  # Le shell s'est terminé
                    continue

            output = ''.join(output_lines).strip()

            # Publier l'événement
            event = Event(
                type=EventType.COMMAND_EXECUTED,
                data={
                    "shell_type": shell_type,
                    "command": command,
                    "output_length": len(output)
                },
                source="ShellManager"
            )
            self.event_bus.publish(event)

            return output if output else None

        except Exception as e:
            print(f"[erreur] Failed to execute command in {shell_type}: {e}")
            return None

    def _monitor_shell_output(self, shell_type: str, process: subprocess.Popen) -> None:
        """Surveiller la sortie d'un shell en arrière-plan."""
        buffer = ""
        try:
            while True:
                # Lire un caractère à la fois pour détecter les invites de commande
                char = process.stdout.read(1)
                if not char:
                    break  # Fin du flux

                buffer += char

                # Vérifier si nous avons atteint la fin d'une commande
                # (Simple heuristique : retour à la ligne suivi d'une invite)
                if buffer.endswith('\n') and len(buffer) > 1:
                    # Vérifier si cela ressemble à une invite de commande
                    lines = buffer.split('\n')
                    if len(lines) >= 2:
                        potential_prompt = lines[-2].strip()
                        # Heuristique simple pour détecter une invite
                        if (prompt_indicators := ['>', '$', '#', 'PS']) and \
                           any(potential_prompt.endswith(indicator) for indicator in prompt_indicators):
                            # Envoyer la sortie accumulée (sans la dernière ligne qui est l'invite)
                            output_to_send = '\n'.join(lines[:-1])
                            self._shell_queues[shell_type].put(output_to_send)
                            self._shell_queues[shell_type].put("__END_OF_COMMAND__")
                            buffer = lines[-1]  # Garder seulement l'invite pour le prochain cycle

                # Éviter que le buffer ne devienne trop grand
                if len(buffer) > 10000:
                    buffer = buffer[-5000:]  # Garder les derniers 5000 caractères

        except Exception as e:
            print(f"[erreur] Error monitoring {shell_type} shell output: {e}")
        finally:
            # Nettoyer lorsque le shell se termine
            self._cleanup_shell(shell_type)

    def _cleanup_shell(self, shell_type: str) -> None:
        """Nettoyer les ressources associées à un shell."""
        if shell_type in self._shells:
            try:
                self._shells[shell_type].terminate()
                self._shells[shell_type].wait(timeout=5)
            except Exception:
                try:
                    self._shells[shell_type].kill()
                except Exception:
                    pass
            finally:
                del self._shells[shell_type]

        if shell_type in self._shell_queues:
            del self._shell_queues[shell_type]

        if shell_type in self._shell_threads:
            # Le thread se terminera naturellement lorsque le processus se terminera
            del self._shell_threads[shell_type]

        if shell_type in self._shell_outputs:
            del self._shell_outputs[shell_type]

    def shutdown_all(self) -> None:
        """Arrêter tous les shells."""
        for shell_type in list(self._shells.keys()):
            self._cleanup_shell(shell_type)


class WatchManager:
    """Gestionnaire de surveillance pour les fichiers, dossiers et dépôts Git."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._watches: Dict[str, dict] = {}
        self._watch_threads: Dict[str, Thread] = {}
        self._stop_events: Dict[str, ThreadEvent] = {}
        self._last_states: Dict[str, any] = {}

    def watch_file(self, file_path: str, callback: Optional[Callable[[str], None]] = None) -> bool:
        """Surveiller un fichier pour les modifications."""
        try:
            path = Path(file_path).resolve()
            if not path.exists():
                print(f"[erreur] File does not exist: {file_path}")
                return False

            watch_id = f"file:{file_path}"
            if watch_id in self._watches:
                return True  # Déjà surveillé

            # Stocker l'état initial
            self._last_states[watch_id] = {
                "modified_time": path.stat().st_mtime,
                "size": path.stat().st_size
            }

            # Créer l'événement d'arrêt pour ce watch
            stop_event = ThreadEvent()
            self._stop_events[watch_id] = stop_event

            # Démarrer le thread de surveillance
            thread = Thread(target=self._watch_file_thread,
                          args=(watch_id, path, stop_event, callback),
                          daemon=True)
            self._watch_threads[watch_id] = thread
            thread.start()

            self._watches[watch_id] = {
                "type": "file",
                "path": str(path),
                "callback": callback
            }

            # Publier l'événement
            event = Event(
                type=EventType.FILE_CHANGED,
                data={"watch_id": watch_id, "path": file_path, "action": "started_watching"},
                source="WatchManager"
            )
            self.event_bus.publish(event)

            return True

        except Exception as e:
            print(f"[erreur] Failed to watch file {file_path}: {e}")
            return False

    def watch_directory(self, dir_path: str, callback: Optional[Callable[[dict], None]] = None,
                         ignore_dirs: Optional[Set[str]] = None, poll_delay: float = 2.0) -> bool:
        """Surveiller un répertoire pour les modifications.

        `ignore_dirs` exclut des sous-dossiers bruyants (`.git`, `__pycache__`,
        `.remember`, ...) de la surveillance. Le callback recoit un dict
        {"path", "added", "removed", "modified"} (chemins relatifs) plutot que
        le seul chemin racine, pour permettre d'identifier precisement ce qui
        a change.
        """
        try:
            path = Path(dir_path).resolve()
            if not path.exists() or not path.is_dir():
                print(f"[erreur] Directory does not exist: {dir_path}")
                return False

            watch_id = f"dir:{dir_path}"
            if watch_id in self._watches:
                return True  # Déjà surveillé

            # Stocker l'état initial (liste des fichiers avec leurs timestamps)
            self._last_states[watch_id] = self._get_directory_state(path, ignore_dirs)

            # Créer l'événement d'arrêt pour ce watch
            stop_event = ThreadEvent()
            self._stop_events[watch_id] = stop_event

            # Démarrer le thread de surveillance
            thread = Thread(target=self._watch_directory_thread,
                          args=(watch_id, path, stop_event, callback, ignore_dirs, poll_delay),
                          daemon=True)
            self._watch_threads[watch_id] = thread
            thread.start()

            self._watches[watch_id] = {
                "type": "directory",
                "path": str(path),
                "callback": callback
            }

            # Publier l'événement
            event = Event(
                type=EventType.DIRECTORY_CHANGED,
                data={"watch_id": watch_id, "path": dir_path, "action": "started_watching"},
                source="WatchManager"
            )
            self.event_bus.publish(event)

            return True

        except Exception as e:
            print(f"[erreur] Failed to watch directory {dir_path}: {e}")
            return False

    def watch_git_repo(self, repo_path: str = ".", callback: Optional[Callable[[str], None]] = None) -> bool:
        """Surveiller un dépôt Git pour les modifications."""
        try:
            path = Path(repo_path).resolve()
            if not (path / ".git").exists():
                print(f"[erreur] Not a git repository: {repo_path}")
                return False

            watch_id = f"git:{repo_path}"
            if watch_id in self._watches:
                return True  # Déjà surveillé

            # Stocker l'état initial (dernier commit)
            self._last_states[watch_id] = self._get_git_state(path)

            # Créer l'événement d'arrêt pour ce watch
            stop_event = ThreadEvent()
            self._stop_events[watch_id] = stop_event

            # Démarrer le thread de surveillance
            thread = Thread(target=self._watch_git_thread,
                          args=(watch_id, path, stop_event, callback),
                          daemon=True)
            self._watch_threads[watch_id] = thread
            thread.start()

            self._watches[watch_id] = {
                "type": "git",
                "path": str(path),
                "callback": callback
            }

            # Publier l'événement
            event = Event(
                type=EventType.GIT_CHANGE,
                data={"watch_id": watch_id, "path": repo_path, "action": "started_watching"},
                source="WatchManager"
            )
            self.event_bus.publish(event)

            return True

        except Exception as e:
            print(f"[erreur] Failed to watch git repo {repo_path}: {e}")
            return False

    def unwatch(self, watch_id: str) -> bool:
        """Arrêter la surveillance d'une ressource."""
        if watch_id not in self._watches:
            return False

        # Signaler l'arrêt
        if watch_id in self._stop_events:
            self._stop_events[watch_id].set()

        # Attendre que le thread se termine (avec timeout)
        if watch_id in self._watch_threads:
            thread = self._watch_threads[watch_id]
            thread.join(timeout=5.0)
            del self._watch_threads[watch_id]

        # Nettoyer les ressources
        watch_info = self._watches.pop(watch_id, None)
        self._stop_events.pop(watch_id, None)
        self._last_states.pop(watch_id, None)

        # Publier l'événement
        event_type_map = {
            "file": EventType.FILE_CHANGED,
            "directory": EventType.DIRECTORY_CHANGED,
            "git": EventType.GIT_CHANGE
        }
        event_type = event_type_map.get(watch_info["type"] if watch_info else None, EventType.FILE_CHANGED)

        event = Event(
            type=event_type,
            data={"watch_id": watch_id, "action": "stopped_watching"},
            source="WatchManager"
        )
        self.event_bus.publish(event)

        return True

    def _get_file_state(self, path: Path) -> dict:
        """Obtenir l'état actuel d'un fichier."""
        stat = path.stat()
        return {
            "modified_time": stat.st_mtime,
            "size": stat.st_size
        }

    def _get_directory_state(self, path: Path, ignore_dirs: Optional[Set[str]] = None) -> dict:
        """Obtenir l'état actuel d'un répertoire (dossiers de `ignore_dirs` exclus)."""
        ignore_dirs = ignore_dirs or set()
        files_info = {}
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
                for fname in files:
                    if fname.startswith("."):
                        continue
                    item = Path(root) / fname
                    try:
                        stat = item.stat()
                    except OSError:
                        continue
                    rel_path = str(item.relative_to(path))
                    files_info[rel_path] = {
                        "modified_time": stat.st_mtime,
                        "size": stat.st_size
                    }
        except Exception:
            pass  # Ignorer les erreurs d'accès
        return files_info

    def _get_git_state(self, path: Path) -> str:
        """Obtenir l'état actuel d'un dépôt Git (hash du dernier commit)."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def _watch_file_thread(self, watch_id: str, path: Path, stop_event: ThreadEvent,
                          callback: Optional[Callable[[str], None]]) -> None:
        """Thread de surveillance pour un fichier."""
        last_state = self._last_states.get(watch_id, {})

        while not stop_event.is_set():
            try:
                current_state = self._get_file_state(path)

                # Vérifier les changements
                if (last_state.get("modified_time") != current_state.get("modified_time") or
                    last_state.get("size") != current_state.get("size")):

                    # Mettre à jour l'état
                    self._last_states[watch_id] = current_state

                    # Publier l'événement
                    event = Event(
                        type=EventType.FILE_CHANGED,
                        data={
                            "watch_id": watch_id,
                            "path": str(path),
                            "change_type": "modified"
                        },
                        source="WatchManager"
                    )
                    self.event_bus.publish(event)

                    # Appeler le callback si fourni
                    if callback:
                        try:
                            callback(str(path))
                        except Exception as e:
                            print(f"[erreur] Error in file watch callback: {e}")

                # Attendre avant la prochaine vérification
                last_state = current_state
                time.sleep(1.0)

            except Exception as e:
                print(f"[erreur] Error in file watch thread for {watch_id}: {e}")
                time.sleep(5.0)  # Attendre plus longtemps en cas d'erreur

    def _watch_directory_thread(self, watch_id: str, path: Path, stop_event: ThreadEvent,
                               callback: Optional[Callable[[dict], None]],
                               ignore_dirs: Optional[Set[str]] = None,
                               poll_delay: float = 2.0) -> None:
        """Thread de surveillance pour un répertoire."""
        last_state = self._last_states.get(watch_id, {})

        while not stop_event.is_set():
            try:
                current_state = self._get_directory_state(path, ignore_dirs)

                # Comparer les états
                added = set(current_state.keys()) - set(last_state.keys())
                removed = set(last_state.keys()) - set(current_state.keys())
                modified = {
                    name for name in set(current_state.keys()) & set(last_state.keys())
                    if (current_state[name].get("modified_time") != last_state[name].get("modified_time") or
                        current_state[name].get("size") != last_state[name].get("size"))
                }

                # S'il y a des changements
                if added or removed or modified:
                    # Mettre à jour l'état
                    self._last_states[watch_id] = current_state

                    # Publier l'événement
                    event = Event(
                        type=EventType.DIRECTORY_CHANGED,
                        data={
                            "watch_id": watch_id,
                            "path": str(path),
                            "added": list(added),
                            "removed": list(removed),
                            "modified": list(modified)
                        },
                        source="WatchManager"
                    )
                    self.event_bus.publish(event)

                    # Appeler le callback si fourni
                    if callback:
                        try:
                            callback({
                                "path": str(path),
                                "added": sorted(added),
                                "removed": sorted(removed),
                                "modified": sorted(modified),
                            })
                        except Exception as e:
                            print(f"[erreur] Error in directory watch callback: {e}")

                # Attendre avant la prochaine vérification
                last_state = current_state
                time.sleep(poll_delay)  # Les répertoires peuvent prendre plus de temps à changer

            except Exception as e:
                print(f"[erreur] Error in directory watch thread for {watch_id}: {e}")
                time.sleep(5.0)  # Attendre plus longtemps en cas d'erreur

    def _watch_git_thread(self, watch_id: str, path: Path, stop_event: ThreadEvent,
                         callback: Optional[Callable[[str], None]]) -> None:
        """Thread de surveillance pour un dépôt Git."""
        last_state = self._last_states.get(watch_id, "")

        while not stop_event.is_set():
            try:
                current_state = self._get_git_state(path)

                # Vérifier si le hash du commit a changé
                if last_state != current_state and current_state:
                    # Mettre à jour l'état
                    self._last_states[watch_id] = current_state

                    # Publier l'événement
                    event = Event(
                        type=EventType.GIT_CHANGE,
                        data={
                            "watch_id": watch_id,
                            "path": str(path),
                            "old_commit": last_state[:8] if last_state else None,
                            "new_commit": current_state[:8] if current_state else None
                        },
                        source="WatchManager"
                    )
                    self.event_bus.publish(event)

                    # Appeler le callback si fourni
                    if callback:
                        try:
                            callback(str(path))
                        except Exception as e:
                            print(f"[erreur] Error in git watch callback: {e}")

                # Attendre avant la prochaine vérification
                last_state = current_state
                time.sleep(5.0)  # Git peut prendre du temps pour détecter les changements

            except Exception as e:
                print(f"[erreur] Error in git watch thread for {watch_id}: {e}")
                time.sleep(10.0)  # Attendre encore plus longtemps en cas d'erreur


class BackgroundTasks:
    """Gestionnaire de tâches en arrière-plan."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._tasks: Dict[str, dict] = {}
        self._task_threads: Dict[str, Thread] = {}
        self._stop_events: Dict[str, ThreadEvent] = {}
        self._task_queue: Queue = Queue()
        self._worker_threads: List[Thread] = []
        self._running = False

    def start_worker_pool(self, num_workers: int = 4) -> None:
        """Démarrer un pool de workers pour traiter les tâches en arrière-plan."""
        if self._running:
            return

        self._running = True
        for i in range(num_workers):
            worker = Thread(target=self._worker_loop, args=(f"worker-{i}",), daemon=True)
            self._worker_threads.append(worker)
            worker.start()

        # Publier l'événement
        event = Event(
            type=EventType.HEARTBEAT,
            data={"component": "BackgroundTasks", "action": "worker_pool_started", "workers": num_workers},
            source="BackgroundTasks"
        )
        self.event_bus.publish(event)

        record_metric("background_tasks_workers_started", 1, "count", {"count": num_workers})

    def stop_worker_pool(self) -> None:
        """Arrêter le pool de workers."""
        self._running = False
        # Ajouter des toxines pour arrêter les workers
        for _ in self._worker_threads:
            self._task_queue.put(None)

        # Attendre que les workers se terminent
        for thread in self._worker_threads:
            thread.join(timeout=5.0)

        self._worker_threads.clear()

        # Publier l'événement
        event = Event(
            type=EventType.HEARTBEAT,
            data={"component": "BackgroundTasks", "action": "worker_pool_stopped"},
            source="BackgroundTasks"
        )
        self.event_bus.publish(event)

    def submit_task(self, task_id: str, func: Callable, *args, **kwargs) -> bool:
        """Soumettre une tâche à exécuter en arrière-plan."""
        if task_id in self._tasks:
            print(f"[avertissement] Task {task_id} already exists")
            return False

        task_data = {
            "id": task_id,
            "function": func,
            "args": args,
            "kwargs": kwargs,
            "submitted_at": time.time(),
            "status": "queued"
        }

        self._tasks[task_id] = task_data
        self._task_queue.put((task_id, func, args, kwargs))

        # Publier l'événement
        event = Event(
            type=EventType.HEARTBEAT,
            data={"component": "BackgroundTasks", "action": "task_submitted", "task_id": task_id},
            source="BackgroundTasks"
        )
        self.event_bus.publish(event)

        return True

    def _worker_loop(self, worker_name: str) -> None:
        """Boucle principale d'un worker."""
        while self._running:
            try:
                # Récupérer une tâche de la file d'attente
                item = self._task_queue.get(timeout=1.0)
                if item is None:  # Toxine pour arrêter
                    break

                task_id, func, args, kwargs = item

                # Mettre à jour le statut
                if task_id in self._tasks:
                    self._tasks[task_id]["status"] = "running"
                    self._tasks[task_id]["started_at"] = time.time()

                # Exécuter la tâche
                try:
                    result = func(*args, **kwargs)

                    # Mettre à jour le statut
                    if task_id in self._tasks:
                        self._tasks[task_id]["status"] = "completed"
                        self._tasks[task_id]["completed_at"] = time.time()
                        self._tasks[task_id]["result"] = result

                    # Publier l'événement de completion
                    event = Event(
                        type=EventType.HEARTBEAT,
                        data={
                            "component": "BackgroundTasks",
                            "action": "task_completed",
                            "task_id": task_id,
                            "worker": worker_name
                        },
                        source="BackgroundTasks"
                    )
                    self.event_bus.publish(event)

                except Exception as e:
                    # Gérer les erreurs
                    if task_id in self._tasks:
                        self._tasks[task_id]["status"] = "failed"
                        self._tasks[task_id]["failed_at"] = time.time()
                        self._tasks[task_id]["error"] = str(e)

                    # Publier l'événement d'erreur
                    error_event = Event(
                        type=EventType.ERROR_OCCURRED,
                        data={
                            "component": "BackgroundTasks",
                            "task_id": task_id,
                            "worker": worker_name,
                            "error": str(e)
                        },
                        source="BackgroundTasks"
                    )
                    self.event_bus.publish(error_event)

                finally:
                    self._task_queue.task_done()

            except queue.Empty:
                continue  # Timeout normal, boucler encore
            except Exception as e:
                print(f"[erreur] Error in worker {worker_name}: {e}")

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Obtenir le statut d'une tâche spécifique."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[dict]:
        """Lister toutes les tâches."""
        return list(self._tasks.values())


class RuntimeCache:
    """Cache en mémoire pour stocker des données temporaires pendant la session."""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, dict] = {}
        self._access_order: List[str] = []  # Pour LRU
        self._max_size = max_size
        self._lock = threading.RLock()

    def get(self, key: str) -> Any:
        """Obtenir une valeur du cache."""
        with self._lock:
            if key not in self._cache:
                return None

            # Mettre à jour l'ordre d'accès (MRU)
            self._access_order.remove(key)
            self._access_order.append(key)

            # Vérifier l'expiration
            entry = self._cache[key]
            if "expires_at" in entry and time.time() > entry["expires_at"]:
                # Expiré, le supprimer
                del self._cache[key]
                self._access_order.remove(key)
                return None

            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Stocker une valeur dans le cache."""
        with self._lock:
            # Calculer le temps d'expiration si spécifié
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl

            # Ajouter ou mettre à jour l'entrée
            if key in self._cache:
                # Mettre à jour l'entrée existante
                self._cache[key] = {
                    "value": value,
                    "created_at": self._cache[key].get("created_at", time.time()),
                    "accessed_at": time.time(),
                    "expires_at": expires_at
                }
                # Déplacer à la fin (MRU)
                self._access_order.remove(key)
                self._access_order.append(key)
            else:
                # Nouvelle entrée
                self._cache[key] = {
                    "value": value,
                    "created_at": time.time(),
                    "accessed_at": time.time(),
                    "expires_at": expires_at
                }
                self._access_order.append(key)

                # Appliquer la politique LRU si nécessaire
                if len(self._cache) > self._max_size:
                    # Supprimer l'élément le moins récemment utilisé
                    lru_key = self._access_order.pop(0)
                    del self._cache[lru_key]

            # Publier l'événement
            event = Event(
                type=EventType.HEARTBEAT,
                data={
                    "component": "RuntimeCache",
                    "action": "item_set",
                    "key": key,
                    "cache_size": len(self._cache)
                },
                source="RuntimeCache"
            )
            # Note: On ne publie pas ici pour éviter les boucles infinies potentielles
            # Le EventBus sera utilisé ailleurs pour publier des événements de cache si nécessaire

    def delete(self, key: str) -> bool:
        """Supprimer une clé du cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_order.remove(key)

                # Publier l'événement
                event = Event(
                    type=EventType.HEARTBEAT,
                    data={
                        "component": "RuntimeCache",
                        "action": "item_deleted",
                        "key": key,
                        "cache_size": len(self._cache)
                    },
                    source="RuntimeCache"
                )
                # Note: Même remarque que ci-dessus

                return True
            return False

    def clear(self) -> None:
        """Vider complètement le cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

            # Publier l'événement
            event = Event(
                type=EventType.HEARTBEAT,
                data={
                    "component": "RuntimeCache",
                    "action": "cache_cleared"
                },
                source="RuntimeCache"
            )
            # Note: Même remarque que ci-dessus

    def size(self) -> int:
        """Obtenir la taille actuelle du cache."""
        with self._lock:
            return len(self._cache)

    def keys(self) -> List[str]:
        """Obtenir toutes les clés du cache."""
        with self._lock:
            return list(self._cache.keys())


class RuntimeManager:
    """Gestionnaire principal qui coordonne tous les composants du runtime."""

    def __init__(self):
        self.event_bus = EventBus()
        self.process_manager = ProcessManager(self.event_bus)
        self.shell_manager = ShellManager(self.event_bus)
        self.watch_manager = WatchManager(self.event_bus)
        self.background_tasks = BackgroundTasks(self.event_bus)
        self.runtime_cache = RuntimeCache()
        self._initialized = False
        self._start_time = None

    def initialize(self) -> bool:
        """Initialiser tous les composants du runtime."""
        if self._initialized:
            return True

        try:
            # Démarrer le bus d'événements
            self.event_bus.start()

            # Démarrer le pool de workers pour les tâches en arrière-plan
            self.background_tasks.start_worker_pool()

            self._initialized = True
            self._start_time = time.time()

            # Publier l'événement d'initialisation complète
            event = Event(
                type=EventType.HEARTBEAT,
                data={
                    "component": "RuntimeManager",
                    "action": "initialized",
                    "uptime": 0
                },
                source="RuntimeManager"
            )
            self.event_bus.publish(event)

            record_metric("runtime_manager_initialized", 1, "count")
            return True

        except Exception as e:
            print(f"[erreur] Failed to initialize RuntimeManager: {e}")
            return False

    def shutdown(self) -> None:
        """Arrêter tous les composants du runtime."""
        if not self._initialized:
            return

        try:
            # Arrêter le pool de workers
            self.background_tasks.stop_worker_pool()

            # Arrêter tous les shells
            self.shell_manager.shutdown_all()

            # Arrêter le bus d'événements
            self.event_bus.stop()

            self._initialized = False

            # Publier l'événement d'arrêt
            event = Event(
                type=EventType.HEARTBEAT,
                data={
                    "component": "RuntimeManager",
                    "action": "shutdown",
                    "uptime": time.time() - self._start_time if self._start_time else 0
                },
                source="RuntimeManager"
            )
            # Note: Le event_bus est arrêté, donc cet événement ne sera pas traité
            # Mais c'est bon pour la consistance

            record_metric("runtime_manager_shutdown", 1, "count")

        except Exception as e:
            print(f"[erreur] Error during RuntimeManager shutdown: {e}")

    def get_uptime(self) -> float:
        """Obtenir le temps de fonctionnement en secondes."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def is_initialized(self) -> bool:
        """Vérifier si le runtime manager a été initialisé."""
        return self._initialized


# Instance globale du gestionnaire de runtime
runtime_manager = RuntimeManager()


# Fonctions d'aide pour faciliter l'utilisation
def initialize_runtime() -> bool:
    """Initialiser le gestionnaire de runtime global."""
    return runtime_manager.initialize()


def shutdown_runtime() -> None:
    """Arrêter le gestionnaire de runtime global."""
    runtime_manager.shutdown()


def get_runtime_manager() -> RuntimeManager:
    """Obtenir l'instance du gestionnaire de runtime global."""
    return runtime_manager


def get_event_bus() -> EventBus:
    """Obtenir l'instance du bus d'événements global."""
    return runtime_manager.event_bus


def get_process_manager() -> ProcessManager:
    """Obtenir l'instance du gestionnaire de processus global."""
    return runtime_manager.process_manager


def get_shell_manager() -> ShellManager:
    """Obtenir l'instance du gestionnaire de shell global."""
    return runtime_manager.shell_manager


def get_watch_manager() -> WatchManager:
    """Obtenir l'instance du gestionnaire de surveillance global."""
    return runtime_manager.watch_manager


def get_background_tasks() -> BackgroundTasks:
    """Obtenir l'instance du gestionnaire de tâches en arrière-plan global."""
    return runtime_manager.background_tasks


def get_runtime_cache() -> RuntimeCache:
    """Obtenir l'instance du cache global."""
    return runtime_manager.runtime_cache


# Décorateur pour marquer les fonctions qui doivent être exécutées en arrière-plan
def background_task(task_id: Optional[str] = None):
    """
    Décorateur pour exécuter une fonction en arrière-plan.

    Args:
        task_id: Identifiant optionnel pour la tâche (généré automatiquement si None)
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Générer un ID de tâche si non fourni
            actual_task_id = task_id or f"{func.__name__}_{int(time.time() * 1000)}"

            # Soumettre la tâche au gestionnaire de tâches en arrière-plan
            runtime_manager.background_tasks.submit_task(
                task_id=actual_task_id,
                func=func,
                *args,
                **kwargs
            )

            # Retourner un objet permettant de suivre la tâche
            class TaskHandle:
                def __init__(self, tid: str):
                    self.task_id = tid

                def status(self) -> Optional[dict]:
                    return runtime_manager.background_tasks.get_task_status(self.task_id)

                def result(self, timeout: Optional[float] = None) -> Any:
                    start = time.time()
                    while True:
                        status = self.status()
                        if not status:
                            return None
                        if status["status"] in ["completed", "failed"]:
                            return status.get("result") if status["status"] == "completed" else None
                        if timeout and (time.time() - start) > timeout:
                            return None
                        time.sleep(0.1)

            return TaskHandle(actual_task_id)

        return wrapper
    return decorator