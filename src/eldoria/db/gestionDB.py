import os
import sqlite3
import threading
from contextlib import contextmanager

DB_PATH = "./data/eldoria.db"
_DB_LOCK = threading.RLock()

@contextmanager
def get_conn():
    with _DB_LOCK:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS reaction_roles (
          guild_id    INTEGER NOT NULL,
          message_id  INTEGER NOT NULL,
          emoji       TEXT    NOT NULL,
          role_id     INTEGER NOT NULL,
          PRIMARY KEY (guild_id, message_id, emoji)
        );

        CREATE TABLE IF NOT EXISTS secret_roles (
          guild_id    INTEGER NOT NULL,
          channel_id  INTEGER NOT NULL,
          phrase      TEXT    NOT NULL,
          role_id     INTEGER NOT NULL,
          PRIMARY KEY (guild_id, channel_id, phrase)
        );

        CREATE TABLE IF NOT EXISTS temp_voice_parents (
          guild_id           INTEGER NOT NULL,
          parent_channel_id  INTEGER NOT NULL,
          user_limit         INTEGER NOT NULL,
          PRIMARY KEY (guild_id, parent_channel_id)
        );

        CREATE TABLE IF NOT EXISTS temp_voice_active (
          guild_id           INTEGER NOT NULL,
          parent_channel_id  INTEGER NOT NULL,
          channel_id         INTEGER NOT NULL,
          PRIMARY KEY (guild_id, parent_channel_id, channel_id)
        );

        -- -------------------- XP system --------------------
        CREATE TABLE IF NOT EXISTS xp_config (
          guild_id           INTEGER NOT NULL PRIMARY KEY,
          enabled            INTEGER NOT NULL DEFAULT 0,
          points_per_message INTEGER NOT NULL DEFAULT 8,
          cooldown_seconds   INTEGER NOT NULL DEFAULT 90,
          bonus_percent      INTEGER NOT NULL DEFAULT 20
        );

        CREATE TABLE IF NOT EXISTS xp_levels (
        guild_id      INTEGER NOT NULL,
        level         INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5),
        xp_required   INTEGER NOT NULL,
        role_id       INTEGER,              -- NULL tant que le rôle n'est pas créé/lié
        PRIMARY KEY (guild_id, level)
        );

        CREATE TABLE IF NOT EXISTS xp_members (
          guild_id        INTEGER NOT NULL,
          user_id         INTEGER NOT NULL,
          xp              INTEGER NOT NULL DEFAULT 0,
          last_xp_ts      INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY (guild_id, user_id)
        );
        """)

    # NB: les valeurs par défaut pour les niveaux/config XP
    # sont initialisées côté bot (au démarrage) car on a besoin
    # de connaître les guilds actives.
# ----------Helpeurs save replace database

def backup_to_file(dst_path: str):
    """
    Exporte une copie cohérente de la DB vers dst_path.
    Le verrou empêche toute écriture/lecture concurrente via get_conn().
    """
    with _DB_LOCK:
        # checkpoint WAL au cas où
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("PRAGMA wal_checkpoint(FULL);")
        except sqlite3.DatabaseError:
            pass

        bck = sqlite3.connect(dst_path)
        try:
            conn.backup(bck)
        finally:
            bck.close()
            conn.close()

def replace_db_file(new_db_path: str):
    """
    Remplace DB_PATH par new_db_path de façon atomique.
    Le verrou garantit que personne n'utilise la DB pendant le swap.
    """
    with _DB_LOCK:
        # petite vérif que c'est bien une sqlite
        test = sqlite3.connect(new_db_path)
        try:
            test.execute("PRAGMA schema_version;").fetchone()
        finally:
            test.close()

        # Remplacement atomique
        os.replace(new_db_path, DB_PATH)


# ---------- XP system ----------

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


# ---------- Reaction roles ----------
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

# ---------- Secret roles ----------
def sr_upsert(guild_id: int, channel_id: int, phrase: str, role_id: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO secret_roles(guild_id, channel_id, phrase, role_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, channel_id, phrase) DO UPDATE SET role_id=excluded.role_id
        """, (guild_id, channel_id, phrase, role_id))

def sr_delete(guild_id: int, channel_id: int, phrase: str):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM secret_roles
            WHERE guild_id=? AND channel_id=? AND phrase=?
        """, (guild_id, channel_id, phrase))

def sr_match(guild_id: int, channel_id: int, phrase: str):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT role_id FROM secret_roles
            WHERE guild_id=? AND channel_id=? AND phrase=?
        """, (guild_id, channel_id, phrase)).fetchone()
    return row[0] if row else None

def sr_list_messages(guild_id: int, channel_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT phrase
            FROM secret_roles
            WHERE guild_id=? AND channel_id=?
            ORDER BY phrase
        """, (guild_id, channel_id)).fetchall()
    return [r[0] for r in rows]

def sr_list_by_guild_grouped(guild_id: int):
    """
    Retourne une liste de tuples:
      [(channel_id, {phrase: role_id}), ...]
    format compatible avec list(secret_roles_guild.items()) côté JSON.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT channel_id, phrase, role_id
            FROM secret_roles
            WHERE guild_id=?
            ORDER BY channel_id
        """, (guild_id,)).fetchall()

    grouped = {}
    for channel_id, phrase, role_id in rows:
        grouped.setdefault(str(channel_id), {})[phrase] = role_id

    return list(grouped.items())


# ---------- Temp voice ----------
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
