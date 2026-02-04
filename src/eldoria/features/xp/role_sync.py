from __future__ import annotations

import discord

from eldoria.db import database_manager
from eldoria.features.xp.roles import sync_member_level_roles
from eldoria.utils.discord_utils import get_member_by_id_or_raise


async def sync_xp_roles_for_users(guild: discord.Guild, user_ids: list[int]) -> None:
    # Si ton système XP peut être OFF par guilde
    if hasattr(database_manager, "xp_is_enabled") and not database_manager.xp_is_enabled(guild.id):
        return

    for uid in user_ids:
        try:
            member = await get_member_by_id_or_raise(guild=guild, member_id=uid)
            await sync_member_level_roles(guild, member)  # xp=None => relit en DB
        except Exception:
            continue