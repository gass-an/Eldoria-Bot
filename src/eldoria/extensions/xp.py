import discord
from discord.ext import commands

from ..db import gestionDB
from ..features import xp_system, embedGenerator
from ..utils.mentions import level_label


class Xp(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- XP system ----------
    @commands.slash_command(name="xp_enable", description="(Admin) Active le système d'XP sur ce serveur.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_enable(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        await xp_system.ensure_guild_xp_setup(guild)
        gestionDB.xp_set_config(guild.id, enabled=True)

        await ctx.followup.send(content="✅ Système d'XP **activé** sur ce serveur.")

    @commands.slash_command(name="xp_disable", description="(Admin) Désactive le système d'XP sur ce serveur.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_disable(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        gestionDB.xp_ensure_defaults(guild.id)
        gestionDB.xp_set_config(guild.id, enabled=False)

        await ctx.followup.send(content="⛔ Système d'XP **désactivé** sur ce serveur.")

    @commands.slash_command(name="xp_status", description="Affiche l'état du système d'XP sur ce serveur.")
    async def xp_status(self, ctx: discord.ApplicationContext):
        guild = ctx.guild
        if guild is None:
            await ctx.respond(
                "Commande uniquement disponible sur un serveur.",
                ephemeral=True,
            )
            return
        await ctx.defer(ephemeral=True)

        cfg = gestionDB.xp_get_config(guild.id)
        embed, files = await embedGenerator.generate_xp_status_embed(cfg=cfg, guild_id=guild.id, bot=self.bot)
        await ctx.followup.send(embed=embed, files=files, ephemeral=True)

    @commands.slash_command(name="xp", description="Affiche ton XP et ton niveau.")
    async def xp_me(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        guild = ctx.guild
        guild_id = guild.id
        user = ctx.user
        user_id = user.id

        if not gestionDB.xp_is_enabled(guild_id):
            embed, files = await embedGenerator.generate_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        gestionDB.xp_ensure_defaults(guild_id)

        xp, _ = gestionDB.xp_get_member(guild_id, user_id)
        levels = gestionDB.xp_get_levels(guild_id)
        lvl = xp_system.compute_level(xp, levels)

        role_ids = gestionDB.xp_get_role_ids(guild_id)
        lvl_label = level_label(guild, role_ids, lvl)

        next_req = None
        next_label = None
        for level, req in levels:
            if level == lvl + 1:
                next_req = req
                next_label = level_label(guild, role_ids, lvl + 1)
                break

        embed, files = await embedGenerator.generate_xp_profile_embed(
            guild_id=guild_id,
            user=user,
            xp=xp,
            level=lvl,
            level_label=lvl_label,
            next_level_label=next_label,
            next_xp_required=next_req,
            bot=self.bot,
        )

        await ctx.followup.send(embed=embed, files=files, ephemeral=True)

    @commands.slash_command(name="xp_roles", description="Affiche les rôles des niveaux et l'XP requis pour les obtenir.")
    async def xp_roles(self, ctx: discord.ApplicationContext):
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        guild_id = guild.id

        if not gestionDB.xp_is_enabled(guild_id):
            embed, files = await embedGenerator.generate_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        gestionDB.xp_ensure_defaults(guild_id)

        levels_with_roles = gestionDB.xp_get_levels_with_roles(guild_id)
        embed, files = await embedGenerator.generate_xp_roles_embed(levels_with_roles, guild_id, self.bot)
        await ctx.followup.send(embed=embed, files=files, ephemeral=True)

    @commands.slash_command(name="xp_classement", description="Affiche le classement des joueurs en fonction de leurs XP.")
    async def xp_list(self, ctx: discord.ApplicationContext):
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        guild_id = guild.id

        if not gestionDB.xp_is_enabled(guild_id):
            embed, files = await embedGenerator.generate_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        gestionDB.xp_ensure_defaults(guild_id)

        rows = gestionDB.xp_list_members(guild_id, limit=200, offset=0)
        levels = gestionDB.xp_get_levels(guild_id)
        role_ids = gestionDB.xp_get_role_ids(guild_id)

        items = []
        for (uid, xp) in rows:
            lvl = xp_system.compute_level(xp, levels)
            lbl = level_label(guild, role_ids, lvl)
            items.append((uid, xp, lvl, lbl))

        from ..pages import gestionPages  # import local pour éviter cycles
        paginator = gestionPages.Paginator(
            items=items,
            embed_generator=embedGenerator.generate_list_xp_embed,
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
    async def xp_set_level(self, ctx: discord.ApplicationContext, level: int, xp_required: int):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        gestionDB.xp_ensure_defaults(guild.id)
        gestionDB.xp_set_level_threshold(guild.id, level, xp_required)

        role_ids = gestionDB.xp_get_role_ids(guild.id)
        lbl = level_label(guild, role_ids, level)
        await ctx.followup.send(content=f"✅ Seuil mis à jour : **{lbl}** = **{xp_required} XP**.")

        try:
            for m in guild.members:
                await xp_system.sync_member_level_roles(guild, m)
        except Exception:
            pass

    @commands.slash_command(name="xp_set_config", description="(Admin) Configure les paramètres du système XP (champs vides = inchangés).")
    @discord.option("points_per_message", int, description="XP gagné par message (>=0)", min_value=0, max_value=1000, required=False)
    @discord.option("cooldown_seconds", int, description="Cooldown en secondes entre 2 gains", min_value=0, max_value=3600, required=False)
    @discord.option("bonus_percent", int, description="Bonus en % si le membre affiche le tag du serveur (0 = désactiver)", min_value=0, max_value=300, required=False)
    @discord.option("karuta_k_small_percent", int, description="% d'XP accordé pour les petits messages Karuta (k<=10) (ex: 30)", min_value=0, max_value=100, required=False)
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_set_config(self, ctx: discord.ApplicationContext, points_per_message: int | None = None, cooldown_seconds: int | None = None, 
                            bonus_percent: int | None = None, karuta_k_small_percent: int | None = None):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        gestionDB.xp_ensure_defaults(guild.id)
        if all(v is None for v in (points_per_message, cooldown_seconds, bonus_percent, karuta_k_small_percent)):
            await ctx.followup.send(content="Aucun champ fourni : aucune modification appliquée.")
            return

        gestionDB.xp_set_config(
            guild.id,
            points_per_message=points_per_message,
            cooldown_seconds=cooldown_seconds,
            bonus_percent=bonus_percent,
            karuta_k_small_percent=karuta_k_small_percent,
        )

        # Message récap uniquement des champs modifiés
        parts = []
        if points_per_message is not None:
            parts.append(f"**{points_per_message} XP**/message")
        if cooldown_seconds is not None:
            parts.append(f"cooldown **{cooldown_seconds}s**")
        if bonus_percent is not None:
            parts.append(f"bonus tag **{bonus_percent}%**")
        if karuta_k_small_percent is not None:
            parts.append(f"karuta k<=10 **{karuta_k_small_percent}%**")

        await ctx.followup.send(content="✅ Config XP mise à jour : " + ", ".join(parts) + ".")

    @commands.slash_command(name="xp_role_setup", description="(Admin) Associe un rôle existant à un niveau XP (remplace l'ancien rôle en base).")
    @discord.option("from_role", discord.Role, description="Rôle actuellement utilisé par un niveau (ex: @level1)",)
    @discord.option("to_role", discord.Role, description="Nouveau rôle à utiliser à la place (ex: @dep)",)
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_role_setup(self, ctx: discord.ApplicationContext, from_role: discord.Role, to_role: discord.Role):
        """Permet de remplacer un rôle lvlX par un rôle existant.

        Exemple: /xp_role_setup @level1 @dep
        -> met à jour en DB le role_id du niveau 1 pour pointer vers @dep.
        """
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        gestionDB.xp_ensure_defaults(guild.id)

        # Déterminer le niveau correspondant à from_role.
        role_ids = gestionDB.xp_get_role_ids(guild.id)
        level: int | None = None

        for lvl, rid in role_ids.items():
            if rid == from_role.id:
                level = int(lvl)
                break

        # Fallback: si la DB ne connaît pas encore le rôle, tenter via le nom "levelX".
        if level is None:
            name = (from_role.name or "").lower().strip()
            if name.startswith("level"):
                try:
                    parsed = int(name.replace("level", "", 1))
                    if 1 <= parsed <= 5:
                        level = parsed
                except ValueError:
                    level = None

        if level is None:
            await ctx.followup.send(
                content=(
                    "❌ Je n'arrive pas à déterminer quel niveau correspond à ce rôle. "
                    "Assure-toi de sélectionner un rôle du système XP : `/xp_roles`."
                )
            )
            return

        # Écrire le nouveau role_id en base
        gestionDB.xp_upsert_role_id(guild.id, level, to_role.id)

        # Resynchroniser les membres (best-effort)
        try:
            for m in guild.members:
                await xp_system.sync_member_level_roles(guild, m)
        except Exception:
            pass

        await ctx.followup.send(
            content=f"✅ Rôle de niveau **{level}** mis à jour : {from_role.mention} → {to_role.mention}."
        )
    @commands.slash_command(name="xp_modify", description="(Admin) Ajoute/retire des XP à un membre.")
    @discord.option("member", discord.Member, description="Membre à modifier")
    @discord.option("delta", int, description="Nombre d'XP à ajouter (négatif = retirer)")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_modify(self, ctx: discord.ApplicationContext, member: discord.Member, delta: int):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return
        if member.bot:
            await ctx.followup.send(content="❌ Impossible de modifier l'XP d'un bot.")
            return

        gestionDB.xp_ensure_defaults(guild.id)
        new_xp = gestionDB.xp_add_xp(guild.id, member.id, delta)
        levels = gestionDB.xp_get_levels(guild.id)
        lvl = xp_system.compute_level(new_xp, levels)

        await xp_system.sync_member_level_roles(guild, member, xp=new_xp)

        role_ids = gestionDB.xp_get_role_ids(guild.id)
        lbl = level_label(guild, role_ids, lvl)

        await ctx.followup.send(content=f"✅ {member.mention} est maintenant à **{new_xp} XP** (**{lbl}**).")


def setup(bot: commands.Bot):
    bot.add_cog(Xp(bot))
