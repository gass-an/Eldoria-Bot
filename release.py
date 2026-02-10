import subprocess

from src.eldoria.version import VERSION


def run(cmd):
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
