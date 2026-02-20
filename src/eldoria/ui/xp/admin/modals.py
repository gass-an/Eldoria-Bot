"""Modals pour l'interface d'administration du système XP."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord

from eldoria.ui.xp.admin.validators import XP_SETTINGS_RULES, XP_VOICE_RULES, validate_int_ranges


def _parse_optional_int(raw: str | None) -> int | None:
    s = (raw or "").strip()
    if not s:
        return None
    return int(s)


OnSubmitDict = Callable[[discord.Interaction, dict[str, int | None]], Awaitable[None]]
OnSubmitInt = Callable[[discord.Interaction, int], Awaitable[None]]


class XpSettingsModal(discord.ui.Modal):
    """Saisie précise des paramètres messages (champs vides = inchangés)."""

    def __init__(self, *, on_submit: OnSubmitDict, current: dict) -> None:
        """Initialise le modal de paramètres généraux du système XP."""
        super().__init__(title="XP — Paramètres (messages)")
        self._on_submit_cb = on_submit

        self.points_per_message = discord.ui.InputText(
            label="XP / message (>=0)",
            placeholder=f"Actuel: {current.get('points_per_message')} (Nombre entier)",
            required=False,
            min_length=0,
            max_length=6,
        )
        self.cooldown_seconds = discord.ui.InputText(
            label="Délai XP entre 2 messages (≥ 0 s)",
            placeholder=f"Actuel: {current.get('cooldown_seconds')} (Nombre entier)",
            required=False,
            min_length=0,
            max_length=6,
        )
        self.bonus_percent = discord.ui.InputText(
            label="Bonus si tag serveur actif (0..300%)",
            placeholder=f"Actuel: {current.get('bonus_percent')} (Nombre entier)",
            required=False,
            min_length=0,
            max_length=4,
        )
        self.karuta_k_small_percent = discord.ui.InputText(
            label="% XP si message pour Karuta (0..100)",
            placeholder=f"Actuel: {current.get('karuta_k_small_percent')} (Nombre entier)",
            required=False,
            min_length=0,
            max_length=3,
        )

        self.add_item(self.points_per_message)
        self.add_item(self.cooldown_seconds)
        self.add_item(self.bonus_percent)
        self.add_item(self.karuta_k_small_percent)

    async def callback(self, interaction: discord.Interaction) -> None:
        """Traite la soumission du modal de paramètres généraux du système XP."""
        try:
            payload: dict[str, int | None] = {
                "points_per_message": _parse_optional_int(self.points_per_message.value),
                "cooldown_seconds": _parse_optional_int(self.cooldown_seconds.value),
                "bonus_percent": _parse_optional_int(self.bonus_percent.value),
                "karuta_k_small_percent": _parse_optional_int(self.karuta_k_small_percent.value),
            }
        except ValueError:
            await interaction.response.send_message("❌ Valeur invalide : utilise uniquement des nombres entiers.", ephemeral=True)
            return
        
        errs = validate_int_ranges(payload, XP_SETTINGS_RULES)
        if errs:
            await interaction.response.send_message(
                "❌ **Paramètres invalides :**\n" + "\n".join(errs),
                ephemeral=True,
            )
            return
        
        await self._on_submit_cb(interaction, payload)


class XpVoiceModal(discord.ui.Modal):
    """Saisie précise des paramètres vocaux (champs vides = inchangés)."""

    def __init__(self, *, on_submit: OnSubmitDict, current: dict) -> None:
        """Initialise le modal de paramètres vocaux du système XP."""
        super().__init__(title="XP — Paramètres (vocal)")
        self._on_submit_cb = on_submit

        self.voice_interval_seconds = discord.ui.InputText(
            label="Intervalle XP vocal (30..3600 s)",
            placeholder=f"Actuel: {current.get('voice_interval_seconds')} (Nombre entier)",
            required=False,
            min_length=0,
            max_length=4,
        )
        self.voice_xp_per_interval = discord.ui.InputText(
            label="XP / intervalle (>=0)",
            placeholder=f"Actuel: {current.get('voice_xp_per_interval')} (Nombre entier)",
            required=False,
            min_length=0,
            max_length=6,
        )
        self.voice_daily_cap_xp = discord.ui.InputText(
            label="Cap journalier (>=0)",
            placeholder=f"Actuel: {current.get('voice_daily_cap_xp')} (Nombre entier)",
            required=False,
            min_length=0,
            max_length=6,
        )

        self.add_item(self.voice_interval_seconds)
        self.add_item(self.voice_xp_per_interval)
        self.add_item(self.voice_daily_cap_xp)

    async def callback(self, interaction: discord.Interaction) -> None:
        """Traite la soumission du modal de paramètres vocaux du système XP."""
        try:
            payload: dict[str, int | None] = {
                "voice_interval_seconds": _parse_optional_int(self.voice_interval_seconds.value),
                "voice_xp_per_interval": _parse_optional_int(self.voice_xp_per_interval.value),
                "voice_daily_cap_xp": _parse_optional_int(self.voice_daily_cap_xp.value),
            }
        except ValueError:
            await interaction.response.send_message("❌ Valeur invalide : utilise uniquement des nombres entiers.", ephemeral=True)
            return
        
        errs = validate_int_ranges(payload, XP_VOICE_RULES)
        if errs:
            await interaction.response.send_message(
                "❌ **Paramètres invalides :**\n" + "\n".join(errs),
                ephemeral=True,
            )
            return

        await self._on_submit_cb(interaction, payload)


class XpLevelThresholdModal(discord.ui.Modal):
    """Saisie précise d'un seuil de niveau."""

    def __init__(self, *, level: int, current_xp: int, on_submit: OnSubmitInt) -> None:
        """Initialise le modal de seuil de niveau du système XP.""" 
        super().__init__(title=f"XP — Seuil du niveau {level}")
        self._on_submit_cb = on_submit

        self.xp_required = discord.ui.InputText(
            label="XP requis (>=0)",
            placeholder=f"Actuel: {current_xp} (Nombre entier)",
            required=True,
            min_length=1,
            max_length=8,
        )
        self.add_item(self.xp_required)

    async def callback(self, interaction: discord.Interaction) -> None:
        """Traite la soumission du modal de seuil de niveau du système XP."""
        try:
            val = int((self.xp_required.value or "").strip())
            if val < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ XP requis invalide (nombre >= 0).", ephemeral=True)
            return

        await self._on_submit_cb(interaction, val)