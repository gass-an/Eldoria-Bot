from .connection import get_conn


def _table_columns(conn, table: str) -> set[str]:
    """Retourne la liste des colonnes d'une table (SQLite)."""
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return {str(r[1]) for r in rows}


def migrate_db():
    """Migration douce (sans perte) pour les anciennes DB.

    Important : `CREATE TABLE IF NOT EXISTS` ne met *pas* à jour le schéma
    d'une table existante. Donc si ton bot tourne déjà, il faut ajouter les
    colonnes manquantes via `ALTER TABLE`.
    """

    with get_conn() as conn:
        # --- xp_config : ajout des colonnes vocal si elles n'existent pas ---
        cols = _table_columns(conn, "xp_config")
        if cols:
            # (name, sql_type, default_value)
            wanted = [
                ("voice_enabled", "INTEGER", "1"),
                ("voice_xp_per_interval", "INTEGER", "1"),
                ("voice_interval_seconds", "INTEGER", "180"),
                ("voice_daily_cap_xp", "INTEGER", "100"),
                ("voice_levelup_channel_id", "INTEGER", "0"),
            ]

            for name, sql_type, dflt in wanted:
                if name not in cols:
                    # NOT NULL + DEFAULT non-null est accepté par SQLite lors d'un ADD COLUMN
                    conn.execute(
                        f"ALTER TABLE xp_config ADD COLUMN {name} {sql_type} NOT NULL DEFAULT {dflt};"
                    )

            # Sécurise les vieilles lignes où SQLite pourrait laisser NULL
            conn.execute("UPDATE xp_config SET voice_enabled=COALESCE(voice_enabled, 1);")
            conn.execute("UPDATE xp_config SET voice_xp_per_interval=COALESCE(voice_xp_per_interval, 1);")
            conn.execute("UPDATE xp_config SET voice_interval_seconds=COALESCE(voice_interval_seconds, 180);")
            conn.execute("UPDATE xp_config SET voice_daily_cap_xp=COALESCE(voice_daily_cap_xp, 100);")
            conn.execute("UPDATE xp_config SET voice_levelup_channel_id=COALESCE(voice_levelup_channel_id, 0);")

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

        -- -------------------- Welcome message system --------------------          
        CREATE TABLE IF NOT EXISTS welcome_config (
			guild_id       	INTEGER NOT NULL PRIMARY KEY,
			enabled      	INTEGER NOT NULL DEFAULT 0,
			channel_id		INTEGER NOT NULL
        );

        -- Historique des messages de bienvenue tirés (anti-répétition)
        -- On stocke la clé du JSON (ex: w01) avec un timestamp Unix.
        CREATE TABLE IF NOT EXISTS welcome_message_history (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			guild_id   INTEGER NOT NULL,
			message_key TEXT   NOT NULL,
			used_at    INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_welcome_message_history_guild_time
          	ON welcome_message_history(guild_id, used_at);

        -- -------------------- XP system --------------------
        CREATE TABLE IF NOT EXISTS xp_config (
			guild_id           INTEGER NOT NULL PRIMARY KEY,
			enabled            INTEGER NOT NULL DEFAULT 0,
			points_per_message INTEGER NOT NULL DEFAULT 8,
			cooldown_seconds   INTEGER NOT NULL DEFAULT 90,
			bonus_percent      INTEGER NOT NULL DEFAULT 20,
			karuta_k_small_percent INTEGER NOT NULL DEFAULT 30,

			-- ---- Vocal XP ----
			voice_enabled           INTEGER NOT NULL DEFAULT 1,
			voice_xp_per_interval   INTEGER NOT NULL DEFAULT 1,
			voice_interval_seconds  INTEGER NOT NULL DEFAULT 180,
			voice_daily_cap_xp      INTEGER NOT NULL DEFAULT 100,

			-- Salon (texte) où annoncer les passages de niveaux dus au vocal.
			-- 0 = auto (system_channel / #general si trouvable), sinon ID du salon.
			voice_levelup_channel_id INTEGER NOT NULL DEFAULT 0
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

        -- Progress vocal (cap journalier + buffer)
        CREATE TABLE IF NOT EXISTS xp_voice_progress (
			guild_id        INTEGER NOT NULL,
			user_id         INTEGER NOT NULL,
			day_key         TEXT    NOT NULL DEFAULT '',
			last_tick_ts    INTEGER NOT NULL DEFAULT 0,
			buffer_seconds  INTEGER NOT NULL DEFAULT 0,
			bonus_cents     INTEGER NOT NULL DEFAULT 0,
			xp_today        INTEGER NOT NULL DEFAULT 0,
			PRIMARY KEY (guild_id, user_id)
        );
                           
		-- -------------------- Duel system --------------------
        CREATE TABLE IF NOT EXISTS duels (
            duel_id 		INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id		INTEGER NOT NULL,
            channel_id		INTEGER NOT NULL,
            message_id		INTEGER,
            player_a_id		INTEGER NOT NULL,
            player_b_id		INTEGER NOT NULL,
            game_type		TEXT,
            stake_xp		INTEGER,
			status			TEXT NOT NULL CHECK(status IN ('CONFIG','INVITED','ACTIVE','FINISHED','CANCELLED','EXPIRED')),
			created_at		INTEGER NOT NULL,
			expires_at		INTEGER,
            finished_at		INTEGER,
			payload         TEXT          
        );

        -- Accélère la task d'expiration (status + expires_at)
        CREATE INDEX IF NOT EXISTS idx_duels_status_expires
            ON duels(status, expires_at);

        -- Accélère les lookups via message (UI)
        CREATE INDEX IF NOT EXISTS idx_duels_message
            ON duels(guild_id, channel_id, message_id);
        """)

    # Migration douce pour DB déjà en prod (ajout de colonnes/tables manquantes)
    migrate_db()

    # NB: les valeurs par défaut pour les niveaux/config XP
    # sont initialisées côté bot (au démarrage) car on a besoin
    # de connaître les guilds actives.