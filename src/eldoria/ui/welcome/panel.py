"""Panel de configuration des messages de bienvenue (/welcome) : activation/désactivation + choix du salon."""

from __future__ import annotations

import discord

from eldoria.features.welcome.welcome_service import WelcomeService
from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_ERROR, EMBED_COLOUR_VALIDATION
from eldoria.ui.common.embeds.images import common_files, decorate


def build_welcome_panel_embed(
    *,
    enabled: bool,
    channel: discord.abc.GuildChannel | None,
) -> tuple[discord.Embed, list[discord.File]]:
    """Construit l'embed du panneau de configuration des messages de bienvenue en fonction de l'état actuel (activé/désactivé, salon configuré)."""
    colour = EMBED_COLOUR_VALIDATION if enabled else EMBED_COLOUR_ERROR

    status = "✅ Activé" if enabled else "⛔ Désactivé"
    channel_txt = channel.mention if channel is not None else "*(aucun salon configuré)*"

    embed = discord.Embed(
        title="👋 Messages de bienvenue",
        description=(
            f"**État :** {status}\n"
            f"**Salon :** {channel_txt}\n\n"
            "Utilise les boutons pour activer/désactiver, puis sélectionne un salon si activé.\n\u200b\n"
        ),
        color=colour,
    )

    if enabled and channel is None:
        embed.add_field(
            name="⚠️ Salon manquant",
            value="Les messages sont activés, mais aucun salon n'est configuré. Sélectionne un salon ci-dessous.",
            inline=False,
        )

    embed.set_footer(text="Configure les messages de bienvenue de ton serveur.")
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files


class WelcomePanelView(BasePanelView):
    """Panneau /welcome (activation + choix salon)."""

    def __init__(self, *, welcome_service: WelcomeService, author_id: int, guild: discord.Guild) -> None:
        """Initialise la vue du panneau de configuration des messages de bienvenue avec une référence au welcome_service, à l'auteur de l'interaction et à la guild."""
        super().__init__(author_id=author_id)
        self.welcome = welcome_service
        self.guild = guild

        self.welcome.ensure_defaults(guild.id)
        cfg = self.welcome.get_config(guild.id)

        self.enabled: bool = bool(cfg.get("enabled"))
        channel_id = int(cfg.get("channel_id") or 0)
        self.channel: discord.abc.GuildChannel | None = guild.get_channel(channel_id) if channel_id else None

        # Buttons (row 0)
        self.add_item(
            RoutedButton(
                label="Activer",
                style=discord.ButtonStyle.success,
                custom_id="wm:enable",
                disabled=self.enabled,
                row=0,
            )
        )
        self.add_item(
            RoutedButton(
                label="Désactiver",
                style=discord.ButtonStyle.danger,
                custom_id="wm:disable",
                disabled=not self.enabled,
                row=0,
            )
        )

        # ChannelSelect (row 1) uniquement si activé
        if self.enabled:
            placeholder = "Choisir un salon de bienvenue…"
            if self.channel is not None:
                placeholder = f"Salon actuel : #{self.channel.name}"

            # IMPORTANT: on instancie dynamiquement au lieu d'un decorator
            channel_select = discord.ui.ChannelSelect(
                placeholder=placeholder,
                custom_id="wm:channel",
                channel_types=[discord.ChannelType.text, discord.ChannelType.news],
                min_values=1,
                max_values=1,
                row=1,
            )

            async def _on_channel_select(interaction: discord.Interaction) -> None:
                if not channel_select.values:
                    await interaction.response.defer()
                    return

                ch = channel_select.values[0]
                guild_id = self.guild.id

                self.welcome.ensure_defaults(guild_id)
                self.welcome.set_config(guild_id, channel_id=ch.id, enabled=True)

                view = WelcomePanelView(welcome_service=self.welcome, author_id=self.author_id, guild=self.guild)
                embed, _files = view.current_embed()
                await interaction.response.edit_message(embed=embed, view=view)

            channel_select.callback = _on_channel_select  # type: ignore[attr-defined]
            self.add_item(channel_select)

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Route les interactions des boutons en fonction de leur custom_id."""
        cid = (interaction.data or {}).get("custom_id")
        guild_id = self.guild.id

        if cid == "wm:enable":
            self.welcome.ensure_defaults(guild_id)
            self.welcome.set_enabled(guild_id, True)

            view = WelcomePanelView(welcome_service=self.welcome, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "wm:disable":
            self.welcome.ensure_defaults(guild_id)
            self.welcome.set_enabled(guild_id, False)

            view = WelcomePanelView(welcome_service=self.welcome, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await interaction.response.defer()

    def current_embed(self) -> tuple[discord.Embed, list[discord.File]]:
        """Construit l'embed du panneau de configuration des messages de bienvenue en fonction de l'état actuel (activé/désactivé, salon configuré)."""
        return build_welcome_panel_embed(enabled=self.enabled, channel=self.channel)