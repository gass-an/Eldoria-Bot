"""Module de la vue pour retirer des salons vocaux temporaires."""
from __future__ import annotations

import discord

from eldoria.features.temp_voice.temp_voice_service import TempVoiceService
from eldoria.ui.common.components import BasePanelView, RoutedButton, RoutedSelect
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_ERROR
from eldoria.ui.common.embeds.images import decorate


def build_tempvoice_remove_embed(
    *,
    configured: list[tuple[discord.VoiceChannel, int]],
    selected: discord.VoiceChannel | None,
) -> discord.Embed:
    """Embed de l'écran Retirer un salon parent."""
    embed = discord.Embed(
        title="🔴 Retirer un salon parent",
        description="Sélectionne un salon configuré, puis supprime-le.\n\u200b\n",
        color=EMBED_COLOUR_ERROR,
    )

    if configured:
        lines = [f"- {ch.mention} (limite: **{limit}**)" for ch, limit in configured]
        embed.add_field(name="Salons configurés", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Salons configurés", value="Aucun salon parent configuré.", inline=False)

    embed.add_field(
        name="Sélection",
        value=selected.mention if selected else "Aucune",
        inline=False,
    )

    embed.set_footer(text="Seule la configuration sera retirée. Les salons créés ne seront pas supprimés.")
    decorate(embed, None, None)
    return embed

class TempVoiceRemoveView(BasePanelView):
    """Écran Retirer.
    
    - Select : salons déjà configurés (parents)
    - Bouton : supprimer
    - Bouton : retour
    """

    def __init__(self, *, temp_voice_service: TempVoiceService, author_id: int, guild: discord.Guild) -> None:
        """Initialise la vue de suppression de salons vocaux temporaires avec une référence au temp_voice_service, à l'auteur de l'interaction et à la guild."""
        super().__init__(author_id=author_id)
        self.temp_voice = temp_voice_service
        self.guild = guild

        self.selected_channel: discord.VoiceChannel | None = None

        self._render()

    def _get_configured(self) -> list[tuple[discord.VoiceChannel, int]]:
        """Retourne [(VoiceChannel, user_limit), ...] à partir de list_parents().
        
        list_parents(guild_id) -> list[tuple[parent_channel_id, user_limit]]
        """
        parents: list[tuple[int, int]] = self.temp_voice.list_parents(self.guild.id)
    
        configured: list[tuple[discord.VoiceChannel, int]] = []
        for channel_id, user_limit in parents:
            ch = self.guild.get_channel(channel_id)
            if isinstance(ch, discord.VoiceChannel):
                configured.append((ch, user_limit))
        return configured

    def current_embed(self) -> discord.Embed:
        """Construit l'embed de la vue de suppression de salons vocaux temporaires en fonction des salons configurés et du salon sélectionné."""
        configured = self._get_configured()
        return build_tempvoice_remove_embed(configured=configured, selected=self.selected_channel)

    def _render(self) -> None:
        self.clear_items()

        configured = self._get_configured()
        options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch, _limit in configured[:25]]

        self.add_item(RoutedSelect(
            placeholder="Sélectionner un salon configuré…",
            options=options if options else [discord.SelectOption(label="Aucun salon configuré", value="none")],
            custom_id="tv:remove:select",
            disabled=(len(options) == 0),
            row=0,
        ))
        
        self.add_item(RoutedButton(label="Retour", style=discord.ButtonStyle.secondary, custom_id="tv:back", emoji="⬅️", row=1))

        self.add_item(RoutedButton(
            label="Supprimer",
            style=discord.ButtonStyle.danger,
            custom_id="tv:remove:delete",
            disabled=(self.selected_channel is None),
            emoji="🗑️",
            row=1,
            ))

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Route les interactions des boutons en fonction de leur custom_id."""
        cid = (interaction.data or {}).get("custom_id")

        if cid == "tv:back":
            from .home import TempVoiceHomeView  # import local pour éviter cycles

            home = TempVoiceHomeView(temp_voice_service=self.temp_voice, author_id=self.author_id, guild=self.guild)
            embed, _ = home.current_embed()
            await interaction.response.edit_message(embed=embed, view=home)
            return

        if cid == "tv:remove:delete":
            if self.selected_channel is None:
                return

            self.temp_voice.delete_parent(self.guild.id, self.selected_channel.id)

            self.selected_channel = None
            self._render()
            await interaction.response.edit_message(embed=self.current_embed(), view=self)
            return

        await interaction.response.defer()

    async def route_select(self, interaction: discord.Interaction, values: list[str]) -> None:
        """Route les interactions du select en fonction de leur custom_id."""
        cid = (interaction.data or {}).get("custom_id")

        if cid == "tv:remove:select":
            if not values or values[0] == "none":
                await interaction.response.defer()
                return

            channel_id = int(values[0])
            ch = self.guild.get_channel(channel_id)
            if isinstance(ch, discord.VoiceChannel):
                self.selected_channel = ch

            self._render()
            await interaction.response.edit_message(embed=self.current_embed(), view=self)
            return

        await interaction.response.defer()
