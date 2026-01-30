from sqlite3 import Connection

from ..connection import get_conn
from ...defaults import XP_CONFIG_DEFAULTS, XP_LEVELS_DEFAULTS

# ------------ XP system -----------
def xp_ensure_defaults(guild_id: int, default_levels: dict[int, int] | None = None):
    """Crée la config et les niveaux par défaut si absents.

    ⚠️ Aucune migration automatique n'est effectuée ici.
    Si tu supprimes la DB, elle sera recréée au lancement avec le schéma + defaults actuels.
    """
    if default_levels is None:
        default_levels = dict(XP_LEVELS_DEFAULTS)

    with get_conn() as conn:
        # Crée une ligne de config si absente.
        # On insère explicitement les valeurs de defaults.py pour ne pas dépendre des DEFAULT SQL.
        conn.execute(
            """
            INSERT OR IGNORE INTO xp_config(
              guild_id,
              enabled,
              points_per_message,
              cooldown_seconds,
              bonus_percent,
              karuta_k_small_percent,

              voice_enabled,
              voice_xp_per_interval,
              voice_interval_seconds,
              voice_daily_cap_xp,
              voice_levelup_channel_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                1 if bool(XP_CONFIG_DEFAULTS["enabled"]) else 0,
                int(XP_CONFIG_DEFAULTS["points_per_message"]),
                int(XP_CONFIG_DEFAULTS["cooldown_seconds"]),
                int(XP_CONFIG_DEFAULTS["bonus_percent"]),
                int(XP_CONFIG_DEFAULTS["karuta_k_small_percent"]),

                1 if bool(XP_CONFIG_DEFAULTS.get("voice_enabled", True)) else 0,
                int(XP_CONFIG_DEFAULTS.get("voice_xp_per_interval", 1)),
                int(XP_CONFIG_DEFAULTS.get("voice_interval_seconds", 180)),
                int(XP_CONFIG_DEFAULTS.get("voice_daily_cap_xp", 100)),
                int(XP_CONFIG_DEFAULTS.get("voice_levelup_channel_id", 0)),
            ),
        )

        # Crée les niveaux si absents
        for lvl, xp_req in default_levels.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO xp_levels(guild_id, level, xp_required, role_id)
                VALUES (?, ?, ?, NULL)
                """,
                (guild_id, int(lvl), int(xp_req)),
            )


