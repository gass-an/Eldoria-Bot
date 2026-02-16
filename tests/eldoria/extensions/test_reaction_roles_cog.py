from __future__ import annotations

import sys
import types

import pytest


# ---------- Local stubs / shims (in case conftest doesn't provide everything) ----------
def _ensure_discord_stubs() -> None:
    """
    Ensure the minimal subset of discord.py surface used by this cog exists at import-time.
    This complements the project's tests/conftest.py stubs and prevents import-time crashes
    due to evaluated annotations.
    """
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    # Exceptions used in the cog
    for exc_name in ("Forbidden", "HTTPException", "NotFound"):
        if not hasattr(discord, exc_name):
            setattr(discord, exc_name, type(exc_name, (Exception,), {}))

    # Basic types used in annotations / decorators
    if not hasattr(discord, "RawReactionActionEvent"):
        class RawReactionActionEvent:  # pragma: no cover
            pass
        discord.RawReactionActionEvent = RawReactionActionEvent

    if not hasattr(discord, "ApplicationContext"):
        class ApplicationContext:  # pragma: no cover
            pass
        discord.ApplicationContext = ApplicationContext

    if not hasattr(discord, "Member"):
        class Member:  # pragma: no cover
            pass
        discord.Member = Member

    if not hasattr(discord, "Role"):
        class Role:  # pragma: no cover
            pass
        discord.Role = Role

    # discord.option + default_permissions decorators (no-op in tests)
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

    # discord.ext.commands surface
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

# ---------- Import module under test (adjust path if needed) ----------
import eldoria.extensions.reaction_roles as rr_mod  # noqa: E402
from eldoria.extensions.reaction_roles import ReactionRoles, setup  # noqa: E402


# ---------- Fakes ----------
class _FakeEmoji:
    def __init__(self, name: str):
        self.name = name


class _FakePayload:
    def __init__(self, guild_id: int, user_id: int, message_id: int, emoji_name: str):
        self.guild_id = guild_id
        self.user_id = user_id
        self.message_id = message_id
        self.emoji = _FakeEmoji(emoji_name)


class _FakeRole:
    def __init__(self, role_id: int, position: int = 0):
        self.id = role_id
        self.position = position


class _FakeMember:
    def __init__(self, member_id: int, roles=None):
        self.id = member_id
        self.roles = roles or []
        self.added = []
        self.removed = []
        self._raise_add = None
        self._raise_remove = None

    async def add_roles(self, role):
        if self._raise_add:
            raise self._raise_add
        self.added.append(role)

    async def remove_roles(self, role):
        if self._raise_remove:
            raise self._raise_remove
        self.removed.append(role)

    def __eq__(self, other):
        return getattr(other, "id", object()) == self.id


class _FakeMessage:
    def __init__(self, content: str = "hello"):
        self.content = content
        self.reactions_added = []
        self.reaction_cleared = []
        self.reactions_cleared = 0
        self._raise_add_reaction = None
        self._raise_clear_reaction = None
        self._raise_clear_reactions = None

    async def add_reaction(self, emoji: str):
        if self._raise_add_reaction:
            raise self._raise_add_reaction
        self.reactions_added.append(emoji)

    async def clear_reaction(self, emoji: str):
        if self._raise_clear_reaction:
            raise self._raise_clear_reaction
        self.reaction_cleared.append(emoji)

    async def clear_reactions(self):
        if self._raise_clear_reactions:
            raise self._raise_clear_reactions
        self.reactions_cleared += 1


import discord  # type: ignore


class _FakeChannel(discord.TextChannel):  # type: ignore[misc]
    def __init__(self, message: _FakeMessage):
        self._message = message

    async def fetch_message(self, _message_id: int):
        return self._message


class _FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id
        self._members = {}
        self._roles = {}

    def get_member(self, user_id: int):
        return self._members.get(user_id)

    @property
    def me(self):
        # discord.py expose `guild.me` = Member représentant le bot sur le serveur.
        # Dans ces tests, le bot a l'id 999 (voir _FakeBotUser).
        return self._members.get(999)

    def get_role(self, role_id: int):
        return self._roles.get(role_id)


class _FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)


class _FakeCtx:
    def __init__(self, guild=None, user=None):
        self.guild = guild
        self.user = user
        self.followup = _FakeFollowup()
        self.deferred = False
        self.responded = []

    async def defer(self, ephemeral: bool = False):
        self.deferred = True
        self.defer_ephemeral = ephemeral

    async def respond(self, content: str, ephemeral: bool = False):
        self.responded.append({"content": content, "ephemeral": ephemeral})


