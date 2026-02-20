from __future__ import annotations

import pytest

from eldoria.ui.xp.admin.validators import (
    XP_SETTINGS_RULES,
    XP_VOICE_RULES,
    RangeRule,
    validate_int_ranges,
)


# ---------- Tests: RangeRule ----------
def test_range_rule_is_frozen():
    rule = RangeRule(label="Test", min_value=0, max_value=10)

    with pytest.raises(Exception):
        # dataclass(frozen=True) => immuable
        rule.min_value = 5  # type: ignore[attr-defined]


# ---------- Tests: validate_int_ranges (basic OK) ----------
def test_validate_ok_within_range():
    values = {"points_per_message": 10}
    errors = validate_int_ranges(values, XP_SETTINGS_RULES)
    assert errors == []


def test_validate_ignores_none_values():
    values = {
        "points_per_message": None,
        "cooldown_seconds": None,
    }
    errors = validate_int_ranges(values, XP_SETTINGS_RULES)
    assert errors == []


def test_validate_ignores_missing_keys():
    values = {"unknown_key": 999}
    errors = validate_int_ranges(values, XP_SETTINGS_RULES)
    assert errors == []


# ---------- Tests: min violations ----------
def test_validate_min_violation():
    values = {"points_per_message": -1}
    errors = validate_int_ranges(values, XP_SETTINGS_RULES)

    assert len(errors) == 1
    assert "XP / message" in errors[0]
    assert "≥ **0**" in errors[0]
    assert "`-1`" in errors[0]


# ---------- Tests: max violations ----------
def test_validate_max_violation():
    values = {"bonus_percent": 999}
    errors = validate_int_ranges(values, XP_SETTINGS_RULES)

    assert len(errors) == 1
    assert "Bonus tag (%)" in errors[0]
    assert "≤ **300**" in errors[0]
    assert "`999`" in errors[0]


# ---------- Tests: both min and max ----------
def test_validate_multiple_errors_accumulate():
    values = {
        "points_per_message": -5,        # below min
        "bonus_percent": 999,            # above max
        "cooldown_seconds": 4000,        # above max
    }
    errors = validate_int_ranges(values, XP_SETTINGS_RULES)

    assert len(errors) == 3

    assert any("XP / message" in e for e in errors)
    assert any("Bonus tag (%)" in e for e in errors)
    assert any("Délai XP (s)" in e for e in errors)


# ---------- Tests: voice rules ----------
def test_validate_voice_min_violation():
    values = {"voice_interval_seconds": 10}  # min=30
    errors = validate_int_ranges(values, XP_VOICE_RULES)

    assert len(errors) == 1
    assert "Intervalle vocal (s)" in errors[0]
    assert "≥ **30**" in errors[0]


def test_validate_voice_max_violation():
    values = {"voice_daily_cap_xp": 9999}  # max=5000
    errors = validate_int_ranges(values, XP_VOICE_RULES)

    assert len(errors) == 1
    assert "Cap journalier" in errors[0]
    assert "≤ **5000**" in errors[0]


# ---------- Tests: custom rule (min only / max only) ----------
def test_validate_rule_with_min_only():
    rules = {
        "x": RangeRule(label="X value", min_value=5, max_value=None),
    }
    errors = validate_int_ranges({"x": 3}, rules)
    assert len(errors) == 1
    assert "≥ **5**" in errors[0]


def test_validate_rule_with_max_only():
    rules = {
        "x": RangeRule(label="X value", min_value=None, max_value=10),
    }
    errors = validate_int_ranges({"x": 20}, rules)
    assert len(errors) == 1
    assert "≤ **10**" in errors[0]