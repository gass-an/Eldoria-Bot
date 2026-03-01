from __future__ import annotations

import sys

import pytest

# ---------- Import module under test (adjust path if needed) ----------
import eldoria.extensions.reaction_roles as rr_mod  # noqa: E402
from eldoria.exceptions.general import GuildRequired
from eldoria.extensions.reaction_roles import ReactionRoles, setup  # noqa: E402
from tests._fakes import (
    FakeBot,
    FakeCtx,
    FakeGuild,
    FakeMember,
    FakeMessage,
    FakeReactionChannel,
    FakeReactionPayload,
    FakeRole,
    FakeRoleService,
    FakeServices,
)


# ---------- Tests: events ----------
@pytest.mark.asyncio
async def test_on_raw_reaction_add_ignores_missing_guild():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    cog = ReactionRoles(bot)

    payload = FakeReactionPayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload)

    assert role_svc.calls == []


@pytest.mark.asyncio
async def test_on_raw_reaction_add_ignores_missing_member_or_bot_user():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(1)
    bot._guilds[1] = guild
    cog = ReactionRoles(bot)

    # Missing member
    payload = FakeReactionPayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload)
    assert role_svc.calls == []

    # Member is bot user
    bot_member = FakeMember(999)
    guild._members[999] = bot_member
    payload2 = FakeReactionPayload(guild_id=1, user_id=999, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload2)
    assert role_svc.calls == []


@pytest.mark.asyncio
async def test_on_raw_reaction_add_no_rule_or_no_role():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(1)
    member = FakeMember(2)
    guild._members[2] = member
    bot._guilds[1] = guild
    cog = ReactionRoles(bot)

    # No rule
    role_svc._rr_role_id = None
    payload = FakeReactionPayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload)
    assert ("rr_get_role_id", 1, 3, "🔥") in role_svc.calls
    assert member.added == []

    # Rule exists but role missing
    role_svc.calls.clear()
    role_svc._rr_role_id = 123
    payload2 = FakeReactionPayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload2)
    assert ("rr_get_role_id", 1, 3, "🔥") in role_svc.calls
    assert member.added == []


@pytest.mark.asyncio
async def test_on_raw_reaction_add_adds_role_and_ignores_perm_errors():
    discord = sys.modules["discord"]
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(1)
    role = FakeRole(123)
    member = FakeMember(2)
    guild._members[2] = member
    guild._roles[123] = role
    bot._guilds[1] = guild
    cog = ReactionRoles(bot)

    role_svc._rr_role_id = 123

    payload = FakeReactionPayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload)
    assert member.added == [role]

    # Forbidden is swallowed
    member2 = FakeMember(3)
    member2._raise_add = discord.Forbidden()
    guild._members[3] = member2
    payload2 = FakeReactionPayload(guild_id=1, user_id=3, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload2)
    assert member2.added == []


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_paths():
    discord = sys.modules["discord"]
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(1)
    bot._guilds[1] = guild
    cog = ReactionRoles(bot)

    # No role mapping
    role_svc._rr_role_id = None
    payload = FakeReactionPayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_remove(payload)
    assert ("rr_get_role_id", 1, 3, "🔥") in role_svc.calls

    # Role mapping but missing role/member
    role_svc.calls.clear()
    role_svc._rr_role_id = 123
    await cog.on_raw_reaction_remove(payload)
    assert (guild.get_member(2) is None)

    # Happy path
    role = FakeRole(123)
    member2 = FakeMember(2)
    guild._roles[123] = role
    guild._members[2] = member2
    await cog.on_raw_reaction_remove(payload)
    assert member2.removed == [role]

    # Forbidden swallowed
    member3 = FakeMember(3)
    member3._raise_remove = discord.Forbidden()
    guild._members[3] = member3
    payload3 = FakeReactionPayload(guild_id=1, user_id=3, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_remove(payload3)
    assert member3.removed == []


# ---------- Tests: /add_reaction_role ----------
@pytest.mark.asyncio
async def test_add_reaction_role_rejects_other_guild(monkeypatch):
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)
    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (222, 1, 2), raising=True)

    from eldoria.exceptions.role import InvalidGuild

    with pytest.raises(InvalidGuild):
        await cog.rr_add(ctx, "link", "🔥", FakeRole(10))


