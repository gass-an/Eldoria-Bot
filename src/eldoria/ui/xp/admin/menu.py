"""Panneau d'administration du système XP."""

from __future__ import annotations

import discord

from eldoria.features.xp.xp_service import XpService
from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.xp.admin.embeds import build_xp_admin_menu_embed


class XpAdminMenuView(BasePanelView):
    """Vue du panneau d'administration général du système XP."""

    def __init__(self, *, xp: XpService, author_id: int, guild: discord.Guild) -> None:
        """Initialise la vue du panneau d'administration général du système XP."""
        super().__init__(author_id=author_id)
        self.xp = xp
        self.guild = guild

        self.xp.ensure_defaults(guild.id)
        cfg = self.xp.get_config(guild.id)
        enabled = bool(cfg.get("enabled"))

        # Toggle XP global
        self.add_item(
            RoutedButton(
                label="Activer XP",
                style=discord.ButtonStyle.success,
                custom_id="xp:enable",
                disabled=enabled,
                row=0,
            )
        )
        self.add_item(
            RoutedButton(
                label="Désactiver XP",
                style=discord.ButtonStyle.danger,
                custom_id="xp:disable",
                disabled=not enabled,
                row=0,
            )
        )

        # Navigation
        self.add_item(RoutedButton(
            label="Paramètres", 
            disabled= not enabled, 
            style=discord.ButtonStyle.secondary, 
            custom_id="xp:nav:settings", 
            emoji="⚙️", 
            row=1
            ))
        
        self.add_item(RoutedButton(
            label="Vocal",
            disabled= not enabled,
            style=discord.ButtonStyle.secondary,
            custom_id="xp:nav:voice",
            emoji="🎙️",
            row=1
            ))
        
        self.add_item(RoutedButton(
            label="Niveaux & rôles", 
            disabled= not enabled,
            style=discord.ButtonStyle.secondary,
            custom_id="xp:nav:levels",
            emoji="🏅",
            row=1
            ))

    def current_embed(self) -> tuple[discord.Embed, list[discord.File]]:
        """Construit l'embed du panneau d'administration général du système XP."""
        cfg = self.xp.get_config(self.guild.id)
        return build_xp_admin_menu_embed(cfg)

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Route les interactions des boutons du panneau d'administration général du système XP."""
        cid = (interaction.data or {}).get("custom_id")
        gid = self.guild.id

        if cid == "xp:enable":
            self.xp.ensure_defaults(gid)
            self.xp.set_config(gid, enabled=True)
            view = XpAdminMenuView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "xp:disable":
            self.xp.ensure_defaults(gid)
            self.xp.set_config(gid, enabled=False)
            view = XpAdminMenuView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "xp:nav:settings":
            from eldoria.ui.xp.admin.settings import XpAdminSettingsView  # local import (no cycle)
            view = XpAdminSettingsView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "xp:nav:voice":
            from eldoria.ui.xp.admin.voice import XpAdminVoiceView  # local import (no cycle)
            view = XpAdminVoiceView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "xp:nav:levels":
            from eldoria.ui.xp.admin.levels import XpAdminLevelsView  # local import (no cycle)
            view = XpAdminLevelsView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await interaction.response.defer()