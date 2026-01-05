import os
import sqlite3
import threading
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

def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS reaction_roles (
          guild_id    INTEGER NOT NULL,
          message_id  INTEGER NOT NULL,
          emoji       TEXT    NOT NULL,
          role_id     INTEGER NOT NULL,
          PRIMARY KEY (guild_id, message_id, emoji)
        );

        CREATE TABLE IF NOT EXISTS secret_roles (
          guild_id    INTEGER NOT NULL,
          channel_id  INTEGER NOT NULL,
          phrase      TEXT    NOT NULL,
          role_id     INTEGER NOT NULL,
          PRIMARY KEY (guild_id, channel_id, phrase)
        );

        CREATE TABLE IF NOT EXISTS temp_voice_parents (
          guild_id           INTEGER NOT NULL,
          parent_channel_id  INTEGER NOT NULL,
          user_limit         INTEGER NOT NULL,
          PRIMARY KEY (guild_id, parent_channel_id)
        );

        CREATE TABLE IF NOT EXISTS temp_voice_active (
          guild_id           INTEGER NOT NULL,
          parent_channel_id  INTEGER NOT NULL,
          channel_id         INTEGER NOT NULL,
          PRIMARY KEY (guild_id, parent_channel_id, channel_id)
        );
        """)
# ----------Helpeurs save replace database

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


# ---------- Reaction roles ----------
def rr_upsert(guild_id: int, message_id: int, emoji: str, role_id: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO reaction_roles(guild_id, message_id, emoji, role_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, message_id, emoji) DO UPDATE SET role_id=excluded.role_id
        """, (guild_id, message_id, emoji, role_id))

def rr_delete(guild_id: int, message_id: int, emoji: str):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM reaction_roles
            WHERE guild_id=? AND message_id=? AND emoji=?
        """, (guild_id, message_id, emoji))

def rr_delete_message(guild_id: int, message_id: int):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM reaction_roles
            WHERE guild_id=? AND message_id=?
        """, (guild_id, message_id))

def rr_get_role_id(guild_id: int, message_id: int, emoji: str):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT role_id FROM reaction_roles
            WHERE guild_id=? AND message_id=? AND emoji=?
        """, (guild_id, message_id, emoji)).fetchone()
    return row[0] if row else None

def rr_list_by_message(guild_id: int, message_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT emoji, role_id
            FROM reaction_roles
            WHERE guild_id=? AND message_id=?
        """, (guild_id, message_id)).fetchall()
    return {emoji: role_id for (emoji, role_id) in rows}

def rr_list_by_guild_grouped(guild_id: int):
    """
    Retourne une liste de tuples:
      [(message_id, {emoji: role_id}), ...]
    compatible avec ton paginator + embed_generator existants.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT message_id, emoji, role_id
            FROM reaction_roles
            WHERE guild_id=?
            ORDER BY message_id
        """, (guild_id,)).fetchall()

    grouped = {}
    for message_id, emoji, role_id in rows:
        grouped.setdefault(str(message_id), {})[emoji] = role_id

    # format identique à ton JSON: list(role_config_guild.items())
    return list(grouped.items())

# ---------- Secret roles ----------
def sr_upsert(guild_id: int, channel_id: int, phrase: str, role_id: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO secret_roles(guild_id, channel_id, phrase, role_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, channel_id, phrase) DO UPDATE SET role_id=excluded.role_id
        """, (guild_id, channel_id, phrase, role_id))

def sr_delete(guild_id: int, channel_id: int, phrase: str):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM secret_roles
            WHERE guild_id=? AND channel_id=? AND phrase=?
        """, (guild_id, channel_id, phrase))

def sr_match(guild_id: int, channel_id: int, phrase: str):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT role_id FROM secret_roles
            WHERE guild_id=? AND channel_id=? AND phrase=?
        """, (guild_id, channel_id, phrase)).fetchone()
    return row[0] if row else None

def sr_list_messages(guild_id: int, channel_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT phrase
            FROM secret_roles
            WHERE guild_id=? AND channel_id=?
            ORDER BY phrase
        """, (guild_id, channel_id)).fetchall()
    return [r[0] for r in rows]

def sr_list_by_guild_grouped(guild_id: int):
    """
    Retourne une liste de tuples:
      [(channel_id, {phrase: role_id}), ...]
    format compatible avec list(secret_roles_guild.items()) côté JSON.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT channel_id, phrase, role_id
            FROM secret_roles
            WHERE guild_id=?
            ORDER BY channel_id
        """, (guild_id,)).fetchall()

    grouped = {}
    for channel_id, phrase, role_id in rows:
        grouped.setdefault(str(channel_id), {})[phrase] = role_id

    return list(grouped.items())


# ---------- Temp voice ----------
def tv_upsert_parent(guild_id: int, parent_channel_id: int, user_limit: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO temp_voice_parents(guild_id, parent_channel_id, user_limit)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, parent_channel_id) DO UPDATE SET user_limit=excluded.user_limit
        """, (guild_id, parent_channel_id, user_limit))

def tv_get_parent(guild_id: int, parent_channel_id: int):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT user_limit FROM temp_voice_parents
            WHERE guild_id=? AND parent_channel_id=?
        """, (guild_id, parent_channel_id)).fetchone()
    return row[0] if row else None

def tv_find_parent_of_active(guild_id: int, channel_id: int):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT parent_channel_id
            FROM temp_voice_active
            WHERE guild_id=? AND channel_id=?
        """, (guild_id, channel_id)).fetchone()
    return row[0] if row else None

def tv_add_active(guild_id: int, parent_channel_id: int, channel_id: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO temp_voice_active(guild_id, parent_channel_id, channel_id)
            VALUES (?, ?, ?)
        """, (guild_id, parent_channel_id, channel_id))

def tv_remove_active(guild_id: int, parent_channel_id: int, channel_id: int):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM temp_voice_active
            WHERE guild_id=? AND parent_channel_id=? AND channel_id=?
        """, (guild_id, parent_channel_id, channel_id))

def tv_list_active(guild_id: int, parent_channel_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT channel_id FROM temp_voice_active
            WHERE guild_id=? AND parent_channel_id=?
        """, (guild_id, parent_channel_id)).fetchall()
    return [r[0] for r in rows]
def tv_list_active_all(guild_id: int):
    with get_conn() as conn:
        return conn.execute("""
            SELECT parent_channel_id, channel_id
            FROM temp_voice_active
            WHERE guild_id=?
        """, (guild_id,)).fetchall()

def tv_delete_parent(guild_id: int, parent_channel_id: int):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM temp_voice_parents
            WHERE guild_id=? AND parent_channel_id=?
        """, (guild_id, parent_channel_id))

def tv_list_parents(guild_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT parent_channel_id, user_limit
            FROM temp_voice_parents
            WHERE guild_id=?
        """, (guild_id,)).fetchall()
    return rows
