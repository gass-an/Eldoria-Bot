from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Optional
from zoneinfo import ZoneInfo

import discord

from eldoria.db.repo.xp_repo import xp_get_role_ids

from ..config import AUTO_SAVE_TZ
from ..utils.timestamp import now_ts
from ..db import database_manager
from ..defaults import XP_CONFIG_DEFAULTS, XP_LEVELS_DEFAULTS

TIMEZONE = ZoneInfo(AUTO_SAVE_TZ)

@dataclass(frozen=True)
class XpConfig:
    enabled: bool = bool(XP_CONFIG_DEFAULTS["enabled"])
    points_per_message: int = int(XP_CONFIG_DEFAULTS["points_per_message"])
    cooldown_seconds: int = int(XP_CONFIG_DEFAULTS["cooldown_seconds"])
    bonus_percent: int = int(XP_CONFIG_DEFAULTS["bonus_percent"])
    # Pour les petits messages (<=10) qui commencent par "k" (commandes Karuta)
    # on n'attribue qu'un certain pourcentage de l'XP.
    # Ex: 30 => 30% de l'XP normal.
    karuta_k_small_percent: int = int(XP_CONFIG_DEFAULTS["karuta_k_small_percent"])

    # ---- Vocal XP ----
    voice_enabled: bool = bool(XP_CONFIG_DEFAULTS.get("voice_enabled", True))
    voice_xp_per_interval: int = int(XP_CONFIG_DEFAULTS.get("voice_xp_per_interval", 1))
    voice_interval_seconds: int = int(XP_CONFIG_DEFAULTS.get("voice_interval_seconds", 180))
    voice_daily_cap_xp: int = int(XP_CONFIG_DEFAULTS.get("voice_daily_cap_xp", 100))

    # 0 = auto (system_channel / #general si trouvable), sinon ID du salon.
    voice_levelup_channel_id: int = int(XP_CONFIG_DEFAULTS.get("voice_levelup_channel_id", 0))


def _day_key_utc(ts: int | None = None) -> str:
    dt = datetime.fromtimestamp(
        ts if ts is not None else now_ts(), 
        tz=TIMEZONE #prend la timezone défini dans le .env
        )  
    return dt.strftime("%Y%m%d")



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


def _has_active_server_tag_for_guild(member: discord.abc.User, guild: discord.Guild) -> bool:
    """True si le membre affiche l'identité (Server Tag) de CETTE guilde sur son profil.

    Compatibilité: si la lib ne fournit pas ces champs, retourne False (pas de bonus plutôt que planter).
    """
    # Selon les versions/forks, primary_guild peut être sur User ou accessible via member._user
    user_obj = member
    pg = getattr(user_obj, "primary_guild", None)
    if pg is None:
        pg = getattr(getattr(member, "_user", None), "primary_guild", None)

    if pg is None:
        return False

    identity_enabled = bool(getattr(pg, "identity_enabled", False))
    if not identity_enabled:
        return False

    identity_guild_id = getattr(pg, "identity_guild_id", None)
    if identity_guild_id != guild.id:
        return False

    # Si la lib expose le tag côté guilde, on vérifie aussi l'égalité des tags
    guild_tag = getattr(guild, "tag", None)
    user_tag = getattr(pg, "tag", None)
    if guild_tag and user_tag:
        return str(user_tag).upper() == str(guild_tag).upper()

    return True


def compute_level(xp: int, levels: Iterable[tuple[int, int]]) -> int:
    """Renvoie le niveau correspondant à l'XP (plus haut seuil atteint)."""
    lvl = 1
    for level, required in levels:
        if xp >= required:
            lvl = level
    return lvl

def get_xp_role_ids(guild_id: int | None) -> Dict[int, int]:
    """
    Retourne le mapping {level: role_id} pour un serveur XP.
    Si guild_id est None ou invalide, retourne un dict vide.
    """
    if not guild_id:
        return {}

    try:
        return xp_get_role_ids(guild_id) or {}
    except Exception:
        # sécurité : l'UI ne doit jamais planter à cause de la DB
        return {}


