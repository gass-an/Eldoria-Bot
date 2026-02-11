"""Module de pagination pour les embeds."""

from collections.abc import Awaitable, Callable, Sequence
from math import ceil
from typing import Any

import discord
from discord.ui import Button, View

EmbedGenerator = Callable[
    [Sequence[Any], int, int, Any, Any],
    Awaitable[tuple[discord.Embed, list[discord.File] | None]]
]


class Paginator(View):
    """View de pagination pour les embeds.

    - items: la liste complète des items à paginer
    - embed_generator: une fonction asynchrone qui génère un embed à partir d'une page d'items
    - identifiant_for_embed: un identifiant optionnel à passer à l'embed_generator (ex: user_id pour un profil)
    - bot: instance du bot, à passer à l'embed_generator si besoin
    """

    def __init__(
        self,
        items: Sequence[Any],
        embed_generator: EmbedGenerator | None = None,
        identifiant_for_embed: Any | None = None,
        bot: Any | None = None,
    ) -> None:
        """Initialise la pagination avec les items et la fonction de génération d'embed."""
        super().__init__(timeout=240)

        self.items: Sequence[Any] = items
        self.page_size: int = 10
        self.current_page: int = 0
        self.total_pages: int = ceil(len(items) / self.page_size)
        self.embed_generator: EmbedGenerator | None = embed_generator
        self.identifiant_for_embed: Any | None = identifiant_for_embed
        self.bot: Any | None = bot

        self.previous_button: Button = Button(
            label="Précédent",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        self.next_button: Button = Button(
            label="Suivant",
            style=discord.ButtonStyle.secondary,
        )

        self.previous_button.callback = self.previous_page
        self.next_button.callback = self.next_page

        self.add_item(self.previous_button)
        self.add_item(self.next_button)

    async def create_embed(self) -> tuple[discord.Embed, list[discord.File] | None]:
        """Crée l'embed de la première page à afficher."""
        embed, files = await self.embed_generator(
            self.items[:self.page_size],
            0,
            self.total_pages,
            self.identifiant_for_embed,
            self.bot,
        )
        return embed, files

    async def update_embed(self, interaction: discord.Interaction) -> None:
        """Met à jour l'embed affiché en fonction de la page courante."""
        start_index: int = self.current_page * self.page_size
        end_index: int = start_index + self.page_size
        page_items: Sequence[Any] = self.items[start_index:end_index]

        embed, _ = await self.embed_generator(
            page_items,
            self.current_page,
            self.total_pages,
            self.identifiant_for_embed,
            self.bot,
        )

        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

        await interaction.response.edit_message(embed=embed, view=self)

    async def previous_page(self, interaction: discord.Interaction) -> None:
        """Affiche la page précédente si possible."""
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_embed(interaction)

    async def next_page(self, interaction: discord.Interaction) -> None:
        """Affiche la page suivante si possible."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        await self.update_embed(interaction)
        