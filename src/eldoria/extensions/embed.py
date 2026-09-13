"""Cog permettant aux administrateurs de publier des embeds personnalisés."""

from typing import cast

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.embed.modal import EmbedModal
from eldoria.utils.guards import require_guild_ctx


class Embed(commands.Cog):
    """Commandes de création et de publication d'embeds personnalisés."""

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog avec une référence au bot."""
        self.bot = bot

    @commands.slash_command(
        name="embed",
        description="(Admin) Crée et publie un embed dans le salon choisi.",
    )
    @discord.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @discord.option(
        "role",
        description="Rôle à mentionner au-dessus de l'embed (optionnel).",
    )
    async def create_embed(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
        role: discord.Role | None = None,
    ) -> None:
        """Ouvre le formulaire de création d'un embed et propose un aperçu avant envoi."""
        guild, _channel = require_guild_ctx(ctx)
        if role is not None and role.id == guild.id:
            await ctx.respond("❌ Le rôle `@everyone` ne peut pas être mentionné.", ephemeral=True)
            return

        author = cast(discord.Member, ctx.author)

        modal = EmbedModal(
            channel=channel,
            author=author,
            role=role,
        )
        await ctx.send_modal(modal)


def setup(bot: EldoriaBot) -> None:
    """Ajoute le cog de création d'embeds au bot."""
    bot.add_cog(Embed(bot))
