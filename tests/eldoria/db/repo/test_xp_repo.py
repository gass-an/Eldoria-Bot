import pytest

from eldoria.db.repo import xp_repo as mod

# ----------------------------
# Fakes (à factoriser plus tard)
# ----------------------------

class FakeCursor:
    def __init__(self, *, one=None, all=None, lastrowid=None):
        self._one = one
        self._all = all
        self.lastrowid = lastrowid

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakeConn:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self._next = FakeCursor(one=None, all=[])

    def set_next(self, *, one=None, all=None, lastrowid=None):
        self._next = FakeCursor(one=one, all=all, lastrowid=lastrowid)

    def execute(self, sql: str, params: tuple = ()):
        self.calls.append((sql.strip(), params))
        return self._next


class FakeConnCM:
    def __init__(self, conn: FakeConn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def fconn(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(mod, "get_conn", lambda: FakeConnCM(conn), raising=True)
    return conn


# ----------------------------
# xp_ensure_defaults
# ----------------------------

def test_xp_ensure_defaults_uses_given_levels_and_inserts_config_and_levels(monkeypatch, fconn: FakeConn):
    monkeypatch.setattr(
        mod,
        "XP_CONFIG_DEFAULTS",
        {
            "enabled": False,
            "points_per_message": 8,
            "cooldown_seconds": 90,
            "bonus_percent": 20,
            "karuta_k_small_percent": 30,
            "voice_enabled": True,
            "voice_xp_per_interval": 1,
            "voice_interval_seconds": 180,
            "voice_daily_cap_xp": 100,
            "voice_levelup_channel_id": 0,
        },
        raising=True,
    )

    default_levels = {1: 0, 2: 100, 3: 200}
    mod.xp_ensure_defaults(123, default_levels)

    # 1 call config + N calls levels
    assert len(fconn.calls) == 1 + len(default_levels)

    sql0, params0 = fconn.calls[0]
    assert "INSERT OR IGNORE INTO xp_config" in sql0
    assert params0[0] == 123
    assert params0[1:] == (
        0,  # enabled False
        8,
        90,
        20,
        30,
        1,  # voice_enabled True
        1,
        180,
        100,
        0,
    )

    # levels inserts
    for (lvl, req), (sql, params) in zip(default_levels.items(), fconn.calls[1:], strict=False):
        assert "INSERT OR IGNORE INTO xp_levels" in sql
        assert params == (123, int(lvl), int(req))


def test_xp_ensure_defaults_uses_XP_LEVELS_DEFAULTS_when_none(monkeypatch, fconn: FakeConn):
    monkeypatch.setattr(mod, "XP_LEVELS_DEFAULTS", {1: 0, 2: 50}, raising=True)
    monkeypatch.setattr(
        mod,
        "XP_CONFIG_DEFAULTS",
        {
            "enabled": True,
            "points_per_message": 1,
            "cooldown_seconds": 2,
            "bonus_percent": 3,
            "karuta_k_small_percent": 4,
        },
        raising=True,
    )

    mod.xp_ensure_defaults(1, None)
    # 1 config insert + 2 levels inserts
    assert len(fconn.calls) == 3


# ----------------------------
# xp_get_config
# ----------------------------

def test_xp_get_config_returns_casted_values_when_row_exists(fconn: FakeConn):
    fconn.set_next(one=(1, "8", "90", "20", "30", 0, "2", "180", "100", "0"))
    cfg = mod.xp_get_config(123)

    assert cfg == {
        "enabled": True,
        "points_per_message": 8,
        "cooldown_seconds": 90,
        "bonus_percent": 20,
        "karuta_k_small_percent": 30,
        "voice_enabled": False,
        "voice_xp_per_interval": 2,
        "voice_interval_seconds": 180,
        "voice_daily_cap_xp": 100,
        "voice_levelup_channel_id": 0,
    }

    sql, params = fconn.calls[0]
    assert "FROM xp_config WHERE guild_id=?" in sql
    assert params == (123,)


def test_xp_get_config_when_missing_inserts_defaults_and_returns_XP_CONFIG_DEFAULTS(monkeypatch, fconn: FakeConn):
    # 1st SELECT -> None
    seq = [FakeCursor(one=None), FakeCursor(one=None)]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        fconn.calls.append((sql.strip(), params))
        cur = seq[i["n"]] if i["n"] < len(seq) else FakeCursor(one=None)
        i["n"] += 1
        return cur

    fconn.execute = exec_seq  # type: ignore[assignment]

    defaults = {
        "enabled": False,
        "points_per_message": 9,
        "cooldown_seconds": 10,
        "bonus_percent": 11,
        "karuta_k_small_percent": 12,
        "voice_enabled": True,
        "voice_xp_per_interval": 1,
        "voice_interval_seconds": 180,
        "voice_daily_cap_xp": 100,
        "voice_levelup_channel_id": 0,
    }
    monkeypatch.setattr(mod, "XP_CONFIG_DEFAULTS", defaults, raising=True)

    cfg = mod.xp_get_config(999)
    assert cfg == dict(defaults)

    # doit faire SELECT puis INSERT (via 2e get_conn, mais même FakeConn ici)
    assert any("SELECT enabled" in s for (s, _) in fconn.calls)
    assert any("INSERT OR IGNORE INTO xp_config" in s for (s, _) in fconn.calls)


# ----------------------------
# xp_set_config
# ----------------------------

def test_xp_set_config_noop_when_no_fields(monkeypatch):
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)
    mod.xp_set_config(1)
    # si get_conn appelé => fail


def test_xp_set_config_inserts_then_updates_with_correct_sets_and_params(monkeypatch, fconn: FakeConn):
    monkeypatch.setattr(
        mod,
        "XP_CONFIG_DEFAULTS",
        {
            "enabled": True,
            "points_per_message": 8,
            "cooldown_seconds": 90,
            "bonus_percent": 20,
            "karuta_k_small_percent": 30,
            "voice_enabled": True,
            "voice_xp_per_interval": 1,
            "voice_interval_seconds": 180,
            "voice_daily_cap_xp": 100,
            "voice_levelup_channel_id": 0,
        },
        raising=True,
    )

    mod.xp_set_config(
        123,
        enabled=False,
        points_per_message=5,
        voice_enabled=False,
        voice_xp_per_interval=2,
        voice_levelup_channel_id=999,
    )

    assert len(fconn.calls) == 2

    sql1, params1 = fconn.calls[0]
    assert "INSERT OR IGNORE INTO xp_config" in sql1
    assert params1[0] == 123

    sql2, params2 = fconn.calls[1]
    assert sql2.startswith("UPDATE xp_config SET")
    # ordre = celui de la fonction
    assert "enabled=?" in sql2
    assert "points_per_message=?" in sql2
    assert "voice_enabled=?" in sql2
    assert "voice_xp_per_interval=?" in sql2
    assert "voice_levelup_channel_id=?" in sql2
    assert params2 == (0, 5, 0, 2, 999, 123)


# ----------------------------
# Voice progress
# ----------------------------

def test_xp_voice_get_progress_returns_defaults_when_missing(fconn: FakeConn):
    fconn.set_next(one=None)
    prog = mod.xp_voice_get_progress(1, 2)
    assert prog == {
        "day_key": "",
        "last_tick_ts": 0,
        "buffer_seconds": 0,
        "bonus_cents": 0,
        "xp_today": 0,
    }


def test_xp_voice_get_progress_casts_values_when_row_exists(fconn: FakeConn):
    fconn.set_next(one=("20260101", "10", "20", "30", "40"))
    prog = mod.xp_voice_get_progress(1, 2)
    assert prog == {
        "day_key": "20260101",
        "last_tick_ts": 10,
        "buffer_seconds": 20,
        "bonus_cents": 30,
        "xp_today": 40,
    }


def test_xp_voice_upsert_progress_always_inserts_ignore_and_updates_only_if_sets_present(fconn: FakeConn):
    mod.xp_voice_upsert_progress(1, 2)
    assert len(fconn.calls) == 1
    assert fconn.calls[0][0] == "INSERT OR IGNORE INTO xp_voice_progress(guild_id, user_id) VALUES (?, ?)"
    assert fconn.calls[0][1] == (1, 2)

    fconn.calls.clear()
    mod.xp_voice_upsert_progress(1, 2, day_key="x", xp_today=5)
    assert len(fconn.calls) == 2

    sql1, params1 = fconn.calls[0]
    assert "INSERT OR IGNORE INTO xp_voice_progress" in sql1
    assert params1 == (1, 2)

    sql2, params2 = fconn.calls[1]
    assert sql2.startswith("UPDATE xp_voice_progress SET")
    assert "day_key=?" in sql2
    assert "xp_today=?" in sql2
    assert "WHERE guild_id=? AND user_id=?" in sql2
    assert params2 == ("x", 5, 1, 2)


# ----------------------------
# xp_is_enabled
# ----------------------------

def test_xp_is_enabled_false_when_missing(fconn: FakeConn):
    fconn.set_next(one=None)
    assert mod.xp_is_enabled(1) is False


def test_xp_is_enabled_casts_bool(fconn: FakeConn):
    fconn.set_next(one=(1,))
    assert mod.xp_is_enabled(1) is True
    fconn.calls.clear()
    fconn.set_next(one=(0,))
    assert mod.xp_is_enabled(1) is False


# ----------------------------
# Levels
# ----------------------------

def test_xp_get_levels_maps_and_sorts_by_query(fconn: FakeConn):
    fconn.set_next(all=[("1", "0"), ("2", "100")])
    levels = mod.xp_get_levels(1)
    assert levels == [(1, 0), (2, 100)]

    sql, params = fconn.calls[0]
    assert "ORDER BY level" in sql
    assert params == (1,)


def test_xp_get_levels_with_roles_maps_none_role(fconn: FakeConn):
    fconn.set_next(all=[("1", "0", None), ("2", "100", "999")])
    rows = mod.xp_get_levels_with_roles(1)
    assert rows == [(1, 0, None), (2, 100, 999)]


def test_xp_set_level_threshold_executes_upsert(fconn: FakeConn):
    mod.xp_set_level_threshold(1, 2, 150)
    sql, params = fconn.calls[0]
    assert "INSERT INTO xp_levels" in sql
    assert "DO UPDATE SET xp_required=excluded.xp_required" in sql
    assert params == (1, 2, 150)


def test_xp_upsert_role_id_executes_upsert(fconn: FakeConn):
    mod.xp_upsert_role_id(1, 2, 999)
    sql, params = fconn.calls[0]
    assert "INSERT INTO xp_levels" in sql
    assert "DO UPDATE SET role_id=excluded.role_id" in sql
    assert params == (1, 2, 999)


def test_xp_get_role_ids_builds_dict(fconn: FakeConn):
    fconn.set_next(all=[(1, 111), ("2", "222")])
    d = mod.xp_get_role_ids(1)
    assert d == {1: 111, 2: 222}


# ----------------------------
# Members
# ----------------------------

def test_xp_get_member_uses_provided_conn_and_returns_default_if_missing(monkeypatch):
    conn = FakeConn()
    conn.set_next(one=None)
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    assert mod.xp_get_member(1, 2, conn=conn) == (0, 0)
    sql, params = conn.calls[0]
    assert "SELECT xp, last_xp_ts FROM xp_members" in sql
    assert params == (1, 2)


def test_xp_get_member_uses_get_conn_when_conn_none(fconn: FakeConn):
    fconn.set_next(one=(10, 20))
    assert mod.xp_get_member(1, 2) == (10, 20)


def test_xp_set_member_noop_when_no_fields(monkeypatch):
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)
    mod.xp_set_member(1, 2)
    # no get_conn


