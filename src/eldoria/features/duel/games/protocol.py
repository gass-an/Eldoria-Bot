from __future__ import annotations

from sqlite3 import Row
from typing import Any, Protocol


class DuelGame(Protocol):
    GAME_KEY: str  # ex "RPS"

    def play(self, duel_id: int, user_id: int, action: dict[str, Any]) -> dict[str, Any]: ...
    def is_complete(self, duel: Row) -> bool: ...
    def resolve(self, duel: Row) -> str: ...