"""Script de release pour le bot Eldoria, qui crée un tag Git avec la version actuelle et pousse le commit et le tag vers le dépôt distant."""

import subprocess

from src.eldoria.version import VERSION


def run(cmd: list[str]) -> None:
    """Exécute une commande shell et affiche la sortie, en levant une exception en cas d'erreur."""
    subprocess.run(cmd, check=True)

# Vérifie que le repo est clean
run(["git", "diff", "--quiet"])

# Crée le tag sur le commit courant
run(["git", "tag", f"v{VERSION}"])

# Push le commit
run(["git", "push"])

# Push le tag
run(["git", "push", "origin", f"v{VERSION}"])

print(f"Release v{VERSION} publiée avec succès.")
