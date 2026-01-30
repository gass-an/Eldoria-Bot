import discord
from discord.ext import commands
from discord.ext import tasks

from eldoria.exceptions.duel_exceptions import DuelError
from eldoria.exceptions.duel_ui_errors import duel_error_message
from eldoria.features.duel.duel_service import cancel_expired_duels, new_duel
from eldoria.ui.duels.flow.home import HomeView, build_home_duels_embed



def require_guild_ctx(ctx: discord.ApplicationContext):
    if ctx.guild is None or ctx.channel is None:
        raise RuntimeError("Command used outside guild")
    return ctx.guild, ctx.channel

class Duels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.clear_expired_duels_loop.start()

    @tasks.loop(minutes=1)
    async def clear_expired_duels_loop(self):
        cancel_expired_duels()


    # -------------------- Commands --------------------
    @commands.slash_command(name="duel", description="Defi un autre membre en duel (pari de l'xp)")
    @discord.option("member", discord.Member, description="La personne que vous voulez provoquez en duel !")
    async def duel_command(self, ctx: discord.ApplicationContext, member: discord.Member):
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
        channel_id = channel.id
        player_a_id = ctx.user.id
        player_b_id = member.id

        try:
            data_for_embed = new_duel(guild_id=guild_id, channel_id=channel_id, player_a_id=player_a_id, player_b_id=player_b_id)
        except DuelError as e:
            await ctx.followup.send(duel_error_message(e), ephemeral=True)
            return
        
        expires_at = data_for_embed["duel"]["expires_at"]
        duel_id = data_for_embed["duel"]["id"]
        embed, files = await build_home_duels_embed(expires_at)
        await ctx.followup.send(embed=embed, files=files, view=HomeView(bot=self.bot, duel_id=duel_id), ephemeral=True)










def setup(bot: commands.Bot):
    bot.add_cog(Duels(bot))
