from __future__ import annotations

import sys
import types

import pytest


# ---------- Local stubs / shims (complements tests/conftest.py stubs) ----------
def _ensure_discord_stubs() -> None:
    """
    Ensure minimal discord.py surface used by this cog exists at import-time.
    This avoids collection-time crashes because annotations are evaluated
    (no __future__ annotations in the source).
    """
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    # Exceptions used in the cog
    for exc_name in ("Forbidden", "HTTPException", "NotFound"):
        if not hasattr(discord, exc_name):
            setattr(discord, exc_name, type(exc_name, (Exception,), {}))

    # Types used in annotations
    if not hasattr(discord, "ApplicationContext"):
        class ApplicationContext:  # pragma: no cover
            pass
        discord.ApplicationContext = ApplicationContext

    if not hasattr(discord, "Member"):
        class Member:  # pragma: no cover
            pass
        discord.Member = Member

    if not hasattr(discord, "VoiceState"):
        class VoiceState:  # pragma: no cover
            pass
        discord.VoiceState = VoiceState

    if not hasattr(discord, "VoiceChannel"):
        class VoiceChannel:  # pragma: no cover
            pass
        discord.VoiceChannel = VoiceChannel

    if not hasattr(discord, "PermissionOverwrite"):
        class PermissionOverwrite:  # pragma: no cover
            def __init__(self, **_k):
                self.kw = _k
        discord.PermissionOverwrite = PermissionOverwrite

    # decorators (no-op for tests)
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
import eldoria.extensions.temp_voice as tv_mod  # noqa: E402
from eldoria.extensions.temp_voice import TempVoice, setup  # noqa: E402


# ---------- Fakes ----------
class _FakeVoiceChannel:
    def __init__(self, channel_id: int, *, category="CAT", bitrate: int = 64, mention: str | None = None):
        self.id = channel_id
        self.category = category
        self.bitrate = bitrate
        self.mention = mention or f"<#{channel_id}>"
        self.members = []
        self.deleted = False
        self._delete_raises = None

    async def delete(self):
        self.deleted = True
        if self._delete_raises:
            raise self._delete_raises


class _FakeVoiceState:
    def __init__(self, channel=None):
        self.channel = channel


class _FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id
        self.created = []

    async def create_voice_channel(self, **kwargs):
        # create a new channel object with id derived from call count
        new_id = 10_000 + len(self.created) + 1
        ch = _FakeVoiceChannel(new_id, category=kwargs.get("category"), bitrate=kwargs.get("bitrate", 64))
        self.created.append({"kwargs": kwargs, "channel": ch})
        return ch


class _FakeMember:
    def __init__(self, member_id: int, guild: _FakeGuild, display_name: str = "User"):
        self.id = member_id
        self.guild = guild
        self.display_name = display_name
        self.moved_to = []

    async def move_to(self, channel):
        self.moved_to.append(channel)


class _FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, *args, **kwargs):
        # discord.py/pycord accept `content` positionnel. On le normalise.
        if args and "content" not in kwargs:
            kwargs["content"] = args[0]
        self.sent.append(kwargs)


class _FakeCtx:
    def __init__(self, guild=None):
        self.guild = guild
        self.author = types.SimpleNamespace(id=123)
        self.followup = _FakeFollowup()
        self.deferred = False
        self.responded = []

    async def defer(self, ephemeral: bool = False):
        self.deferred = True
        self.defer_ephemeral = ephemeral

    async def respond(self, content: str, ephemeral: bool = False):
        self.responded.append({"content": content, "ephemeral": ephemeral})


class _FakeTempVoiceService:
    def __init__(self):
        self.calls = []
        self._parents = {}  # (guild_id, parent_channel_id) -> user_limit
        self._active = {}   # (guild_id, parent_id) -> set(active_channel_ids)
        self._find_parent_of_active = {}  # (guild_id, active_channel_id) -> parent_id

    def find_parent_of_active(self, guild_id: int, channel_id: int):
        self.calls.append(("find_parent_of_active", guild_id, channel_id))
        return self._find_parent_of_active.get((guild_id, channel_id))

    def remove_active(self, guild_id: int, parent_id: int, channel_id: int):
        self.calls.append(("remove_active", guild_id, parent_id, channel_id))

    def get_parent(self, guild_id: int, channel_id: int):
        self.calls.append(("get_parent", guild_id, channel_id))
        return self._parents.get((guild_id, channel_id))

    def add_active(self, guild_id: int, parent_id: int, channel_id: int):
        self.calls.append(("add_active", guild_id, parent_id, channel_id))
        self._find_parent_of_active[(guild_id, channel_id)] = parent_id

    def upsert_parent(self, guild_id: int, channel_id: int, user_limit: int):
        self.calls.append(("upsert_parent", guild_id, channel_id, user_limit))
        self._parents[(guild_id, channel_id)] = user_limit

    def delete_parent(self, guild_id: int, channel_id: int):
        self.calls.append(("delete_parent", guild_id, channel_id))
        self._parents.pop((guild_id, channel_id), None)

    def list_parents(self, guild_id: int):
        self.calls.append(("list_parents", guild_id))
        # return list of dicts like other configs (we don't care about shape)
        return [{"parent_channel_id": cid, "user_limit": lim} for (gid, cid), lim in self._parents.items() if gid == guild_id]


