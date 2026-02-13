from __future__ import annotations

import pytest

from eldoria.db.repo import reaction_roles_repo as mod


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


def test_rr_upsert_executes_insert_on_conflict_with_params(fconn: FakeConn):
    mod.rr_upsert(1, 2, "😀", 99)

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "INSERT INTO reaction_roles" in sql
    assert "ON CONFLICT(guild_id, message_id, emoji) DO UPDATE" in sql
    assert params == (1, 2, "😀", 99)


def test_rr_delete_executes_delete_with_params(fconn: FakeConn):
    mod.rr_delete(1, 2, "🔥")

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "DELETE FROM reaction_roles" in sql
    assert "WHERE guild_id=? AND message_id=? AND emoji=?" in sql
    assert params == (1, 2, "🔥")


def test_rr_delete_message_executes_delete_message_with_params(fconn: FakeConn):
    mod.rr_delete_message(1, 2)

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "DELETE FROM reaction_roles" in sql
    assert "WHERE guild_id=? AND message_id=?" in sql
    assert params == (1, 2)


def test_rr_get_role_id_returns_role_id_when_row_exists(fconn: FakeConn):
    fconn.set_next(one=(123,), all=None)

    rid = mod.rr_get_role_id(1, 2, "✅")
    assert rid == 123

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT role_id FROM reaction_roles" in sql
    assert "WHERE guild_id=? AND message_id=? AND emoji=?" in sql
    assert params == (1, 2, "✅")


def test_rr_get_role_id_returns_none_when_no_row(fconn: FakeConn):
    fconn.set_next(one=None, all=None)
    assert mod.rr_get_role_id(1, 2, "❌") is None


def test_rr_list_by_message_builds_dict_mapping(fconn: FakeConn):
    fconn.set_next(all=[("😀", 1), ("🔥", 2)], one=None)

    res = mod.rr_list_by_message(1, 2)
    assert res == {"😀": 1, "🔥": 2}

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT emoji, role_id" in sql
    assert "WHERE guild_id=? AND message_id=?" in sql
    assert params == (1, 2)


def test_rr_list_by_message_last_duplicate_wins_python_dict_semantics(fconn: FakeConn):
    """
    Si la DB renvoie 2 fois le même emoji, le dict écrase avec le dernier.
    Teste la logique Python (pas la DB).
    """
    fconn.set_next(all=[("😀", 1), ("😀", 999)], one=None)

    res = mod.rr_list_by_message(1, 2)
    assert res == {"😀": 999}


def test_rr_list_by_guild_grouped_groups_by_message_id_as_str(fconn: FakeConn):
    # rows = (message_id, emoji, role_id)
    fconn.set_next(
        all=[
            (10, "😀", 111),
            (10, "🔥", 222),
            (11, "✅", 999),
        ],
        one=None,
    )

    res = mod.rr_list_by_guild_grouped(1)

    # ordre d'insertion dict (donc ordre rows)
    assert res == [
        ("10", {"😀": 111, "🔥": 222}),
        ("11", {"✅": 999}),
    ]

    assert len(fconn.calls) == 1
    sql, params = fconn.calls[0]
    assert "SELECT message_id, emoji, role_id" in sql
    assert "WHERE guild_id=?" in sql
    assert "ORDER BY message_id" in sql
    assert params == (1,)


def test_rr_list_by_guild_grouped_empty_returns_empty_list(fconn: FakeConn):
    fconn.set_next(all=[], one=None)
    assert mod.rr_list_by_guild_grouped(1) == []
