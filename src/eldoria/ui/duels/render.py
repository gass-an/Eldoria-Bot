"""Module de rendu pour les interfaces utilisateur de duels."""

from __future__ import annotations

import logging

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.exceptions.duel import InvalidSnapshot
from eldoria.features.xp.roles import sync_xp_roles_for_users
from eldoria.ui.duels.registry import require_renderer

log = logging.getLogger(__name__)

async def render_duel_message(
    *,
    snapshot: dict,
    guild: discord.Guild,
    bot: EldoriaBot,
) -> tuple[discord.Embed, list[discord.File], discord.ui.View | None]:
    """Point d'entrée unique pour rendre un duel (embed + fichiers + view) depuis un snapshot."""
    # ✅ 0) Appliquer les effets “hors rendu” (ex: sync roles XP)
    effects = snapshot.get("effects") or {}
    if effects.get("xp_changed"):
        user_ids = effects.get("sync_roles_user_ids") or []
        if user_ids:
            try:
                await sync_xp_roles_for_users(guild, list(user_ids))
            except Exception:
                log.exception(f"Erreur lors du sync des rôles XP après un duel : {user_ids}")
                pass

    # ✅ 1) Rendu normal
    duel = snapshot.get("duel") or {}
    game_key = duel.get("game_type")
    if not game_key:
        raise InvalidSnapshot()

    renderer = require_renderer(str(game_key))
    return await renderer(snapshot, guild, bot)
