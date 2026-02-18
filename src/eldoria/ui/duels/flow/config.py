"""Module de configuration du pari en XP pour les duels."""

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.exceptions.duel import DuelError
from eldoria.exceptions.ui.duel_ui import duel_error_message
from eldoria.features.duel.constants import STAKE_XP_DEFAULTS
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_thumb, decorate_thumb_only
from eldoria.ui.duels.flow.invite import InviteView, build_invite_duels_embed
from eldoria.utils.discord_utils import (
    get_member_by_id_or_raise,
    get_text_or_thread_channel,
    require_guild,
)


async def build_config_stake_duels_embed(expires_at: int) -> tuple[discord.Embed, list[discord.File]]:
    """Construit l'embed de configuration du pari en XP."""
    embed = discord.Embed(
        title="Configuration du pari en XP",
        description=f"La configuration expire <t:{expires_at}:R>\n\n> Choisi un valeur d'XP que tu souhaites parier.",
        colour=EMBED_COLOUR_PRIMARY
    )

    embed.set_footer(text="Choisi le pari ci-dessous.")
    decorate_thumb_only(embed, None)
    files = common_thumb(None)
    return embed, files


class StakeXpView(discord.ui.View):
    """View pour la configuration du pari en XP."""

    def __init__(self, bot: EldoriaBot, duel_id: int) -> None:
        """Initialise la view avec les boutons de pari en XP."""
        super().__init__(timeout=600)
        self.bot = bot
        self.duel_id = duel_id
        self.duel = bot.services.duel

        list_stake = STAKE_XP_DEFAULTS
        for stake in list_stake:
            if stake in self.duel.get_allowed_stakes(duel_id):
                disable = False 
            else:
                disable = True
            
            btn = discord.ui.Button(
                label=str(stake),
                style=discord.ButtonStyle.secondary,
                disabled=disable
            )

            async def on_click(interaction: discord.Interaction, stake: int =stake) -> None:
                """Gère le clic sur un bouton de pari en XP."""
                await interaction.response.defer()
                try : 
                    snapshot = self.duel.configure_stake_xp(self.duel_id, stake_xp=stake)
                except DuelError as e:
                    await interaction.edit_original_response(content=duel_error_message(e), embeds=[], attachments=[], view=None)
                    return
                
                channel_id = snapshot["duel"]["channel_id"]
                channel = await get_text_or_thread_channel(bot=bot, channel_id=channel_id)
                
                player_a_id = snapshot["duel"]["player_a"]
                player_b_id = snapshot["duel"]["player_b"]
                message = await channel.send(content=f"<@{player_b_id}>. Quelqu'un vous provoque en duel !")
                
                try :
                    snapshot2 = self.duel.send_invite(duel_id=duel_id, message_id=message.id)
                except DuelError as e:
                    await interaction.edit_original_response(content=duel_error_message(e), embeds=[], attachments=[], view=None)
                    return
                
                guild = require_guild(interaction=interaction)
                
                try:
                    player_a = await get_member_by_id_or_raise(guild, player_a_id)
                    player_b = await get_member_by_id_or_raise(guild, player_b_id)
                except ValueError:
                    await interaction.edit_original_response(content="Un des participants n'a pas pu être trouvé.", embeds=[], attachments=[], view=None)
                    return
                
                xp_dict = snapshot2["xp"]
                stake_xp = snapshot2["duel"]["stake_xp"]
                expires_at = snapshot2["duel"]["expires_at"]
                game_type = snapshot2["duel"]["game_type"]

                embed, files = await build_invite_duels_embed(player_a, player_b, xp_dict, stake_xp, expires_at, game_type)
                await message.edit( 
                    content=f"||{player_a.mention} vs {player_b.mention}||", 
                    embed=embed,
                    files=files, 
                    view=InviteView(duel_id=duel_id, bot=bot),
                    )
                
                await interaction.edit_original_response(content="Invitation envoyée !", embeds=[], attachments=[], view=None)

            btn.callback = on_click
            self.add_item(btn)