from eldoria.features.duel.games.registry import register_game
from eldoria.features.duel.games.rps.rps import game as rps_game


def init_games() -> None:
    register_game(rps_game)