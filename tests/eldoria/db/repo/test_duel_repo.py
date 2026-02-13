from __future__ import annotations

import pytest

from eldoria.db.repo import duel_repo as mod

# ----------------------------
# Fakes
# ----------------------------

class FakeCursor:
    def __init__(self, *, lastrowid=None, one=None, all=None):
        self.lastrowid = lastrowid
        self._one = one
        self._all = all

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakeConn:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self._next_cursor = FakeCursor(one=None, all=[])

    def set_next_cursor(self, cursor: FakeCursor):
        self._next_cursor = cursor

    def execute(self, sql: str, params: tuple = ()):
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


# ----------------------------
# _execute_in_conn
# ----------------------------

def test__execute_in_conn_calls_conn_execute():
    conn = FakeConn()
    cur = FakeCursor(one=("ok",), all=None)
    conn.set_next_cursor(cur)

    out = mod._execute_in_conn(conn, "SELECT 1", (123,))

    assert out is cur
    assert conn.calls == [("SELECT 1", (123,))]


# ----------------------------
# create_duel
# ----------------------------

def test_create_duel_inserts_and_returns_lastrowid(fconn: FakeConn):
    fconn.set_next_cursor(FakeCursor(lastrowid=777))

    duel_id = mod.create_duel(1, 2, 10, 11, 1000, 2000)

    assert duel_id == 777
    assert len(fconn.calls) == 1

    sql, params = fconn.calls[0]
    assert "INSERT INTO duels" in sql
    assert "VALUES (?, ?, NULL, ?, ?, NULL, NULL, 'CONFIG', ?, ?, NULL, NULL)" in sql
    assert params == (1, 2, 10, 11, 1000, 2000)


# ----------------------------
# get_duel_by_id / by_message / active_for_user
# ----------------------------

def test_get_duel_by_id_uses_provided_conn_no_get_conn(monkeypatch):
    conn = FakeConn()
    conn.set_next_cursor(FakeCursor(one=("ROW",)))

    # si get_conn est appelé -> fail
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    row = mod.get_duel_by_id(123, conn=conn)
    assert row == ("ROW",)

    assert len(conn.calls) == 1
    sql, params = conn.calls[0]
    assert "SELECT *" in sql and "FROM duels" in sql and "WHERE duel_id = ?" in sql
    assert params == (123,)


def test_get_duel_by_id_uses_get_conn_when_conn_none(fconn: FakeConn):
    fconn.set_next_cursor(FakeCursor(one=("ROW2",)))
    row = mod.get_duel_by_id(123)
    assert row == ("ROW2",)


def test_get_duel_by_message_id_uses_correct_query_and_params(fconn: FakeConn):
    fconn.set_next_cursor(FakeCursor(one=("MSGROW",)))
    row = mod.get_duel_by_message_id(1, 2, 3)
    assert row == ("MSGROW",)

    sql, params = fconn.calls[0]
    assert "WHERE guild_id = ?" in sql
    assert "AND channel_id = ?" in sql
    assert "AND message_id = ?" in sql
    assert "LIMIT 1" in sql
    assert params == (1, 2, 3)


def test_get_active_duel_for_user_filters_status_and_orders(fconn: FakeConn):
    fconn.set_next_cursor(FakeCursor(one=("ACTIVEROW",)))
    row = mod.get_active_duel_for_user(1, 42)
    assert row == ("ACTIVEROW",)

    sql, params = fconn.calls[0]
    assert "status IN ('INVITED','ACTIVE')" in sql
    assert "ORDER BY created_at DESC" in sql
    assert "LIMIT 1" in sql
    assert params == (1, 42, 42)


# ----------------------------
# update_duel_if_status
# ----------------------------

def test_update_duel_if_status_returns_false_if_no_fields_to_update():
    assert mod.update_duel_if_status(1, "CONFIG") is False


def test_update_duel_if_status_executes_update_and_checks_changes_true(monkeypatch):
    conn = FakeConn()

    # 1) UPDATE => pas besoin de résultat
    # 2) SELECT changes() => fetchone()[0] -> 1
    cursors = [
        FakeCursor(one=None),
        FakeCursor(one=(1,)),
    ]
    idx = {"i": 0}

    def execute(sql: str, params: tuple = ()):
        conn.calls.append((sql.strip(), params))
        cur = cursors[idx["i"]]
        idx["i"] += 1
        return cur

    conn.execute = execute  # type: ignore[assignment]

    # get_conn ne doit pas être appelé car conn fourni
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    ok = mod.update_duel_if_status(
        7,
        "CONFIG",
        message_id=999,
        game_type=None,
        stake_xp=10,
        expires_at=None,
        finished_at=None,
        payload="{}",
        conn=conn,
    )
    assert ok is True

    # UPDATE params : (message_id, game_type, stake_xp, expires_at, finished_at, payload, duel_id, required_status)
    sql1, params1 = conn.calls[0]
    assert sql1.startswith("UPDATE duels")
    assert params1 == (999, None, 10, None, None, "{}", 7, "CONFIG")

    sql2, params2 = conn.calls[1]
    assert sql2 == "SELECT changes()"
    assert params2 == ()


