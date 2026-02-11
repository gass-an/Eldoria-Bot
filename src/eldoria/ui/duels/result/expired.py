"""Module pour construire l'embed de résultat d'un duel expiré."""

from __future__ import annotations

import discord

from eldoria.json_tools.duels_json import get_game_text
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_ERROR
from eldoria.ui.common.embeds.images import common_thumb, decorate_thumb_only


async def build_expired_duels_embed(
    *,
    player_a: discord.Member,
    player_b: discord.Member,
    previous_status: str,
    stake_xp: int,
    game_type: str,
) -> tuple[discord.Embed, list[discord.File]]:
    """Embed de résultat pour un duel expiré.

    - previous_status : CONFIG / INVITED / ACTIVE (avant transition vers EXPIRED)
    - stake_xp : mise (peut être None en CONFIG)
    - game_type : clé du jeu (peut être vide en CONFIG)
    """
    prev = (previous_status or "").upper()
    stake = int(stake_xp or 0)

    if game_type:
        game_name, _ = get_game_text(game_type)
        title = f"⏰ Duel expiré — {game_name}"
    else:
        title = "⏰ Duel expiré"

    if prev == "INVITED":
        reason = "L'invitation n'a pas été acceptée à temps."
    elif prev == "ACTIVE":
        reason = "Le duel n'a pas été terminé à temps."
    else:
        reason = "Le duel n'a pas été configuré à temps."

    description = (
        f"**{player_a.display_name}** vs **{player_b.display_name}**\n"
        f"{reason}\n\u200b\n"
    )

    embed = discord.Embed(
        title=title,
        description=description,
        colour=EMBED_COLOUR_ERROR,
    )

    if stake > 0:
        embed.add_field(name="Mise", value=f"{stake} XP", inline=True)

        # En ACTIVE, le service rembourse au moment de l'expiration.
        if prev == "ACTIVE":
            embed.add_field(name="Remboursement", value="✅ Mise remboursée", inline=True)
        else:
            embed.add_field(name="Remboursement", value="ℹ️ Aucune mise prélevée", inline=True)

    embed.set_footer(text="Le duel est terminé.")
    decorate_thumb_only(embed, None)
    files = common_thumb(None)
    return embed, files
