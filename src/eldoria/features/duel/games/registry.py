from typing import Dict
from .protocol import DuelGame

_REGISTRY: Dict[str, DuelGame] = {}

def register_game(game: DuelGame) -> None:
    _REGISTRY[game.GAME_KEY] = game

def get_game(game_key: str) -> DuelGame | None:
    return _REGISTRY.get(game_key)

def require_game(game_key: str) -> DuelGame:
    g = get_game(game_key)
    if not g:
        raise ValueError(f"Game not registered: {game_key}")
    return g