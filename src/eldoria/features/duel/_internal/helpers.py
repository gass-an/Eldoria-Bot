from sqlite3 import Row
from typing import cast
import json

from typing import Any

from eldoria.db.connection import get_conn
from eldoria.db.repo.duel_repo import get_duel_by_id, transition_status, update_duel_if_status
from eldoria.db.repo.xp_repo import xp_add_xp, xp_get_member
from eldoria.exceptions.duel_exceptions import DuelAlreadyHandled, DuelNotFinishable, DuelNotFinished, DuelNotFound, ExpiredDuel, InvalidResult, WrongGameType
from eldoria.features.duel import constants
from eldoria.features.duel.constants import DUEL_RESULTS, DUEL_STATUS_ACTIVE, DUEL_STATUS_CONFIG, DUEL_STATUS_FINISHED, GAME_TYPES, STAKE_XP_DEFAULTS

from eldoria.utils.timestamp import now_ts


def finish_duel(duel_id: int, result: str, *, ignore_expired: bool=False):
    duel = get_duel_or_raise(duel_id)
    if not ignore_expired:
        assert_duel_not_expired(duel)
    
    if result not in DUEL_RESULTS:
        raise InvalidResult(result)
    
    status = duel["status"]
    if status != DUEL_STATUS_ACTIVE:
        raise DuelNotFinishable(status)
    
    guild_id = duel["guild_id"]
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]
    stake_xp = duel["stake_xp"]

    # Transaction: status + payout + finished_at dans la même connexion
    with get_conn() as conn:
        if not transition_status(
            duel_id,
            from_status=DUEL_STATUS_ACTIVE,
            to_status=DUEL_STATUS_FINISHED,
            expires_at=None,
            conn=conn,
        ):
            raise DuelAlreadyHandled(duel_id, DUEL_STATUS_ACTIVE)

        match result:
            case constants.DUEL_RESULT_DRAW:
                modify_xp_for_players(guild_id, player_a_id, player_b_id, stake_xp, conn=conn)

            case constants.DUEL_RESULT_WIN_A:
                xp_add_xp(guild_id, player_a_id, 2 * stake_xp, conn=conn)

            case constants.DUEL_RESULT_WIN_B:
                xp_add_xp(guild_id, player_b_id, 2 * stake_xp, conn=conn)

            case _:
                raise InvalidResult(result)

        if not update_duel_if_status(
            duel_id,
            required_status=DUEL_STATUS_FINISHED,
            finished_at=now_ts(),
            conn=conn,
        ):
            raise DuelNotFinished(duel_id, DUEL_STATUS_FINISHED)
        




def load_payload_any(duel: Row) -> dict[str, Any]:
    try:
        raw = duel["payload"]
        if not raw:
            return {}
        return cast(dict[str, Any], json.loads(raw))
    except Exception:
        return {}

def dump_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"))



def _get_allowed_stakes_from_duel(duel: Row) -> list[int]:
    if not duel:
        return []
    
    guild_id = duel["guild_id"]
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]

    player_a_xp = xp_get_member(guild_id, player_a_id)[0]
    player_b_xp = xp_get_member(guild_id, player_b_id)[0]

    return [stake_xp 
            for stake_xp in STAKE_XP_DEFAULTS 
            if (player_a_xp >= stake_xp and player_b_xp >= stake_xp)
    ]

def get_allowed_stakes(duel_id: int) -> list[int]:
    duel = get_duel_by_id(duel_id)
    return _get_allowed_stakes_from_duel(duel)
    

def is_configuration_available(duel_id: int) -> bool:
    duel = get_duel_by_id(duel_id)
    if not duel:
        return False
    
    game_type = duel["game_type"]
    stake_xp = duel["stake_xp"]
    status = duel["status"]

    return (
        game_type in GAME_TYPES and 
        stake_xp in _get_allowed_stakes_from_duel(duel) and 
        status == DUEL_STATUS_CONFIG
    )

def modify_xp_for_players(
    guild_id: int,
    player_a_id: int,
    player_b_id: int,
    xp: int,
    *,
    conn=None,
) -> dict[int, int]:
    """Modifie l'XP des 2 joueurs et retourne {user_id: new_xp}."""
    new_xp_player_a = xp_add_xp(guild_id, player_a_id, xp, conn=conn)
    new_xp_player_b = xp_add_xp(guild_id, player_b_id, xp, conn=conn)
    return {player_a_id: new_xp_player_a, player_b_id: new_xp_player_b}


def assert_duel_not_expired(duel: Row): 
    expires_at = duel["expires_at"]
    if expires_at is not None and expires_at <= now_ts():
        raise ExpiredDuel(duel["duel_id"])
    
def get_duel_or_raise(duel_id: int) -> Row:
    duel = get_duel_by_id(duel_id)
    if not duel:
        raise DuelNotFound(duel_id)
    return duel

def get_xp_for_players(guild_id: int, player_a_id: int, player_b_id: int, *,conn=None) -> dict[int, int]:
        player_a_xp = xp_get_member(guild_id, player_a_id, conn=conn)[0]
        player_b_xp = xp_get_member(guild_id, player_b_id, conn=conn)[0]
        return {player_a_id: player_a_xp, player_b_id: player_b_xp}

def build_snapshot(duel_row: Row, 
                   *, 
                   allowed_stakes: list[int] | None = None, 
                   xp: dict[int, int] | None = None, 
                   game_infos: dict[str, Any] | None = None, 
                   effects: dict[str, Any] | None = None
                   ) -> dict[str, Any]:
    id = duel_row["duel_id"]
    channel_id = duel_row["channel_id"]
    message_id = duel_row["message_id"]
    status = duel_row["status"]
    player_a = duel_row["player_a_id"]
    player_b = duel_row["player_b_id"]
    game_type = duel_row["game_type"]
    stake_xp = duel_row["stake_xp"]
    expires_at = duel_row["expires_at"]

    result = {
        "duel" : {
            "id" : id,
            "channel_id" : channel_id,
            "message_id" : message_id,
            "status" : status,
            "player_a" : player_a,
            "player_b" : player_b,
            "game_type" : game_type,
            "stake_xp" : stake_xp,
            "expires_at" : expires_at
        }
    }

    if allowed_stakes is not None:
        result["ui"] = {"allowed_stakes": allowed_stakes}

    if xp is not None:
        result["xp"] = cast(dict[str, Any], xp)

    if game_infos is not None:
        result["game"] = game_infos

    if effects is not None:
        result["effects"] = effects
    return result