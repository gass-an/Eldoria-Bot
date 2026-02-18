"""Module interne gérant la logique de gameplay d'un duel, c'est à dire l'appel au jeu configuré pour faire avancer le duel.

Vérifie si les conditions de fin sont remplies, et résoudre le résultat du duel en fonction du jeu.
"""

import json
from sqlite3 import Row
from typing import Any, cast

from eldoria.db.repo.xp_repo import xp_get_levels, xp_get_role_ids
from eldoria.exceptions import duel as exc
from eldoria.features.duel._internal import helpers
from eldoria.features.duel.games.registry import require_game
from eldoria.features.xp.levels import compute_level


def play_game_action(duel_id: int, user_id: int, action: dict[str, Any]) -> dict[str, Any]:
    """Appelle le bon jeu via le registry, puis si FINISHED => finish_duel.
    
    Retourne un snapshot prêt pour l'UI (avec xp si fini).
    """
    duel = helpers.get_duel_or_raise(duel_id)

    game_key = duel["game_type"]
    if not game_key:
        raise exc.WrongGameType("NONE", "CONFIGURED_GAME")

    game = require_game(str(game_key))

    # 1) le jeu fait son travail (payload + état)
    snapshot = game.play(duel_id, user_id, action)

    # 2) si FINISHED -> service finalise (status+xp)
    game_infos = snapshot.get("game", {})
    state = game_infos.get("state")

    if state == "FINISHED":
        result = game_infos.get("result")
        if not isinstance(result, str):
            raise exc.InvalidResult(str(result))

        # idempotent (si déjà terminé -> DuelAlreadyHandled / DuelNotFinishable)
        finished_now = False
        try:
            helpers.finish_duel(duel_id, result)
            finished_now = True
        except (exc.DuelAlreadyHandled, exc.DuelNotFinishable):
            # quelqu'un a déjà fini / plus ACTIVE, on continue quand même
            pass

        # relire duel + xp (source de vérité)
        duel2 = helpers.get_duel_or_raise(duel_id)
        guild_id = duel2["guild_id"]
        player_a_id = duel2["player_a_id"]
        player_b_id = duel2["player_b_id"]
        xp = helpers.get_xp_for_players(guild_id, player_a_id, player_b_id)


        payload = {}
        try:
            payload = json.loads(duel2["payload"] or "{}")
        except Exception:
            pass

        baseline = payload.get("xp_baseline")
        level_changes = []

        if baseline:
            levels = xp_get_levels(guild_id)

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

        
        role_ids = xp_get_role_ids(guild_id)
        effects = {
            "xp_changed": True,
            "sync_roles_user_ids": [player_a_id, player_b_id],
            "xp_role_ids": role_ids,
        }
        if finished_now:
            effects["level_changes"] = level_changes

        # on renvoie snapshot FINAL enrichi
        return helpers.build_snapshot(duel_row=duel2, xp=xp, game_infos=cast(dict[str, Any], game_infos), effects=effects)

    # Sinon WAITING -> on renvoie tel quel
    return snapshot

def is_duel_complete_for_game(duel: Row) -> bool:
    """Retourne True si le duel est dans un état considéré comme "complet" pour le jeu configuré, c'est à dire que les conditions de victoire/défaite sont remplies et que le duel peut être fini."""
    game_key = duel["game_type"]
    if not game_key:
        return False

    try:
        game = require_game(game_key)
    except ValueError:
        return False

    return game.is_complete(duel)


def resolve_duel_for_game(duel: Row) -> str:
    """Retourne le résultat du duel pour le jeu configuré, en supposant que le duel est dans un état "complet" (conditions de victoire/défaite remplies)."""
    game_key = duel["game_type"]
    if not game_key:
        raise exc.WrongGameType(game_key, "UNKNOWN")

    try:
        game = require_game(game_key)
    except ValueError:
        raise exc.WrongGameType(game_key, "SUPPORTED_GAME")

    return game.resolve(duel)
