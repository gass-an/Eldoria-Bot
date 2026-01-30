from __future__ import annotations

from typing import Optional

import discord

from .registry import require_renderer


async def render_duel_message(
    *,
    snapshot: dict,
    guild: discord.Guild,
    bot: object,
) -> tuple[discord.Embed, list[discord.File], Optional[discord.ui.View]]:
    """Point d'entrée unique pour rendre un duel (embed + fichiers + view) depuis un snapshot."""
    duel = snapshot.get("duel") or {}
    game_key = duel.get("game_type")
    if not game_key:
        raise ValueError("snapshot.duel.game_type manquant")

    renderer = require_renderer(str(game_key))
    return await renderer(snapshot, guild, bot)
