"""Module de gestion des messages de bienvenue.

Contenant les fonctions nécessaires pour créer, récupérer, mettre à jour et supprimer les configurations de messages de bienvenue
et leur historique dans la base de données.
"""

from __future__ import annotations

import time
from typing import Any

from eldoria.db.connection import get_conn

# ------------ Welcome message -----------

def wm_ensure_defaults(guild_id: int, *, enabled: bool = False, channel_id: int = 0) -> None:
    """Crée la ligne de config si absente (valeurs par défaut côté code)."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO welcome_config(guild_id, enabled, channel_id)
            VALUES (?, ?, ?)
            """,
            (guild_id, 1 if enabled else 0, int(channel_id)),
        )


def wm_get_config(guild_id: int) -> dict[str, Any]:
    """Retourne {"enabled": bool, "channel_id": int} et crée la config si absente."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT enabled, channel_id FROM welcome_config WHERE guild_id=?",
            (guild_id,),
        ).fetchone()

    if not row:
        # IMPORTANT: channel_id est NOT NULL => on met 0 par défaut
        wm_ensure_defaults(guild_id, enabled=False, channel_id=0)
        return {"enabled": False, "channel_id": 0}

    return {"enabled": bool(row[0]), "channel_id": int(row[1])}


def wm_set_config(
    guild_id: int,
    *,
    enabled: bool | None = None,
    channel_id: int | None = None,
) -> None:
    """Update partiel (enabled et/ou channel_id). Crée la ligne si absente."""
    sets: list[str] = []
    params: list[int] = []

    if enabled is not None:
        sets.append("enabled=?")
        params.append(1 if bool(enabled) else 0)

    if channel_id is not None:
        sets.append("channel_id=?")
        params.append(int(channel_id))

    if not sets:
        return

    with get_conn() as conn:
        # s'assure que la ligne existe (channel_id NOT NULL)
        conn.execute(
            """
            INSERT OR IGNORE INTO welcome_config(guild_id, enabled, channel_id)
            VALUES (?, 0, 0)
            """,
            (guild_id,),
        )
        conn.execute(
            f"UPDATE welcome_config SET {', '.join(sets)} WHERE guild_id=?",
            (*params, guild_id),
        )


def wm_set_enabled(guild_id: int, enabled: bool) -> None:
    """Active/désactive le système de message de bienvenue pour une guild."""
    wm_set_config(guild_id, enabled=enabled)


def wm_set_channel_id(guild_id: int, channel_id: int) -> None:
    """Définit le salon cible (channel_id) où envoyer les messages de bienvenue."""
    wm_set_config(guild_id, channel_id=channel_id)


def wm_is_enabled(guild_id: int) -> bool:
    """Indique si les messages de bienvenue sont activés pour une guild."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT enabled FROM welcome_config WHERE guild_id=?",
            (guild_id,),
        ).fetchone()
    return bool(row[0]) if row else False


def wm_get_channel_id(guild_id: int) -> int:
    """Retourne le channel_id configuré pour les messages de bienvenue (0 si non configuré)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT channel_id FROM welcome_config WHERE guild_id=?",
            (guild_id,),
        ).fetchone()
    return int(row[0]) if row else 0


def wm_delete_config(guild_id: int) -> None:
    """Optionnel: reset complet de la config de bienvenue pour une guild."""
    with get_conn() as conn:
        conn.execute("DELETE FROM welcome_config WHERE guild_id=?", (guild_id,))


# ------------ Welcome message history (anti-répétition) -----------

def wm_get_recent_message_keys(guild_id: int, *, limit: int = 10) -> list[str]:
    """Retourne les dernières clés de messages tirées, du plus récent au plus ancien."""
    limit = max(0, int(limit))
    if limit == 0:
        return []

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT message_key
            FROM welcome_message_history
            WHERE guild_id=?
            ORDER BY used_at DESC, id DESC
            LIMIT ?
            """,
            (guild_id, limit),
        ).fetchall()

    return [str(r[0]) for r in rows if r and r[0] is not None]


def wm_record_welcome_message(
    guild_id: int,
    message_key: str,
    *,
    used_at: int | None = None,
    keep: int = 10,
) -> None:
    """Enregistre une clé de message tirée et conserve uniquement les `keep` plus récentes."""
    if not message_key:
        return

    ts = int(used_at if used_at is not None else time.time())
    keep = max(0, int(keep))

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO welcome_message_history(guild_id, message_key, used_at)
            VALUES (?, ?, ?)
            """,
            (guild_id, str(message_key), ts),
        )

        if keep == 0:
            conn.execute(
                "DELETE FROM welcome_message_history WHERE guild_id=?",
                (guild_id,),
            )
            return

        # Supprime tout sauf les `keep` plus récentes pour cette guild
        conn.execute(
            """
            DELETE FROM welcome_message_history
            WHERE id IN (
              SELECT id FROM welcome_message_history
              WHERE guild_id=?
              ORDER BY used_at DESC, id DESC
              LIMIT -1 OFFSET ?
            )
            """,
            (guild_id, keep),
        )
