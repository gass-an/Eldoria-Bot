"""Cog de gestion des salons vocaux temporaires.

Permet aux utilisateurs de créer automatiquement un salon vocal temporaire en rejoignant un salon vocal parent spécifique.
Inclut des commandes pour configurer les salons parents, supprimer la configuration et lister les salons parents configurés sur le serveur.
"""
import logging

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.pagination import Paginator
from eldoria.ui.temp_voice.home import TempVoiceHomeView, build_tempvoice_home_embed
from eldoria.ui.temp_voice.list import build_list_temp_voice_parents_embed

log = logging.getLogger(__name__)

class TempVoice(commands.Cog):
    """Cog de gestion des salons vocaux temporaires.
    
    Permet aux utilisateurs de créer automatiquement un salon vocal temporaire en rejoignant un salon vocal parent spécifique.
    Inclut des commandes pour configurer les salons parents, supprimer la configuration et lister les salons parents configurés sur le serveur.
    """

    tempvoice = SlashCommandGroup(
        name="tempvoice",
        description="Gère les salons vocaux temporaires.",
        default_member_permissions=discord.Permissions(manage_channels=True)
    )

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog TempVoice avec une référence au bot et à son service de gestion des salons vocaux temporaires."""
        self.bot = bot
        self.temp_voice = self.bot.services.temp_voice

    # -------------------- Events --------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Événement déclenché lorsqu'un utilisateur rejoint, quitte ou se déplace entre des salons vocaux.
        
        Gère la création automatique de salons vocaux temporaires lorsqu'un utilisateur rejoint un salon vocal parent configuré,
        et la suppression de ces salons temporaires lorsqu'ils deviennent vides.
        """
        guild = member.guild

        # 1) DELETE d'abord : si on quitte un salon temporaire et qu'il devient vide
        if before.channel:
            parent_id = self.temp_voice.find_parent_of_active(guild.id, before.channel.id)
            if parent_id is not None and len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                except discord.Forbidden:
                    log.warning(
                        "TempVoice: Impossible de supprimer le salon %s dans la guild %s "
                        "(permissions manquantes).",
                        before.channel.id,
                        guild.id,
                    )
                except discord.HTTPException as e:
                    log.error(
                        "TempVoice: Erreur HTTP lors de la suppression du salon %s "
                        "dans la guild %s: %s",
                        before.channel.id,
                        guild.id,
                        e,
                    )
                finally:
                    self.temp_voice.remove_active(guild.id, parent_id, before.channel.id)

        # 2) GARDE-FOU : si on arrive déjà dans un salon temporaire, on ne crée rien
        if after.channel:
            if self.temp_voice.find_parent_of_active(guild.id, after.channel.id) is not None:
                return

            # 3) CREATE : uniquement si after.channel est un "parent" configuré
            user_limit = self.temp_voice.get_parent(guild.id, after.channel.id)
            if user_limit is not None:
                category = after.channel.category
                new_channel_name = f"Salon de {member.display_name}"
                overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
                    member: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
                }

                new_channel = await guild.create_voice_channel(
                    name=new_channel_name,
                    category=category,
                    overwrites=overwrites,
                    bitrate=after.channel.bitrate,
                    user_limit=user_limit,
                )

                # Important : enregistrer AVANT le move pour que le 2e event (move) soit filtré
                self.temp_voice.add_active(guild.id, after.channel.id, new_channel.id)

                await member.move_to(new_channel)

    # -------------------- Commands --------------------
    @tempvoice.command(name="config", description="Gestion des vocaux temporaires (panel).")
    @commands.has_permissions(manage_channels=True)
    async def tv_config(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /tempvoice config : affiche un panel de gestion des vocaux temporaires."""
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.followup.send("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return

        view = TempVoiceHomeView(temp_voice_service=self.temp_voice, author_id=ctx.author.id, guild=ctx.guild)
        embed, files = build_tempvoice_home_embed()
        await ctx.followup.send(embed=embed, files=files, view=view, ephemeral=True)


    @tempvoice.command(name="list", description="Affiche la liste des salons parents qui créent des vocaux temporaires.")
    @commands.has_permissions(manage_channels=True)
    async def tv_list(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /tempvoice list : affiche la liste des salons parents qui créent des vocaux temporaires.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité, récupère les salons parents configurés pour le serveur,
        et affiche le tout dans un embed paginé.
        """
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return

        guild_id = ctx.guild.id
        parents = self.temp_voice.list_parents(guild_id)

        await ctx.defer(ephemeral=True)
        paginator = Paginator(
            items=parents,
            embed_generator=build_list_temp_voice_parents_embed,
            identifiant_for_embed=guild_id,
            bot=self.bot,
        )
        embed, files = await paginator.create_embed()
        await ctx.followup.send(embed=embed, files=files, view=paginator)


def setup(bot: EldoriaBot) -> None:
    """Fonction d'initialisation du cog TempVoice, appelée par le bot lors du chargement de l'extension."""
    bot.add_cog(TempVoice(bot))
