import json
from sqlite3 import Row
from typing import Any

from eldoria.db.repo.duel_repo import update_payload_if_unchanged
from eldoria.features.duel._internal.helpers import assert_duel_not_expired, build_snapshot, dump_payload, get_duel_or_raise
from eldoria.features.duel.games.protocol import DuelGame

from ...constants import *
from .rps_constants import *
from .....exceptions.duel_exceptions import *


# ---------------- helpers ------------------
def load_rps_payload(duel) -> dict:
    try:
        payload = duel["payload"]
        if not payload:
            raise ValueError
        return json.loads(payload)
    except Exception:
        return {
            RPS_PAYLOAD_VERSION: 1,
            RPS_PAYLOAD_A_MOVE: None,
            RPS_PAYLOAD_B_MOVE: None
        }

def who_is_moving(duel, user_id):
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]

    if user_id not in (player_a_id, player_b_id):
        raise NotAuthorizedPlayer(user_id=user_id)
    
    if user_id == player_a_id:
        return RPS_PAYLOAD_A_MOVE
    return RPS_PAYLOAD_B_MOVE

def assert_duel_playable(duel: Row, user_id: int) -> bool:
    status = duel["status"]
    if status != DUEL_STATUS_ACTIVE:
        raise DuelNotActive(status)
    
    game_type = duel["game_type"]
    if game_type != GAME_RPS:
        raise WrongGameType(game_type, GAME_RPS)
    
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]

    if user_id not in (player_a_id, player_b_id):
        raise NotAuthorizedPlayer(user_id=user_id)
    return True

def compute_rps_result(a_move: str, b_move: str) -> str:
    if a_move not in RPS_MOVES or b_move not in RPS_MOVES : 
        raise InvalidMove()
    
    if a_move == b_move:
        return DUEL_RESULT_DRAW
    
    if WINS[a_move] == b_move:
        return DUEL_RESULT_WIN_A
    
    else:
        return DUEL_RESULT_WIN_B
    


def _other_slot(player_slot: str) -> str:
    return RPS_PAYLOAD_B_MOVE if player_slot == RPS_PAYLOAD_A_MOVE else RPS_PAYLOAD_A_MOVE


def _apply_move_or_raise(payload: dict[str, Any], player_slot: str, move: str) -> None:
    """Écrit le coup dans le payload, en empêchant un second coup du même joueur."""
    if payload.get(player_slot):
        raise AlreadyPlayed()
    payload[player_slot] = move


def _persist_move_cas(
    duel_id: int,
    player_slot: str,
    move: str,
) -> None:
    """
    Persiste le coup via CAS (compare-and-swap) pour éviter le 'lost update'
    si les 2 joueurs jouent en même temps.

    Stratégie : 2 tentatives max.
    """
    # Tentative 1
    duel = get_duel_or_raise(duel_id)
    old_payload_json = duel["payload"]  # peut être None
    payload = load_rps_payload(duel)
    _apply_move_or_raise(payload, player_slot, move)
    new_payload_json = dump_payload(payload)

    if update_payload_if_unchanged(duel_id, old_payload_json, new_payload_json):
        return

    # Tentative 2 (refetch + rebuild)
    duel = get_duel_or_raise(duel_id)
    old_payload_json = duel["payload"]
    payload = load_rps_payload(duel)
    _apply_move_or_raise(payload, player_slot, move)
    new_payload_json = dump_payload(payload)
    
    if update_payload_if_unchanged(duel_id, old_payload_json, new_payload_json):
        return

    # Si on échoue encore, on abandonne proprement
    raise PayloadError()


def _build_waiting_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        RPS_DICT_STATE: RPS_STATE_WAITING,
        "a_played": payload.get(RPS_PAYLOAD_A_MOVE) is not None,
        "b_played": payload.get(RPS_PAYLOAD_B_MOVE) is not None,
    }


def _build_finished_response(result: str, a_move: str, b_move: str) -> dict[str, Any]:
    return {
        RPS_DICT_STATE: RPS_STATE_FINISHED,
        RPS_DICT_RESULT: result,
        RPS_PAYLOAD_A_MOVE: a_move,
        RPS_PAYLOAD_B_MOVE: b_move,
    }









# ---------------- API publique du jeu ----------------
class RPSGame:
    GAME_KEY = GAME_RPS

    @staticmethod
    def play(duel_id: int, user_id: int, action: dict[str, Any]) -> dict[str, Any]:
        duel = get_duel_or_raise(duel_id)
        assert_duel_not_expired(duel)
        assert_duel_playable(duel, user_id)

        move = action.get("move")
        if move not in RPS_MOVES:
            raise InvalidMove()

        player_slot = who_is_moving(duel, user_id)
        other_slot = _other_slot(player_slot)

        _persist_move_cas(duel_id, player_slot, move)

        duel = get_duel_or_raise(duel_id)
        payload = load_rps_payload(duel)

        other_move = payload.get(other_slot)
        if not other_move:
            return build_snapshot(
                duel_row=duel,
                game_infos=_build_waiting_response(payload),
            )

        a_move = payload.get(RPS_PAYLOAD_A_MOVE)
        b_move = payload.get(RPS_PAYLOAD_B_MOVE)
        if not a_move or not b_move:
            raise PayloadError()

        result = compute_rps_result(a_move, b_move)

        return build_snapshot(
            duel_row=duel,
            game_infos=_build_finished_response(result, a_move, b_move),
        )
    
    @staticmethod
    def is_complete(duel: Row) -> bool:
        payload = load_rps_payload(duel)
        return payload[RPS_PAYLOAD_A_MOVE] is not None and payload[RPS_PAYLOAD_B_MOVE] is not None

    @staticmethod
    def resolve(duel: Row) -> str:
        """
        Suppose que le duel est complet. Retourne WIN_A/WIN_B/DRAW.
        """
        payload = load_rps_payload(duel)
        a_move = payload.get(RPS_PAYLOAD_A_MOVE)
        b_move = payload.get(RPS_PAYLOAD_B_MOVE)
        if not a_move or not b_move:
            raise PayloadError()
        return compute_rps_result(a_move, b_move)

game: DuelGame = RPSGame()