def test_xp_set_member_inserts_then_updates_partial(fconn: FakeConn):
    mod.xp_set_member(1, 2, xp=10)

    assert len(fconn.calls) == 2
    assert fconn.calls[0][0] == "INSERT OR IGNORE INTO xp_members(guild_id, user_id) VALUES (?, ?)"
    assert fconn.calls[0][1] == (1, 2)

    sql2, params2 = fconn.calls[1]
    assert sql2.startswith("UPDATE xp_members SET")
    assert "xp=?" in sql2
    assert "WHERE guild_id=? AND user_id=?" in sql2
    assert params2 == (10, 1, 2)


def test_xp_add_xp_uses_provided_conn_executes_insert_update_optional_last_ts_and_select(monkeypatch):
    conn = FakeConn()

    # Simule séquence : INSERT(ignore) (no fetch), UPDATE (no fetch), UPDATE last_ts (no fetch), SELECT xp fetchone
    seq = [
        FakeCursor(one=None),
        FakeCursor(one=None),
        FakeCursor(one=None),
        FakeCursor(one=(42,)),
    ]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        conn.calls.append((sql.strip(), params))
        cur = seq[i["n"]]
        i["n"] += 1
        return cur

    conn.execute = exec_seq  # type: ignore[assignment]
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    new_xp = mod.xp_add_xp(1, 2, 5, set_last_xp_ts=999, conn=conn)
    assert new_xp == 42

    assert "INSERT OR IGNORE INTO xp_members" in conn.calls[0][0]
    assert "UPDATE xp_members SET xp = MAX" in conn.calls[1][0]
    assert "UPDATE xp_members SET last_xp_ts=?" in conn.calls[2][0]
    assert conn.calls[2][1] == (999, 1, 2)
    assert "SELECT xp FROM xp_members" in conn.calls[3][0]


