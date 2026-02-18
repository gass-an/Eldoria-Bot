"""Cog gérant les commandes liées au système d'XP (expérience) du bot Eldoria.
    
Ce module permet aux administrateurs de configurer le système d'XP, de définir les rôles associés aux niveaux,
et aux utilisateurs de consulter leur profil d'XP, les rôles de niveau, et le classement des joueurs.
Il inclut également une commande pour modifier manuellement l'XP d'un membre.
Les commandes sont principalement destinées à être utilisées sur un serveur Discord, et certaines nécessitent des permissions d'administrateur
"""
import logging
import re

import discord
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.ui.common.pagination import Paginator
from eldoria.ui.xp.autocompletion import xp_level_role_autocomplete
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

    # ---------- XP system ----------
    @commands.slash_command(name="xp_enable", description="(Admin) Active le système d'XP sur ce serveur.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_enable(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp_enable : active le système d'XP sur ce serveur.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité, 
        et met à jour la configuration dans la base de données pour activer le système d'XP.
        """
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        await self.xp.ensure_guild_xp_setup(guild)
        self.xp.set_config(guild.id, enabled=True)

        await ctx.followup.send(content="✅ Système d'XP **activé** sur ce serveur.")

    @commands.slash_command(name="xp_disable", description="(Admin) Désactive le système d'XP sur ce serveur.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_disable(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp_disable : désactive le système d'XP sur ce serveur.
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité,
        et met à jour la configuration dans la base de données pour désactiver le système d'XP.
        Note : les données d'XP ne sont pas supprimées, donc réactiver le système plus tard restaurera les XP précédents.
        """
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        self.xp.ensure_defaults(guild.id)
        self.xp.set_config(guild.id, enabled=False)

        await ctx.followup.send(content="⛔ Système d'XP **désactivé** sur ce serveur.")

    @commands.slash_command(name="xp_status", description="Affiche l'état du système d'XP sur ce serveur.")
    async def xp_status(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp_status : affiche l'état du système d'XP sur ce serveur.
        
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

    @commands.slash_command(name="xp", description="Affiche ton XP et ton niveau.")
    async def xp_me(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp : affiche ton XP et ton niveau.
        
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

    @commands.slash_command(name="xp_roles", description="Affiche les rôles des niveaux et l'XP requis pour les obtenir.")
    async def xp_roles(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp_roles : affiche les rôles des niveaux et l'XP requis pour les obtenir.
        
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

    @commands.slash_command(name="xp_classement", description="Affiche le classement des joueurs en fonction de leurs XP.")
    async def xp_list(self, ctx: discord.ApplicationContext) -> None:
        """Commande slash /xp_classement : affiche le classement des joueurs en fonction de leurs XP.
        
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

    @commands.slash_command(name="xp_set_level", description="(Admin) Définit l'XP requis pour un niveau.")
    @discord.option("level", int, description="Niveau (1..5)", min_value=1, max_value=5)
    @discord.option("xp_required", int, description="XP requis pour atteindre ce niveau", min_value=0)
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_set_level(self, ctx: discord.ApplicationContext, level: int, xp_required: int) -> None:
        """Commande slash /xp_set_level : définit l'XP requis pour un niveau. Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité.
        
        Met à jour la configuration dans la base de données pour définir le seuil d'XP requis pour atteindre le niveau spécifié. 
        Après la mise à jour, synchronise les rôles de niveau pour tous les membres du serveur afin de refléter les changements de seuils de niveau.
        """
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        self.xp.ensure_defaults(guild.id)
        self.xp.set_level_threshold(guild.id, level, xp_required)

        role_ids = self.xp.get_role_ids(guild.id)
        label = level_label(guild, role_ids, level)
        await ctx.followup.send(content=f"✅ Seuil mis à jour : **{label}** = **{xp_required} XP**.")

        for member in guild.members:
            if member.bot:
                continue
            try:
                await self.xp.sync_member_level_roles(guild, member)
            except discord.Forbidden:
                log.warning(
                    "xp_set_level: forbidden pendant sync_member_level_roles (guild_id=%s user_id=%s)",
                    guild.id, member.id
                )
            except discord.HTTPException:
                log.warning(
                    "xp_set_level: HTTPException pendant sync_member_level_roles (guild_id=%s user_id=%s)",
                    guild.id, member.id
                )
            except Exception:
                log.exception(
                    "xp_set_level: erreur inattendue pendant sync_member_level_roles (guild_id=%s user_id=%s)",
                    guild.id, member.id
                )

    @commands.slash_command(name="xp_set_config", description="(Admin) Configure les paramètres du système XP (champs vides = inchangés).")
    @discord.option("points_per_message", int, description="XP gagné par message (>=0)", min_value=0, max_value=1000, required=False)
    @discord.option("cooldown_seconds", int, description="Cooldown en secondes entre 2 gains", min_value=0, max_value=3600, required=False)
    @discord.option("bonus_percent", int, description="Bonus en % si le membre affiche le tag du serveur (0 = désactiver)", min_value=0, max_value=300, required=False)
    @discord.option("karuta_k_small_percent", int, description="% d'XP accordé pour les petits messages Karuta (k<=10) (ex: 30)", min_value=0, max_value=100, required=False)
    @discord.option("voice_enabled", bool, description="Active l'XP en vocal (le système XP doit être actif)", required=False)
    @discord.option("voice_interval_seconds", int, description="Intervalle en secondes pour 1 gain vocal (ex: 180)", min_value=30, max_value=3600, required=False)
    @discord.option("voice_xp_per_interval", int, description="XP gagné par intervalle vocal (>=0)", min_value=0, max_value=1000, required=False)
    @discord.option("voice_daily_cap_xp", int, description="Cap journalier d'XP gagné en vocal (ex: 100)", min_value=0, max_value=5000, required=False)
    @discord.option("voice_levelup_channel", discord.TextChannel, description="Salon texte pour annoncer les passages de niveau grâce au vocal (suggestion: #general).", required=False,)
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_set_config(
        self,
        ctx: discord.ApplicationContext,
        points_per_message: int | None = None,
        cooldown_seconds: int | None = None,
        bonus_percent: int | None = None,
        karuta_k_small_percent: int | None = None,
        voice_enabled: bool | None = None,
        voice_interval_seconds: int | None = None,
        voice_xp_per_interval: int | None = None,
        voice_daily_cap_xp: int | None = None,
        voice_levelup_channel: discord.TextChannel | None = None,
    ) -> None:
        """Commande slash /xp_set_config : configure les paramètres du système XP (champs vides = inchangés).
        
        Vérifie les permissions de l'utilisateur, la configuration de la fonctionnalité et
        met à jour la configuration dans la base de données pour les paramètres du système d'XP (points par message, cooldown, bonus, XP vocal, etc.). 
        Affiche ensuite un message de confirmation avec les paramètres qui ont été modifiés.
        """
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        self.xp.ensure_defaults(guild.id)

        if all(v is None for v in (
            points_per_message, cooldown_seconds, bonus_percent, karuta_k_small_percent,
            voice_enabled, voice_interval_seconds, voice_xp_per_interval, voice_daily_cap_xp,
            voice_levelup_channel,
        )):
            await ctx.followup.send(content="INFO: Aucun champ fourni : aucune modification appliquée.")
            return

        self.xp.set_config(
            guild.id,
            points_per_message=points_per_message,
            cooldown_seconds=cooldown_seconds,
            bonus_percent=bonus_percent,
            karuta_k_small_percent=karuta_k_small_percent,
            voice_enabled=voice_enabled,
            voice_interval_seconds=voice_interval_seconds,
            voice_xp_per_interval=voice_xp_per_interval,
            voice_daily_cap_xp=voice_daily_cap_xp,
            voice_levelup_channel_id=(voice_levelup_channel.id if voice_levelup_channel is not None else None),
        )

        parts = []
        if points_per_message is not None:
            parts.append(f"**{points_per_message} XP**/message")
        if cooldown_seconds is not None:
            parts.append(f"cooldown **{cooldown_seconds}s**")
        if bonus_percent is not None:
            parts.append(f"bonus tag **{bonus_percent}%**")
        if karuta_k_small_percent is not None:
            parts.append(f"karuta k<=10 **{karuta_k_small_percent}%**")
        if voice_enabled is not None:
            parts.append(f"vocal **{'on' if voice_enabled else 'off'}**")
        if voice_interval_seconds is not None:
            parts.append(f"vocal interval **{voice_interval_seconds}s**")
        if voice_xp_per_interval is not None:
            parts.append(f"vocal gain **{voice_xp_per_interval} XP**")
        if voice_daily_cap_xp is not None:
            parts.append(f"cap vocal **{voice_daily_cap_xp} XP/jour**")
        if voice_levelup_channel is not None:
            parts.append(f"annonces vocal dans {voice_levelup_channel.mention}")

        await ctx.followup.send(content="✅ Config XP mise à jour : " + ", ".join(parts) + ".")

    @commands.slash_command(name="xp_set_role", description="(Admin) Associe un rôle existant à un niveau XP (remplace l'ancien rôle en base).")
    @discord.option("from_role", str, description="Rôle XP existant (choisir dans la liste).", autocomplete=xp_level_role_autocomplete)
    @discord.option("to_role", discord.Role, description="Nouveau rôle à utiliser à la place (ex: @dep)")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_role_setup(self, ctx: discord.ApplicationContext, from_role: str, to_role: discord.Role) -> None:
        """Permet de remplacer un rôle lvlX par un rôle existant.

        Exemple: /xp_role_setup @level1 @dep
        -> met à jour en DB le role_id du niveau 1 pour pointer vers @dep.
        """
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        self.xp.ensure_defaults(guild.id)
        
        m = LEVEL_RE.search(from_role.strip())
        if not m:
            await ctx.followup.send(content="❌ Sélection invalide. Choisis un rôle dans l'autocomplete.")
            return
        
        level = int(m.group(1))

        role_ids = self.xp.get_role_ids(guild.id)  # dict[level] = role_id
        if not role_ids:
            await ctx.followup.send(content="❌ Aucun rôle XP enregistré en base.")
            return
        
        # Valider que le level existe en base
        from_role_id = role_ids.get(level)
        if not from_role_id:
            await ctx.followup.send(content=f"❌ Aucun role XP en base pour le niveau {level}.")
            return


        from_role_obj = guild.get_role(from_role_id)
        if from_role_obj is None:
            await ctx.followup.send(content="❌ Le rôle source n'existe plus sur le serveur.")
            return
        
        # Empêcher d'utiliser un rôle déjà associé à un autre niveau XP
        # (sinon 2 niveaux partageraient le même role_id -> incohérences)
        existing_level = next((lvl for (lvl, rid) in role_ids.items() if rid == to_role.id), None)

        if existing_level is not None and existing_level != level:
            await ctx.followup.send(
                content=(
                    f"❌ Le rôle {to_role.mention} est déjà associé au niveau {existing_level}. "
                    "Choisis un autre rôle ou remappe d'abord ce niveau."
                )
            )
            return

        if from_role_obj.id == to_role.id:
            await ctx.followup.send(content="⚠️ `from_role` et `to_role` sont identiques, aucune modification.")
            return

        # 3) Update DB
        self.xp.upsert_role_id(guild.id, level, to_role.id)

        # 4) Migration: uniquement les membres qui avaient l'ancien rôle
        affected = [mem for mem in guild.members if (not mem.bot and from_role_obj in mem.roles)]

        failed = 0

        for mem in affected:
            try:
                await mem.remove_roles(from_role_obj, reason="XP role setup: replace role mapping")
                await self.xp.sync_member_level_roles(guild, mem)

            except discord.Forbidden:
                failed += 1
                log.warning(
                    "xp_set_role: forbidden sur membre (guild_id=%s user_id=%s from_role=%s to_role=%s)",
                    guild.id, mem.id, from_role_obj.id, to_role.id
                )

            except discord.HTTPException:
                failed += 1
                log.warning(
                    "xp_set_role: HTTPException sur membre (guild_id=%s user_id=%s from_role=%s to_role=%s)",
                    guild.id, mem.id, from_role_obj.id, to_role.id
                )

            except Exception:
                failed += 1
                log.exception(
                    "xp_set_role: erreur inattendue sur membre (guild_id=%s user_id=%s)",
                    guild.id, mem.id
                )

        await ctx.followup.send(
            content=(
                f"✅ Rôle de niveau {level} mis à jour: {from_role_obj.mention} -> {to_role.mention}\n"
                + (f"\n ⚠️: échecs: {failed} (permissions/hiérarchie)." if failed else "")
            )
        )


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
