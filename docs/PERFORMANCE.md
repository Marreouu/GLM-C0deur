# Performance - GLM Code

Ce document décrit les aspects de performance du projet GLM Code, y compris l'optimisation du code, la gestion des ressources, le monitoring et les bonnes pratiques pour garantir une expérience utilisateur optimale.

## Vue d'ensemble

La performance est un aspect crucial de GLM Code, car l'application interagit directement avec le système de fichiers et exécute des commandes. Ce document fournit un guide complet pour optimiser les performances du projet.

## Architecture performante

### Principes de conception

#### 1. Modularité

- **Séparation des concerns** : Chaque module a une responsabilité claire
- **Faible couplage** : Les modules sont indépendants les uns des autres
- **Haute cohésion** : Les éléments d'un module sont liés fonctionnellement

#### 2. Asynchronie

- **Non-blocking I/O** : Utilisation de l'asynchronie pour les opérations I/O
- **Concurrency** : Traitement parallèle des tâches
- **Streaming** : Traitement des données en flux continu

#### 3. Caching

- **Cache des réponses** : Éviter les requêtes redondantes
- **Cache des fichiers** : Mettre en cache les fichiers fréquemment accédés
- **Cache des configurations** : Éviter la relecture des configurations

### Optimisation des performances

#### 1. Optimisation du code

```python
# Avant : Boucle inefficace
def process_files(files):
    results = []
    for file in files:
        content = read_file(file)
        processed = process_content(content)
        results.append(processed)
    return results

# Après : Utilisation de list comprehension
def process_files(files):
    return [process_content(read_file(file)) for file in files]
```

#### 2. Optimisation de la mémoire

```python
# Avant : Chargement complet du fichier
def read_large_file(path):
    with open(path, 'r') as f:
        return f.read()

# Après : Lecture par morceaux
def read_large_file(path, chunk_size=8192):
    with open(path, 'r') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk
```

#### 3. Optimisation des E/S

```python
# Avant : Opérations séquentielles
def copy_files(src, dst):
    for file in os.listdir(src):
        shutil.copy(os.path.join(src, file), dst)

# Après : Opérations parallèles
def copy_files(src, dst):
    with ThreadPoolExecutor() as executor:
        for file in os.listdir(src):
            executor.submit(shutil.copy, os.path.join(src, file), dst)
```

## Gestion des ressources

### Mémoire

#### 1. Gestion de la mémoire

```python
# Utilisation de générateurs pour économiser la mémoire
def read_large_files(file_paths):
    for file_path in file_paths:
        with open(file_path, 'r') as f:
            yield f.read()

# Utilisation de weak references pour les objets lourds
import weakref

class HeavyObject:
    def __init__(self, data):
        self.data = data

# Cache avec weak references
cache = weakref.WeakValueDictionary()

def get_heavy_object(key):
    if key in cache:
        return cache[key]
    obj = HeavyObject(load_data(key))
    cache[key] = obj
    return obj
```

#### 2. Surveillance de la mémoire

```python
import psutil
import os

def get_memory_usage():
    """Récupère l'utilisation de la mémoire."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # Mo

def monitor_memory():
    """Surveille l'utilisation de la mémoire."""
    while True:
        memory_usage = get_memory_usage()
        if memory_usage > 500:  # 500Mo
            print("Alerte: utilisation mémoire élevée")
        time.sleep(60)
```

### CPU

#### 1. Optimisation CPU

```python
# Utilisation de Cython pour les fonctions critiques
# example.pyx
def fibonacci(int n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Compilation
# python setup.py build_ext --inplace
```

#### 2. Surveillance CPU

```python
import psutil

def get_cpu_usage():
    """Récupère l'utilisation CPU."""
    return psutil.cpu_percent(interval=1)

def monitor_cpu():
    """Surveille l'utilisation CPU."""
    while True:
        cpu_usage = get_cpu_usage()
        if cpu_usage > 80:  # 80%
            print("Alerte: utilisation CPU élevée")
        time.sleep(60)
```

### Disque

#### 1. Optimisation du disque

```python
# Utilisation de SSD pour les fichiers temporaires
import tempfile
import os

def create_temp_file():
    """Crée un fichier temporaire sur SSD."""
    temp_dir = '/tmp/ssd'  # Chemin vers SSD
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return tempfile.NamedTemporaryFile(dir=temp_dir, delete=False)
```

#### 2. Surveillance du disque

```python
import psutil

def get_disk_usage():
    """Récupère l'utilisation du disque."""
    disk = psutil.disk_usage('/')
    return disk.percent

def monitor_disk():
    """Surveille l'utilisation du disque."""
    while True:
        disk_usage = get_disk_usage()
        if disk_usage > 90:  # 90%
            print("Alerte: utilisation disque élevée")
        time.sleep(60)
```

## Monitoring et profiling

### Outils de monitoring

#### 1. Monitoring applicatif

