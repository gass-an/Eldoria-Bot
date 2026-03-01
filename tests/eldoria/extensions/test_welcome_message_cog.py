from __future__ import annotations

import discord  # type: ignore
import pytest

import eldoria.extensions.welcome_message as wm_mod
from eldoria.extensions.welcome_message import WelcomeMessage, setup
from tests._fakes import (
    FakeBot,
    FakeCtx,
    FakeGuild,
    FakeMember,
    FakeMessage,
    FakeServices,
    FakeTextChannel,
    FakeWelcomeService,
)


# ---------- Tests: on_member_join ----------
@pytest.mark.asyncio
async def test_on_member_join_noop_when_disabled():
    welcome = FakeWelcomeService()
    bot = FakeBot(services=FakeServices(welcome=welcome))
    cog = WelcomeMessage(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild=guild)
    welcome.set_config(111, {"enabled": False, "channel_id": 123})
    welcome.calls.clear()

    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_noop_when_no_channel_id():
    welcome = FakeWelcomeService()
    bot = FakeBot(services=FakeServices(welcome=welcome))
    cog = WelcomeMessage(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild=guild)
    welcome.set_config(111, {"enabled": True, "channel_id": 0})
    welcome.calls.clear()

    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_ignores_missing_or_wrong_channel_type():
    welcome = FakeWelcomeService()
    bot = FakeBot(services=FakeServices(welcome=welcome))
    cog = WelcomeMessage(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild=guild)
    welcome.set_config(111, {"enabled": True, "channel_id": 555})
    welcome.calls.clear()

    # missing
    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]

    # wrong type
    welcome.calls.clear()
    guild.add_channel(object())
    # force a wrong channel instance in the mapping
    guild._channels[555] = object()  # type: ignore[attr-defined]
    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_sends_message_and_reactions(monkeypatch):
    welcome = FakeWelcomeService()
    bot = FakeBot(services=FakeServices(welcome=welcome))
    cog = WelcomeMessage(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild=guild)

    msg = FakeMessage(message_id=777)
    ch = FakeTextChannel(555, send_returns=msg)
    guild.add_channel(ch)

    welcome.set_config(111, {"enabled": True, "channel_id": 555})

    async def fake_build_welcome_embed(*, guild_id, member, bot):
        assert guild_id == 111
        return ("EMBED", ["🔥", "✅"])

    monkeypatch.setattr(wm_mod, "build_welcome_embed", fake_build_welcome_embed, raising=True)

    await cog.on_member_join(member)

    assert ch.sent[-1]["content"] == f"||{member.mention}||"
    assert ch.sent[-1]["embed"] == "EMBED"
    assert msg.reactions_added == ["🔥", "✅"]


@pytest.mark.asyncio
async def test_on_member_join_reaction_failure_does_not_crash(monkeypatch):
    welcome = FakeWelcomeService()
    bot = FakeBot(services=FakeServices(welcome=welcome))
    cog = WelcomeMessage(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild=guild)

    msg = FakeMessage(message_id=777)
    msg._raise_add_reaction = discord.Forbidden()  # type: ignore[call-arg]

    ch = FakeTextChannel(555, send_returns=msg)
    guild.add_channel(ch)
    welcome.set_config(111, {"enabled": True, "channel_id": 555})

    async def fake_build_welcome_embed(*, guild_id, member, bot):
        return ("EMBED", ["🔥", "✅"])

    monkeypatch.setattr(wm_mod, "build_welcome_embed", fake_build_welcome_embed, raising=True)

    await cog.on_member_join(member)
    assert len(ch.sent) == 1


@pytest.mark.asyncio
async def test_on_member_join_is_fully_safe(monkeypatch):
    welcome = FakeWelcomeService()
    bot = FakeBot(services=FakeServices(welcome=welcome))
    cog = WelcomeMessage(bot)

    guild = FakeGuild(111)
    member = FakeMember(1, guild=guild)
    welcome.set_config(111, {"enabled": True, "channel_id": 555})

    def boom(_guild_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(welcome, "get_config", boom, raising=True)
    await cog.on_member_join(member)  # should not raise


# ---------- Tests: /welcome (panel) ----------
@pytest.mark.asyncio
async def test_welcome_panel_defers_and_sends(monkeypatch):
    welcome = FakeWelcomeService()
    bot = FakeBot(services=FakeServices(welcome=welcome))
    cog = WelcomeMessage(bot)

    guild = FakeGuild(111)
    author = FakeMember(456, guild=guild)
    ctx = FakeCtx(guild=guild, author=author)

    def fake_require_guild_ctx(passed_ctx):
        assert passed_ctx is ctx
        return (guild, None)

    def view_factory(*, welcome_service, author_id, guild):
        assert welcome_service is welcome
        assert author_id == 456
        assert guild is guild

        def current_embed(self):
            return ("PANEL_EMBED", ["FILE1"])

        return type("WelcomePanelViewStub", (), {"current_embed": current_embed})()

    monkeypatch.setattr(wm_mod, "require_guild_ctx", fake_require_guild_ctx, raising=True)
    monkeypatch.setattr(wm_mod, "WelcomePanelView", view_factory, raising=True)

    await cog.welcome_panel(ctx)

    assert ctx.deferred is True
    assert ctx.defer_ephemeral is True

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "PANEL_EMBED"
    assert sent["files"] == ["FILE1"]
    assert sent["ephemeral"] is True
    assert hasattr(sent["view"], "current_embed")


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    welcome = FakeWelcomeService()
    bot = FakeBot(services=FakeServices(welcome=welcome))

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], WelcomeMessage)
