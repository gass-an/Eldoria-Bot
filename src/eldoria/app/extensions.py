"""Module définissant les extensions à charger pour le bot Eldoria."""

from typing import Final

from eldoria.config import SAVE_ENABLED

_base_extensions: list[str] = [
    "eldoria.extensions.core",
    "eldoria.extensions.xp",
    "eldoria.extensions.xp_voice",
    "eldoria.extensions.duels",
    "eldoria.extensions.reaction_roles",
    "eldoria.extensions.secret_roles",
    "eldoria.extensions.temp_voice",
    "eldoria.extensions.welcome_message",
]

if SAVE_ENABLED:
    _base_extensions.append("eldoria.extensions.saves")

EXTENSIONS: Final[tuple[str, ...]] = tuple(_base_extensions)