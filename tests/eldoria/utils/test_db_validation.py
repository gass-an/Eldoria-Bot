import importlib

import pytest

import eldoria.utils.db_validation as db_validation


class FakeAttachment:
    def __init__(self, *, filename: str, payload: bytes):
        self.filename = filename
        self._payload = payload
        self.saved_paths: list[str] = []

    async def save(self, path):
        path_str = str(path)
        self.saved_paths.append(path_str)
        with open(path_str, "wb") as f:
            f.write(self._payload)


class _Tmp:
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def close(self):
        return None


class _Cursor:
    def __init__(self, row=(1,)):
        self._row = row

    def fetchone(self):
        return self._row


class _ConnOK:
    def execute(self, sql):
        return _Cursor((1,))

    def close(self):
        pass


@pytest.fixture
def mod():
    # Recharge le module pour pouvoir monkeypatch ses dépendances proprement
    importlib.reload(db_validation)
    return db_validation


@pytest.mark.asyncio
async def test_is_valid_sqlite_db_rejects_non_db_extension(mod):
    att = FakeAttachment(filename="not_a_db.txt", payload=b"hello")
    assert await mod.is_valid_sqlite_db(att) is False
    assert att.saved_paths == []


@pytest.mark.asyncio
async def test_is_valid_sqlite_db_accepts_valid_db_and_cleans_temp(tmp_path, monkeypatch, mod):
    att = FakeAttachment(filename="backup.DB", payload=b"doesnt matter")

    temp_file = tmp_path / "upload_tmp.db"
    monkeypatch.setattr(mod.tempfile, "NamedTemporaryFile", lambda delete=False: _Tmp(str(temp_file)))

    removed: list[str] = []

    def fake_unlink(self):
        removed.append(str(self))

    monkeypatch.setattr(mod.Path, "unlink", fake_unlink, raising=True)

    # IMPORTANT : patch dans le module under test (mod.sqlite3), pas sqlite3 global
    monkeypatch.setattr(mod.sqlite3, "connect", lambda p: _ConnOK())

    assert await mod.is_valid_sqlite_db(att) is True
    assert att.saved_paths == [str(temp_file)]
    assert removed == [str(temp_file)]


@pytest.mark.asyncio
async def test_is_valid_sqlite_db_rejects_invalid_db_and_cleans_temp(tmp_path, monkeypatch, mod):
    att = FakeAttachment(filename="bad.db", payload=b"this is not sqlite")

    temp_file = tmp_path / "bad_tmp.db"
    monkeypatch.setattr(mod.tempfile, "NamedTemporaryFile", lambda delete=False: _Tmp(str(temp_file)))

    removed: list[str] = []

    def fake_unlink(self):
        removed.append(str(self))

    monkeypatch.setattr(mod.Path, "unlink", fake_unlink, raising=True)

    def bad_connect(p):
        raise mod.sqlite3.DatabaseError("not sqlite")

    monkeypatch.setattr(mod.sqlite3, "connect", bad_connect)

    assert await mod.is_valid_sqlite_db(att) is False
    assert att.saved_paths == [str(temp_file)]
    assert removed == [str(temp_file)]


@pytest.mark.asyncio
async def test_is_valid_sqlite_db_cleanup_retries_on_permission_error(tmp_path, monkeypatch, mod):
    """
    Sous Windows, os.remove peut lever PermissionError si le fichier est encore lock.
    Le code retry et dort un peu. On vérifie qu'il retry sans exploser.
    """
    att = FakeAttachment(filename="ok.db", payload=b"doesnt matter")

    temp_file = tmp_path / "locked_tmp.db"
    monkeypatch.setattr(mod.tempfile, "NamedTemporaryFile", lambda delete=False: _Tmp(str(temp_file)))

    # Conn valide
    monkeypatch.setattr(mod.sqlite3, "connect", lambda p: _ConnOK())

    calls = {"unlink": 0, "sleep": 0}

    def fake_unlink(self):
        calls["unlink"] += 1
        # 2 échecs puis succès
        if calls["unlink"] <= 2:
            raise PermissionError("locked")
        return None

    def fake_sleep(_):
        calls["sleep"] += 1

    monkeypatch.setattr(mod.Path, "unlink", fake_unlink, raising=True)
    monkeypatch.setattr(mod.time, "sleep", fake_sleep)

    assert await mod.is_valid_sqlite_db(att) is True
    assert calls["unlink"] == 3
    assert calls["sleep"] == 2
