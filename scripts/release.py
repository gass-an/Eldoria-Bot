"""Release Eldoria: tag current version and push commit + tag."""

import subprocess

from src.eldoria.version import VERSION


def run(cmd: list[str]) -> None:
    """Exécute une commande, en levant en cas d'erreur."""
    subprocess.run(cmd, check=True)


def tag_exists(tag: str) -> bool:
    """Vérifie si un tag git existe déjà."""
    res = subprocess.run(["git", "tag", "--list", tag], capture_output=True, text=True, check=True)
    return bool(res.stdout.strip())


# Repo clean (staged & unstaged)
run(["git", "diff", "--quiet"])
run(["git", "diff", "--cached", "--quiet"])

tag = f"v{VERSION}"

if tag_exists(tag):
    raise SystemExit(f"Tag {tag} existe déjà. Abandon.")

run(["git", "tag", tag])
run(["git", "push"])
run(["git", "push", "origin", tag])

print(f"Release {tag} publiée avec succès.")