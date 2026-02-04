from __future__ import annotations

import discord

from eldoria.exceptions.duel_exceptions import DuelError
from eldoria.exceptions.duel_ui_errors import duel_error_message
from eldoria.features.duel.duel_service import play_game_action
from eldoria.features.duel.games.rps.rps_constants import (
    RPS_MOVE_PAPER,
    RPS_MOVE_ROCK,
    RPS_MOVE_SCISSORS,
)
from eldoria.ui.duels.apply import apply_duel_snapshot
from eldoria.utils.discord_utils import require_user_id


class RpsView(discord.ui.View):
    def __init__(self, *, bot: object, duel_id: int):
        super().__init__(timeout=600)
        self.bot = bot
        self.duel_id = duel_id

    async def _play(self, interaction: discord.Interaction, move: str) -> None:
        await interaction.response.defer()

        try:
            snapshot = play_game_action(
                duel_id=self.duel_id,
                user_id=require_user_id(interaction=interaction),
                action={"move": move},
            )
        except DuelError as e:
            await interaction.followup.send(content=duel_error_message(e), ephemeral=True)
            return

        # re-render the same message
        from eldoria.ui.duels.render import render_duel_message  # local import to avoid cycles
        await apply_duel_snapshot(interaction=interaction, snapshot=snapshot, bot=self.bot)

    @discord.ui.button(label="🪨 Pierre", style=discord.ButtonStyle.secondary)
    async def rock(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._play(interaction, RPS_MOVE_ROCK)

    @discord.ui.button(label="📄 Feuille", style=discord.ButtonStyle.secondary)
    async def paper(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._play(interaction, RPS_MOVE_PAPER)

    @discord.ui.button(label="✂️ Ciseaux", style=discord.ButtonStyle.secondary)
    async def scissors(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._play(interaction, RPS_MOVE_SCISSORS)
