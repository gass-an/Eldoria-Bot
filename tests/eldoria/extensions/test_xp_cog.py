from __future__ import annotations

import sys
import types

import pytest


# ---------- Local stubs / shims (complements tests/conftest.py stubs) ----------
def _ensure_discord_stubs() -> None:
    """
    Ensure minimal discord.py surface used by this module exists at import-time.
    (Source file does not use `from __future__ import annotations`, so annotations evaluate at import time.)
    """
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    # Exceptions
    for exc_name in ("Forbidden", "HTTPException", "NotFound"):
        if not hasattr(discord, exc_name):
            setattr(discord, exc_name, type(exc_name, (Exception,), {}))

    # AllowedMentions (only used in xp_enable? none; used in welcome; but keep generic)
    if not hasattr(discord, "AllowedMentions"):
        class AllowedMentions:  # pragma: no cover
            def __init__(self, **kw):
                self.kw = kw

            @staticmethod
            def none():
                return "ALLOWED_MENTIONS_NONE"
        discord.AllowedMentions = AllowedMentions

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
import eldoria.extensions.xp as xp_mod  # noqa: E402
from eldoria.extensions.xp import Xp, setup  # noqa: E402

# ---------- Fakes ----------
discord = sys.modules["discord"]


class _FakeRole(discord.Role):
    def __init__(self, role_id: int, *, mention: str | None = None):
        self.id = role_id
        self.mention = mention or f"<@&{role_id}>"


class _FakeMember(discord.Member):
    def __init__(self, member_id: int, *, bot: bool = False, roles=None, mention: str | None = None):
        self.id = member_id
        self.bot = bot
        self.roles = list(roles or [])
        self.mention = mention or f"<@{member_id}>"
        self.removed_roles = []
        self._remove_raises = None

    async def remove_roles(self, *roles, reason: str | None = None):
        if self._remove_raises:
            raise self._remove_raises
        self.removed_roles.append({"roles": roles, "reason": reason})
        # also update local roles for realism
        for r in roles:
            if r in self.roles:
                self.roles.remove(r)


class _FakeGuild(discord.Guild):
    def __init__(self, guild_id: int, *, members=None):
        self.id = guild_id
        self.members = list(members or [])
        self._roles = {}
        self._channels = {}

    def get_role(self, role_id: int):
        return self._roles.get(role_id)

    def add_role(self, role: _FakeRole):
        self._roles[role.id] = role

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class _FakeTextChannel(discord.TextChannel):
    def __init__(self, channel_id: int = 1, mention: str | None = None):
        self.id = channel_id
        self.mention = mention or f"<#{channel_id}>"


class _FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, *args, **kwargs):
        # discord.py autorise content en positionnel
        if args:
            # on normalise: 1er arg = content
            kwargs = {"content": args[0], **kwargs}
        self.sent.append(kwargs)


class _FakeCtx:
    def __init__(self, *, guild=None, user=None):
        self.guild = guild
        self.user = user or _FakeMember(123)
        self.followup = _FakeFollowup()
        self.deferred = False
        self.responded = []

    async def defer(self, ephemeral: bool = False):
        self.deferred = True
        self.defer_ephemeral = ephemeral

    async def respond(self, content: str, ephemeral: bool = False):
        self.responded.append({"content": content, "ephemeral": ephemeral})


