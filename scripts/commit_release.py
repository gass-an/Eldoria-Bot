"""Commit release changes (version.py + CHANGELOG.md only).

Usage:
  python scripts/commit_release.py 0.6.1
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Final

VERSION_FILE: Final[Path] = Path("src/eldoria/version.py")
CHANGELOG: Final[Path] = Path("CHANGELOG.md")


def run(cmd: list[str]) -> None:
    """Exécute une commande, en levant en cas d'erreur."""
    subprocess.run(cmd, check=True)


def output(cmd: list[str]) -> str:
    """Exécute une commande et retourne stdout nettoyé."""
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout.strip()


def ensure_only_release_files_modified() -> None:
    """Vérifie que seuls VERSION_FILE et CHANGELOG sont modifiés (staged ou unstaged)."""
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]

    # Normalize to POSIX paths for cross-platform compatibility (Windows/Linux/Mac)
    allowed = {VERSION_FILE.as_posix(), CHANGELOG.as_posix()}

    for ln in lines:
        raw_path = ln[3:].strip()  # after "XY "
        norm_path = raw_path.replace("\\", "/")
        if norm_path not in allowed:
            raise SystemExit(f"Refus: autre fichier modifié détecté: {ln}")


def has_release_changes() -> bool:
    """Indique si les fichiers de release contiennent des changements à committer."""
    res = subprocess.run(
        ["git", "diff", "--quiet", "--", str(VERSION_FILE), str(CHANGELOG)],
        check=False,
    )
    return res.returncode != 0


def main() -> None:
    """Parse arguments, ensure only release files are modified, and commit."""
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        raise SystemExit(__doc__.strip())  # type: ignore

    version = sys.argv[1]
    expected_message = f"release(v{version})"

    if output(["git", "log", "-1", "--pretty=%s"]) == expected_message and not output(
        ["git", "status", "--porcelain"]
    ):
        print(f"Commit déjà présent: {expected_message}")
        return

    ensure_only_release_files_modified()

    if not has_release_changes():
        raise SystemExit("Aucun changement de release à committer.")

    run(["git", "add", str(VERSION_FILE), str(CHANGELOG)])
    run(["git", "commit", "-m", expected_message])
    print(f"Committed: {expected_message}")


if __name__ == "__main__":
    main()
