from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.xp.embeds import profile as M
from tests._fakes._profile_entities_fakes import FakeAvatar, FakeGuild
from tests._fakes.xp_ui import FakeBot


class FakeUser:
    def __init__(self, display_name: str, avatar_url: str | None):
        self.display_name = display_name
        self.display_avatar = FakeAvatar(avatar_url) if avatar_url is not None else None

@pytest.mark.asyncio
async def test_build_xp_profile_embed_next_level_branch_and_remaining(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["FILES"])

    bot = FakeBot(guild=FakeGuild("Eldoria"))
    user = FakeUser("Alice", "https://cdn/avatar.png")

    embed, files = await M.build_xp_profile_embed(
        guild_id=42,
        user=user,
        xp=80,
        level=3,
        level_label="Bronze",
        next_level_label="Silver",
        next_xp_required=100,
        bot=bot,
    )

    assert bot.get_guild_calls == [42]
    assert isinstance(embed, discord.Embed)
    assert embed.title == "📊 Ton profil XP"
    assert embed.colour == 123

    # Author
    assert embed.author == {"name": "Alice", "icon_url": "https://cdn/avatar.png"}

    # Fields (ordre exact attendu)
    assert embed.fields[0] == {"name": "Niveau actuel", "value": "**Bronze** (niveau 3)", "inline": True}
    assert embed.fields[1] == {"name": "XP total", "value": "**80 XP**", "inline": True}

    # Prochain niveau + remaining = 100-80 = 20
    assert embed.fields[2]["name"] == "Prochain niveau"
    assert "**Silver**" in embed.fields[2]["value"]
    assert "Seuil : **100 XP**" in embed.fields[2]["value"]
    assert "XP restante : **20 XP**" in embed.fields[2]["value"]
    assert embed.fields[2]["inline"] is False

    # Footer serveur
    assert embed.footer == {"text": "Serveur : Eldoria"}
    assert files == ["FILES"]

@pytest.mark.asyncio
async def test_build_xp_profile_embed_remaining_clamped_to_zero(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    bot = FakeBot(guild=FakeGuild("Srv"))
    user = FakeUser("Bob", "u")

    embed, _ = await M.build_xp_profile_embed(
        guild_id=1,
        user=user,
        xp=150,
        level=9,
        level_label="Gold",
        next_level_label="Diamond",
        next_xp_required=100,  # xp > required => remaining 0
        bot=bot,
    )

    assert "XP restante : **0 XP**" in embed.fields[2]["value"]

@pytest.mark.asyncio
async def test_build_xp_profile_embed_max_level_branch(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 7)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["F"])

    bot = FakeBot(guild=FakeGuild("Eldoria"))
    user = FakeUser("Alice", "u")

    embed, files = await M.build_xp_profile_embed(
        guild_id=42,
        user=user,
        xp=999,
        level=50,
        level_label="MAX",
        next_level_label=None,
        next_xp_required=None,  # max level
        bot=bot,
    )

    # 3 fields: niveau, xp total, progression
    assert len(embed.fields) == 3
    assert embed.fields[2] == {
        "name": "Progression",
        "value": "🏆 **Niveau maximum atteint !**",
        "inline": False,
    }
    assert files == ["F"]

@pytest.mark.asyncio
async def test_build_xp_profile_embed_user_without_avatar_sets_icon_url_none(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    bot = FakeBot(guild=FakeGuild("Srv"))
    user = FakeUser("NoAvatar", None)

    embed, _ = await M.build_xp_profile_embed(
        guild_id=1,
        user=user,
        xp=10,
        level=1,
        level_label="lvl1",
        next_level_label="lvl2",
        next_xp_required=20,
        bot=bot,
    )

    assert embed.author == {"name": "NoAvatar", "icon_url": None}

@pytest.mark.asyncio
async def test_build_xp_profile_embed_footer_fallback_when_guild_none(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    bot = FakeBot(guild=None)
    user = FakeUser("Alice", "u")

    embed, _ = await M.build_xp_profile_embed(
        guild_id=999,
        user=user,
        xp=10,
        level=1,
        level_label="lvl1",
        next_level_label="lvl2",
        next_xp_required=20,
        bot=bot,
    )

    assert embed.footer == {"text": "Serveur : 999"}