"""Modules d'embeds pour l'interface d'administration du système XP."""

from __future__ import annotations

import discord

from eldoria.ui.common.embeds.colors import (
    EMBED_COLOUR_ERROR,
    EMBED_COLOUR_PRIMARY,
    EMBED_COLOUR_VALIDATION,
)
from eldoria.ui.common.embeds.images import common_files, decorate


def _bool_badge(value: bool) -> str:
    return "✅ Activé" if value else "⛔ Désactivé"


def build_xp_admin_menu_embed(cfg: dict) -> tuple[discord.Embed, list[discord.File]]:
    """Embed du panneau d'administration général du système XP."""
    enabled = bool(cfg.get("enabled"))
    colour = EMBED_COLOUR_VALIDATION if enabled else EMBED_COLOUR_ERROR

    embed = discord.Embed(
        title="⭐ Admin XP — Panneau",
        description=(
            f"**Système XP :** {_bool_badge(enabled)}\n\n"
            "Choisis une section :\n"
            "• ⚙️ Paramètres (messages)\n"
            "• 🎙️ Vocal\n"
            "• 🏅 Niveaux & rôles\n\u200b"
        ),
        color=colour,
    )
    embed.set_footer(text="Configure le système d'XP pour ton serveur.")
    decorate(embed, None, None)
    return embed, common_files(None, None)


def build_xp_admin_settings_embed(cfg: dict) -> tuple[discord.Embed, list[discord.File]]:
    """Embed du panneau d'administration des paramètres généraux du système XP."""
    enabled = bool(cfg.get("enabled"))
    embed = discord.Embed(
        title="⚙️ Admin XP — Paramètres (messages)",
        description=(
            f"**Système XP :** {_bool_badge(enabled)}\n\n"
            f"**XP / message :** `{cfg.get('points_per_message')}`\n"
            f"**Cooldown :** `{cfg.get('cooldown_seconds')}s`\n"
            f"**Bonus tag :** `{cfg.get('bonus_percent')}%`\n"
            f"**Karuta k<=10 :** `{cfg.get('karuta_k_small_percent')}%`\n\u200b"
        ),
        color=EMBED_COLOUR_PRIMARY,
    )
    embed.set_footer(text="Configure les paramètres liés aux messages pour le système d'XP.")
    decorate(embed, None, None)
    return embed, common_files(None, None)


def build_xp_admin_voice_embed(cfg: dict, channel: discord.abc.GuildChannel | None) -> tuple[discord.Embed, list[discord.File]]:
    """Embed du panneau d'administration des paramètres liés à l'XP vocal."""
    enabled = bool(cfg.get("enabled"))
    voice_enabled = bool(cfg.get("voice_enabled"))
    channel_txt = channel.mention if channel is not None else "*(aucun salon configuré)*"

    embed = discord.Embed(
        title="🎙️ Admin XP — Vocal",
        description=(
            f"**Système XP :** {_bool_badge(enabled)}\n"
            f"**XP Vocal :** {_bool_badge(voice_enabled)}\n\n"
            f"**Intervalle :** `{cfg.get('voice_interval_seconds')}s`\n"
            f"**XP / intervalle :** `{cfg.get('voice_xp_per_interval')}`\n"
            f"**Cap / jour :** `{cfg.get('voice_daily_cap_xp')}`\n"
            f"**Salon annonces :** {channel_txt}\n\u200b"
        ),
        color=EMBED_COLOUR_PRIMARY,
    )
    embed.set_footer(text="Configure les paramètres liés à l'XP vocal.")
    if voice_enabled and channel is None:
        embed.add_field(
            name="⚠️ Salon d'annonces manquant",
            value="Tu as activé l'XP vocal mais aucun salon d'annonces n'est défini.",
            inline=False,
        )

    decorate(embed, None, None)
    return embed, common_files(None, None)


def build_xp_admin_levels_embed(
    *,
    levels_with_roles: list[tuple[int, int, int | None]],
    selected_level: int,
    selected_role: discord.Role | None,
) -> tuple[discord.Embed, list[discord.File]]:
    """Embed du panneau d'administration des niveaux et rôles associés."""
    lines = []
    for lvl, xp_req, role_id in levels_with_roles:
        role_txt = f"<@&{role_id}>" if role_id else "*(aucun rôle)*"
        cursor = "➡️ " if lvl == selected_level else "• "
        lines.append(f"{cursor}**Niveau {lvl}** : `{xp_req} XP` → {role_txt}")

    sel_role_txt = selected_role.mention if selected_role else "*(aucun rôle)*"

    embed = discord.Embed(
        title="🏅 Admin XP — Niveaux & rôles",
        description=(
            "\n".join(lines)
            + "\n\n"
            + f"**Sélection :** Niveau `{selected_level}` → rôle {sel_role_txt}\n"
            "Utilise le menu pour choisir un niveau, puis modifie seuil / rôle.\n\u200b"
        ),
        color=EMBED_COLOUR_PRIMARY,
    )
    embed.set_footer(text="Configure les niveaux et rôles associés au système d'XP.")
    decorate(embed, None, None)
    return embed, common_files(None, None)