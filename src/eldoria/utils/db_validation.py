import os
import sqlite3
import tempfile
import time


async def is_valid_sqlite_db(attachment) -> bool:
    # 1) Vérification extension
    if not attachment.filename.lower().endswith(".db"):
        return False

    # 2) Sauvegarde temporaire
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    await attachment.save(tmp_path)

    conn = None
    try:
        conn = sqlite3.connect(tmp_path)
        conn.execute("PRAGMA schema_version;")
        return True
    except sqlite3.DatabaseError:
        return False
    finally:
        # fermer la DB si ouverte
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass

        # suppression robuste (Windows peut locker le fichier brièvement)
        for _ in range(5):
            try:
                os.remove(tmp_path)
                break
            except FileNotFoundError:
                break
            except PermissionError:
                time.sleep(0.05)
        # Si après retries ça ne passe pas, on n'explose pas :
        # le fichier peut être nettoyé par un job/cron, ou sera écrasé plus tard.