async def ensure_guild_xp_setup(guild: discord.Guild):
    """Crée la config + niveaux par défaut + rôles level5..level1 (si absents),
    sans jamais toucher aux positions (création uniquement).
    """
    database_manager.xp_ensure_defaults(guild.id, XP_LEVELS_DEFAULTS)

    role_ids = database_manager.xp_get_role_ids(guild.id)
    roles_by_id = {r.id: r for r in guild.roles}

    # On crée du plus haut niveau au plus bas : level5 → level1
    for lvl in range(5, 0, -1):
        role: discord.Role | None = None

        # 1) Priorité : role_id déjà connu en DB
        rid = role_ids.get(lvl)
        if rid:
            role = roles_by_id.get(rid)

        # 2) Fallback anti-doublons si DB reset : retrouver par nom
        if role is None:
            role = discord.utils.get(guild.roles, name=f"level{lvl}")

        # 3) Créer si vraiment absent (sans déplacer)
        if role is None:
            try:
                role = await guild.create_role(
                    name=f"level{lvl}",
                    reason="Initialisation des rôles XP",
                )
            except discord.Forbidden:
                # pas la permission de créer des rôles → on arrête sans casser
                return

        # 4) Stocker/mettre à jour en DB
        database_manager.xp_upsert_role_id(guild.id, lvl, role.id)


async def sync_member_level_roles(guild: discord.Guild, member: discord.Member, *, xp: int | None = None):
    """Met à jour les rôles lvlX d'un membre en fonction de son XP."""
    if member.bot:
        return

    if xp is None:
        xp, _ = database_manager.xp_get_member(guild.id, member.id)

    levels = database_manager.xp_get_levels(guild.id)
    if not levels:
        # fallback (normalement impossible si ensure_guild_xp_setup est appelé)
        levels = list(XP_LEVELS_DEFAULTS.items())

    current_lvl = compute_level(xp, levels)
    role_ids = database_manager.xp_get_role_ids(guild.id)
    if not role_ids:
        return

    desired_role_id = role_ids.get(current_lvl)
    desired_role = guild.get_role(desired_role_id) if desired_role_id else None

    # Liste des rôles de niveaux déjà présents
    lvl_roles_present = [r for r in member.roles if any(r.id == rid for rid in role_ids.values())]
    to_remove = [r for r in lvl_roles_present if desired_role is None or r.id != desired_role.id]

    # Ajout / retrait (évite les erreurs si le bot ne peut pas gérer)
    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="Mise à jour niveau XP")
        if desired_role and desired_role not in member.roles:
            await member.add_roles(desired_role, reason="Mise à jour niveau XP")
    except discord.Forbidden:
        return


async def handle_message_xp(message: discord.Message) -> Optional[tuple[int, int, int]]:
    """Attribue l'XP d'un message si le cooldown est passé.

    Retourne (new_xp, new_level, old_level) si XP ajouté, sinon None.
    """
    if message.guild is None:
        return None
    if message.author.bot:
        return None

    guild = message.guild
    member = message.author

    config_raw = database_manager.xp_get_config(guild.id)
    config = XpConfig(**config_raw)

    # XP global switch (par guilde)
    if not config.enabled:
        return None

    now = now_ts()
    old_xp, last_ts = database_manager.xp_get_member(guild.id, member.id)
    if last_ts and (now - last_ts) < config.cooldown_seconds:
        return None

    gained = max(int(config.points_per_message), 0)
    if gained == 0:
        return None


    # Bonus: si le membre affiche le Server Tag de cette guilde sur son profil.
    # Si bonus_percent == 0, cela désactive de fait le bonus.
    if config.bonus_percent > 0 and _has_active_server_tag_for_guild(member, guild):
        gained = int(round(gained * (1 + config.bonus_percent / 100)))

    # Malus "anti-karuta" : les messages très courts qui commencent par "k"/"K" ne donnent
    # qu'un % de l'XP qu'ils auraient dû rapporter (configurable).
    # Exemple typique : k, kd, kcd, kt burn, ...
    content = (message.content or "").strip()
    if content and content[0] in ("k", "K") and len(content) <= 10:
        pct = max(int(getattr(config, "karuta_k_small_percent", 30)), 0)
        gained = int(round(gained * (pct / 100)))

    new_xp = database_manager.xp_add_xp(guild.id, member.id, gained, set_last_xp_ts=now)

    levels = database_manager.xp_get_levels(guild.id)
    old_lvl = compute_level(old_xp, levels)
    new_lvl = compute_level(new_xp, levels)

    await sync_member_level_roles(guild, member, xp=new_xp)

    return new_xp, new_lvl, old_lvl


