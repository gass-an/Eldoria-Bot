"""Panneau d'administration de la configuration des niveaux du système XP."""

from __future__ import annotations

import discord

from eldoria.features.xp.xp_service import XpService
from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.xp.admin.embeds import build_xp_admin_levels_embed
from eldoria.ui.xp.admin.menu import XpAdminMenuView
from eldoria.ui.xp.admin.modals import XpLevelThresholdModal


class XpAdminLevelsView(BasePanelView):
    """Vue du panneau d'administration de la configuration des niveaux du système XP."""

    def __init__(self, *, xp: XpService, author_id: int, guild: discord.Guild, selected_level: int = 1) -> None:
        """Initialise la vue du panneau d'administration de la configuration des niveaux du système XP."""
        super().__init__(author_id=author_id)
        self.xp = xp
        self.guild = guild

        self.xp.ensure_defaults(guild.id)
        self.selected_level = max(1, min(5, selected_level))

        self.levels_with_roles = self.xp.get_levels_with_roles(guild.id)  # (level, xp_required, role_id)

        # pick selected role object
        role_id = next((rid for (lvl, _xp, rid) in self.levels_with_roles if lvl == self.selected_level), None)
        self.selected_role = guild.get_role(role_id) if role_id else None

        self.add_item(RoutedButton(label="Retour", style=discord.ButtonStyle.secondary, custom_id="xp:back", emoji="⬅️", row=0))


        # Select: choose level (1..5)
        level_select = discord.ui.Select(
            placeholder=f"Niveau sélectionné : {self.selected_level}",
            custom_id="xp:levels:pick",
            options=[discord.SelectOption(label=f"Niveau {i}", value=str(i)) for i in range(1, 6)],
            min_values=1,
            max_values=1,
            row=1,
        )

        async def _on_level_pick(interaction: discord.Interaction) -> None:
            try:
                lvl = int(level_select.values[0])
            except Exception:
                await interaction.response.defer()
                return

            view = XpAdminLevelsView(xp=self.xp, author_id=self.author_id, guild=self.guild, selected_level=lvl)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)

        level_select.callback = _on_level_pick  # type: ignore[attr-defined]
        self.add_item(level_select)

        # Buttons
        self.add_item(RoutedButton(label="Fixer XP (modal)", style=discord.ButtonStyle.primary, custom_id="xp:levels:set_xp", emoji="✏️", row=2))

        # Role mapping: try RoleSelect if available, else fallback to existing slash command usage
        if hasattr(discord.ui, "RoleSelect"):
            role_select = discord.ui.RoleSelect(  # type: ignore[attr-defined]
                placeholder="Choisir un rôle pour ce niveau…",
                custom_id="xp:levels:set_role",
                min_values=1,
                max_values=1,
                row=3,
            )

            async def _on_role_select(interaction: discord.Interaction) -> None:
                if not role_select.values:
                    await interaction.response.defer()
                    return
                role = role_select.values[0]
                self.xp.upsert_role_id(self.guild.id, self.selected_level, role.id)

                view = XpAdminLevelsView(xp=self.xp, author_id=self.author_id, guild=self.guild, selected_level=self.selected_level)
                embed, _files = view.current_embed()
                await interaction.response.edit_message(embed=embed, view=view)

            role_select.callback = _on_role_select  # type: ignore[attr-defined]
            self.add_item(role_select)

    def current_embed(self) -> tuple[discord.Embed, list[discord.File]]:
        """Construit l'embed du panneau d'administration de la configuration des niveaux du système XP."""
        return build_xp_admin_levels_embed(
            levels_with_roles=self.levels_with_roles,
            selected_level=self.selected_level,
            selected_role=self.selected_role,
        )

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Route les interactions des boutons du panneau d'administration de la configuration des niveaux du système XP."""
        cid = (interaction.data or {}).get("custom_id")
        gid = self.guild.id

        if cid == "xp:levels:set_xp":
            # current xp for this level
            current_xp = next((xp for (lvl, xp, _rid) in self.levels_with_roles if lvl == self.selected_level), 0)

            async def _on_submit(modal_inter: discord.Interaction, xp_required: int) -> None:
                self.xp.ensure_defaults(gid)
                self.xp.set_level_threshold(gid, self.selected_level, xp_required)

                view = XpAdminLevelsView(xp=self.xp, author_id=self.author_id, guild=self.guild, selected_level=self.selected_level)
                embed, _files = view.current_embed()
                await modal_inter.response.defer()
                await modal_inter.edit_original_response(embed=embed, view=view)

            await interaction.response.send_modal(
                XpLevelThresholdModal(level=self.selected_level, current_xp=current_xp, on_submit=_on_submit)
            )
            return

        if cid == "xp:back":
            view = XpAdminMenuView(xp=self.xp, author_id=self.author_id, guild=self.guild)
            embed, _files = view.current_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            return

        await interaction.response.defer()