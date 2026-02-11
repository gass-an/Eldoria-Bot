"""Cog gérant les duels entre membres, avec des paris d'XP.
    
Permet de défier un autre membre, d'accepter ou refuser le duel, et gère les résultats (gagnant, perdant, égalité)
ainsi que les conséquences sur l'XP des joueurs.
Inclut également une loop pour annuler les duels expirés et mettre à jour l'interface utilisateur en conséquence.
"""
import discord
from discord.ext import commands, tasks

from eldoria.app.bot import EldoriaBot
from eldoria.exceptions.duel_exceptions import DuelError
from eldoria.exceptions.duel_ui_errors import duel_error_message
from eldoria.ui.duels.flow.home import HomeView, build_home_duels_embed
from eldoria.ui.duels.result.expired import build_expired_duels_embed
from eldoria.ui.xp.embeds.status import build_xp_disable_embed
from eldoria.utils.discord_utils import get_member_by_id_or_raise, get_text_or_thread_channel
from eldoria.utils.timestamp import now_ts


def require_guild_ctx(ctx: discord.ApplicationContext) -> tuple[discord.Guild, discord.abc.GuildChannel]:
    """Extrait la guild et le channel d'un contexte de commande, ou lève une exception si le contexte n'est pas dans une guild ou un channel."""
    if ctx.guild is None or ctx.channel is None:
        raise RuntimeError("Command used outside guild")
    return ctx.guild, ctx.channel

class Duels(commands.Cog):
    """Cog gérant les duels entre membres, avec des paris d'XP.
    
    Permet de défier un autre membre, d'accepter ou refuser le duel, et gère les résultats (gagnant, perdant, égalité)
    ainsi que les conséquences sur l'XP des joueurs.
    Inclut également une loop pour annuler les duels expirés et mettre à jour l'interface utilisateur en conséquence.
    """

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog Duels avec une référence au bot et à ses services de duel et d'XP, et démarre les loops de maintenance pour les duels."""
        self.bot = bot
        self.clear_expired_duels_loop.start()
        self.maintenance_cleanup.start()
        self.duel = self.bot.services.duel
        self.xp = self.bot.services.xp


    # -------------------- Loops --------------------
    @tasks.loop(hours=24)
    async def maintenance_cleanup(self) -> None:
        """Loop de maintenance quotidienne pour nettoyer les duels expirés et autres données obsolètes."""
        self.duel.cleanup_old_duels(now_ts())

    @tasks.loop(seconds=15)
    async def clear_expired_duels_loop(self) -> None:
        """Loop régulière pour annuler les duels expirés.
        
        Met à jour leur état dans la base de données, et éditer les messages associés pour refléter le changement d'état (EXPIRED).
        Gère également les remboursements d'XP si nécessaire.
        """
        # 1) Service (DB) : transition vers EXPIRED + refunds éventuels
        expired = self.duel.cancel_expired_duels()

        # 2) UI : éditer uniquement les messages associés
        for info in expired:
            try:
                await self._apply_expired_ui(info)
            except Exception:
                # On ne casse pas la loop pour un message supprimé / perms / etc.
                continue
            if info.get("xp_changed"):
                guild = self.bot.get_guild(info["guild_id"])
                if guild is None:
                    continue
                await self.xp.sync_xp_roles_for_users(guild, info.get("sync_roles_user_ids", []))


    @maintenance_cleanup.before_loop
    async def before_maintenance_cleanup(self) -> None:
        """Attente que le bot soit prêt avant de démarrer la loop de maintenance."""
        await self.bot.wait_until_ready()

    @clear_expired_duels_loop.before_loop
    async def before_clear_expired_duels_loop(self) -> None:
        """Attente que le bot soit prêt avant de démarrer la loop de nettoyage des duels expirés."""
        await self.bot.wait_until_ready()

    # -------------------- Helpers --------------------
    async def _apply_expired_ui(self, info: dict) -> None:
        """Édite le message du duel pour afficher l'état EXPIRED.

        `info` provient de cancel_expired_duels().
        """
        message_id = info.get("message_id")
        channel_id = info.get("channel_id")

        if not message_id or not channel_id:
            return

        guild = self.bot.get_guild(int(info["guild_id"]))
        if guild is None:
            return

        player_a = await get_member_by_id_or_raise(guild, int(info["player_a_id"]))
        player_b = await get_member_by_id_or_raise(guild, int(info["player_b_id"]))

        embed, _files = await build_expired_duels_embed(
            player_a=player_a,
            player_b=player_b,
            previous_status=str(info.get("previous_status")),
            stake_xp=int(info.get("stake_xp") or 0),
            game_type=str(info.get("game_type") or ""),
        )

        channel = await get_text_or_thread_channel(bot=self.bot, channel_id=int(channel_id))
        message = await channel.fetch_message(int(message_id))

        # On supprime les boutons : view=None
        await message.edit(content="", embed=embed, view=None)


    # -------------------- Commands --------------------
    @commands.slash_command(name="duel", description="Defi un autre membre en duel (pari de l'xp)")
    @discord.option("member", discord.Member, description="La personne que vous voulez provoquez en duel !")
    async def duel_command(self, ctx: discord.ApplicationContext, member: discord.Member) -> None:
        """Commande slash /duel : défie un autre membre en duel avec un pari d'XP.
        
        Vérifie les conditions d'éligibilité (pas de duel actif, pas de défi à soi-même, etc.),
        crée le duel dans la base de données, et envoie un message avec les détails du duel et les options pour accepter ou refuser le défi.
        """
        await ctx.defer(ephemeral=True)

        if member.bot:
            await ctx.followup.send(content="🤖 Tu ne peux pas défier un bot.", ephemeral=True)
            return

        if member.id == ctx.user.id:
            await ctx.followup.send(content="😅 Tu ne peux pas te défier toi-même.", ephemeral=True)
            return

        try:
            guild, channel = require_guild_ctx(ctx)
        except RuntimeError:
            await ctx.respond("❌ Utilisable uniquement sur un serveur.", ephemeral=True)
            return

        guild_id = guild.id

        if not self.xp.is_enabled(guild_id):
            embed, files = await build_xp_disable_embed(guild_id, self.bot)
            await ctx.followup.send(embed=embed, files=files, ephemeral=True)
            return

        channel_id = channel.id
        player_a_id = ctx.user.id
        player_b_id = member.id

        try:
            snapshot = self.duel.new_duel(guild_id=guild_id, channel_id=channel_id, player_a_id=player_a_id, player_b_id=player_b_id)
        except DuelError as e:
            await ctx.followup.send(duel_error_message(e), ephemeral=True)
            return
        
        expires_at = snapshot["duel"]["expires_at"]
        duel_id = snapshot["duel"]["id"]
        embed, files = await build_home_duels_embed(expires_at)
        await ctx.followup.send(embed=embed, files=files, view=HomeView(bot=self.bot, duel_id=duel_id), ephemeral=True)

def setup(bot: EldoriaBot) -> None:
    """Fonction d'initialisation du cog Duels, appelée lors du chargement de l'extension."""
    bot.add_cog(Duels(bot))
