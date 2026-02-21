"""Panneau d'administration des paramètres généraux du système XP."""

from __future__ import annotations

import discord

from eldoria.features.xp.xp_service import XpService
from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.xp.admin.embeds import build_xp_admin_voice_embed
from eldoria.ui.xp.admin.menu import XpAdminMenuView
from eldoria.ui.xp.admin.modals import XpVoiceModal


class XpAdminVoiceView(BasePanelView):
    """Vue du panneau d'administration des paramètres liés à l'XP vocal."""

    def __init__(self, *, xp: XpService, author_id: int, guild: discord.Guild) -> None:
        """Initialise la vue du panneau d'administration des paramètres liés à l'XP vocal."""
        super().__init__(author_id=author_id)
        self.xp = xp
        self.guild = guild

        self.xp.ensure_defaults(guild.id)
        self.cfg = self.xp.get_config(guild.id)

        voice_enabled = bool(self.cfg.get("voice_enabled"))
        voice_channel_id = int(self.cfg.get("voice_levelup_channel_id") or 0)
        self.voice_channel = guild.get_channel(voice_channel_id) if voice_channel_id else None

        self.add_item(RoutedButton(label="Retour", style=discord.ButtonStyle.secondary, custom_id="xp:back", emoji="⬅️", row=0))

        self.add_item(
            RoutedButton(
                label="Activer vocal",
                style=discord.ButtonStyle.success,
                custom_id="xp:voice:on",
                disabled=voice_enabled,
                row=0,
            )
        )

        self.add_item(
            RoutedButton(
                label="Désactiver vocal",
                style=discord.ButtonStyle.danger,
                custom_id="xp:voice:off",
                disabled=not voice_enabled,
                row=0,
            )
        )

        self.add_item(RoutedButton(
            label="Modifier",
            disabled=not voice_enabled,
            style=discord.ButtonStyle.primary,
            custom_id="xp:voice:modal",
            emoji="✏️",
            row=0
            ))

        # Channel select (only useful even if voice off, allow setting it)
        placeholder = "Choisir le salon d'annonces…"
        if self.voice_channel is not None:
            placeholder = f"Salon actuel : #{self.voice_channel.name}"

        channel_select = discord.ui.ChannelSelect(
            placeholder=placeholder,
            custom_id="xp:voice:channel",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
            disabled=not voice_enabled,
            row=1,
        )

        async def _on_channel_select(interaction: discord.Interaction) -> None:
            if not channel_select.values:
                await interaction.response.defer()
                return

            ch = channel_select.values[0]
            self.xp.ensure_defaults(guild.id)
            self.xp.set_config(guild.id, voice_levelup_channel_id=ch.id)

            view = XpAdminVoiceView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)

        channel_select.callback = _on_channel_select  # type: ignore[attr-defined]
        self.add_item(channel_select)
        

    def current_embed(self) -> tuple[discord.Embed, list[discord.File]]:
        """Construit l'embed du panneau d'administration des paramètres liés à l'XP vocal."""
        cfg = self.xp.get_config(self.guild.id)
        voice_channel_id = int(cfg.get("voice_levelup_channel_id") or 0)
        channel = self.guild.get_channel(voice_channel_id) if voice_channel_id else None
        return build_xp_admin_voice_embed(cfg, channel)

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Route les interactions des boutons du panneau d'administration des paramètres liés à l'XP vocal."""
        cid = (interaction.data or {}).get("custom_id")
        gid = self.guild.id

        if cid == "xp:voice:on":
            self.xp.ensure_defaults(gid)
            self.xp.set_config(gid, voice_enabled=True)
            view = XpAdminVoiceView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "xp:voice:off":
            self.xp.ensure_defaults(gid)
            self.xp.set_config(gid, voice_enabled=False)
            view = XpAdminVoiceView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        if cid == "xp:voice:modal":
            current = self.xp.get_config(gid)

            async def _on_submit(modal_inter: discord.Interaction, payload: dict) -> None:
                payload = {k: v for k, v in payload.items() if v is not None}
                if not payload:
                    await modal_inter.response.send_message("INFO: Aucun champ fourni : aucune modification appliquée.", ephemeral=True)
                    return

                self.xp.ensure_defaults(gid)
                self.xp.set_config(gid, **payload)
                view = XpAdminVoiceView(xp=self.xp, author_id=self.author_id, guild=self.guild)
                embed, _files = view.current_embed()
                await modal_inter.response.defer()
                await modal_inter.edit_original_response(embed=embed, view=view)

            await interaction.response.send_modal(XpVoiceModal(on_submit=_on_submit, current=current))
            return

        if cid == "xp:back":
            view = XpAdminMenuView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await interaction.response.defer()