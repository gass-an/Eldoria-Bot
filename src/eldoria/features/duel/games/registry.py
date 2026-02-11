"""Module de gestion des jeux de duel. Permet d'enregistrer et de récupérer les différentes implémentations de jeux de duel disponibles dans le système."""

from eldoria.features.duel.games.protocol import DuelGame

_REGISTRY: dict[str, DuelGame] = {}

def register_game(game: DuelGame) -> None:
    """Enregistre un jeu de duel auprès du système, en utilisant sa clé unique définie dans l'attribut GAME_KEY."""
    _REGISTRY[game.GAME_KEY] = game

def get_game(game_key: str) -> DuelGame | None:
    """Retourne l'instance du jeu de duel correspondant à la clé spécifiée, ou None si aucun jeu n'est enregistré avec cette clé."""
    return _REGISTRY.get(game_key)

def require_game(game_key: str) -> DuelGame:
    """Retourne l'instance du jeu de duel correspondant à la clé spécifiée. Lève une exception si aucun jeu n'est enregistré avec cette clé."""
    g = get_game(game_key)
    if not g:
        raise ValueError(f"Game not registered: {game_key}")
    return g