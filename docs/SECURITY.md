# Politique de sécurité - GLM Code

GLM Code s'engage à fournir un produit sécurisé et à protéger les données de ses utilisateurs. Ce document décrit notre approche de la sécurité, les pratiques de codage sécurisé et la façon de signaler les problèmes de sécurité.

## Vue d'ensemble

### Principes de sécurité

1. **Security by Design** : La sécurité est intégrée dès la conception
2. **Defense in Depth** : Couches multiples de protection
3. **Least Privilege** : Accès minimal nécessaire
4. **Zero Trust** : Vérification de toutes les requêtes
5. **Transparency** : Communication ouverte sur les problèmes de sécurité

### Responsabilités

- **Équipe de développement** : Maintenir la sécurité du code
- **Utilisateurs** : Configurer correctement et suivre les bonnes pratiques
- **Communauté** : Signaler les problèmes de sécurité

## Pratiques de codage sécurisé

### Entrées utilisateur

#### Validation des entrées

```python
def validate_path(path: str) -> bool:
    """Valide un chemin de fichier pour les attaques de type path traversal."""
    try:
        # Convertir en chemin absolu
        abs_path = os.path.abspath(path)
        # Vérifier que le chemin est dans le répertoire autorisé
        allowed_dir = os.path.abspath("/allowed/path")
        return abs_path.startswith(allowed_dir)
    except (OSError, ValueError):
        return False
```

#### Échappement des sorties

```python
def safe_print(text: str) -> None:
    """Affiche du texte de manière sécurisée."""
    from html import escape
    safe_text = escape(text)
    print(safe_text)
```

### Gestion des fichiers

#### Chemins de fichiers

```python
def safe_read_file(path: str) -> str:
    """Lit un fichier de manière sécurisée."""
    # Valider le chemin
    if not validate_path(path):
        raise ValueError("Chemin de fichier non autorisé")
    
    # Vérifier les permissions
    if not os.access(path, os.R_OK):
        raise PermissionError("Permission refusée")
    
    # Lire le fichier avec limite de taille
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read(1024 * 1024)  # 1Mo max
        return content
```

#### Permissions

```python
def safe_write_file(path: str, content: str) -> None:
    """Écrit un fichier de manière sécurisée."""
    # Valider le chemin
    if not validate_path(path):
        raise ValueError("Chemin de fichier non autorisé")
    
    # Créer les répertoires parents si nécessaire
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Écrire le fichier
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
```

### Gestion des commandes

#### Exécution sécurisée

```python
def safe_run_command(command: str, timeout: int = 30) -> str:
    """Exécute une commande de manière sécurisée."""
    # Liste des commandes autorisées
    allowed_commands = ['ls', 'cat', 'grep', 'find', 'git']
    
    # Valider la commande
    if not any(command.startswith(cmd) for cmd in allowed_commands):
        raise ValueError("Commande non autorisée")
    
    # Exécuter avec timeout
    try:
        result = subprocess.run(
            command,
            shell=True,
            timeout=timeout,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise TimeoutError("Commande timeout")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Commande échouée: {e.stderr}")
```

### Gestion des clés API

#### Stockage sécurisé

```python
def get_api_key() -> str:
    """Récupère la clé API de manière sécurisée."""
    # Privilégier les variables d'environnement
    api_key = os.getenv('GLMCODE_API_KEY')
    if api_key:
        return api_key
    
    # Ensuite vérifier le fichier de configuration
    config_path = os.path.expanduser('~/.glmcode/config.toml')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = toml.load(f)
            return config.get('zai', {}).get('api_key', '')
    
    raise ValueError("Clé API non trouvée")
```

#### Protection des clés

```python
# Ne jamais logger les clés API
def log_info(message: str) -> None:
    """Journalise un message sans les clés API."""
    import re
    # Masquer les clés API
    masked_message = re.sub(r'api_key=[^&]*', 'api_key=***', message)
    logging.info(masked_message)
```

### Cryptographie

#### Hashage de mots de passe

