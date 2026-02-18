"""Cog de gestion de l'XP vocale, attribuant de l'XP aux membres présents dans les salons vocaux selon certaines règles (1 XP / 3 minutes, cap journalier, etc.).

Inclut une boucle de vérification régulière pour attribuer l'XP 
et un listener pour détecter les changements d'état vocal des membres
afin de gérer les périodes inéligibles.
"""
import logging

import discord
from discord.ext import commands, tasks

from eldoria.app.bot import EldoriaBot
from eldoria.utils.mentions import level_mention
from eldoria.utils.timestamp import now_ts

log = logging.getLogger(__name__)

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

    def __init__(self, bot: EldoriaBot) -> None:
        """Initialise le cog XpVoice avec une référence au bot et à son service d'XP, et démarre la boucle de vérification régulière pour attribuer l'XP vocal."""
        self.bot = bot
        self.voice_xp_loop.start()
        self.xp = self.bot.services.xp

    def cog_unload(self) -> None:
        """Arrête la boucle de vérification régulière pour l'XP vocal lors du déchargement du cog."""
        try:
            self.voice_xp_loop.cancel()
            log.info("Loop de vérification régulière pour l'XP vocal arrêtée proprement.")
        except Exception:
            log.exception("Erreur lors de l'arrêt de la loop de vérification régulière pour l'XP vocal.")

    @tasks.loop(minutes=1)
    async def voice_xp_loop(self) -> None:
        """Boucle régulière pour attribuer de l'XP aux membres présents dans les salons vocaux.
        
        Pour chaque serveur, vérifie la configuration de l'XP vocale, parcourt les salons vocaux et leurs membres,
        et attribue de l'XP aux membres éligibles (pas seuls, pas mute/deaf). Si un membre atteint un nouveau niveau,
        envoie un message de félicitations dans le salon texte approprié.
        """
        for guild in list(getattr(self.bot, "guilds", []) or []):
            try:
                self.xp.ensure_defaults(guild.id)

                cfg = self.xp.get_config(guild.id)
                if not bool(cfg.get("enabled", False)) or not bool(cfg.get("voice_enabled", True)):
                    continue

                now = now_ts()

                for vc in list(getattr(guild, "voice_channels", []) or []):
                    members = list(getattr(vc, "members", []) or [])
                    if not members:
                        continue

                    active_members = [m for m in members if self.xp.is_voice_member_active(m)]
                    if len(active_members) < 2:
                        for m in active_members:
                            try:
                                self.xp.voice_upsert_progress(guild.id, m.id, last_tick_ts=now)
                            except Exception:
                                log.exception(
                                    "XP vocal: erreur lors de la mise à jour du progress (guild_id=%s, user_id=%s)",
                                    guild.id,
                                    m.id,
                                )
                        continue

                    for member in active_members:
                        try:
                            res = await self.xp.tick_voice_xp_for_member(guild, member)
                            if res is None:
                                continue

                            new_xp, new_lvl, old_lvl = res
                            if new_lvl <= old_lvl:
                                continue

                            txt_channel = _pick_voice_levelup_text_channel(guild, cfg)
                            if txt_channel is None:
                                continue

                            me = getattr(guild, "me", None) or guild.get_member(getattr(self.bot.user, "id", 0) or 0)
                            if me is not None and not txt_channel.permissions_for(me).send_messages:
                                continue

                            role_ids = self.xp.get_role_ids(guild.id)
                            lvl_txt = level_mention(guild, new_lvl, role_ids)

                            await txt_channel.send(
                                f"🎉 Félicitations {member.mention}, tu passes {lvl_txt} grâce à ta présence dans un salon vocal !",
                                allowed_mentions=discord.AllowedMentions(users=True, roles=False),
                            )

                        except discord.Forbidden:
                            log.warning(
                                "XP vocal: permissions insuffisantes pour envoyer le message (guild_id=%s, channel_id=%s)",
                                guild.id,
                                getattr(txt_channel, "id", None),
                            )
                            continue

                        except discord.HTTPException:
                            log.warning(
                                "XP vocal: échec d'envoi du message (HTTPException) (guild_id=%s, channel_id=%s)",
                                guild.id,
                                getattr(txt_channel, "id", None),
                            )
                            continue

                        except Exception:
                            log.exception(
                                "XP vocal: erreur inattendue lors du tick (guild_id=%s, user_id=%s, vc_id=%s)",
                                guild.id,
                                member.id,
                                getattr(vc, "id", None),
                            )
                            continue

            except Exception:
                log.exception("XP vocal: erreur inattendue au niveau du serveur (guild_id=%s)", guild.id)
                continue


    @voice_xp_loop.before_loop
    async def _wait_until_ready(self) -> None:
        """Attente que le bot soit prêt avant de démarrer la boucle de vérification de l'XP vocale."""
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
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
            self.xp.ensure_defaults(member.guild.id)

            now = now_ts()  # helper interne (UTC)

            # On met juste à jour last_tick_ts; le calcul réel est fait par la loop.
            self.xp.voice_upsert_progress(
                member.guild.id,
                member.id,
                last_tick_ts=now,
            )
        except Exception as e:
            log.warning(
                "XP vocal: erreur lors de la mise à jour du progress sur voice_state_update (guild_id=%s, user_id=%s): %s",
                member.guild.id,
                member.id,
                e,
            )
            return


def setup(bot: EldoriaBot) -> None:
    """Fonction d'initialisation du cog XpVoice, appelée par le bot lors du chargement de l'extension."""
    bot.add_cog(XpVoice(bot))
