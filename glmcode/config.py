"""Chargement de la configuration (API Z.ai / GLM-4.7).

Priorite (du plus fort au plus faible) :
1. Variables d'environnement (GLMCODE_*)
2. Fichier config.toml dans le dossier courant
3. Fichier ~/.glmcode/config.toml
4. Valeurs par defaut

L'endpoint est compatible avec l'API OpenAI (/chat/completions).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


# Reglages par defaut pour l'API Z.ai (GLM-4.7).
DEFAULT_BASE_URL = "https://api.z.ai/api/paas/v4"
DEFAULT_MODEL = "glm-4.5-flash"  # modele gratuit ; glm-4.6/glm-4.7 sont payants

# Codeur local (Ollama) par defaut pour le mode orchestrateur.
DEFAULT_CODER_BASE_URL = "http://localhost:11434/v1"
DEFAULT_CODER_MODEL = "qwen2.5-coder:latest"


@dataclass
class CoderConfig:
    """Modele 'codeur' delegue par l'orchestrateur (ex. qwen2.5-coder via Ollama)."""

    enabled: bool = False
    base_url: str = DEFAULT_CODER_BASE_URL
    model: str = DEFAULT_CODER_MODEL
    api_key: str = ""  # vide pour Ollama
    fallback_model: str = ""  # modele de secours si le principal est rate-limite
    max_retries: int = 3
    temperature: float = 0.2
    max_tokens: int = 8192


@dataclass
class RuntimeConfig:
    """Surveillance de fichiers en arriere-plan (reveil automatique de l'agent)."""

    enabled: bool = True
    file_watch_delay: float = 2.0


@dataclass
class Config:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    # Modele de secours si `model` est indisponible (surcharge / rate limit).
    fallback_model: str = "glm-4.5-flash"
    max_retries: int = 3
    temperature: float = 0.3
    max_tokens: int = 8192
    # Confirmation avant toute action qui modifie le disque ou lance une commande.
    auto_approve: bool = False
    system_prompt: str = ""
    # Modele codeur (orchestrateur). Desactive par defaut = mono-modele.
    coder: CoderConfig = field(default_factory=CoderConfig)
    # Skills : dossiers supplementaires + integration des skills Claude Code.
    skills_dirs: list = field(default_factory=list)
    include_claude_skills: bool = False
    # Surveillance de fichiers (section [runtime] optionnelle).
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)


def _load_toml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _config_search_paths() -> list[Path]:
    return [
        Path.cwd() / "config.toml",
        Path.home() / ".glmcode" / "config.toml",
    ]


def load_config() -> Config:
    data: dict = {}
    for path in _config_search_paths():
        found = _load_toml(path)
        if found:
            # Le premier fichier trouve gagne (dossier courant prioritaire).
            data = found
            break

    # Supporte une section [zai] optionnelle ou des cles a la racine.
    section = data.get("zai", {}) if isinstance(data.get("zai"), dict) else {}

    def pick(env_key: str, toml_key: str, fallback):
        if env_key in os.environ:
            return os.environ[env_key]
        if toml_key in section:
            return section[toml_key]
        if toml_key in data:
            return data[toml_key]
        return fallback

    api_key = pick("GLMCODE_API_KEY", "api_key", "")
    # Compat : accepte aussi les cles standard Z.ai.
    if not api_key:
        api_key = os.environ.get("ZAI_API_KEY", os.environ.get("ZHIPUAI_API_KEY", ""))

    # Section [coder] optionnelle (orchestrateur cerveau + codeur).
    coder_section = data.get("coder", {}) if isinstance(data.get("coder"), dict) else {}
    coder_enabled = str(
        os.environ.get("GLMCODE_CODER_ENABLED", coder_section.get("enabled", False))
    ).lower() in ("1", "true", "yes", "on")
    coder = CoderConfig(
        enabled=coder_enabled,
        base_url=str(
            os.environ.get(
                "GLMCODE_CODER_BASE_URL",
                coder_section.get("base_url", DEFAULT_CODER_BASE_URL),
            )
        ),
        model=str(
            os.environ.get(
                "GLMCODE_CODER_MODEL", coder_section.get("model", DEFAULT_CODER_MODEL)
            )
        ),
        api_key=str(coder_section.get("api_key", "")),
        fallback_model=str(coder_section.get("fallback_model", "")),
        max_retries=int(coder_section.get("max_retries", 3)),
        temperature=float(coder_section.get("temperature", 0.2)),
        max_tokens=int(coder_section.get("max_tokens", 8192)),
    )

    # Section [skills] optionnelle.
    skills_section = data.get("skills", {}) if isinstance(data.get("skills"), dict) else {}
    skills_dirs = skills_section.get("dirs", []) or []
    include_claude_skills = str(
        os.environ.get(
            "GLMCODE_CLAUDE_SKILLS", skills_section.get("include_claude", False)
        )
    ).lower() in ("1", "true", "yes", "on")

    # Section [runtime] optionnelle (surveillance de fichiers en arriere-plan).
    runtime_section = data.get("runtime", {}) if isinstance(data.get("runtime"), dict) else {}
    runtime_cfg = RuntimeConfig(
        enabled=str(
            os.environ.get("GLMCODE_WATCH_ENABLED", runtime_section.get("enabled", True))
        ).lower()
        in ("1", "true", "yes", "on"),
        file_watch_delay=float(runtime_section.get("file_watch_delay", 2.0)),
    )

    return Config(
        api_key=str(api_key),
        base_url=str(pick("GLMCODE_BASE_URL", "base_url", DEFAULT_BASE_URL)),
        model=str(pick("GLMCODE_MODEL", "model", DEFAULT_MODEL)),
        fallback_model=str(pick("GLMCODE_FALLBACK_MODEL", "fallback_model", "glm-4.5-flash")),
        max_retries=int(pick("GLMCODE_MAX_RETRIES", "max_retries", 3)),
        temperature=float(pick("GLMCODE_TEMPERATURE", "temperature", 0.3)),
        max_tokens=int(pick("GLMCODE_MAX_TOKENS", "max_tokens", 8192)),
        auto_approve=str(pick("GLMCODE_AUTO_APPROVE", "auto_approve", "false")).lower()
        in ("1", "true", "yes", "on"),
        system_prompt=str(data.get("system_prompt", "")),
        coder=coder,
        skills_dirs=list(skills_dirs),
        include_claude_skills=include_claude_skills,
        runtime=runtime_cfg,
    )