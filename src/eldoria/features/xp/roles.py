from typing import Dict
import discord

from eldoria.db.repo.xp_repo import xp_get_levels, xp_get_member, xp_get_role_ids
from eldoria.defaults import XP_LEVELS_DEFAULTS
from eldoria.features.xp.levels import compute_level


async def sync_member_level_roles(guild: discord.Guild, member: discord.Member, *, xp: int | None = None):
    """Met à jour les rôles lvlX d'un membre en fonction de son XP."""
    if member.bot:
        return

    if xp is None:
        xp, _ = xp_get_member(guild.id, member.id)

    levels = xp_get_levels(guild.id)
    if not levels:
        # fallback (normalement impossible si ensure_guild_xp_setup est appelé)
        levels = list(XP_LEVELS_DEFAULTS.items())

    current_lvl = compute_level(xp, levels)
    role_ids = xp_get_role_ids(guild.id)
    if not role_ids:
        return

    desired_role_id = role_ids.get(current_lvl)
    desired_role = guild.get_role(desired_role_id) if desired_role_id else None

    # Liste des rôles de niveaux déjà présents
    lvl_roles_present = [r for r in member.roles if any(r.id == rid for rid in role_ids.values())]
    to_remove = [r for r in lvl_roles_present if desired_role is None or r.id != desired_role.id]

    # Ajout / retrait (évite les erreurs si le bot ne peut pas gérer)
    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="Mise à jour niveau XP")
        if desired_role and desired_role not in member.roles:
            await member.add_roles(desired_role, reason="Mise à jour niveau XP")
    except discord.Forbidden:
        return
    

def get_xp_role_ids(guild_id: int | None) -> Dict[int, int]:
    """
    Retourne le mapping {level: role_id} pour un serveur XP.
    Si guild_id est None ou invalide, retourne un dict vide.
    """
    if not guild_id:
        return {}

    try:
        return xp_get_role_ids(guild_id) or {}
    except Exception:
        # sécurité : l'UI ne doit jamais planter à cause de la DB
        return {}