```python
import time
from functools import wraps

def monitor_performance(func):
    """Décorateur pour monitorer les performances."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{func.__name__} exécuté en {execution_time:.2f} secondes")
        return result
    return wrapper

# Utilisation
@monitor_performance
def process_data(data):
    # Traitement des données
    pass
```

#### 2. Monitoring système

```python
import psutil
import time

def system_monitor():
    """Monitor système."""
    while True:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Mémoire
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disque
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Réseau
        network = psutil.net_io_counters()
        
        print(f"CPU: {cpu_percent}% | Mémoire: {memory_percent}% | Disque: {disk_percent}%")
        time.sleep(60)
```

### Profiling

#### 1. Profiling avec cProfile

```python
import cProfile
import pstats

def profile_function():
    """Profile une fonction."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Fonction à profiler
    process_data()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats()

# Exécution
profile_function()
```

#### 2. Profiling avec line_profiler

```python
# installation
# pip install line_profiler

# @profile
def process_data():
    # Fonction à profiler
    pass

# Exécution
# kernprof -l -v script.py
```

#### 3. Profiling avec memory_profiler

```python
# installation
# pip install memory_profiler

# @profile
def process_data():
    # Fonction à profiler
    pass

# Exécution
# python -m memory_profiler script.py
```

#### 4. Profiling avec decorators personnalisés (GLM Code)

GLM Code utilise un système de profiling personnalisé basé sur des decorateurs `@profile` et l'enregistrement de métriques via `record_metric`.

```python
from glmcode.performance_monitor import profile, record_metric

@profile("nom_de_la_fonction")
def ma_fonction(parametre):
    try:
        # Logique de la fonction
        result = faire_quelque_chose(parametre)
        
        # Enregistrement de métriques de succès
        record_metric("ma_fonction_success", 1, "count", {
            "parametre": parametre,
            "resultat_taille": len(str(result)) if result else 0
        })
        return result
    except ValueError as e:
        # Enregistrement de métriques d'erreur
        record_metric("ma_fonction_value_error", 1, "count", {
            "parametre": parametre,
            "erreur": str(e)
        })
        raise
    except Exception as e:
        # Enregistrement de métriques d'erreur générique
        record_metric("ma_fonction_error", 1, "count", {
            "parametre": parametre,
            "erreur_type": type(e).__name__,
            "erreur_message": str(e)
        })
        raise
```

Ce système permet de :
1. Mesurer le temps d'exécution de chaque fonction décorée
2. Compter les succès et les échecs par type d'erreur
3. Enregistrer des métriques personnalisées avec des dimensions contextuelles
4. Surveiller les performances en temps réel via le performance monitor

## Tests de performance

### Tests unitaires de performance

```python
import pytest
import time

def test_file_reading_performance():
    """Test la performance de la lecture de fichiers."""
    start_time = time.time()
    for _ in range(100):
        read_file('test.txt')
    end_time = time.time()
    assert end_time - start_time < 1.0  # Moins de 1 seconde

def test_command_execution_performance():
    """Test la performance de l'exécution de commandes."""
    start_time = time.time()
    for _ in range(10):
        run_command('ls -la')
    end_time = time.time()
    assert end_time - start_time < 5.0  # Moins de 5 secondes
```

### Tests de charge

```python
import pytest
import threading
import time

def test_concurrent_file_operations():
    """Test les opérations de fichiers concurrentes."""
    def worker():
        for _ in range(10):
            read_file('test.txt')
    
    threads = []
    start_time = time.time()
    
    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    end_time = time.time()
    assert end_time - start_time < 10.0  # Moins de 10 secondes
```

### Tests de stress

```python
import pytest
import threading
import time

def test_memory_stress():
    """Test le stress mémoire."""
    def worker():
        data = []
        for _ in range(1000):
            data.append('x' * 1000)
        time.sleep(1)
    
    threads = []
    start_time = time.time()
    
    for _ in range(100):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    end_time = time.time()
    assert end_time - start_time < 60.0  # Moins de 60 secondes
```

## Optimisation spécifique

### Optimisation du streaming

```python
# Avant : Streaming simple
def stream_response():
    response = requests.get('https://api.example.com/data', stream=True)
    for chunk in response.iter_content(chunk_size=8192):
        yield chunk

# Après : Streaming optimisé
def stream_response():
    response = requests.get('https://api.example.com/data', stream=True)
    response.raw.decode_content = True  # Décompression automatique
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        for chunk in response.iter_content(chunk_size=8192):
            executor.submit(process_chunk, chunk)
```

### Optimisation de la base de données

```python
# Avant : Requêtes séquentielles
def get_user_data(user_ids):
    results = []
    for user_id in user_ids:
        user = get_user_from_db(user_id)
        results.append(user)
    return results

# Après : Requêtes batch
def get_user_data(user_ids):
    query = "SELECT * FROM users WHERE id IN (%s)" % ','.join(['%s'] * len(user_ids))
    return execute_query(query, user_ids)
```

