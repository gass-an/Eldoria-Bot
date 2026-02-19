""""Module des modals pour la gestion des vocaux temporaires."""
from __future__ import annotations

from collections.abc import Callable

import discord


class UserLimitModal(discord.ui.Modal):
    """Modal pour définir la limite d'utilisateurs d'un salon vocal temporaire."""
    
    def __init__(self, *, on_value: Callable) -> None:
        """Initialise la modal avec un champ de saisie pour la limite d'utilisateurs."""
        super().__init__(title="Définir la limite d'utilisateurs")
        self._on_value = on_value

        self.limit_input = discord.ui.InputText(
            label="Limite (1 à 99)",
            placeholder="Ex: 5",
            required=True,
            min_length=1,
            max_length=2,
        )
        self.add_item(self.limit_input)

    async def callback(self, interaction: discord.Interaction) -> None:
        """Lorsque l'utilisateur soumet la modal, valide la saisie et appelle la fonction de rappel avec la valeur."""
        raw = (self.limit_input.value or "").strip()
        try:
            value = int(raw)
        except ValueError:
            await interaction.response.send_message("❌ Merci d'entrer un nombre.", ephemeral=True)
            return

        if not (1 <= value <= 99):
            await interaction.response.send_message("❌ La limite doit être entre 1 et 99.", ephemeral=True)
            return

        await self._on_value(interaction, value)
