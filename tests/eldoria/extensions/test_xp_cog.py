from __future__ import annotations

import sys
import types

import pytest


# ---------- Local stubs / shims (complements tests/conftest.py stubs) ----------
def _ensure_discord_stubs() -> None:
    """
    Ensure minimal discord.py surface used by this module exists at import-time.
    """
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    # Exceptions
    for exc_name in ("Forbidden", "HTTPException", "NotFound"):
        if not hasattr(discord, exc_name):
            setattr(discord, exc_name, type(exc_name, (Exception,), {}))

    # Types used in annotations
    for name in ("ApplicationContext", "Guild", "TextChannel", "Role", "Member"):
        if not hasattr(discord, name):
            setattr(discord, name, type(name, (), {}))

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

    # discord.commands.SlashCommandGroup
    if "discord.commands" not in sys.modules:
        sys.modules["discord.commands"] = types.ModuleType("discord.commands")
    dcmd = sys.modules["discord.commands"]

    if not hasattr(dcmd, "SlashCommandGroup"):
        class SlashCommandGroup:  # pragma: no cover
            def __init__(self, *args, **kwargs):
                pass

            def command(self, *args, **kwargs):
                def deco(fn):
                    return fn
                return deco

        dcmd.SlashCommandGroup = SlashCommandGroup

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

# ---------- Import module under test ----------
import eldoria.extensions.xp as xp_mod  # noqa: E402
from eldoria.extensions.xp import Xp, setup  # noqa: E402

# ---------- Fakes ----------
discord = sys.modules["discord"]


class _FakeMember(discord.Member):
    def __init__(self, member_id: int, *, bot: bool = False):
        self.id = member_id
        self.bot = bot
        self.mention = f"<@{member_id}>"


class _FakeGuild(discord.Guild):
    def __init__(self, guild_id: int):
        self.id = guild_id


class _FakeFollowup:
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, *args, **kwargs):
        # discord.py allows positional content
        if args:
            kwargs = {"content": args[0], **kwargs}
        self.sent.append(kwargs)


class _FakeCtx:
    def __init__(self, *, guild=None, user=None, author=None):
        self.guild = guild
        self.user = user or _FakeMember(123)
        self.author = author or self.user  # used by xp_admin
        self.followup = _FakeFollowup()
        self.deferred = False
        self.responded: list[dict] = []

    async def defer(self, ephemeral: bool = False):
        self.deferred = True
        self.defer_ephemeral = ephemeral

    async def respond(self, content: str, ephemeral: bool = False):
        self.responded.append({"content": content, "ephemeral": ephemeral})


class _FakeXpService:
    def __init__(self):
        self.calls: list[tuple] = []

        self._enabled = True
        self._cfg = {"enabled": True}
        self._snapshot = {
            "xp": 10,
            "level": 1,
            "level_label": "lvl1",
            "next_level_label": "lvl2",
            "next_xp_required": 20,
        }
        self._levels_with_roles = [{"level": 1, "role_id": 111, "xp_required": 0}]
        self._leaderboard_items = [{"user_id": 1, "xp": 10}]

        self._add_xp_new = 150
        self._levels = [(0, 1), (100, 2)]

    async def ensure_guild_xp_setup(self, guild):
        self.calls.append(("ensure_guild_xp_setup", guild.id))

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))

    def set_config(self, guild_id: int, **kwargs):
        self.calls.append(("set_config", guild_id, kwargs))

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return dict(self._cfg)

    def is_enabled(self, guild_id: int):
        self.calls.append(("is_enabled", guild_id))
        return bool(self._enabled)

    def build_snapshot_for_xp_profile(self, guild, user_id: int):
        self.calls.append(("build_snapshot_for_xp_profile", guild.id, user_id))
        return dict(self._snapshot)

    def get_levels_with_roles(self, guild_id: int):
        self.calls.append(("get_levels_with_roles", guild_id))
        return list(self._levels_with_roles)

    def get_leaderboard_items(self, guild, *, limit: int, offset: int):
        self.calls.append(("get_leaderboard_items", guild.id, limit, offset))
        return list(self._leaderboard_items)

    async def sync_member_level_roles(self, guild, member, xp: int | None = None):
        self.calls.append(("sync_member_level_roles", guild.id, member.id, xp))

    def add_xp(self, guild_id: int, user_id: int, delta: int):
        self.calls.append(("add_xp", guild_id, user_id, delta))
        return int(self._add_xp_new)

    def get_levels(self, guild_id: int):
        self.calls.append(("get_levels", guild_id))
        return list(self._levels)

    def compute_level(self, xp: int, levels):
        self.calls.append(("compute_level", xp))
        lvl = 0
        for th, lv in levels:
            if xp >= th:
                lvl = lv
        return lvl

    def get_role_ids(self, guild_id: int):
        self.calls.append(("get_role_ids", guild_id))
        return {1: 111, 2: 222}


