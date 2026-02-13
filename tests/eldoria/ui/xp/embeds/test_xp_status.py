from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.xp.embeds import status as M


class FakeGuild:
    def __init__(self, name: str):
        self.name = name


class FakeBot:
    def __init__(self, guild):
        self._guild = guild
        self.get_guild_calls: list[int] = []

    def get_guild(self, gid: int):
        self.get_guild_calls.append(gid)
        return self._guild


@pytest.mark.asyncio
async def test_build_xp_status_embed_disabled_branch(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)

    decorated = {"called": False}
    def fake_decorate(embed, t, b):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["FILES"])

    bot = FakeBot(guild=FakeGuild("Srv"))
    cfg = {"enabled": False}

    embed, files = await M.build_xp_status_embed(cfg, guild_id=42, bot=bot)

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Statut du système XP"
    assert embed.colour == 123

    # 2 fields: État + Information
    assert len(embed.fields) == 2
    assert embed.fields[0] == {"name": "État", "value": "⛔ Désactivé", "inline": True}
    assert embed.fields[1]["name"] == "Information"
    assert "/xp_enable" in embed.fields[1]["value"]
    assert embed.fields[1]["inline"] is False

    assert embed.footer == {"text": "Serveur : Srv"}
    assert decorated["called"] is True
    assert files == ["FILES"]


@pytest.mark.asyncio
async def test_build_xp_status_embed_enabled_voice_disabled(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    bot = FakeBot(guild=FakeGuild("Srv"))
    cfg = {
        "enabled": True,
        "points_per_message": 9,
        "cooldown_seconds": 12,
        "bonus_percent": 7,
        "karuta_k_small_percent": 30,
        "voice_enabled": False,
    }

    embed, _ = await M.build_xp_status_embed(cfg, guild_id=1, bot=bot)

    # Champs attendus (XP system enabled)
    # État, XP/message, Cooldown, Bonus, Malus, XP Vocal
    assert [f["name"] for f in embed.fields] == [
        "État",
        "XP / message",
        "Cooldown",
        "Bonus Server Tag",
        "Malus Karuta (k<=10)",
        "XP Vocal",
    ]

    assert embed.fields[0]["value"] == "✅ Activé"
    assert embed.fields[1]["value"] == "9"
    assert embed.fields[2]["value"] == "12 secondes"
    assert embed.fields[3]["value"] == "+7%"
    assert embed.fields[4]["value"] == "30%"
    assert embed.fields[5]["value"] == "⛔ Désactivé"

    # pas de champs "Gain vocal" / "Cap vocal" si voice_disabled
    assert all(f["name"] not in ("Gain vocal", "Cap vocal") for f in embed.fields)


@pytest.mark.asyncio
async def test_build_xp_status_embed_enabled_voice_enabled_with_cap_hours(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["F"])

    bot = FakeBot(guild=None)  # footer fallback guild_id
    cfg = {
        "enabled": True,
        # on teste aussi defaults
        # points_per_message default 8
        # cooldown_seconds default 90
        # bonus_percent default 20
        # karuta_k_small_percent default 30
        "voice_enabled": True,
        "voice_interval_seconds": 180,  # 3 min
        "voice_xp_per_interval": 2,
        "voice_daily_cap_xp": 100,
    }

    embed, files = await M.build_xp_status_embed(cfg, guild_id=999, bot=bot)

    assert files == ["F"]

    # Vérif defaults dans les fields
    # champ XP/message = "8"
    xp_msg = next(f for f in embed.fields if f["name"] == "XP / message")
    assert xp_msg["value"] == "8"

    cooldown = next(f for f in embed.fields if f["name"] == "Cooldown")
    assert cooldown["value"] == "90 secondes"

    bonus = next(f for f in embed.fields if f["name"] == "Bonus Server Tag")
    assert bonus["value"] == "+20%"

    malus = next(f for f in embed.fields if f["name"] == "Malus Karuta (k<=10)")
    assert malus["value"] == "30%"

    # Vocal
    voice = next(f for f in embed.fields if f["name"] == "XP Vocal")
    assert voice["value"] == "✅ Activé"

    gain = next(f for f in embed.fields if f["name"] == "Gain vocal")
    assert gain["value"] == "2 XP / 3min"

    cap = next(f for f in embed.fields if f["name"] == "Cap vocal")
    # cap_seconds = (cap_xp*interval)/per_int = (100*180)/2 = 9000s = 2.5h
    assert cap["value"] == "100 XP/jour (2.5h)"

    # Footer fallback
    assert embed.footer == {"text": "Serveur : 999"}


@pytest.mark.asyncio
async def test_build_xp_status_embed_voice_enabled_cap_without_hours_when_per_int_zero(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    bot = FakeBot(guild=FakeGuild("Srv"))
    cfg = {
        "enabled": True,
        "voice_enabled": True,
        "voice_interval_seconds": 180,
        "voice_xp_per_interval": 0,   # force else branch
        "voice_daily_cap_xp": 100,
    }

    embed, _ = await M.build_xp_status_embed(cfg, guild_id=1, bot=bot)

    gain = next(f for f in embed.fields if f["name"] == "Gain vocal")
    assert gain["value"] == "0 XP / 3min"

    cap = next(f for f in embed.fields if f["name"] == "Cap vocal")
    assert cap["value"] == "100 XP/jour"


@pytest.mark.asyncio
async def test_build_xp_status_embed_minutes_min_1(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    bot = FakeBot(guild=FakeGuild("Srv"))
    cfg = {
        "enabled": True,
        "voice_enabled": True,
        "voice_interval_seconds": 1,   # //60 = 0 -> clamp to 1
        "voice_xp_per_interval": 1,
        "voice_daily_cap_xp": 10,
    }

    embed, _ = await M.build_xp_status_embed(cfg, guild_id=1, bot=bot)

    gain = next(f for f in embed.fields if f["name"] == "Gain vocal")
    assert gain["value"] == "1 XP / 1min"


@pytest.mark.asyncio
async def test_build_xp_disable_embed_matches_disabled_layout(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 55)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["FILES"])

    bot = FakeBot(guild=FakeGuild("Srv"))

    embed, files = await M.build_xp_disable_embed(guild_id=42, bot=bot)

    assert embed.title == "Statut du système XP"
    assert embed.colour == 55
    assert len(embed.fields) == 2
    assert embed.fields[0]["value"] == "⛔ Désactivé"
    assert "/xp_enable" in embed.fields[1]["value"]
    assert embed.footer == {"text": "Serveur : Srv"}
    assert files == ["FILES"]
