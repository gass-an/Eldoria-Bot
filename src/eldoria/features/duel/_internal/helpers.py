"""Module de fonctions utilitaires pour la gestion des duels, utilisées en interne dans les différentes étapes du processus de duel (configuration, résolution, etc.)."""

import json
from sqlite3 import Connection, Row
from typing import Any, cast

from eldoria.db.connection import get_conn
from eldoria.db.repo.duel_repo import get_duel_by_id, transition_status, update_duel_if_status
from eldoria.db.repo.xp_repo import xp_add_xp, xp_get_member
from eldoria.exceptions import duel_exceptions as exc
from eldoria.features.duel import constants
from eldoria.utils.timestamp import now_ts


def finish_duel(duel_id: int, result: str, *, ignore_expired: bool=False) -> bool:
    """Finit un duel en mettant à jour son status, son résultat, et son timestamp de fin dans la base de données.
    
    Uniquement si le duel est actuellement actif et pas déjà fini, et retourne True si la mise à jour a été effectuée, ou False sinon.
    """
    duel = get_duel_or_raise(duel_id)
    if not ignore_expired:
        assert_duel_not_expired(duel)
    
    if result not in constants.DUEL_RESULTS:
        raise exc.InvalidResult(result)
    
    status = duel["status"]
    if status != constants.DUEL_STATUS_ACTIVE:
        raise exc.DuelNotFinishable(status)
    
    guild_id = duel["guild_id"]
    player_a_id = duel["player_a_id"]
    player_b_id = duel["player_b_id"]
    stake_xp = duel["stake_xp"]

    # Transaction: status + payout + finished_at dans la même connexion
    with get_conn() as conn:
        if not transition_status(
            duel_id,
            from_status=constants.DUEL_STATUS_ACTIVE,
            to_status=constants.DUEL_STATUS_FINISHED,
            expires_at=None,
            conn=conn,
        ):
            raise exc.DuelAlreadyHandled(duel_id, constants.DUEL_STATUS_ACTIVE)

        match result:
            case constants.DUEL_RESULT_DRAW:
                modify_xp_for_players(guild_id, player_a_id, player_b_id, stake_xp, conn=conn)

            case constants.DUEL_RESULT_WIN_A:
                xp_add_xp(guild_id, player_a_id, 2 * stake_xp, conn=conn)

            case constants.DUEL_RESULT_WIN_B:
                xp_add_xp(guild_id, player_b_id, 2 * stake_xp, conn=conn)

            case _:
                raise exc.InvalidResult(result)

        if not update_duel_if_status(
            duel_id,
            required_status=constants.DUEL_STATUS_FINISHED,
            finished_at=now_ts(),
            conn=conn,
        ):
            raise exc.DuelNotFinished(duel_id, constants.DUEL_STATUS_FINISHED)
        




def load_payload_any(duel: Row) -> dict[str, Any]:
    """Charge le contenu du champ payload d'un duel, qui est une chaîne JSON, et retourne un dictionnaire.
    
    En cas d'erreur (ex: JSON invalide), retourne un dictionnaire vide.
    """
    try:
        raw = duel["payload"]
        if not raw:
            return {}
        return cast(dict[str, Any], json.loads(raw))
    except Exception:
        return {}

def dump_payload(payload: dict[str, Any]) -> str:
    """Sérialise un dictionnaire en une chaîne JSON à stocker dans le champ payload d'un duel."""
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
            for stake_xp in constants.STAKE_XP_DEFAULTS 
            if (player_a_xp >= stake_xp and player_b_xp >= stake_xp)
    ]

def get_allowed_stakes(duel_id: int) -> list[int]:
    """Retourne la liste des mises en XP autorisées pour un duel donné, c'est à dire les mises pour lesquelles les 2 joueurs ont suffisamment d'XP."""
    duel = get_duel_by_id(duel_id)
    return _get_allowed_stakes_from_duel(duel)
    

def is_configuration_available(duel_id: int) -> bool:
    """Retourne True si la configuration du duel est disponible.
    
    C'est à dire que le duel existe, n'est pas expiré, et que son statut, son type de jeu et sa mise sont compatibles avec une configuration.
    """
    duel = get_duel_by_id(duel_id)
    if not duel:
        return False
    
    game_type = duel["game_type"]
    stake_xp = duel["stake_xp"]
    status = duel["status"]

    return (
        game_type in constants.GAME_TYPES and 
        stake_xp in _get_allowed_stakes_from_duel(duel) and 
        status == constants.DUEL_STATUS_CONFIG
    )

def modify_xp_for_players(
    guild_id: int,
    player_a_id: int,
    player_b_id: int,
    xp: int,
    *,
    conn: Connection | None =None,
) -> dict[int, int]:
    """Modifie l'XP des 2 joueurs et retourne {user_id: new_xp}."""
    new_xp_player_a = xp_add_xp(guild_id, player_a_id, xp, conn=conn)
    new_xp_player_b = xp_add_xp(guild_id, player_b_id, xp, conn=conn)
    return {player_a_id: new_xp_player_a, player_b_id: new_xp_player_b}


def assert_duel_not_expired(duel: Row) -> None: 
    """Lève une exception si le duel est expiré, c'est à dire que son timestamp d'expiration est dépassé."""
    expires_at = duel["expires_at"]
    if expires_at is not None and expires_at <= now_ts():
        raise exc.ExpiredDuel(duel["duel_id"])
    
def get_duel_or_raise(duel_id: int) -> Row:
    """Retourne la ligne de duel correspondante à l'identifiant fourni, ou lève une exception si aucun duel n'est trouvé."""
    duel = get_duel_by_id(duel_id)
    if not duel:
        raise exc.DuelNotFound(duel_id)
    return duel

def get_xp_for_players(guild_id: int, player_a_id: int, player_b_id: int, *,conn: Connection | None = None) -> dict[int, int]:
        """Retourne un dictionnaire {user_id: xp} avec l'XP actuel des 2 joueurs."""
        player_a_xp = xp_get_member(guild_id, player_a_id, conn=conn)[0]
        player_b_xp = xp_get_member(guild_id, player_b_id, conn=conn)[0]
        return {player_a_id: player_a_xp, player_b_id: player_b_xp}

def build_snapshot(
        duel_row: Row, 
        *, 
        allowed_stakes: list[int] | None = None, 
        xp: dict[int, int] | None = None, 
        game_infos: dict[str, Any] | None = None, 
        effects: dict[str, Any] | None = None
    ) -> dict[str, Any]:
    """Construit un snapshot du duel à partir de la ligne de duel et des informations fournies, dans un format prêt à être utilisé pour l'interface utilisateur."""
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