class _FakeRoleService:
    def __init__(self):
        # For rr_get_role_id
        self._rr_role_id = None
        # For rr_list_by_message
        self._by_message = {}
        # For rr_list_by_guild_grouped
        self._guild_grouped = []
        # Calls
        self.calls = []

    def rr_get_role_id(self, guild_id: int, message_id: int, emoji: str):
        self.calls.append(("rr_get_role_id", guild_id, message_id, emoji))
        return self._rr_role_id

    def rr_list_by_message(self, guild_id: int, message_id: int):
        self.calls.append(("rr_list_by_message", guild_id, message_id))
        return dict(self._by_message)

    def rr_upsert(self, guild_id: int, message_id: int, emoji: str, role_id: int):
        self.calls.append(("rr_upsert", guild_id, message_id, emoji, role_id))

    def rr_delete(self, guild_id: int, message_id: int, emoji: str):
        self.calls.append(("rr_delete", guild_id, message_id, emoji))

    def rr_delete_message(self, guild_id: int, message_id: int):
        self.calls.append(("rr_delete_message", guild_id, message_id))

    def rr_list_by_guild_grouped(self, guild_id: int):
        self.calls.append(("rr_list_by_guild_grouped", guild_id))
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
        self._guilds = {}
        self._channels = {}

    def get_guild(self, guild_id: int):
        return self._guilds.get(guild_id)

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)

    async def fetch_channel(self, channel_id: int):
        return self._channels[channel_id]


# ---------- Tests: events ----------
@pytest.mark.asyncio
async def test_on_raw_reaction_add_ignores_missing_guild():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    cog = ReactionRoles(bot)

    payload = _FakePayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload)

    assert role_svc.calls == []


@pytest.mark.asyncio
async def test_on_raw_reaction_add_ignores_missing_member_or_bot_user():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(1)
    bot._guilds[1] = guild
    cog = ReactionRoles(bot)

    # Missing member
    payload = _FakePayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload)
    assert role_svc.calls == []

    # Member is bot user
    bot_member = _FakeMember(999)
    guild._members[999] = bot_member
    payload2 = _FakePayload(guild_id=1, user_id=999, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload2)
    assert role_svc.calls == []


@pytest.mark.asyncio
async def test_on_raw_reaction_add_no_rule_or_no_role():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(1)
    member = _FakeMember(2)
    guild._members[2] = member
    bot._guilds[1] = guild
    cog = ReactionRoles(bot)

    # No rule
    role_svc._rr_role_id = None
    payload = _FakePayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload)
    assert ("rr_get_role_id", 1, 3, "🔥") in role_svc.calls
    assert member.added == []

    # Rule exists but role missing
    role_svc.calls.clear()
    role_svc._rr_role_id = 123
    payload2 = _FakePayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload2)
    assert ("rr_get_role_id", 1, 3, "🔥") in role_svc.calls
    assert member.added == []


