"""UI de configuration des vocaux temporaires - écran Ajouter un salon parent."""
from __future__ import annotations

import discord

from eldoria.features.temp_voice.temp_voice_service import TempVoiceService
from eldoria.ui.common.components import BasePanelView, RoutedButton, RoutedSelect
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_VALIDATION
from eldoria.ui.common.embeds.images import decorate
from eldoria.ui.temp_voice.modals import UserLimitModal


def build_tempvoice_add_embed(
    *,
    selected_channel: discord.VoiceChannel | None,
    user_limit: int | None,
    last_saved: tuple[discord.VoiceChannel, int] | None = None,
) -> discord.Embed:
    """Embed de l'écran Ajouter un salon parent."""
    embed = discord.Embed(
        title="🟢 Ajouter un salon parent",
        description="\n\u200b\n1. Sélectionne un salon vocal\n2. Défini la limite d'utilisateurs\n3. Enregistre\n\u200b\n",
        color=EMBED_COLOUR_VALIDATION,
    )
    # 🆕 Confirmation visuelle intégrée
    if last_saved is not None:
        channel, limit = last_saved
        embed.add_field(
            name="✅ Configuration enregistrée",
            value=f"{channel.mention} configuré avec une limite de **{limit}** utilisateurs.\n\u200b\n",
            inline=False,
        )
    
    embed.add_field(
        name="Salon sélectionné",
        value=selected_channel.mention if selected_channel else "Aucun",
        inline=True,
    )
    embed.add_field(
        name="Limite d'utilisateurs",
        value=str(user_limit) if user_limit else "Non définie",
        inline=True,
    )

    embed.set_footer(text="Sélectionne un salon parent pour les vocaux temporaires.")
    decorate(embed, None, None)
    return embed


class TempVoiceAddView(BasePanelView):
    """Écran Ajouter.

    - Select : salons vocaux existants
    - Bouton : définir limite (Modal)
    - Bouton : enregistrer
    - Bouton : retour
    """

    def __init__(self, *, temp_voice_service: TempVoiceService, author_id: int, guild: discord.Guild) -> None:
        """Initialise la vue d'ajout de salons vocaux temporaires avec une référence au temp_voice_service, à l'auteur de l'interaction et à la guild."""
        super().__init__(author_id=author_id)
        self.temp_voice = temp_voice_service
        self.guild = guild

        self.selected_channel: discord.VoiceChannel | None = None
        self.user_limit: int | None = None
        self.last_saved: tuple[discord.VoiceChannel, int] | None = None

        self._render()

    def current_embed(self) -> discord.Embed:
        """Construit l'embed de l'écran Ajouter un salon parent en fonction du salon sélectionné et de la limite d'utilisateurs."""
        return build_tempvoice_add_embed(
            selected_channel=self.selected_channel,
            user_limit=self.user_limit,
            last_saved=self.last_saved,
            )

    def _render(self) -> None:
        self.clear_items()

        # Select channels (limite 25)
        options = [discord.SelectOption(label=ch.name, value=str(ch.id)) for ch in self.guild.voice_channels[:25]]
        if not options:
            options = [discord.SelectOption(label="Aucun salon vocal", value="none")]

        select = RoutedSelect(
            placeholder="Sélectionner un salon vocal…",
            options=options,
            custom_id="tv:add:select",
            disabled=(options[0].value == "none"),
        )

        btn_limit = RoutedButton(label="Définir limite", style=discord.ButtonStyle.primary, custom_id="tv:add:limit")
        btn_save = RoutedButton(
            label="Enregistrer",
            style=discord.ButtonStyle.success,
            custom_id="tv:add:save",
            disabled=not (self.selected_channel and self.user_limit),
            emoji="✅",
        )
        btn_back = RoutedButton(label="Retour", style=discord.ButtonStyle.secondary, custom_id="tv:back")

        self.add_item(select)
        self.add_item(btn_limit)
        self.add_item(btn_save)
        self.add_item(btn_back)

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Route les interactions des boutons en fonction de leur custom_id."""
        cid = (interaction.data or {}).get("custom_id")

        if cid == "tv:back":
            # retour home : on reconstruit un HomeView côté caller, donc ici on re-met embed home + view home
            from .home import TempVoiceHomeView  # import local pour éviter cycles

            home = TempVoiceHomeView(temp_voice_service=self.temp_voice, author_id=self.author_id, guild=self.guild)
            embed, _ = home.current_embed()
            await interaction.response.edit_message(embed=embed, view=home)
            return

        if cid == "tv:add:limit":
            async def on_value(interaction: discord.Interaction, value: int) -> None:
                self.user_limit = value
                self._render()
                await interaction.response.edit_message(embed=self.current_embed(), view=self)

            await interaction.response.send_modal(UserLimitModal(on_value=on_value))
            return

        if cid == "tv:add:save":
            if self.selected_channel is None or self.user_limit is None:
                return

            self.temp_voice.upsert_parent(self.guild.id, self.selected_channel.id, self.user_limit)

            self.last_saved = (self.selected_channel, self.user_limit)
            self.selected_channel = None
            self.user_limit = None
            
            self._render()
            await interaction.response.edit_message(embed=self.current_embed(), view=self)
            return

        await interaction.response.defer()

    async def route_select(self, interaction: discord.Interaction, values: list[str]) -> None:
        """Route les interactions du select en fonction de leur custom_id."""
        cid = (interaction.data or {}).get("custom_id")

        if cid == "tv:add:select":
            if values and values[0] != "none":
                channel_id = int(values[0])
                ch = self.guild.get_channel(channel_id)
                if isinstance(ch, discord.VoiceChannel):
                    self.selected_channel = ch

            self._render()
            await interaction.response.edit_message(embed=self.current_embed(), view=self)
            return

        await interaction.response.defer()
