"""Module de gestion des tests unitaires avec pytest."""

import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from eldoria.exceptions.internal import TestsFailed

log = logging.getLogger(__name__)

_PYTEST_SUMMARY_RE = re.compile(
    r"(?:(?P<failed>\d+)\s+failed)?"
    r"(?:,\s*)?"
    r"(?:(?P<passed>\d+)\s+passed)?"
    r"(?:,\s*)?"
    r"(?:(?P<skipped>\d+)\s+skipped)?"
    r"(?:,\s*)?"
    r"(?:(?P<xfailed>\d+)\s+xfailed)?"
    r"(?:,\s*)?"
    r"(?:(?P<xpassed>\d+)\s+xpassed)?"
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TESTS_PATH = PROJECT_ROOT / "tests"

def _parse_pytest_counts(output: str) -> dict[str, int]:
    """Extrait les compteurs depuis la/les lignes de fin pytest.
    
    '2 failed, 367 passed, 4 skipped in 3.21s'
    """
    counts = {"failed": 0, "passed": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}

    # on cherche en partant de la fin (le résumé est à la fin)
    for line in reversed(output.splitlines()):
        if " in " in line and ("passed" in line or "failed" in line or "skipped" in line):
            m = _PYTEST_SUMMARY_RE.search(line)
            if m:
                for k in counts:
                    v = m.group(k)
                    counts[k] = int(v) if v else 0
                return counts

    # fallback: parfois pytest -q sort un résumé minimal
    # ex: "367 passed in 2.13s"
    for line in reversed(output.splitlines()):
        m = _PYTEST_SUMMARY_RE.search(line)
        if m and (m.group("passed") or m.group("failed")):
            for k in counts:
                v = m.group(k)
                counts[k] = int(v) if v else 0
            return counts

    return counts

def run_tests(*, logger: logging.Logger | None = None) -> str | None:
    """Lance pytest si des tests existent.

    Retourne un label stylé pour step(): "367/367 Tests validés" ou "2 tests fails / 367".
    En cas d'échec, log la liste des tests en échec (résumé pytest) et lève si TESTS_STRICT=1.
    """
    # ✅ Ne jamais relancer pytest quand on est déjà dans pytest (évite pytest-dans-pytest)
    if "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules:
        return None

    if logger is None:
        logger = log

    tests_path = TESTS_PATH
    if not tests_path.exists() or not any(tests_path.rglob("test_*.py")):
        return None

    logger.info("⏳ Lancement des tests…")

    p = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        capture_output=True,
        text=True,
    )

    combined = (p.stdout or "") + "\n" + (p.stderr or "")
    counts = _parse_pytest_counts(combined)

    total = counts["passed"] + counts["failed"] + counts["skipped"] + counts["xfailed"] + counts["xpassed"]
    failed = counts["failed"]
    passed = counts["passed"]

    # Fallbacks si parsing KO
    if total == 0 and p.returncode == 0:
        return "Tests validés"
    if total == 0 and p.returncode != 0:
        logger.warning("❌ Tests en échec (résumé indisponible)")
        # tente quand même d'afficher un résumé utile
        logger.warning("📌 Sortie pytest:\n%s", combined.strip()[-2000:])
        raise TestsFailed()

    # ✅ Succès
    if failed == 0 and p.returncode == 0:
        return f"{passed}/{total} Tests validés"

    # ❌ Échec
    logger.warning("❌ Tests : %d fails | %d passed | %d total", failed, passed, total)

    # 🔎 Récupérer une liste lisible des échecs (sans tout spammer)
    maxfail = int(os.getenv("TESTS_MAXFAIL", "20"))
    details = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-rfE",         # short summary (fails + errors)
            "--tb=short",
            f"--maxfail={maxfail}",
        ],
        capture_output=True,
        text=True,
    )

    out = ((details.stdout or "") + "\n" + (details.stderr or "")).strip()
    if out:
        lines = [l.rstrip() for l in out.splitlines() if l.strip()]

        # garder surtout la section "short test summary info"
        start = None
        for i, line in enumerate(lines):
            if "short test summary info" in line.lower():
                start = i
                break

        if start is not None:
            snippet = lines[start : start + 80]  # limite anti-spam
        else:
            # fallback: juste les lignes FAILED/ERROR
            failed_lines = [l for l in lines if l.startswith("FAILED ") or l.startswith("ERROR ")]
            snippet = failed_lines[:80] if failed_lines else lines[-80:]

        logger.warning("📌 Détails des échecs:\n%s", "\n".join(snippet))

    strict = os.getenv("TESTS_STRICT", "1") == "1"  # par défaut: on bloque
    if strict:
        raise TestsFailed()

    return f"{failed} tests fails / {total}"