### Optimisation du réseau

```python
# Avant : Requêtes HTTP séquentielles
def fetch_urls(urls):
    results = []
    for url in urls:
        response = requests.get(url)
        results.append(response.text)
    return results

# Après : Requêtes HTTP parallèles
def fetch_urls(urls):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(requests.get, url) for url in urls]
        results = [future.result().text for future in futures]
    return results
```

## Bonnes pratiques

### 1. Écrire un code performant

- **Utiliser les bons algorithmes** : Complexité temporelle et spatiale
- **Éviter les opérations coûteuses** : Boucles imbriquées, regex complexes
- **Utiliser les structures de données appropriées** : Dictionnaires pour les recherches rapides
- **Minimiser les allocations mémoire** : Réutiliser les objets quand possible

### 2. Mesurer les performances

- **Profiler régulièrement** : Identifier les goulots d'étranglement
- **Benchmark les performances** : Comparer différentes implémentations
- **Monitorer en production** : Détecter les problèmes de performance

### 3. Optimiser progressivement

- **Commencer par un code simple** : Optimiser ensuite
- **Optimiser les parties critiques** : Les fonctions les plus utilisées
- **Ne pas prématurer l'optimisation** : Optimiser seulement quand nécessaire

### 4. Documenter les performances

- **Documenter les performances attendues** : Complexité, temps d'exécution
- **Documenter les optimisations** : Pourquoi et comment
- **Documenter les compromis** : Performance vs lisibilité vs maintenabilité

## Outils et ressources

### Outils de profiling

- **cProfile** : Profiling Python standard
- **line_profiler** : Profiling par ligne
- **memory_profiler** : Profiling mémoire
- **py-spy** : Profiling sans instrumentation
- **snakeviz** : Visualisation des profils

### Outils de monitoring

- **Prometheus** : Monitoring système et applicatif
- **Grafana** : Visualisation des métriques
- **New Relic** : Monitoring applicatif
- **Datadog** : Monitoring et observabilité

### Outils d'optimisation

- **Numba** : Compilation JIT pour Python
- **Cython** : Compilation de Python en C
- **PyPy** : Interprète Python JIT
- **numexpr** : Évaluation numérique rapide

## Performance en production

### Surveillance en production

```python
import logging
import time
from prometheus_client import Counter, Histogram, start_http_server

# Metrics
REQUEST_COUNT = Counter('glmcode_requests_total', 'Total requests')
REQUEST_DURATION = Histogram('glmcode_request_duration_seconds', 'Request duration')

def monitor_performance():
    """Démarre le monitoring."""
    start_http_server(8000)  # Expose les métriques sur http://localhost:8000

def log_performance(func):
    """Décorateur pour loguer les performances."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        REQUEST_COUNT.inc()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        REQUEST_DURATION.observe(duration)
        logging.info(f"{func.__name__} exécuté en {duration:.2f}s")
        return result
    return wrapper
```

### Alertes de performance

```python
from prometheus_client import Gauge

# Metrics
MEMORY_USAGE = Gauge('glmcode_memory_usage_bytes', 'Memory usage')
CPU_USAGE = Gauge('glmcode_cpu_usage_percent', 'CPU usage')

def check_performance():
    """Vérifie les performances et envoie des alertes."""
    while True:
        memory = get_memory_usage()
        cpu = get_cpu_usage()
        
        MEMORY_USAGE.set(memory)
        CPU_USAGE.set(cpu)
        
        if memory > 500 * 1024 * 1024:  # 500Mo
            send_alert("Mémoire élevée", f"Utilisation mémoire: {memory/1024/1024:.1f}Mo")
        
        if cpu > 80:  # 80%
            send_alert("CPU élevé", f"Utilisation CPU: {cpu}%")
        
        time.sleep(60)
```

## Conclusion

La performance est un aspect crucial de GLM Code. En suivant les bonnes pratiques décrites dans ce document, vous pouvez garantir une expérience utilisateur optimale tout en maintenant la qualité et la maintenabilité du code.

### Points clés

1. **Mesurer avant d'optimiser** : Utiliser les outils de profiling pour identifier les problèmes
2. **Optimiser progressivement** : Commencer par les parties critiques
3. **Monitorer en production** : Détecter les problèmes de performance en temps réel
4. **Documenter les performances** : Garder une trace des optimisations et des compromis

### Ressources supplémentaires

- [Python Performance Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
- [High Performance Python](https://www.oreilly.com/library/view/high-performance-python/9781492052036/)
- [Python Optimization Techniques](https://realpython.com/python-performance-optimization/)

---

*Cette documentation de performance est régulièrement mise à jour pour refléter les meilleures pratiques et les évolutions du projet. Pour plus d'informations, consultez le [README principal](../README.md) et la [documentation](./README.md).*