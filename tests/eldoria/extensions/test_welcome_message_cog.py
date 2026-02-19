from __future__ import annotations

import discord  # type: ignore
import pytest

import eldoria.extensions.welcome_message as wm_mod
from eldoria.extensions.welcome_message import WelcomeMessage, setup


# ---------- Fakes ----------
class _FakeMessage:
    def __init__(self, message_id: int = 42):
        self.id = message_id
        self.reactions: list[str] = []
        self._raise_add_reaction: Exception | None = None

    async def add_reaction(self, emoji: str):
        if self._raise_add_reaction:
            raise self._raise_add_reaction
        self.reactions.append(emoji)


class _BaseChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.sent: list[dict] = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)
        return _FakeMessage()


class _FakeTextChannel(_BaseChannel, discord.TextChannel):  # type: ignore[misc]
    def __init__(self, channel_id: int):
        super().__init__(channel_id)
        self.mention = f"<#{channel_id}>"


class _OtherChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id


class _FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id
        self._channels: dict[int, object] = {}

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class _FakeMember:
    def __init__(self, member_id: int, guild: _FakeGuild):
        self.id = member_id
        self.guild = guild
        self.mention = f"<@{member_id}>"


class _FakeFollowup:
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)


class _FakeAuthor:
    def __init__(self, user_id: int):
        self.id = user_id


class _FakeCtx:
    def __init__(self, *, guild, author_id: int = 123):
        self.guild = guild
        self.author = _FakeAuthor(author_id)
        self.followup = _FakeFollowup()
        self.deferred = False
        self.defer_ephemeral: bool | None = None

    async def defer(self, ephemeral: bool = False):
        self.deferred = True
        self.defer_ephemeral = ephemeral


class _FakeWelcomeService:
    def __init__(self):
        self.calls: list[tuple] = []
        self._config = {"enabled": False, "channel_id": 0}

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return dict(self._config)


class _FakeServices:
    def __init__(self, welcome: _FakeWelcomeService):
        self.welcome = welcome


class _FakeBotUser:
    def __init__(self, user_id: int):
        self.id = user_id


class _FakeBot:
    def __init__(self, welcome: _FakeWelcomeService):
        self.services = _FakeServices(welcome)
        self.user = _FakeBotUser(999)


# ---------- Tests: on_member_join ----------
@pytest.mark.asyncio
async def test_on_member_join_noop_when_disabled():
    welcome = _FakeWelcomeService()
    cog = WelcomeMessage(_FakeBot(welcome))

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    welcome._config = {"enabled": False, "channel_id": 123}

    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_noop_when_no_channel_id():
    welcome = _FakeWelcomeService()
    cog = WelcomeMessage(_FakeBot(welcome))

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    welcome._config = {"enabled": True, "channel_id": 0}

    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_ignores_missing_or_wrong_channel_type():
    welcome = _FakeWelcomeService()
    cog = WelcomeMessage(_FakeBot(welcome))

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    welcome._config = {"enabled": True, "channel_id": 555}

    # missing
    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]

    # wrong type
    welcome.calls.clear()
    guild._channels[555] = _OtherChannel(555)
    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_sends_message_and_reactions(monkeypatch):
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    ch = _FakeTextChannel(555)
    guild._channels[555] = ch

    welcome._config = {"enabled": True, "channel_id": 555}

    async def fake_build_welcome_embed(*, guild_id, member, bot):
        assert guild_id == 111
        return ("EMBED", ["🔥", "✅"])

    monkeypatch.setattr(wm_mod, "build_welcome_embed", fake_build_welcome_embed, raising=True)

    await cog.on_member_join(member)

    assert ch.sent[-1]["content"] == f"||{member.mention}||"
    assert ch.sent[-1]["embed"] == "EMBED"


@pytest.mark.asyncio
async def test_on_member_join_reaction_failure_does_not_crash(monkeypatch):
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    ch = _FakeTextChannel(555)
    guild._channels[555] = ch
    welcome._config = {"enabled": True, "channel_id": 555}

    async def fake_build_welcome_embed(*, guild_id, member, bot):
        return ("EMBED", ["🔥", "✅"])

    monkeypatch.setattr(wm_mod, "build_welcome_embed", fake_build_welcome_embed, raising=True)

    msg = _FakeMessage(message_id=777)
    msg._raise_add_reaction = discord.Forbidden()  # type: ignore[call-arg]

    async def fake_send(**kwargs):
        ch.sent.append(kwargs)
        return msg

    ch.send = fake_send  # type: ignore[assignment]

    await cog.on_member_join(member)
    assert len(ch.sent) == 1


@pytest.mark.asyncio
async def test_on_member_join_is_fully_safe(monkeypatch):
    welcome = _FakeWelcomeService()
    cog = WelcomeMessage(_FakeBot(welcome))

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)
    welcome._config = {"enabled": True, "channel_id": 555}

    def boom(_guild_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(welcome, "get_config", boom, raising=True)
    await cog.on_member_join(member)  # should not raise


# ---------- Tests: /welcome (panel) ----------
@pytest.mark.asyncio
async def test_welcome_panel_defers_and_sends(monkeypatch):
    welcome = _FakeWelcomeService()
    cog = WelcomeMessage(_FakeBot(welcome))

    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild, author_id=456)

    def fake_require_guild_ctx(passed_ctx):
        assert passed_ctx is ctx
        return (guild, None)

    class _FakeView:
        def __init__(self, *, welcome_service, author_id, guild):
            assert welcome_service is welcome
            assert author_id == 456
            assert guild is guild

        def current_embed(self):
            return ("PANEL_EMBED", ["FILE1"])

    monkeypatch.setattr(wm_mod, "require_guild_ctx", fake_require_guild_ctx, raising=True)
    monkeypatch.setattr(wm_mod, "WelcomePanelView", _FakeView, raising=True)

    await cog.welcome_panel(ctx)

    assert ctx.deferred is True
    assert ctx.defer_ephemeral is True

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "PANEL_EMBED"
    assert sent["files"] == ["FILE1"]
    assert sent["ephemeral"] is True
    assert isinstance(sent["view"], _FakeView)


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], WelcomeMessage)