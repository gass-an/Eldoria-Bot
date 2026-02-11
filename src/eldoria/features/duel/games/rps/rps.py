"""Implémentation du jeu de pierre-papier-ciseaux pour les duels de type RPS, conforme à l'interface DuelGame."""

import json
from sqlite3 import Row
from typing import Any

from eldoria.db.repo.duel_repo import update_payload_if_unchanged
from eldoria.exceptions import duel_exceptions as exc
from eldoria.features.duel import constants
from eldoria.features.duel._internal import helpers
from eldoria.features.duel.games.protocol import DuelGame
from eldoria.features.duel.games.rps import rps_constants as rps


# ---------------- helpers ------------------
def load_rps_payload(duel: Row) -> dict:
    """Charge le payload du duel et retourne un dictionnaire avec les coups joués par les joueurs, ou des valeurs par défaut si le payload est absent ou mal formé."""
    try:
        payload = duel["payload"]
        if not payload:
            raise ValueError
        return json.loads(payload)
    except Exception:
        return {
            rps.RPS_PAYLOAD_VERSION: 1,
            rps.RPS_PAYLOAD_A_MOVE: None,
            rps.RPS_PAYLOAD_B_MOVE: None
        }

def who_is_moving(duel: Row, user_id: int) -> str:
    """Détermine si l'utilisateur est le joueur A ou le joueur B dans le duel.
    
    Retourne la clé de slot correspondante pour le payload (RPS_PAYLOAD_A_MOVE ou RPS_PAYLOAD_B_MOVE). 
    Lève une exception si l'utilisateur n'est pas impliqué dans le duel.
    """
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]

    if user_id not in (player_a_id, player_b_id):
        raise exc.NotAuthorizedPlayer(user_id=user_id)
    
    if user_id == player_a_id:
        return rps.RPS_PAYLOAD_A_MOVE
    return rps.RPS_PAYLOAD_B_MOVE

def assert_duel_playable(duel: Row, user_id: int) -> bool:
    """Vérifie que le duel est dans un état permettant de jouer, que le jeu est bien RPS, et que l'utilisateur est bien un des deux joueurs impliqués.
    
    Lève une exception si une de ces conditions n'est pas remplie.
    """
    status = duel["status"]
    if status != constants.DUEL_STATUS_ACTIVE:
        raise exc.DuelNotActive(status)
    
    game_type = duel["game_type"]
    if game_type != constants.GAME_RPS:
        raise exc.WrongGameType(game_type, constants.GAME_RPS)
    
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]

    if user_id not in (player_a_id, player_b_id):
        raise exc.NotAuthorizedPlayer(user_id=user_id)
    return True

def compute_rps_result(a_move: str, b_move: str) -> str:
    """Calcule le résultat du duel de pierre-papier-ciseaux en fonction des coups joués par les joueurs A et B."""
    if a_move not in rps.RPS_MOVES or b_move not in rps.RPS_MOVES : 
        raise exc.InvalidMove()
    
    if a_move == b_move:
        return constants.DUEL_RESULT_DRAW
    
    if rps.WINS[a_move] == b_move:
        return constants.DUEL_RESULT_WIN_A
    
    else:
        return constants.DUEL_RESULT_WIN_B
    


def _other_slot(player_slot: str) -> str:
    return rps.RPS_PAYLOAD_B_MOVE if player_slot == rps.RPS_PAYLOAD_A_MOVE else rps.RPS_PAYLOAD_A_MOVE


def _apply_move_or_raise(payload: dict[str, Any], player_slot: str, move: str) -> None:
    """Écrit le coup dans le payload, en empêchant un second coup du même joueur."""
    if payload.get(player_slot):
        raise exc.AlreadyPlayed()
    payload[player_slot] = move