def test_xp_add_xp_uses_get_conn_when_conn_none(fconn: FakeConn):
    # Simule insert/update/select sans last_ts
    seq = [FakeCursor(one=None), FakeCursor(one=None), FakeCursor(one=(10,))]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        fconn.calls.append((sql.strip(), params))
        cur = seq[i["n"]]
        i["n"] += 1
        return cur

    fconn.execute = exec_seq  # type: ignore[assignment]

    assert mod.xp_add_xp(1, 2, 5) == 10


def test_xp_list_members_maps_rows_and_uses_limit_offset(fconn: FakeConn):
    fconn.set_next(all=[("10", "1000"), (2, 5)])
    rows = mod.xp_list_members(1, limit="3", offset="7")  # type: ignore[arg-type]
    assert rows == [(10, 1000), (2, 5)]

    sql, params = fconn.calls[0]
    assert "ORDER BY xp DESC, user_id ASC" in sql
    assert "LIMIT ? OFFSET ?" in sql
    assert params == (1, 3, 7)


def test_xp_get_role_ids_empty_when_no_rows(fconn: FakeConn):
    fconn.set_next(all=[])
    assert mod.xp_get_role_ids(1) == {}


def test_xp_get_member_casts_ints_when_row_exists(monkeypatch):
    conn = FakeConn()
    conn.set_next(one=("7", "9"))
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    assert mod.xp_get_member(1, 2, conn=conn) == (7, 9)