@pytest.mark.asyncio
async def test_on_raw_reaction_add_adds_role_and_ignores_perm_errors():
    discord = sys.modules["discord"]
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(1)
    role = _FakeRole(123)
    member = _FakeMember(2)
    guild._members[2] = member
    guild._roles[123] = role
    bot._guilds[1] = guild
    cog = ReactionRoles(bot)

    role_svc._rr_role_id = 123

    payload = _FakePayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload)
    assert member.added == [role]

    # Forbidden is swallowed
    member2 = _FakeMember(3)
    member2._raise_add = discord.Forbidden()
    guild._members[3] = member2
    payload2 = _FakePayload(guild_id=1, user_id=3, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_add(payload2)
    assert member2.added == []


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_paths():
    discord = sys.modules["discord"]
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(1)
    bot._guilds[1] = guild
    cog = ReactionRoles(bot)

    # No role mapping
    role_svc._rr_role_id = None
    payload = _FakePayload(guild_id=1, user_id=2, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_remove(payload)
    assert ("rr_get_role_id", 1, 3, "🔥") in role_svc.calls

    # Role mapping but missing role/member
    role_svc.calls.clear()
    role_svc._rr_role_id = 123
    await cog.on_raw_reaction_remove(payload)
    assert (guild.get_member(2) is None)

    # Happy path
    role = _FakeRole(123)
    member2 = _FakeMember(2)
    guild._roles[123] = role
    guild._members[2] = member2
    await cog.on_raw_reaction_remove(payload)
    assert member2.removed == [role]

    # Forbidden swallowed
    member3 = _FakeMember(3)
    member3._raise_remove = discord.Forbidden()
    guild._members[3] = member3
    payload3 = _FakePayload(guild_id=1, user_id=3, message_id=3, emoji_name="🔥")
    await cog.on_raw_reaction_remove(payload3)
    assert member3.removed == []


# ---------- Tests: /add_reaction_role ----------
@pytest.mark.asyncio
async def test_add_reaction_role_rejects_other_guild(monkeypatch):
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (222, 1, 2), raising=True)

    await cog.add_reaction_role(ctx, "link", "🔥", _FakeRole(10))
    assert ctx.followup.sent[-1]["content"] == "Le lien que vous m'avez fourni provient d'un autre serveur."


@pytest.mark.asyncio
async def test_add_reaction_role_rejects_role_above_bot(monkeypatch):
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)

    bot_member = _FakeMember(999, roles=[_FakeRole(1, position=5)])
    guild._members[999] = bot_member

    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    msg = _FakeMessage("m")
    chan = _FakeChannel(msg)
    bot._channels[777] = chan

    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)

    role = _FakeRole(10, position=5)  # equal => reject (>=)
    await cog.add_reaction_role(ctx, "link", "🔥", role)

    assert "Je ne peux pas attribuer le rôle" in ctx.followup.sent[-1]["content"]
    assert role_svc.calls == [("rr_list_by_message", 111, 888)] or role_svc.calls == []  # may return earlier


@pytest.mark.asyncio
async def test_add_reaction_role_detects_conflicts(monkeypatch):
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)

    bot_member = _FakeMember(999, roles=[_FakeRole(1, position=100)])
    guild._members[999] = bot_member

    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    msg = _FakeMessage("m")
    bot._channels[777] = _FakeChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)

    # existing same role different emoji => reject
    role_svc._by_message = {"😀": 42}
    role = _FakeRole(42, position=1)
    await cog.add_reaction_role(ctx, "link", "🔥", role)
    assert "déjà associé à l'emoji" in ctx.followup.sent[-1]["content"]

    # existing same emoji different role => reject
    ctx2 = _FakeCtx(guild=guild, user=_FakeMember(1))
    role_svc._by_message = {"🔥": 99}
    await cog.add_reaction_role(ctx2, "link", "🔥", _FakeRole(42, position=1))
    assert "déjà associé au rôle" in ctx2.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_add_reaction_role_handles_notfound_and_forbidden(monkeypatch):
    discord = sys.modules["discord"]
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)

    bot_member = _FakeMember(999, roles=[_FakeRole(1, position=100)])
    guild._members[999] = bot_member

    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    msg = _FakeMessage("m")
    bot._channels[777] = _FakeChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)
    role_svc._by_message = {}

    # NotFound during reaction add (or role ops)
    msg._raise_add_reaction = discord.NotFound()
    await cog.add_reaction_role(ctx, "link", "🔥", _FakeRole(42, position=1))
    assert ctx.followup.sent[-1]["content"] == "Message ou canal introuvable."

    # Forbidden
    ctx2 = _FakeCtx(guild=guild, user=_FakeMember(1))
    msg2 = _FakeMessage("m")
    msg2._raise_add_reaction = discord.Forbidden()
    bot._channels[778] = _FakeChannel(msg2)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 778, 888), raising=True)
    await cog.add_reaction_role(ctx2, "link", "🔥", _FakeRole(42, position=1))
    assert "Un problème est survenu" in ctx2.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_add_reaction_role_success(monkeypatch):
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)

    bot_member = _FakeMember(999, roles=[_FakeRole(1, position=100)])
    guild._members[999] = bot_member

    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    msg = _FakeMessage("hello world")
    bot._channels[777] = _FakeChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)
    role_svc._by_message = {}

    role = _FakeRole(42, position=1)
    await cog.add_reaction_role(ctx, "https://msg", "🔥", role)

    # bot role check "can manage" did a dummy add/remove
    assert bot_member.added == [role]
    assert bot_member.removed == [role]

    assert msg.reactions_added == ["🔥"]
    assert ("rr_upsert", 111, 888, "🔥", 42) in role_svc.calls
    assert "bien associée" in ctx.followup.sent[-1]["content"]


