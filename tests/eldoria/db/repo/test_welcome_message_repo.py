from __future__ import annotations

import pytest

from eldoria.db.repo import welcome_message_repo as mod
from tests._fakes._db_fakes import FakeConn, FakeConnCM


@pytest.fixture
def fconn(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(mod, "get_conn", lambda: FakeConnCM(conn), raising=True)
    return conn

# ----------------------------
# Config
# ----------------------------

def test_wm_ensure_defaults_inserts_or_ignores_with_casts(fconn: FakeConn):
    mod.wm_ensure_defaults(123, enabled=True, channel_id="456")  # type: ignore[arg-type]

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "INSERT OR IGNORE INTO welcome_config" in sql
    assert params == (123, 1, 456)

def test_wm_get_config_returns_defaults_and_calls_ensure_when_missing(monkeypatch, fconn: FakeConn):
    # SELECT retourne None
    fconn.set_next(one=None, all=None)

    called = {"n": 0, "args": None}

    def fake_ensure(guild_id: int, *, enabled: bool = False, channel_id: int = 0):
        called["n"] += 1
        called["args"] = (guild_id, enabled, channel_id)

    monkeypatch.setattr(mod, "wm_ensure_defaults", fake_ensure, raising=True)

    cfg = mod.wm_get_config(999)

    assert cfg == {"enabled": False, "channel_id": 0}
    assert called["n"] == 1
    assert called["args"] == (999, False, 0)

def test_wm_get_config_casts_types_when_row_exists(fconn: FakeConn):
    fconn.set_next(one=(1, "777"), all=None)
    cfg = mod.wm_get_config(1)
    assert cfg == {"enabled": True, "channel_id": 777}

def test_wm_set_config_noop_when_no_fields(monkeypatch):
    # si get_conn est appelé -> fail
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    mod.wm_set_config(1)
    # rien à assert : absence d'exception prouve no-op

def test_wm_set_config_updates_enabled_only_and_ensures_row_exists(fconn: FakeConn):
    mod.wm_set_config(10, enabled=False)

    assert len(fconn.calls) == 2

    sql1, params1 = fconn.calls[0]
    assert "INSERT OR IGNORE INTO welcome_config" in sql1
    assert params1 == (10,)

    sql2, params2 = fconn.calls[1]
    assert sql2.startswith("UPDATE welcome_config SET")
    assert "enabled=?" in sql2
    assert "WHERE guild_id=?" in sql2
    assert params2 == (0, 10)

def test_wm_set_config_updates_channel_only(fconn: FakeConn):
    mod.wm_set_config(10, channel_id=1234)

    assert len(fconn.calls) == 2
    sql2, params2 = fconn.calls[1]
    assert "channel_id=?" in sql2
    assert params2 == (1234, 10)

def test_wm_set_config_updates_both_enabled_and_channel(fconn: FakeConn):
    mod.wm_set_config(10, enabled=True, channel_id=555)

    assert len(fconn.calls) == 2
    sql2, params2 = fconn.calls[1]

    # ordre des sets = enabled puis channel_id (selon ton code)
    assert "enabled=?" in sql2
    assert "channel_id=?" in sql2
    assert params2 == (1, 555, 10)

def test_wm_set_enabled_delegates_to_set_config(monkeypatch):
    seen = {}

    def fake_set_config(guild_id: int, *, enabled=None, channel_id=None):
        seen["guild_id"] = guild_id
        seen["enabled"] = enabled
        seen["channel_id"] = channel_id

    monkeypatch.setattr(mod, "wm_set_config", fake_set_config, raising=True)

    mod.wm_set_enabled(1, True)
    assert seen == {"guild_id": 1, "enabled": True, "channel_id": None}

def test_wm_set_channel_id_delegates_to_set_config(monkeypatch):
    seen = {}

    def fake_set_config(guild_id: int, *, enabled=None, channel_id=None):
        seen["guild_id"] = guild_id
        seen["enabled"] = enabled
        seen["channel_id"] = channel_id

    monkeypatch.setattr(mod, "wm_set_config", fake_set_config, raising=True)

    mod.wm_set_channel_id(2, 999)
    assert seen == {"guild_id": 2, "enabled": None, "channel_id": 999}

def test_wm_is_enabled_false_when_missing(fconn: FakeConn):
    fconn.set_next(one=None, all=None)
    assert mod.wm_is_enabled(1) is False

def test_wm_is_enabled_casts_bool(fconn: FakeConn):
    fconn.set_next(one=(1,), all=None)
    assert mod.wm_is_enabled(1) is True

    fconn.calls.clear()
    fconn.set_next(one=(0,), all=None)
    assert mod.wm_is_enabled(1) is False

def test_wm_get_channel_id_returns_0_when_missing(fconn: FakeConn):
    fconn.set_next(one=None, all=None)
    assert mod.wm_get_channel_id(1) == 0

def test_wm_get_channel_id_casts_int(fconn: FakeConn):
    fconn.set_next(one=("123",), all=None)
    assert mod.wm_get_channel_id(1) == 123

def test_wm_delete_config_executes_delete(fconn: FakeConn):
    mod.wm_delete_config(5)
    sql, params = fconn.calls[0]
    assert sql == "DELETE FROM welcome_config WHERE guild_id=?"
    assert params == (5,)

# ----------------------------
# History
# ----------------------------

def test_wm_get_recent_message_keys_limit_zero_or_negative_returns_empty(monkeypatch):
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    assert mod.wm_get_recent_message_keys(1, limit=0) == []
    assert mod.wm_get_recent_message_keys(1, limit=-10) == []

def test_wm_get_recent_message_keys_executes_select_with_limit_and_filters_none(fconn: FakeConn):
    fconn.set_next(all=[("a",), (None,), ("b",), ()], one=None)  # () -> r[0] would fail if not guarded by `if r`
    res = mod.wm_get_recent_message_keys(1, limit=3)

    assert res == ["a", "b"]

    sql, params = fconn.calls[0]
    assert "FROM welcome_message_history" in sql
    assert "ORDER BY used_at DESC, id DESC" in sql
    assert "LIMIT ?" in sql
    assert params == (1, 3)

def test_wm_record_welcome_message_noop_on_empty_key(monkeypatch):
    monkeypatch.setattr(
        mod,
        "get_conn",
        lambda: (_ for _ in ()).throw(AssertionError("get_conn called")),
        raising=True,
    )

    mod.wm_record_welcome_message(1, "")

def test_wm_record_welcome_message_spaces_key_is_not_noop(fconn):
    # "   " est truthy => insert doit se produire
    fconn.calls.clear()
    mod.wm_record_welcome_message(1, "   ", used_at=1, keep=0)

    assert len(fconn.calls) == 2
    sql1, params1 = fconn.calls[0]
    assert "INSERT INTO welcome_message_history" in sql1
    assert params1 == (1, "   ", 1)

def test_wm_record_welcome_message_uses_used_at_when_provided_and_keep_positive(fconn: FakeConn):
    mod.wm_record_welcome_message(1, "k1", used_at=12345, keep=10)

    assert len(fconn.calls) == 2

    sql1, params1 = fconn.calls[0]
    assert "INSERT INTO welcome_message_history" in sql1
    assert params1 == (1, "k1", 12345)

    sql2, params2 = fconn.calls[1]
    assert "DELETE FROM welcome_message_history" in sql2
    assert "LIMIT -1 OFFSET ?" in sql2
    assert params2 == (1, 10)

def test_wm_record_welcome_message_uses_time_time_when_used_at_none(monkeypatch, fconn: FakeConn):
    monkeypatch.setattr(mod.time, "time", lambda: 999.9, raising=True)

    mod.wm_record_welcome_message(1, "k2", used_at=None, keep=1)

    sql1, params1 = fconn.calls[0]
    assert params1 == (1, "k2", 999)  # int(time.time())

def test_wm_record_welcome_message_keep_zero_deletes_all_and_returns_early(fconn: FakeConn):
    mod.wm_record_welcome_message(1, "k3", used_at=1, keep=0)

    assert len(fconn.calls) == 2
    sql1, params1 = fconn.calls[0]
    assert "INSERT INTO welcome_message_history" in sql1
    assert params1 == (1, "k3", 1)

    sql2, params2 = fconn.calls[1]
    assert sql2 == "DELETE FROM welcome_message_history WHERE guild_id=?"
    assert params2 == (1,)

def test_wm_record_welcome_message_keep_negative_clamps_to_zero_and_deletes_all(fconn: FakeConn):
    mod.wm_record_welcome_message(1, "k4", used_at=1, keep=-5)

    assert len(fconn.calls) == 2
    assert fconn.calls[1][0] == "DELETE FROM welcome_message_history WHERE guild_id=?"
