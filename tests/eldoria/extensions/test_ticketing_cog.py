from __future__ import annotations

import inspect
from types import SimpleNamespace

import discord
import pytest

from eldoria.extensions import ticketing as mod
from tests._fakes import FakeCtx


class Category:
    def __init__(self, category_id: int, name: str, position: int = 0):
        self.id = category_id
        self.name = name
        self.position = position


class Role:
    def __init__(self, role_id: int, *, manage_guild: bool = False, administrator: bool = False):
        self.id = role_id
        self.permissions = SimpleNamespace(
            manage_guild=manage_guild, administrator=administrator
        )

    def __hash__(self):
        return hash(self.id)


class Member:
    def __init__(self, member_id: int):
        self.id = member_id

    def __hash__(self):
        return hash(self.id)


class PermissionOverwrite:
    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)

    def pair(self):
        names = sorted(self.kwargs)
        allow = sum(1 << index for index, name in enumerate(names) if self.kwargs[name])
        deny = sum(1 << index for index, name in enumerate(names) if self.kwargs[name] is False)
        return SimpleNamespace(value=allow), SimpleNamespace(value=deny)


class RawOverwrite:
    def __init__(self, target_id: int, overwrite_type: int, allow: int, deny: int):
        self.id = target_id
        self.type = overwrite_type
        self.allow = allow
        self.deny = deny


def raw_overwrites(guild, overwrites):
    result = []
    for target, overwrite in overwrites.items():
        allow, deny = overwrite.pair()
        result.append(
            RawOverwrite(
                target.id,
                1 if target == guild.me else 0,
                allow.value,
                deny.value,
            )
        )
    return result


class Channel(discord.abc.GuildChannel):  # type: ignore[misc]
    def __init__(
        self,
        channel_id: int,
        guild,
        *,
        fail_edit: bool = False,
        fail_send: bool = False,
    ):
        self.id = channel_id
        self.guild = guild
        self.fail_edit = fail_edit
        self.fail_send = fail_send
        self.name = "ticket-007"
        self.category = guild.ticket_category
        self.overwrites = {}
        self._overwrites = []
        self.sent = []
        self.edits = []

    async def send(self, **kwargs):
        if self.fail_send:
            raise discord.HTTPException("cannot send")
        self.sent.append(kwargs)

    async def edit(self, **kwargs):
        if self.fail_edit:
            raise discord.HTTPException("discord unavailable")
        self.edits.append(kwargs)
        self.name = kwargs.get("name", self.name)
        self.category = kwargs.get("category", self.category)
        self.overwrites = kwargs.get("overwrites", self.overwrites)
        self._overwrites = raw_overwrites(self.guild, self.overwrites)
        return self


class Service:
    def __init__(
        self,
        ticket=None,
        *,
        archive_category_id=0,
        close_result=True,
        close_error=None,
        status_after_false=None,
    ):
        self.ticket = ticket
        self.config = {
            "category_id": 10,
            "archive_category_id": archive_category_id,
        }
        self.saved_archive_ids = []
        self.closed = []
        self.close_result = close_result
        self.close_error = close_error
        self.status_after_false = status_after_false

    def get_config(self, _guild_id):
        return self.config

    def set_archive_category_id(self, _guild_id, category_id):
        self.config["archive_category_id"] = category_id
        self.saved_archive_ids.append(category_id)

    def get_ticket_by_channel(self, _guild_id, _channel_id):
        return None if self.ticket is None else dict(self.ticket)

    def close_ticket(self, ticket_id, closed_at):
        self.closed.append((ticket_id, closed_at))
        if self.close_error is not None:
            raise self.close_error
        if self.close_result:
            self.ticket["status"] = "CLOSED"
            return True
        if self.status_after_false is not None:
            self.ticket["status"] = self.status_after_false
        return False


