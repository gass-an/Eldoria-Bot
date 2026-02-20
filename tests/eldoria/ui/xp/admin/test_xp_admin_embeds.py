from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.xp.admin import embeds as M


# --------- helpers (compat stub) ----------
def _title(embed: discord.Embed) -> str:
    return getattr(embed, "title", None) or getattr(embed, "kwargs", getattr(embed, "kwargs", None)) or embed.kwargs.get("title")  # type: ignore[attr-defined]

def _desc(embed: discord.Embed) -> str:
    return getattr(embed, "description", None) or embed.kwargs.get("description", "")  # type: ignore[attr-defined]

def _colour(embed: discord.Embed):
    # some stubs use embed.colour; others keep it in kwargs["color"]
    return getattr(embed, "colour", None) or getattr(embed, "color", None) or embed.kwargs.get("color")  # type: ignore[attr-defined]


class FakeChannel(discord.abc.GuildChannel):  # type: ignore[misc]
    def __init__(self, channel_id: int, *, mention: str | None = None):
        self.id = channel_id
        self.mention = mention or f"<#{channel_id}>"


class FakeRole(discord.Role):  # type: ignore[misc]
    def __init__(self, role_id: int, *, mention: str | None = None):
        self.id = role_id
        self.mention = mention or f"<@&{role_id}>"


def test_bool_badge():
    assert M._bool_badge(True) == "✅ Activé"
    assert M._bool_badge(False) == "⛔ Désactivé"


def test_build_xp_admin_menu_embed_enabled_colour_and_decorate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 111)
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 222)

    called = {"decorate": 0, "files": 0}

    def fake_decorate(embed, t, b):
        called["decorate"] += 1
        return embed

    def fake_common_files(t, b):
        called["files"] += 1
        return ["FILES"]

    monkeypatch.setattr(M, "decorate", fake_decorate)
    monkeypatch.setattr(M, "common_files", fake_common_files)

    embed, files = M.build_xp_admin_menu_embed({"enabled": True})

    assert isinstance(embed, discord.Embed)
    assert _title(embed) == "⭐ Admin XP — Panneau"
    assert _colour(embed) == 111
    assert "**Système XP :** ✅ Activé" in _desc(embed)
    assert "• ⚙️ Paramètres" in _desc(embed)
    assert "• 🎙️ Vocal" in _desc(embed)
    assert "• 🏅 Niveaux & rôles" in _desc(embed)
    assert embed.footer == {"text": "Configure le système d'XP pour ton serveur."}

    assert files == ["FILES"]
    assert called["decorate"] == 1
    assert called["files"] == 1


def test_build_xp_admin_menu_embed_disabled_colour(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 111)
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 222)
    monkeypatch.setattr(M, "decorate", lambda e, *_a: e)
    monkeypatch.setattr(M, "common_files", lambda *_a: [])

    embed, _files = M.build_xp_admin_menu_embed({"enabled": False})

    assert _colour(embed) == 222
    assert "**Système XP :** ⛔ Désactivé" in _desc(embed)


def test_build_xp_admin_settings_embed_contains_cfg_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 999)
    monkeypatch.setattr(M, "decorate", lambda e, *_a: e)
    monkeypatch.setattr(M, "common_files", lambda *_a: ["FILES"])

    cfg = {
        "enabled": True,
        "points_per_message": 3,
        "cooldown_seconds": 10,
        "bonus_percent": 20,
        "karuta_k_small_percent": 30,
    }

    embed, files = M.build_xp_admin_settings_embed(cfg)

    assert _title(embed) == "⚙️ Admin XP — Paramètres (messages)"
    assert _colour(embed) == 999
    d = _desc(embed)

    assert "**Système XP :** ✅ Activé" in d
    assert "**XP / message :** `3`" in d
    assert "**Cooldown :** `10s`" in d
    assert "**Bonus tag :** `20%`" in d
    assert "**Karuta k<=10 :** `30%`" in d

    assert embed.footer == {"text": "Configure les paramètres liés aux messages pour le système d'XP."}
    assert files == ["FILES"]


def test_build_xp_admin_voice_embed_channel_placeholder_and_warning(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)
    monkeypatch.setattr(M, "decorate", lambda e, *_a: e)
    monkeypatch.setattr(M, "common_files", lambda *_a: [])

    cfg = {
        "enabled": True,
        "voice_enabled": True,
        "voice_interval_seconds": 180,
        "voice_xp_per_interval": 2,
        "voice_daily_cap_xp": 100,
    }

    # voice enabled + no channel => warning field
    embed, _ = M.build_xp_admin_voice_embed(cfg, channel=None)

    assert _title(embed) == "🎙️ Admin XP — Vocal"
    assert _colour(embed) == 123
    d = _desc(embed)
    assert "**Système XP :** ✅ Activé" in d
    assert "**XP Vocal :** ✅ Activé" in d
    assert "**Salon annonces :** *(aucun salon configuré)*" in d

    assert len(embed.fields) == 1
    assert embed.fields[0]["name"] == "⚠️ Salon d'annonces manquant"
    assert "aucun salon d'annonces" in embed.fields[0]["value"]
    assert embed.fields[0]["inline"] is False

    # channel present => no warning + mention shown
    ch = FakeChannel(55, mention="#annonces")
    embed2, _ = M.build_xp_admin_voice_embed(cfg, channel=ch)
    d2 = _desc(embed2)
    assert "#annonces" in d2
    assert "Salon annonces" in d2
    assert embed2.fields == []


def test_build_xp_admin_levels_embed_builds_lines_and_selection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 321)
    monkeypatch.setattr(M, "decorate", lambda e, *_a: e)
    monkeypatch.setattr(M, "common_files", lambda *_a: ["FILES"])

    levels = [
        (1, 0, 111),
        (2, 100, None),
        (3, 250, 333),
    ]
    selected_level = 2
    selected_role = FakeRole(999, mention="@Chosen")

    embed, files = M.build_xp_admin_levels_embed(
        levels_with_roles=levels,
        selected_level=selected_level,
        selected_role=selected_role,
    )

    assert _title(embed) == "🏅 Admin XP — Niveaux & rôles"
    assert _colour(embed) == 321
    d = _desc(embed)

    # cursor on selected level only
    assert "• **Niveau 1** : `0 XP` → <@&111>" in d
    assert "➡️ **Niveau 2** : `100 XP` → *(aucun rôle)*" in d
    assert "• **Niveau 3** : `250 XP` → <@&333>" in d

    assert "**Sélection :** Niveau `2` → rôle @Chosen" in d
    assert "Utilise le menu" in d

    assert embed.footer == {"text": "Configure les niveaux et rôles associés au système d'XP."}
    assert files == ["FILES"]