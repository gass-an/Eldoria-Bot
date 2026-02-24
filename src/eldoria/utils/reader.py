"""Utilitaires pour la lecture de fichiers, notamment les logs du bot."""


from collections import deque
from pathlib import Path

from eldoria.config import LOG_PATH
from eldoria.exceptions.general import LogFileNotFound


def tail_lines(path: str = LOG_PATH, maxlen: int = 200) -> str:
    """Lit les n dernières lignes d'un fichier de log et les retourne sous forme de chaîne de caractères."""
    p = Path(path)
    if not p.exists():
        raise LogFileNotFound()

    with p.open("r", encoding="utf-8", errors="replace") as f:
        last = deque(f, maxlen=maxlen)

    return "".join(last)