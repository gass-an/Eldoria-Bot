# tests/eldoria/extensions/test_welcome_message_cog.py
from __future__ import annotations

import sys
import types

import pytest


# ---------- Local stubs / shims (complements tests/conftest.py stubs) ----------
def _ensure_discord_stubs() -> None:
    """
    Ensure minimal discord.py surface used by this cog exists at import-time.
    The source does not use `from __future__ import annotations`, so typing
    annotations are evaluated at import time.
    """
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    # Exceptions
    for exc_name in ("Forbidden", "HTTPException", "NotFound"):
        if not hasattr(discord, exc_name):
            setattr(discord, exc_name, type(exc_name, (Exception,), {}))

    # Types used
    if not hasattr(discord, "ApplicationContext"):
        class ApplicationContext:  # pragma: no cover
            pass
        discord.ApplicationContext = ApplicationContext

    if not hasattr(discord, "Member"):
        class Member:  # pragma: no cover
            pass
        discord.Member = Member

    if not hasattr(discord, "TextChannel"):
        class TextChannel:  # pragma: no cover
            pass
        discord.TextChannel = TextChannel

    if not hasattr(discord, "Thread"):
        class Thread:  # pragma: no cover
            pass
        discord.Thread = Thread

    if not hasattr(discord, "AllowedMentions"):
        class AllowedMentions:  # pragma: no cover
            @staticmethod
            def none():
                return "ALLOWED_MENTIONS_NONE"
        discord.AllowedMentions = AllowedMentions

    # Decorators
    if not hasattr(discord, "option"):
        def option(*_a, **_k):  # pragma: no cover
            def deco(fn):
                return fn
            return deco
        discord.option = option

    if not hasattr(discord, "default_permissions"):
        def default_permissions(**_k):  # pragma: no cover
            def deco(fn):
                return fn
            return deco
        discord.default_permissions = default_permissions

    # discord.ext.commands
    if "discord.ext" not in sys.modules:
        sys.modules["discord.ext"] = types.ModuleType("discord.ext")
    if "discord.ext.commands" not in sys.modules:
        sys.modules["discord.ext.commands"] = types.ModuleType("discord.ext.commands")
    commands = sys.modules["discord.ext.commands"]

    if not hasattr(commands, "Cog"):
        class Cog:  # pragma: no cover
            @classmethod
            def listener(cls, *_a, **_k):
                def deco(fn):
                    return fn
                return deco
        commands.Cog = Cog

    if not hasattr(commands, "slash_command"):
        def slash_command(*_a, **_k):  # pragma: no cover
            def deco(fn):
                return fn
            return deco
        commands.slash_command = slash_command

    if not hasattr(commands, "has_permissions"):
        def has_permissions(**_k):  # pragma: no cover
            def deco(fn):
                return fn
            return deco
        commands.has_permissions = has_permissions


_ensure_discord_stubs()

# ---------- Import module under test (adjust if needed) ----------
import eldoria.extensions.welcome_message as wm_mod  # noqa: E402
from eldoria.extensions.welcome_message import WelcomeMessage, setup  # noqa: E402


# ---------- Fakes ----------
class _FakeMessage:
    def __init__(self):
        self.reactions = []
        self._raise_add_reaction = None

    async def add_reaction(self, emoji: str):
        if self._raise_add_reaction:
            raise self._raise_add_reaction
        self.reactions.append(emoji)


class _BaseChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)
        return _FakeMessage()


discord = sys.modules["discord"]

class _FakeTextChannel(_BaseChannel, discord.TextChannel):
    def __init__(self, channel_id: int, mention: str | None = None):
        super().__init__(channel_id)
        self.mention = mention or f"<#{channel_id}>"

class _FakeThread(_BaseChannel, discord.Thread):
    pass


class _OtherChannel:
    """Not TextChannel/Thread -> should be ignored."""
    def __init__(self, channel_id: int):
        self.id = channel_id


class _FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id
        self._channels = {}

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class _FakeMember:
    def __init__(self, member_id: int, guild: _FakeGuild):
        self.id = member_id
        self.guild = guild
        self.mention = f"<@{member_id}>"


class _FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)


class _FakeCtx:
    def __init__(self, guild=None):
        self.guild = guild
        self.followup = _FakeFollowup()
        self.deferred = False
        self.responded = []

    async def defer(self, ephemeral: bool = False):
        self.deferred = True
        self.defer_ephemeral = ephemeral

    async def respond(self, content: str, ephemeral: bool = False):
        self.responded.append({"content": content, "ephemeral": ephemeral})


