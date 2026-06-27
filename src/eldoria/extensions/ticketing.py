"""Cog d'administration du système de ticketing.

Commande /ticketing (admin) qui ouvre un panneau pour activer/désactiver le système.
Lors de l'activation, on crée une catégorie + un salon principal contenant le bouton public.
"""

import logging

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.ticketing.panel import TicketingAdminView
from eldoria.ui.ticketing.create_view import TicketCreateView
from eldoria.utils.guards import require_guild_ctx

log = logging.getLogger(__name__)


class Ticketing(commands.Cog):
    def __init__(self, bot: EldoriaBot) -> None:
        self.bot = bot

    async def _clear_open_channel(self, channel: discord.TextChannel, guild_id: int) -> None:
        """Vide le salon principal de ticketing avant de republier le bouton."""
        bot_member = channel.guild.me
        if bot_member is None:
            log.warning("Ticketing clear impossible: bot member introuvable (guild=%s, channel=%s)", guild_id, channel.id)
            return

        perms = channel.permissions_for(bot_member)
        if not perms.read_message_history:
            log.warning("Ticketing clear ignoré: permission Read Message History manquante (guild=%s, channel=%s)", guild_id, channel.id)
            return

        try:
            # Purge est le chemin le plus rapide; Discord gère ensuite les suppressions compatibles.
            await channel.purge(limit=None)
        except discord.Forbidden:
            log.warning("Ticketing clear refusé: impossible de purge le salon principal (guild=%s, channel=%s)", guild_id, channel.id)
            return
        except discord.HTTPException:
            log.exception("Ticketing clear: erreur HTTP pendant purge (guild=%s, channel=%s)", guild_id, channel.id)
            return

    @commands.slash_command(name="ticketing", description="(Admin) Configure le système de ticketing")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def ticketing_panel(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer(ephemeral=True)
        guild, _ = require_guild_ctx(ctx)

        view = TicketingAdminView(ticketing=self.bot.services.ticketing, author_id=ctx.author.id, guild=guild)
        embed, files = view.current_embed()
        await ctx.followup.send(embed=embed, files=files, view=view, ephemeral=True)

    # Helper to ensure category + open channel exists and send the persistent message with button
    async def ensure_setup(self, guild: discord.Guild) -> None:
        ts = self.bot.services.ticketing
        cfg = ts.get_config(guild.id)
        bot_member = guild.me
        if bot_member is None:
            log.warning("Ticketing setup impossible: bot member introuvable (guild=%s)", guild.id)
            return

        guild_perms = guild.me.guild_permissions
        if not guild_perms.manage_channels:
            log.warning("Ticketing setup impossible: permission Manage Channels manquante (guild=%s)", guild.id)
            return

        category_id = int(cfg.get("category_id") or 0)
        open_channel_id = int(cfg.get("open_channel_id") or 0)

        category = guild.get_channel(category_id) if category_id else None
        if category is not None and not isinstance(category, discord.CategoryChannel):
            category = None
        if category is None:
            try:
                category = await guild.create_category(name="Tickets")
                ts.set_category_id(guild.id, category.id)
            except discord.Forbidden:
                log.warning("Ticketing setup refusé: impossible de créer la catégorie (guild=%s)", guild.id)
                return
            except discord.HTTPException:
                log.exception("Ticketing setup: erreur HTTP à la création de catégorie (guild=%s)", guild.id)
                return

        open_channel = guild.get_channel(open_channel_id) if open_channel_id else None
        if open_channel is None:
            # create a text channel under category where users can click the button
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=True),
                bot_member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            try:
                open_channel = await guild.create_text_channel(
                    name="🏰 Salle-des-requêtes",
                    category=category,
                    overwrites=overwrites,
                    topic="Salon dédié à l'ouverture des requêtes. Utilise le bouton ci-dessous pour créer un ticket."
                )
                ts.set_open_channel_id(guild.id, open_channel.id)
            except discord.Forbidden:
                log.warning("Ticketing setup refusé: impossible de créer le salon principal (guild=%s)", guild.id)
                return
            except discord.HTTPException:
                log.exception("Ticketing setup: erreur HTTP à la création du salon principal (guild=%s)", guild.id)
                return

        # Best effort: on tente d'aligner les permissions, sans bloquer le setup si c'est refusé.
        channel_perms = open_channel.permissions_for(bot_member)
        if channel_perms.manage_roles or channel_perms.manage_channels:
            try:
                await open_channel.set_permissions(guild.default_role, view_channel=True, send_messages=False)
                await open_channel.set_permissions(bot_member, view_channel=True, send_messages=True, read_message_history=True)
            except discord.Forbidden:
                log.warning(
                    "Ticketing setup: impossible de corriger les permissions du salon principal (guild=%s, channel=%s). "
                    "Le bot peut continuer si le salon est déjà utilisable.",
                    guild.id,
                    open_channel.id,
                )
            except discord.HTTPException:
                log.exception("Ticketing setup: erreur HTTP en correction permissions (guild=%s, channel=%s)", guild.id, open_channel.id)
        else:
            log.warning(
                "Ticketing setup: permissions insuffisantes pour modifier les overwrites du salon principal "
                "(guild=%s, channel=%s). Droit requis: Manage Roles ou Manage Channels sur ce salon.",
                guild.id,
                open_channel.id,
            )

        # send embed + persistent view
        try:
            # register persistent view on bot (safe even if already registered)
            try:
                self.bot.add_view(TicketCreateView())
            except Exception:
                pass

            if isinstance(open_channel, discord.TextChannel):
                await self._clear_open_channel(open_channel, guild.id)
            else:
                log.warning(
                    "Ticketing setup: salon principal non textuel, nettoyage ignoré (guild=%s, channel=%s)",
                    guild.id,
                    getattr(open_channel, "id", 0),
                )

            # send (ou éditer) le message présentant le bouton
            embed = discord.Embed(title="📜 Envoyer une requête", description="Adresse ton message aux gardiens du serveur en ouvrant un ticket privé. Nous te répondrons dans les meilleurs délais.", color=discord.Color.blurple())
            # send as normal message (no ephemeral)
            await open_channel.send(embed=embed, view=TicketCreateView())
        except discord.Forbidden:
            log.warning("Ticketing setup refusé: envoi du message d'ouverture impossible (guild=%s, channel=%s)", guild.id, open_channel.id)
        except discord.HTTPException:
            log.exception("Erreur lors de l'envoi du message d'ouverture de ticket (guild=%s)", guild.id)


def setup(bot: EldoriaBot) -> None:
    bot.add_cog(Ticketing(bot))

