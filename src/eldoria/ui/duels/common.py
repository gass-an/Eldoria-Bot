from __future__ import annotations

import discord

from eldoria.json_tools.duels_json import get_game_text
from eldoria.features.embed.common.embedImages import decorate_thumb_only, common_thumb
from eldoria.features.embed.common.embedColors import EMBED_COLOUR_VALIDATION


async def build_game_base_embed(
    *,
    player_a: discord.Member,
    player_b: discord.Member,
    stake_xp: int,
    expires_at: int,
    game_type: str,
) -> tuple[discord.Embed, list[discord.File]]:
    game_name, game_description = get_game_text(game_type)

    expire_line = f"Ce duel expire <t:{expires_at}:R>\n" if expires_at else ""
    embed = discord.Embed(
        title=f"{game_name}",
        description=(
            f"{expire_line}\n"
            f"**{player_a.display_name}** vs **{player_b.display_name}**\n"
            f"Mise : **{stake_xp} XP**\n\n"
            f"> {game_description}\n\u200b\n"
        ),
        colour=EMBED_COLOUR_VALIDATION,
    )

    decorate_thumb_only(embed, None)
    files = common_thumb(None)
    return embed, files

async def build_game_result_base_embed(
    *,
    player_a: discord.Member,
    player_b: discord.Member,
    stake_xp: int,
    game_type: str,
) -> tuple[discord.Embed, list[discord.File]]:
    game_name, _game_description = get_game_text(game_type)

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