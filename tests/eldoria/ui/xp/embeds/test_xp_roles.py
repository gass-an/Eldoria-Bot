from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.xp.embeds import roles as M
from tests._fakes._discord_entities_fakes import FakeRole
from tests._fakes.xp_ui import FakeBot


class FakeGuild:
    def __init__(self, roles=None):
        self._roles = roles or {}
        self.get_role_calls: list[int | None] = []

    def get_role(self, role_id):
        self.get_role_calls.append(role_id)
        return self._roles.get(role_id)

@pytest.mark.asyncio
async def test_build_xp_roles_embed_no_configuration(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["FILES"])

    bot = FakeBot(guild=FakeGuild())

    embed, files = await M.build_xp_roles_embed([], guild_id=42, bot=bot)

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Rôles & Niveaux XP"
    assert "XP requis" in embed.description
    assert embed.colour == 123

    assert len(embed.fields) == 1
    assert embed.fields[0] == {
        "name": "Aucune configuration",
        "value": "Aucun niveau n'est configuré pour ce serveur.",
        "inline": False,
    }

    assert files == ["FILES"]
    assert bot.get_guild_calls == [42]

@pytest.mark.asyncio
async def test_build_xp_roles_embed_builds_lines_with_role_mentions_and_fallbacks(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    guild = FakeGuild(roles={100: FakeRole(100)})
    bot = FakeBot(guild=guild)

    levels_with_roles = [
        (1, 0, None),     # role_id None => fallback lvl1
        (2, 50, 100),     # role exists => mention
        (3, 100, 999),    # role missing => fallback lvl3
        (4, 150, 0),      # role_id falsy => fallback lvl4
    ]

    embed, files = await M.build_xp_roles_embed(levels_with_roles, guild_id=42, bot=bot)

    assert files == []
    assert len(embed.fields) == 1
    assert embed.fields[0]["name"] == "Niveaux"

    value = embed.fields[0]["value"].split("\n")
    assert value[0] == "**Niveau 1** — lvl1 — **0 XP**"
    assert value[1] == "**Niveau 2** — <@&100> — **50 XP**"
    assert value[2] == "**Niveau 3** — lvl3 — **100 XP**"
    assert value[3] == "**Niveau 4** — lvl4 — **150 XP**"

    # get_role called only for truthy role_id values (100, 999)
    assert guild.get_role_calls == [100, 999]
    assert bot.get_guild_calls == [42]

@pytest.mark.asyncio
async def test_build_xp_roles_embed_guild_none_falls_back_to_lvl(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    bot = FakeBot(guild=None)

    embed, _ = await M.build_xp_roles_embed([(2, 50, 100)], guild_id=42, bot=bot)

    assert embed.fields[0]["name"] == "Niveaux"
    assert embed.fields[0]["value"] == "**Niveau 2** — lvl2 — **50 XP**"

@pytest.mark.asyncio
async def test_build_xp_roles_embed_guild_id_zero_does_not_call_get_guild(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda e, t, b: e)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    bot = FakeBot(guild=FakeGuild(roles={100: FakeRole(100)}))

    embed, _ = await M.build_xp_roles_embed([(2, 50, 100)], guild_id=0, bot=bot)

    assert bot.get_guild_calls == []  # guild_id falsy => pas d'appel
    assert embed.fields[0]["value"] == "**Niveau 2** — lvl2 — **50 XP**"