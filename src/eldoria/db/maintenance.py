# src/eldoria/db/maintenance.py
import os, sqlite3,  shutil, errno
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
