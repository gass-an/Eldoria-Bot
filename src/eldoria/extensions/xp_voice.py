import discord
from discord.ext import commands, tasks

from eldoria.app.bot import EldoriaBot
from eldoria.features.xp.voice_xp import is_voice_member_active, tick_voice_xp_for_member
from eldoria.utils.timestamp import now_ts

from ..db import database_manager
from ..utils.mentions import level_mention


def _pick_voice_levelup_text_channel(guild: discord.Guild, cfg: dict) -> discord.TextChannel | None:
    """Retourne le salon texte où annoncer les levels vocaux.

    Priorité:
    1) ID configuré (voice_levelup_channel_id)
    2) system_channel
    3) un salon nommé 'general' / 'général' etc.
    """
    cid = int(cfg.get("voice_levelup_channel_id", 0) or 0)
    ch = guild.get_channel(cid) if cid else None
    if isinstance(ch, discord.TextChannel):
        return ch

    ch2 = getattr(guild, "system_channel", None)
    if isinstance(ch2, discord.TextChannel):
        return ch2

    preferred_names = (
        "general",
        "général",
        "general-chat",
        "général-chat",
        "chat-general",
        "discussion",
        "chat",
    )
    for n in preferred_names:
        found = discord.utils.get(getattr(guild, "text_channels", []) or [], name=n)
        if isinstance(found, discord.TextChannel):
            return found
    return None


class XpVoice(commands.Cog):
    """Attribution d'XP en vocal.

    - 1 XP / 3 minutes (configurable)
    - Cap journalier (configurable) : 5h => 100 XP/jour par défaut
    - Pas d'XP si seul dans le vocal
    - Pas d'XP si mute/deaf (self ou serveur)
    - Le cooldown ne s'applique PAS (cooldown réservé aux messages)
    """

    def __init__(self, bot: EldoriaBot):
        self.bot = bot
        self.voice_xp_loop.start()

    def cog_unload(self):
        try:
            self.voice_xp_loop.cancel()
        except Exception:
            pass

    @tasks.loop(minutes=1)
    async def voice_xp_loop(self):
        for guild in list(getattr(self.bot, "guilds", []) or []):
            try:
                database_manager.xp_ensure_defaults(guild.id)

                cfg = database_manager.xp_get_config(guild.id)
                if not bool(cfg.get("enabled", False)) or not bool(cfg.get("voice_enabled", True)):
                    continue

                now = now_ts()

                for vc in list(getattr(guild, "voice_channels", []) or []):
                    members = list(getattr(vc, "members", []) or [])
                    if not members:
                        continue

                    active_members = [m for m in members if is_voice_member_active(m)]
                    active_count = len(active_members)

                    if active_count < 2:
                        # coupe le compteur pour éviter d'accumuler du temps "solo"
                        for m in active_members:
                            try:
                                database_manager.xp_voice_upsert_progress(
                                    guild.id,
                                    m.id,
                                    last_tick_ts=now,
                                )
                            except Exception:
                                continue
                        continue

                    for member in active_members:
                        try:
                            res = await tick_voice_xp_for_member(guild, member)
                            if res is None:
                                continue

                            new_xp, new_lvl, old_lvl = res
                            if new_lvl <= old_lvl:
                                continue

                            txt_channel = _pick_voice_levelup_text_channel(guild, cfg)
                            if txt_channel is None:
                                continue

                            # Vérif perm d'envoi
                            me = getattr(guild, "me", None) or guild.get_member(getattr(self.bot.user, "id", 0) or 0)
                            if me is not None:
                                perms = txt_channel.permissions_for(me)
                                if not perms.send_messages:
                                    continue

                            lvl_txt = level_mention(guild, new_lvl)

                            await txt_channel.send(
                                f"🎉 Félicitations {member.mention}, tu passes {lvl_txt} grâce à ta présence dans un salon vocal !",
                                allowed_mentions=discord.AllowedMentions(
                                    users=True,
                                    roles=False,
                                ),
                            )
                        except Exception:
                            continue
            except Exception:
                continue


    @voice_xp_loop.before_loop
    async def _wait_until_ready(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Évite les gains pendant les périodes inéligibles.

        On "coupe" le compteur dès qu'il y a un changement (move/join/leave/mute/deaf),
        comme ça le prochain tick ne comptabilise pas le segment précédent.
        """
        if member.bot or member.guild is None:
            return

        relevant_change = (
        before.channel != after.channel
        or bool(getattr(before, "mute", False)) != bool(getattr(after, "mute", False))
        or bool(getattr(before, "deaf", False)) != bool(getattr(after, "deaf", False))
        or bool(getattr(before, "self_mute", False)) != bool(getattr(after, "self_mute", False))
        or bool(getattr(before, "self_deaf", False)) != bool(getattr(after, "self_deaf", False))
    )

        if not relevant_change:
            return

        try:
            # Assure la config (au cas où la guild vient d'être join)
            database_manager.xp_ensure_defaults(member.guild.id)

            now = now_ts()  # helper interne (UTC)

            # On met juste à jour last_tick_ts; le calcul réel est fait par la loop.
            database_manager.xp_voice_upsert_progress(
                member.guild.id,
                member.id,
                last_tick_ts=now,
            )
        except Exception:
            return


def setup(bot: EldoriaBot):
    bot.add_cog(XpVoice(bot))
