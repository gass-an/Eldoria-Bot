import re
import discord
from discord.ext import commands

from ..db import database_manager
from ..features import embed_builder, xp_system
from ..utils.mentions import level_label


LEVEL_RE = re.compile(r"^level\s*(\d+)\b", re.IGNORECASE)

# -------------------- Fonctions pour l'autocompletion --------------------
async def xp_level_role_autocomplete(interaction: discord.AutocompleteContext):
    user_input = (interaction.value or "").lower()
    guild = interaction.interaction.guild
    if guild is None:
        return []

    guild_id = guild.id
    role_ids = database_manager.xp_get_role_ids(guild_id)  # dict[level]=role_id
    if not role_ids:
        return []

    results = []
    for level, rid in sorted(role_ids.items()):
        role = guild.get_role(rid)
        if role is None:
            continue
        label = f"Level {level} — {role.name}"
        if user_input and user_input not in label.lower():
            continue
        results.append(label)
        if len(results) >= 25:
            break
    return results

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
        database_manager.xp_set_config(guild.id, enabled=True)

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

        database_manager.xp_ensure_defaults(guild.id)
        database_manager.xp_set_config(guild.id, enabled=False)

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

        cfg = database_manager.xp_get_config(guild.id)
        embed, files = await embed_builder.generate_xp_status_embed(cfg=cfg, guild_id=guild.id, bot=self.bot)
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

        if not database_manager.xp_is_enabled(guild_id):
            embed, files = await embed_builder.generate_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        database_manager.xp_ensure_defaults(guild_id)

        xp, _ = database_manager.xp_get_member(guild_id, user_id)
        levels = database_manager.xp_get_levels(guild_id)
        lvl = xp_system.compute_level(xp, levels)

        role_ids = database_manager.xp_get_role_ids(guild_id)
        lvl_label = level_label(guild, role_ids, lvl)

        next_req = None
        next_label = None
        for level, req in levels:
            if level == lvl + 1:
                next_req = req
                next_label = level_label(guild, role_ids, lvl + 1)
                break

        embed, files = await embed_builder.generate_xp_profile_embed(
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

        if not database_manager.xp_is_enabled(guild_id):
            embed, files = await embed_builder.generate_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        database_manager.xp_ensure_defaults(guild_id)

        levels_with_roles = database_manager.xp_get_levels_with_roles(guild_id)
        embed, files = await embed_builder.generate_xp_roles_embed(levels_with_roles, guild_id, self.bot)
        await ctx.followup.send(embed=embed, files=files, ephemeral=True)

    @commands.slash_command(name="xp_classement", description="Affiche le classement des joueurs en fonction de leurs XP.")
    async def xp_list(self, ctx: discord.ApplicationContext):
        if ctx.guild is None:
            await ctx.respond("Commande uniquement disponible sur un serveur.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        guild_id = guild.id

        if not database_manager.xp_is_enabled(guild_id):
            embed, files = await embed_builder.generate_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        database_manager.xp_ensure_defaults(guild_id)

        rows = database_manager.xp_list_members(guild_id, limit=200, offset=0)
        levels = database_manager.xp_get_levels(guild_id)
        role_ids = database_manager.xp_get_role_ids(guild_id)

        items = []
        for (uid, xp) in rows:
            lvl = xp_system.compute_level(xp, levels)
            lbl = level_label(guild, role_ids, lvl)
            items.append((uid, xp, lvl, lbl))

        from ..pages import page_manager  # import local pour éviter cycles
        paginator = page_manager.Paginator(
            items=items,
            embed_generator=embed_builder.generate_list_xp_embed,
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

        database_manager.xp_ensure_defaults(guild.id)
        database_manager.xp_set_level_threshold(guild.id, level, xp_required)

        role_ids = database_manager.xp_get_role_ids(guild.id)
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
    ):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        database_manager.xp_ensure_defaults(guild.id)

        if all(v is None for v in (
            points_per_message, cooldown_seconds, bonus_percent, karuta_k_small_percent,
            voice_enabled, voice_interval_seconds, voice_xp_per_interval, voice_daily_cap_xp,
            voice_levelup_channel,
        )):
            await ctx.followup.send(content="INFO: Aucun champ fourni : aucune modification appliquée.")
            return

        database_manager.xp_set_config(
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
        if voice_levelup_channel is not None:
            parts.append(f"annonces vocal → {voice_levelup_channel.mention}")

        await ctx.followup.send(content="✅ Config XP mise à jour : " + ", ".join(parts) + ".")

    @commands.slash_command(name="xp_set_role", description="(Admin) Associe un rôle existant à un niveau XP (remplace l'ancien rôle en base).")
    @discord.option("from_role", str, description="Rôle XP existant (choisir dans la liste).", autocomplete=xp_level_role_autocomplete)
    @discord.option("to_role", discord.Role, description="Nouveau rôle à utiliser à la place (ex: @dep)")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_role_setup(self, ctx: discord.ApplicationContext, from_role: str, to_role: discord.Role):
        """Permet de remplacer un rôle lvlX par un rôle existant.

        Exemple: /xp_role_setup @level1 @dep
        -> met à jour en DB le role_id du niveau 1 pour pointer vers @dep.
        """
        await ctx.defer(ephemeral=True)

        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return

        database_manager.xp_ensure_defaults(guild.id)
        
        m = LEVEL_RE.search(from_role.strip())
        if not m:
            await ctx.followup.send(content="❌ Sélection invalide. Choisis un rôle dans l'autocomplete.")
            return
        
        level = int(m.group(1))

        role_ids = database_manager.xp_get_role_ids(guild.id)  # dict[level] = role_id
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

        # 3) Update DB (il te faut une fonction qui set le role_id d'un level)
        database_manager.xp_upsert_role_id(guild.id, level, to_role.id)

        # 4) Migration: uniquement les membres qui avaient l'ancien rôle
        affected = [mem for mem in guild.members if (not mem.bot and from_role_obj in mem.roles)]

        failed = 0
        for mem in affected:
            try:
                await mem.remove_roles(from_role_obj, reason="XP role setup: replace role mapping")
                await xp_system.sync_member_level_roles(guild, mem)
            except discord.Forbidden:
                failed += 1
            except Exception:
                failed += 1

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
    async def xp_modify(self, ctx: discord.ApplicationContext, member: discord.Member, delta: int):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        if guild is None:
            await ctx.followup.send(content="Commande uniquement disponible sur un serveur.")
            return
        if member.bot:
            await ctx.followup.send(content="❌ Impossible de modifier l'XP d'un bot.")
            return

        database_manager.xp_ensure_defaults(guild.id)
        new_xp = database_manager.xp_add_xp(guild.id, member.id, delta)
        levels = database_manager.xp_get_levels(guild.id)
        lvl = xp_system.compute_level(new_xp, levels)

        await xp_system.sync_member_level_roles(guild, member, xp=new_xp)

        role_ids = database_manager.xp_get_role_ids(guild.id)
        lbl = level_label(guild, role_ids, lvl)

        await ctx.followup.send(content=f"✅ {member.mention} est maintenant à **{new_xp} XP** (**{lbl}**).")


def setup(bot: commands.Bot):
    bot.add_cog(Xp(bot))
