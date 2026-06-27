"""Repo DB pour la configuration et les numéros du système de ticketing.

Stocke l'état (enabled) ainsi que les IDs de category et du channel "ouvert".
"""

from __future__ import annotations

from typing import Any

from eldoria.db.connection import get_conn


def tk_ensure_defaults(
    guild_id: int, *, enabled: bool = False, category_id: int = 0, open_channel_id: int = 0
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO ticketing_config(guild_id, enabled, category_id, open_channel_id)
            VALUES (?, ?, ?, ?)
            """,
            (guild_id, 1 if enabled else 0, int(category_id), int(open_channel_id)),
        )


def tk_get_config(guild_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT enabled, category_id, open_channel_id FROM ticketing_config WHERE guild_id=?",
            (guild_id,),
        ).fetchone()

    if not row:
        tk_ensure_defaults(guild_id, enabled=False, category_id=0, open_channel_id=0)
        return {"enabled": False, "category_id": 0, "open_channel_id": 0}

    return {"enabled": bool(row[0]), "category_id": int(row[1]), "open_channel_id": int(row[2])}


def tk_set_config(
    guild_id: int,
    *,
    enabled: bool | None = None,
    category_id: int | None = None,
    open_channel_id: int | None = None,
) -> None:
    sets: list[str] = []
    params: list[int] = []

    if enabled is not None:
        sets.append("enabled=?")
        params.append(1 if bool(enabled) else 0)

    if category_id is not None:
        sets.append("category_id=?")
        params.append(int(category_id))

    if open_channel_id is not None:
        sets.append("open_channel_id=?")
        params.append(int(open_channel_id))

    if not sets:
        return

    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO ticketing_config(guild_id, enabled, category_id, open_channel_id)
            VALUES (?, 0, 0, 0)
            """,
            (guild_id,),
        )
        conn.execute(
            f"UPDATE ticketing_config SET {', '.join(sets)} WHERE guild_id=?", (*params, guild_id)
        )


def tk_set_enabled(guild_id: int, enabled: bool) -> None:
    tk_set_config(guild_id, enabled=enabled)


def tk_set_category_id(guild_id: int, category_id: int) -> None:
    tk_set_config(guild_id, category_id=category_id)


def tk_set_open_channel_id(guild_id: int, open_channel_id: int) -> None:
    tk_set_config(guild_id, open_channel_id=open_channel_id)


def tk_is_enabled(guild_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT enabled FROM ticketing_config WHERE guild_id=?", (guild_id,)
        ).fetchone()
    return bool(row[0]) if row else False


def tk_get_category_id(guild_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT category_id FROM ticketing_config WHERE guild_id=?", (guild_id,)
        ).fetchone()
    return int(row[0]) if row else 0


def tk_get_open_channel_id(guild_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT open_channel_id FROM ticketing_config WHERE guild_id=?", (guild_id,)
        ).fetchone()
    return int(row[0]) if row else 0


def tk_delete_config(guild_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM ticketing_config WHERE guild_id=?", (guild_id,))


def tk_allocate_ticket_number(guild_id: int) -> int:
    """Réserve et retourne atomiquement le prochain numéro du serveur."""
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO ticket_sequences(guild_id, next_number)
            VALUES (?, 2)
            ON CONFLICT(guild_id) DO UPDATE
            SET next_number = ticket_sequences.next_number + 1
            RETURNING next_number - 1
            """,
            (guild_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError(f"Impossible d'allouer un numéro de ticket au serveur {guild_id}")
    return int(row[0])


def tk_record_ticket(
    guild_id: int,
    ticket_number: int,
    channel_id: int,
    owner_id: int,
    created_at: int,
) -> None:
    """Enregistre l'association entre un numéro de ticket et son salon Discord."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tickets(
                guild_id, ticket_number, channel_id, owner_id, status, created_at
            )
            VALUES (?, ?, ?, ?, 'OPEN', ?)
            """,
            (guild_id, ticket_number, channel_id, owner_id, created_at),
        )
