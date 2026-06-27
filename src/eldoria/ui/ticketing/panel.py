"""Panneau d'administration /ticketing : activation/désactivation du système de tickets."""

from __future__ import annotations

import discord

from eldoria.features.ticketing.ticketing_service import TicketingService
from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_ERROR, EMBED_COLOUR_VALIDATION
from eldoria.ui.common.embeds.images import common_files, decorate


def build_ticketing_panel_embed(*, enabled: bool, category: discord.CategoryChannel | None, open_channel: discord.abc.GuildChannel | None) -> tuple[discord.Embed, list[discord.File]]:
    colour = EMBED_COLOUR_VALIDATION if enabled else EMBED_COLOUR_ERROR

    status = "✅ Activé" if enabled else "⛔ Désactivé"
    cat_txt = category.mention if category is not None else "*(aucune catégorie configurée)*"
    open_txt = open_channel.mention if open_channel is not None else "*(aucun channel configuré)*"

    embed = discord.Embed(
        title="🎫 Système de tickets",
        description=(
            f"**État :** {status}\n"
            f"**Catégorie :** {cat_txt}\n"
            f"**Salon principal :** {open_txt}\n\n"
            "Active le système pour créer une zone de tickets publique et permettre aux utilisateurs d'ouvrir un ticket via un bouton."
        ),
        color=colour,
    )

    embed.set_footer(text="Configure le système de ticketing de ton serveur.")
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files


class TicketingAdminView(BasePanelView):
    def __init__(self, *, ticketing: TicketingService, author_id: int, guild: discord.Guild) -> None:
        super().__init__(author_id=author_id)
        self.ticketing = ticketing
        self.guild = guild

        self.ticketing.ensure_defaults(guild.id)
        cfg = self.ticketing.get_config(guild.id)

        self.enabled: bool = bool(cfg.get("enabled"))
        category_id = int(cfg.get("category_id") or 0)
        open_channel_id = int(cfg.get("open_channel_id") or 0)

        self.category = guild.get_channel(category_id) if category_id else None
        self.open_channel = guild.get_channel(open_channel_id) if open_channel_id else None

        # Buttons
        self.add_item(RoutedButton(label="Activer", style=discord.ButtonStyle.success, custom_id="tk:enable", disabled=self.enabled, row=0))
        self.add_item(RoutedButton(label="Désactiver", style=discord.ButtonStyle.danger, custom_id="tk:disable", disabled=not self.enabled, row=0))

    def current_embed(self) -> tuple[discord.Embed, list[discord.File]]:
        return build_ticketing_panel_embed(enabled=self.enabled, category=self.category, open_channel=self.open_channel)

    async def route_button(self, interaction: discord.Interaction) -> None:
        cid = (interaction.data or {}).get("custom_id")
        gid = self.guild.id

        if cid == "tk:enable":
            self.ticketing.ensure_defaults(gid)
            self.ticketing.set_enabled(gid, True)
            # Try to trigger the extension helper to create the category / open channel
            try:
                bot = interaction.client
                cog = None
                if hasattr(bot, "get_cog"):
                    cog = bot.get_cog("Ticketing")
                if cog and hasattr(cog, "ensure_setup"):
                    await getattr(cog, "ensure_setup")(self.guild)
            except Exception:
                # ignore failures here but log via interaction
                pass
            view = TicketingAdminView(ticketing=self.ticketing, author_id=self.author_id, guild=self.guild)
            embed, files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "tk:disable":
            self.ticketing.ensure_defaults(gid)
            self.ticketing.set_enabled(gid, False)
            # hide the open channel from @everyone if configured
            try:
                cfg = self.ticketing.get_config(gid)
                open_channel_id = int(cfg.get("open_channel_id") or 0)
                if open_channel_id:
                    ch = self.guild.get_channel(open_channel_id)
                    if ch is not None:
                        await ch.set_permissions(self.guild.default_role, view_channel=False, send_messages=False)
            except Exception:
                pass

            view = TicketingAdminView(ticketing=self.ticketing, author_id=self.author_id, guild=self.guild)
            embed, files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await interaction.response.defer()


