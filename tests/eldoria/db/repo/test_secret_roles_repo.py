from __future__ import annotations

import pytest

from eldoria.db.repo import secret_roles_repo as mod


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
        self._next_cursor: FakeCursor = FakeCursor(one=None, all=[])

    def set_next(self, *, one=None, all=None):
        self._next_cursor = FakeCursor(one=one, all=all)

    def execute(self, sql: str, params: tuple):
        # enregistre le SQL “normalisé” (strip) + params
        self.calls.append((sql.strip(), params))
        return self._next_cursor


class FakeConnCM:
    def __init__(self, conn: FakeConn):
        self.conn = conn
        self.entered = 0
        self.exited = 0

    def __enter__(self):
        self.entered += 1
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        self.exited += 1
        return False


@pytest.fixture
def fconn(monkeypatch):
    conn = FakeConn()
    cm = FakeConnCM(conn)
    monkeypatch.setattr(mod, "get_conn", lambda: cm, raising=True)
    return conn


def test_sr_upsert_executes_insert_on_conflict_with_params(fconn: FakeConn):
    mod.sr_upsert(1, 2, "hello", 99)

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "INSERT INTO secret_roles" in sql
    assert "ON CONFLICT(guild_id, channel_id, phrase) DO UPDATE" in sql
    assert params == (1, 2, "hello", 99)


def test_sr_delete_executes_delete_with_params(fconn: FakeConn):
    mod.sr_delete(1, 2, "bye")

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "DELETE FROM secret_roles" in sql
    assert "WHERE guild_id=? AND channel_id=? AND phrase=?" in sql
    assert params == (1, 2, "bye")


def test_sr_match_returns_role_id_when_row_exists(fconn: FakeConn):
    fconn.set_next(one=(123,), all=None)

    rid = mod.sr_match(1, 2, "p")
    assert rid == 123

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT role_id FROM secret_roles" in sql
    assert "WHERE guild_id=? AND channel_id=? AND phrase=?" in sql
    assert params == (1, 2, "p")


def test_sr_match_returns_none_when_no_row(fconn: FakeConn):
    fconn.set_next(one=None, all=None)

    rid = mod.sr_match(1, 2, "missing")
    assert rid is None


def test_sr_list_messages_returns_list_of_phrases(fconn: FakeConn):
    fconn.set_next(all=[("b",), ("a",)], one=None)

    res = mod.sr_list_messages(1, 2)
    assert res == ["b", "a"]  # la DB décide de l'ordre; nous on mappe juste r[0]

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT phrase" in sql
    assert "ORDER BY phrase" in sql  # la logique “tri” = requête contient ORDER BY
    assert params == (1, 2)


def test_sr_list_by_guild_grouped_groups_rows_by_channel_and_casts_channel_id_to_str(fconn: FakeConn):
    # rows = (channel_id, phrase, role_id)
    fconn.set_next(
        all=[
            (10, "a", 111),
            (10, "b", 222),
            (11, "x", 999),
        ],
        one=None,
    )

    res = mod.sr_list_by_guild_grouped(1)

    # Important: le code retourne list(grouped.items()) -> ordre d'insertion
    assert res == [
        ("10", {"a": 111, "b": 222}),
        ("11", {"x": 999}),
    ]

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT channel_id, phrase, role_id" in sql
    assert "WHERE guild_id=?" in sql
    assert "ORDER BY channel_id" in sql
    assert params == (1,)


def test_sr_list_by_guild_grouped_empty_rows_returns_empty_list(fconn: FakeConn):
    fconn.set_next(all=[], one=None)
    assert mod.sr_list_by_guild_grouped(1) == []
