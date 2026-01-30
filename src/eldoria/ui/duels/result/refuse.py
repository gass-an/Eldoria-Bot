import discord

from eldoria.features.embed.common.embedColors import EMBED_COLOUR_ERROR
from eldoria.features.embed.common.embedImages import common_thumb, decorate_thumb_only


async def build_refuse_duels_embed(player_b: discord.Member):

    embed = discord.Embed(
        title=f"Invitation à un duel",
        description=f"L'invitation à été refusée par {player_b.display_name}.\nL'XP n'a pas été modifié.",
        colour=EMBED_COLOUR_ERROR
    )

    embed.set_footer(text="Peut-être une prochaine fois.")
    decorate_thumb_only(embed, None)
    files = common_thumb(None)
    return embed, files