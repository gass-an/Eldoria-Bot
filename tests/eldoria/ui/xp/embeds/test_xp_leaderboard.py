from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.xp.embeds import leaderboard as M


class FakeMember:
    def __init__(self, uid: int, name: str):
        self.id = uid
        self.display_name = name


class FakeRole:
    def __init__(self, rid: int):
        self.id = rid
        self.mention = f"<@&{rid}>"


class FakeGuild:
    def __init__(self, *, members=None, roles=None):
        self._members = members or {}
        self._roles = roles or {}
        self.get_role_calls: list[int | None] = []
        self.get_member_calls: list[int] = []

    def get_member(self, user_id: int):
        self.get_member_calls.append(user_id)
        return self._members.get(user_id)

    def get_role(self, role_id):
        self.get_role_calls.append(role_id)
        return self._roles.get(role_id)


class FakeBot:
    def __init__(self, guild):
        self._guild = guild
        self.get_guild_calls: list[int] = []

    def get_guild(self, gid: int):
        self.get_guild_calls.append(gid)
        return self._guild


@pytest.mark.asyncio
async def test_build_list_xp_embed_empty_items(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)

    monkeypatch.setattr(M, "decorate", lambda embed, t, b: embed)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["FILES"])

    # role ids should not matter here
    monkeypatch.setattr(M, "get_xp_role_ids", lambda guild_id: {1: 111})

    bot = FakeBot(guild=FakeGuild())
    embed, files = await M.build_list_xp_embed(
        items=[],
        current_page=0,
        total_pages=3,
        guild_id=42,
        bot=bot,
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Classement XP"
    assert embed.colour == 123
    assert files == ["FILES"]

    assert len(embed.fields) == 1
    assert embed.fields[0] == {
        "name": "Aucun membre",
        "value": "Personne n'a encore gagné d'XP.",
        "inline": False,
    }

    assert embed.footer == {"text": "Page 1/3"}


@pytest.mark.asyncio
async def test_build_list_xp_embed_tuple3_uses_role_mention_when_available(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)

    deco = {"called": False}
    def fake_decorate(embed, t, b):
        deco["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    # DB mapping level -> role_id
    monkeypatch.setattr(M, "get_xp_role_ids", lambda guild_id: {5: 500})

    guild = FakeGuild(
        members={10: FakeMember(10, "Alice")},
        roles={500: FakeRole(500)},
    )
    bot = FakeBot(guild=guild)

    items = [(10, 1234, 5)]
    embed, files = await M.build_list_xp_embed(items, current_page=0, total_pages=1, guild_id=42, bot=bot)

    assert files == []
    assert deco["called"] is True

    assert len(embed.fields) == 1
    assert embed.fields[0]["name"] == "Membres"
    assert embed.fields[0]["value"] == "**1.** Alice — <@&500> — **1234 XP**"
    assert embed.footer == {"text": "Page 1/1"}

    # get_role called for role_id 500
    assert guild.get_role_calls == [500]
    assert guild.get_member_calls == [10]


@pytest.mark.asyncio
async def test_build_list_xp_embed_tuple3_fallback_lvl_when_role_missing(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    # role id exists in mapping but guild.get_role returns None
    monkeypatch.setattr(M, "get_xp_role_ids", lambda guild_id: {5: 999})

    guild = FakeGuild(members={10: FakeMember(10, "Alice")}, roles={})
    bot = FakeBot(guild=guild)

    items = [(10, 50, 5)]
    embed, _ = await M.build_list_xp_embed(items, current_page=0, total_pages=1, guild_id=42, bot=bot)

    assert embed.fields[0]["value"] == "**1.** Alice — lvl5 — **50 XP**"


@pytest.mark.asyncio
async def test_build_list_xp_embed_tuple4_uses_precomputed_label_and_handles_missing_member(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["F"])

    # Même si DB renvoie des ids, on ne doit pas être obligé de get_role pour tuple4
    monkeypatch.setattr(M, "get_xp_role_ids", lambda guild_id: {1: 111})

    guild = FakeGuild(members={}, roles={111: FakeRole(111)})
    bot = FakeBot(guild=guild)

    items = [(999, 10, 1, "CUSTOM_LABEL")]
    embed, files = await M.build_list_xp_embed(items, current_page=0, total_pages=1, guild_id=42, bot=bot)

    assert files == ["F"]
    assert embed.fields[0]["value"] == "**1.** ID 999 — CUSTOM_LABEL — **10 XP**"

    # Pas besoin de get_role pour construire le label dans tuple4
    assert guild.get_role_calls == []
    assert guild.get_member_calls == [999]


@pytest.mark.asyncio
async def test_build_list_xp_embed_rank_starts_at_page_offset(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])
    monkeypatch.setattr(M, "get_xp_role_ids", lambda guild_id: {})

    guild = FakeGuild(members={1: FakeMember(1, "A"), 2: FakeMember(2, "B")})
    bot = FakeBot(guild=guild)

    items = [(1, 1, 1), (2, 2, 2)]
    # current_page=2 => rank_start = 2*10+1 = 21
    embed, _ = await M.build_list_xp_embed(items, current_page=2, total_pages=10, guild_id=42, bot=bot)

    v = embed.fields[0]["value"].split("\n")
    assert v[0].startswith("**21.**")
    assert v[1].startswith("**22.**")
    assert embed.footer == {"text": "Page 3/10"}


@pytest.mark.asyncio
async def test_build_list_xp_embed_when_guild_none_uses_id_fallback(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])
    monkeypatch.setattr(M, "get_xp_role_ids", lambda guild_id: {1: 111})

    bot = FakeBot(guild=None)

    items = [(1, 100, 3)]
    embed, _ = await M.build_list_xp_embed(items, current_page=0, total_pages=1, guild_id=42, bot=bot)

    # guild None => member None => "ID 1", label fallback lvl3
    assert embed.fields[0]["value"] == "**1.** ID 1 — lvl3 — **100 XP**"