class _FakeServices:
    def __init__(self, xp: _FakeXpService):
        self.xp = xp


class _FakeBot:
    def __init__(self, xp: _FakeXpService):
        self.services = _FakeServices(xp)


# ---------- UI/embed patches ----------
@pytest.fixture
def _patch_ui(monkeypatch: pytest.MonkeyPatch):
    async def _fake_build_xp_disable_embed(guild_id, bot):
        return ("DISABLED", ["F"])

    async def _fake_build_xp_status_embed(*, cfg, guild_id, bot):
        return ("STATUS", ["F"])

    async def _fake_build_xp_profile_embed(**kwargs):
        return ("PROFILE", ["F"])

    async def _fake_build_xp_roles_embed(levels_with_roles, guild_id, bot):
        return ("ROLES", ["F"])

    monkeypatch.setattr(xp_mod, "build_xp_disable_embed", _fake_build_xp_disable_embed, raising=True)
    monkeypatch.setattr(xp_mod, "build_xp_status_embed", _fake_build_xp_status_embed, raising=True)
    monkeypatch.setattr(xp_mod, "build_xp_profile_embed", _fake_build_xp_profile_embed, raising=True)
    monkeypatch.setattr(xp_mod, "build_xp_roles_embed", _fake_build_xp_roles_embed, raising=True)
    monkeypatch.setattr(xp_mod, "build_list_xp_embed", lambda *_a, **_k: "X", raising=True)
    monkeypatch.setattr(xp_mod, "level_label", lambda *_a, **_k: "LevelLabel", raising=True)
    yield


# ---------- Tests: /xp profile ----------
@pytest.mark.asyncio
async def test_xp_profile_requires_guild(_patch_ui):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    ctx = _FakeCtx(guild=None)

    await cog.xp_profile(ctx)

    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_profile_disabled_shows_disable_embed(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = False
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(42))

    await cog.xp_profile(ctx)

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "DISABLED"
    assert sent["files"] == ["F"]
    assert sent["ephemeral"] is True


@pytest.mark.asyncio
async def test_xp_profile_happy_path_builds_profile_embed(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = True
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(42))

    await cog.xp_profile(ctx)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("build_snapshot_for_xp_profile", 1, 42) in xp.calls
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "PROFILE"
    assert sent["files"] == ["F"]
    assert sent["ephemeral"] is True


# ---------- Tests: /xp status ----------
@pytest.mark.asyncio
async def test_xp_status_requires_guild(_patch_ui):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    ctx = _FakeCtx(guild=None)

    await cog.xp_status(ctx)

    sent = ctx.followup.sent[-1]
    assert sent["content"] == "Commande uniquement disponible sur un serveur."
    assert sent["ephemeral"] is True


@pytest.mark.asyncio
async def test_xp_status_builds_embed(_patch_ui):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    xp._cfg = {"enabled": True, "foo": "bar"}
    await cog.xp_status(ctx)

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "STATUS"
    assert sent["files"] == ["F"]
    assert sent["ephemeral"] is True


