from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from eldoria.db.connection import get_conn


# ---------- Secret roles ----------

def sr_upsert(guild_id: int, channel_id: int, phrase: str, role_id: int) -> None:
    """Crée ou met à jour une règle de rôle secret associant une phrase à un rôle dans un salon donné."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO secret_roles(guild_id, channel_id, phrase, role_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, channel_id, phrase) DO UPDATE SET role_id=excluded.role_id
        """, (guild_id, channel_id, phrase, role_id))


def sr_delete(guild_id: int, channel_id: int, phrase: str) -> None:
    """Supprime une règle de rôle secret pour une phrase donnée dans un salon."""
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM secret_roles
            WHERE guild_id=? AND channel_id=? AND phrase=?
        """, (guild_id, channel_id, phrase))


def sr_match(guild_id: int, channel_id: int, phrase: str) -> Optional[int]:
    """Retourne l'identifiant du rôle associé à une phrase si elle existe, sinon None."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT role_id FROM secret_roles
            WHERE guild_id=? AND channel_id=? AND phrase=?
        """, (guild_id, channel_id, phrase)).fetchone()
    return row[0] if row else None


def sr_list_messages(guild_id: int, channel_id: int) -> List[str]:
    """Liste toutes les phrases configurées pour les rôles secrets d'un salon, triées alphabétiquement."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT phrase
            FROM secret_roles
            WHERE guild_id=? AND channel_id=?
            ORDER BY phrase
        """, (guild_id, channel_id)).fetchall()
    return [r[0] for r in rows]


def sr_list_by_guild_grouped(guild_id: int) -> List[Tuple[str, Dict[str, int]]]:
    """
    Retourne les rôles secrets d'un serveur, groupés par salon.

    Format:
        [
            (channel_id, {phrase: role_id}),
            ...
        ]

    Le channel_id est retourné sous forme de chaîne afin d'être directement
    compatible avec une sérialisation JSON (ex: list(secret_roles_guild.items())).
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT channel_id, phrase, role_id
            FROM secret_roles
            WHERE guild_id=?
            ORDER BY channel_id
        """, (guild_id,)).fetchall()

    grouped: Dict[str, Dict[str, int]] = {}
    for channel_id, phrase, role_id in rows:
        grouped.setdefault(str(channel_id), {})[phrase] = role_id

    return list(grouped.items())