# ---------- Tests: /remove_specific_reaction ----------
@pytest.mark.asyncio
async def test_remove_specific_reaction_other_guild(monkeypatch):
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (222, 1, 2), raising=True)
    await cog.remove_specific_reaction(ctx, "link", "🔥")
    assert ctx.followup.sent[-1]["content"] == "Le lien que vous m'avez fourni provient d'un autre serveur."


@pytest.mark.asyncio
async def test_remove_specific_reaction_success_and_forbidden(monkeypatch):
    discord = sys.modules["discord"]
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    msg = _FakeMessage("m")
    bot._channels[777] = _FakeChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)

    await cog.remove_specific_reaction(ctx, "link", "🔥")
    assert ("rr_delete", 111, 888, "🔥") in role_svc.calls
    assert msg.reaction_cleared == ["🔥"]

    # Forbidden clear
    ctx2 = _FakeCtx(guild=guild, user=_FakeMember(1))
    msg2 = _FakeMessage("m")
    msg2._raise_clear_reaction = discord.Forbidden()
    bot._channels[778] = _FakeChannel(msg2)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 778, 888), raising=True)
    await cog.remove_specific_reaction(ctx2, "link", "🔥")
    assert ctx2.followup.sent[-1]["content"] == "Je n'ai pas la permission de supprimer les réactions."


# ---------- Tests: /remove_all_reactions ----------
@pytest.mark.asyncio
async def test_remove_all_reactions_other_guild(monkeypatch):
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (222, 1, 2), raising=True)
    await cog.remove_all_reactions(ctx, "link")
    assert ctx.followup.sent[-1]["content"] == "Le lien que vous m'avez fourni provient d'un autre serveur."


@pytest.mark.asyncio
async def test_remove_all_reactions_success_and_forbidden(monkeypatch):
    discord = sys.modules["discord"]
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    msg = _FakeMessage("m")
    bot._channels[777] = _FakeChannel(msg)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 777, 888), raising=True)

    await cog.remove_all_reactions(ctx, "link")
    assert ("rr_delete_message", 111, 888) in role_svc.calls
    assert msg.reactions_cleared == 1

    # Forbidden
    ctx2 = _FakeCtx(guild=guild, user=_FakeMember(1))
    msg2 = _FakeMessage("m")
    msg2._raise_clear_reactions = discord.Forbidden()
    bot._channels[778] = _FakeChannel(msg2)
    monkeypatch.setattr(rr_mod, "extract_id_from_link", lambda _s: (111, 778, 888), raising=True)
    await cog.remove_all_reactions(ctx2, "link")
    assert ctx2.followup.sent[-1]["content"] == "Je n'ai pas la permission de supprimer les réactions."


# ---------- Tests: /list_of_reaction_roles ----------
@pytest.mark.asyncio
async def test_list_reaction_roles_requires_guild():
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    ctx = _FakeCtx(guild=None, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    await cog.list_reaction_roles(ctx)
    assert ctx.responded[-1]["content"] == "Commande uniquement disponible sur un serveur."
    assert ctx.responded[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_list_reaction_roles_uses_paginator(monkeypatch):
    role_svc = _FakeRoleService()
    bot = _FakeBot(role_svc)
    guild = _FakeGuild(111)
    ctx = _FakeCtx(guild=guild, user=_FakeMember(1))
    cog = ReactionRoles(bot)

    role_svc._guild_grouped = [{"message_id": 1, "roles": []}]

    created = {}

    class _FakePaginator:
        def __init__(self, items, embed_generator, identifiant_for_embed, bot):
            created["items"] = items
            created["embed_generator"] = embed_generator
            created["ident"] = identifiant_for_embed
            created["bot"] = bot

        async def create_embed(self):
            return ("EMBED", ["FILES"])

    monkeypatch.setattr(rr_mod, "Paginator", _FakePaginator, raising=True)
    monkeypatch.setattr(rr_mod, "build_list_roles_embed", lambda *_a, **_k: "X", raising=True)

    await cog.list_reaction_roles(ctx)

    assert created["ident"] == 111
    assert created["bot"] is bot
    assert ctx.deferred is True
    assert ctx.followup.sent[-1]["embed"] == "EMBED"
    assert ctx.followup.sent[-1]["files"] == ["FILES"]
    # view is paginator instance
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
    assert isinstance(added["cog"], ReactionRoles)
