from .connection import get_conn

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
          guild_id           INTEGER NOT NULL PRIMARY KEY,
          enabled            INTEGER NOT NULL DEFAULT 0,
          channel_id		 INTEGER NOT NULL
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
          karuta_k_small_percent INTEGER NOT NULL DEFAULT 30
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