def xp_get_config(guild_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT enabled, points_per_message, cooldown_seconds, bonus_percent, karuta_k_small_percent,
                   voice_enabled, voice_xp_per_interval, voice_interval_seconds, voice_daily_cap_xp,
                   voice_levelup_channel_id
            FROM xp_config WHERE guild_id=?
            """,
            (guild_id,),
        ).fetchone()
    if not row:
        # Si la ligne n'existe pas, on la crée pour bénéficier des DEFAULT du schéma,
        # mais on renvoie aussi des valeurs cohérentes côté code.
        with get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO xp_config(
                  guild_id,
                  enabled,
                  points_per_message,
                  cooldown_seconds,
                  bonus_percent,
              karuta_k_small_percent,
              voice_enabled,
              voice_xp_per_interval,
              voice_interval_seconds,
              voice_daily_cap_xp,
              voice_levelup_channel_id
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    1 if bool(XP_CONFIG_DEFAULTS["enabled"]) else 0,
                    int(XP_CONFIG_DEFAULTS["points_per_message"]),
                    int(XP_CONFIG_DEFAULTS["cooldown_seconds"]),
                    int(XP_CONFIG_DEFAULTS["bonus_percent"]),
                int(XP_CONFIG_DEFAULTS["karuta_k_small_percent"]),
                1 if bool(XP_CONFIG_DEFAULTS.get("voice_enabled", True)) else 0,
                int(XP_CONFIG_DEFAULTS.get("voice_xp_per_interval", 1)),
                int(XP_CONFIG_DEFAULTS.get("voice_interval_seconds", 180)),
                int(XP_CONFIG_DEFAULTS.get("voice_daily_cap_xp", 100)),
                int(XP_CONFIG_DEFAULTS.get("voice_levelup_channel_id", 0)),
                ),
            )
        return dict(XP_CONFIG_DEFAULTS)
    return {
        "enabled": bool(row[0]),
        "points_per_message": int(row[1]),
        "cooldown_seconds": int(row[2]),
        "bonus_percent": int(row[3]),
        "karuta_k_small_percent": int(row[4]),

        "voice_enabled": bool(row[5]),
        "voice_xp_per_interval": int(row[6]),
        "voice_interval_seconds": int(row[7]),
        "voice_daily_cap_xp": int(row[8]),
        "voice_levelup_channel_id": int(row[9]),
    }


def xp_set_config(
    guild_id: int,
    *,
    enabled: bool | None = None,
    points_per_message: int | None = None,
    cooldown_seconds: int | None = None,
    bonus_percent: int | None = None,
    karuta_k_small_percent: int | None = None,

    voice_enabled: bool | None = None,
    voice_xp_per_interval: int | None = None,
    voice_interval_seconds: int | None = None,
    voice_daily_cap_xp: int | None = None,
    voice_levelup_channel_id: int | None = None,
):
    sets = []
    params = []
    if enabled is not None:
        sets.append("enabled=?")
        params.append(1 if bool(enabled) else 0)
    if points_per_message is not None:
        sets.append("points_per_message=?")
        params.append(int(points_per_message))
    if cooldown_seconds is not None:
        sets.append("cooldown_seconds=?")
        params.append(int(cooldown_seconds))
    if bonus_percent is not None:
        sets.append("bonus_percent=?")
        params.append(int(bonus_percent))
    if karuta_k_small_percent is not None:
        sets.append("karuta_k_small_percent=?")
        params.append(int(karuta_k_small_percent))

    if voice_enabled is not None:
        sets.append("voice_enabled=?")
        params.append(1 if bool(voice_enabled) else 0)
    if voice_xp_per_interval is not None:
        sets.append("voice_xp_per_interval=?")
        params.append(int(voice_xp_per_interval))
    if voice_interval_seconds is not None:
        sets.append("voice_interval_seconds=?")
        params.append(int(voice_interval_seconds))
    if voice_daily_cap_xp is not None:
        sets.append("voice_daily_cap_xp=?")
        params.append(int(voice_daily_cap_xp))
    if voice_levelup_channel_id is not None:
        sets.append("voice_levelup_channel_id=?")
        params.append(int(voice_levelup_channel_id))

    if not sets:
        return

    with get_conn() as conn:
        conn.execute(
                """
                INSERT OR IGNORE INTO xp_config(
                  guild_id,
                  enabled,
                  points_per_message,
                  cooldown_seconds,
                  bonus_percent,
                  karuta_k_small_percent,
                  voice_enabled,
                  voice_xp_per_interval,
                  voice_interval_seconds,
                  voice_daily_cap_xp,
                  voice_levelup_channel_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    1 if bool(XP_CONFIG_DEFAULTS["enabled"]) else 0,
                    int(XP_CONFIG_DEFAULTS["points_per_message"]),
                    int(XP_CONFIG_DEFAULTS["cooldown_seconds"]),
                    int(XP_CONFIG_DEFAULTS["bonus_percent"]),
                    int(XP_CONFIG_DEFAULTS["karuta_k_small_percent"]),
                    1 if bool(XP_CONFIG_DEFAULTS.get("voice_enabled", True)) else 0,
                    int(XP_CONFIG_DEFAULTS.get("voice_xp_per_interval", 1)),
                    int(XP_CONFIG_DEFAULTS.get("voice_interval_seconds", 180)),
                    int(XP_CONFIG_DEFAULTS.get("voice_daily_cap_xp", 100)),
                    int(XP_CONFIG_DEFAULTS.get("voice_levelup_channel_id", 0)),
                ),
            )
        conn.execute(
            f"UPDATE xp_config SET {', '.join(sets)} WHERE guild_id=?",
            (*params, guild_id),
        )


# ------------ Vocal XP progress -----------
def xp_voice_get_progress(guild_id: int, user_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT day_key, last_tick_ts, buffer_seconds, bonus_cents, xp_today
            FROM xp_voice_progress
            WHERE guild_id=? AND user_id=?
            """,
            (guild_id, user_id),
        ).fetchone()
    if not row:
        return {
            "day_key": "",
            "last_tick_ts": 0,
            "buffer_seconds": 0,
            "bonus_cents": 0,
            "xp_today": 0,
        }
    return {
        "day_key": str(row[0] or ""),
        "last_tick_ts": int(row[1]),
        "buffer_seconds": int(row[2]),
        "bonus_cents": int(row[3]),
        "xp_today": int(row[4]),
    }


def xp_voice_upsert_progress(
    guild_id: int,
    user_id: int,
    *,
    day_key: str | None = None,
    last_tick_ts: int | None = None,
    buffer_seconds: int | None = None,
    bonus_cents: int | None = None,
    xp_today: int | None = None,
):
    sets = []
    params: list[object] = []
    if day_key is not None:
        sets.append("day_key=?")
        params.append(str(day_key))
    if last_tick_ts is not None:
        sets.append("last_tick_ts=?")
        params.append(int(last_tick_ts))
    if buffer_seconds is not None:
        sets.append("buffer_seconds=?")
        params.append(int(buffer_seconds))
    if bonus_cents is not None:
        sets.append("bonus_cents=?")
        params.append(int(bonus_cents))
    if xp_today is not None:
        sets.append("xp_today=?")
        params.append(int(xp_today))

    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO xp_voice_progress(guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id),
        )
        if sets:
            conn.execute(
                f"UPDATE xp_voice_progress SET {', '.join(sets)} WHERE guild_id=? AND user_id=?",
                (*params, guild_id, user_id),
            )

def xp_is_enabled(guild_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT enabled FROM xp_config WHERE guild_id=?",
            (guild_id,),
        ).fetchone()
    return bool(row[0]) if row else False


def xp_get_levels(guild_id: int) -> list[tuple[int, int]]:
    """Retourne [(level, xp_required), ...] trié."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT level, xp_required FROM xp_levels WHERE guild_id=? ORDER BY level",
            (guild_id,),
        ).fetchall()
    return [(int(l), int(x)) for (l, x) in rows]

