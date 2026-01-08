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

    @commands.slash_command(name="xp_list", description="Liste les XP des membres (classement).")
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

    @commands.slash_command(name="xp_set_config", description="(Admin) Configure le gain d'XP par message et le cooldown.")
    @discord.option("points_per_message", int, description="XP gagné par message (>=0)", min_value=0, max_value=1000)
    @discord.option("cooldown_seconds", int, description="Cooldown en secondes entre 2 gains", min_value=0, max_value=3600)
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_set_config(self, ctx: discord.ApplicationContext, points_per_message: int, cooldown_seconds: int):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        gestionDB.xp_ensure_defaults(guild.id)
        gestionDB.xp_set_config(guild.id, points_per_message=points_per_message, cooldown_seconds=cooldown_seconds)
        await ctx.followup.send(
            content=f"✅ Config XP mise à jour : **{points_per_message} XP**/message, cooldown **{cooldown_seconds}s**."
        )

    @commands.slash_command(
        name="xp_set_bonus",
        description="(Admin) Définit le bonus d'XP appliqué si le membre affiche le tag du serveur sur son profil.",
    )
    @discord.option("bonus_percent", int, description="Bonus en % (0 pour désactiver)", min_value=0, max_value=300)
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_set_bonus(self, ctx: discord.ApplicationContext, bonus_percent: int):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        gestionDB.xp_ensure_defaults(guild.id)
        gestionDB.xp_set_config(guild.id, bonus_percent=bonus_percent)

        await ctx.followup.send(content=f"✅ Bonus XP lié au tag du serveur mis à **{bonus_percent}%**.")

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