def _persist_move_cas(
    duel_id: int,
    player_slot: str,
    move: str,
) -> None:
    """Persiste le coup via CAS (compare-and-swap) pour éviter le 'lost update' si les 2 joueurs jouent en même temps.

    Stratégie : 2 tentatives max.
    """
    # Tentative 1
    duel = helpers.get_duel_or_raise(duel_id)
    old_payload_json = duel["payload"]  # peut être None
    payload = load_rps_payload(duel)
    _apply_move_or_raise(payload, player_slot, move)
    new_payload_json = helpers.dump_payload(payload)

    if update_payload_if_unchanged(duel_id, old_payload_json, new_payload_json):
        return

    # Tentative 2 (refetch + rebuild)
    duel = helpers.get_duel_or_raise(duel_id)
    old_payload_json = duel["payload"]
    payload = load_rps_payload(duel)
    _apply_move_or_raise(payload, player_slot, move)
    new_payload_json = helpers.dump_payload(payload)
    
    if update_payload_if_unchanged(duel_id, old_payload_json, new_payload_json):
        return

    # Si on échoue encore, on abandonne proprement
    raise exc.PayloadError()


def _build_waiting_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        rps.RPS_DICT_STATE: rps.RPS_STATE_WAITING,
        "a_played": payload.get(rps.RPS_PAYLOAD_A_MOVE) is not None,
        "b_played": payload.get(rps.RPS_PAYLOAD_B_MOVE) is not None,
    }


def _build_finished_response(result: str, a_move: str, b_move: str) -> dict[str, Any]:
    return {
        rps.RPS_DICT_STATE: rps.RPS_STATE_FINISHED,
        rps.RPS_DICT_RESULT: result,
        rps.RPS_PAYLOAD_A_MOVE: a_move,
        rps.RPS_PAYLOAD_B_MOVE: b_move,
    }









# ---------------- API publique du jeu ----------------
class RPSGame:
    """Implémentation du jeu de pierre-papier-ciseaux pour les duels de type RPS, conforme à l'interface DuelGame."""

    GAME_KEY = constants.GAME_RPS

    @staticmethod
    def play(duel_id: int, user_id: int, action: dict[str, Any]) -> dict[str, Any]:
        """Traite une action de jeu (coup joué) pour un duel de type RPS, met à jour le duel en conséquence.
        
        Retourne un snapshot du duel avec les informations de jeu mises à jour.
        Si le coup joué fait que le duel est terminé, met également à jour le statut du duel et les XP des joueurs.
        """
        duel = helpers.get_duel_or_raise(duel_id)
        helpers.assert_duel_not_expired(duel)
        assert_duel_playable(duel, user_id)

        move = action.get("move")
        if move not in rps.RPS_MOVES:
            raise exc.InvalidMove()

        player_slot = who_is_moving(duel, user_id)
        other_slot = _other_slot(player_slot)

        _persist_move_cas(duel_id, player_slot, move)

        duel = helpers.get_duel_or_raise(duel_id)
        payload = load_rps_payload(duel)

        other_move = payload.get(other_slot)
        if not other_move:
            return helpers.build_snapshot(
                duel_row=duel,
                game_infos=_build_waiting_response(payload),
            )

        a_move = payload.get(rps.RPS_PAYLOAD_A_MOVE)
        b_move = payload.get(rps.RPS_PAYLOAD_B_MOVE)
        if not a_move or not b_move:
            raise exc.PayloadError()

        result = compute_rps_result(a_move, b_move)

        return helpers.build_snapshot(
            duel_row=duel,
            game_infos=_build_finished_response(result, a_move, b_move),
        )
    
    @staticmethod
    def is_complete(duel: Row) -> bool:
        """Retourne True si le duel est dans un état considéré comme "complet" pour le jeu de RPS.
        
        C'est à dire que les 2 joueurs ont joué leur coup et que le résultat peut être déterminé.
        """
        payload = load_rps_payload(duel)
        return payload[rps.RPS_PAYLOAD_A_MOVE] is not None and payload[rps.RPS_PAYLOAD_B_MOVE] is not None

    @staticmethod
    def resolve(duel: Row) -> str:
        """Suppose que le duel est complet. Retourne WIN_A/WIN_B/DRAW."""
        payload = load_rps_payload(duel)
        a_move = payload.get(rps.RPS_PAYLOAD_A_MOVE)
        b_move = payload.get(rps.RPS_PAYLOAD_B_MOVE)
        if not a_move or not b_move:
            raise exc.PayloadError()
        return compute_rps_result(a_move, b_move)

game: DuelGame = RPSGame()