import discord
from discord.ext import commands

from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.common.embeds.images import common_files, decorate


async def build_xp_status_embed(cfg: dict, guild_id: int, bot: commands.Bot):
    guild = bot.get_guild(guild_id)
    enabled = bool(cfg.get("enabled", False))
    
    embed = discord.Embed(
        title="Statut du système XP",
        description="Configuration actuelle du système d'expérience sur ce serveur.",
        colour=EMBED_COLOUR_PRIMARY
    )

    if enabled :
        embed.add_field(
            name="État",
            value="✅ Activé",
            inline=False
        )
        embed.add_field(
            name="XP / message",
            value=str(cfg.get("points_per_message", 8)),
            inline=True
        )
        embed.add_field(
            name="Cooldown",
            value=f"{cfg.get('cooldown_seconds', 90)} secondes",
            inline=True
        )
        embed.add_field(
            name="Bonus Server Tag",
            value=f"+{cfg.get('bonus_percent', 20)}%",
            inline=True
        )
        embed.add_field(
            name="Malus Karuta (k<=10)",
            value=f"{cfg.get('karuta_k_small_percent', 30)}%",
            inline=False
        )

        # ---- Vocal XP ----
        voice_enabled = bool(cfg.get("voice_enabled", True))
        embed.add_field(
            name="XP Vocal",
            value="✅ Activé" if voice_enabled else "⛔ Désactivé",
            inline=True
        )

        if voice_enabled:
            interval_s = int(cfg.get("voice_interval_seconds", 180))
            per_int = int(cfg.get("voice_xp_per_interval", 1))
            cap_xp = int(cfg.get("voice_daily_cap_xp", 100))

            minutes = max(interval_s // 60, 1)  # affichage propre
            embed.add_field(
                name="Gain vocal",
                value=f"{per_int} XP / {minutes}min",
                inline=True
            )

            # Affiche une durée max "équivalente" au cap XP (si per_int > 0)
            if per_int > 0 and interval_s > 0 and cap_xp > 0:
                cap_seconds = int((cap_xp * interval_s) / per_int)
                cap_hours = cap_seconds / 3600
                embed.add_field(
                    name="Cap vocal",
                    value=f"{cap_xp} XP/jour ({cap_hours:.1f}h)",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Cap vocal",
                    value=f"{cap_xp} XP/jour",
                    inline=True
                )
    
    else :
        embed.add_field(
            name="État",
            value="⛔ Désactivé",
            inline=True
        )
        embed.add_field(
        name="Information",
        value="Demandez à un administrateur d'utiliser `/xp_enable` pour activer le système.",
        inline=False
        )

    embed.set_footer(text=f"Serveur : {guild.name if guild else guild_id}")

    # Images centralisées (thumbnail + banner)
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files


async def build_xp_disable_embed(guild_id: int, bot: commands.Bot):
    guild = bot.get_guild(guild_id)
    embed = discord.Embed(
        title="Statut du système XP",
        description="Configuration actuelle du système d'expérience sur ce serveur.",
        colour=EMBED_COLOUR_PRIMARY
    )

    embed.add_field(
            name="État",
            value="⛔ Désactivé",
            inline=True
    )
    embed.add_field(
        name="Information",
        value="Demandez à un administrateur d'utiliser `/xp_enable` pour activer le système.",
        inline=False
    )

    embed.set_footer(text=f"Serveur : {guild.name if guild else guild_id}")

    # Images centralisées (thumbnail + banner)
    decorate(embed, None, None)
    files = common_files(None, None)
    return embed, files