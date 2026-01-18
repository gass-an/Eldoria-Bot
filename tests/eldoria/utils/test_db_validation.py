import os
import tempfile
import importlib
import pytest


class FakeAttachment:
    def __init__(self, *, filename: str, payload: bytes):
        self.filename = filename
        self._payload = payload
        self.saved_paths = []

    async def save(self, path: str):
        self.saved_paths.append(path)
        with open(path, "wb") as f:
            f.write(self._payload)


class _Tmp:
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


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


class _ConnBad:
    def execute(self, sql):
        raise RuntimeError("should not be called")

    def close(self):
        pass


@pytest.fixture
def mod():
    # on importe le module pour pouvoir monkeypatch SES dépendances (sqlite3/os/tempfile)
    m = importlib.import_module("eldoria.utils.db_validation")
    importlib.reload(m)
    return m


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

    removed = []
    monkeypatch.setattr(mod.os, "remove", lambda p: removed.append(p))

    # IMPORTANT: patch dans le module under test, pas sqlite3 global
    monkeypatch.setattr(mod.sqlite3, "connect", lambda p: _ConnOK())

    assert await mod.is_valid_sqlite_db(att) is True
    assert att.saved_paths == [str(temp_file)]
    assert removed == [str(temp_file)]


@pytest.mark.asyncio
async def test_is_valid_sqlite_db_rejects_invalid_db_and_cleans_temp(tmp_path, monkeypatch, mod):
    att = FakeAttachment(filename="bad.db", payload=b"this is not sqlite")

    temp_file = tmp_path / "bad_tmp.db"
    monkeypatch.setattr(mod.tempfile, "NamedTemporaryFile", lambda delete=False: _Tmp(str(temp_file)))

    removed = []
    monkeypatch.setattr(mod.os, "remove", lambda p: removed.append(p))

    def bad_connect(p):
        raise mod.sqlite3.DatabaseError("not sqlite")

    monkeypatch.setattr(mod.sqlite3, "connect", bad_connect)

    assert await mod.is_valid_sqlite_db(att) is False
    assert att.saved_paths == [str(temp_file)]
    assert removed == [str(temp_file)]
