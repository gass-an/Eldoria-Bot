from __future__ import annotations

import pytest

from eldoria.db.repo import temp_voice_repo as mod


class FakeCursor:
    def __init__(self, *, one=None, all=None):
        self._one = one
        self._all = all

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakeConn:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self._next = FakeCursor(one=None, all=[])

    def set_next(self, *, one=None, all=None):
        self._next = FakeCursor(one=one, all=all)

    def execute(self, sql: str, params: tuple):
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


def test_tv_upsert_parent_executes_insert_on_conflict(fconn: FakeConn):
    mod.tv_upsert_parent(1, 10, 5)

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "INSERT INTO temp_voice_parents" in sql
    assert "ON CONFLICT(guild_id, parent_channel_id) DO UPDATE SET user_limit=excluded.user_limit" in sql
    assert params == (1, 10, 5)


def test_tv_get_parent_returns_user_limit_or_none(fconn: FakeConn):
    fconn.set_next(one=(7,), all=None)
    assert mod.tv_get_parent(1, 10) == 7

    fconn.calls.clear()
    fconn.set_next(one=None, all=None)
    assert mod.tv_get_parent(1, 10) is None

    sql, params = fconn.calls[0]
    assert "SELECT user_limit FROM temp_voice_parents" in sql
    assert "WHERE guild_id=? AND parent_channel_id=?" in sql
    assert params == (1, 10)


def test_tv_find_parent_of_active_returns_parent_or_none(fconn: FakeConn):
    fconn.set_next(one=(999,), all=None)
    assert mod.tv_find_parent_of_active(1, 55) == 999

    fconn.calls.clear()
    fconn.set_next(one=None, all=None)
    assert mod.tv_find_parent_of_active(1, 55) is None

    sql, params = fconn.calls[0]
    assert "SELECT parent_channel_id" in sql
    assert "FROM temp_voice_active" in sql
    assert "WHERE guild_id=? AND channel_id=?" in sql
    assert params == (1, 55)


def test_tv_add_active_executes_insert_or_ignore(fconn: FakeConn):
    mod.tv_add_active(1, 10, 100)

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "INSERT OR IGNORE INTO temp_voice_active" in sql
    assert params == (1, 10, 100)


def test_tv_remove_active_executes_delete(fconn: FakeConn):
    mod.tv_remove_active(1, 10, 100)

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "DELETE FROM temp_voice_active" in sql
    assert "WHERE guild_id=? AND parent_channel_id=? AND channel_id=?" in sql
    assert params == (1, 10, 100)


def test_tv_list_active_maps_channel_ids(fconn: FakeConn):
    fconn.set_next(all=[(100,), (101,), (999,)], one=None)

    res = mod.tv_list_active(1, 10)
    assert res == [100, 101, 999]

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT channel_id FROM temp_voice_active" in sql
    assert "WHERE guild_id=? AND parent_channel_id=?" in sql
    assert params == (1, 10)


def test_tv_list_active_all_returns_rows_directly(fconn: FakeConn):
    rows = [(10, 100), (10, 101), (11, 200)]
    fconn.set_next(all=rows, one=None)

    res = mod.tv_list_active_all(1)
    assert res == rows

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT parent_channel_id, channel_id" in sql
    assert "FROM temp_voice_active" in sql
    assert "WHERE guild_id=?" in sql
    assert params == (1,)


def test_tv_delete_parent_executes_delete(fconn: FakeConn):
    mod.tv_delete_parent(1, 10)

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "DELETE FROM temp_voice_parents" in sql
    assert "WHERE guild_id=? AND parent_channel_id=?" in sql
    assert params == (1, 10)


def test_tv_list_parents_returns_rows(fconn: FakeConn):
    rows = [(10, 2), (11, 0)]
    fconn.set_next(all=rows, one=None)

    res = mod.tv_list_parents(1)
    assert res == rows

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT parent_channel_id, user_limit" in sql
    assert "FROM temp_voice_parents" in sql
    assert "WHERE guild_id=?" in sql
    assert params == (1,)