def test_xp_set_member_updates_both_fields_in_one_query(fconn: FakeConn):
    mod.xp_set_member(1, 2, xp=10, last_xp_ts=20)

    assert len(fconn.calls) == 2
    sql2, params2 = fconn.calls[1]
    assert "xp=?" in sql2
    assert "last_xp_ts=?" in sql2
    assert params2 == (10, 20, 1, 2)


def test_xp_add_xp_with_conn_and_no_last_ts_does_not_update_last_ts(monkeypatch):
    conn = FakeConn()
    seq = [FakeCursor(one=None), FakeCursor(one=None), FakeCursor(one=(5,))]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        conn.calls.append((sql.strip(), params))
        cur = seq[i["n"]]
        i["n"] += 1
        return cur

    conn.execute = exec_seq  # type: ignore[assignment]
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    assert mod.xp_add_xp(1, 2, 1, set_last_xp_ts=None, conn=conn) == 5
    assert len(conn.calls) == 3
    assert not any("last_xp_ts" in sql for (sql, _) in conn.calls)


def test_xp_set_config_updates_single_field_voice_levelup_channel_id(fconn: FakeConn):
    fconn.calls.clear()
    mod.xp_set_config(1, voice_levelup_channel_id=123)

    assert len(fconn.calls) == 2
    sql2, params2 = fconn.calls[1]
    assert "voice_levelup_channel_id=?" in sql2
    assert "enabled=?" not in sql2
    assert params2 == (123, 1)