class Guild:
    def __init__(self, service, *, archive=None):
        self.id = 1
        self.default_role = Role(1)
        self.admin_role = Role(2, manage_guild=True)
        self.regular_role = Role(3)
        self.roles = [self.default_role, self.admin_role, self.regular_role]
        self.me = Role(999)
        self.ticket_category = Category(10, "Tickets", 4)
        self.categories = [self.ticket_category]
        self.channels = {10: self.ticket_category}
        self.created = []
        if archive is not None:
            self.categories.append(archive)
            self.channels[archive.id] = archive

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    async def create_category(self, **kwargs):
        archive = Category(20, kwargs["name"], kwargs.get("position", 0))
        self.created.append(kwargs)
        self.categories.append(archive)
        self.channels[archive.id] = archive
        return archive


def make_cog(
    monkeypatch,
    *,
    ticket=None,
    archive=None,
    archive_category_id=0,
    fail_edit=False,
    fail_send=False,
    close_result=True,
    close_error=None,
    status_after_false=None,
    bot_member_present=True,
):
    monkeypatch.setattr(mod.discord, "CategoryChannel", Category, raising=False)
    monkeypatch.setattr(mod.discord, "PermissionOverwrite", PermissionOverwrite)
    service = Service(
        ticket,
        archive_category_id=archive_category_id,
        close_result=close_result,
        close_error=close_error,
        status_after_false=status_after_false,
    )
    guild = Guild(service, archive=archive)
    if not bot_member_present:
        guild.me = None
    channel = Channel(100, guild, fail_edit=fail_edit, fail_send=fail_send)
    guild.channels[channel.id] = channel
    author = SimpleNamespace(id=42, mention="<@42>")
    ctx = FakeCtx(guild=guild, channel=channel, author=author, user=author)
    bot = SimpleNamespace(services=SimpleNamespace(ticketing=service))
    return mod.Ticketing(bot), ctx, service, guild, channel


@pytest.mark.asyncio
async def test_close_archives_with_fresh_category_and_private_read_only_overwrites(monkeypatch):
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, guild, channel = make_cog(monkeypatch, ticket=ticket)
    monkeypatch.setattr(mod, "now_ts", lambda: 123456)

    await cog.close_ticket(ctx)

    assert guild.created == [{"name": "Tickets Archivés", "position": 5}]
    assert service.saved_archive_ids == [20]
    assert channel.edits[0]["name"] == "closed-007"
    assert channel.edits[0]["sync_permissions"] is False
    overwrites = channel.edits[0]["overwrites"]
    assert set(overwrites) == {guild.default_role, guild.admin_role, guild.me}
    assert overwrites[guild.default_role].kwargs["view_channel"] is False
    assert overwrites[guild.admin_role].kwargs["view_channel"] is True
    assert overwrites[guild.admin_role].kwargs["send_messages"] is False
    assert overwrites[guild.admin_role].kwargs["send_messages_in_threads"] is False
    assert overwrites[guild.admin_role].kwargs["add_reactions"] is False
    assert overwrites[guild.admin_role].kwargs["manage_webhooks"] is False
    assert overwrites[guild.admin_role].kwargs["manage_channels"] is False
    assert overwrites[guild.admin_role].kwargs["use_application_commands"] is False
    assert set(overwrites[guild.admin_role].kwargs) == {
        "view_channel",
        "read_message_history",
        "send_messages",
        "send_messages_in_threads",
        "create_public_threads",
        "create_private_threads",
        "add_reactions",
        "send_tts_messages",
        "mention_everyone",
        "manage_messages",
        "manage_threads",
        "manage_webhooks",
        "manage_channels",
        "manage_permissions",
        "pin_messages",
        "use_application_commands",
        "use_external_apps",
        "send_voice_messages",
        "send_polls",
    }
    assert service.closed == [(5, 123456)]
    assert channel.sent[0]["allowed_mentions"].everyone is False
    assert ctx.followup.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_close_rejects_non_ticket_and_already_closed(monkeypatch):
    cog, ctx, service, _, _ = make_cog(monkeypatch, ticket=None)
    await cog.close_ticket(ctx)
    assert ctx.followup.sent[-1]["content"] == (
        "Cette commande ne peut être utilisée que dans un ticket."
    )

    service.ticket = {"id": 5, "ticket_number": 7, "status": "CLOSED"}
    await cog.close_ticket(ctx)
    assert ctx.followup.sent[-1]["content"] == "Ce ticket est déjà archivé."


