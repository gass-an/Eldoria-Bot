from __future__ import annotations

from eldoria.db import schema as mod
from tests._fakes import Conn, ConnCM


def test__table_columns_returns_set_of_column_names():
    # rows format = (cid, name, type, notnull, dflt_value, pk) typiquement
    conn = Conn(pragma_rows=[(0, "guild_id", "INTEGER", 1, None, 1), (1, "enabled", "INTEGER", 1, 0, 0)])
    cols = mod._table_columns(conn, "xp_config")
    assert cols == {"guild_id", "enabled"}
    assert conn.executed == ["PRAGMA table_info(xp_config);"]


def test_migrate_db_no_xp_config_table_noop(monkeypatch):
    """
    Si PRAGMA table_info renvoie [], cols == empty => aucune migration (ni ALTER ni UPDATE).
    """
    conn = Conn(pragma_rows=[])
    cm = ConnCM(conn)

    monkeypatch.setattr(mod, "get_conn", lambda: cm, raising=True)

    mod.migrate_db()

    assert cm.entered == 1
    assert cm.exited == 1
    # seulement les inspections de schéma
    assert conn.executed == [
        "PRAGMA table_info(xp_config);",
        "PRAGMA table_info(tickets);",
    ]


def test_migrate_db_adds_missing_voice_columns_and_updates(monkeypatch):
    """
    Si la table existe (cols non vide) et qu'il manque certaines colonnes vocal,
    on doit faire les ALTER correspondants + les UPDATE COALESCE.
    """
    # xp_config existe mais sans colonnes vocal
    conn = Conn(
        pragma_rows=[
            (0, "guild_id", "INTEGER", 1, None, 1),
            (1, "enabled", "INTEGER", 1, 0, 0),
            (2, "points_per_message", "INTEGER", 1, 8, 0),
        ]
    )
    cm = ConnCM(conn)
    monkeypatch.setattr(mod, "get_conn", lambda: cm, raising=True)

    mod.migrate_db()

    sql = "\n".join(conn.executed)

    # PRAGMA
    assert "PRAGMA table_info(xp_config);" in sql

    # ALTER pour toutes les colonnes vocal demandées
    assert "ALTER TABLE xp_config ADD COLUMN voice_enabled INTEGER NOT NULL DEFAULT 1;" in sql
    assert "ALTER TABLE xp_config ADD COLUMN voice_xp_per_interval INTEGER NOT NULL DEFAULT 1;" in sql
    assert "ALTER TABLE xp_config ADD COLUMN voice_interval_seconds INTEGER NOT NULL DEFAULT 180;" in sql
    assert "ALTER TABLE xp_config ADD COLUMN voice_daily_cap_xp INTEGER NOT NULL DEFAULT 100;" in sql
    assert "ALTER TABLE xp_config ADD COLUMN voice_levelup_channel_id INTEGER NOT NULL DEFAULT 0;" in sql

    # UPDATE COALESCE toujours exécutés
    assert "UPDATE xp_config SET voice_enabled=COALESCE(voice_enabled, 1);" in sql
    assert "UPDATE xp_config SET voice_xp_per_interval=COALESCE(voice_xp_per_interval, 1);" in sql
    assert "UPDATE xp_config SET voice_interval_seconds=COALESCE(voice_interval_seconds, 180);" in sql
    assert "UPDATE xp_config SET voice_daily_cap_xp=COALESCE(voice_daily_cap_xp, 100);" in sql
    assert "UPDATE xp_config SET voice_levelup_channel_id=COALESCE(voice_levelup_channel_id, 0);" in sql


def test_migrate_db_when_voice_columns_already_exist_no_alter_but_updates(monkeypatch):
    """
    Si toutes les colonnes vocal existent déjà, pas d'ALTER mais on fait quand même les UPDATE.
    """
    conn = Conn(
        pragma_rows=[
            (0, "guild_id", "INTEGER", 1, None, 1),
            (1, "voice_enabled", "INTEGER", 1, 1, 0),
            (2, "voice_xp_per_interval", "INTEGER", 1, 1, 0),
            (3, "voice_interval_seconds", "INTEGER", 1, 180, 0),
            (4, "voice_daily_cap_xp", "INTEGER", 1, 100, 0),
            (5, "voice_levelup_channel_id", "INTEGER", 1, 0, 0),
        ]
    )
    cm = ConnCM(conn)
    monkeypatch.setattr(mod, "get_conn", lambda: cm, raising=True)

    mod.migrate_db()

    # aucun ALTER sur xp_config (le fake réutilise ces colonnes pour l'inspection de tickets)
    assert not any(
        s.strip().upper().startswith("ALTER TABLE XP_CONFIG") for s in conn.executed
    )

    # updates présents
    assert any("UPDATE xp_config SET voice_enabled=COALESCE" in s for s in conn.executed)
    assert any("UPDATE xp_config SET voice_levelup_channel_id=COALESCE" in s for s in conn.executed)


def test_init_db_executes_schema_script_and_calls_migrate(monkeypatch):
    conn = Conn()
    cm = ConnCM(conn)

    monkeypatch.setattr(mod, "get_conn", lambda: cm, raising=True)

    migrate_calls = {"n": 0}

    def fake_migrate():
        migrate_calls["n"] += 1

    monkeypatch.setattr(mod, "migrate_db", fake_migrate, raising=True)

    mod.init_db()

    assert cm.entered == 1
    assert cm.exited == 1

    # executescript appelé une fois avec le gros script
    assert len(conn.scripts) == 1
    assert "CREATE TABLE IF NOT EXISTS xp_config" in conn.scripts[0]
    assert "CREATE TABLE IF NOT EXISTS duels" in conn.scripts[0]
    assert "CREATE TABLE IF NOT EXISTS ticket_sequences" in conn.scripts[0]
    assert "ticket_number   INTEGER NOT NULL" in conn.scripts[0]

    # migrate appelé après
    assert migrate_calls["n"] == 1


def test_migrate_db_adds_ticket_number_to_existing_table(monkeypatch):
    class TableAwareConn(Conn):
        def execute(self, sql: str):
            self.executed.append(sql)
            if "table_info(xp_config)" in sql:
                from tests._fakes import Cursor

                return Cursor(rows=[])
            if "table_info(tickets)" in sql:
                from tests._fakes import Cursor

                return Cursor(rows=[(0, "id", "INTEGER", 0, None, 1)])
            from tests._fakes import Cursor

            return Cursor(row=(1,))

    conn = TableAwareConn()
    monkeypatch.setattr(mod, "get_conn", lambda: ConnCM(conn), raising=True)

    mod.migrate_db()

    sql = "\n".join(conn.executed)
    assert "ALTER TABLE tickets ADD COLUMN ticket_number INTEGER;" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_guild_number" in sql
