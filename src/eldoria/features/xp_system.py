from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

import discord

from ..db import gestionDB


@dataclass(frozen=True)
class XpConfig:
    enabled: bool = False
    points_per_message: int = 8
    cooldown_seconds: int = 90
    bonus_percent: int = 20


DEFAULT_LEVELS: dict[int, int] = {
    1: 0,
    2: 600,
    3: 1800,
    4: 3800,
    5: 7200,
}


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _has_active_server_tag_for_guild(member: discord.abc.User, guild: discord.Guild) -> bool:
    """True si le membre affiche l'identité (Server Tag) de CETTE guilde sur son profil.

    Compatibilité: si la lib ne fournit pas ces champs, retourne False (pas de bonus plutôt que planter).
    """
    # Selon les versions/forks, primary_guild peut être sur User ou accessible via member._user
    user_obj = member
    pg = getattr(user_obj, "primary_guild", None)
    if pg is None:
        pg = getattr(getattr(member, "_user", None), "primary_guild", None)

    if pg is None:
        return False

    identity_enabled = bool(getattr(pg, "identity_enabled", False))
    if not identity_enabled:
        return False

    identity_guild_id = getattr(pg, "identity_guild_id", None)
    if identity_guild_id != guild.id:
        return False

    # Si la lib expose le tag côté guilde, on vérifie aussi l'égalité des tags
    guild_tag = getattr(guild, "tag", None)
    user_tag = getattr(pg, "tag", None)
    if guild_tag and user_tag:
        return str(user_tag).upper() == str(guild_tag).upper()

    return True


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


async def handle_message_xp(message: discord.Message) -> Optional[tuple[int, int, int]]:
    """Attribue l'XP d'un message si le cooldown est passé.

    Retourne (new_xp, new_level, old_level) si XP ajouté, sinon None.
    """
    if message.guild is None:
        return None
    if message.author.bot:
        return None

    guild = message.guild
    member = message.author

    config_raw = gestionDB.xp_get_config(guild.id)
    config = XpConfig(**config_raw)

    # XP global switch (par guilde)
    if not config.enabled:
        return None

    now = _now_ts()
    old_xp, last_ts = gestionDB.xp_get_member(guild.id, member.id)
    if last_ts and (now - last_ts) < config.cooldown_seconds:
        return None

    gained = max(int(config.points_per_message), 0)
    if gained == 0:
        return None


    # Bonus: si le membre affiche le Server Tag de cette guilde sur son profil.
    # Si bonus_percent == 0, cela désactive de fait le bonus.
    if config.bonus_percent > 0 and _has_active_server_tag_for_guild(member, guild):
        gained = int(round(gained * (1 + config.bonus_percent / 100)))

    # Malus "anti-karuta" : les messages très courts qui commencent par "k"/"K" ne donnent
    # que 30% de l'XP qu'ils auraient dû rapporter.
    # Exemple typique : k, kd, kcd, kt burn, ...
    content = (message.content or "").strip()
    if content and content[0] in ("k", "K") and len(content) <= 10:
        gained = int(round(gained * 0.30))

    new_xp = gestionDB.xp_add_xp(guild.id, member.id, gained, set_last_xp_ts=now)

    levels = gestionDB.xp_get_levels(guild.id)
    old_lvl = compute_level(old_xp, levels)
    new_lvl = compute_level(new_xp, levels)

    await sync_member_level_roles(guild, member, xp=new_xp)

    return new_xp, new_lvl, old_lvl