@pytest.mark.asyncio
async def test_close_reuses_persisted_renamed_category(monkeypatch):
    archive = Category(20, "Anciennes requêtes", 30)
    ticket = {"id": 5, "ticket_number": 1000, "status": "OPEN"}
    cog, ctx, service, guild, channel = make_cog(
        monkeypatch, ticket=ticket, archive=archive, archive_category_id=20
    )

    await cog.close_ticket(ctx)

    assert guild.created == []
    assert service.saved_archive_ids == []
    assert channel.edits[0]["category"] is archive
    assert channel.edits[0]["name"] == "closed-1000"


@pytest.mark.asyncio
async def test_close_reuses_untracked_named_category(monkeypatch):
    archive = Category(20, "Tickets Archivés", 30)
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, guild, _ = make_cog(monkeypatch, ticket=ticket, archive=archive)

    await cog.close_ticket(ctx)

    assert guild.created == []
    assert service.saved_archive_ids == [20]


@pytest.mark.asyncio
async def test_discord_failure_does_not_close_database_ticket(monkeypatch):
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, _, channel = make_cog(
        monkeypatch, ticket=ticket, fail_edit=True
    )

    await cog.close_ticket(ctx)

    assert service.closed == []
    assert ticket["status"] == "OPEN"
    assert channel.sent == []
    assert "Impossible d'archiver" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_false_close_result_while_still_open_reports_partial_state(monkeypatch):
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, _, channel = make_cog(
        monkeypatch, ticket=ticket, close_result=False
    )

    await cog.close_ticket(ctx)

    assert len(channel.edits) == 1
    assert channel.sent == []
    assert ticket["status"] == "OPEN"
    assert "base indique encore" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_false_close_result_when_already_closed_is_not_an_error(monkeypatch):
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, _, _, channel = make_cog(
        monkeypatch,
        ticket=ticket,
        close_result=False,
        status_after_false="CLOSED",
    )

    await cog.close_ticket(ctx)

    assert len(channel.edits) == 1
    assert channel.sent == []
    assert "déjà archivé" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_sqlite_error_can_be_retried_with_close(monkeypatch):
    import sqlite3

    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, _, channel = make_cog(
        monkeypatch,
        ticket=ticket,
        close_error=sqlite3.OperationalError("database locked"),
    )

    await cog.close_ticket(ctx)

    assert len(channel.edits) == 1
    assert channel.sent == []
    assert "archivé sur Discord" in ctx.followup.sent[-1]["content"]
    assert "Réessayez `/close`" in ctx.followup.sent[-1]["content"]

    service.close_error = None
    await cog.close_ticket(ctx)

    assert len(channel.edits) == 1
    assert len(channel.sent) == 1
    assert ticket["status"] == "CLOSED"
    assert ctx.followup.sent[-1]["content"] == "Le ticket #007 a été archivé."


@pytest.mark.asyncio
async def test_retry_reapplies_raw_overwrite_for_participant_missing_from_cache(
    monkeypatch,
):
    archive = Category(20, "Tickets Archivés", 30)
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, guild, channel = make_cog(
        monkeypatch,
        ticket=ticket,
        archive=archive,
        archive_category_id=20,
    )
    former_participant = Member(77)
    channel.name = "closed-007"
    channel.category = archive
    channel.overwrites = cog._archive_overwrites(guild)
    channel._overwrites = raw_overwrites(guild, channel.overwrites)
    # Simule py-cord: channel.overwrites omet le membre absent du cache,
    # tandis que channel._overwrites conserve bien son entrée Discord brute.
    channel._overwrites.append(
        RawOverwrite(former_participant.id, 1, allow=1, deny=0)
    )

    await cog.close_ticket(ctx)

    assert len(channel.edits) == 1
    applied = channel.edits[0]["overwrites"]
    assert former_participant not in applied
    assert set(applied) == {guild.default_role, guild.admin_role, guild.me}
    assert service.closed


