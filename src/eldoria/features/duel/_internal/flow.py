from typing import Any

from eldoria.db.connection import get_conn
from eldoria.db.repo import duel_repo
from eldoria.db.repo.xp_repo import xp_get_member
from eldoria.exceptions import duel_exceptions as exc
from eldoria.features.duel import constants
from eldoria.features.duel._internal import helpers
from eldoria.utils.timestamp import add_duration, now_ts


def new_duel(guild_id: int, channel_id: int, player_a_id: int, player_b_id: int) -> dict[str, Any]:
    if player_a_id == player_b_id:
        raise exc.SamePlayerDuel(player_a_id, player_b_id)
    
    if (duel_repo.get_active_duel_for_user(guild_id, player_a_id) or duel_repo.get_active_duel_for_user(guild_id, player_b_id)):
        raise exc.PlayerAlreadyInDuel()
    created_at = now_ts()
    expires_at = add_duration(created_at, minutes=10)

    duel_id = duel_repo.create_duel(guild_id, channel_id, player_a_id, player_b_id, created_at, expires_at)
    duel = helpers.get_duel_or_raise(duel_id)
    return helpers.build_snapshot(duel_row=duel)



def configure_game_type(duel_id: int, game_type: str) -> dict[str, Any]:
    duel = helpers.get_duel_or_raise(duel_id)
    helpers.assert_duel_not_expired(duel)

    if game_type not in constants.GAME_TYPES:
        raise exc.InvalidGameType(game_type)
    
    if not duel_repo.update_duel_if_status(duel_id, required_status=constants.DUEL_STATUS_CONFIG, game_type=game_type):
        raise exc.ConfigurationError()
    
    duel = helpers.get_duel_or_raise(duel_id)
    allowed_stakes = helpers._get_allowed_stakes_from_duel(duel)
    return helpers.build_snapshot(duel_row=duel, allowed_stakes=allowed_stakes)


def configure_stake_xp(duel_id: int, stake_xp: int) -> dict[str, Any]:
    duel = helpers.get_duel_or_raise(duel_id)
    helpers.assert_duel_not_expired(duel)
    
    if stake_xp not in constants.STAKE_XP_DEFAULTS:
        raise exc.InvalidStake(stake_xp)

    if stake_xp not in helpers.get_allowed_stakes(duel_id): 
        raise exc.InsufficientXp(stake_xp)
    
    if not duel_repo.update_duel_if_status(duel_id, required_status=constants.DUEL_STATUS_CONFIG, stake_xp=stake_xp):
        raise exc.ConfigurationError()
    
    duel = helpers.get_duel_or_raise(duel_id)
    return helpers.build_snapshot(duel_row=duel)





def send_invite(duel_id: int, message_id: int) ->  dict[str, Any]:
    duel = helpers.get_duel_or_raise(duel_id)
    helpers.assert_duel_not_expired(duel)
    
    if not helpers.is_configuration_available(duel_id):
        raise exc.ConfigurationIncomplete()

    if not message_id:
        raise exc.MissingMessageId()

    if not duel_repo.update_duel_if_status(duel_id, required_status=constants.DUEL_STATUS_CONFIG, message_id=message_id):
        raise exc.ConfigurationError()
    
    invite_expires_at = add_duration(now_ts(), minutes=5)
    if not duel_repo.transition_status(duel_id, from_status=constants.DUEL_STATUS_CONFIG, to_status=constants.DUEL_STATUS_INVITED, expires_at=invite_expires_at):
        raise exc.DuelAlreadyHandled(duel_id, constants.DUEL_STATUS_CONFIG)
    
    duel = helpers.get_duel_or_raise(duel_id)
    guild_id = duel["guild_id"]
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]
    xp_dict = helpers.get_xp_for_players(guild_id, player_a_id, player_b_id)
    return helpers.build_snapshot(duel_row=duel, xp=xp_dict)





def accept_duel(duel_id: int, user_id: int)-> dict[str, Any]:
    duel = helpers.get_duel_or_raise(duel_id)
    helpers.assert_duel_not_expired(duel)
    
    player_b_id = duel["player_b_id"]
    if (player_b_id != user_id):
        raise exc.NotAuthorizedPlayer(user_id=user_id)
    
    status = duel["status"]
    if status != constants.DUEL_STATUS_INVITED:
        raise exc.DuelNotAcceptable(status)
    
    stake_xp = duel["stake_xp"]
    if stake_xp not in helpers._get_allowed_stakes_from_duel(duel):
        raise exc.InsufficientXp(required=stake_xp)
    
    active_expires_at = add_duration(now_ts(), minutes=10)

    guild_id = duel["guild_id"]
    player_a_id = duel["player_a_id"]

    # Transaction: status + xp dans la même connexion
    with get_conn() as conn:
        if not duel_repo.transition_status(
            duel_id,
            from_status=constants.DUEL_STATUS_INVITED,
            to_status=constants.DUEL_STATUS_ACTIVE,
            expires_at=active_expires_at,
            conn=conn,
        ):
            raise exc.DuelAlreadyHandled(duel_id, constants.DUEL_STATUS_INVITED)

        payload = helpers.load_payload_any(duel)
        if "xp_baseline" not in payload:
            xp_a = xp_get_member(guild_id, player_a_id, conn=conn)[0]
            xp_b = xp_get_member(guild_id, player_b_id, conn=conn)[0]
            payload["xp_baseline"] = {"player_a_before_xp": xp_a, "player_b_before_xp": xp_b}

            old_payload_json = duel["payload"]  # peut être None
            new_payload_json = helpers.dump_payload(payload)

            duel_repo.update_payload_if_unchanged(duel_id, old_payload_json, new_payload_json, conn=conn)

        helpers.modify_xp_for_players(
            guild_id,
            player_a_id,
            player_b_id,
            -stake_xp,
            conn=conn,
        )
    
    duel = helpers.get_duel_or_raise(duel_id)
    return helpers.build_snapshot(duel_row=duel)


def refuse_duel(duel_id: int, user_id: int) -> dict[str, Any]:
    duel = helpers.get_duel_or_raise(duel_id)
    helpers.assert_duel_not_expired(duel)
    
    player_b_id = duel["player_b_id"]
    if (player_b_id != user_id):
        raise exc.NotAuthorizedPlayer(user_id=user_id)
    
    status = duel["status"]
    if status != constants.DUEL_STATUS_INVITED:
        raise exc.DuelNotAcceptable(status)

    with get_conn() as conn:
        if not duel_repo.transition_status(
            duel_id,
            from_status=constants.DUEL_STATUS_INVITED,
            to_status=constants.DUEL_STATUS_CANCELLED,
            expires_at=None,
            conn=conn,
        ):
            raise exc.DuelAlreadyHandled(duel_id, constants.DUEL_STATUS_INVITED)

        duel_repo.update_duel_if_status(
            duel_id,
            required_status=constants.DUEL_STATUS_CANCELLED,
            finished_at=now_ts(),
            conn=conn,
        )
    duel = helpers.get_duel_or_raise(duel_id)
    return helpers.build_snapshot(duel_row=duel)    
