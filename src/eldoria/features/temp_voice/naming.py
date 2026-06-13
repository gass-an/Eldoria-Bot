"""Utilitaires de nommage pour les salons vocaux temporaires."""

from __future__ import annotations

import re
from typing import Final

MAX_VOICE_CHANNEL_NAME_LENGTH: Final = 100
_LEADING_DECORATIONS_RE = re.compile(r"^[\W_]+", flags=re.UNICODE)


def _normalize_label(value: str, *, fallback: str) -> str:
    label = re.sub(r"\s+", " ", value).strip()
    label = _LEADING_DECORATIONS_RE.sub("", label).strip()
    return label or fallback


def build_temp_voice_channel_name(parent_name: str, member_display_name: str) -> str:
    """Construit un nom lisible pour un salon vocal temporaire.

    Exemple: ``➕ - Duo`` + ``Anthony`` -> ``Duo de Anthony``.
    """

    parent_label = _normalize_label(parent_name, fallback="Salon")
    member_label = _normalize_label(member_display_name, fallback="membre")

    suffix = f" de {member_label}"
    if len(suffix) >= MAX_VOICE_CHANNEL_NAME_LENGTH:
        member_label = member_label[: MAX_VOICE_CHANNEL_NAME_LENGTH - 4].rstrip() or "membre"
        suffix = f" de {member_label}"
        if len(suffix) >= MAX_VOICE_CHANNEL_NAME_LENGTH:
            return suffix[:MAX_VOICE_CHANNEL_NAME_LENGTH].rstrip()

    available_for_parent = MAX_VOICE_CHANNEL_NAME_LENGTH - len(suffix)
    parent_label = parent_label[:available_for_parent].rstrip(" -–—:,_") or parent_label[:available_for_parent].rstrip()
    if not parent_label:
        parent_label = "Salon"

    name = f"{parent_label}{suffix}"
    return name[:MAX_VOICE_CHANNEL_NAME_LENGTH].rstrip()

