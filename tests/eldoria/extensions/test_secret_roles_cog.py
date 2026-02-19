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

    if not hasattr(discord, "TextChannel"):
        class TextChannel:  # pragma: no cover
            pass
        discord.TextChannel = TextChannel

    if not hasattr(discord, "Role"):
        class Role:  # pragma: no cover
            pass
        discord.Role = Role

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
import eldoria.extensions.secret_roles as sr_mod  # noqa: E402
from eldoria.extensions.secret_roles import SecretRoles, setup  # noqa: E402


# ---------- Fakes ----------
class _FakeRole:
    def __init__(self, role_id: int, position: int = 0):
        self.id = role_id
        self.position = position


class _FakeTextChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id


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


class _FakeMember:
    def __init__(self, member_id: int, roles=None):
        self.id = member_id
        self.roles = roles or []
        self.added = []
        self.removed = []
        self._raise_add_remove = None

    async def add_roles(self, role):
        if self._raise_add_remove:
            raise self._raise_add_remove
        self.added.append(role)

    async def remove_roles(self, role):
        if self._raise_add_remove:
            raise self._raise_add_remove
        self.removed.append(role)


class _FakeGuild:
    def __init__(self, guild_id: int, me: _FakeMember):
        self.id = guild_id
        self.me = me

    def get_member(self, user_id: int):
        # only bot user used in this cog
        return self.me


class _FakeRoleService:
    def __init__(self):
        self.calls = []
        self._sr_match_role_id = None
        self._guild_grouped = []

    def sr_match(self, guild_id: int, channel_id: int, message: str):
        self.calls.append(("sr_match", guild_id, channel_id, message))
        return self._sr_match_role_id

    def sr_upsert(self, guild_id: int, channel_id: int, message: str, role_id: int):
        self.calls.append(("sr_upsert", guild_id, channel_id, message, role_id))

    def sr_delete(self, guild_id: int, channel_id: int, message: str):
        self.calls.append(("sr_delete", guild_id, channel_id, message))

    def sr_list_by_guild_grouped(self, guild_id: int):
        self.calls.append(("sr_list_by_guild_grouped", guild_id))
        return list(self._guild_grouped)


class _FakeServices:
    def __init__(self, role_service: _FakeRoleService):
        self.role = role_service


class _FakeBotUser:
    def __init__(self, user_id: int):
        self.id = user_id


class _FakeBot:
    def __init__(self, role_service: _FakeRoleService):
        self.services = _FakeServices(role_service)
        self.user = _FakeBotUser(999)


# ---------- Tests: add_secret_role ----------
@pytest.mark.asyncio
async def test_add_secret_role_requires_guild():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    cog = SecretRoles(bot)
    ctx = _FakeCtx(guild=None)

    await cog.sr_add(ctx, "msg", _FakeTextChannel(10), _FakeRole(1))
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_add_secret_role_rejects_role_above_bot():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)

    
    me = _FakeMember(123456789, roles=[_FakeRole(101, position=4)])
    guild = _FakeGuild(111, me)
    ctx = _FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role = _FakeRole(1, position=5)  # equal => reject
    await cog.sr_add(ctx, "msg", _FakeTextChannel(10), role)
    assert "au-dessus de mes permissions" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_add_secret_role_rejects_existing_other_role():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)

    me = _FakeMember(123456789, roles=[_FakeRole(101, position=4)])
    guild = _FakeGuild(111, me)
    ctx = _FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_match_role_id = 9999
    await cog.sr_add(ctx, "hello", _FakeTextChannel(10), _FakeRole(1, position=1))
    assert "déjà associé au rôle" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_add_secret_role_propagates_forbidden_when_probing_role():
    discord = sys.modules["discord"]
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)

    me = _FakeMember(123456789, roles=[_FakeRole(101, position=4)])
    me._raise_add_remove = discord.Forbidden()
    guild = _FakeGuild(111, me)
    ctx = _FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    with pytest.raises(discord.Forbidden):
        await cog.sr_add(ctx, "hello", _FakeTextChannel(10), _FakeRole(1, position=1))


@pytest.mark.asyncio
async def test_add_secret_role_success_upserts_and_confirms():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)

    me = _FakeMember(123456789, roles=[_FakeRole(101, position=4)])
    guild = _FakeGuild(111, me)
    ctx = _FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_match_role_id = None
    role = _FakeRole(1, position=1)
    await cog.sr_add(ctx, "hello", _FakeTextChannel(10), role)

    # probes add/remove worked
    assert me.added == [role]
    assert me.removed == [role]

    assert ("sr_upsert", 111, 10, "hello", 1) in role_svc.calls
    assert "bien associée" in ctx.followup.sent[-1]["content"]


# ---------- Tests: delete_secret_role ----------
@pytest.mark.asyncio
async def test_delete_secret_role_requires_guild():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    cog = SecretRoles(bot)
    ctx = _FakeCtx(guild=None)

    await cog.sr_remove(ctx, _FakeTextChannel(10), "msg")
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["content"] == "Commande uniquement disponible sur un serveur."


@pytest.mark.asyncio
async def test_delete_secret_role_handles_not_found():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)

    me = _FakeMember(123456789, roles=[_FakeRole(101, position=4)])
    guild = _FakeGuild(111, me)
    ctx = _FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_match_role_id = None
    await cog.sr_remove(ctx, _FakeTextChannel(10), "hello")
    assert "Aucune attribution trouvée" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_delete_secret_role_deletes_when_exists():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)

    me = _FakeMember(123456789, roles=[_FakeRole(101, position=4)])
    guild = _FakeGuild(111, me)
    ctx = _FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_match_role_id = 42
    await cog.sr_remove(ctx, _FakeTextChannel(10), "hello")
    assert ("sr_delete", 111, 10, "hello") in role_svc.calls
    assert "n'attribue plus de rôle" in ctx.followup.sent[-1]["content"]


# ---------- Tests: list_of_secret_roles ----------
@pytest.mark.asyncio
async def test_list_of_secret_roles_requires_guild():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    cog = SecretRoles(bot)
    ctx = _FakeCtx(guild=None)

    await cog.sr_list(ctx)
    assert ctx.responded[-1]["content"] == "Commande uniquement disponible sur un serveur."
    assert ctx.responded[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_list_of_secret_roles_uses_paginator(monkeypatch):
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)

    me = _FakeMember(123456789, roles=[_FakeRole(101, position=4)])
    guild = _FakeGuild(111, me)
    ctx = _FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._guild_grouped = [{"channel_id": 10, "items": []}]

    created = {}

    class _FakePaginator:
        def __init__(self, items, embed_generator, identifiant_for_embed, bot):
            created["items"] = items
            created["embed_generator"] = embed_generator
            created["ident"] = identifiant_for_embed
            created["bot"] = bot

        async def create_embed(self):
            return ("EMBED", ["FILES"])

    monkeypatch.setattr(sr_mod, "Paginator", _FakePaginator, raising=True)
    monkeypatch.setattr(sr_mod, "build_list_secret_roles_embed", lambda *_a, **_k: "X", raising=True)

    await cog.sr_list(ctx)

    assert ("sr_list_by_guild_grouped", 111) in role_svc.calls
    assert created["ident"] == 111
    assert created["bot"] is bot
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["embed"] == "EMBED"
    assert ctx.followup.sent[-1]["files"] == ["FILES"]
    assert ctx.followup.sent[-1]["view"].__class__.__name__ == "_FakePaginator"


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], SecretRoles)
