from __future__ import annotations

import eldoria.features.save.save_service as save_service_mod


def test_get_db_path_returns_connection_db_path(monkeypatch):
    svc = save_service_mod.SaveService()

    monkeypatch.setattr(
        save_service_mod.connection,
        "DB_PATH",
        "/fake/path/db.sqlite",
    )

    assert svc.get_db_path() == "/fake/path/db.sqlite"


def test_backup_to_file_delegates_to_maintenance(monkeypatch):
    svc = save_service_mod.SaveService()

    called = {}

    def fake_backup(dst_path):
        called["dst"] = dst_path

    monkeypatch.setattr(
        save_service_mod.maintenance,
        "backup_to_file",
        fake_backup,
    )

    svc.backup_to_file("/tmp/backup.sqlite")

    assert called["dst"] == "/tmp/backup.sqlite"


def test_replace_db_file_delegates_to_maintenance(monkeypatch):
    svc = save_service_mod.SaveService()

    called = {}

    def fake_replace(path):
        called["path"] = path

    monkeypatch.setattr(
        save_service_mod.maintenance,
        "replace_db_file",
        fake_replace,
    )

    svc.replace_db_file("/tmp/new.sqlite")

    assert called["path"] == "/tmp/new.sqlite"


def test_init_db_delegates_to_schema(monkeypatch):
    svc = save_service_mod.SaveService()

    called = {"n": 0}

    def fake_init():
        called["n"] += 1

    monkeypatch.setattr(
        save_service_mod.schema,
        "init_db",
        fake_init,
    )

    svc.init_db()

    assert called["n"] == 1
