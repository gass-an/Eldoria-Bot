from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture(autouse=True)
def sqlite_in_memory(monkeypatch):
    real_connect = sqlite3.connect

    def guarded_connect(path, *a, **k):
        if isinstance(path, str):
            normalized = path.replace("\\", "/")
            if normalized.endswith("/data/eldoria.db") or normalized.endswith("data/eldoria.db"):
                return real_connect(":memory:")
        return real_connect(path, *a, **k)

    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
