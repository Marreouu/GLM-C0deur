"""Client HTTP avec mise en cache pour les ressources distantes de GLM Code."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Union, Dict, Any

from glmcode.version import Version


class RemoteResource:
    """Représente une ressource distante avec métadonnées de cache."""

    def __init__(
        self,
        url: str,
        cache_key: str,
        expires_in: int = 3600,  # 1 heure par défaut
    ):
        self.url = url
        self.cache_key = cache_key
        self.expires_in = expires_in
        self._last_fetch: float = 0
        self._cached_data: Optional[bytes] = None
        self._etag: Optional[str] = None
        self._last_modified: Optional[str] = None

    def is_expired(self) -> bool:
        """Verifie si le cache est expiré."""
        return time.time() - self._last_fetch > self.expires_in

    def needs_update(self) -> bool:
        """Verifie si une mise à jour est nécessaire (expiré ou jamais récupéré)."""
        return self._cached_data is None or self.is_expired()


class RemoteClient:
    """Client HTTP pour récupérer des ressources distantes avec mise en cache locale."""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialise le client distant.

        Args:
            cache_dir: Répertoire pour le cache local (défaut: .cache/remote)
        """
        if cache_dir is None:
            cache_dir = os.path.join(".cache", "remote")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._resources: dict[str, RemoteResource] = {}

    def _get_cache_path(self, cache_key: str) -> Path:
        """Obtient le chemin du fichier de cache pour une clé donnée."""
        # Hasher la clé pour éviter les problèmes de système de fichiers
        hashed = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{hashed}.cache"

    def _get_meta_path(self, cache_key: str) -> Path:
        """Obtient le chemin du fichier de métadonnées de cache."""
        hashed = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{hashed}.meta"

    def _save_to_cache(self, cache_key: str, data: bytes, etag: Optional[str] = None, last_modified: Optional[str] = None) -> None:
        """Sauvegarde les données dans le cache avec métadonnées."""
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_meta_path(cache_key)

        # Sauvegarder les données
        cache_path.write_bytes(data)

        # Sauvegarder les métadonnées
        meta_data = {
            "etag": etag,
            "last_modified": last_modified,
            "timestamp": time.time(),
        }
        meta_path.write_text(json.dumps(meta_data, indent=2))

    def _load_from_cache(self, cache_key: str) -> tuple[Optional[bytes], Optional[str], Optional[str]]:
        """Charge les données depuis le cache si disponibles et valides."""
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_meta_path(cache_key)

        if not cache_path.exists() or not meta_path.exists():
            return None, None, None

        try:
            # Charger les métadonnées
            meta_data = json.loads(meta_path.read_text())
            etag = meta_data.get("etag")
            last_modified = meta_data.get("last_modified")
            timestamp = meta_data.get("timestamp", 0)

            # Vérifier si le cache est encore valide (24h max pour les métadonnées)
            if time.time() - timestamp > 86400:  # 24 heures
                return None, None, None

            # Charger les données
            data = cache_path.read_bytes()
            return data, etag, last_modified
        except (json.JSONDecodeError, OSError):
            return None, None, None

    def _fetch_url(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        timeout: int = 30
    ) -> tuple[Optional[int], Optional[bytes], Optional[str], Optional[str]]:
        """
        Récupère une URL avec support conditionnel GET.

        Returns:
            Tuple (status_code, data, etag, last_modified) ou (None, None, None, None) en cas d'erreur
        """
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "GLM-Code-Updater/1.0")

        if etag:
            req.add_header("If-None-Match", etag)
        if last_modified:
            req.add_header("If-Modified-Since", last_modified)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = response.getcode()
                data = response.read()
                new_etag = response.headers.get("ETag")
                new_last_modified = response.headers.get("Last-Modified")
                return status, data, new_etag, new_last_modified
        except urllib.error.HTTPError as e:
            # 304 Not Modified signifie que le cache est encore valide
            if e.code == 304:
                return 304, None, etag, last_modified
            # Autres erreurs HTTP
            return None, None, None, None
        except urllib.error.URLError:
            # Erreur de réseau
            return None, None, None, None
        except Exception:
            # Autre erreur inattendue
            return None, None, None, None

    def get_resource(
        self,
        url: str,
        cache_key: Optional[str] = None,
        expires_in: int = 3600,
        force_refresh: bool = False
    ) -> Optional[bytes]:
        """
        Récupère une ressource depuis l'URL avec mise en cache.

        Args:
            url: URL de la ressource à récupérer
            cache_key: Clé de cache personnalisée (si None, basée sur l'URL)
            expires_in: Durée de validité du cache en secondes
            force_refresh: Forcer le rechargement depuis la source

        Returns:
            Les données de la ressource ou None en cas d'erreur
        """
        if cache_key is None:
            cache_key = url

        # Obtenir ou créer la ressource
        if cache_key not in self._resources:
            self._resources[cache_key] = RemoteResource(url, cache_key, expires_in)
        resource = self._resources[cache_key]

        # Vérifier si on peut utiliser le cache
        if not force_refresh and not resource.needs_update():
            cached_data, _, _ = self._load_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # Essayer de récupérer depuis le réseau avec support conditionnel
        cached_data, etag, last_modified = self._load_from_cache(cache_key)
        status, data, new_etag, new_last_modified = self._fetch_url(
            url,
            etag=etag,
            last_modified=last_modified
        )

        if status == 200 and data is not None:
            # Nouvelle donnée reçue
            self._save_to_cache(cache_key, data, new_etag, new_last_modified)
            resource._last_fetch = time.time()
            resource._cached_data = data
            resource._etag = new_etag
            resource._last_modified = new_last_modified
            return data
        elif status == 304:
            # Le cache est encore valide
            if cached_data is not None:
                resource._last_fetch = time.time()  # Rafraîchir le timestamp
                return cached_data
            # Si on n'a pas de cache malgré le 304, essayer de le recharger sans condition
            return self.get_resource(url, cache_key, expires_in, force_refresh=True)
        else:
            # Erreur ou pas de modification, retourner le cache si disponible
            if cached_data is not None:
                return cached_data
            return None

    def get_json(
        self,
        url: str,
        cache_key: Optional[str] = None,
        expires_in: int = 3600,
        force_refresh: bool = False
    ) -> Optional[dict]:
        """
        Récupère et parse du JSON depuis une URL.

        Args:
            url: URL du ressource JSON
            cache_key: Clé de cache personnalisée
            expires_in: Durée de validité du cache en secondes
            force_refresh: Forcer le rechargement depuis la source

        Returns:
            Dictionnaire parsé ou None en cas d'erreur
        """
        data = self.get_resource(url, cache_key, expires_in, force_refresh)
        if data is None:
            return None

        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def get_text(
        self,
        url: str,
        cache_key: Optional[str] = None,
        expires_in: int = 3600,
        force_refresh: bool = False
    ) -> Optional[str]:
        """
        Récupère du texte depuis une URL.

        Args:
            url: URL de la ressource texte
            cache_key: Clé de cache personnalisée
            expires_in: Durée de validité du cache en secondes
            force_refresh: Forcer le rechargement depuis la source

        Returns:
            Contenu texte ou None en cas d'erreur
        """
        data = self.get_resource(url, cache_key, expires_in, force_refresh)
        if data is None:
            return None

        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return None

    def clear_cache(self, older_than: Optional[float] = None) -> int:
        """
        Nettoie le cache.

        Args:
            older_than: Supprimer les entrées plus anciennes que ce nombre de secondes
                       (None = tout supprimer)

        Returns:
            Nombre de fichiers supprimés
        """
        count = 0
        now = time.time()

        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                if older_than is None:
                    # Supprimer tout
                    cache_file.unlink()
                    # Aussi supprimer les métadonnées associées
                    meta_file = self.cache_dir / f"{cache_file.stem}.meta"
                    if meta_file.exists():
                        meta_file.unlink()
                    count += 1
                else:
                    # Vérifier l'âge basé sur le fichier de métadonnées
                    meta_file = self.cache_dir / f"{cache_file.stem}.meta"
                    if meta_file.exists():
                        meta_data = json.loads(meta_file.read_text())
                        timestamp = meta_data.get("timestamp", 0)
                        if now - timestamp > older_than:
                            cache_file.unlink()
                            meta_file.unlink()
                            count += 1
            except (OSError, json.JSONDecodeError, KeyError):
                # En cas d'erreur, continuer avec les autres fichiers
                continue

        return count

    def get_cache_size(self) -> int:
        """
        Retourne la taille totale du cache en octets.

        Returns:
            Taille en octets
        """
        total_size = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                total_size += cache_file.stat().st_size
            except OSError:
                pass
        return total_size