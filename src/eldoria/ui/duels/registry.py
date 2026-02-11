"""Module de registre pour les fonctions de rendu des interfaces utilisateur de duels."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord

# render returns (embed, files, view)
RenderFn = Callable[[dict, discord.Guild, object], Awaitable[tuple[discord.Embed, list[discord.File], discord.ui.View | None]]]

_RENDERERS: dict[str, RenderFn] = {}


def register_renderer(game_key: str, renderer: RenderFn) -> None:
    """Enregistre une fonction de rendu pour un type de jeu de duel."""
    _RENDERERS[str(game_key)] = renderer


def require_renderer(game_key: str) -> RenderFn:
    """Récupère la fonction de rendu pour un type de jeu de duel, ou lève une erreur si aucune n'est enregistrée."""
    key = str(game_key)
    if key not in _RENDERERS:
        raise ValueError(f"No duel UI renderer registered for game_key={key}")
    return _RENDERERS[key]
