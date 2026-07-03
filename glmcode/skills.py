"""Systeme de skills : des fichiers markdown reutilisables invocables par /nom.

Un skill est un fichier .md avec un entete (frontmatter) :

    ---
    name: revue-code
    description: Revue de code approfondie
    ---

    <instructions injectees dans le contexte quand on invoque /revue-code>

Ils sont cherches dans (par ordre de priorite) :
1. ./skills/            (dossier du projet courant)
2. ~/.glmcode/skills/   (skills globaux de l'utilisateur)
3. le pack integre livre avec GLM Code
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    body: str
    source: str  # "projet", "global" ou "integre"


def _parse(path: Path, source: str) -> Skill | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    name = path.stem
    description = ""
    body = text

    # Frontmatter optionnel entre deux lignes '---'.
    if text.lstrip().startswith("---"):
        stripped = text.lstrip()
        end = stripped.find("\n---", 3)
        if end != -1:
            header = stripped[3:end]
            body = stripped[end + 4 :].lstrip("\n")
            for line in header.splitlines():
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()
                # Retire les guillemets eventuels autour de la valeur.
                value = value.strip('"').strip("'")
                if key == "name" and value:
                    name = value
                elif key == "description":
                    description = value

    return Skill(name=name, description=description, body=body.strip(), source=source)


def claude_skill_dirs() -> list[Path]:
    """Detecte les dossiers de skills de Claude Code presents sur la machine."""
    dirs: list[Path] = []
    # Skills "superpowers" (workflows de dev generaux) — derniere version.
    sp = Path.home() / ".claude" / "plugins" / "cache" / "claude-plugins-official" / "superpowers"
    if sp.is_dir():
        versions = sorted(p for p in sp.iterdir() if (p / "skills").is_dir())
        if versions:
            dirs.append(versions[-1] / "skills")
    # Skills personnels de l'utilisateur.
    personal = Path.home() / ".claude" / "skills"
    if personal.is_dir():
        dirs.append(personal)
    return dirs


def _scan_dir(directory: Path, source: str, out: dict[str, Skill]) -> None:
    # Fichiers plats : ./skills/nom.md
    for path in sorted(directory.glob("*.md")):
        skill = _parse(path, source)
        if skill and skill.name not in out:
            out[skill.name] = skill
    # Structure Claude : ./skills/nom/SKILL.md
    for path in sorted(directory.glob("*/SKILL.md")):
        skill = _parse(path, source)
        if skill and skill.name not in out:
            out[skill.name] = skill


def load_skills(
    extra_dirs: list[str] | None = None, include_claude: bool = False
) -> dict[str, Skill]:
    """Charge tous les skills. Le premier trouve (par ordre des dossiers) gagne."""
    dirs: list[tuple[Path, str]] = [
        (Path.cwd() / "skills", "projet"),
        (Path.home() / ".glmcode" / "skills", "global"),
        (Path(__file__).parent / "builtin_skills", "integre"),
    ]
    for extra in extra_dirs or []:
        dirs.append((Path(extra).expanduser(), "config"))
    if include_claude:
        dirs.extend((d, "claude") for d in claude_skill_dirs())

    skills: dict[str, Skill] = {}
    for directory, source in dirs:
        if directory.is_dir():
            _scan_dir(directory, source, skills)
    return skills


def compose_prompt(skill: Skill, user_arg: str) -> str:
    """Construit le message a envoyer au modele a partir d'un skill + l'argument."""
    if user_arg:
        return f"{skill.body}\n\n---\nDemande de l'utilisateur : {user_arg}"
    return skill.body