def xp_get_levels_with_roles(guild_id: int) -> list[tuple[int, int, int | None]]:
    """Retourne [(level, xp_required, role_id), ...] trié."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT level, xp_required, role_id FROM xp_levels WHERE guild_id=? ORDER BY level",
            (guild_id,),
        ).fetchall()
    return [(int(l), int(x), (int(r) if r is not None else None)) for (l, x, r) in rows]


def xp_set_level_threshold(guild_id: int, level: int, xp_required: int):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO xp_levels(guild_id, level, xp_required, role_id)
            VALUES (?, ?, ?, NULL)
            ON CONFLICT(guild_id, level) DO UPDATE SET xp_required=excluded.xp_required
            """,
            (guild_id, int(level), int(xp_required)),
        )


def xp_upsert_role_id(guild_id: int, level: int, role_id: int):
    """
    Lie (ou met à jour) le role_id pour un niveau.
    Si la ligne du niveau n'existe pas encore, on la crée avec xp_required=0 (à ajuster ensuite).
    """
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO xp_levels(guild_id, level, xp_required, role_id)
            VALUES (?, ?, 0, ?)
            ON CONFLICT(guild_id, level) DO UPDATE SET role_id=excluded.role_id
            """,
            (guild_id, int(level), int(role_id)),
        )

def xp_get_role_ids(guild_id: int) -> dict[int, int]:
    """Retourne {level: role_id} pour les niveaux qui ont un role_id non NULL."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT level, role_id FROM xp_levels WHERE guild_id=? AND role_id IS NOT NULL",
            (guild_id,),
        ).fetchall()
    return {int(level): int(role_id) for (level, role_id) in rows}


def xp_get_member(guild_id: int, user_id: int, *, conn: Connection | None = None) -> tuple[int, int]:
    """Retourne (xp, last_xp_ts)."""
    if conn is None:
        with get_conn() as conn2:
            return xp_get_member(guild_id, user_id, conn=conn2)
    row = conn.execute(
        "SELECT xp, last_xp_ts FROM xp_members WHERE guild_id=? AND user_id=?",
        (guild_id, user_id),
    ).fetchone()
    return (int(row[0]), int(row[1])) if row else (0, 0)


def xp_set_member(guild_id: int, user_id: int, *, xp: int | None = None, last_xp_ts: int | None = None):
    sets = []
    params = []
    if xp is not None:
        sets.append("xp=?")
        params.append(int(xp))
    if last_xp_ts is not None:
        sets.append("last_xp_ts=?")
        params.append(int(last_xp_ts))
    if not sets:
        return
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO xp_members(guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id),
        )
        conn.execute(
            f"UPDATE xp_members SET {', '.join(sets)} WHERE guild_id=? AND user_id=?",
            (*params, guild_id, user_id),
        )


def xp_add_xp(
    guild_id: int,
    user_id: int,
    delta: int,
    *,
    set_last_xp_ts: int | None = None,
    conn: Connection | None = None,
) -> int:
    """Ajoute delta et retourne le nouvel XP."""
    if conn is None:
        with get_conn() as conn2:
            return xp_add_xp(guild_id, user_id, delta, set_last_xp_ts=set_last_xp_ts, conn=conn2)

    conn.execute(
        "INSERT OR IGNORE INTO xp_members(guild_id, user_id) VALUES (?, ?)",
        (guild_id, user_id),
    )
    conn.execute(
        "UPDATE xp_members SET xp = MAX(xp + ?, 0) WHERE guild_id=? AND user_id=?",
        (int(delta), guild_id, user_id),
    )
    if set_last_xp_ts is not None:
        conn.execute(
            "UPDATE xp_members SET last_xp_ts=? WHERE guild_id=? AND user_id=?",
            (int(set_last_xp_ts), guild_id, user_id),
        )
    row = conn.execute(
        "SELECT xp FROM xp_members WHERE guild_id=? AND user_id=?",
        (guild_id, user_id),
    ).fetchone()
    return int(row[0]) if row else 0


def xp_list_members(guild_id: int, limit: int = 100, offset: int = 0) -> list[tuple[int, int]]:
    """Retourne [(user_id, xp), ...] trié décroissant."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT user_id, xp
            FROM xp_members
            WHERE guild_id=?
            ORDER BY xp DESC, user_id ASC
            LIMIT ? OFFSET ?
            """,
            (guild_id, int(limit), int(offset)),
        ).fetchall()
    return [(int(uid), int(xp)) for (uid, xp) in rows]