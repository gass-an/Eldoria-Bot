import json
from  sqlite3 import Row
from typing import Any, cast

from eldoria.features.duel.duel_helpers import _get_allowed_stakes_from_duel, _is_duel_complete_for_game, _resolve_duel_for_game, assert_duel_not_expired, build_snapshot, dump_payload, finish_duel, get_allowed_stakes, get_duel_or_raise, get_xp_for_players, is_configuration_available, load_payload_any, modify_xp_for_players
from eldoria.features.duel.games.registry import require_game
from eldoria.features.xp_system import compute_level

from ...exceptions.duel_exceptions import *
from ...db.database_manager import *
from ...db.connection import get_conn
from ...utils.timestamp import *
from .constants import *
import eldoria.features.duel.constants as constants

from eldoria.db import database_manager


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



def play_game_action(duel_id: int, user_id: int, action: dict[str, Any]) -> dict[str, Any]:
    """
    Appelle le bon jeu via le registry, puis si FINISHED => finish_duel.
    Retourne un snapshot prêt pour l'UI (avec xp si fini).
    """
    duel = get_duel_or_raise(duel_id)

    game_key = duel["game_type"]
    if not game_key:
        raise WrongGameType("NONE", "CONFIGURED_GAME")

    game = require_game(str(game_key))

    # 1) le jeu fait son travail (payload + état)
    snapshot = game.play(duel_id, user_id, action)

    # 2) si FINISHED -> service finalise (status+xp)
    game_infos = snapshot.get("game", {})
    state = game_infos.get("state")

    if state == "FINISHED":
        result = game_infos.get("result")
        if not isinstance(result, str):
            raise InvalidResult(str(result))

        # idempotent (si déjà terminé -> DuelAlreadyHandled / DuelNotFinishable)
        finished_now = False
        try:
            finish_duel(duel_id, result)
            finished_now = True
        except (DuelAlreadyHandled, DuelNotFinishable):
            # quelqu'un a déjà fini / plus ACTIVE, on continue quand même
            pass

        # relire duel + xp (source de vérité)
        duel2 = get_duel_or_raise(duel_id)
        guild_id = duel2["guild_id"]
        player_a_id = duel2["player_a_id"]
        player_b_id = duel2["player_b_id"]
        xp = get_xp_for_players(guild_id, player_a_id, player_b_id)


        payload = {}
        try:
            payload = json.loads(duel2["payload"] or "{}")
        except Exception:
            pass

        baseline = payload.get("xp_baseline")
        level_changes = []

        if baseline:
            levels = database_manager.xp_get_levels(guild_id)

            # Player A
            old_xp = baseline.get("player_a_before_xp")
            new_xp = xp[player_a_id]
            if old_xp is not None:
                old_lvl = compute_level(old_xp, levels)
                new_lvl = compute_level(new_xp, levels)
                if old_lvl != new_lvl:
                    level_changes.append({
                        "user_id": player_a_id,
                        "old_level": old_lvl,
                        "new_level": new_lvl,
                    })

            # Player B
            old_xp = baseline.get("player_b_before_xp")
            new_xp = xp[player_b_id]
            if old_xp is not None:
                old_lvl = compute_level(old_xp, levels)
                new_lvl = compute_level(new_xp, levels)
                if old_lvl != new_lvl:
                    level_changes.append({
                        "user_id": player_b_id,
                        "old_level": old_lvl,
                        "new_level": new_lvl,
                    })


        effects = {
            "xp_changed": True,
            "sync_roles_user_ids": [player_a_id, player_b_id],
        }
        if finished_now:
            effects["level_changes"] = level_changes

        # on renvoie snapshot FINAL enrichi
        return build_snapshot(duel_row=duel2, xp=xp, game_infos=cast(dict[str, Any], game_infos), effects=effects)

    # Sinon WAITING -> on renvoie tel quel
    return snapshot









