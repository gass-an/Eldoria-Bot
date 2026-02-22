"""Roll CHANGELOG.md.

- moves content under '## [Unreleased]' into '## [X.Y.Z] - YYYY-MM-DD'
- removes empty categories (### ...) in the created release section
- recreates an empty Unreleased template

Usage:
  python scripts/roll_changelog.py 0.6.1
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Final

CHANGELOG: Final[Path] = Path("CHANGELOG.md")

UNRELEASED_TEMPLATE: Final[str] = """## [Unreleased]

### Added

### Changed

### Fixed

### Notes

"""


def extract_unreleased(text: str) -> tuple[str, str, str]:
    """Extrait la section Unreleased du changelog, et retourne (before, unreleased_body, after)."""
    m = re.search(r"^## \[Unreleased\]\s*$", text, flags=re.MULTILINE)
    if not m:
        raise SystemExit("CHANGELOG.md: section '## [Unreleased]' introuvable.")

    header_end = text.find("\n", m.end())
    header_end = len(text) if header_end == -1 else header_end + 1

    m2 = re.search(r"^## \[.+?\]", text[header_end:], flags=re.MULTILINE)
    body_end = header_end + m2.start() if m2 else len(text)

    before = text[: m.start()]
    body = text[header_end:body_end].strip("\n")
    after = text[body_end:].lstrip("\n")
    return before, body, after


def clean_empty_categories(body: str) -> str:
    """Supprime les catégories (### ...) qui n'ont pas de bullet points dans leur section."""
    body = body.strip()
    if not body:
        return ""

    chunks = re.split(r"(?=^### )", body, flags=re.MULTILINE)
    kept: list[str] = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        lines = chunk.splitlines()
        header = lines[0].strip() if lines else ""
        rest = lines[1:] if len(lines) > 1 else []

        has_bullets = any(line.strip().startswith("-") for line in rest)
        if header.startswith("### ") and has_bullets:
            kept.append(chunk)
        elif not header.startswith("### "):
            kept.append(chunk)  # keep unexpected text

    return "\n\n".join(kept).strip()


def main() -> None:
    """Parse arguments, extract Unreleased section, clean it, and write back the updated changelog."""
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        raise SystemExit(__doc__.strip()) # type: ignore

    version = sys.argv[1]
    today = date.today().isoformat()

    text = CHANGELOG.read_text(encoding="utf-8")
    before, unreleased_body, after = extract_unreleased(text)

    cleaned = clean_empty_categories(unreleased_body)
    if not cleaned:
        raise SystemExit("Unreleased est vide (aucune entrée '- ...'). Abandon.")

    release_section = f"## [{version}] - {today}\n\n{cleaned}\n\n"

    new_text = before + UNRELEASED_TEMPLATE + "\n" + release_section + after
    new_text = re.sub(r"\n{4,}", "\n\n\n", new_text)

    CHANGELOG.write_text(new_text, encoding="utf-8")
    print(f"CHANGELOG rolled -> {version} ({today})")


if __name__ == "__main__":
    main()