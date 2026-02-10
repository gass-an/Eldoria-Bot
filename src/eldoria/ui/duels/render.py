from __future__ import annotations
from typing import Optional
import discord

from eldoria.features.xp.roles import sync_xp_roles_for_users
from .registry import require_renderer


async def render_duel_message(
    *,
    snapshot: dict,
    guild: discord.Guild,
    bot: object,
) -> tuple[discord.Embed, list[discord.File], Optional[discord.ui.View]]:
    """Point d'entrée unique pour rendre un duel (embed + fichiers + view) depuis un snapshot."""
    
    # ✅ 0) Appliquer les effets “hors rendu” (ex: sync roles XP)
    effects = snapshot.get("effects") or {}
    if effects.get("xp_changed"):
        user_ids = effects.get("sync_roles_user_ids") or []
        if user_ids:
            try:
                await sync_xp_roles_for_users(guild, list(user_ids))
            except Exception:
                # On évite de casser le rendu si Discord refuse / membre introuvable, etc.
                pass

    # ✅ 1) Rendu normal
    duel = snapshot.get("duel") or {}
    game_key = duel.get("game_type")
    if not game_key:
        raise ValueError("snapshot.duel.game_type manquant")

    renderer = require_renderer(str(game_key))
    return await renderer(snapshot, guild, bot)
