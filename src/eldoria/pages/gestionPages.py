import discord
from discord.ui import Button, View
from math import ceil

class Paginator(View):
    def __init__(self, items, embed_generator=None, identifiant_for_embed=None, bot=None):
        
        super().__init__(timeout=240)
        self.items = items
        self.page_size = 10
        self.current_page = 0
        self.total_pages = ceil(len(items) / self.page_size)
        self.embed_generator = embed_generator
        self.identifiant_for_embed = identifiant_for_embed
        self.bot = bot

        
        self.previous_button = Button(label='Précédent', style=discord.ButtonStyle.secondary, disabled=True)
        self.next_button = Button(label='Suivant', style=discord.ButtonStyle.secondary)
        self.previous_button.callback = self.previous_page
        self.next_button.callback = self.next_page
        self.add_item(self.previous_button)
        self.add_item(self.next_button)


    async def create_embed(self):
        embed,files = await self.embed_generator(self.items[:self.page_size], 0, self.total_pages, self.identifiant_for_embed, self.bot)
        return embed,files


    async def update_embed(self, interaction: discord.Interaction):

        start_index = self.current_page * self.page_size
        end_index = start_index + self.page_size
        page_items = self.items[start_index:end_index]

        embed, _ = await self.embed_generator(page_items, self.current_page, self.total_pages, self.identifiant_for_embed, self.bot)


        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

        await interaction.response.edit_message(embed=embed, view=self)

    async def previous_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_embed(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        await self.update_embed(interaction)

        