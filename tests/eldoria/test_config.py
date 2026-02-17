from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_config_fresh(monkeypatch, tmp_name: str = "eldoria_config_under_test"):
    """Charge src/eldoria/config.py sous un nom unique pour isoler les effets d'import."""
    # Empêche la .env locale de polluer les tests (sinon load_dotenv remet des vars)
    import dotenv
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)

    sys.modules.pop(tmp_name, None)

    cfg_path = Path(__file__).resolve().parents[2] / "src" / "eldoria" / "config.py"
    spec = importlib.util.spec_from_file_location(tmp_name, cfg_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[tmp_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return mod


def test_env_helpers_required_and_optional_paths(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "x")
    monkeypatch.delenv("ADMIN_USER_ID", raising=False)
    monkeypatch.delenv("GUILD_FOR_SAVE", raising=False)
    monkeypatch.delenv("CHANNEL_FOR_SAVE", raising=False)

    mod = _load_config_fresh(monkeypatch, "cfg_a")

    with pytest.raises(RuntimeError, match="Missing required environment variable"):
        mod.env_str_required("NOPE")

    monkeypatch.delenv("MISSING_INT", raising=False)
    assert mod.env_int_optional("MISSING_INT") is None

    monkeypatch.setenv("BAD_INT", "abc")
    with pytest.raises(RuntimeError, match="must be an integer"):
        mod.env_int_optional("BAD_INT")


def test_config_import_raises_when_save_enabled_but_missing_vars(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "x")
    monkeypatch.setenv("ADMIN_USER_ID", "1")
    monkeypatch.delenv("GUILD_FOR_SAVE", raising=False)
    monkeypatch.delenv("CHANNEL_FOR_SAVE", raising=False)

    with pytest.raises(RuntimeError, match="fonctionnalité de sauvegarde"):
        _load_config_fresh(monkeypatch, "cfg_b")
