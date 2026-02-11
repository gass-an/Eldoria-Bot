"""Module de logique métier pour la fonctionnalité de gestion des profils XP et du leaderboard."""

from typing import Any

import discord

from eldoria.db.repo.xp_repo import xp_get_levels, xp_get_member, xp_get_role_ids, xp_list_members
from eldoria.features.xp.levels import compute_level
from eldoria.utils.mentions import level_label


def build_snapshot_for_xp_profile(guild: discord.Guild, user_id: int) -> dict[str, Any]:
    """Construit un snapshot de données pour la commande de profil XP d'un membre.

    Retourne un dict avec les clés suivantes :
    - xp: XP totale du membre
    - level: niveau calculé à partir de l'XP et des paliers de niveaux
    - level_label: mention du rôle de niveau actuel (ex: @level3) ou "Niveau 0" si aucun rôle
    - next_level_label: mention du rôle du niveau suivant, ou None si aucun palier supérieur
    - next_xp_required: XP requise pour atteindre le niveau suivant, ou None si aucun palier supérieur
    """
    guild_id = guild.id

    xp, _ = xp_get_member(guild_id, user_id)
    levels = xp_get_levels(guild_id)
    lvl = compute_level(xp, levels)

    role_ids = xp_get_role_ids(guild_id)
    lvl_label = level_label(guild, role_ids, lvl)

    next_req = None
    next_label = None
    for level, req in levels:
        if level == lvl + 1:
            next_req = req
            next_label = level_label(guild, role_ids, lvl + 1)
            break

    return {
        "xp": xp,
        "level": lvl,
        "level_label": lvl_label,
        "next_level_label": next_label,
        "next_xp_required": next_req,
    }
    
def get_leaderboard_items(guild: discord.Guild, *, limit: int = 200, offset: int = 0) -> list[tuple[int, int, int, str]]:
    """Retourne une liste des membres du serveur triés par XP décroissante, avec leur niveau et label de rôle.

    Chaque item de la liste est un tuple : (user_id, xp, level, level_label).
    - user_id: identifiant du membre
    - xp: XP totale du membre
    - level: niveau calculé à partir de l'XP et des paliers de niveaux
    - level_label: mention du rôle de niveau actuel (ex: @level3) ou "Niveau 0" si aucun rôle
    """
    guild_id = guild.id
    rows = xp_list_members(guild_id, limit, offset)
    levels = xp_get_levels(guild_id)
    role_ids = xp_get_role_ids(guild_id)

    items = []
    for (user_id, xp) in rows:
        level = compute_level(xp, levels)
        label = level_label(guild, role_ids, level)
        items.append((user_id, xp, level, label))

    return items