def cancel_expired_duels() -> list[dict[str, Any]]:
    """Expire les duels arrivés à échéance.

    Retourne une liste d'objets décrivant les duels effectivement passés en EXPIRED.
    Le Cog peut s'en servir pour éditer le message Discord associé (embed + suppression des boutons).
    """

    duels = list_expired_duels(now_ts())
    expired: list[dict[str, Any]] = []

    for duel in duels:
        duel_id = duel["duel_id"]
        status = duel["status"]

        # 1) Cas spécial : duel ACTIVE expiré mais "terminable"
        if status == DUEL_STATUS_ACTIVE:
            try:
                # Re-check frais (évite stale read si payload a bougé juste après list_expired_duels)
                fresh = get_duel_or_raise(duel_id)

                if fresh["status"] == DUEL_STATUS_ACTIVE and _is_duel_complete_for_game(fresh):
                    result = _resolve_duel_for_game(fresh)
                    
                    finished_now = False
                    try:
                        finish_duel(duel_id, result, ignore_expired=True)
                        finished_now = True
                    except (DuelAlreadyHandled, DuelNotFinishable):
                        # quelqu'un l'a déjà terminé / il n'est plus ACTIVE
                        pass
                    
                    if finished_now:
                        expired.append({
                            "duel_id": duel_id,
                            "guild_id": fresh["guild_id"],
                            "channel_id": fresh["channel_id"],
                            "message_id": fresh["message_id"],
                            "player_a_id": fresh["player_a_id"],
                            "player_b_id": fresh["player_b_id"],
                            "stake_xp": fresh["stake_xp"],
                            "game_type": fresh["game_type"],
                            "previous_status": DUEL_STATUS_ACTIVE,
                            "xp_changed": True,
                            "sync_roles_user_ids": [fresh["player_a_id"], fresh["player_b_id"]],
                            "auto_finished": True,
                        })
                        
                    continue
            except Exception as e:
                print(f"[cancel_expired_duels] resolve error duel_id={duel_id} \n Error : {e}")
                pass

        # 2) Sinon : expire normalement (transaction + refund si duel était ACTIVE)
        with get_conn() as conn:
            if not transition_status(
                duel_id,
                from_status=status,
                to_status=DUEL_STATUS_EXPIRED,
                expires_at=None,
                conn=conn,
            ):
                continue

            update_duel_if_status(
                duel_id,
                required_status=DUEL_STATUS_EXPIRED,
                finished_at=now_ts(),
                conn=conn,
            )

            # Pour l'UI : uniquement si on a un message à éditer.
            # (CONFIG est souvent un message éphémère, donc message_id peut être NULL)
            expired.append(
                {
                    "duel_id": duel_id,
                    "guild_id": duel["guild_id"],
                    "channel_id": duel["channel_id"],
                    "message_id": duel["message_id"],
                    "player_a_id": duel["player_a_id"],
                    "player_b_id": duel["player_b_id"],
                    "stake_xp": duel["stake_xp"],
                    "game_type": duel["game_type"],
                    "previous_status": status,
                    "xp_changed": status == DUEL_STATUS_ACTIVE,
                    "sync_roles_user_ids": [duel["player_a_id"], duel["player_b_id"]],
                }
            )

            if status in (DUEL_STATUS_CONFIG, DUEL_STATUS_INVITED):
                continue

            guild_id = duel["guild_id"]
            player_a_id = duel["player_a_id"]
            player_b_id = duel["player_b_id"]
            stake_xp = duel["stake_xp"]

            modify_xp_for_players(guild_id, player_a_id, player_b_id, stake_xp, conn=conn)

    return expired


def cleanup_old_duels(now_ts: int) -> None:
    cutoff_short = now_ts - (KEEP_EXPIRED_DAYS * 86400)
    cutoff_finished = now_ts - (KEEP_FINISHED_DAYS * 86400)

    cleanup_duels(
        cutoff_short=cutoff_short,
        cutoff_finished=cutoff_finished,
    )

