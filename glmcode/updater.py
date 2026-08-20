"""Systeme de mise a jour automatique pour GLM Code."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from glmcode.remote import RemoteClient
from glmcode.version import Version, get_default_version


class UpdateManager:
    """Gestionnaire de mise a jour pour GLM Code."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialise le gestionnaire de mise a jour.

        Args:
            config_dir: Répertoire de configuration (défaut: répertoire courant)
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd()
        self.cache_dir = self.config_dir / ".cache" / "remote"
        self.backup_dir = self.config_dir / ".backup"
        self.update_url = "https://raw.githubusercontent.com/Marreouu/MAJ-GLMC0DE/main/remote/update.json"
        self.remote_client = RemoteClient(str(self.cache_dir))
        self._current_version: Optional[Version] = None
        self._update_info: Optional[Dict[str, Any]] = None

    def _get_current_version(self) -> Version:
        """Obtient la version actuelle de l'application."""
        if self._current_version is None:
            self._current_version = get_default_version()
        return self._current_version

    def check_for_update(self, channel: str = "stable") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verifie si une mise a jour est disponible.

        Args:
            channel: Canal de mise a jour a verifier (stable, beta, dev)

        Returns:
            Tuple (mise_a_jour_disponible, informations_de_mise_a_jour)
        """
        try:
            # Récupérer les informations de mise à jour
            update_data = self.remote_client.get_json(
                self.update_url,
                cache_key="update.json",
                expires_in=300,  # 5 minutes
                force_refresh=False
            )

            if update_data is None:
                return False, None

            # Vérifier le canal
            if update_data.get("channel", "stable") != channel:
                return False, None

            self._update_info = update_data

            # Analyser la version
            remote_version_str = update_data.get("version", "0.0.0")
            try:
                remote_version = Version.parse(remote_version_str)
            except ValueError:
                return False, None

            current_version = self._get_current_version()

            # Vérifier si une mise à jour est disponible
            update_available = remote_version > current_version

            # Vérifier la version minimale requise
            min_version_str = update_data.get("minimum_version", "0.0.0")
            try:
                min_version = Version.parse(min_version_str)
                if current_version < min_version:
                    # La version actuelle est trop ancienne, mise à jour critique
                    update_available = True
            except ValueError:
                pass

            return update_available, update_data

        except Exception:
            return False, None

    def _download_update(self, download_url: str, expected_hash: Optional[str] = None) -> Optional[Path]:
        """
        Télécharge la mise à jour depuis l'URL spécifiée.

        Args:
            download_url: URL du fichier ZIP de mise à jour
            expected_hash: Hash SHA256 attendu pour vérifier l'intégrité

        Returns:
            Chemin vers le fichier téléchargé ou None en cas d'échec
        """
        try:
            # Télécharger dans un fichier temporaire
            temp_dir = Path(tempfile.gettempdir())
            zip_path = temp_dir / f"glmcode_update_{int(time.time())}.zip"

            # Télécharger avec suivi de progression
            response_data = self.remote_client.get_resource(
                download_url,
                cache_key=f"update_zip_{hashlib.md5(download_url.encode()).hexdigest()}",
                expires_in=3600,  # 1 heure
                force_refresh=True
            )

            if response_data is None:
                return None

            # Écrire le fichier téléchargé
            zip_path.write_bytes(response_data)

            # Vérifier l'intégrité si un hash est fourni
            if expected_hash is not None:
                actual_hash = hashlib.sha256(response_data).hexdigest()
                if actual_hash.lower() != expected_hash.lower():
                    zip_path.unlink(missing_ok=True)
                    return None

            return zip_path

        except Exception:
            return None

    def _create_backup(self) -> Optional[Path]:
        """
        Crée une sauvegarde de l'installation actuelle.

        Returns:
            Chemin vers l'archive de sauvegarde ou None en cas d'échec
        """
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time())
            backup_name = f"glmcode_backup_{timestamp}"
            backup_path = self.backup_dir / f"{backup_name}.zip"

            # Fichiers et répertoires à sauvegarder
            items_to_backup = [
                "glmcode/",  # Code source principal
                "config/",   # Configuration
                "data/",     # Données utilisateur (si existe)
                "data/",     # Données utilisateur (si existe)
                "sessions/", # Sessions sauvegardées
                ".glmcode/", # Configuration utilisateur
                "requirements.txt",
                "README.md",
                "LICENSE",
            ]

            # Créer l'archive ZIP
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for item in items_to_backup:
                    item_path = self.config_dir / item
                    if not item_path.exists():
                        continue

                    if item_path.is_file():
                        # Ajouter le fichier individuel
                        arcname = str(Path(item) / item_path.name)
                        zipf.write(item_path, arcname)
                    elif item_path.is_dir():
                        # Ajouter récursivement le contenu du répertoire
                        for file_path in item_path.rglob("*"):
                            if file_path.is_file():
                                # Calculer le chemin relatif pour l'archive
                                relative_path = file_path.relative_to(self.config_dir)
                                arcname = str(relative_path)
                                zipf.write(file_path, arcname)

            return backup_path

        except Exception:
            return None

    def _extract_update(self, zip_path: Path, extract_to: Path) -> bool:
        """
        Extrait la mise à jour depuis l'archive ZIP.

        Args:
            zip_path: Chemin vers l'archive ZIP
            extract_to: Répertoire où extraire les fichiers

        Returns:
            True si l'extraction réussit, False sinon
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # Vérifier l'intégrité de l'archive
                bad_file = zipf.testzip()
                if bad_file is not None:
                    return False

                # Extraire tous les fichiers
                zipf.extractall(extract_to)
                return True

        except Exception:
            return False

    def _apply_update(self, extracted_dir: Path) -> bool:
        """
        Applique la mise à jour en remplaçant les fichiers anciens.

        Args:
            extracted_dir: Répertoire contenant les fichiers mis à jour

        Returns:
            True si l'application réussit, False sinon
        """
        try:
            # Liste des éléments à mettre à jour depuis l'archive
            # On exclut certains répertoires/fichiers utilisateur pour préserver les données
            items_to_update = [
                "glmcode/",
                "requirements.txt",
                "README.md",
                "LICENSE",
            ]

            # Fichiers et répertoires à prservers (utilisateur)
            protected_items = {
                "config/",          # Configuration utilisateur
                "data/",            # Données utilisateur
                "sessions/",        # Sessions sauvegardées
                ".cache/",          # Cache
                ".backup/",         # Sauvegardes
                ".glmcode/",        # Configuration CLI utilisateur
                "*.toml",           # Fichiers de configuration
                "*.json",           # Fichiers de configuration JSON
            }

            def should_protect(path: Path) -> bool:
                """Détermine si un chemin doit être protégé (pas écrasé)."""
                path_str = str(path.relative_to(extracted_dir)) if path.is_relative_to(extracted_dir) else str(path)

                # Vérifier les modèles de protection
                for pattern in protected_items:
                    if pattern.endswith("/"):
                        # Répertoire à protéger
                        if path_str.startswith(pattern.rstrip("/")):
                            return True
                    elif "*" in pattern:
                        # Modèle avec wildcard
                        import fnmatch
                        if fnmatch.fnmatch(path_str, pattern):
                            return True
                    else:
                        # Correspondance exacte
                        if path_str == pattern:
                            return True
                return False

            # Copier les fichiers de mise à jour
            for item in items_to_update:
                src_item = extracted_dir / item
                if not src_item.exists():
                    continue

                dest_item = self.config_dir / item

                if src_item.is_file():
                    # Copier le fichier individuel
                    dest_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_item, dest_item)
                elif src_item.is_dir():
                    # Copier récursivement le répertoire
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    shutil.copytree(
                        src_item,
                        dest_item,
                        ignore=lambda src, names: [
                            name for name in names
                            if should_protect(Path(src) / name)
                        ]
                    )
                else:
                    # Lien symbolique ou autre type spécial
                    if dest_item.exists():
                        if dest_item.is_symlink() or not dest_item.is_dir():
                            dest_item.unlink()
                        else:
                            shutil.rmtree(dest_item)
                    shutil.copy2(src_item, dest_item)

            return True

        except Exception:
            return False

    def _restore_from_backup(self, backup_path: Path) -> bool:
        """
        Restaure l'application depuis une sauvegarde.

        Args:
            backup_path: Chemin vers l'archive de sauvegarde

        Returns:
            True si la restauration réussit, False sinon
        """
        try:
            # Créer un répertoire temporaire pour l'extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extraire la sauvegarde
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_path)

                # Trouver le répertoire racine de la sauvegarde
                # (il devrait contenir le contenu de l'application)
                items = list(temp_path.iterdir())
                if len(items) == 1 and items[0].is_dir():
                    source_dir = items[0]
                else:
                    source_dir = temp_path

                # Restaurer en écrasant tout sauf les éléments protégés
                protected_items = {
                    "config/",
                    "data/",
                    "sessions/",
                    ".cache/",
                    ".backup/",
                    ".glmcode/",
                    "*.toml",
                    "*.json",
                }

                def should_protect(path: Path) -> bool:
                    """Détermine si un chemin doit être protégé pendant la restauration."""
                    try:
                        relative_path = path.relative_to(source_dir)
                        path_str = str(relative_path)
                    except ValueError:
                        # Le chemin n'est pas relatif à source_dir
                        return False

                    # Vérifier les modèles de protection
                    for pattern in protected_items:
                        if pattern.endswith("/"):
                            # Répertoire à protéger
                            if path_str.startswith(pattern.rstrip("/")):
                                return True
                        elif "*" in pattern:
                            # Modèle avec wildcard
                            import fnmatch
                            if fnmatch.fnmatch(path_str, pattern):
                                return True
                        else:
                            # Correspondance exacte
                            if path_str == pattern:
                                return True
                    return False

                # Copier tout sauf les éléments protégés
                for item in source_dir.rglob("*"):
                    if item.is_file():
                        relative_path = item.relative_to(source_dir)
                        dest_path = self.config_dir / relative_path

                        # Vérifier si ce fichier doit être protégé
                        if should_protect(item):
                            continue  # Ne pas écraser les éléments protégés

                        # Créer le répertoire de destination si nécessaire
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_path)

            return True

        except Exception:
            return False

    def apply_update(self) -> bool:
        """
        Applique la mise à jour disponible.

        Returns:
            True si la mise à jour réussit, False sinon
        """
        if self._update_info is None:
            return False

        try:
            # Étape 1: Créer une sauvegarde
            backup_path = self._create_backup()
            if backup_path is None:
                return False

            try:
                # Étape 2: Télécharger la mise à jour
                download_url = self._update_info.get("download_zip")
                if not download_url:
                    return False

                zip_path = self._download_update(download_url)
                if zip_path is None:
                    return False

                try:
                    # Étape 3: Extraire dans un répertoire temporaire
                    with tempfile.TemporaryDirectory() as temp_dir:
                        extract_path = Path(temp_dir) / "extracted"
                        extract_path.mkdir()

                        if not self._extract_update(zip_path, extract_path):
                            return False

                        # Étape 4: Appliquer la mise à jour
                        if not self._apply_update(extract_path):
                            return False

                        # Nettoyer le fichier ZIP téléchargé
                        zip_path.unlink(missing_ok=True)

                        # Mettre à jour la version actuelle si disponible
                        if "version" in self._update_info:
                            try:
                                self._current_version = Version.parse(self._update_info["version"])
                            except ValueError:
                                pass  # Garder l'ancienne version si échec de parsing

                        return True

                finally:
                    # Nettoyer le fichier ZIP en cas d'erreur
                    zip_path.unlink(missing_ok=True)

            except Exception:
                # En cas d'échec, tenter de restaurer depuis la sauvegarde
                if backup_path and backup_path.exists():
                    self._restore_from_backup(backup_path)
                raise

        except Exception:
            return False

    def get_update_info(self) -> Optional[Dict[str, Any]]:
        """Retourne les informations de la dernière vérification de mise à jour."""
        return self._update_info

    def get_current_version(self) -> Version:
        """Retourne la version actuelle de l'application."""
        return self._get_current_version()

    def get_latest_version(self) -> Optional[Version]:
        """Retourne la dernière version disponible si une vérification a été effectuée."""
        if self._update_info is None:
            return None
        try:
            return Version.parse(self._update_info.get("version", "0.0.0"))
        except ValueError:
            return None