```python
import hashlib
import os

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash un mot de passe avec salt."""
    if salt is None:
        salt = os.urandom(32).hex()
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt
```

#### Chiffrement

```python
from cryptography.fernet import Fernet

def encrypt_data(data: str, key: bytes) -> bytes:
    """Chiffre des données."""
    f = Fernet(key)
    return f.encrypt(data.encode('utf-8'))

def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    """Déchiffre des données."""
    f = Fernet(key)
    return f.decrypt(encrypted_data).decode('utf-8')
```

## Configuration sécurisée

### Fichiers de configuration

#### Exemple de configuration sécurisée

```toml
# config.toml
[zai]
api_key = "${GLMCODE_API_KEY}"  # Utiliser des variables d'environnement
base_url = "https://api.z.ai/api/paas/v4"

[coder]
enabled = false
base_url = "http://localhost:11434/v1"
model = "qwen2.5-coder:latest"

[security]
# Paramètres de sécurité
max_file_size = 1048576  # 1Mo
command_timeout = 30
allowed_commands = ["ls", "cat", "grep", "find"]
log_level = "INFO"
```

#### Permissions des fichiers

```bash
# Configurer les permissions sécurisées
chmod 600 ~/.glmcode/config.toml
chmod 700 ~/.glmcode/
```

### Variables d'environnement

```bash
# Exemple de configuration sécurisée
export GLMCODE_API_KEY="votre-cle-api-secrete"
export GLMCODE_LOG_LEVEL="INFO"
export GLMCODE_MAX_FILE_SIZE="1048576"
```

## Réseau

### Communications sécurisées

#### HTTPS

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_secure_session() -> requests.Session:
    """Crée une session HTTP sécurisée."""
    session = requests.Session()
    
    # Configuration des retries
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session
```

#### Validation des certificats

```python
# Toujours vérifier les certificats SSL
response = session.get(
    "https://api.z.ai/api/paas/v4",
    verify=True  # Vérifier le certificat SSL
)
```

### Pare-feu et proxy

```python
# Configuration du proxy sécurisé
proxies = {
    'http': 'http://proxy.company.com:8080',
    'https': 'http://proxy.company.com:8080',
}

# Configuration du pare-feu
allowed_ips = [
    '192.168.1.0/24',
    '10.0.0.0/8'
]
```

## Stockage des données

### Gestion des logs

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging() -> None:
    """Configure le logging sécurisé."""
    logger = logging.getLogger('glmcode')
    logger.setLevel(logging.INFO)
    
    # Rotation des logs avec compression
    handler = RotatingFileHandler(
        'glm.log',
        maxBytes=10*1024*1024,  # 10Mo
        backupCount=5,
        encoding='utf-8'
    )
    
    # Formater les logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
```

### Sauvegardes

```python
import shutil
from datetime import datetime

def backup_config() -> None:
    """Effectue une sauvegarde sécurisée de la configuration."""
    config_path = os.path.expanduser('~/.glmcode/config.toml')
    backup_path = os.path.expanduser(f'~/.glmcode/backup/config_{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml')
    
    # Créer la sauvegarde
    shutil.copy2(config_path, backup_path)
    
    # Chiffrer la sauvegarde
    key = get_encryption_key()
    encrypted_backup = encrypt_file(backup_path, key)
    
    # Supprimer la sauvegarde non chiffrée
    os.remove(backup_path)
    
    return encrypted_backup
```

## Tests de sécurité

### Tests unitaires

```python
import pytest

def test_input_validation():
    """Test la validation des entrées."""
    assert validate_path("/allowed/path/file.txt") == True
    assert validate_path("/etc/passwd") == False
    assert validate_path("../../etc/passwd") == False

def test_command_execution():
    """Test l'exécution sécurisée des commandes."""
    assert safe_run_command("ls -la") != ""
    with pytest.raises(ValueError):
        safe_run_command("rm -rf /")
```

### Tests d'intégration

