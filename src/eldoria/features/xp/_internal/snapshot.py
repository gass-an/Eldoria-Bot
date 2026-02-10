import discord
from eldoria.db.repo.xp_repo import xp_get_levels, xp_get_member, xp_get_role_ids, xp_list_members
from eldoria.features.xp.levels import compute_level
from eldoria.utils.mentions import level_label


def build_snapshot_for_xp_profile(guild: discord.Guild, user_id: int) -> dict[str, str]:
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