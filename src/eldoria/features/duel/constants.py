from typing import Final

STAKE_XP_DEFAULTS: Final[list[int]] = [
    5,
    10,
    50,
    100
]

# Game Status
DUEL_STATUS_CONFIG: Final[str] = "CONFIG"
DUEL_STATUS_INVITED: Final[str] = "INVITED"
DUEL_STATUS_ACTIVE: Final[str] = "ACTIVE"
DUEL_STATUS_FINISHED: Final[str] = "FINISHED"
DUEL_STATUS_CANCELLED: Final[str] = "CANCELLED"
DUEL_STATUS_EXPIRED: Final[str] = "EXPIRED"

DUEL_STATUS: Final[list[str]] = [
    DUEL_STATUS_CONFIG,
    DUEL_STATUS_INVITED,
    DUEL_STATUS_ACTIVE,
    DUEL_STATUS_FINISHED,
    DUEL_STATUS_CANCELLED,
    DUEL_STATUS_EXPIRED
]

# Game type
GAME_RPS: Final[str] = "RPS" # Rock-Papers-Scissors

GAME_TYPES: Final[list[str]] = [
    GAME_RPS
]

# Results
DUEL_RESULT_WIN_A: Final[str] = "WIN_A"
DUEL_RESULT_WIN_B: Final[str] = "WIN_B"
DUEL_RESULT_DRAW: Final[str] = "DRAW"

DUEL_RESULTS: Final[list[str]] = [
    DUEL_RESULT_WIN_A,
    DUEL_RESULT_WIN_B,
    DUEL_RESULT_DRAW
]


KEEP_EXPIRED_DAYS: Final[int] = 3
KEEP_FINISHED_DAYS: Final[int] = 30
