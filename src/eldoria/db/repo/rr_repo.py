from ..connection import get_conn

# ---------- Reaction roles --------
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