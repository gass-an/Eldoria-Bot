from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import discord

import gestionDB


@dataclass(frozen=True)
class XpConfig:
    points_per_message: int = 5
    cooldown_seconds: int = 60
    server_tag: str | None = None
    bonus_percent: int = 50


DEFAULT_LEVELS: dict[int, int] = {
            1: 0,
            2: 300,
            3: 600,
            4: 1000,
            5: 3000,
        }


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def compute_level(xp: int, levels: Iterable[tuple[int, int]]) -> int:
    """Renvoie le niveau correspondant à l'XP (plus haut seuil atteint)."""
    lvl = 1
    for level, required in levels:
        if xp >= required:
            lvl = level
    return lvl


async def ensure_guild_xp_setup(guild: discord.Guild):
    """Crée la config + niveaux par défaut + rôles level5..level1 (si absents),
    sans jamais toucher aux positions (création uniquement).
    """
    gestionDB.xp_ensure_defaults(guild.id, DEFAULT_LEVELS)

    role_ids = gestionDB.xp_get_role_ids(guild.id)
    roles_by_id = {r.id: r for r in guild.roles}

    # On crée du plus haut niveau au plus bas : level5 → level1
    for lvl in range(5, 0, -1):
        role: discord.Role | None = None

        # 1) Priorité : role_id déjà connu en DB
        rid = role_ids.get(lvl)
        if rid:
            role = roles_by_id.get(rid)

        # 2) Fallback anti-doublons si DB reset : retrouver par nom
        if role is None:
            role = discord.utils.get(guild.roles, name=f"level{lvl}")

        # 3) Créer si vraiment absent (sans déplacer)
        if role is None:
            try:
                role = await guild.create_role(
                    name=f"level{lvl}",
                    reason="Initialisation des rôles XP",
                )
            except discord.Forbidden:
                # pas la permission de créer des rôles → on arrête sans casser
                return

        # 4) Stocker/mettre à jour en DB
        gestionDB.xp_upsert_role_id(guild.id, lvl, role.id)


async def sync_member_level_roles(guild: discord.Guild, member: discord.Member, *, xp: int | None = None):
    """Met à jour les rôles lvlX d'un membre en fonction de son XP."""
    if member.bot:
        return

    if xp is None:
        xp, _ = gestionDB.xp_get_member(guild.id, member.id)

    levels = gestionDB.xp_get_levels(guild.id)
    if not levels:
        # fallback (normalement impossible si ensure_guild_xp_setup est appelé)
        levels = list(DEFAULT_LEVELS.items())

    current_lvl = compute_level(xp, levels)
    role_ids = gestionDB.xp_get_role_ids(guild.id)
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


async def handle_message_xp(message: discord.Message) -> tuple[int, int] | None:
    """Attribue l'XP d'un message si le cooldown est passé.

    Retourne (new_xp, new_level) si XP ajouté, sinon None.
    """
    if message.guild is None:
        return None
    if message.author.bot:
        return None

    guild = message.guild
    member = message.author

    config_raw = gestionDB.xp_get_config(guild.id)
    config = XpConfig(**config_raw)

    now = _now_ts()
    old_xp, last_ts = gestionDB.xp_get_member(guild.id, member.id)
    if last_ts and (now - last_ts) < config.cooldown_seconds:
        return None

    gained = max(int(config.points_per_message), 0)
    if gained == 0:
        return None

    # Bonus si le tag du serveur est présent dans le pseudo (configurable)
    if config.server_tag:
        name = (member.nick or member.display_name or "")
        if config.server_tag in name:
            gained = int(round(gained * (1 + config.bonus_percent / 100)))

    new_xp = gestionDB.xp_add_xp(guild.id, member.id, gained, set_last_xp_ts=now)
    levels = gestionDB.xp_get_levels(guild.id)
    new_lvl = compute_level(new_xp, levels)

    await sync_member_level_roles(guild, member, xp=new_xp)
    return new_xp, new_lvl
