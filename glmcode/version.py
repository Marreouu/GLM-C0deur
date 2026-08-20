"""Gestion des versions pour le systeme de mise a jour automatique de GLM Code."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Version:
    """Representation d'une version semantique (major.minor.patch)."""
    major: int
    minor: int
    patch: int
    suffix: str = ""

    def __post_init__(self):
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Les numeros de version doivent être positifs")

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """
        Analyse une chaine de version en objet Version.

        Supporte les formats:
        - "1.0.0"
        - "1.0.0-alpha"
        - "v1.0.0"
        - "1.0.0+build.1"

        Args:
            version_str: Chaine representant la version

        Returns:
            Instance de Version

        Raises:
            ValueError: Si la chaine ne peut pas être analysée
        """
        # Nettoyer la chaine
        version_str = version_str.strip().lower()

        # Enlever le prefixe 'v' si present
        if version_str.startswith('v'):
            version_str = version_str[1:]

        # Separer la partie principale du suffixe (build, pre-release, etc.)
        # On garde seulement la partie principale pour la comparaison
        main_part = version_str.split('+')[0].split('-')[0]

        # Parser les composants principaux
        parts = main_part.split('.')
        if len(parts) != 3:
            raise ValueError(f"Format de version invalide: {version_str}")

        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except ValueError:
            raise ValueError(f"Les composants de version doivent être des entiers: {version_str}")

        # Extraire le suffixe (tout ce qui vient apres le troisieme point ou apres un tiret)
        suffix = ""
        if '-' in version_str:
            # Tout apres le premier tiret (après avoir enlevé le 'v' éventuel)
            suffix_part = version_str.split('-', 1)[1]
            # Mais on veut garder seulement ce qui est avant le '+'
            if '+' in suffix_part:
                suffix = '-' + suffix_part.split('+')[0]
            else:
                suffix = '-' + suffix_part
        elif '+' in version_str:
            # C'est un build metadata, on le garde comme suffixe
            suffix = '+' + version_str.split('+', 1)[1]

        return cls(major, minor, patch, suffix)

    def __str__(self) -> str:
        """Retourne la representation en chaine de la version."""
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.suffix:
            return base + self.suffix
        return base

    def __lt__(self, other: "Version") -> bool:
        """Comparaison stricte inférieure."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "Version") -> bool:
        """Comparaison inférieure ou égale."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "Version") -> bool:
        """Comparaison stricte supérieure."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "Version") -> bool:
        """Comparaison supérieure ou égale."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        """Egalité (ignore les suffixes pour la comparaison de base)."""
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __ne__(self, other: object) -> bool:
        """Inégalité."""
        if not isinstance(other, Version):
            return NotImplemented
        return not self.__eq__(other)

    def is_compatible_with(self, other: "Version") -> bool:
        """
        Verifie si cette version est compatible avec une autre version.

        Selon la sémantique de versioning, les versions avec le même majeur
        sont considérées comme compatibles pour les mises à jour mineures.
        """
        if not isinstance(other, Version):
            return NotImplemented
        return self.major == other.major


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare deux chaines de version.

    Returns:
        -1 si v1 < v2
         0 si v1 == v2
         1 si v1 > v2
    """
    try:
        version1 = Version.parse(v1)
        version2 = Version.parse(v2)
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0
    except ValueError:
        # En cas d'erreur de parsing, retourner une comparaison lexicographique
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0


def is_version_compatibility(current: str, required: str) -> bool:
    """
    Verifie si la version actuelle satisfait la version requise.

    Args:
        current: Version actuelle (ex: "1.2.3")
        required: Version requise (ex: ">=1.0.0" ou "1.0.0")

    Returns:
        True si la version actuelle satisface la requise
    """
    # Gérer les expressions de version simples
    if '>=' in required:
        min_version = required.split('>=')[1].strip()
        return compare_versions(current, min_version) >= 0
    elif '>' in required:
        min_version = required.split('>')[1].strip()
        return compare_versions(current, min_version) > 0
    elif '<=' in required:
        max_version = required.split('<=')[1].strip()
        return compare_versions(current, max_version) <= 0
    elif '<' in required:
        max_version = required.split('<')[1].strip()
        return compare_versions(current, max_version) < 0
    elif '=' in required or not any(op in required for op in ['>', '<', '=']):
        # Version exacte ou implicite
        target_version = required.replace('=', '').strip()
        return compare_versions(current, target_version) == 0
    else:
        # Par défaut, essayer une comparaison directe
        return compare_versions(current, required) >= 0


def get_default_version() -> Version:
    """Retourne la version par defaut depuis __version__.py."""
    try:
        from glmcode import __version__
        return Version.parse(__version__)
    except (ImportError, AttributeError, ValueError):
        return Version(0, 1, 0)  # Version de secours