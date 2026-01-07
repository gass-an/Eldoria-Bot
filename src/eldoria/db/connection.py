# src/eldoria/db/connection.py
import os, sqlite3, threading
from contextlib import contextmanager

DB_PATH = "./data/eldoria.db"
_DB_LOCK = threading.RLock()

@contextmanager
def get_conn():
    with _DB_LOCK:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
