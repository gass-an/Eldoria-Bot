import sqlite3
import tempfile
import os

async def is_valid_sqlite_db(attachment) -> bool:
    # 1. Vérification extension
    if not attachment.filename.lower().endswith(".db"):
        return False

    # 2. Sauvegarde temporaire
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        await attachment.save(tmp.name)
        tmp_path = tmp.name

    # 3. Vérification réelle SQLite
    try:
        conn = sqlite3.connect(tmp_path)
        conn.execute("PRAGMA schema_version;")
        conn.close()
        return True
    except sqlite3.DatabaseError:
        return False
    finally:
        os.remove(tmp_path)
