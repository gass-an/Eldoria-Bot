"""Cog d'administration du système de ticketing.

Commande /ticketing (admin) qui ouvre un panneau pour activer/désactiver le système.
Lors de l'activation, on crée une catégorie + un salon principal contenant le bouton public.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.ticketing.create_view import TicketCreateView
from eldoria.ui.ticketing.embeds import (
    build_ticket_closed_embed,
    build_ticket_request_embed,
)
from eldoria.ui.ticketing.panel import TicketingAdminView
from eldoria.utils.guards import require_guild_ctx
from eldoria.utils.timestamp import now_ts

log = logging.getLogger(__name__)


class Ticketing(commands.Cog):
    def __init__(self, bot: EldoriaBot) -> None:
        self.bot = bot
        self._close_locks: dict[tuple[int, int], asyncio.Lock] = {}
        self._archive_locks: dict[int, asyncio.Lock] = {}

    async def _archive_category(self, guild: discord.Guild) -> discord.CategoryChannel:
        """Résout ou crée une seule catégorie d'archives par serveur."""
        lock = self._archive_locks.setdefault(guild.id, asyncio.Lock())
        async with lock:
            return await self._archive_category_unlocked(guild)

    async def _archive_category_unlocked(
        self, guild: discord.Guild
    ) -> discord.CategoryChannel:
        service = self.bot.services.ticketing
        cfg = service.get_config(guild.id)
        stored_id = int(cfg.get("archive_category_id") or 0)
        stored = guild.get_channel(stored_id) if stored_id else None
        if isinstance(stored, discord.CategoryChannel):
            return stored

        category = next(
            (item for item in guild.categories if item.name == "Tickets Archivés"),
            None,
        )
        if category is None:
            ticket_category_id = int(cfg.get("category_id") or 0)
            ticket_category = guild.get_channel(ticket_category_id) if ticket_category_id else None
            create_options = {"name": "Tickets Archivés"}
            if isinstance(ticket_category, discord.CategoryChannel):
                create_options["position"] = ticket_category.position + 1
            category = await guild.create_category(**create_options)

        service.set_archive_category_id(guild.id, category.id)
        return category

    @staticmethod
    def _archive_overwrites(
        guild: discord.Guild,
    ) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
        read_only = dict(
            view_channel=True,
            read_message_history=True,
            send_messages=False,
            send_messages_in_threads=False,
            create_public_threads=False,
            create_private_threads=False,
            add_reactions=False,
            send_tts_messages=False,
            mention_everyone=False,
            manage_messages=False,
            manage_threads=False,
            manage_webhooks=False,
            manage_channels=False,
            manage_permissions=False,
            pin_messages=False,
            use_application_commands=False,
            use_external_apps=False,
            send_voice_messages=False,
            send_polls=False,
        )
        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }
        for role in guild.roles:
            if role.permissions.manage_guild or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(**read_only)
        if guild.me is None:
            raise RuntimeError("Membre Discord du bot introuvable")
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            manage_channels=True,
            manage_permissions=True,
        )
        return overwrites

    @staticmethod
    def _overwrites_match(
        channel: discord.abc.GuildChannel,
        expected: dict[discord.abc.Snowflake, discord.PermissionOverwrite],
        guild: discord.Guild,
    ) -> bool:
        """Compare les overwrites bruts, y compris les membres hors cache."""
        raw_overwrites = getattr(channel, "_overwrites", None)
        if raw_overwrites is None:
            return False

        actual = {
            (int(overwrite.id), int(overwrite.type)): (
                int(overwrite.allow),
                int(overwrite.deny),
            )
            for overwrite in raw_overwrites
        }
        expected_raw: dict[tuple[int, int], tuple[int, int]] = {}
        for target, expected_overwrite in expected.items():
            if not hasattr(expected_overwrite, "pair"):
                # Les objets Discord réels exposent toujours pair(). En cas de
                # représentation inconnue, on resécurise le salon par prudence.
                return False
            allow, deny = expected_overwrite.pair()
            overwrite_type = 1 if target == guild.me else 0
            expected_raw[(int(target.id), overwrite_type)] = (
                int(allow.value),
                int(deny.value),
            )
        return actual == expected_raw

    @commands.slash_command(name="close", description="(Admin) Ferme et archive le ticket actuel")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def close_ticket(self, ctx: discord.ApplicationContext) -> None:
        """Archive le ticket du salon courant sans supprimer son historique."""
        await ctx.defer(ephemeral=True)
        guild, channel = require_guild_ctx(ctx)
        await self._close_ticket_channel(ctx, guild, channel)

    async def _close_ticket_channel(
        self,
        ctx: discord.ApplicationContext,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
    ) -> None:
        """Sécurise le salon puis finalise le ticket correspondant en base."""
        service = self.bot.services.ticketing
        ticket = service.get_ticket_by_channel(guild.id, channel.id)
        if ticket is None:
            await ctx.followup.send(
                "Cette commande ne peut être utilisée que dans un ticket.", ephemeral=True
            )
            return

        key = (guild.id, channel.id)
        lock = self._close_locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached_channel = guild.get_channel(channel.id)
            if cached_channel is not None:
                channel = cached_channel
            ticket = service.get_ticket_by_channel(guild.id, channel.id)
            if ticket is None:
                await ctx.followup.send(
                    "Cette commande ne peut être utilisée que dans un ticket.", ephemeral=True
                )
                return
            if ticket["status"] == "CLOSED":
                await ctx.followup.send("Ce ticket est déjà archivé.", ephemeral=True)
                return

            raw_number = ticket["ticket_number"]
            if raw_number is None:
                log.error(
                    "Ticket historique sans numéro public; archivage refusé "
                    "(guild=%s, channel=%s, ticket=%s)",
                    guild.id,
                    channel.id,
                    ticket["id"],
                )
                await ctx.followup.send(
                    "Ce ticket historique ne possède pas de numéro public fiable. "
                    "Il ne peut pas être archivé automatiquement.",
                    ephemeral=True,
                )
                return

            number = int(raw_number)
            if guild.me is None:
                log.error(
                    "Archivage impossible: membre bot introuvable (guild=%s, channel=%s)",
                    guild.id,
                    channel.id,
                )
                await ctx.followup.send(
                    "Impossible d'archiver ce ticket : mon membre serveur est introuvable. "
                    "Réessayez lorsque Discord aura actualisé les membres du serveur.",
                    ephemeral=True,
                )
                return

            try:
                archive_category = await self._archive_category(guild)
            except (discord.Forbidden, discord.HTTPException):
                log.exception(
                    "Préparation des archives Discord impossible (guild=%s, channel=%s)",
                    guild.id,
                    channel.id,
                )
                await ctx.followup.send(
                    "Impossible d'archiver ce ticket sur Discord. Vérifiez mes permissions "
                    "et la capacité de la catégorie, puis réessayez.",
                    ephemeral=True,
                )
                return
            except Exception:
                log.exception(
                    "Préparation de l'archivage impossible (guild=%s, channel=%s)",
                    guild.id,
                    channel.id,
                )
                await ctx.followup.send(
                    "L'archivage n'a pas pu être préparé. Aucun changement n'a été "
                    "appliqué au ticket; vous pouvez réessayer.",
                    ephemeral=True,
                )
                return

            expected_overwrites = self._archive_overwrites(guild)
            already_archived = (
                channel.name == f"closed-{number:03d}"
                and getattr(getattr(channel, "category", None), "id", None)
                == archive_category.id
                and self._overwrites_match(
                    channel, expected_overwrites, guild
                )
            )
            if not already_archived:
                try:
                    edited_channel = await channel.edit(
                        name=f"closed-{number:03d}",
                        category=archive_category,
                        sync_permissions=False,
                        overwrites=expected_overwrites,
                        reason=f"Ticket #{number:03d} fermé par {ctx.author}",
                    )
                    if edited_channel is not None:
                        channel = edited_channel
                except (discord.Forbidden, discord.HTTPException):
                    log.exception(
                        "Archivage Discord du ticket impossible (guild=%s, channel=%s)",
                        guild.id,
                        channel.id,
                    )
                    await ctx.followup.send(
                        "Impossible d'archiver ce ticket sur Discord. Vérifiez mes "
                        "permissions et la capacité de la catégorie, puis réessayez.",
                        ephemeral=True,
                    )
                    return
                except Exception:
                    log.exception(
                        "Erreur inattendue pendant l'archivage Discord "
                        "(guild=%s, channel=%s)",
                        guild.id,
                        channel.id,
                    )
                    await ctx.followup.send(
                        "Impossible de finaliser l'archivage Discord. Aucun changement "
                        "n'a été enregistré en base; vous pouvez réessayer.",
                        ephemeral=True,
                    )
                    return

            closed_at = now_ts()
            try:
                persisted = service.close_ticket(int(ticket["id"]), closed_at)
                current = (
                    service.get_ticket_by_channel(guild.id, channel.id)
                    if not persisted
                    else None
                )
            except sqlite3.Error:
                log.exception(
                    "Ticket archivé sur Discord mais persistance SQLite en échec "
                    "(guild=%s, channel=%s, ticket=%s)",
                    guild.id,
                    channel.id,
                    ticket["id"],
                )
                await ctx.followup.send(
                    "Le salon a été archivé sur Discord, mais sa fermeture n'a pas "
                    "pu être enregistrée. Réessayez `/close` pour finaliser l'opération.",
                    ephemeral=True,
                )
                return

            if not persisted:
                if current is not None and current["status"] == "CLOSED":
                    log.info(
                        "Fermeture déjà enregistrée par un autre traitement (ticket=%s)",
                        ticket["id"],
                    )
                    await ctx.followup.send(
                        f"Le ticket #{number:03d} était déjà archivé.", ephemeral=True
                    )
                    return

                log.error(
                    "Ticket archivé sur Discord mais toujours OPEN en SQLite "
                    "(guild=%s, channel=%s, ticket=%s)",
                    guild.id,
                    channel.id,
                    ticket["id"],
                )
                await ctx.followup.send(
                    "Le salon a été archivé sur Discord, mais la base indique encore "
                    "que le ticket est ouvert. Réessayez `/close` pour finaliser l'opération.",
                    ephemeral=True,
                )
                return

            embed = build_ticket_closed_embed(
                closed_by_mention=ctx.author.mention,
                closed_at=closed_at,
                ticket_number=number,
            )
            try:
                await channel.send(
                    embed=embed, allowed_mentions=discord.AllowedMentions.none()
                )
            except (discord.Forbidden, discord.HTTPException):
                log.exception(
                    "Ticket fermé mais embed de confirmation impossible "
                    "(guild=%s, channel=%s, ticket=%s)",
                    guild.id,
                    channel.id,
                    ticket["id"],
                )
            except Exception:
                log.exception(
                    "Ticket fermé mais erreur inattendue pendant l'envoi de l'embed "
                    "(guild=%s, channel=%s, ticket=%s)",
                    guild.id,
                    channel.id,
                    ticket["id"],
                )

            await ctx.followup.send(
                f"Le ticket #{number:03d} a été archivé.", ephemeral=True
            )

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
            embed = build_ticket_request_embed()
            # send as normal message (no ephemeral)
            await open_channel.send(embed=embed, view=TicketCreateView())
        except discord.Forbidden:
            log.warning("Ticketing setup refusé: envoi du message d'ouverture impossible (guild=%s, channel=%s)", guild.id, open_channel.id)
        except discord.HTTPException:
            log.exception("Erreur lors de l'envoi du message d'ouverture de ticket (guild=%s)", guild.id)


def setup(bot: EldoriaBot) -> None:
    bot.add_cog(Ticketing(bot))
