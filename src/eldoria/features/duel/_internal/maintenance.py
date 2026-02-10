from typing import Any

from eldoria.db.connection import get_conn
from eldoria.db.repo.duel_repo import (
    cleanup_duels, 
    list_expired_duels, 
    transition_status, 
    update_duel_if_status
    )
from eldoria.exceptions.duel_exceptions import DuelAlreadyHandled, DuelNotFinishable
from eldoria.features.duel._internal.gameplay import is_duel_complete_for_game, resolve_duel_for_game
from eldoria.features.duel._internal.helpers import (
    finish_duel, 
    get_duel_or_raise, 
    modify_xp_for_players
    )
from eldoria.features.duel.constants import (
    DUEL_STATUS_ACTIVE, 
    DUEL_STATUS_CONFIG, 
    DUEL_STATUS_EXPIRED, 
    DUEL_STATUS_INVITED, 
    KEEP_EXPIRED_DAYS, 
    KEEP_FINISHED_DAYS
    )
from eldoria.utils.timestamp import now_ts


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

                if fresh["status"] == DUEL_STATUS_ACTIVE and is_duel_complete_for_game(fresh):
                    result = resolve_duel_for_game(fresh)
                    
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
