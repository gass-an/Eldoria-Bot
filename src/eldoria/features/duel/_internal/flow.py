from typing import Any

from eldoria.db.connection import get_conn
from eldoria.db.repo.duel_repo import (
    create_duel, 
    get_active_duel_for_user, 
    transition_status, 
    update_duel_if_status, 
    update_payload_if_unchanged
    )
from eldoria.db.repo.xp_repo import xp_get_member
from eldoria.exceptions.duel_exceptions import (
    ConfigurationError, 
    ConfigurationIncomplete,
    DuelAlreadyHandled, 
    DuelNotAcceptable, 
    InsufficientXp, 
    InvalidGameType, 
    InvalidStake, 
    MissingMessageId, 
    NotAuthorizedPlayer, 
    PlayerAlreadyInDuel, 
    SamePlayerDuel
    )
from eldoria.features.duel._internal.helpers import (
    _get_allowed_stakes_from_duel, 
    assert_duel_not_expired, 
    build_snapshot, 
    dump_payload, 
    get_allowed_stakes, 
    get_duel_or_raise, 
    get_xp_for_players, 
    is_configuration_available, 
    load_payload_any, 
    modify_xp_for_players
    )
from eldoria.features.duel.constants import (
    DUEL_STATUS_ACTIVE, 
    DUEL_STATUS_CANCELLED, 
    DUEL_STATUS_CONFIG, 
    DUEL_STATUS_INVITED, 
    GAME_TYPES, 
    STAKE_XP_DEFAULTS
    )
from eldoria.utils.timestamp import add_duration, now_ts


def new_duel(guild_id: int, channel_id: int, player_a_id: int, player_b_id: int) -> dict[str, Any]:
    if player_a_id == player_b_id:
        raise SamePlayerDuel(player_a_id, player_b_id)
    
    if (get_active_duel_for_user(guild_id, player_a_id) or get_active_duel_for_user(guild_id, player_b_id)):
        raise PlayerAlreadyInDuel()
    created_at = now_ts()
    expires_at = add_duration(created_at, minutes=10)

    duel_id = create_duel(guild_id, channel_id, player_a_id, player_b_id, created_at, expires_at)
    duel = get_duel_or_raise(duel_id)
    return build_snapshot(duel_row=duel)



def configure_game_type(duel_id: int, game_type: str) -> dict[str, Any]:
    duel = get_duel_or_raise(duel_id)
    assert_duel_not_expired(duel)

    if game_type not in GAME_TYPES:
        raise InvalidGameType(game_type)
    
    if not update_duel_if_status(duel_id, required_status=DUEL_STATUS_CONFIG, game_type=game_type):
        raise ConfigurationError()
    
    duel = get_duel_or_raise(duel_id)
    allowed_stakes = _get_allowed_stakes_from_duel(duel)
    return build_snapshot(duel_row=duel, allowed_stakes=allowed_stakes)


def configure_stake_xp(duel_id: int, stake_xp: int) -> dict[str, Any]:
    duel = get_duel_or_raise(duel_id)
    assert_duel_not_expired(duel)
    
    if stake_xp not in STAKE_XP_DEFAULTS:
        raise InvalidStake(stake_xp)

    if stake_xp not in get_allowed_stakes(duel_id): 
        raise InsufficientXp(stake_xp)
    
    if not update_duel_if_status(duel_id, required_status=DUEL_STATUS_CONFIG, stake_xp=stake_xp):
        raise ConfigurationError()
    
    duel = get_duel_or_raise(duel_id)
    return build_snapshot(duel_row=duel)





def send_invite(duel_id: int, message_id: int) ->  dict[str, Any]:
    duel = get_duel_or_raise(duel_id)
    assert_duel_not_expired(duel)
    
    if not is_configuration_available(duel_id):
        raise ConfigurationIncomplete()

    if not message_id:
        raise MissingMessageId()

    if not update_duel_if_status(duel_id, required_status=DUEL_STATUS_CONFIG, message_id=message_id):
        raise ConfigurationError()
    
    invite_expires_at = add_duration(now_ts(), minutes=5)
    if not  transition_status(duel_id, from_status=DUEL_STATUS_CONFIG, to_status=DUEL_STATUS_INVITED, expires_at=invite_expires_at):
        raise DuelAlreadyHandled(duel_id, DUEL_STATUS_CONFIG)
    
    duel = get_duel_or_raise(duel_id)
    guild_id = duel["guild_id"]
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]
    xp_dict = get_xp_for_players(guild_id, player_a_id, player_b_id)
    return build_snapshot(duel_row=duel, xp=xp_dict)





def accept_duel(duel_id: int, user_id: int)-> dict[str, Any]:
    duel = get_duel_or_raise(duel_id)
    assert_duel_not_expired(duel)
    
    player_b_id = duel["player_b_id"]
    if (player_b_id != user_id):
        raise NotAuthorizedPlayer(user_id=user_id)
    
    status = duel["status"]
    if status != DUEL_STATUS_INVITED:
        raise DuelNotAcceptable(status)
    
    stake_xp = duel["stake_xp"]
    if stake_xp not in _get_allowed_stakes_from_duel(duel):
        raise InsufficientXp(required=stake_xp)
    
    active_expires_at = add_duration(now_ts(), minutes=10)

    guild_id = duel["guild_id"]
    player_a_id = duel["player_a_id"]

    # Transaction: status + xp dans la même connexion
    with get_conn() as conn:
        if not transition_status(
            duel_id,
            from_status=DUEL_STATUS_INVITED,
            to_status=DUEL_STATUS_ACTIVE,
            expires_at=active_expires_at,
            conn=conn,
        ):
            raise DuelAlreadyHandled(duel_id, DUEL_STATUS_INVITED)

        payload = load_payload_any(duel)
        if "xp_baseline" not in payload:
            xp_a = xp_get_member(guild_id, player_a_id, conn=conn)[0]
            xp_b = xp_get_member(guild_id, player_b_id, conn=conn)[0]
            payload["xp_baseline"] = {"player_a_before_xp": xp_a, "player_b_before_xp": xp_b}

            old_payload_json = duel["payload"]  # peut être None
            new_payload_json = dump_payload(payload)

            update_payload_if_unchanged(duel_id, old_payload_json, new_payload_json, conn=conn)

        modify_xp_for_players(
            guild_id,
            player_a_id,
            player_b_id,
            -stake_xp,
            conn=conn,
        )
    
    duel = get_duel_or_raise(duel_id)
    return build_snapshot(duel_row=duel)


def refuse_duel(duel_id: int, user_id: int) -> dict[str, Any]:
    duel = get_duel_or_raise(duel_id)
    assert_duel_not_expired(duel)
    
    player_b_id = duel["player_b_id"]
    if (player_b_id != user_id):
        raise NotAuthorizedPlayer(user_id=user_id)
    
    status = duel["status"]
    if status != DUEL_STATUS_INVITED:
        raise DuelNotAcceptable(status)

    with get_conn() as conn:
        if not transition_status(
            duel_id,
            from_status=DUEL_STATUS_INVITED,
            to_status=DUEL_STATUS_CANCELLED,
            expires_at=None,
            conn=conn,
        ):
            raise DuelAlreadyHandled(duel_id, DUEL_STATUS_INVITED)

        update_duel_if_status(
            duel_id,
            required_status=DUEL_STATUS_CANCELLED,
            finished_at=now_ts(),
            conn=conn,
        )
    duel = get_duel_or_raise(duel_id)
    return build_snapshot(duel_row=duel)    
