from __future__ import annotations

import sys

import pytest

# ---------- Local stubs / shims (complements tests/conftest.py stubs) ----------
# ---------- Import module under test ----------
import eldoria.extensions.xp as xp_mod  # noqa: E402
from eldoria.extensions.xp import Xp, setup  # noqa: E402

# ---------- Fakes ----------
discord = sys.modules["discord"]


def _member_init(self, member_id: int, *, bot: bool = False):
    self.id = member_id
    self.bot = bot
    self.mention = f"<@{member_id}>"


MemberStub = type("MemberStub", (discord.Member,), {"__init__": _member_init})


def _guild_init(self, guild_id: int):
    self.id = guild_id


GuildStub = type("GuildStub", (discord.Guild,), {"__init__": _guild_init})


def _followup_init(self):
    self.sent = []


async def _followup_send(self, *args, **kwargs):
    if args:
        kwargs = {"content": args[0], **kwargs}
    self.sent.append(kwargs)


FollowupStub = type("FollowupStub", (), {"__init__": _followup_init, "send": _followup_send})


def _ctx_init(self, *, guild=None, user=None, author=None):
    discord_mod = sys.modules["discord"]
    GuildChan = type("_GuildChan", (discord_mod.abc.GuildChannel,), {"id": 0})
    self.guild = guild
    self.user = user or MemberStub(123)
    self.author = author or self.user
    self.channel = GuildChan()
    self.followup = FollowupStub()
    self.deferred = False
    self.responded = []


async def _ctx_defer(self, ephemeral: bool = False):
    self.deferred = True
    self.defer_ephemeral = ephemeral


async def _ctx_respond(self, content: str, ephemeral: bool = False):
    self.responded.append({"content": content, "ephemeral": ephemeral})


CtxStub = type(
    "CtxStub",
    (),
    {
        "__init__": _ctx_init,
        "defer": _ctx_defer,
        "respond": _ctx_respond,
    },
)


def _xpsvc_init(self):
    # Use the canonical fake (shared) to keep behavior consistent.
    from tests._fakes import FakeXpService

    impl = FakeXpService()
    self._impl = impl
    # Expose the same stateful attributes the tests tweak.
    self.calls = impl.calls
    self._enabled = impl._enabled
    self._cfg = impl._cfg
    self._snapshot = impl._snapshot
    self._levels_with_roles = impl._levels_with_roles
    self._leaderboard_items = impl._leaderboard_items
    self._add_xp_new = impl._add_xp_new
    self._levels = impl._levels


async def _xpsvc_ensure_guild_xp_setup(self, guild):
    return await self._impl.ensure_guild_xp_setup(guild)


def _xpsvc_ensure_defaults(self, guild_id: int):
    return self._impl.ensure_defaults(guild_id)


def _xpsvc_set_config(self, guild_id: int, **kwargs):
    # Keep local view in sync for assertions.
    self._cfg.update(kwargs)
    return self._impl.set_config(guild_id, **kwargs)


def _xpsvc_get_config(self, guild_id: int):
    # The original stub returned only self._cfg.
    self.calls.append(("get_config", guild_id))
    return dict(self._cfg)


def _xpsvc_is_enabled(self, guild_id: int):
    self.calls.append(("is_enabled", guild_id))
    return bool(self._enabled)


def _xpsvc_require_enabled(self, guild_id: int):
    self.calls.append(("require_enabled", guild_id))
    if not self._enabled:
        from eldoria.exceptions.general import XpDisabled

        raise XpDisabled(guild_id)


def _xpsvc_build_snapshot(self, guild, user_id: int):
    self.calls.append(("build_snapshot_for_xp_profile", guild.id, user_id))
    return dict(self._snapshot)


def _xpsvc_levels_with_roles(self, guild_id: int):
    self.calls.append(("get_levels_with_roles", guild_id))
    return list(self._levels_with_roles)


def _xpsvc_leaderboard(self, guild, *, limit: int, offset: int):
    self.calls.append(("get_leaderboard_items", guild.id, limit, offset))
    return list(self._leaderboard_items)


async def _xpsvc_sync_member_level_roles(self, guild, member, xp: int | None = None):
    self.calls.append(("sync_member_level_roles", guild.id, member.id, xp))


def _xpsvc_add_xp(self, guild_id: int, user_id: int, delta: int):
    self.calls.append(("add_xp", guild_id, user_id, delta))
    return int(self._add_xp_new)


