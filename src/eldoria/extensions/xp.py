"""Cog gérant les commandes liées au système d'XP (expérience) du bot Eldoria.
    
Ce module permet aux administrateurs de configurer le système d'XP, de définir les rôles associés aux niveaux,
et aux utilisateurs de consulter leur profil d'XP, les rôles de niveau, et le classement des joueurs.
Il inclut également une commande pour modifier manuellement l'XP d'un membre.
Les commandes sont principalement destinées à être utilisées sur un serveur Discord, et certaines nécessitent des permissions d'administrateur
"""
import logging
import re

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.pagination import Paginator
from eldoria.ui.xp.admin.menu import XpAdminMenuView
from eldoria.ui.xp.embeds.leaderboard import build_list_xp_embed
from eldoria.ui.xp.embeds.profile import build_xp_profile_embed
from eldoria.ui.xp.embeds.roles import build_xp_roles_embed
from eldoria.ui.xp.embeds.status import build_xp_disable_embed, build_xp_status_embed
from eldoria.utils.mentions import level_label

log = logging.getLogger(__name__)

LEVEL_RE = re.compile(r"^level\s*(\d+)\b", re.IGNORECASE)

class Xp(commands.Cog):
    """Cog gérant les commandes liées au système d'XP (expérience) du bot Eldoria.
    
    Ce module permet aux administrateurs de configurer le système d'XP, de définir les rôles associés aux niveaux,
    et aux utilisateurs de consulter leur profil d'XP, les rôles de niveau, et le classement des joueurs.
    Il inclut également une commande pour modifier manuellement l'XP d'un membre.
    Les commandes sont principalement destinées à être utilisées sur un serveur Discord, et certaines nécessitent des permissions d'administrateur
    """
    
    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog Xp avec une référence au bot et à son service d'XP."""
        self.bot = bot
        self.xp = self.bot.services.xp

    xp_command = SlashCommandGroup(
        name="xp",
        description="Gère le système d'XP du serveur."
    )

    # ---------- XP public system ----------
    @xp_command.command(name="profile", description="Affiche ton XP et ton niveau.")
    async def xp_profile(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp profile: affiche ton XP et ton niveau.
        
        Vérifie la configuration du système d'XP, récupère les données d'XP et de niveau pour l'utilisateur et 
        affiche un embed avec les informations de profil d'XP (XP actuel, niveau actuel, XP requis pour le prochain niveau, etc.).
        """
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild = ctx.guild
        guild_id = guild.id
        user = ctx.user
        user_id = user.id

        if not self.xp.is_enabled(guild_id):
            embed, files = await build_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        self.xp.ensure_defaults(guild_id)

        snapshot = self.xp.build_snapshot_for_xp_profile(guild, user_id)

        embed, files = await build_xp_profile_embed(
            guild_id=guild_id,
            user=user,
            xp=snapshot["xp"],
            level=snapshot["level"],
            level_label=snapshot["level_label"],
            next_level_label=snapshot["next_level_label"],
            next_xp_required=snapshot["next_xp_required"],
            bot=self.bot,
        )

        await ctx.followup.send(embed=embed, files=files, ephemeral=True)

    @xp_command.command(name="status", description="Affiche l'état du système d'XP sur ce serveur.")
    async def xp_status(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp status : affiche l'état du système d'XP sur ce serveur.
        
        Vérifie la configuration de la fonctionnalité, et affiche un embed indiquant si le système d'XP est activé ou désactivé, 
        ainsi que les paramètres de configuration actuels (points par message, cooldown, bonus, etc.).
        """
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return

        cfg = self.xp.get_config(guild.id)
        embed, files = await build_xp_status_embed(cfg=cfg, guild_id=guild.id, bot=self.bot)
        await ctx.followup.send(embed=embed, files=files, ephemeral=True)

    @xp_command.command(name="leaderboard", description="Affiche le classement des joueurs en fonction de leurs XP.")
    async def xp_leaderboard(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp leaderboard : affiche le classement des joueurs en fonction de leurs XP.
        
        Vérifie la configuration du système d'XP, récupère les données de classement (XP et niveau) pour les membres du serveur et 
        affiche un embed paginé avec le classement des joueurs.
        """
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        guild_id = guild.id

        if not self.xp.is_enabled(guild_id):
            embed, files = await build_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        self.xp.ensure_defaults(guild_id)

        items = self.xp.get_leaderboard_items(guild, limit=200, offset=0)

        paginator = Paginator(
            items=items,
            embed_generator=build_list_xp_embed,
            identifiant_for_embed=guild_id,
            bot=self.bot,
        )
        embed, files = await paginator.create_embed()
        await ctx.followup.send(embed=embed, files=files, view=paginator)

    @xp_command.command(name="roles", description="Affiche les rôles des niveaux et l'XP requis pour les obtenir.")
    async def xp_roles(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp roles : affiche les rôles des niveaux et l'XP requis pour les obtenir.
        
        Vérifie la configuration du système d'XP, récupère les rôles associés à chaque niveau et les seuils d'XP correspondants et 
        affiche un embed avec les informations de rôles de niveau.
        """
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        guild_id = guild.id

        if not self.xp.is_enabled(guild_id):
            embed, files = await build_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        self.xp.ensure_defaults(guild_id)

        levels_with_roles = self.xp.get_levels_with_roles(guild_id)
        embed, files = await build_xp_roles_embed(levels_with_roles, guild_id, self.bot)
        await ctx.followup.send(embed=embed, files=files, ephemeral=True)


    # ---------- XP admin system ----------
    @commands.slash_command(name="xp_admin", description="(Admin) Panneau de configuration du système XP.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_admin(self, ctx: discord.ApplicationContext) -> None:
        """Ouvre le panneau admin XP (UI)."""
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        self.xp.ensure_defaults(guild.id)

        view = XpAdminMenuView(xp=self.xp, author_id=ctx.author.id, guild=guild)
        embed, files = view.current_embed()
        await ctx.followup.send(embed=embed, files=files, view=view, ephemeral=True)


    @commands.slash_command(name="xp_modify", description="(Admin) Ajoute/retire des XP à un membre.")
    @discord.option("member", discord.Member, description="Membre à modifier")
    @discord.option("delta", int, description="Nombre d'XP à ajouter (négatif = retirer)")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_modify(self, ctx: discord.ApplicationContext, member: discord.Member, delta: int) -> None:
        """Commande slash /xp_modify : ajoute/retire des XP à un membre.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité,
        met à jour les XP du membre dans la base de données en ajoutant le delta spécifié (positif ou négatif).
        Après la mise à jour, synchronise les rôles de niveau du membre pour refléter les changements d'XP
        et affiche un message de confirmation avec le nouveau total d'XP et le niveau du membre.
        """
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return
        if member.bot:
            await ctx.followup.send(content="❌ Impossible de modifier l'XP d'un bot.")
            return

        self.xp.ensure_defaults(guild.id)
        new_xp = self.xp.add_xp(guild.id, member.id, delta)
        levels = self.xp.get_levels(guild.id)
        lvl = self.xp.compute_level(new_xp, levels)

        await self.xp.sync_member_level_roles(guild, member, xp=new_xp)

        role_ids = self.xp.get_role_ids(guild.id)
        lbl = level_label(guild, role_ids, lvl)

        await ctx.followup.send(content=f"✅ {member.mention} est maintenant à **{new_xp} XP** (**{lbl}**).")


def setup(bot: EldoriaBot) -> None:
    """Fonction d'initialisation du cog Xp, appelée par le bot lors du chargement de l'extension."""
    bot.add_cog(Xp(bot))
