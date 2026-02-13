import importlib

import pytest

import eldoria.defaults as defaults
from eldoria.features.xp._internal import config as xp_config_module


def _reload_with_defaults(monkeypatch: pytest.MonkeyPatch, fake_defaults: dict) -> object:
    # Patch la source réelle (eldoria.defaults), pas la copie dans config.py
    monkeypatch.setattr(defaults, "XP_CONFIG_DEFAULTS", fake_defaults, raising=True)
    importlib.reload(xp_config_module)
    return xp_config_module


def test_xp_config_uses_defaults(monkeypatch):
    fake_defaults = {
        "enabled": False,
        "points_per_message": 5,
        "cooldown_seconds": 10,
        "bonus_percent": 20,
        "karuta_k_small_percent": 30,
        "voice_enabled": False,
        "voice_xp_per_interval": 2,
        "voice_interval_seconds": 60,
        "voice_daily_cap_xp": 50,
        "voice_levelup_channel_id": 999,
    }

    mod = _reload_with_defaults(monkeypatch, fake_defaults)
    cfg = mod.XpConfig()

    assert cfg.enabled is False
    assert cfg.points_per_message == 5
    assert cfg.cooldown_seconds == 10
    assert cfg.bonus_percent == 20
    assert cfg.karuta_k_small_percent == 30
    assert cfg.voice_enabled is False
    assert cfg.voice_xp_per_interval == 2
    assert cfg.voice_interval_seconds == 60
    assert cfg.voice_daily_cap_xp == 50
    assert cfg.voice_levelup_channel_id == 999


def test_xp_config_voice_defaults_fallback(monkeypatch):
    fake_defaults = {
        "enabled": True,
        "points_per_message": 1,
        "cooldown_seconds": 2,
        "bonus_percent": 3,
        "karuta_k_small_percent": 4,
        # volontairement sans voice_*
    }

    mod = _reload_with_defaults(monkeypatch, fake_defaults)
    cfg = mod.XpConfig()

    assert cfg.voice_enabled is True
    assert cfg.voice_xp_per_interval == 1
    assert cfg.voice_interval_seconds == 180
    assert cfg.voice_daily_cap_xp == 100
    assert cfg.voice_levelup_channel_id == 0


def test_xp_config_is_frozen():
    cfg = xp_config_module.XpConfig()
    with pytest.raises((AttributeError, TypeError)):
        cfg.points_per_message = 999


def test_xp_config_casts_types(monkeypatch):
    fake_defaults = {
        "enabled": 0,
        "points_per_message": "10",
        "cooldown_seconds": "20",
        "bonus_percent": "30",
        "karuta_k_small_percent": "40",
        "voice_enabled": 1,
        "voice_xp_per_interval": "2",
        "voice_interval_seconds": "3",
        "voice_daily_cap_xp": "4",
        "voice_levelup_channel_id": "5",
    }

    mod = _reload_with_defaults(monkeypatch, fake_defaults)
    cfg = mod.XpConfig()

    assert cfg.enabled is False
    assert cfg.points_per_message == 10
    assert cfg.cooldown_seconds == 20
    assert cfg.bonus_percent == 30
    assert cfg.karuta_k_small_percent == 40
    assert cfg.voice_enabled is True
    assert cfg.voice_xp_per_interval == 2
    assert cfg.voice_interval_seconds == 3
    assert cfg.voice_daily_cap_xp == 4
    assert cfg.voice_levelup_channel_id == 5
