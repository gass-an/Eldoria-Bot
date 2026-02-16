from __future__ import annotations

from typing import Any


class FakeCursor:
    """Cursor minimaliste pour les repos (fetchone/fetchall/lastrowid)."""

    def __init__(self, *, one: Any = None, all: Any = None, lastrowid: Any = None):
        self._one = one
        self._all = all
        self.lastrowid = lastrowid

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakeConn:
    """Connexion minimaliste pour les tests de repos.

    - Enregistre les appels à execute dans `calls`
    - Permet de configurer le prochain cursor via `set_next`
    """

    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self._next = FakeCursor(one=None, all=[])

    # Compat totale avec tes tests existants
    def set_next_cursor(self, cursor: FakeCursor):
        self._next = cursor

    # Optionnel mais pratique
    def set_next(self, *, one=None, all=None, lastrowid=None):
        self._next = FakeCursor(one=one, all=all, lastrowid=lastrowid)

    def execute(self, sql: str, params: tuple = ()):
        self.calls.append((sql.strip(), params))
        return self._next


class FakeConnCM:
    """Context manager qui renvoie une FakeConn."""

    def __init__(self, conn: FakeConn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False
