"""Module de gestion de la connexion à la base de données SQLite."""

import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager

DB_PATH = "./data/eldoria.db"
_DB_LOCK = threading.RLock()

@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Context manager pour obtenir une connexion à la base de données SQLite.
    
    Assure que les connexions sont thread-safe en utilisant un verrou.
    """
    with _DB_LOCK:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
