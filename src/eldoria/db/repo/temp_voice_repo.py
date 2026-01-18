from ..connection import get_conn

# ---------- Temp voice ------------
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