```python
def test_secure_file_operations():
    """Test les opérations de fichiers sécurisées."""
    # Test de lecture
    content = safe_read_file("/allowed/path/file.txt")
    assert isinstance(content, str)
    
    # Test d'écriture
    safe_write_file("/allowed/path/output.txt", "test")
    assert os.path.exists("/allowed/path/output.txt")
```

### Tests de pénétration

```python
def test_path_traversal():
    """Test les attaques de type path traversal."""
    # Test avec chemin relatif
    assert validate_path("../../../etc/passwd") == False
    
    # Test avec chemin absolu
    assert validate_path("/etc/passwd") == False

def test_injection():
    """Test les injections de commandes."""
    # Test avec injection
    with pytest.raises(ValueError):
        safe_run_command("ls; rm -rf /")
```

## Gestion des incidents

### Processus de réponse

1. **Identification** : Détecter l'incident
2. **Évaluation** : Évaluer l'impact
3. **Contenance** : Contenir l'incident
4. **Éradication** : Éliminer la cause
5. **Restauration** : Restaurer les services
6. **Post-mortem** : Analyse et amélioration

### Communication

```python
def security_incident(incident_type: str, severity: str, description: str) -> None:
    """Gère un incident de sécurité."""
    # Journaliser l'incident
    logging.critical(f"Security incident: {incident_type} - {severity} - {description}")
    
    # Notifier l'équipe
    notify_security_team(incident_type, severity, description)
    
    # Notifier les utilisateurs affectés
    if severity in ["critical", "high"]:
        notify_users(incident_type, description)
```

### Rapports

```python
def generate_security_report() -> dict:
    """Génère un rapport de sécurité."""
    return {
        "incidents": get_incident_count(),
        "vulnerabilities": get_vulnerability_count(),
        "compliance": get_compliance_status(),
        "performance": get_security_metrics()
    }
```

## Compliance

### Standards

- **OWASP Top 10** : Protection contre les vulnérabilités web
- **NIST Cybersecurity Framework** : Gestion des risques
- **ISO 27001** : Management de la sécurité de l'information
- **GDPR** : Protection des données personnelles

### Audits

```python
def security_audit() -> dict:
    """Effectue un audit de sécurité."""
    audit_results = {
        "code_quality": audit_code_quality(),
        "dependencies": audit_dependencies(),
        "infrastructure": audit_infrastructure(),
        "compliance": audit_compliance()
    }
    return audit_results
```

## Ressources

### Outils

- **OWASP ZAP** : Scanning web application
- **SonarQube** : Code quality analysis
- **Dependabot** : Dependency scanning
- **Snyk** : Vulnerability scanning

### Documentation

- **OWASP Cheat Sheet Series** : Guides de sécurité
- **NIST Cybersecurity Framework** : Framework de sécurité
- **OWASP Top 10** : Top 10 des vulnérabilités
- **Mozilla Security Guidelines** : Guidelines de sécurité

## Contact

### Équipe de sécurité

- **Email** : security@glmcode.com
- **GPG Key** : [Clé GPG publique]
- **Slack** : #security-team

### Signaler un problème

```bash
# Signaler un problème de sécurité
curl -X POST https://glmcode.com/security-report \
  -H "Content-Type: application/json" \
  -d '{
    "type": "vulnerability",
    "severity": "high",
    "description": "Description du problème",
    "affected_versions": ["0.1.0"],
    "reproduction": "Étapes pour reproduire"
  }'
```

### Politique de divulgation responsable

Nous encourageons la divulgation responsable des vulnérabilités :

1. **Privately report** : Signaler les problèmes en privé
2. **Give time to fix** : Donner un délai raisonnable pour corriger
3. **Coordinate disclosure** : Coordonner la divulgation
4. **No public disclosure** : Pas de divulgation publique avant la correction

---

*Cette politique de sécurité est régulièrement mise à jour pour refléter les meilleures pratiques et les nouvelles menaces. Pour plus d'informations, consultez le [README principal](../README.md) et la [documentation](./README.md).*