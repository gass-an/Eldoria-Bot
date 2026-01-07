# src/eldoria/db/maintenance.py
import os, sqlite3
from .connection import DB_PATH, _DB_LOCK

def backup_to_file(dst_path: str):
    """
    Exporte une copie cohérente de la DB vers dst_path.
    Le verrou empêche toute écriture/lecture concurrente via get_conn().
    """
    with _DB_LOCK:
        # checkpoint WAL au cas où
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("PRAGMA wal_checkpoint(FULL);")
        except sqlite3.DatabaseError:
            pass

        bck = sqlite3.connect(dst_path)
        try:
            conn.backup(bck)
        finally:
            bck.close()
            conn.close()

def replace_db_file(new_db_path: str):
    """
    Remplace DB_PATH par new_db_path de façon atomique.
    Le verrou garantit que personne n'utilise la DB pendant le swap.
    """
    with _DB_LOCK:
        # petite vérif que c'est bien une sqlite
        test = sqlite3.connect(new_db_path)
        try:
            test.execute("PRAGMA schema_version;").fetchone()
        finally:
            test.close()

        # Remplacement atomique
        os.replace(new_db_path, DB_PATH)
