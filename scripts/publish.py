"""Publication en une commande.

publication complète (bump + changelog + commit + tag+push):
  python scripts/publish.py --to 0.6.1

Test local (bump + changelog + commit), WITHOUT tag/push:
  python scripts/publish.py --to 0.6.1 --no-release
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Final

SCRIPTS_DIR: Final[Path] = Path("scripts")
BUMP: Final[Path] = SCRIPTS_DIR / "bump_version.py"
ROLL: Final[Path] = SCRIPTS_DIR / "roll_changelog.py"
COMMIT: Final[Path] = SCRIPTS_DIR / "commit_release.py"
RELEASE: Final[Path] = SCRIPTS_DIR / "release.py"

VERSION_FILE: Final[Path] = Path("src/eldoria/version.py")
VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'VERSION\s*:\s*Final\[str\]\s*=\s*"(?P<v>\d+\.\d+\.\d+)"'
)


def run(cmd: list[str]) -> None:
    """Exécute une commande, en levant en cas d'erreur."""
    subprocess.run(cmd, check=True)


def ensure_repo_clean() -> None:
    """Vérifie que le repo git est clean (pas de changement non commité)."""
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    if res.stdout.strip():
        raise SystemExit("Repo non clean. Commit/stash avant publish.")


def read_version() -> str:
    """Lit la version actuelle dans src/eldoria/version.py."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    m = VERSION_PATTERN.search(content)
    if not m:
        raise SystemExit("VERSION introuvable dans src/eldoria/version.py")
    return m.group("v")


def main() -> None:
    """Publie une nouvelle version.
    
    - bump version
    - roll changelog
    - commit changes

    Usage:
        python scripts/publish.py --to 0.6.1        
        python scripts/publish.py --to 0.6.1 --no-release
    """
    args = sys.argv[1:]
    if "--to" not in args:
        raise SystemExit(__doc__.strip()) # type: ignore

    no_release = "--no-release" in args
    args = [a for a in args if a != "--no-release"]

    if len(args) != 2 or args[0] != "--to":
        raise SystemExit(__doc__.strip()) # type: ignore

    ensure_repo_clean()

    before = read_version()
    to_version = args[1]
    if not re.fullmatch(r"\d+\.\d+\.\d+", to_version):
        raise SystemExit("Version invalide. Format attendu: X.Y.Z")

    run(["python", str(BUMP), "--to", to_version])

    after = read_version()
    if after == before:
        raise SystemExit("La version n'a pas changé. Abandon.")

    run(["python", str(ROLL), after])
    run(["python", str(COMMIT), after])

    if not no_release:
        run(["python", str(RELEASE)])
        print(f"Published v{after}")
    else:
        print(f"Local publish OK (no tag/push): v{after}")


if __name__ == "__main__":
    main()