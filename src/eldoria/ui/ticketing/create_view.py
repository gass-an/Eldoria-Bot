"""Vue partagée pour le bouton public de création de ticket.

Le view est conçu pour être enregistré en tant que persistent view via bot.add_view(..., )
de sorte que les boutons restent actifs entre les redémarrages.
"""

from __future__ import annotations

import logging

import discord

from eldoria.utils.interactions import reply_ephemeral
from eldoria.utils.timestamp import now_ts

log = logging.getLogger(__name__)


class TicketCreateView(discord.ui.View):
    def __init__(self) -> None:
        # timeout=None pour persistance
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📜 Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id="ticket:create"
    )
    async def create_ticket(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        """Crée un salon privé sous la catégorie configurée et y envoie un message de bienvenue pour l'utilisateur."""
        try:
            guild = interaction.guild
            if guild is None:
                await interaction.response.send_message(
                    "Impossible de créer un ticket ici.", ephemeral=True
                )
                return

            # Laisser la logique de création au handler dans l'extension via un event (on_tick_create) ?
            # Pour simplicité, on crée le channel ici en se basant sur la configuration stockée par le service.
            from eldoria.app.bot import EldoriaBot

            bot = interaction.client
            if not isinstance(bot, EldoriaBot):
                await interaction.response.send_message(
                    "Erreur interne (bot inattendu).", ephemeral=True
                )
                return

            ticketing = bot.services.ticketing
            cfg = ticketing.get_config(guild.id)
            category_id = int(cfg.get("category_id") or 0)
            if not category_id:
                await interaction.response.send_message(
                    "Le système de tickets n'est pas configuré sur ce serveur.", ephemeral=True
                )
                return

            category = guild.get_channel(category_id)
            if category is None or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message(
                    "La catégorie de tickets est introuvable. Contacte un administrateur.",
                    ephemeral=True,
                )
                return

            bot_member = guild.me
            if bot_member is None:
                await reply_ephemeral(interaction, "Erreur interne: membre bot introuvable.")
                return

            if not bot_member.guild_permissions.manage_channels:
                await reply_ephemeral(
                    interaction,
                    "Je n'ai pas la permission **Gérer les salons** pour créer un ticket.",
                )
                return

            creator = guild.get_member(interaction.user.id)
            if creator is None:
                await reply_ephemeral(
                    interaction, "Impossible d'identifier ton profil serveur pour créer le ticket."
                )
                return

            # Préparer les overwrites: par défaut on masque pour @everyone
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}

            # L'overwrite de @everyone s'applique aussi au bot sans autorisation explicite.
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            )

            # Autoriser les rôles admin à voir/envoyer
            for role in guild.roles:
                if role.permissions.administrator or role.permissions.manage_guild:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    )

            # Autoriser la personne qui a cliqué
            overwrites[creator] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # Le compteur est persistant et propre à chaque serveur.
            ticket_number = ticketing.allocate_ticket_number(guild.id)

            # Créer le channel (minimum trois chiffres, sans limite après 999).
            ch = await guild.create_text_channel(
                name=f"ticket-{ticket_number:03d}",
                category=category,
                overwrites=overwrites,
                topic=f"Ticket #{ticket_number} créé par {interaction.user.name}",
            )

            ticketing.record_ticket(
                guild.id,
                ticket_number,
                ch.id,
                interaction.user.id,
                now_ts(),
            )

            await ch.send(
                f"🏰 {interaction.user.mention} — Bienvenue dans la salle des requêtes.\n\n" +
                "Explique ici la raison de ta venue en donnant un maximum de détails. " +
                "Le conseil de modération examinera ta demande dans les meilleurs délais.\n\n" +
                "📜 Merci de rester courtois et respectueux envers l'équipe. " +
                "Plus ta demande sera claire et précise, plus nous pourrons t'aider rapidement."
            )
            await interaction.response.send_message(
                f"Ton ticket a été créé : {ch.mention}", ephemeral=True
            )

        except discord.Forbidden:
            await reply_ephemeral(
                interaction, "Je n'ai pas les permissions nécessaires pour créer ce ticket."
            )
        except discord.HTTPException:
            log.exception(
                "Erreur HTTP lors de la création d'un ticket (guild=%s)",
                getattr(interaction.guild, "id", None),
            )
            await reply_ephemeral(
                interaction,
                "Erreur Discord lors de la création du ticket. Réessaie dans quelques instants.",
            )
        except Exception:
            log.exception("Erreur inattendue lors de la création d'un ticket")
            await reply_ephemeral(interaction, "Erreur lors de la création du ticket.")
