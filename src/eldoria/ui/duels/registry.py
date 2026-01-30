from __future__ import annotations

from typing import Awaitable, Callable, Optional, Protocol

import discord

# render returns (embed, files, view)
RenderFn = Callable[[dict, discord.Guild, object], Awaitable[tuple[discord.Embed, list[discord.File], Optional[discord.ui.View]]]]

_RENDERERS: dict[str, RenderFn] = {}


def register_renderer(game_key: str, renderer: RenderFn) -> None:
    _RENDERERS[str(game_key)] = renderer


def require_renderer(game_key: str) -> RenderFn:
    key = str(game_key)
    if key not in _RENDERERS:
        raise ValueError(f"No duel UI renderer registered for game_key={key}")
    return _RENDERERS[key]
