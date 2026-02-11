"""Module de fonctions de maintenance pour les duels, notamment la gestion de l'expiration des duels et le nettoyage des anciens duels dans la base de données."""

from typing import Any

from eldoria.db.connection import get_conn
from eldoria.db.repo import duel_repo
from eldoria.exceptions.duel_exceptions import DuelAlreadyHandled, DuelNotFinishable
from eldoria.features.duel import constants
from eldoria.features.duel._internal import helpers
from eldoria.features.duel._internal.gameplay import (
    is_duel_complete_for_game,
    resolve_duel_for_game,
)
from eldoria.utils.timestamp import now_ts


def cancel_expired_duels() -> list[dict[str, Any]]:
    """Expire les duels arrivés à échéance.

    Retourne une liste d'objets décrivant les duels effectivement passés en EXPIRED.
    Le Cog peut s'en servir pour éditer le message Discord associé (embed + suppression des boutons).
    """
    duels = duel_repo.list_expired_duels(now_ts())
    expired: list[dict[str, Any]] = []

    for duel in duels:
        duel_id = duel["duel_id"]
        status = duel["status"]

        # 1) Cas spécial : duel ACTIVE expiré mais "terminable"
        if status == constants.DUEL_STATUS_ACTIVE:
            try:
                # Re-check frais (évite stale read si payload a bougé juste après list_expired_duels)
                fresh = helpers.get_duel_or_raise(duel_id)

                if fresh["status"] == constants.DUEL_STATUS_ACTIVE and is_duel_complete_for_game(fresh):
                    result = resolve_duel_for_game(fresh)
                    
                    finished_now = False
                    try:
                        helpers.finish_duel(duel_id, result, ignore_expired=True)
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
                            "previous_status": constants.DUEL_STATUS_ACTIVE,
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
            if not duel_repo.transition_status(
                duel_id,
                from_status=status,
                to_status=constants.DUEL_STATUS_EXPIRED,
                expires_at=None,
                conn=conn,
            ):
                continue

            duel_repo.update_duel_if_status(
                duel_id,
                required_status=constants.DUEL_STATUS_EXPIRED,
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
                    "xp_changed": status == constants.DUEL_STATUS_ACTIVE,
                    "sync_roles_user_ids": [duel["player_a_id"], duel["player_b_id"]],
                }
            )

            if status in (constants.DUEL_STATUS_CONFIG, constants.DUEL_STATUS_INVITED):
                continue

            guild_id = duel["guild_id"]
            player_a_id = duel["player_a_id"]
            player_b_id = duel["player_b_id"]
            stake_xp = duel["stake_xp"]

            helpers.modify_xp_for_players(guild_id, player_a_id, player_b_id, stake_xp, conn=conn)

    return expired


def cleanup_old_duels(now_ts: int) -> None:
    """Supprime les duels expirés depuis plus de KEEP_EXPIRED_DAYS jours, et les duels finis depuis plus de KEEP_FINISHED_DAYS jours, afin de nettoyer la base de données."""
    cutoff_short = now_ts - (constants.KEEP_EXPIRED_DAYS * 86400)
    cutoff_finished = now_ts - (constants.KEEP_FINISHED_DAYS * 86400)

    duel_repo.cleanup_duels(
        cutoff_short=cutoff_short,
        cutoff_finished=cutoff_finished,
    )