class _FakeXpService:
    def __init__(self):
        self.calls = []

        # behavior knobs
        self._enabled = True
        self._cfg = {"enabled": True}
        self._snapshot = {
            "xp": 10,
            "level": 1,
            "level_label": "lvl1",
            "next_level_label": "lvl2",
            "next_xp_required": 20,
        }
        self._levels_with_roles = []
        self._leaderboard_items = [{"user_id": 1, "xp": 10}]
        self._role_ids = {1: 111, 2: 222}
        self._levels = [(0, 1), (100, 2)]
        self._add_xp_new = 50

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

    def set_level_threshold(self, guild_id: int, level: int, xp_required: int):
        self.calls.append(("set_level_threshold", guild_id, level, xp_required))

    async def sync_member_level_roles(self, guild, member, xp: int | None = None):
        self.calls.append(("sync_member_level_roles", guild.id, member.id, xp))

    def get_role_ids(self, guild_id: int):
        self.calls.append(("get_role_ids", guild_id))
        return dict(self._role_ids)

    def upsert_role_id(self, guild_id: int, level: int, role_id: int):
        self.calls.append(("upsert_role_id", guild_id, level, role_id))
        self._role_ids[level] = role_id

    def add_xp(self, guild_id: int, user_id: int, delta: int):
        self.calls.append(("add_xp", guild_id, user_id, delta))
        return int(self._add_xp_new)

    def get_levels(self, guild_id: int):
        self.calls.append(("get_levels", guild_id))
        return list(self._levels)

    def compute_level(self, xp: int, levels):
        self.calls.append(("compute_level", xp))
        # naive: return highest level whose threshold <= xp
        lvl = 0
        for th, lv in levels:
            if xp >= th:
                lvl = lv
        return lvl


class _FakeServices:
    def __init__(self, xp: _FakeXpService):
        self.xp = xp


class _FakeBot:
    def __init__(self, xp: _FakeXpService):
        self.services = _FakeServices(xp)


# ---------- Embed/paginator stubs ----------
@pytest.fixture
def _patch_ui(monkeypatch):
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