class _FakeWelcomeService:
    def __init__(self):
        self.calls = []
        self._config = {"enabled": False, "channel_id": 0}
        self._channel_id = 0

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return dict(self._config)

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))

    def set_config(self, guild_id: int, **kwargs):
        self.calls.append(("set_config", guild_id, kwargs))

    def get_channel_id(self, guild_id: int):
        self.calls.append(("get_channel_id", guild_id))
        return self._channel_id

    def set_enabled(self, guild_id: int, enabled: bool):
        self.calls.append(("set_enabled", guild_id, enabled))


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
async def test_on_member_join_noop_when_disabled(monkeypatch):
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    welcome._config = {"enabled": False, "channel_id": 123}

    await cog.on_member_join(member)

    # no channel send
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_noop_when_no_channel_id():
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    welcome._config = {"enabled": True, "channel_id": 0}

    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_noop_when_channel_missing_or_wrong_type(monkeypatch):
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    # Channel missing
    welcome._config = {"enabled": True, "channel_id": 555}
    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]

    # Wrong type
    welcome.calls.clear()
    guild._channels[555] = _OtherChannel(555)
    await cog.on_member_join(member)
    assert welcome.calls == [("get_config", 111)]


@pytest.mark.asyncio
async def test_on_member_join_sends_message_and_adds_reactions(monkeypatch):
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
async def test_on_member_join_ignores_reaction_failures(monkeypatch):
    discord = sys.modules["discord"]
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

    # Make first reaction fail
    msg = _FakeMessage()
    msg._raise_add_reaction = discord.Forbidden()
    async def fake_send(**kwargs):
        ch.sent.append(kwargs)
        return msg
    ch.send = fake_send  # type: ignore[assignment]

    await cog.on_member_join(member)
    # even if reactions fail, it should not crash; send happened
    assert len(ch.sent) == 1


@pytest.mark.asyncio
async def test_on_member_join_is_fully_safe_on_any_exception(monkeypatch):
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    welcome._config = {"enabled": True, "channel_id": 555}

    def boom(_guild_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(welcome, "get_config", boom, raising=True)

    # Should not raise
    await cog.on_member_join(member)


# ---------- Tests: /welcome_setup ----------
@pytest.mark.asyncio
async def test_welcome_setup_requires_guild():
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)
    ctx = _FakeCtx(guild=None)

    await cog.welcome_setup(ctx, _FakeTextChannel(1))
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_welcome_setup_sets_config_and_confirms(monkeypatch):
    discord = sys.modules["discord"]
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild)
    ch = _FakeTextChannel(555, mention="#welcome")

    await cog.welcome_setup(ctx, ch)

    assert ("ensure_defaults", 111) in welcome.calls
    assert ("set_config", 111, {"channel_id": 555, "enabled": True}) in welcome.calls

    sent = ctx.followup.sent[-1]
    assert "configurés" in sent["content"]
    assert sent["allowed_mentions"] == discord.AllowedMentions.none()


# ---------- Tests: /welcome_enable ----------
@pytest.mark.asyncio
async def test_welcome_enable_requires_guild():
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)
    ctx = _FakeCtx(guild=None)

    await cog.welcome_enable(ctx)
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_welcome_enable_requires_channel_setup():
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild)

    welcome._channel_id = 0
    await cog.welcome_enable(ctx)

    assert ("ensure_defaults", 111) in welcome.calls
    assert ("get_channel_id", 111) in welcome.calls
    assert "Aucun salon de bienvenue" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_welcome_enable_sets_enabled_when_channel_configured():
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild)

    welcome._channel_id = 555
    await cog.welcome_enable(ctx)

    assert ("set_enabled", 111, True) in welcome.calls
    assert "activés" in ctx.followup.sent[-1]["content"]


# ---------- Tests: /welcome_disable ----------
@pytest.mark.asyncio
async def test_welcome_disable_requires_guild():
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)
    ctx = _FakeCtx(guild=None)

    await cog.welcome_disable(ctx)
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_welcome_disable_sets_enabled_false():
    welcome = _FakeWelcomeService()
    bot = _FakeBot(welcome)
    cog = WelcomeMessage(bot)

    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild)

    await cog.welcome_disable(ctx)

    assert ("ensure_defaults", 111) in welcome.calls
    assert ("set_enabled", 111, False) in welcome.calls
    assert "désactivés" in ctx.followup.sent[-1]["content"]


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