def _xpsvc_get_levels(self, guild_id: int):
    self.calls.append(("get_levels", guild_id))
    return list(self._levels)


def _xpsvc_compute_level(self, xp: int, levels):
    self.calls.append(("compute_level", xp))
    lvl = 0
    for th, lv in levels:
        if xp >= th:
            lvl = lv
    return lvl


def _xpsvc_get_role_ids(self, guild_id: int):
    self.calls.append(("get_role_ids", guild_id))
    return {1: 111, 2: 222}


XpServiceStub = type(
    "XpServiceStub",
    (),
    {
        "__init__": _xpsvc_init,
        "ensure_guild_xp_setup": _xpsvc_ensure_guild_xp_setup,
        "ensure_defaults": _xpsvc_ensure_defaults,
        "set_config": _xpsvc_set_config,
        "get_config": _xpsvc_get_config,
        "is_enabled": _xpsvc_is_enabled,
        "require_enabled": _xpsvc_require_enabled,
        "build_snapshot_for_xp_profile": _xpsvc_build_snapshot,
        "get_levels_with_roles": _xpsvc_levels_with_roles,
        "get_leaderboard_items": _xpsvc_leaderboard,
        "sync_member_level_roles": _xpsvc_sync_member_level_roles,
        "add_xp": _xpsvc_add_xp,
        "get_levels": _xpsvc_get_levels,
        "compute_level": _xpsvc_compute_level,
        "get_role_ids": _xpsvc_get_role_ids,
    },
)


def _services_init(self, xp: XpServiceStub):
    self.xp = xp


ServicesStub = type("ServicesStub", (), {"__init__": _services_init})


def _bot_init(self, xp: XpServiceStub):
    self.services = ServicesStub(xp)


BotStub = type("BotStub", (), {"__init__": _bot_init})


# ---------- UI/embed patches ----------
@pytest.fixture
def _patch_ui(monkeypatch: pytest.MonkeyPatch):
    async def _fake_build_xp_status_embed(*, config, guild_id, bot):
        return ("STATUS", ["F"])

    async def _fake_build_xp_profile_embed(**kwargs):
        return ("PROFILE", ["F"])

    async def _fake_build_xp_roles_embed(levels_with_roles, guild_id, bot):
        return ("ROLES", ["F"])

    monkeypatch.setattr(xp_mod, "build_xp_status_embed", _fake_build_xp_status_embed, raising=True)
    monkeypatch.setattr(xp_mod, "build_xp_profile_embed", _fake_build_xp_profile_embed, raising=True)
    monkeypatch.setattr(xp_mod, "build_xp_roles_embed", _fake_build_xp_roles_embed, raising=True)
    monkeypatch.setattr(xp_mod, "build_list_xp_embed", lambda *_a, **_k: "X", raising=True)
    monkeypatch.setattr(xp_mod, "level_label", lambda *_a, **_k: "LevelLabel", raising=True)
    yield


# ---------- Tests: /xp profile ----------
@pytest.mark.asyncio
async def test_xp_profile_requires_guild(_patch_ui):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    ctx = CtxStub(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.xp_profile(ctx)


@pytest.mark.asyncio
async def test_xp_profile_disabled_shows_disable_embed(_patch_ui):
    xp = XpServiceStub()
    xp._enabled = False
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild, user=MemberStub(42))

    from eldoria.exceptions.general import XpDisabled

    with pytest.raises(XpDisabled):
        await cog.xp_profile(ctx)


@pytest.mark.asyncio
async def test_xp_profile_happy_path_builds_profile_embed(_patch_ui):
    xp = XpServiceStub()
    xp._enabled = True
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild, user=MemberStub(42))

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
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    ctx = CtxStub(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.xp_status(ctx)


@pytest.mark.asyncio
async def test_xp_status_builds_embed(_patch_ui):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild)

    xp._cfg = {"enabled": True, "foo": "bar"}
    await cog.xp_status(ctx)

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "STATUS"
    assert sent["files"] == ["F"]
    assert sent["ephemeral"] is True


# ---------- Tests: /xp leaderboard ----------
@pytest.mark.asyncio
async def test_xp_leaderboard_requires_guild_responds(_patch_ui):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    ctx = CtxStub(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.xp_leaderboard(ctx)


@pytest.mark.asyncio
async def test_xp_leaderboard_disabled_embed(_patch_ui):
    xp = XpServiceStub()
    xp._enabled = False
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild)

    from eldoria.exceptions.general import XpDisabled

    with pytest.raises(XpDisabled):
        await cog.xp_leaderboard(ctx)


