"""Validation des données de configuration du système XP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RangeRule:
    """Règle de validation pour une valeur entière."""

    label: str
    min_value: int | None = None
    max_value: int | None = None


XP_SETTINGS_RULES: dict[str, RangeRule] = {
    "points_per_message": RangeRule(label="XP / message", min_value=0, max_value=1000),
    "cooldown_seconds": RangeRule(label="Délai XP (s)", min_value=0, max_value=3600),
    "bonus_percent": RangeRule(label="Bonus tag (%)", min_value=0, max_value=300),
    "karuta_k_small_percent": RangeRule(label="Karuta k<=10 (%)", min_value=0, max_value=100),
}

XP_VOICE_RULES: dict[str, RangeRule] = {
    "voice_interval_seconds": RangeRule(label="Intervalle vocal (s)", min_value=30, max_value=3600),
    "voice_xp_per_interval": RangeRule(label="XP / intervalle", min_value=0, max_value=1000),
    "voice_daily_cap_xp": RangeRule(label="Cap journalier", min_value=0, max_value=5000),
}

def validate_int_ranges(values: dict[str, int | None], rules: dict[str, RangeRule]) -> list[str]:
    """Retourne une liste de messages d'erreur (vide si OK)."""
    errors: list[str] = []

    for key, rule in rules.items():
        v = values.get(key)
        if v is None:
            continue

        if rule.min_value is not None and v < rule.min_value:
            errors.append(f"• **{rule.label}** doit être ≥ **{rule.min_value}** (reçu: `{v}`)")
        if rule.max_value is not None and v > rule.max_value:
            errors.append(f"• **{rule.label}** doit être ≤ **{rule.max_value}** (reçu: `{v}`)")

    return errors