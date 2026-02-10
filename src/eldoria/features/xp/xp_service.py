from dataclasses import dataclass
from sqlite3 import Connection
from typing import Iterable, Optional

import discord

from eldoria.db.repo import xp_repo
from eldoria.features.xp._internal import (
    message_xp,
    setup,
    snapshot, 
    voice_xp,
    )
from eldoria.features.xp import levels, roles

@dataclass(slots=True)
class XpService:

    # -------------------------- fonctions synchrone --------------------------
    def is_voice_member_active(self, member: discord.Member) -> bool:
        return voice_xp.is_voice_member_active(member)

    def compute_level(self, xp: int, level: Iterable[tuple[int, int]]) -> int:
        return levels.compute_level(xp, level)
    
    def build_snapshot_for_xp_profile(self, guild: discord.Guild, user_id: int) -> dict[str, str]: 
        return snapshot.build_snapshot_for_xp_profile(guild, user_id)
        
    def get_leaderboard_items(self, guild: discord.Guild, *, limit: int = 200, offset: int = 0) -> list[tuple[int, int, int, str]]:
        return snapshot.get_leaderboard_items(guild, limit=limit, offset=offset)

    def is_enabled(self, guild_id: int) -> bool:
        return xp_repo.xp_is_enabled(guild_id)
    
    def ensure_defaults(self, guild_id: int, default_levels: dict[int, int] | None = None) -> None:
        return xp_repo.xp_ensure_defaults(guild_id, default_levels)
    
    def get_config(self, guild_id: int) -> dict:
        return xp_repo.xp_get_config(guild_id)
    
    def get_role_ids(self, guild_id: int) -> dict[int, int]:
        return xp_repo.xp_get_role_ids(guild_id)
    
    def get_levels_with_roles(self, guild_id: int) -> list[tuple[int, int, int | None]]:
        return xp_repo.xp_get_levels_with_roles(guild_id)

    def set_level_threshold(self, guild_id: int, level: int, xp_required: int) -> None:
        return xp_repo.xp_set_level_threshold(guild_id, level, xp_required)
    
    def upsert_role_id(self, guild_id: int, level: int, role_id: int) -> None:
        return xp_repo.xp_upsert_role_id(guild_id, level, role_id)
    
    def get_levels(self, guild_id: int) -> list[tuple[int, int]]:
        return xp_repo.xp_get_levels(guild_id)

    def add_xp(
        self,
        guild_id: int,
        user_id: int,
        delta: int,
        *,
        set_last_xp_ts: int | None = None,
        conn: Connection | None = None,
    ) -> int:
        return xp_repo.xp_add_xp(
            guild_id=guild_id,
            user_id=user_id,
            delta=delta,
            set_last_xp_ts=set_last_xp_ts,
            conn=conn,
        )
    
    def voice_upsert_progress(
        self,
        guild_id: int,
        user_id: int,
        *,
        day_key: str | None = None,
        last_tick_ts: int | None = None,
        buffer_seconds: int | None = None,
        bonus_cents: int | None = None,
        xp_today: int | None = None,
    ) -> None:
        return xp_repo.xp_voice_upsert_progress(
            guild_id,
            user_id,
            day_key=day_key ,
            last_tick_ts=last_tick_ts ,
            buffer_seconds=buffer_seconds ,
            bonus_cents=bonus_cents ,
            xp_today=xp_today,
        )
    
    def set_config(
        self,
        guild_id: int,
        *,
        enabled: bool | None = None,
        points_per_message: int | None = None,
        cooldown_seconds: int | None = None,
        bonus_percent: int | None = None,
        karuta_k_small_percent: int | None = None,

        voice_enabled: bool | None = None,
        voice_xp_per_interval: int | None = None,
        voice_interval_seconds: int | None = None,
        voice_daily_cap_xp: int | None = None,
        voice_levelup_channel_id: int | None = None,
    ) -> None:
        return xp_repo.xp_set_config(
            guild_id,
            enabled=enabled,
            points_per_message=points_per_message,
            cooldown_seconds=cooldown_seconds,
            bonus_percent=bonus_percent,
            karuta_k_small_percent=karuta_k_small_percent,

            voice_enabled=voice_enabled,
            voice_xp_per_interval=voice_xp_per_interval,
            voice_interval_seconds=voice_interval_seconds,
            voice_daily_cap_xp=voice_daily_cap_xp,
            voice_levelup_channel_id=voice_levelup_channel_id,
        )
    

    # -------------------------- fonctions asynchrone --------------------------
    async def handle_message_xp(self, message: discord.Message) -> Optional[tuple[int, int, int]]:
        return await message_xp.handle_message_xp(message)
        
    async def sync_xp_roles_for_users(self, guild: discord.Guild, user_ids: list[int]) -> None:
        return await roles.sync_xp_roles_for_users(guild, user_ids)
    
    async def sync_member_level_roles(self, guild: discord.Guild, member: discord.Member, *, xp: int | None = None) -> None:
        return await roles.sync_member_level_roles(guild, member, xp=xp)

    async def tick_voice_xp_for_member(self, guild: discord.Guild, member: discord.Member) -> Optional[tuple[int, int, int]]:
        return await voice_xp.tick_voice_xp_for_member(guild, member)
    
    async def ensure_guild_xp_setup(self, guild: discord.Guild) -> None:
        return await setup.ensure_guild_xp_setup(guild)

    
    