import discord

from eldoria.app.bot import EldoriaBot
from eldoria.exceptions.duel_exceptions import DuelError
from eldoria.exceptions.duel_ui_errors import duel_error_message
from eldoria.json_tools.duels_json import get_duel_embed_data
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate
from eldoria.ui.duels.flow.config import StakeXpView, build_config_stake_duels_embed


async def build_home_duels_embed(expires_at: int):
    duel_data = get_duel_embed_data()

    title = duel_data["title"]
    description = duel_data["description"]
    games = duel_data["games"]

    embed = discord.Embed(
        title=f"{title}",
        description=f"La configuration expire <t:{expires_at}:R>\n\n> {description}\n\u200b\n\u200b\n",
        colour=EMBED_COLOUR_PRIMARY
    )

    for game_key, game in games.items():
        game_description = game["description"]
        embed.add_field(
            name=game["name"],
            value=f"> {game_description}",
            inline=False
        )

    embed.set_footer(text="Choisi le jeu ci-dessous.")

    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files


class HomeView(discord.ui.View):
    def __init__(self, bot: EldoriaBot, duel_id: int):
        super().__init__(timeout=600)
        self.bot = bot
        self.duel_id = duel_id
        self.duel = bot.services.duel

        data = get_duel_embed_data()
        games = data.get("games", {})

        for game_key, game in games.items():
            label = game.get("name", str(game_key))[:80]  # Discord limite label à 80

            btn = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary
            )

            # IMPORTANT: on capture game_key avec une valeur par défaut
            async def on_click(interaction: discord.Interaction, gk=game_key):
                await interaction.response.defer()
                try : 
                    snapshot = self.duel.configure_game_type(self.duel_id, gk)
                except DuelError as e:
                    await interaction.edit_original_response(content=duel_error_message(e), embeds=[], attachments=[], view=None)
                    return
                
                expires_at = snapshot["duel"]["expires_at"]
                embed, files = await build_config_stake_duels_embed(expires_at)
                await interaction.edit_original_response(
                    embed=embed, files=files, view=StakeXpView(duel_id=duel_id, bot=bot)
                    )
                

            btn.callback = on_click
            self.add_item(btn)