from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.welcome import embeds as M
from tests._fakes._profile_entities_fakes import FakeAvatar, FakeGuild


class FakeMember:
    def __init__(self, mention: str, avatar_url: str):
        self.mention = mention
        self.display_avatar = FakeAvatar(avatar_url)

class FakeWelcomeService:
    def __init__(self):
        self.calls: list[dict] = []
        self.ret = ("Titre", "Message de bienvenue", ["😀", "🔥"])

    def get_welcome_message(self, guild_id: int, *, user: str, server: str, recent_limit: int):
        self.calls.append(
            {"guild_id": guild_id, "user": user, "server": server, "recent_limit": recent_limit}
        )
        return self.ret

class FakeServices:
    def __init__(self, welcome: FakeWelcomeService):
        self.welcome = welcome

class FakeBot:
    def __init__(self, guild: FakeGuild, welcome: FakeWelcomeService):
        self._guild = guild
        self.services = FakeServices(welcome)
        self.get_guild_calls: list[int] = []

    def get_guild(self, guild_id: int):
        self.get_guild_calls.append(guild_id)
        return self._guild

@pytest.mark.asyncio
async def test_build_welcome_embed_builds_embed_and_returns_emojis(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1234)

    welcome = FakeWelcomeService()
    guild = FakeGuild("Eldoria")
    bot = FakeBot(guild=guild, welcome=welcome)

    member = FakeMember(mention="<@42>", avatar_url="https://cdn/avatar.png")

    embed, emojis = await M.build_welcome_embed(guild_id=999, member=member, bot=bot)

    assert bot.get_guild_calls == [999]

    # appel service welcome avec bons params
    assert welcome.calls == [
        {"guild_id": 999, "user": "<@42>", "server": "Eldoria", "recent_limit": 10}
    ]

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Titre"
    assert embed.colour == 1234
    assert embed.description == "\u200b\nMessage de bienvenue\n\u200b"

    assert embed.footer == {"text": "✨ Bienvenue parmi nous."}
    assert embed.thumbnail == {"url": "https://cdn/avatar.png"}

    assert emojis == ["😀", "🔥"]

@pytest.mark.asyncio
async def test_build_welcome_embed_supports_empty_emojis(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)

    welcome = FakeWelcomeService()
    welcome.ret = ("Hello", "Bienvenue", [])

    bot = FakeBot(guild=FakeGuild("Srv"), welcome=welcome)
    member = FakeMember(mention="<@1>", avatar_url="u")

    embed, emojis = await M.build_welcome_embed(guild_id=1, member=member, bot=bot)

    assert embed.title == "Hello"
    assert emojis == []