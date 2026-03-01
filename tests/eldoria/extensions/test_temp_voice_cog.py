from __future__ import annotations

import sys

import pytest

# ---------- Local stubs / shims (complements tests/conftest.py stubs) ----------
# ---------- Import module under test (adjust if needed) ----------
import eldoria.extensions.temp_voice as tv_mod  # noqa: E402
from eldoria.extensions.temp_voice import TempVoice, setup  # noqa: E402
from tests._fakes import (
    FakeBot,
    FakeCtx,
    FakeGuild,
    FakeMember,
    FakeTempVoiceService,
    FakeVoiceChannel,
    FakeVoiceState,
)


# ---------- Tests: voice events ----------
@pytest.mark.asyncio
async def test_voice_state_update_deletes_empty_temp_channel_and_removes_active_even_if_delete_fails():
    discord = sys.modules["discord"]
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)
    cog = TempVoice(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild)

    before_ch = FakeVoiceChannel(10)
    before_ch.members = []  # empty => delete
    before_ch._delete_raises = discord.Forbidden()  # still must call remove_active in finally

    svc._find_parent_of_active[(111, 10)] = 999  # channel 10 is active for parent 999

    before = FakeVoiceState(before_ch)
    after = FakeVoiceState(None)

    await cog.on_voice_state_update(member, before, after)

    assert ("remove_active", 111, 999, 10) in svc.calls
    assert before_ch.deleted is True


@pytest.mark.asyncio
async def test_voice_state_update_guard_if_after_is_already_temp():
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)
    cog = TempVoice(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild)

    after_ch = FakeVoiceChannel(20)
    # mark after as already active temp
    svc._find_parent_of_active[(111, 20)] = 999

    before = FakeVoiceState(None)
    after = FakeVoiceState(after_ch)

    await cog.on_voice_state_update(member, before, after)

    # Should return early: no get_parent, no create
    assert ("get_parent", 111, 20) not in svc.calls
    assert guild.created == []
    assert member.moved_to == []


@pytest.mark.asyncio
async def test_voice_state_update_creates_temp_channel_for_configured_parent_and_moves_user():
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)
    cog = TempVoice(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild, display_name="Faucon")

    parent = FakeVoiceChannel(30, category="MYCAT", bitrate=96)
    svc._parents[(111, 30)] = 7  # user_limit

    before = FakeVoiceState(None)
    after = FakeVoiceState(parent)

    await cog.on_voice_state_update(member, before, after)

    # created a voice channel with correct parameters
    assert len(guild.created) == 1
    created_kwargs = guild.created[0]["kwargs"]
    assert created_kwargs["name"] == "Salon de Faucon"
    assert created_kwargs["category"] == "MYCAT"
    assert created_kwargs["bitrate"] == 96
    assert created_kwargs["user_limit"] == 7
    # overwrites contains member -> PermissionOverwrite
    overwrites = created_kwargs["overwrites"]
    assert member in overwrites

    # add_active recorded BEFORE move_to
    created_channel = guild.created[0]["channel"]
    assert ("add_active", 111, 30, created_channel.id) in svc.calls
    assert member.moved_to == [created_channel]


@pytest.mark.asyncio
async def test_voice_state_update_does_nothing_if_not_parent():
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)
    cog = TempVoice(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild)

    after_ch = FakeVoiceChannel(40)
    # no parent config
    before = FakeVoiceState(None)
    after = FakeVoiceState(after_ch)

    await cog.on_voice_state_update(member, before, after)

    assert guild.created == []
    assert member.moved_to == []


# ---------- Tests: commands (refacto) ----------
# Le cog a été refactorisé : les commandes "init/remove/list" ont été remplacées par
# un panel (/tempvoice config) et un listing (/tempvoice list).


@pytest.mark.asyncio
async def test_tv_config_requires_guild():
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)
    cog = TempVoice(bot)
    ctx = FakeCtx(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.tv_config(ctx)


@pytest.mark.asyncio
async def test_tv_config_sends_panel(monkeypatch):
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)
    cog = TempVoice(bot)

    guild = FakeGuild(111)
    ctx = FakeCtx(guild=guild)

    monkeypatch.setattr(tv_mod, "TempVoiceHomeView", lambda **kw: ("VIEW", kw), raising=True)
    monkeypatch.setattr(tv_mod, "build_tempvoice_home_embed", lambda: ("EMBED", ["F"]), raising=True)

    await cog.tv_config(ctx)

    assert ctx.deferred is True
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "EMBED"
    assert sent["files"] == ["F"]
    assert sent["ephemeral"] is True
    # view est un tuple ("VIEW", kwargs)
    assert sent["view"][0] == "VIEW"
    assert sent["view"][1]["guild"].id == 111


@pytest.mark.asyncio
async def test_tv_list_requires_guild():
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)
    cog = TempVoice(bot)
    ctx = FakeCtx(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.tv_list(ctx)


@pytest.mark.asyncio
async def test_tv_list_uses_paginator(monkeypatch):
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)
    cog = TempVoice(bot)

    guild = FakeGuild(111)
    ctx = FakeCtx(guild=guild)

    svc._parents[(111, 123)] = 5

    created = {}

    def paginator_factory(items, embed_generator, identifiant_for_embed, bot):
        created["items"] = items
        created["embed_generator"] = embed_generator
        created["ident"] = identifiant_for_embed
        created["bot"] = bot

        async def create_embed(self):
            return ("EMBED", ["FILES"])

        return type("PaginatorStub", (), {"create_embed": create_embed})()

    monkeypatch.setattr(tv_mod, "Paginator", paginator_factory, raising=True)
    monkeypatch.setattr(tv_mod, "build_list_temp_voice_parents_embed", lambda *_a, **_k: "X", raising=True)

    await cog.tv_list(ctx)

    assert ("list_parents", 111) in svc.calls
    assert created["ident"] == 111
    assert created["bot"] is bot
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["embed"] == "EMBED"
    assert ctx.followup.sent[-1]["files"] == ["FILES"]
    assert hasattr(ctx.followup.sent[-1]["view"], "create_embed")


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    svc = FakeTempVoiceService()
    bot = FakeBot(svc)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], TempVoice)
