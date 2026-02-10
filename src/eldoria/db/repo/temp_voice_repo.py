from __future__ import annotations

from typing import Optional, List, Tuple

from eldoria.db.connection import get_conn



# ---------- Temp voice ------------

def tv_upsert_parent(guild_id: int, parent_channel_id: int, user_limit: int) -> None:
    """Insère ou met à jour la configuration d'un parent de salons vocaux temporaires (limite d'utilisateurs)."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO temp_voice_parents(guild_id, parent_channel_id, user_limit)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, parent_channel_id) DO UPDATE SET user_limit=excluded.user_limit
        """, (guild_id, parent_channel_id, user_limit))


def tv_get_parent(guild_id: int, parent_channel_id: int) -> Optional[int]:
    """Récupère la limite d'utilisateurs d'un parent de salons temporaires ; None si non configuré."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT user_limit FROM temp_voice_parents
            WHERE guild_id=? AND parent_channel_id=?
        """, (guild_id, parent_channel_id)).fetchone()
    return row[0] if row else None


def tv_find_parent_of_active(guild_id: int, channel_id: int) -> Optional[int]:
    """Retourne l'identifiant du parent associé à un salon temporaire actif ; None si introuvable."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT parent_channel_id
            FROM temp_voice_active
            WHERE guild_id=? AND channel_id=?
        """, (guild_id, channel_id)).fetchone()
    return row[0] if row else None


def tv_add_active(guild_id: int, parent_channel_id: int, channel_id: int) -> None:
    """Enregistre un salon vocal temporaire actif (sans effet s'il existe déjà)."""
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO temp_voice_active(guild_id, parent_channel_id, channel_id)
            VALUES (?, ?, ?)
        """, (guild_id, parent_channel_id, channel_id))


def tv_remove_active(guild_id: int, parent_channel_id: int, channel_id: int) -> None:
    """Supprime l'enregistrement d'un salon vocal temporaire actif."""
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM temp_voice_active
            WHERE guild_id=? AND parent_channel_id=? AND channel_id=?
        """, (guild_id, parent_channel_id, channel_id))


def tv_list_active(guild_id: int, parent_channel_id: int) -> List[int]:
    """Liste les identifiants des salons vocaux temporaires actifs pour un parent donné."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT channel_id FROM temp_voice_active
            WHERE guild_id=? AND parent_channel_id=?
        """, (guild_id, parent_channel_id)).fetchall()
    return [r[0] for r in rows]


def tv_list_active_all(guild_id: int) -> List[Tuple[int, int]]:
    """Liste tous les salons vocaux temporaires actifs d'un serveur (parent_channel_id, channel_id)."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT parent_channel_id, channel_id
            FROM temp_voice_active
            WHERE guild_id=?
        """, (guild_id,)).fetchall()


def tv_delete_parent(guild_id: int, parent_channel_id: int) -> None:
    """Supprime la configuration d'un parent de salons vocaux temporaires."""
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM temp_voice_parents
            WHERE guild_id=? AND parent_channel_id=?
        """, (guild_id, parent_channel_id))


def tv_list_parents(guild_id: int) -> List[Tuple[int, int]]:
    """Liste les parents de salons vocaux temporaires configurés (parent_channel_id, user_limit)."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT parent_channel_id, user_limit
            FROM temp_voice_parents
            WHERE guild_id=?
        """, (guild_id,)).fetchall()
    return rows
