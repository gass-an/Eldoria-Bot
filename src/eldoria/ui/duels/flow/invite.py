"""Module de gestion de l'invitation au duel."""

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.exceptions.duel import DuelError
from eldoria.exceptions.ui.duel_ui import duel_error_message
from eldoria.json_tools.duels_json import get_game_text
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_thumb, decorate_thumb_only
from eldoria.ui.duels.render import render_duel_message
from eldoria.ui.duels.result.refuse import build_refuse_duels_embed
from eldoria.utils.discord_utils import (
    get_member_by_id_or_raise,
    get_text_or_thread_channel,
    require_guild,
    require_user_id,
)


async def build_invite_duels_embed(
        player_a: discord.Member, 
        player_b: discord.Member, 
        xp_dict: dict[int, int] ,
        stake_xp: int,
        expires_at: int,
        game_type: str,
        ) -> tuple[discord.Embed, list[discord.File]]:
    """Construit l'embed d'invitation au duel."""
    embed = discord.Embed(
        title="Invitation à un duel",
        description=f"Cette invitation expire <t:{expires_at}:R>\n**{player_b.display_name}** est provoqué en duel par **{player_a.display_name}**\n\u200b\n",
        colour=EMBED_COLOUR_PRIMARY
    )

    player_a_xp = xp_dict[player_a.id]
    player_b_xp = xp_dict[player_b.id]

    embed.add_field(
        name="Vos points d'XP actuels:",
        value=f"{player_a.display_name} : {player_a_xp} XP\n {player_b.display_name} : {player_b_xp} XP\n\u200b\n",
        inline=True
    )

    embed.add_field(
        name="Points d'XP mis en jeu",
        value=f"{stake_xp} XP",
        inline=True
    )

    game_name, game_description = get_game_text(game_type)

    embed.add_field(
        name="Type de jeu",
        value=f"{game_name}\n{game_description}\n\u200b\n",
        inline=False
    )


    embed.set_footer(text=f"{player_b.display_name} fais ton choix : Accepter ou Refuser ?")
    decorate_thumb_only(embed, None)
    files = common_thumb(None)
    return embed, files



class InviteView(discord.ui.View):
    """View pour l'invitation au duel, avec les boutons Accepter et Refuser."""

    def __init__(self, bot: EldoriaBot, duel_id: int) -> None:
        """Initialise la view avec les boutons Accepter et Refuser."""
        super().__init__(timeout=300)
        self.bot = bot
        self.duel_id = duel_id
        self.duel = bot.services.duel
        
    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.secondary)
    async def accept(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """Gère le clic sur le bouton Accepter."""
        await interaction.response.defer()

        try:
            snapshot = self.duel.accept_duel(duel_id=self.duel_id, user_id=require_user_id(interaction=interaction))
            snapshot.get("duel")
        except DuelError as e:
            await interaction.followup.send(content=duel_error_message(e), ephemeral=True)
            return

        guild = require_guild(interaction=interaction)

        try:
            embed, _, view = await render_duel_message(snapshot=snapshot, guild=guild, bot=self.bot)
        except Exception:
            # fallback minimal si jamais un renderer n'existe pas encore
            await interaction.followup.send(content="Le duel a été accepté, mais l'UI du jeu n'est pas encore prête.", ephemeral=True)
            return

        msg = interaction.message
        if msg is None:
            await interaction.followup.send(content="Impossible de modifier le message (message introuvable).", ephemeral=True)
            return

        # On édite le message d'invite (celui avec les boutons accepter/refuser)
        await msg.edit(content=msg.content or "", embed=embed, view=view)


    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.secondary)
    async def refuse(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """Gère le clic sur le bouton Refuser."""
        await interaction.response.defer()

        try:
            snapshot = self.duel.refuse_duel(duel_id=self.duel_id, user_id=require_user_id(interaction=interaction))
        except DuelError as e:
            await interaction.followup.send(content=duel_error_message(e), ephemeral=True)
            return
        
        player_b_id = snapshot["duel"]["player_b"]
        guild = require_guild(interaction=interaction)
        
        try:
            player_b = await get_member_by_id_or_raise(guild, player_b_id)
        except ValueError:
            await interaction.edit_original_response(content="Un des participants n'a pas pu être trouvé.", embeds=[], attachments=[], view=None)
            return
        
        embed, _ = await build_refuse_duels_embed(player_b=player_b)
        
        message_id = snapshot["duel"]["message_id"]
        channel_id = snapshot["duel"]["channel_id"]
        channel = await get_text_or_thread_channel(bot=self.bot, channel_id=channel_id)
        message = await channel.fetch_message(message_id) 

        await message.edit( content="", embed=embed, view=None)