"""Module de maintenance de la base de données SQLite, incluant des fonctions pour sauvegarder et remplacer le fichier de la base de données."""
import errno
import os
import shutil
import sqlite3

from eldoria.db.connection import _DB_LOCK, DB_PATH


def backup_to_file(dst_path: str) -> None:
    """Crée une copie de la base de données SQLite à l'emplacement spécifié."""
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

def replace_db_file(new_db_path: str) -> None:
    """Remplace le fichier de la base de données SQLite par celui spécifié.
    
    Effectue des vérifications pour s'assurer que le nouveau fichier est une base de données SQLite valide avant de remplacer l'ancien.
    """
    with _DB_LOCK:
        test = sqlite3.connect(new_db_path)
        try:
            test.execute("PRAGMA schema_version;").fetchone()
        finally:
            test.close()

        try:
            os.replace(new_db_path, DB_PATH)
        except OSError as e:
            # Cross-device link (EXDEV/errno 18 selon plateformes)
            if e.errno in (errno.EXDEV, 18):
                dst_dir = os.path.dirname(DB_PATH) or "."
                os.makedirs(dst_dir, exist_ok=True)

                tmp_in_dst = os.path.join(dst_dir, ".incoming_eldoria.db")
                shutil.copy2(new_db_path, tmp_in_dst)
                os.replace(tmp_in_dst, DB_PATH)  # atomique dans le même FS

                try:
                    os.remove(new_db_path)
                except OSError:
                    pass
            else:
                raise