class _FakeServices:
    def __init__(self, temp_voice: _FakeTempVoiceService):
        self.temp_voice = temp_voice


class _FakeBot:
    def __init__(self, temp_voice: _FakeTempVoiceService):
        self.services = _FakeServices(temp_voice)


# ---------- Tests: voice events ----------
@pytest.mark.asyncio
async def test_voice_state_update_deletes_empty_temp_channel_and_removes_active_even_if_delete_fails():
    discord = sys.modules["discord"]
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)
    cog = TempVoice(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    before_ch = _FakeVoiceChannel(10)
    before_ch.members = []  # empty => delete
    before_ch._delete_raises = discord.Forbidden()  # still must call remove_active in finally

    svc._find_parent_of_active[(111, 10)] = 999  # channel 10 is active for parent 999

    before = _FakeVoiceState(before_ch)
    after = _FakeVoiceState(None)

    await cog.on_voice_state_update(member, before, after)

    assert ("remove_active", 111, 999, 10) in svc.calls
    assert before_ch.deleted is True


@pytest.mark.asyncio
async def test_voice_state_update_guard_if_after_is_already_temp():
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)
    cog = TempVoice(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    after_ch = _FakeVoiceChannel(20)
    # mark after as already active temp
    svc._find_parent_of_active[(111, 20)] = 999

    before = _FakeVoiceState(None)
    after = _FakeVoiceState(after_ch)

    await cog.on_voice_state_update(member, before, after)

    # Should return early: no get_parent, no create
    assert ("get_parent", 111, 20) not in svc.calls
    assert guild.created == []
    assert member.moved_to == []


@pytest.mark.asyncio
async def test_voice_state_update_creates_temp_channel_for_configured_parent_and_moves_user():
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)
    cog = TempVoice(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild, display_name="Faucon")

    parent = _FakeVoiceChannel(30, category="MYCAT", bitrate=96)
    svc._parents[(111, 30)] = 7  # user_limit

    before = _FakeVoiceState(None)
    after = _FakeVoiceState(parent)

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
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)
    cog = TempVoice(bot)

    guild = _FakeGuild(111)
    member = _FakeMember(1, guild)

    after_ch = _FakeVoiceChannel(40)
    # no parent config
    before = _FakeVoiceState(None)
    after = _FakeVoiceState(after_ch)

    await cog.on_voice_state_update(member, before, after)

    assert guild.created == []
    assert member.moved_to == []


# ---------- Tests: commands (refacto) ----------
# Le cog a été refactorisé : les commandes "init/remove/list" ont été remplacées par
# un panel (/tempvoice config) et un listing (/tempvoice list).


@pytest.mark.asyncio
async def test_tv_config_requires_guild():
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)
    cog = TempVoice(bot)
    ctx = _FakeCtx(guild=None)

    await cog.tv_config(ctx)
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_tv_config_sends_panel(monkeypatch):
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)
    cog = TempVoice(bot)

    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild)

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
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)
    cog = TempVoice(bot)
    ctx = _FakeCtx(guild=None)

    await cog.tv_list(ctx)
    assert ctx.responded[-1]["content"] == "Commande uniquement disponible sur un serveur."
    assert ctx.responded[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_tv_list_uses_paginator(monkeypatch):
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)
    cog = TempVoice(bot)

    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild)

    svc._parents[(111, 123)] = 5

    created = {}

    class _FakePaginator:
        def __init__(self, items, embed_generator, identifiant_for_embed, bot):
            created["items"] = items
            created["embed_generator"] = embed_generator
            created["ident"] = identifiant_for_embed
            created["bot"] = bot

        async def create_embed(self):
            return ("EMBED", ["FILES"])

    monkeypatch.setattr(tv_mod, "Paginator", _FakePaginator, raising=True)
    monkeypatch.setattr(tv_mod, "build_list_temp_voice_parents_embed", lambda *_a, **_k: "X", raising=True)

    await cog.tv_list(ctx)

    assert ("list_parents", 111) in svc.calls
    assert created["ident"] == 111
    assert created["bot"] is bot
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["embed"] == "EMBED"
    assert ctx.followup.sent[-1]["files"] == ["FILES"]
    assert ctx.followup.sent[-1]["view"].__class__.__name__ == "_FakePaginator"


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    svc = _FakeTempVoiceService()
    bot = _FakeBot(svc)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], TempVoice)
