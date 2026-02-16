from __future__ import annotations

import sys
from pathlib import Path


def add_src_to_syspath() -> None:
    """Ajoute le dossier src au PYTHONPATH AVANT tout import projet."""
    root = Path(__file__).resolve().parents[2]  # tests/_bootstrap -> tests -> repo root
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
