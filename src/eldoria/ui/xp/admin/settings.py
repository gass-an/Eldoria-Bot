"""Panneau d'administration des paramètres généraux du système XP."""

from __future__ import annotations

import discord

from eldoria.features.xp.xp_service import XpService
from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.xp.admin.embeds import build_xp_admin_settings_embed
from eldoria.ui.xp.admin.menu import XpAdminMenuView
from eldoria.ui.xp.admin.modals import XpSettingsModal


class XpAdminSettingsView(BasePanelView):
    """Vue du panneau d'administration des paramètres généraux du système XP."""

    def __init__(self, *, xp: XpService, author_id: int, guild: discord.Guild) -> None:
        """Initialise la vue du panneau d'administration des paramètres généraux du système XP."""
        super().__init__(author_id=author_id)
        self.xp = xp
        self.guild = guild

        # Controls
        self.add_item(RoutedButton(label="Retour", style=discord.ButtonStyle.secondary, custom_id="xp:back", emoji="⬅️", row=0))
        self.add_item(RoutedButton(label="Modifier", style=discord.ButtonStyle.primary, custom_id="xp:set:settings", emoji="✏️", row=0))

    def current_embed(self) -> tuple[discord.Embed, list[discord.File]]:
        """Construit l'embed du panneau d'administration des paramètres généraux du système XP."""
        cfg = self.xp.get_config(self.guild.id)
        return build_xp_admin_settings_embed(cfg)

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Route les interactions des boutons du panneau d'administration des paramètres généraux du système XP."""
        cid = (interaction.data or {}).get("custom_id")
        gid = self.guild.id

        if cid == "xp:set:settings":
            current = self.xp.get_config(gid)

            async def _on_submit(modal_inter: discord.Interaction, payload: dict) -> None:
                # remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                if not payload:
                    await modal_inter.response.send_message("INFO: Aucun champ fourni : aucune modification appliquée.", ephemeral=True)
                    return

                self.xp.ensure_defaults(gid)
                self.xp.set_config(gid, **payload)
                view = XpAdminSettingsView(xp=self.xp, author_id=self.author_id, guild=self.guild)
                embed, _files = view.current_embed()
                await modal_inter.response.defer()
                await modal_inter.edit_original_response(embed=embed, view=view)

            await interaction.response.send_modal(XpSettingsModal(on_submit=_on_submit, current=current))
            return

        if cid == "xp:back":
            view = XpAdminMenuView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await interaction.response.defer()