"""Bump Eldoria version in src/eldoria/version.py.

Usage:
  python scripts/bump_version.py --to 0.6.1
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

VERSION_FILE: Final[Path] = Path("src/eldoria/version.py")
PATTERN: Final[re.Pattern[str]] = re.compile(
    r'VERSION\s*:\s*Final\[str\]\s*=\s*"(?P<v>\d+\.\d+\.\d+)"'
)


def read_version() -> str:
    """Lit la version actuelle dans src/eldoria/version.py."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    m = PATTERN.search(content)
    if not m:
        raise SystemExit(
            'VERSION introuvable (attendu: VERSION: Final[str] = "x.y.z") dans src/eldoria/version.py'
        )
    return m.group("v")


def set_version(new_version: str) -> None:
    """Remplace la version dans src/eldoria/version.py par new_version."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    new_content, n = PATTERN.subn(f'VERSION: Final[str] = "{new_version}"', content)
    if n != 1:
        raise SystemExit("Échec: remplacement VERSION (match inattendu).")
    VERSION_FILE.write_text(new_content, encoding="utf-8")


def main() -> None:
    """Parse les arguments, vérifie le format de la nouvelle version, et met à jour src/eldoria/version.py."""
    args = sys.argv[1:]
    if len(args) != 2 or args[0] != "--to":
        raise SystemExit(__doc__.strip())   # type: ignore

    new_version = args[1]
    if not re.fullmatch(r"\d+\.\d+\.\d+", new_version):
        raise SystemExit("Version invalide. Format attendu: X.Y.Z")

    current = read_version()
    set_version(new_version)
    print(f"Version: {current} -> {new_version}")


if __name__ == "__main__":
    main()