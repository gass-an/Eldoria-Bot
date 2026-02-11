"""Module de la view pour le jeu Pierre-Papier-Ciseaux dans les duels."""

from __future__ import annotations

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.exceptions.duel_exceptions import DuelError
from eldoria.exceptions.duel_ui_errors import duel_error_message
from eldoria.features.duel.games.rps.rps_constants import (
    RPS_MOVE_PAPER,
    RPS_MOVE_ROCK,
    RPS_MOVE_SCISSORS,
)
from eldoria.ui.duels.apply import apply_duel_snapshot
from eldoria.utils.discord_utils import require_user_id


class RpsView(discord.ui.View):
    """View pour le jeu Pierre-Papier-Ciseaux dans les duels."""

    def __init__(self, *, bot: EldoriaBot, duel_id: int) -> None:
        """Initialise la view avec les boutons pour jouer au Pierre-Papier-Ciseaux."""
        super().__init__(timeout=600)
        self.bot = bot
        self.duel_id = duel_id
        self.duel = self.bot.services.duel

    async def _play(self, interaction: discord.Interaction, move: str) -> None:
        await interaction.response.defer()

        try:
            snapshot = self.duel.play_game_action(
                duel_id=self.duel_id,
                user_id=require_user_id(interaction=interaction),
                action={"move": move},
            )
        except DuelError as e:
            await interaction.followup.send(content=duel_error_message(e), ephemeral=True)
            return

        # re-render the same message
        await apply_duel_snapshot(interaction=interaction, snapshot=snapshot, bot=self.bot)

    @discord.ui.button(label="🪨 Pierre", style=discord.ButtonStyle.secondary)
    async def rock(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """Gère le clic sur le bouton Pierre."""
        await self._play(interaction, RPS_MOVE_ROCK)

    @discord.ui.button(label="📄 Feuille", style=discord.ButtonStyle.secondary)
    async def paper(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """Gère le clic sur le bouton Feuille."""
        await self._play(interaction, RPS_MOVE_PAPER)

    @discord.ui.button(label="✂️ Ciseaux", style=discord.ButtonStyle.secondary)
    async def scissors(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        """Gère le clic sur le bouton Ciseaux."""
        await self._play(interaction, RPS_MOVE_SCISSORS)
