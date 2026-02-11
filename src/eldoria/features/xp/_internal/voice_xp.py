"""Module de logique métier pour la fonctionnalité d'XP par message."""

import discord

from eldoria.db.repo import xp_repo
from eldoria.features.xp._internal.config import XpConfig
from eldoria.features.xp._internal.tags import has_active_server_tag_for_guild
from eldoria.features.xp._internal.time import day_key_utc
from eldoria.features.xp.levels import compute_level
from eldoria.features.xp.roles import sync_member_level_roles
from eldoria.utils.timestamp import now_ts


def is_voice_member_active(member: discord.Member) -> bool:
    """Actif = peut participer (non-bot, en vocal, pas mute/deaf)."""
    if member.bot:
        return False
    vs = member.voice
    if vs is None or vs.channel is None:
        return False

    # Muted ou deaf (server ou self)
    if bool(getattr(vs, "mute", False)) or bool(getattr(vs, "self_mute", False)):
        return False
    if bool(getattr(vs, "deaf", False)) or bool(getattr(vs, "self_deaf", False)):
        return False

    return True


def is_voice_eligible_in_channel(member: discord.Member, active_count: int) -> bool:
    """Éligible = membre actif + au moins 2 actifs dans le salon."""
    if not is_voice_member_active(member):
        return False
    return active_count >= 2


async def tick_voice_xp_for_member(guild: discord.Guild, member: discord.Member) -> tuple[int, int, int] | None:
    """Attribue l'XP vocale à un membre si les conditions sont remplies.

    Retourne (new_xp, new_level, old_level) si XP ajouté, sinon None.
    """
    if member.bot:
        return None

    config_raw = xp_repo.xp_get_config(guild.id)
    config = XpConfig(**config_raw)

    if not config.enabled or not config.voice_enabled:
        return None

    now = now_ts()
    day_key = day_key_utc(now)

    prog = xp_repo.xp_voice_get_progress(guild.id, member.id)

    # Reset journalier + persistance immédiate
    if prog.get("day_key") != day_key:
        prog = {
            "day_key": day_key,
            "last_tick_ts": 0,
            "buffer_seconds": 0,
            "bonus_cents": 0,
            "xp_today": 0,
        }
        xp_repo.xp_voice_upsert_progress(
            guild.id,
            member.id,
            day_key=day_key,
            last_tick_ts=0,
            buffer_seconds=0,
            bonus_cents=0,
            xp_today=0,
        )

    last_tick = int(prog.get("last_tick_ts", 0) or 0)
    if last_tick <= 0:
        xp_repo.xp_voice_upsert_progress(guild.id, member.id, day_key=day_key, last_tick_ts=now)
        return None

    # L'éligibilité salon est gérée par la loop; ici seulement l'état du membre
    if not is_voice_member_active(member):
        xp_repo.xp_voice_upsert_progress(guild.id, member.id, day_key=day_key, last_tick_ts=now)
        return None

    # Bornage delta (anti-jump)
    delta = max(now - last_tick, 0)
    if delta > 600:
        delta = 600

    buffer_seconds = int(prog.get("buffer_seconds", 0) or 0) + delta

    if config.voice_daily_cap_xp <= 0 or config.voice_interval_seconds <= 0 or config.voice_xp_per_interval <= 0:
        xp_repo.xp_voice_upsert_progress(guild.id, member.id, day_key=day_key, last_tick_ts=now)
        return None

    xp_today = int(prog.get("xp_today", 0) or 0)
    if xp_today >= config.voice_daily_cap_xp:
        xp_repo.xp_voice_upsert_progress(guild.id, member.id, day_key=day_key, last_tick_ts=now, buffer_seconds=0)
        return None

    intervals = buffer_seconds // config.voice_interval_seconds
    base_gain = int(intervals * config.voice_xp_per_interval)
    if base_gain <= 0:
        xp_repo.xp_voice_upsert_progress(
            guild.id, member.id, day_key=day_key, last_tick_ts=now, buffer_seconds=buffer_seconds
        )
        return None

    buffer_seconds -= int(intervals * config.voice_interval_seconds)

    total_gain = base_gain
    bonus_cents = int(prog.get("bonus_cents", 0) or 0)

    if config.bonus_percent > 0 and has_active_server_tag_for_guild(member, guild):
        bonus_cents += base_gain * int(config.bonus_percent)
        extra = bonus_cents // 100
        bonus_cents %= 100
        total_gain += int(extra)

    cap_left = max(int(config.voice_daily_cap_xp) - xp_today, 0)
    if total_gain > cap_left:
        total_gain = cap_left

    new_xp_today = xp_today + int(total_gain)
    xp_repo.xp_voice_upsert_progress(
        guild.id,
        member.id,
        day_key=day_key,
        last_tick_ts=now,
        buffer_seconds=int(buffer_seconds),
        bonus_cents=int(bonus_cents),
        xp_today=int(new_xp_today),
    )

    if total_gain <= 0:
        return None

    old_xp, _ = xp_repo.xp_get_member(guild.id, member.id)
    new_xp = xp_repo.xp_add_xp(guild.id, member.id, int(total_gain))

    levels = xp_repo.xp_get_levels(guild.id)
    old_lvl = compute_level(old_xp, levels)
    new_lvl = compute_level(new_xp, levels)

    await sync_member_level_roles(guild, member, xp=new_xp)
    return new_xp, new_lvl, old_lvl
