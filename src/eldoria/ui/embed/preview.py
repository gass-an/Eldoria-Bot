"""Construction et validation de l'aperçu d'un embed personnalisé."""

from __future__ import annotations

import discord

from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_thumb, decorate_thumb_only


def build_custom_embed(
    *,
    title: str,
    content: str,
    footer: str,
    author: discord.Member,
) -> discord.Embed:
    """Construit l'embed en identifiant explicitement l'administrateur qui le publie."""
    embed = discord.Embed(title=title, description=content, color=EMBED_COLOUR_PRIMARY)

    avatar = getattr(author, "display_avatar", None)
    avatar_url = str(avatar.url) if avatar is not None else None
    embed.set_author(name=f"Publié par {author.display_name}", icon_url=avatar_url)

    if footer:
        embed.set_footer(text=footer)
    decorate_thumb_only(embed, None)
    return embed


class EmbedPreviewView(BasePanelView):
    """Aperçu éphémère permettant de publier ou d'annuler l'embed."""

    def __init__(
        self,
        *,
        author_id: int,
        channel: discord.TextChannel,
        embed: discord.Embed,
        role: discord.Role | None,
    ) -> None:
        """Initialise les actions de confirmation associées à l'aperçu."""
        super().__init__(author_id=author_id)
        self.channel = channel
        self.embed = embed
        self.role = role
        self.completed = False

        self.add_item(
            RoutedButton(
                label="Publier",
                style=discord.ButtonStyle.success,
                custom_id="embed:publish",
                emoji="✅",
            )
        )
        self.add_item(
            RoutedButton(
                label="Annuler",
                style=discord.ButtonStyle.danger,
                custom_id="embed:cancel",
                emoji="✖️",
            )
        )

    def can_mention_role(self) -> bool:
        """Indique si Discord autorisera réellement le bot à notifier le rôle choisi."""
        if self.role is None or self.role.mentionable:
            return True

        guild = self.channel.guild
        bot_member = guild.me if guild is not None else None
        if bot_member is None:
            return False

        permissions = self.channel.permissions_for(bot_member)
        return permissions.mention_everyone

    async def route_button(self, interaction: discord.Interaction) -> None:
        """Publie l'embed ou annule la création selon le bouton utilisé."""
        cid = (interaction.data or {}).get("custom_id")

        if self.completed:
            await interaction.response.send_message("Cette action a déjà été traitée.", ephemeral=True)
            return

        if cid == "embed:cancel":
            self.completed = True
            await interaction.response.edit_message(
                content="❌ Publication annulée.",
                embed=None,
                attachments=[],
                view=None,
            )
            return

        if cid != "embed:publish":
            await interaction.response.defer()
            return

        if not self.can_mention_role():
            await interaction.response.send_message(
                "❌ Je ne peux pas notifier ce rôle. Active son option **Autoriser tout le monde à "
                "mentionner ce rôle**, ou accorde-moi la permission **Mentionner @everyone, @here "
                "et tous les rôles**.",
                ephemeral=True,
            )
            return

        # Acquitte immédiatement le clic : l'envoi des images peut dépasser
        # la fenêtre de réponse de Discord (environ trois secondes).
        await interaction.response.defer()

        allowed_mentions = discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=[self.role] if self.role is not None else False,
            replied_user=False,
        )
        content = f"|| {self.role.mention} ||" if self.role is not None else None
        try:
            files = common_thumb(None)
            message = await self.channel.send(
                content=content,
                embed=self.embed,
                files=files,
                allowed_mentions=allowed_mentions,
            )
        except discord.Forbidden:
            await interaction.edit_original_response(
                content="❌ Je n'ai pas la permission de publier dans ce salon.",
                embed=self.embed,
                view=self,
            )
            return
        except discord.HTTPException:
            await interaction.edit_original_response(
                content="⚠️ Discord n'a pas pu publier l'embed. Réessaie dans quelques secondes.",
                embed=self.embed,
                view=self,
            )
            return

        self.completed = True
        message_link = getattr(message, "jump_url", None)
        confirmation = f"✅ Embed publié dans {self.channel.mention}."
        if message_link:
            confirmation += f" [Voir le message]({message_link})"
        await interaction.edit_original_response(
            content=confirmation,
            embed=None,
            attachments=[],
            view=None,
        )