# ---------- Tests: /xp leaderboard ----------
@pytest.mark.asyncio
async def test_xp_leaderboard_requires_guild_responds(_patch_ui):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    ctx = _FakeCtx(guild=None)

    await cog.xp_leaderboard(ctx)

    assert ctx.responded[-1]["content"] == "Commande uniquement disponible sur un serveur."
    assert ctx.responded[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_xp_leaderboard_disabled_embed(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = False
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_leaderboard(ctx)

    assert ctx.followup.sent[-1]["embed"] == "DISABLED"


@pytest.mark.asyncio
async def test_xp_leaderboard_uses_paginator(_patch_ui, monkeypatch: pytest.MonkeyPatch):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    class _FakePaginator:
        def __init__(self, items, embed_generator, identifiant_for_embed, bot):
            self.items = items
            self.embed_generator = embed_generator
            self.ident = identifiant_for_embed
            self.bot = bot

        async def create_embed(self):
            return ("LEADER", ["F"])

    monkeypatch.setattr(xp_mod, "Paginator", _FakePaginator, raising=True)

    await cog.xp_leaderboard(ctx)

    assert ("get_leaderboard_items", 1, 200, 0) in xp.calls
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "LEADER"
    assert sent["files"] == ["F"]
    assert isinstance(sent["view"], _FakePaginator)


# ---------- Tests: /xp roles ----------
@pytest.mark.asyncio
async def test_xp_roles_requires_guild_responds(_patch_ui):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    ctx = _FakeCtx(guild=None)

    await cog.xp_roles(ctx)

    assert ctx.responded[-1]["content"] == "Commande uniquement disponible sur un serveur."
    assert ctx.responded[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_xp_roles_disabled_embed(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = False
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_roles(ctx)

    assert ctx.followup.sent[-1]["embed"] == "DISABLED"


@pytest.mark.asyncio
async def test_xp_roles_happy_path(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = True
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_roles(ctx)

    assert ("get_levels_with_roles", 1) in xp.calls
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "ROLES"
    assert sent["ephemeral"] is True

# ---------- Tests: /xp_admin ----------
@pytest.mark.asyncio
async def test_xp_admin_requires_guild(_patch_ui):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    ctx = _FakeCtx(guild=None)

    await cog.xp_admin(ctx)

    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_admin_sends_view(_patch_ui, monkeypatch: pytest.MonkeyPatch):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild, author=_FakeMember(999))

    class _FakeView:
        def __init__(self, *, xp, author_id, guild):
            assert xp is xp_mod  or True  # don't care, just prevent unused check
            self._ = (author_id, guild)

        def current_embed(self):
            return ("ADMIN", ["F"])

    monkeypatch.setattr(xp_mod, "XpAdminMenuView", _FakeView, raising=True)

    await cog.xp_admin(ctx)

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "ADMIN"
    assert sent["files"] == ["F"]
    assert isinstance(sent["view"], _FakeView)
    assert sent["ephemeral"] is True


# ---------- Tests: /xp_modify ----------
@pytest.mark.asyncio
async def test_xp_modify_requires_guild(_patch_ui):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    ctx = _FakeCtx(guild=None)

    await cog.xp_modify(ctx, _FakeMember(1), 10)
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_modify_rejects_bot_member(_patch_ui):
    xp = _FakeXpService()
    cog = Xp(_FakeBot(xp))
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    bot_member = _FakeMember(99, bot=True)
    await cog.xp_modify(ctx, bot_member, 10)

    assert "Impossible de modifier l'XP d'un bot" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_modify_happy_path_adds_xp_syncs_roles_and_confirms(_patch_ui):
    xp = _FakeXpService()
    xp._add_xp_new = 150
    xp._levels = [(0, 1), (100, 2)]
    cog = Xp(_FakeBot(xp))

    guild = _FakeGuild(1)
    member = _FakeMember(42, bot=False)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_modify(ctx, member, -5)

    assert ("add_xp", 1, 42, -5) in xp.calls
    assert ("get_levels", 1) in xp.calls
    assert ("compute_level", 150) in xp.calls
    assert ("sync_member_level_roles", 1, 42, 150) in xp.calls
    assert "150 XP" in ctx.followup.sent[-1]["content"]


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    xp = _FakeXpService()
    bot = _FakeBot(xp)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], Xp)