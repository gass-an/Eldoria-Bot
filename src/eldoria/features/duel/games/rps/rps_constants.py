from typing import Final


RPS_MOVE_ROCK: Final[str] = "ROCK"
RPS_MOVE_PAPER: Final[str] = "PAPER"
RPS_MOVE_SCISSORS: Final[str] = "SCISSORS"

RPS_MOVES: Final[list[str]] = [
    RPS_MOVE_ROCK,
    RPS_MOVE_PAPER,
    RPS_MOVE_SCISSORS,
]

WINS: Final[dict[str, str]] = {
    RPS_MOVE_ROCK: RPS_MOVE_SCISSORS, 
    RPS_MOVE_SCISSORS: RPS_MOVE_PAPER, 
    RPS_MOVE_PAPER: RPS_MOVE_ROCK
}

RPS_PAYLOAD_VERSION: Final[str] = "rps_version"
RPS_PAYLOAD_A_MOVE: Final[str] = "a_move"
RPS_PAYLOAD_B_MOVE: Final[str] = "b_move"

RPS_DICT_STATE: Final[str] = "state"
RPS_DICT_RESULT: Final[str] = "result"

RPS_STATE_WAITING: Final[str] = "WAITING"
RPS_STATE_FINISHED: Final[str] = "FINISHED"