from .rps.rps import game as rps_game
from .registry import register_game

def init_games() -> None:
    register_game(rps_game)