@pytest.mark.asyncio
async def test_xp_leaderboard_uses_paginator(_patch_ui, monkeypatch: pytest.MonkeyPatch):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild)

    def paginator_factory(items, embed_generator, identifiant_for_embed, bot):
        async def create_embed(self):
            return ("LEADER", ["F"])

        return type(
            "PaginatorStub",
            (),
            {
                "items": items,
                "embed_generator": embed_generator,
                "ident": identifiant_for_embed,
                "bot": bot,
                "create_embed": create_embed,
            },
        )()

    monkeypatch.setattr(xp_mod, "Paginator", paginator_factory, raising=True)

    await cog.xp_leaderboard(ctx)

    assert ("get_leaderboard_items", 1, 200, 0) in xp.calls
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "LEADER"
    assert sent["files"] == ["F"]
    assert hasattr(sent["view"], "create_embed")


# ---------- Tests: /xp roles ----------
@pytest.mark.asyncio
async def test_xp_roles_requires_guild_responds(_patch_ui):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    ctx = CtxStub(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.xp_roles(ctx)


@pytest.mark.asyncio
async def test_xp_roles_disabled_embed(_patch_ui):
    xp = XpServiceStub()
    xp._enabled = False
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild)

    from eldoria.exceptions.general import XpDisabled

    with pytest.raises(XpDisabled):
        await cog.xp_roles(ctx)


@pytest.mark.asyncio
async def test_xp_roles_happy_path(_patch_ui):
    xp = XpServiceStub()
    xp._enabled = True
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild)

    await cog.xp_roles(ctx)

    assert ("get_levels_with_roles", 1) in xp.calls
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "ROLES"
    assert sent["ephemeral"] is True

# ---------- Tests: /xp_admin ----------
@pytest.mark.asyncio
async def test_xp_admin_requires_guild(_patch_ui):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    ctx = CtxStub(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.xp_admin(ctx)


@pytest.mark.asyncio
async def test_xp_admin_sends_view(_patch_ui, monkeypatch: pytest.MonkeyPatch):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild, author=MemberStub(999))

    def view_factory(*, xp, author_id, guild):
        _ = (xp, author_id, guild)

        def current_embed(self):
            return ("ADMIN", ["F"])

        return type("ViewStub", (), {"current_embed": current_embed, "_": _})()

    monkeypatch.setattr(xp_mod, "XpAdminMenuView", view_factory, raising=True)

    await cog.xp_admin(ctx)

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "ADMIN"
    assert sent["files"] == ["F"]
    assert hasattr(sent["view"], "current_embed")
    assert sent["ephemeral"] is True


# ---------- Tests: /xp_modify ----------
@pytest.mark.asyncio
async def test_xp_modify_requires_guild(_patch_ui):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    ctx = CtxStub(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.xp_modify(ctx, MemberStub(1), 10)


@pytest.mark.asyncio
async def test_xp_modify_rejects_bot_member(_patch_ui):
    xp = XpServiceStub()
    cog = Xp(BotStub(xp))
    guild = GuildStub(1)
    ctx = CtxStub(guild=guild)

    bot_member = MemberStub(99, bot=True)
    from eldoria.exceptions.general import BotTargetNotAllowed

    with pytest.raises(BotTargetNotAllowed):
        await cog.xp_modify(ctx, bot_member, 10)


@pytest.mark.asyncio
async def test_xp_modify_happy_path_adds_xp_syncs_roles_and_confirms(_patch_ui):
    xp = XpServiceStub()
    xp._add_xp_new = 150
    xp._levels = [(0, 1), (100, 2)]
    cog = Xp(BotStub(xp))

    guild = GuildStub(1)
    member = MemberStub(42, bot=False)
    ctx = CtxStub(guild=guild)

    await cog.xp_modify(ctx, member, -5)

    assert ("add_xp", 1, 42, -5) in xp.calls
    assert ("get_levels", 1) in xp.calls
    assert ("compute_level", 150) in xp.calls
    assert ("sync_member_level_roles", 1, 42, 150) in xp.calls
    assert "150 XP" in ctx.followup.sent[-1]["content"]


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    xp = XpServiceStub()
    bot = BotStub(xp)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], Xp)