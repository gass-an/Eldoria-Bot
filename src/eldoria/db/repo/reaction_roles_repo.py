from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from eldoria.db.connection import get_conn


# ---------- Reaction roles --------

def rr_upsert(guild_id: int, message_id: int, emoji: str, role_id: int) -> None:
    """Crée ou met à jour une règle de rôle par réaction pour un message et un emoji donnés."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO reaction_roles(guild_id, message_id, emoji, role_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, message_id, emoji) DO UPDATE SET role_id=excluded.role_id
        """, (guild_id, message_id, emoji, role_id))


def rr_delete(guild_id: int, message_id: int, emoji: str) -> None:
    """Supprime une règle de rôle par réaction pour un emoji précis sur un message."""
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM reaction_roles
            WHERE guild_id=? AND message_id=? AND emoji=?
        """, (guild_id, message_id, emoji))


def rr_delete_message(guild_id: int, message_id: int) -> None:
    """Supprime toutes les règles de rôles par réaction associées à un message."""
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM reaction_roles
            WHERE guild_id=? AND message_id=?
        """, (guild_id, message_id))


def rr_get_role_id(guild_id: int, message_id: int, emoji: str) -> Optional[int]:
    """Retourne l'identifiant du rôle associé à un emoji sur un message, ou None s'il n'existe pas."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT role_id FROM reaction_roles
            WHERE guild_id=? AND message_id=? AND emoji=?
        """, (guild_id, message_id, emoji)).fetchone()
    return row[0] if row else None


def rr_list_by_message(guild_id: int, message_id: int) -> Dict[str, int]:
    """Retourne toutes les règles de rôles par réaction d'un message sous forme {emoji: role_id}."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT emoji, role_id
            FROM reaction_roles
            WHERE guild_id=? AND message_id=?
        """, (guild_id, message_id)).fetchall()
    return {emoji: role_id for (emoji, role_id) in rows}


def rr_list_by_guild_grouped(guild_id: int) -> List[Tuple[str, Dict[str, int]]]:
    """
    Retourne les rôles par réaction d'un serveur, groupés par message.

    Format:
        [
            (message_id, {emoji: role_id}),
            ...
        ]

    Le message_id est retourné sous forme de chaîne afin d'être compatible
    avec le format JSON et les paginateurs/embeds existants.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT message_id, emoji, role_id
            FROM reaction_roles
            WHERE guild_id=?
            ORDER BY message_id
        """, (guild_id,)).fetchall()

    grouped: Dict[str, Dict[str, int]] = {}
    for message_id, emoji, role_id in rows:
        grouped.setdefault(str(message_id), {})[emoji] = role_id

    # format identique à list(role_config_guild.items())
    return list(grouped.items())
