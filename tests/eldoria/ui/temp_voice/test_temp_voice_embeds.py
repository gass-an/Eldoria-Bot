from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.temp_voice import embeds as M


class FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.mention = f"<#{channel_id}>"


class FakeGuild:
    def __init__(self, channels: dict[int, FakeChannel] | None = None):
        self._channels = channels or {}

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class FakeBot:
    def __init__(self, guild=None):
        self._guild = guild
        self.get_guild_calls: list[int] = []

    def get_guild(self, gid: int):
        self.get_guild_calls.append(gid)
        return self._guild


@pytest.mark.asyncio
async def test_build_list_temp_voice_parents_embed_empty_items(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)

    deco = {"called": 0}
    def fake_decorate(embed, t, b):
        deco["called"] += 1
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["F1", "F2"])

    bot = FakeBot(guild=FakeGuild())

    embed, files = await M.build_list_temp_voice_parents_embed(
        items=[],
        page=0,
        total_pages=3,
        identifiant_for_embed=999,
        bot=bot,
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Salons pour la création de vocaux temporaires"
    assert "Liste des salons configurés" in embed.description
    assert embed.colour == 123
    assert embed.footer == {"text": "Page 1/3"}

    # cas vide => 1 field "Aucun salon"
    assert len(embed.fields) == 1
    assert embed.fields[0] == {
        "name": "Aucun salon",
        "value": "Aucun salon parent n'est configuré.",
        "inline": False,
    }

    # Pas besoin d'appeler bot.get_guild si items vide
    assert bot.get_guild_calls == []

    assert deco["called"] == 1
    assert files == ["F1", "F2"]


@pytest.mark.asyncio
async def test_build_list_temp_voice_parents_embed_guild_none_all_missing(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda embed, t, b: embed)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["FILES"])

    bot = FakeBot(guild=None)

    items = [(111, 2), (222, 5)]
    embed, files = await M.build_list_temp_voice_parents_embed(
        items=items,
        page=1,
        total_pages=2,
        identifiant_for_embed=42,
        bot=bot,
    )

    assert bot.get_guild_calls == [42]
    assert embed.footer == {"text": "Page 2/2"}
    assert files == ["FILES"]

    assert len(embed.fields) == 1
    assert embed.fields[0]["name"] == "Salons configurés"
    v = embed.fields[0]["value"]

    assert "⚠️ Salon introuvable (ID `111`) — **limite**: `2`" in v
    assert "⚠️ Salon introuvable (ID `222`) — **limite**: `5`" in v


@pytest.mark.asyncio
async def test_build_list_temp_voice_parents_embed_mixed_found_and_missing(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 9)
    monkeypatch.setattr(M, "decorate", lambda embed, t, b: embed)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    guild = FakeGuild(channels={111: FakeChannel(111)})
    bot = FakeBot(guild=guild)

    items = [(111, 2), (222, 5)]
    embed, files = await M.build_list_temp_voice_parents_embed(
        items=items,
        page=0,
        total_pages=1,
        identifiant_for_embed=999,
        bot=bot,
    )

    assert bot.get_guild_calls == [999]
    assert embed.footer == {"text": "Page 1/1"}
    assert files == []

    assert len(embed.fields) == 1
    assert embed.fields[0]["name"] == "Salons configurés"

    lines = embed.fields[0]["value"].split("\n")
    assert lines[0] == "🔊 <#111> — **limite**: `2`"
    assert lines[1] == "⚠️ Salon introuvable (ID `222`) — **limite**: `5`"
