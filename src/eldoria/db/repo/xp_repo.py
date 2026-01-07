from ..connection import get_conn

# ------------ XP system -----------
def xp_ensure_defaults(guild_id: int, default_levels: dict[int, int] | None = None):
    """Crée la config et les niveaux par défaut si absents.

    Migration douce:
    - si la guilde est encore sur les anciens *defaults* (5 XP / 60s / 50% et paliers 0/300/600/1000/3000),
      on bascule automatiquement sur les nouveaux defaults.
    - si l'admin a déjà personnalisé la config, on ne touche pas.
    """
    if default_levels is None:
        default_levels = {
            1: 0,
            2: 600,
            3: 1800,
            4: 3800,
            5: 7200,
        }

    old_default_config = (5, 60, 50)
    new_default_config = (8, 90, 20)

    old_default_levels = {
        1: 0,
        2: 300,
        3: 600,
        4: 1000,
        5: 3000,
    }

    with get_conn() as conn:
        # Crée une ligne de config si absente
        conn.execute("""
            INSERT OR IGNORE INTO xp_config(guild_id) VALUES (?)
        """, (guild_id,))

        # Crée les niveaux si absents
        for lvl, xp_req in default_levels.items():
            conn.execute("""
                INSERT OR IGNORE INTO xp_levels(guild_id, level, xp_required, role_id)
                VALUES (?, ?, ?, NULL)
            """, (guild_id, int(lvl), int(xp_req)))

        # --- Migration douce des anciens defaults (si non modifié) ---
        row = conn.execute(
            "SELECT enabled, points_per_message, cooldown_seconds, bonus_percent FROM xp_config WHERE guild_id=?",
            (guild_id,),
        ).fetchone()

        if row and (int(row[1]), int(row[2]), int(row[3])) == old_default_config:
            conn.execute(
                "UPDATE xp_config SET points_per_message=?, cooldown_seconds=?, bonus_percent=? WHERE guild_id=?",
                (*new_default_config, guild_id),
            )

        lvl_rows = conn.execute(
            "SELECT level, xp_required FROM xp_levels WHERE guild_id=? ORDER BY level",
            (guild_id,),
        ).fetchall()

        current_levels = {int(lvl): int(req) for (lvl, req) in lvl_rows}

        # On migre seulement si les 5 niveaux existent ET correspondent aux anciens defaults
        if all(l in current_levels for l in range(1, 6)) and all(
            current_levels.get(l) == old_default_levels[l] for l in old_default_levels
        ):
            for lvl, xp_req in default_levels.items():
                conn.execute(
                    "UPDATE xp_levels SET xp_required=? WHERE guild_id=? AND level=?",
                    (int(xp_req), guild_id, int(lvl)),
                )

def xp_get_config(guild_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT enabled, points_per_message, cooldown_seconds, bonus_percent FROM xp_config WHERE guild_id=?",
            (guild_id,),
        ).fetchone()
    if not row:
        return {
            "enabled": False,
            "points_per_message": 8,
            "cooldown_seconds": 90,
            "bonus_percent": 20,
        }
    return {
        "enabled": bool(row[0]),
        "points_per_message": int(row[1]),
        "cooldown_seconds": int(row[2]),
        "bonus_percent": int(row[3]),
    }


_MISSING = object()


def xp_set_config(
    guild_id: int,
    *,
    enabled: bool | None = None,
    points_per_message: int | None = None,
    cooldown_seconds: int | None = None,
    bonus_percent: int | None = None,
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

    if not sets:
        return

    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO xp_config(guild_id) VALUES (?)", (guild_id,))
        conn.execute(
            f"UPDATE xp_config SET {', '.join(sets)} WHERE guild_id=?",
            (*params, guild_id),
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


def xp_get_member(guild_id: int, user_id: int) -> tuple[int, int]:
    """Retourne (xp, last_xp_ts)."""
    with get_conn() as conn:
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


def xp_add_xp(guild_id: int, user_id: int, delta: int, *, set_last_xp_ts: int | None = None) -> int:
    """Ajoute delta et retourne le nouvel XP."""
    with get_conn() as conn:
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