async def tick_voice_xp_for_member(guild: discord.Guild, member: discord.Member) -> Optional[tuple[int, int, int]]:
    if member.bot:
        return None

    config_raw = database_manager.xp_get_config(guild.id)
    config = XpConfig(**config_raw)

    if not config.enabled or not config.voice_enabled:
        return None

    now = now_ts()
    day_key = _day_key_utc(now)

    prog = database_manager.xp_voice_get_progress(guild.id, member.id)

    # Reset journalier + persistance immédiate
    if prog.get("day_key") != day_key:
        prog = {
            "day_key": day_key,
            "last_tick_ts": 0,
            "buffer_seconds": 0,
            "bonus_cents": 0,
            "xp_today": 0,
        }
        database_manager.xp_voice_upsert_progress(
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
        database_manager.xp_voice_upsert_progress(guild.id, member.id, day_key=day_key, last_tick_ts=now)
        return None

    # L'éligibilité salon est gérée par la loop; ici seulement l'état du membre
    if not is_voice_member_active(member):
        database_manager.xp_voice_upsert_progress(guild.id, member.id, day_key=day_key, last_tick_ts=now)
        return None

    # Bornage delta (anti-jump)
    delta = max(now - last_tick, 0)
    if delta > 600:
        delta = 600

    buffer_seconds = int(prog.get("buffer_seconds", 0) or 0) + delta

    if config.voice_daily_cap_xp <= 0 or config.voice_interval_seconds <= 0 or config.voice_xp_per_interval <= 0:
        database_manager.xp_voice_upsert_progress(guild.id, member.id, day_key=day_key, last_tick_ts=now)
        return None

    xp_today = int(prog.get("xp_today", 0) or 0)
    if xp_today >= config.voice_daily_cap_xp:
        database_manager.xp_voice_upsert_progress(guild.id, member.id, day_key=day_key, last_tick_ts=now, buffer_seconds=0)
        return None

    intervals = buffer_seconds // config.voice_interval_seconds
    base_gain = int(intervals * config.voice_xp_per_interval)
    if base_gain <= 0:
        database_manager.xp_voice_upsert_progress(
            guild.id, member.id, day_key=day_key, last_tick_ts=now, buffer_seconds=buffer_seconds
        )
        return None

    buffer_seconds -= int(intervals * config.voice_interval_seconds)

    total_gain = base_gain
    bonus_cents = int(prog.get("bonus_cents", 0) or 0)

    if config.bonus_percent > 0 and _has_active_server_tag_for_guild(member, guild):
        bonus_cents += base_gain * int(config.bonus_percent)
        extra = bonus_cents // 100
        bonus_cents %= 100
        total_gain += int(extra)

    cap_left = max(int(config.voice_daily_cap_xp) - xp_today, 0)
    if total_gain > cap_left:
        total_gain = cap_left

    new_xp_today = xp_today + int(total_gain)
    database_manager.xp_voice_upsert_progress(
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

    old_xp, _ = database_manager.xp_get_member(guild.id, member.id)
    new_xp = database_manager.xp_add_xp(guild.id, member.id, int(total_gain))

    levels = database_manager.xp_get_levels(guild.id)
    old_lvl = compute_level(old_xp, levels)
    new_lvl = compute_level(new_xp, levels)

    await sync_member_level_roles(guild, member, xp=new_xp)
    return new_xp, new_lvl, old_lvl

