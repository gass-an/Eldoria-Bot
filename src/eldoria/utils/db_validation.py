"""Utilitaires pour la validation de fichiers de base de données SQLite."""

import sqlite3
import tempfile
import time
from pathlib import Path

import discord


async def is_valid_sqlite_db(attachment: discord.Attachment) -> bool:
    """Vérifie si un fichier attaché est une base de données SQLite valide."""
    if not attachment.filename.lower().endswith(".db"):
        return False

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()

    await attachment.save(tmp_path)

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(tmp_path))
        conn.execute("PRAGMA schema_version;")
        return True
    except sqlite3.DatabaseError:
        return False
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass

        for _ in range(5):
            try:
                tmp_path.unlink()
                break
            except FileNotFoundError:
                break
            except PermissionError:
                time.sleep(0.05)