@pytest.mark.asyncio
async def test_add_reaction_role_rejects_role_above_bot(monkeypatch):
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)

    bot_member = FakeMember(999, roles=[FakeRole(1, position=5)], top_role_position=5)
    guild._members[999] = bot_member

    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    msg = FakeMessage("m")
    chan = FakeReactionChannel(msg)
    bot._channels[777] = chan

    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)

    from eldoria.exceptions.role import RoleAboveBot

    role = FakeRole(10, position=5)  # equal => reject (>=)
    with pytest.raises(RoleAboveBot):
        await cog.rr_add(ctx, "link", "🔥", role)


@pytest.mark.asyncio
async def test_add_reaction_role_detects_conflicts(monkeypatch):
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)

    bot_member = FakeMember(999, roles=[FakeRole(1, position=100)])
    guild._members[999] = bot_member

    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    msg = FakeMessage("m")
    bot._channels[777] = FakeReactionChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)

    # existing same role different emoji => reject
    role_svc._by_message = {"😀": 42}
    role = FakeRole(42, position=1)
    from eldoria.exceptions.role import RoleAlreadyBound

    with pytest.raises(RoleAlreadyBound):
        await cog.rr_add(ctx, "link", "🔥", role)

    # existing same emoji different role => reject
    ctx2 = FakeCtx(guild=guild, user=FakeMember(1))
    role_svc._by_message = {"🔥": 99}
    from eldoria.exceptions.role import EmojiAlreadyBound

    with pytest.raises(EmojiAlreadyBound):
        await cog.rr_add(ctx2, "link", "🔥", FakeRole(42, position=1))


@pytest.mark.asyncio
async def test_add_reaction_role_handles_notfound_and_forbidden(monkeypatch):
    discord = sys.modules["discord"]
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)

    bot_member = FakeMember(999, roles=[FakeRole(1, position=100)])
    guild._members[999] = bot_member

    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    msg = FakeMessage("m")
    bot._channels[777] = FakeReactionChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)
    role_svc._by_message = {}

    # NotFound during reaction add (or role ops)
    msg._raise_add_reaction = discord.NotFound()
    with pytest.raises(discord.NotFound):
            await cog.rr_add(ctx, "link", "🔥", FakeRole(42, position=1))


    # Forbidden
    ctx2 = FakeCtx(guild=guild, user=FakeMember(1))
    msg2 = FakeMessage("m")
    msg2._raise_add_reaction = discord.Forbidden()
    bot._channels[778] = FakeReactionChannel(msg2)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 778, 888), raising=True)
    with pytest.raises(discord.Forbidden):
        await cog.rr_add(ctx2, "link", "🔥", FakeRole(42, position=1))



@pytest.mark.asyncio
async def test_add_reaction_role_success(monkeypatch):
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)

    bot_member = FakeMember(999, roles=[FakeRole(1, position=100)])
    guild._members[999] = bot_member

    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    msg = FakeMessage("hello world")
    bot._channels[777] = FakeReactionChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)
    role_svc._by_message = {}

    role = FakeRole(42, position=1)
    await cog.rr_add(ctx, "https://msg", "🔥", role)

    # bot role check "can manage" did a dummy add/remove
    assert bot_member.added == [role]
    assert bot_member.removed == [role]

    assert msg.reactions_added == ["🔥"]
    assert ("rr_upsert", 111, 888, "🔥", 42) in role_svc.calls
    assert "bien associée" in ctx.followup.sent[-1]["content"]


