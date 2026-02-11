"""Module d'initialisation des jeux de duel. C'est ici que les différents jeux sont enregistrés auprès du système de duels."""
from eldoria.features.duel.games.registry import register_game
from eldoria.features.duel.games.rps.rps import game as rps_game


def init_games() -> None:
    """Enregistre tous les jeux de duel disponibles."""
    register_game(rps_game)