def test_update_duel_if_status_changes_zero_returns_false(monkeypatch):
    conn = FakeConn()

    cursors = [FakeCursor(one=None), FakeCursor(one=(0,))]
    i = {"n": 0}

    def execute(sql: str, params: tuple = ()):
        conn.calls.append((sql.strip(), params))
        cur = cursors[i["n"]]
        i["n"] += 1
        return cur

    conn.execute = execute  # type: ignore[assignment]

    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    ok = mod.update_duel_if_status(1, "ACTIVE", payload="x", conn=conn)
    assert ok is False


def test_update_duel_if_status_uses_get_conn_when_conn_none(fconn: FakeConn):
    # UPDATE (ignore) + changes() == 1
    seq = [FakeCursor(one=None), FakeCursor(one=(1,))]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        fconn.calls.append((sql.strip(), params))
        cur = seq[i["n"]]
        i["n"] += 1
        return cur

    fconn.execute = exec_seq  # type: ignore[assignment]

    ok = mod.update_duel_if_status(1, "CONFIG", payload="{}", conn=None)
    assert ok is True


# ----------------------------
# transition_status
# ----------------------------

def test_transition_status_updates_and_checks_changes(monkeypatch):
    conn = FakeConn()
    seq = [FakeCursor(one=None), FakeCursor(one=(1,))]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        conn.calls.append((sql.strip(), params))
        cur = seq[i["n"]]
        i["n"] += 1
        return cur

    conn.execute = exec_seq  # type: ignore[assignment]
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    ok = mod.transition_status(7, "INVITED", "ACTIVE", 9999, conn=conn)
    assert ok is True

    sql1, params1 = conn.calls[0]
    assert sql1.startswith("UPDATE duels")
    assert params1 == ("ACTIVE", 9999, 7, "INVITED")

    sql2, params2 = conn.calls[1]
    assert sql2 == "SELECT changes()"
    assert params2 == ()


def test_transition_status_changes_zero_returns_false(monkeypatch):
    conn = FakeConn()
    seq = [FakeCursor(one=None), FakeCursor(one=(0,))]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        conn.calls.append((sql.strip(), params))
        cur = seq[i["n"]]
        i["n"] += 1
        return cur

    conn.execute = exec_seq  # type: ignore[assignment]
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    assert mod.transition_status(7, "INVITED", "ACTIVE", None, conn=conn) is False


# ----------------------------
# update_payload_if_unchanged
# ----------------------------

def test_update_payload_if_unchanged_updates_only_when_active_and_payload_matches(monkeypatch):
    conn = FakeConn()
    seq = [FakeCursor(one=None), FakeCursor(one=(1,))]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        conn.calls.append((sql.strip(), params))
        cur = seq[i["n"]]
        i["n"] += 1
        return cur

    conn.execute = exec_seq  # type: ignore[assignment]
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    ok = mod.update_payload_if_unchanged(5, old_payload_json=None, new_payload_json="{}", conn=conn)
    assert ok is True

    sql1, params1 = conn.calls[0]
    assert "UPDATE duels" in sql1
    assert "status='ACTIVE'" in sql1
    assert "COALESCE(payload, '') = COALESCE(?, '')" in sql1
    assert params1 == ("{}", 5, None)

    sql2, _ = conn.calls[1]
    assert sql2 == "SELECT changes()"


def test_update_payload_if_unchanged_changes_zero_returns_false(monkeypatch):
    conn = FakeConn()
    seq = [FakeCursor(one=None), FakeCursor(one=(0,))]
    i = {"n": 0}

    def exec_seq(sql: str, params: tuple = ()):
        conn.calls.append((sql.strip(), params))
        cur = seq[i["n"]]
        i["n"] += 1
        return cur

    conn.execute = exec_seq  # type: ignore[assignment]
    monkeypatch.setattr(mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("get_conn called")), raising=True)

    assert mod.update_payload_if_unchanged(5, old_payload_json="a", new_payload_json="b", conn=conn) is False


# ----------------------------
# list_expired_duels
# ----------------------------

def test_list_expired_duels_returns_rows_and_uses_order_by(fconn: FakeConn):
    fconn.set_next_cursor(FakeCursor(all=[("r1",), ("r2",)]))

    rows = mod.list_expired_duels(999)
    assert rows == [("r1",), ("r2",)]

    sql, params = fconn.calls[0]
    assert "status IN ('CONFIG','INVITED','ACTIVE')" in sql
    assert "expires_at <= ?" in sql
    assert "ORDER BY expires_at ASC" in sql
    assert params == (999,)


# ----------------------------
# cleanup_duels
# ----------------------------

def test_cleanup_duels_executes_delete_with_cutoffs(fconn: FakeConn):
    # la fonction dans ton snippet est tronquée, mais on peut au moins vérifier le DELETE et params
    mod.cleanup_duels(100, 200)

    assert fconn.calls, "cleanup_duels doit exécuter au moins un DELETE"
    sql, params = fconn.calls[0]
    assert sql.startswith("DELETE FROM duels")
    assert "status IN ('EXPIRED', 'CANCELLED')" in sql
    assert "status = 'FINISHED'" in sql
    assert params == (100, 200)

    # TODO: si cleanup_duels retourne des rows supprimés dans ta version complète,
    # ajoute un test sur le SELECT préalable et le return.
