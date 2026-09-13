"""Formulaire de création d'un embed personnalisé."""

from __future__ import annotations

import discord

from eldoria.ui.common.embeds.images import common_thumb
from eldoria.ui.embed.preview import EmbedPreviewView, build_custom_embed


class EmbedModal(discord.ui.Modal):
    """Formulaire demandant le titre, le contenu et le footer de l'embed."""

    def __init__(
        self,
        *,
        channel: discord.TextChannel,
        author: discord.Member,
        role: discord.Role | None,
    ) -> None:
        """Initialise le formulaire avec sa cible et l'administrateur à l'origine de l'envoi."""
        super().__init__(title="Créer un embed")
        self.channel = channel
        self.author = author
        self.role = role

        self.title_input = discord.ui.InputText(
            label="Titre",
            placeholder="Titre de l'annonce",
            required=True,
            min_length=1,
            max_length=256,
        )
        self.content_input = discord.ui.InputText(
            label="Contenu",
            placeholder="Contenu de l'annonce",
            required=True,
            min_length=1,
            max_length=4000,
            style=discord.InputTextStyle.long,
        )
        self.footer_input = discord.ui.InputText(
            label="Footer (optionnel)",
            placeholder="Texte affiché en bas de l'embed",
            required=False,
            max_length=2048,
        )

        self.add_item(self.title_input)
        self.add_item(self.content_input)
        self.add_item(self.footer_input)

    async def callback(self, interaction: discord.Interaction) -> None:
        """Affiche un aperçu éphémère de l'embed avant sa publication."""
        embed = build_custom_embed(
            title=(self.title_input.value or "").strip(),
            content=(self.content_input.value or "").strip(),
            footer=(self.footer_input.value or "").strip(),
            author=self.author,
        )
        view = EmbedPreviewView(
            author_id=self.author.id,
            channel=self.channel,
            embed=embed,
            role=self.role,
        )
        role_status = self.role.mention if self.role is not None else "aucun"
        files = common_thumb(None)
        await interaction.response.send_message(
            content=(
                f"**Aperçu avant publication dans {self.channel.mention}**\n"
                f"Rôle mentionné : {role_status}."
            ),
            embed=embed,
            files=files,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
