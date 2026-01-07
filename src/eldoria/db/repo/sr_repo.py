from ..connection import get_conn

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