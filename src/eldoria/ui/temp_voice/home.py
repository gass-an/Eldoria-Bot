"""UI du menu principal de gestion des vocaux temporaires : boutons Ajouter / Retirer."""
from __future__ import annotations

import discord

from eldoria.features.temp_voice.temp_voice_service import TempVoiceService
from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate
from eldoria.ui.temp_voice.add import TempVoiceAddView
from eldoria.ui.temp_voice.remove import TempVoiceRemoveView


def build_tempvoice_home_embed() -> tuple[discord.Embed, list[discord.File]]:
    """Embed du menu principal de gestion des vocaux temporaires."""
    embed = discord.Embed(
        title="🔊 Vocaux temporaires",
        description="Choisis une action.\n\u200b\n",
        color=EMBED_COLOUR_PRIMARY,
    )
    embed.add_field(name="🟢 Ajouter", value="Configurer un salon parent.\n\u200b\n", inline=True)
    embed.add_field(name="🔴 Retirer", value="Supprimer un salon parent déjà configuré.\n\u200b\n", inline=True)
    embed.set_footer(text="Configure les vocaux temporaires de ton serveur.")
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files

class TempVoiceHomeView(BasePanelView):
    """/tempvoice -> menu principal : boutons Ajouter / Retirer.
    
    Navigation : edit_message(embed=..., view=...)
    """

    def __init__(self, *, temp_voice_service: TempVoiceService, author_id: int, guild: discord.Guild) -> None:
        """Initialise la vue du menu principal de gestion des vocaux temporaires avec une référence au temp_voice_service, à l'auteur de l'interaction et à la guild."""
        super().__init__(author_id=author_id)
        self.temp_voice = temp_voice_service
        self.guild = guild

        self.add_item(RoutedButton(label="Ajouter", style=discord.ButtonStyle.success, custom_id="tv:go:add", emoji="➕"))
        self.add_item(RoutedButton(label="Retirer", style=discord.ButtonStyle.danger, custom_id="tv:go:remove", emoji="➖"))

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Route les interactions des boutons en fonction de leur custom_id."""
        cid = (interaction.data or {}).get("custom_id")

        if cid == "tv:go:add":
            view = TempVoiceAddView(temp_voice_service=self.temp_voice, author_id=self.author_id, guild=self.guild)
            embed = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "tv:go:remove":
            view = TempVoiceRemoveView(temp_voice_service=self.temp_voice, author_id=self.author_id, guild=self.guild)
            embed = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await interaction.response.defer()

    def current_embed(self) -> tuple[discord.Embed, list[discord.File]]:
        """Construit l'embed du menu principal de gestion des vocaux temporaires."""
        return build_tempvoice_home_embed()
