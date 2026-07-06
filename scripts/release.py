"""Release Eldoria: push current release commit, create tag, then push tag.

Idempotent behavior:
- if the remote tag already exists and points to the current commit, the release is considered already published;
- if a local tag already exists and points to the current commit, it is reused and pushed;
- if a tag exists but points elsewhere, the script aborts.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Final

VERSION_FILE: Final[Path] = Path("src/eldoria/version.py")
VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'VERSION\s*:\s*Final\[str]\s*=\s*"(?P<v>[^"]+)"'
)


def run(cmd: list[str]) -> None:
    """Exécute une commande, en levant en cas d'erreur."""
    subprocess.run(cmd, check=True)


def output(cmd: list[str], *, check: bool = True) -> str:
    """Exécute une commande et retourne stdout nettoyé."""
    res = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return res.stdout.strip()


def ensure_repo_root() -> None:
    """Vérifie que le script est lancé depuis la racine du dépôt Git."""
    root = output(["git", "rev-parse", "--show-toplevel"])
    cwd = Path.cwd().resolve()
    if Path(root).resolve() != cwd:
        raise SystemExit(f"Lance ce script depuis la racine du dépôt: {root}")


def ensure_on_main() -> None:
    """Vérifie que la branche courante est main."""
    branch = output(["git", "branch", "--show-current"])
    if branch != "main":
        raise SystemExit(f"Publication refusée: branche courante '{branch}', attendu 'main'.")


def ensure_clean() -> None:
    """Vérifie qu'aucun changement local n'est présent."""
    run(["git", "diff", "--quiet"])
    run(["git", "diff", "--cached", "--quiet"])
    status = output(["git", "status", "--porcelain"])
    if status:
        raise SystemExit("Repo non clean. Commit/stash avant release.")


def read_version() -> str:
    """Lit la version actuelle dans src/eldoria/version.py."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    m = VERSION_PATTERN.search(content)
    if not m:
        raise SystemExit("VERSION introuvable dans src/eldoria/version.py")
    return m.group("v")


def rev_parse(ref: str) -> str | None:
    """Retourne le hash d'une référence Git, ou None si elle n'existe pas."""
    res = subprocess.run(["git", "rev-parse", "--verify", ref], capture_output=True, text=True)
    if res.returncode != 0:
        return None
    return res.stdout.strip()


def tag_commit(ref: str) -> str | None:
    """Retourne le commit pointé par un tag local, en supportant aussi les tags annotés."""
    return rev_parse(f"{ref}^{{}}") or rev_parse(ref)


def remote_tag_commit(tag: str) -> str | None:
    """Retourne le commit du tag distant origin/tag, ou None s'il n'existe pas."""
    res = subprocess.run(["git", "ls-remote", "--tags", "origin", tag], capture_output=True, text=True, check=True)
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    # Un tag léger pointe directement vers le commit. Un tag annoté expose aussi tag^{}.
    peeled = [line for line in lines if line.endswith(f"refs/tags/{tag}^{{}}")]
    selected = peeled[0] if peeled else lines[0]
    return selected.split()[0]


def main() -> None:
    """Pousse le commit de release, crée le tag si nécessaire, puis pousse le tag."""
    ensure_repo_root()
    ensure_on_main()
    ensure_clean()

    run(["git", "fetch", "origin", "main", "--tags"])

    version = read_version()
    tag = f"v{version}"
    head = output(["git", "rev-parse", "HEAD"])

    remote_tag = remote_tag_commit(tag)
    if remote_tag == head:
        print(f"Release {tag} déjà publiée.")
        return
    if remote_tag is not None:
        raise SystemExit(f"Tag distant {tag} existe déjà mais ne pointe pas vers HEAD. Abandon.")

    local_tag = tag_commit(f"refs/tags/{tag}")
    if local_tag is not None and local_tag != head:
        raise SystemExit(f"Tag local {tag} existe déjà mais ne pointe pas vers HEAD. Abandon.")

    # Important: pousser main avant de créer/pousser le tag distant.
    # Si ce push échoue, aucun tag de release n'est publié.
    run(["git", "push", "origin", "HEAD:main"])

    if local_tag is None:
        run(["git", "tag", tag])

    run(["git", "push", "origin", tag])
    print(f"Release {tag} publiée avec succès.")


if __name__ == "__main__":
    main()
