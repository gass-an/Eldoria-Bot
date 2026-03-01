from __future__ import annotations

import sys

import pytest

# ---------- Import module under test (adjust if needed) ----------
import eldoria.extensions.secret_roles as sr_mod  # noqa: E402
from eldoria.extensions.secret_roles import SecretRoles, setup  # noqa: E402
from tests._fakes import (
    FakeBot,
    FakeCtx,
    FakeGuild,
    FakeMember,
    FakeRole,
    FakeRoleService,
    FakeServices,
    FakeTextChannel,
)


# ---------- Tests: add_secret_role ----------
@pytest.mark.asyncio
async def test_add_secret_role_requires_guild():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    cog = SecretRoles(bot)
    ctx = FakeCtx(guild=None)

    # Nouveau contrat: la commande lève GuildRequired quand elle n'est pas dans une guild.
    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.sr_add(ctx, "msg", FakeTextChannel(10), FakeRole(1))


@pytest.mark.asyncio
async def test_add_secret_role_rejects_role_above_bot():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))

    
    me = FakeMember(123456789, roles=[FakeRole(101, position=4)], top_role_position=5)
    guild = FakeGuild(111, me=me)
    ctx = FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    from eldoria.exceptions.role import RoleAboveBot

    role = FakeRole(1, position=5)  # equal => reject
    with pytest.raises(RoleAboveBot):
        await cog.sr_add(ctx, "msg", FakeTextChannel(10), role)


@pytest.mark.asyncio
async def test_add_secret_role_rejects_existing_other_role():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))

    me = FakeMember(123456789, roles=[FakeRole(101, position=4)])
    guild = FakeGuild(111, me=me)
    ctx = FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_match_role_id = 9999
    from eldoria.exceptions.role import MessageAlreadyBound

    with pytest.raises(MessageAlreadyBound):
        await cog.sr_add(ctx, "hello", FakeTextChannel(10), FakeRole(1, position=1))


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_add_secret_role_propagates_forbidden_when_probing_role():
    discord = sys.modules["discord"]
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))

    me = FakeMember(123456789, roles=[FakeRole(101, position=4)])
    me._raise_add = discord.Forbidden()
    guild = FakeGuild(111, me=me)
    ctx = FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    with pytest.raises(discord.Forbidden):
        await cog.sr_add(ctx, "hello", FakeTextChannel(10), FakeRole(1, position=1))


@pytest.mark.asyncio
async def test_add_secret_role_success_upserts_and_confirms():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))

    me = FakeMember(123456789, roles=[FakeRole(101, position=4)])
    guild = FakeGuild(111, me=me)
    ctx = FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_match_role_id = None
    role = FakeRole(1, position=1)
    await cog.sr_add(ctx, "hello", FakeTextChannel(10), role)

    # probes add/remove worked
    assert me.added == [role]
    assert me.removed == [role]

    assert ("sr_upsert", 111, 10, "hello", 1) in role_svc.calls
    assert "bien associée" in ctx.followup.sent[-1]["content"]


# ---------- Tests: delete_secret_role ----------
@pytest.mark.asyncio
async def test_delete_secret_role_requires_guild():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    cog = SecretRoles(bot)
    ctx = FakeCtx(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.sr_remove(ctx, FakeTextChannel(10), "msg")


@pytest.mark.asyncio
async def test_delete_secret_role_handles_not_found():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))

    me = FakeMember(123456789, roles=[FakeRole(101, position=4)])
    guild = FakeGuild(111, me=me)
    ctx = FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_match_role_id = None
    from eldoria.exceptions.role import SecretRoleNotFound

    with pytest.raises(SecretRoleNotFound):
        await cog.sr_remove(ctx, FakeTextChannel(10), "hello")


@pytest.mark.asyncio
async def test_delete_secret_role_deletes_when_exists():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))

    me = FakeMember(123456789, roles=[FakeRole(101, position=4)])
    guild = FakeGuild(111, me=me)
    ctx = FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_match_role_id = 42
    await cog.sr_remove(ctx, FakeTextChannel(10), "hello")
    assert ("sr_delete", 111, 10, "hello") in role_svc.calls
    assert "n'attribue plus de rôle" in ctx.followup.sent[-1]["content"]


# ---------- Tests: list_of_secret_roles ----------
@pytest.mark.asyncio
async def test_list_of_secret_roles_requires_guild():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    cog = SecretRoles(bot)
    ctx = FakeCtx(guild=None)

    from eldoria.exceptions.general import GuildRequired

    with pytest.raises(GuildRequired):
        await cog.sr_list(ctx)


@pytest.mark.asyncio
async def test_list_of_secret_roles_uses_paginator(monkeypatch):
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))

    me = FakeMember(123456789, roles=[FakeRole(101, position=4)])
    guild = FakeGuild(111, me=me)
    ctx = FakeCtx(guild=guild)
    cog = SecretRoles(bot)

    role_svc._sr_guild_grouped = [{"channel_id": 10, "items": []}]

    created = {}

    def paginator_factory(items, embed_generator, identifiant_for_embed, bot):
        created["items"] = items
        created["embed_generator"] = embed_generator
        created["ident"] = identifiant_for_embed
        created["bot"] = bot

        async def create_embed(self):
            return ("EMBED", ["FILES"])

        return type("PaginatorStub", (), {"create_embed": create_embed})()

    monkeypatch.setattr(sr_mod, "Paginator", paginator_factory, raising=True)
    monkeypatch.setattr(sr_mod, "build_list_secret_roles_embed", lambda *_a, **_k: "X", raising=True)

    await cog.sr_list(ctx)

    assert ("sr_list_by_guild_grouped", 111) in role_svc.calls
    assert created["ident"] == 111
    assert created["bot"] is bot
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["embed"] == "EMBED"
    assert ctx.followup.sent[-1]["files"] == ["FILES"]
    assert hasattr(ctx.followup.sent[-1]["view"], "create_embed")


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], SecretRoles)