@pytest.mark.asyncio
async def test_retry_skips_edit_when_archive_permissions_are_exact(monkeypatch):
    archive = Category(20, "Tickets Archivés", 30)
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, guild, channel = make_cog(
        monkeypatch,
        ticket=ticket,
        archive=archive,
        archive_category_id=20,
    )
    channel.name = "closed-007"
    channel.category = archive
    channel.overwrites = cog._archive_overwrites(guild)
    channel._overwrites = raw_overwrites(guild, channel.overwrites)

    await cog.close_ticket(ctx)

    assert channel.edits == []
    assert service.closed
    assert len(channel.sent) == 1


@pytest.mark.asyncio
async def test_close_refuses_before_discord_changes_when_bot_member_is_missing(
    monkeypatch,
):
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, guild, channel = make_cog(
        monkeypatch, ticket=ticket, bot_member_present=False
    )

    await cog.close_ticket(ctx)

    assert guild.created == []
    assert channel.edits == []
    assert service.closed == []
    assert "membre serveur est introuvable" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_close_uses_channel_returned_by_pycord_edit(monkeypatch):
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, _, guild, channel = make_cog(monkeypatch, ticket=ticket)
    edited_channel = Channel(100, guild)

    async def edit_returns_new_channel(**kwargs):
        channel.edits.append(kwargs)
        edited_channel.name = kwargs["name"]
        edited_channel.category = kwargs["category"]
        edited_channel.overwrites = kwargs["overwrites"]
        edited_channel._overwrites = raw_overwrites(guild, kwargs["overwrites"])
        return edited_channel

    channel.edit = edit_returns_new_channel

    await cog.close_ticket(ctx)

    assert channel.sent == []
    assert len(edited_channel.sent) == 1


@pytest.mark.asyncio
async def test_embed_failure_does_not_undo_successful_close(monkeypatch):
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx, service, _, channel = make_cog(
        monkeypatch, ticket=ticket, fail_send=True
    )

    await cog.close_ticket(ctx)

    assert len(channel.edits) == 1
    assert service.closed
    assert ticket["status"] == "CLOSED"
    assert ctx.followup.sent[-1]["content"] == "Le ticket #007 a été archivé."


@pytest.mark.asyncio
async def test_historical_ticket_without_number_is_not_partially_archived(monkeypatch):
    ticket = {"id": 5, "ticket_number": None, "status": "OPEN"}
    cog, ctx, service, guild, channel = make_cog(monkeypatch, ticket=ticket)

    await cog.close_ticket(ctx)

    assert guild.created == []
    assert channel.edits == []
    assert channel.sent == []
    assert service.closed == []
    assert "pas de numéro public fiable" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_concurrent_close_only_archives_and_notifies_once(monkeypatch):
    ticket = {"id": 5, "ticket_number": 7, "status": "OPEN"}
    cog, ctx_a, service, guild, channel = make_cog(monkeypatch, ticket=ticket)
    author_b = SimpleNamespace(id=43, mention="<@43>")
    ctx_b = FakeCtx(guild=guild, channel=channel, author=author_b, user=author_b)

    import asyncio

    await asyncio.gather(cog.close_ticket(ctx_a), cog.close_ticket(ctx_b))

    assert len(channel.edits) == 1
    assert len(channel.sent) == 1
    assert len(service.closed) == 1


def test_close_reuses_ticketing_admin_permission_decorators():
    source = inspect.getsource(mod.Ticketing)
    close_source = source[source.index('@commands.slash_command(name="close"') :]
    assert "@discord.default_permissions(manage_guild=True)" in close_source
    assert "@commands.has_permissions(manage_guild=True)" in close_source
