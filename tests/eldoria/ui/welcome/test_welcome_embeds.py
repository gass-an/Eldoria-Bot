from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.welcome import embeds as M
from tests._fakes import FakeBot, FakeGuild, FakeMember, FakeServices, FakeWelcomeService


@pytest.mark.asyncio
async def test_build_welcome_embed_builds_embed_and_returns_emojis(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1234)

    welcome = FakeWelcomeService()
    guild = FakeGuild(name="Eldoria")
    bot = FakeBot(guild=guild, services=FakeServices(welcome=welcome))

    member = FakeMember(42, mention="<@42>", avatar_url="https://cdn/avatar.png")

    embed, emojis = await M.build_welcome_embed(guild_id=999, member=member, bot=bot)

    assert bot.get_guild_calls == [999]

    # appel service welcome avec bons params
    assert welcome.calls == [("get_welcome_message", 999, "<@42>", "Eldoria", 10)]

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
    welcome.set_welcome_message_result(("Hello", "Bienvenue", []))

    bot = FakeBot(guild=FakeGuild(name="Srv"), services=FakeServices(welcome=welcome))
    member = FakeMember(1, mention="<@1>", avatar_url="u")

    embed, emojis = await M.build_welcome_embed(guild_id=1, member=member, bot=bot)

    assert embed.title == "Hello"
    assert emojis == []