from typing import Optional
import discord
from eldoria.db.repo.xp_repo import xp_add_xp, xp_get_config, xp_get_levels, xp_get_member
from eldoria.features.xp.config import XpConfig
from eldoria.features.xp.levels import compute_level
from eldoria.features.xp.roles import sync_member_level_roles
from eldoria.features.xp.tags import _has_active_server_tag_for_guild
from eldoria.utils.timestamp import now_ts


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

    config_raw = xp_get_config(guild.id)
    config = XpConfig(**config_raw)

    # XP global switch (par guilde)
    if not config.enabled:
        return None

    now = now_ts()
    old_xp, last_ts = xp_get_member(guild.id, member.id)
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
    # qu'un % de l'XP qu'ils auraient dû rapporter (configurable).
    # Exemple typique : k, kd, kcd, kt burn, ...
    content = (message.content or "").strip()
    if content and content[0] in ("k", "K") and len(content) <= 10:
        pct = max(int(getattr(config, "karuta_k_small_percent", 30)), 0)
        gained = int(round(gained * (pct / 100)))

    new_xp = xp_add_xp(guild.id, member.id, gained, set_last_xp_ts=now)

    levels = xp_get_levels(guild.id)
    old_lvl = compute_level(old_xp, levels)
    new_lvl = compute_level(new_xp, levels)

    await sync_member_level_roles(guild, member, xp=new_xp)

    return new_xp, new_lvl, old_lvl