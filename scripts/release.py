"""Release Eldoria: tag current version and push commit + tag."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Final

VERSION_FILE: Final[Path] = Path("src/eldoria/version.py")
VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'VERSION\s*:\s*Final\[str\]\s*=\s*"(?P<v>\d+\.\d+\.\d+)"'
)


def run(cmd: list[str]) -> None:
    """Exécute une commande, en levant en cas d'erreur."""
    subprocess.run(cmd, check=True)


def tag_exists(tag: str) -> bool:
    """Vérifie si un tag git existe déjà."""
    res = subprocess.run(["git", "tag", "--list", tag], capture_output=True, text=True, check=True)
    return bool(res.stdout.strip())


def read_version() -> str:
    """Lit la version actuelle dans src/eldoria/version.py."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    m = VERSION_PATTERN.search(content)
    if not m:
        raise SystemExit("VERSION introuvable dans src/eldoria/version.py")
    return m.group("v")


# Repo clean (staged & unstaged)
run(["git", "diff", "--quiet"])
run(["git", "diff", "--cached", "--quiet"])

version = read_version()
tag = f"v{version}"

if tag_exists(tag):
    raise SystemExit(f"Tag {tag} existe déjà. Abandon.")

run(["git", "tag", tag])
run(["git", "push"])
run(["git", "push", "origin", tag])

print(f"Release {tag} publiée avec succès.")