# ---------- Tests: /remove_specific_reaction ----------
@pytest.mark.asyncio
async def test_remove_specific_reaction_other_guild(monkeypatch):
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)
    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    from eldoria.exceptions.role import InvalidGuild

    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (222, 1, 2), raising=True)
    with pytest.raises(InvalidGuild):
        await cog.rr_remove(ctx, "link", "🔥")


@pytest.mark.asyncio
async def test_remove_specific_reaction_success_and_forbidden(monkeypatch):
    discord = sys.modules["discord"]
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)
    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    msg = FakeMessage("m")
    bot._channels[777] = FakeReactionChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)

    await cog.rr_remove(ctx, "link", "🔥")
    assert ("rr_delete", 111, 888, "🔥") in role_svc.calls
    assert msg.reaction_cleared == ["🔥"]

    # Forbidden clear
    ctx2 = FakeCtx(guild=guild, user=FakeMember(1))
    msg2 = FakeMessage("m")
    msg2._raise_clear_reaction = discord.Forbidden()
    bot._channels[778] = FakeReactionChannel(msg2)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 778, 888), raising=True)

    with pytest.raises(discord.Forbidden):
        await cog.rr_remove(ctx2, "link", "🔥")


# ---------- Tests: /remove_all_reactions ----------
@pytest.mark.asyncio
async def test_remove_all_reactions_other_guild(monkeypatch):
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)
    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    from eldoria.exceptions.role import InvalidGuild

    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (222, 1, 2), raising=True)
    with pytest.raises(InvalidGuild):
        await cog.rr_clear(ctx, "link")


@pytest.mark.asyncio
async def test_remove_all_reactions_success_and_forbidden(monkeypatch):
    discord = sys.modules["discord"]
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)
    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    msg = FakeMessage("m")
    bot._channels[777] = FakeReactionChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)

    await cog.rr_clear(ctx, "link")
    assert ("rr_delete_message", 111, 888) in role_svc.calls
    assert msg.reactions_cleared == 1

    # Forbidden
    ctx2 = FakeCtx(guild=guild, user=FakeMember(1))
    msg2 = FakeMessage("m")
    msg2._raise_clear_reactions = discord.Forbidden()
    bot._channels[778] = FakeReactionChannel(msg2)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 778, 888), raising=True)
    with pytest.raises(discord.Forbidden):
        await cog.rr_clear(ctx2, "link")



# ---------- Tests: /list_of_reaction_roles ----------
@pytest.mark.asyncio
async def test_list_reaction_roles_requires_guild():
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    ctx = FakeCtx(guild=None, user=FakeMember(1))
    cog = ReactionRoles(bot)

    with pytest.raises(GuildRequired):
        await cog.rr_list(ctx)


@pytest.mark.asyncio
async def test_list_reaction_roles_uses_paginator(monkeypatch):
    role_svc = FakeRoleService()
    bot = FakeBot(services=FakeServices(role=role_svc))
    guild = FakeGuild(111)
    ctx = FakeCtx(guild=guild, user=FakeMember(1))
    cog = ReactionRoles(bot)

    role_svc._guild_grouped = [{"message_id": 1, "roles": []}]

    created = {}

    def paginator_factory(items, embed_generator, identifiant_for_embed, bot):
        created["items"] = items
        created["embed_generator"] = embed_generator
        created["ident"] = identifiant_for_embed
        created["bot"] = bot

        async def create_embed(self):
            return ("EMBED", ["FILES"])

        return type("PaginatorStub", (), {"create_embed": create_embed})()

    monkeypatch.setattr(rr_mod, "Paginator", paginator_factory, raising=True)
    monkeypatch.setattr(rr_mod, "build_list_roles_embed", lambda *_a, **_k: "X", raising=True)

    await cog.rr_list(ctx)

    assert created["ident"] == 111
    assert created["bot"] is bot
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["embed"] == "EMBED"
    assert ctx.followup.sent[-1]["files"] == ["FILES"]
    # view is paginator-like
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
    assert isinstance(added["cog"], ReactionRoles)