# ---------- Tests: xp_enable / xp_disable / xp_status ----------
@pytest.mark.asyncio
async def test_xp_enable_requires_guild(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_enable(ctx)

    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_enable_happy_path(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_enable(ctx)

    assert ("ensure_guild_xp_setup", 1) in xp.calls
    assert ("set_config", 1, {"enabled": True}) in xp.calls
    assert "activé" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_disable_requires_guild(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_disable(ctx)

    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_disable_happy_path(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_disable(ctx)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"enabled": False}) in xp.calls
    assert "désactivé" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_status_requires_guild(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_status(ctx)

    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."
    assert ctx.followup.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_xp_status_builds_embed(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    xp._cfg = {"enabled": True, "foo": "bar"}
    await cog.xp_status(ctx)

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "STATUS"
    assert sent["files"] == ["F"]
    assert sent["ephemeral"] is True


# ---------- Tests: xp_me ----------
@pytest.mark.asyncio
async def test_xp_me_requires_guild(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_me(ctx)
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_me_shows_disabled_embed_when_feature_off(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = False
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(42))

    await cog.xp_me(ctx)

    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "DISABLED"
    assert sent["files"] == ["F"]
    assert sent["ephemeral"] is True


@pytest.mark.asyncio
async def test_xp_me_happy_path_builds_profile_embed(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = True
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(42))

    await cog.xp_me(ctx)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("build_snapshot_for_xp_profile", 1, 42) in xp.calls
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "PROFILE"
    assert sent["files"] == ["F"]
    assert sent["ephemeral"] is True


# ---------- Tests: xp_roles ----------
@pytest.mark.asyncio
async def test_xp_roles_requires_guild_responds(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_roles(ctx)
    assert ctx.responded[-1]["content"] == "Commande uniquement disponible sur un serveur."
    assert ctx.responded[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_xp_roles_disabled_embed(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = False
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_roles(ctx)
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "DISABLED"


@pytest.mark.asyncio
async def test_xp_roles_happy_path(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    xp._levels_with_roles = [{"level": 1, "role_id": 111, "xp_required": 0}]
    await cog.xp_roles(ctx)

    assert ("get_levels_with_roles", 1) in xp.calls
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "ROLES"
    assert sent["ephemeral"] is True


# ---------- Tests: xp_classement (paginator) ----------
@pytest.mark.asyncio
async def test_xp_list_requires_guild_responds(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_list(ctx)
    assert ctx.responded[-1]["content"] == "Commande uniquement disponible sur un serveur."
    assert ctx.responded[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_xp_list_disabled_embed(_patch_ui):
    xp = _FakeXpService()
    xp._enabled = False
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_list(ctx)
    assert ctx.followup.sent[-1]["embed"] == "DISABLED"


@pytest.mark.asyncio
async def test_xp_list_uses_paginator(_patch_ui, monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    created = {}

    class _FakePaginator:
        def __init__(self, items, embed_generator, identifiant_for_embed, bot):
            created["items"] = items
            created["embed_generator"] = embed_generator
            created["ident"] = identifiant_for_embed
            created["bot"] = bot

        async def create_embed(self):
            return ("LEADER", ["F"])

    monkeypatch.setattr(xp_mod, "Paginator", _FakePaginator, raising=True)

    await cog.xp_list(ctx)

    assert ("get_leaderboard_items", 1, 200, 0) in xp.calls
    assert created["ident"] == 1
    sent = ctx.followup.sent[-1]
    assert sent["embed"] == "LEADER"
    assert sent["files"] == ["F"]
    assert sent["view"].__class__.__name__ == "_FakePaginator"


# ---------- Tests: xp_set_level ----------
@pytest.mark.asyncio
async def test_xp_set_level_requires_guild(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_set_level(ctx, 1, 100)
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_set_level_sets_threshold_and_syncs_members_best_effort(_patch_ui, monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)

    m1 = _FakeMember(1)
    m2 = _FakeMember(2)
    guild = _FakeGuild(1, members=[m1, m2])
    ctx = _FakeCtx(guild=guild)

    # make sync fail on second member to ensure it's swallowed by try/except
    async def sync_member_level_roles(guild, member, **kwargs):
        xp.calls.append(("sync_member_level_roles", guild.id, member.id, kwargs.get("xp")))
        if member.id == 2:
            raise RuntimeError("boom")

    monkeypatch.setattr(xp, "sync_member_level_roles", sync_member_level_roles, raising=True)

    await cog.xp_set_level(ctx, 2, 250)

    assert ("set_level_threshold", 1, 2, 250) in xp.calls
    assert any("Seuil mis à jour" in s["content"] for s in ctx.followup.sent)
    # sync attempted for both
    assert ("sync_member_level_roles", 1, 1, None) in xp.calls
    assert ("sync_member_level_roles", 1, 2, None) in xp.calls


# ---------- Tests: xp_set_config ----------
@pytest.mark.asyncio
async def test_xp_set_config_requires_guild(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_set_config(ctx)
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_set_config_no_fields_noop(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_set_config(ctx)
    assert "Aucun champ fourni" in ctx.followup.sent[-1]["content"]
    # no set_config call
    assert not any(c[0] == "set_config" for c in xp.calls)


@pytest.mark.asyncio
async def test_xp_set_config_updates_and_message_parts(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    ch = _FakeTextChannel(10, mention="#general")

    await cog.xp_set_config(
        ctx,
        points_per_message=3,
        cooldown_seconds=10,
        bonus_percent=20,
        karuta_k_small_percent=30,
        voice_enabled=True,
        voice_interval_seconds=180,
        voice_xp_per_interval=2,
        voice_daily_cap_xp=100,
        voice_levelup_channel=ch,
    )

    # set_config called with voice_levelup_channel_id
    assert ("set_config", 1, {
        "points_per_message": 3,
        "cooldown_seconds": 10,
        "bonus_percent": 20,
        "karuta_k_small_percent": 30,
        "voice_enabled": True,
        "voice_interval_seconds": 180,
        "voice_xp_per_interval": 2,
        "voice_daily_cap_xp": 100,
        "voice_levelup_channel_id": 10,
    }) in xp.calls

    msg = ctx.followup.sent[-1]["content"]
    assert "3 XP" in msg
    assert "cooldown" in msg
    assert "bonus tag" in msg
    assert "karuta" in msg
    assert "vocal **on**" in msg
    assert "interval" in msg
    assert "cap vocal" in msg
    assert "#general" in msg


# ---------- Tests: xp_set_role (xp_role_setup) ----------
@pytest.mark.asyncio
async def test_xp_role_setup_requires_guild(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)
    await cog.xp_role_setup(ctx, "level 1", _FakeRole(1))
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_role_setup_invalid_from_role_regex(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)

    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_role_setup(ctx, "not-a-level", _FakeRole(999))
    assert "Sélection invalide" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_role_setup_no_roles_in_db(_patch_ui, monkeypatch):
    xp = _FakeXpService()
    xp._role_ids = {}
    bot = _FakeBot(xp)
    cog = Xp(bot)

    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_role_setup(ctx, "level 1", _FakeRole(999))
    assert "Aucun rôle XP enregistré" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_role_setup_level_missing_in_db(_patch_ui):
    xp = _FakeXpService()
    xp._role_ids = {2: 222}  # no level 1
    bot = _FakeBot(xp)
    cog = Xp(bot)

    guild = _FakeGuild(1)
    ctx = _FakeCtx(guild=guild)

    await cog.xp_role_setup(ctx, "level 1", _FakeRole(999))
    assert "Aucun role XP en base" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_role_setup_source_role_deleted_on_server(_patch_ui):
    xp = _FakeXpService()
    xp._role_ids = {1: 111}
    bot = _FakeBot(xp)
    cog = Xp(bot)

    guild = _FakeGuild(1)  # no role 111 in guild
    ctx = _FakeCtx(guild=guild)

    await cog.xp_role_setup(ctx, "level 1", _FakeRole(999))
    assert "rôle source n'existe plus" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_role_setup_to_role_already_mapped_to_other_level(_patch_ui):
    xp = _FakeXpService()
    xp._role_ids = {1: 111, 2: 222}
    bot = _FakeBot(xp)
    cog = Xp(bot)

    guild = _FakeGuild(1)
    guild.add_role(_FakeRole(111))
    guild.add_role(_FakeRole(222))
    ctx = _FakeCtx(guild=guild)

    # try to map level 1 to role 222 (already used by level 2)
    await cog.xp_role_setup(ctx, "level 1", _FakeRole(222))
    assert "déjà associé au niveau" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_role_setup_noop_when_same_role(_patch_ui):
    xp = _FakeXpService()
    xp._role_ids = {1: 111}
    bot = _FakeBot(xp)
    cog = Xp(bot)

    guild = _FakeGuild(1)
    guild.add_role(_FakeRole(111))
    ctx = _FakeCtx(guild=guild)

    await cog.xp_role_setup(ctx, "level 1", _FakeRole(111))
    assert "identiques" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_xp_role_setup_happy_path_migrates_affected_members_and_reports_failures(_patch_ui):
    discord = sys.modules["discord"]
    xp = _FakeXpService()
    xp._role_ids = {1: 111}
    bot = _FakeBot(xp)
    cog = Xp(bot)

    from_role_obj = _FakeRole(111)
    guild = _FakeGuild(1)
    guild.add_role(from_role_obj)

    # affected members are those having from_role_obj in roles and not bot
    m_ok = _FakeMember(1, bot=False, roles=[from_role_obj])
    m_fail = _FakeMember(2, bot=False, roles=[from_role_obj])
    m_fail._remove_raises = discord.Forbidden()
    m_bot = _FakeMember(3, bot=True, roles=[from_role_obj])
    guild.members = [m_ok, m_fail, m_bot]

    ctx = _FakeCtx(guild=guild)
    to_role = _FakeRole(999)

    await cog.xp_role_setup(ctx, "level 1", to_role)

    # upsert called
    assert ("upsert_role_id", 1, 1, 999) in xp.calls
    # migration attempted for m_ok and m_fail, not m_bot
    assert len(m_ok.removed_roles) == 1
    assert len(m_fail.removed_roles) == 0  # failed before recording
    # sync attempted for m_ok; m_fail may not reach sync due to remove failure
    assert ("sync_member_level_roles", 1, 1, None) in xp.calls
    # message contains failures
    msg = ctx.followup.sent[-1]["content"]
    assert "mis à jour" in msg
    assert "échecs" in msg


# ---------- Tests: xp_modify ----------
@pytest.mark.asyncio
async def test_xp_modify_requires_guild(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)
    ctx = _FakeCtx(guild=None)

    await cog.xp_modify(ctx, _FakeMember(1), 10)
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_xp_modify_rejects_bot_member(_patch_ui):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = Xp(bot)

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
    bot = _FakeBot(xp)
    cog = Xp(bot)

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
