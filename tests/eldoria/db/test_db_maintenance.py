import errno
import importlib

import pytest

import eldoria.db.maintenance as maintenance


@pytest.fixture
def mod():
    importlib.reload(maintenance)
    return maintenance


class _FakeCursor:
    def __init__(self, row=(1,)):
        self._row = row

    def fetchone(self):
        return self._row


class FakeConn:
    def __init__(self, name="main"):
        self.name = name
        self.executed = []
        self.closed = 0
        self.backup_calls = []

    def execute(self, sql):
        self.executed.append(sql)
        # IMPORTANT: ton code attend un objet avec fetchone()
        return _FakeCursor()

    def close(self):
        self.closed += 1

    def backup(self, other_conn):
        self.backup_calls.append(other_conn)


def test_backup_to_file_raises_if_checkpoint_fails(monkeypatch, mod):
    main = FakeConn("main")
    bck = FakeConn("backup")

    def execute_maybe_fail(sql):
        main.executed.append(sql)
        if "wal_checkpoint" in sql.lower():
            raise RuntimeError("checkpoint failed")
        return _FakeCursor()

    main.execute = execute_maybe_fail  # type: ignore[method-assign]

    connect_calls = []

    def fake_connect(arg):
        connect_calls.append(arg)
        if len(connect_calls) == 1:
            return main
        return bck

    monkeypatch.setattr(mod.sqlite3, "connect", fake_connect, raising=True)

    # comportement actuel: l'erreur remonte
    with pytest.raises(RuntimeError, match="checkpoint failed"):
        mod.backup_to_file("backup.db")

    # checkpoint tenté
    assert any("wal_checkpoint" in s.lower() for s in main.executed)


def test_backup_to_file_ignores_sqlite_database_error_on_checkpoint(monkeypatch, mod):
    """Couvre le `except sqlite3.DatabaseError: pass` (ligne 17-18)."""
    main = FakeConn("main")
    bck = FakeConn("backup")

    class FakeDbError(mod.sqlite3.DatabaseError):
        pass

    def execute_maybe_fail(sql):
        main.executed.append(sql)
        if "wal_checkpoint" in sql.lower():
            raise FakeDbError("checkpoint failed")
        return _FakeCursor()

    main.execute = execute_maybe_fail  # type: ignore[method-assign]

    connect_calls = []

    def fake_connect(arg):
        connect_calls.append(arg)
        if len(connect_calls) == 1:
            return main
        return bck

    monkeypatch.setattr(mod.sqlite3, "connect", fake_connect, raising=True)

    # ne doit pas lever
    mod.backup_to_file("backup.db")

    assert any("wal_checkpoint" in s.lower() for s in main.executed)
    assert bck.closed == 1
    assert main.closed == 1


def test_replace_db_file_happy_path_just_replaces(monkeypatch, mod):
    calls = {"replace": []}
    monkeypatch.setattr(mod, "DB_PATH", "eldoria.db", raising=False)

    def fake_replace(src, dst):
        calls["replace"].append((src, dst))

    monkeypatch.setattr(mod.os, "replace", fake_replace, raising=True)
    monkeypatch.setattr(mod.sqlite3, "connect", lambda _: FakeConn("test"), raising=True)

    mod.replace_db_file("new.db")

    assert calls["replace"] == [("new.db", mod.DB_PATH)]


def test_replace_db_file_cross_device_fallback(monkeypatch, mod):
    monkeypatch.setattr(mod, "DB_PATH", r"C:\tmp\eldoria\data\db.sqlite", raising=False)

    calls = {"replace": [], "makedirs": [], "copy2": [], "remove": [], "connect": []}

    # mock sqlite connect (ton code fait sqlite3.connect(new_db_path) + sqlite3.connect(DB_PATH))
    test_conn = FakeConn("test")
    real_conn = FakeConn("real")

    def fake_connect(path):
        calls["connect"].append(path)
        if path == r"D:\downloads\new.db":
            return test_conn
        return real_conn

    monkeypatch.setattr(mod.sqlite3, "connect", fake_connect, raising=True)

    first = True

    def fake_replace(src, dst):
        nonlocal first
        calls["replace"].append((src, dst))
        if first:
            first = False
            raise OSError(errno.EXDEV, "Cross-device link")
        return None

    monkeypatch.setattr(mod.os, "replace", fake_replace, raising=True)
    monkeypatch.setattr(
        mod.os,
        "makedirs",
        lambda p, exist_ok=False: calls["makedirs"].append((p, exist_ok)),
        raising=True,
    )
    monkeypatch.setattr(mod.shutil, "copy2", lambda s, d: calls["copy2"].append((s, d)), raising=True)
    monkeypatch.setattr(mod.os, "remove", lambda p: calls["remove"].append(p), raising=True)

    mod.replace_db_file(r"D:\downloads\new.db")

    # on a bien essayé de se connecter au nouveau fichier pour "valider"
    assert r"D:\downloads\new.db" in calls["connect"]

    # replace initial a échoué (EXDEV) puis fallback
    assert calls["replace"][0] == (r"D:\downloads\new.db", mod.DB_PATH)
    assert calls["copy2"], "fallback doit copier le fichier avant replace atomique"
    assert len(calls["replace"]) == 2, "fallback doit faire un 2e os.replace (tmp -> DB_PATH)"
    assert calls["makedirs"], "fallback doit créer le dossier destination au besoin"


def test_replace_db_file_cross_device_remove_failure_is_ignored(monkeypatch, mod):
    """Couvre le `except OSError: pass` lors du remove (ligne 53-54)."""
    monkeypatch.setattr(mod, "DB_PATH", r"C:\tmp\eldoria\data\db.sqlite", raising=False)

    test_conn = FakeConn("test")

    monkeypatch.setattr(mod.sqlite3, "connect", lambda _p: test_conn, raising=True)

    first = True

    def fake_replace(src, dst):
        nonlocal first
        if first:
            first = False
            raise OSError(errno.EXDEV, "Cross-device link")
        return None

    monkeypatch.setattr(mod.os, "replace", fake_replace, raising=True)
    monkeypatch.setattr(mod.os, "makedirs", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(mod.shutil, "copy2", lambda *_a, **_k: None, raising=True)

    def remove_raises(_p):
        raise OSError("cannot remove")

    monkeypatch.setattr(mod.os, "remove", remove_raises, raising=True)

    # ne doit pas lever
    mod.replace_db_file(r"D:\downloads\new.db")


def test_replace_db_file_other_oserror_is_raised(monkeypatch, mod):
    monkeypatch.setattr(mod, "DB_PATH", "eldoria.db", raising=False)

    def fake_replace(src, dst):
        raise OSError(errno.EPERM, "nope")

    monkeypatch.setattr(mod.os, "replace", fake_replace, raising=True)
    monkeypatch.setattr(mod.sqlite3, "connect", lambda _: FakeConn("test"), raising=True)

    with pytest.raises(OSError) as e:
        mod.replace_db_file("new.db")

    assert e.value.errno == errno.EPERM
