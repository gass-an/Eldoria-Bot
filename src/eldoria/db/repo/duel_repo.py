"""Module de gestion des duels, contenant les fonctions nécessaires pour créer, récupérer, mettre à jour et nettoyer les duels dans la base de données."""

from sqlite3 import Connection, Cursor, Row
from typing import Any

from eldoria.db.connection import get_conn


def _execute_in_conn(
    conn: Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> Cursor:
    """Exécute une requête SQL avec les paramètres spécifiés dans une connexion donnée, et retourne le curseur résultant."""
    return conn.execute(sql, params)


def create_duel(
    guild_id: int,
    channel_id: int,
    player_a_id: int,
    player_b_id: int,
    created_at: int,
    expires_at: int
) -> int:
    """Retourne l'identifiant unique du duel nouvellement créé."""
    with get_conn() as conn:
        cursor = _execute_in_conn(conn, """
            INSERT INTO duels(
                guild_id,
                channel_id,
                message_id,
                player_a_id,
                player_b_id,
                game_type,
                stake_xp,
                status,
                created_at,
                expires_at,
                finished_at,
                payload
            )
            VALUES (?, ?, NULL, ?, ?, NULL, NULL, 'CONFIG', ?, ?, NULL, NULL)
        """, (guild_id, channel_id, player_a_id, player_b_id, created_at, expires_at))
        
        return cursor.lastrowid


def get_duel_by_id(duel_id: int, *, conn: Connection | None = None) -> Row:
    """Retourne les informations d'un duel à partir de son identifiant unique."""
    if conn is None:
        with get_conn() as conn2:
            return get_duel_by_id(duel_id, conn=conn2)
    row = _execute_in_conn(conn, """
            SELECT *
            FROM duels
            WHERE duel_id = ?
        """, (duel_id,)).fetchone()
    return row


def get_duel_by_message_id(guild_id: int, channel_id: int, message_id: int, *, conn: Connection | None = None) -> Row:
    """Retourne les informations d'un duel à partir de l'identifiant du message associé dans Discord."""
    if conn is None:
        with get_conn() as conn2:
            return get_duel_by_message_id(guild_id, channel_id, message_id, conn=conn2)
    row = _execute_in_conn(conn, """
            SELECT *
            FROM duels
            WHERE guild_id = ?
              AND channel_id = ?
              AND message_id = ?
            LIMIT 1
        """, (guild_id, channel_id, message_id)).fetchone()
    return row


def get_active_duel_for_user(guild_id: int, user_id: int, *, conn: Connection | None = None) -> Row:
    """Retourne les informations du duel actif (status INVITED ou ACTIVE) impliquant un utilisateur donné dans un serveur, ou None s'il n'y en a pas."""
    if conn is None:
        with get_conn() as conn2:
            return get_active_duel_for_user(guild_id, user_id, conn=conn2)
    row = _execute_in_conn(conn, """
            SELECT *
            FROM duels
            WHERE guild_id = ?
              AND (player_a_id = ? OR player_b_id = ?)
              AND status IN ('INVITED','ACTIVE')
            ORDER BY created_at DESC
            LIMIT 1
        """, (guild_id, user_id, user_id)).fetchone()
    return row


def update_duel_if_status(
    duel_id: int,
    required_status: str,
    *,
    message_id: int | None = None,
    game_type: str | None = None,
    stake_xp: int | None = None,
    expires_at: int | None = None,
    finished_at: int | None = None,
    payload: str | None = None,
    conn: Connection | None = None,
) -> bool:
    """Met à jour les informations d'un duel uniquement si son status correspond à celui requis, et retourne True si la mise à jour a été effectuée, ou False sinon."""
    if all(v is None for v in (message_id, game_type, stake_xp, expires_at, finished_at, payload)):
        return False

    if conn is None:
        with get_conn() as conn2:
            return update_duel_if_status(
                duel_id,
                required_status,
                message_id=message_id,
                game_type=game_type,
                stake_xp=stake_xp,
                expires_at=expires_at,
                finished_at=finished_at,
                payload=payload,
                conn=conn2,
            )

    _execute_in_conn(conn, """
            UPDATE duels
            SET
                message_id  = COALESCE(?, message_id),
                game_type   = COALESCE(?, game_type),
                stake_xp    = COALESCE(?, stake_xp),
                expires_at  = COALESCE(?, expires_at),
                finished_at = COALESCE(?, finished_at),
                payload     = COALESCE(?, payload)
            WHERE duel_id=?
            AND status=?
        """, (message_id, game_type, stake_xp, expires_at, finished_at, payload, duel_id, required_status))

    changes = _execute_in_conn(conn, "SELECT changes()").fetchone()[0]
    return changes == 1


def transition_status(
    duel_id: int,
    from_status: str,
    to_status: str,
    expires_at: int | None,
    *,
    conn: Connection | None = None,
) -> bool:
    """Fait la transition d'un duel d'un status à un autre uniquement si le status actuel correspond à celui attendu, et retourne True si la transition a été effectuée, ou False sinon."""
    if conn is None:
        with get_conn() as conn2:
            return transition_status(duel_id, from_status, to_status, expires_at, conn=conn2)

    _execute_in_conn(conn, """
            UPDATE duels
            SET 
                status=?,
                expires_at=?
            WHERE duel_id =?
            AND status =?
        """, (to_status, expires_at, duel_id, from_status))

    changes = _execute_in_conn(conn, "SELECT changes()").fetchone()[0]
    return changes == 1

def update_payload_if_unchanged(
    duel_id: int,
    old_payload_json: str | None,
    new_payload_json: str,
    *,
    conn: Connection | None = None,
) -> bool:
    """Met à jour le champ payload d'un duel uniquement si sa valeur actuelle correspond à l'ancienne valeur attendue, et retourne True si la mise à jour a été effectuée, ou False sinon."""
    if conn is None:
        with get_conn() as conn2:
            return update_payload_if_unchanged(duel_id, old_payload_json, new_payload_json, conn=conn2)

    _execute_in_conn(conn, """
            UPDATE duels 
            SET payload=? 
            WHERE duel_id=? 
            AND status='ACTIVE' 
            AND COALESCE(payload, '') = COALESCE(?, '')
        """, (new_payload_json, duel_id, old_payload_json))

    changes = _execute_in_conn(conn, "SELECT changes()").fetchone()[0]
    return changes == 1


def list_expired_duels(now_ts: int, *, conn: Connection | None = None) -> list[Row]:
    """Retourne la liste des duels dont la date d'expiration est dépassée et qui ne sont pas encore dans un status final (FINISHED, CANCELLED, EXPIRED)."""
    if conn is None:
        with get_conn() as conn2:
            return list_expired_duels(now_ts, conn=conn2)
    rows = _execute_in_conn(conn, """
            SELECT *
            FROM duels
            WHERE status IN ('CONFIG','INVITED','ACTIVE')
              AND expires_at IS NOT NULL
              AND expires_at <= ?
            ORDER BY expires_at ASC
        """, (now_ts,)).fetchall()
    return rows


def cleanup_duels(cutoff_short: int, cutoff_finished: int, *, conn: Connection | None = None) -> None:
    """Supprime les duels dont la date de fin est dépassée depuis longtemps."""
    if conn is None:
        with get_conn() as conn2:
            return cleanup_duels(cutoff_short, cutoff_finished, conn=conn2)
    _execute_in_conn(conn, """
        DELETE FROM duels
        WHERE finished_at IS NOT NULL
          AND (
                (status IN ('EXPIRED', 'CANCELLED') AND finished_at <= ?)
             OR (status = 'FINISHED'      AND finished_at <= ?)
          )
        """, (
            cutoff_short,
            cutoff_finished,
        )
    )
    return None