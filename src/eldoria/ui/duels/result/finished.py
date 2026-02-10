from __future__ import annotations

import discord

from eldoria.json_tools.duels_json import get_game_text
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_VALIDATION
from eldoria.ui.common.embeds.images import common_thumb, decorate_thumb_only


async def build_game_result_base_embed(
    *,
    player_a: discord.Member,
    player_b: discord.Member,
    stake_xp: int,
    game_type: str,
) -> tuple[discord.Embed, list[discord.File]]:
    game_name, _ = get_game_text(game_type)

    embed = discord.Embed(
        title=f"{game_name}",
        description=(
            f"**{player_a.display_name}** vs **{player_b.display_name}**\n"
            f"Mise : **{stake_xp} XP**\n\u200b\n"
        ),
        colour=EMBED_COLOUR_VALIDATION,
    )

    decorate_thumb_only(embed, None)
    files = common_thumb(None)
    return embed, files